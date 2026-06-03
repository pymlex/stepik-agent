import json

from models.schemas import (
    CourseEvidence,
    DimensionScore,
    FreshnessQuerySet,
    RankedCourse,
    RankingResult,
    RejectedCourse,
)
from stepik_agent.llm.client import LLMClient
from stepik_agent.llm import prompts
from stepik_agent.gradio_app.formatting import normalize_markdown
from stepik_agent.ranking.weighted_scorer import DEFAULT_WEIGHTS
from stepik_agent.search.ddg import ddg_search


class RankSkill:
    """Freshness via DDG, weighted scores, LLM long explanation."""

    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def build_freshness_notes(
        self,
        goal_text: str,
        courses: list[dict],
    ) -> str:
        snippets = []
        for course in courses[:3]:
            title = course.get("title", "")
            desc = (course.get("description") or course.get("summary") or "")[:200]
            snippets.append(f"{title}: {desc}")

        user = f"Goal: {goal_text}\nCourses:\n" + "\n".join(snippets)
        query_set = self.llm.complete_structured(
            prompts.FRESHNESS_SYSTEM, user, FreshnessQuerySet
        )

        notes = []
        for q in query_set.queries[:3]:
            hits = ddg_search(q, max_results=2)
            if not hits:
                notes.append(f"{q}: no web results")
                continue
            top = hits[0]
            notes.append(
                f"{q}: {top.get('title', '')} — {(top.get('body') or '')[:180]}"
            )
        return "\n".join(notes)

    def rank(
        self,
        goal_text: str,
        filters_dict: dict,
        courses: list[dict],
        freshness: str,
    ) -> RankingResult:
        if not courses:
            return RankingResult(
                ranked=[],
                rejected=[],
                summary="На Stepik не найдено курсов по запросам.",
                detailed_explanation="Поиск не вернул карточек курсов. Измените формулировку цели или ослабьте язык в форме.",
                weights=DEFAULT_WEIGHTS,
            )

        courses_json = json.dumps(courses, ensure_ascii=False, indent=2)[:14000]
        user = prompts.RANK_USER_TEMPLATE.format(
            goal=goal_text,
            filters=filters_dict,
            weights=json.dumps(DEFAULT_WEIGHTS, ensure_ascii=False),
            freshness=freshness or "(not run)",
            courses=courses_json,
        )
        base = self._build_from_weighted(courses, goal_text, freshness, None)

        if self.llm.settings.mock_llm:
            return base

        llm_result = self.llm.complete_structured(
            prompts.RANK_SYSTEM, user, RankingResult
        )
        if llm_result.summary.strip():
            base.summary = llm_result.summary
        if llm_result.detailed_explanation.strip():
            base.detailed_explanation = normalize_markdown(
                llm_result.detailed_explanation
            )
        elif llm_result.summary.strip():
            base.detailed_explanation = normalize_markdown(llm_result.summary)
        if llm_result.ranked:
            by_id = {item.course_id: item for item in llm_result.ranked}
            for item in base.ranked:
                extra = by_id.get(item.course_id)
                if extra and extra.evidence:
                    item.evidence = extra.evidence
        if llm_result.rejected:
            base.rejected = llm_result.rejected
        return base

    def _build_from_weighted(
        self,
        courses: list[dict],
        goal_text: str,
        freshness: str,
        llm_result: RankingResult | None = None,
    ) -> RankingResult:
        ranked = []
        for idx, course in enumerate(courses[:8], start=1):
            evidence = []
            for field in ("summary", "description", "requirements", "workload"):
                val = course.get(field)
                if val:
                    evidence.append(
                        CourseEvidence(field=field, excerpt=str(val)[:140])
                    )
            dims = [
                DimensionScore(
                    name=d["name"],
                    weight=d["weight"],
                    score=d["score"],
                    note=d["note"],
                )
                for d in course.get("_score_breakdown", [])
            ]
            ranked.append(
                RankedCourse(
                    course_id=course["id"],
                    title=course.get("title", ""),
                    rank=idx,
                    score=course.get("_weighted_score", 0.0),
                    evidence=evidence,
                    dimensions=dims,
                )
            )

        rejected = []
        for course in courses[8:12]:
            rejected.append(
                RejectedCourse(
                    course_id=course["id"],
                    title=course.get("title", ""),
                    reason=f"низкий взвешенный балл {course.get('_weighted_score', 0)}",
                    evidence=[],
                )
            )

        explanation = self._format_weighted_explanation(
            ranked, goal_text, freshness, llm_result
        )
        summary = (
            llm_result.summary
            if llm_result and llm_result.summary.strip()
            else f"Ранжирование по взвешенным критериям для цели: {goal_text[:100]}"
        )
        return RankingResult(
            ranked=ranked,
            rejected=rejected,
            summary=summary,
            detailed_explanation=explanation,
            weights=DEFAULT_WEIGHTS,
        )

    def _format_weighted_explanation(
        self,
        ranked: list[RankedCourse],
        goal_text: str,
        freshness: str,
        llm_result: RankingResult | None,
    ) -> str:
        lines = [
            "Итоговый балл курса — взвешенная сумма по критериям. "
            "Если пользователь не задал параметр в форме, критерию присвоен умеренно низкий балл 0.35, "
            "а не жёсткое отсечение. Несовпадения с хотелками снижают балл через веса.",
            "",
            "Веса критериев:",
        ]
        for name, weight in DEFAULT_WEIGHTS.items():
            lines.append(f"- {name}: {weight:.2f}")
        lines.extend(["", f"Цель обучения: {goal_text}", ""])
        if freshness:
            lines.extend(["", "**Актуальность 2026:**", "", freshness[:600], ""])
        return "\n\n".join(lines)
