import logging
import uuid

from models.schemas import (
    AgentStage,
    DeterministicFilters,
    EnrollmentRequest,
    LearningGoal,
    RankingResult,
)
from stepik_agent.agents.skills.enroll_skill import EnrollSkill
from stepik_agent.agents.skills.rank_skill import RankSkill
from stepik_agent.agents.skills.refine_skill import RefineSkill
from stepik_agent.agents.skills.search_skill import SearchSkill
from stepik_agent.agents.stages import stage_banner
from stepik_agent.config import AppSettings, UserPreferences, load_user_preferences
from stepik_agent.db.preferences import PreferencesStore
from stepik_agent.db.search_log import SearchLogStore
from stepik_agent.llm.client import LLMClient
from stepik_agent.pipeline.forms import form_prompt_text, parse_form_response
from stepik_agent.pipeline.history import MessageHistory
from stepik_agent.security.jailbreak import is_jailbreak_attempt, jailbreak_response


logger = logging.getLogger("stepik_agent")

WELCOME_TEXT = (
    "Я помощник по подбору курсов на Stepik. "
    "Сначала опишите текстом, чему хотите научиться. "
    "Затем я задам вопросы по языку, нагрузке и другим параметрам — "
    "их нужно заполнить явно, без догадок с моей стороны."
)


class AgentOrchestrator:
    """Coordinates stages, skills, DB, and chat history."""

    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self.prefs_yaml = load_user_preferences()
        self.prefs_db = PreferencesStore(settings.data_dir / "preferences.db")
        self.search_log = SearchLogStore(settings.data_dir / "search_log.db")
        self.llm = LLMClient(settings)
        self.history = MessageHistory()
        self.session_id = str(uuid.uuid4())[:8]
        self.stage = AgentStage.COLLECT_GOAL
        self.goal: LearningGoal | None = None
        self.filters = DeterministicFilters()
        self.courses: list[dict] = []
        self.rejected_det: list[dict] = []
        self.ranking: RankingResult | None = None
        self.pending_enroll: EnrollmentRequest | None = None
        self._awaiting_form = False

        self.search_skill = SearchSkill(self.llm, self.search_log, settings.stepik_token)
        self.refine_skill = RefineSkill(self.llm)
        self.rank_skill = RankSkill(self.llm)
        self.enroll_skill = EnrollSkill()

    def bootstrap_preferences(self) -> None:
        self.prefs_db.set_preference("default_result_count", str(self.prefs_yaml.default_result_count))
        self.prefs_db.set_preference("message_tone", self.prefs_yaml.message_tone)
        if self.prefs_yaml.preferred_language:
            self.prefs_db.set_preference("preferred_language", self.prefs_yaml.preferred_language)

    def prefs_snapshot(self) -> dict:
        stored = self.prefs_db.list_preferences()
        return {**self.prefs_yaml.model_dump(), **stored}

    def handle_message(self, user_text: str) -> str:
        if is_jailbreak_attempt(user_text):
            logger.warning("jailbreak_blocked session=%s", self.session_id)
            return jailbreak_response()

        self.history.add("user", user_text)
        reply = self._route(user_text)
        self.history.add("assistant", reply)
        logger.info("stage=%s session=%s", self.stage.value, self.session_id)
        return reply

    def _route(self, user_text: str) -> str:
        if self.stage == AgentStage.COLLECT_GOAL:
            self.goal = LearningGoal(raw_text=user_text.strip())
            self.prefs_db.add_session_note(f"goal: {self.goal.raw_text[:200]}")
            self.stage = AgentStage.COLLECT_DETERMINISTIC
            self._awaiting_form = True
            return stage_banner(AgentStage.COLLECT_DETERMINISTIC) + "\n\n" + form_prompt_text()

        if self.stage == AgentStage.COLLECT_DETERMINISTIC and self._awaiting_form:
            self.filters = parse_form_response(user_text)
            self._awaiting_form = False
            return self._run_search_pipeline()

        if self.stage in {AgentStage.PRESENT, AgentStage.FOLLOW_UP}:
            return self._handle_follow_up(user_text)

        if self.stage == AgentStage.ENROLL_CONFIRM and self.pending_enroll:
            req = self.enroll_skill.parse_confirmation(user_text, self.pending_enroll)
            if not req.confirmed:
                self.stage = AgentStage.FOLLOW_UP
                self.pending_enroll = None
                return "Запись отменена. Можете уточнить приоритеты или запросить новый поиск."
            msg = self.enroll_skill.run_enrollment(req)
            self.stage = AgentStage.FOLLOW_UP
            self.pending_enroll = None
            return msg

        return stage_banner(self.stage) + "\nОжидаю цель обучения или уточнение."

    def _run_search_pipeline(self) -> str:
        parts = []
        goal_text = self.goal.raw_text if self.goal else ""
        n = int(self.prefs_db.get_preference("default_result_count") or 5)
        prefs = self.prefs_snapshot()

        self.stage = AgentStage.GENERATE_QUERIES
        parts.append(stage_banner(self.stage))
        query_set = self.search_skill.generate_queries(goal_text, self.filters, prefs, count=5)
        parts.append("Запросы: " + ", ".join(query_set.queries))

        self.stage = AgentStage.SEARCH_INITIAL
        parts.append(stage_banner(self.stage))
        kept, rej = self.search_skill.run_searches(
            query_set.queries,
            self.session_id,
            self.filters,
            per_query_limit=n,
            stage="initial",
        )
        self.rejected_det = rej

        if not kept:
            self.stage = AgentStage.PRESENT
            return (
                "\n\n".join(parts)
                + "\n\n"
                + stage_banner(AgentStage.PRESENT)
                + "\nКурсы не найдены. Ослабьте фильтры или измените цель."
            )

        self.stage = AgentStage.REVIEW_RESULTS
        parts.append(stage_banner(self.stage))
        parts.append(f"Первичная выдача: {len(kept)} курсов.")

        self.stage = AgentStage.REFINE_QUERIES
        parts.append(stage_banner(self.stage))
        refinement = self.refine_skill.refine(goal_text, query_set.queries, kept)
        parts.append(f"Уточнение: {refinement.rationale}")

        self.stage = AgentStage.SEARCH_REFINED
        parts.append(stage_banner(self.stage))
        kept2, rej2 = self.search_skill.run_searches(
            refinement.queries,
            self.session_id,
            self.filters,
            per_query_limit=n,
            stage="refined",
        )
        self.rejected_det.extend(rej2)
        merged = {c["id"]: c for c in kept}
        for c in kept2:
            merged[c["id"]] = c
        self.courses = list(merged.values())

        self.stage = AgentStage.FRESHNESS_CHECK
        parts.append(stage_banner(self.stage))
        freshness = self.rank_skill.build_freshness_notes(goal_text, self.courses)
        parts.append("Актуальность:\n" + freshness)

        self.stage = AgentStage.RANK
        parts.append(stage_banner(self.stage))
        self.ranking = self.rank_skill.rank(
            goal_text,
            self.filters.model_dump(exclude_none=True),
            self.courses,
            freshness,
            self.rejected_det,
        )

        self.stage = AgentStage.PRESENT
        parts.append(stage_banner(self.stage))
        parts.append(self._format_ranking(self.ranking))
        return "\n\n".join(parts)

    def _format_ranking(self, ranking: RankingResult) -> str:
        lines = ["## Подборка курсов", ""]
        if not ranking.ranked:
            lines.append(ranking.summary)
            return "\n".join(lines)

        for item in sorted(ranking.ranked, key=lambda x: x.rank):
            url = ""
            for c in self.courses:
                if c["id"] == item.course_id:
                    url = c.get("canonical_url", "")
                    break
            lines.append(f"{item.rank}. **{item.title}** (id={item.course_id})")
            if url:
                lines.append(f"   {url}")
            for ev in item.evidence:
                lines.append(f"   - `{ev.field}`: {ev.excerpt}")
            if item.freshness_note:
                lines.append(f"   - актуальность: {item.freshness_note}")

        lines.extend(["", "## Почему такое ранжирование", "", ranking.summary])

        if ranking.rejected:
            lines.extend(["", "## Отсеянные курсы", ""])
            for rej in ranking.rejected[:8]:
                lines.append(f"- {rej.title} (id={rej.course_id}): {rej.reason}")
                for ev in rej.evidence:
                    lines.append(f"  - `{ev.field}`: {ev.excerpt}")

        if self.rejected_det:
            lines.extend(["", "## Отсеянные фильтрами", ""])
            for c in self.rejected_det[:8]:
                lines.append(
                    f"- {c.get('title')} (id={c.get('id')}): {c.get('_reject_reason')}"
                )

        lines.extend([
            "",
            "Можно: переранжировать приоритеты, запросить «ещё поиск», "
            "задать вопрос по id курса, «запись на курс N».",
        ])
        return "\n".join(lines)

    def _handle_follow_up(self, user_text: str) -> str:
        lowered = user_text.lower().strip()
        self.stage = AgentStage.FOLLOW_UP

        if "ещё поиск" in lowered or "еще поиск" in lowered or "search more" in lowered:
            extra = self.search_skill.generate_queries(
                self.goal.raw_text if self.goal else "",
                self.filters,
                self.prefs_snapshot(),
                count=3,
            )
            kept, rej = self.search_skill.run_searches(
                extra.queries,
                self.session_id,
                self.filters,
                per_query_limit=5,
                stage="follow_up",
            )
            self.rejected_det.extend(rej)
            for c in kept:
                if c["id"] not in {x["id"] for x in self.courses}:
                    self.courses.append(c)
            self.ranking = self.rank_skill.rank(
                self.goal.raw_text if self.goal else "",
                self.filters.model_dump(exclude_none=True),
                self.courses,
                "",
                self.rejected_det,
            )
            return stage_banner(AgentStage.RANK) + "\n\n" + self._format_ranking(self.ranking)

        if "переранж" in lowered or "приоритет" in lowered:
            self.prefs_db.add_session_note(f"priority: {user_text[:200]}")
            self.ranking = self.rank_skill.rank(
                (self.goal.raw_text if self.goal else "") + f"\nUser priority: {user_text}",
                self.filters.model_dump(exclude_none=True),
                self.courses,
                "",
                self.rejected_det,
            )
            return stage_banner(AgentStage.RANK) + "\n\n" + self._format_ranking(self.ranking)

        if lowered.startswith("запись") or "enroll" in lowered:
            course_id = self._extract_course_id(user_text)
            if course_id is None:
                return "Укажите id курса: «запись на курс 12345»."
            course = next((c for c in self.courses if c["id"] == course_id), None)
            if not course:
                return f"Курс id={course_id} отсутствует в текущей выдаче."
            url = course.get("canonical_url") or f"https://stepik.org/course/{course_id}"
            self.pending_enroll = EnrollmentRequest(course_id=course_id, course_url=url)
            self.stage = AgentStage.ENROLL_CONFIRM
            return self.enroll_skill.confirmation_message(
                course_id, course.get("title", ""), url
            )

        if self.courses and self.ranking:
            answer = self.llm.complete_text(
                "Answer about Stepik courses using only provided cards. No hallucination.",
                f"Question: {user_text}\nCourses: {self.courses[:5]}",
            )
            return stage_banner(AgentStage.FOLLOW_UP) + "\n\n" + answer

        return "Нет активной выдачи. Начните с описания цели обучения."

    def _extract_course_id(self, text: str) -> int | None:
        tokens = text.replace(",", " ").split()
        for token in reversed(tokens):
            if token.isdigit():
                return int(token)
        return None
