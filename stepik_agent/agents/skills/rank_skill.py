import json

from models.schemas import RankingResult, FreshnessQuerySet
from stepik_agent.llm.client import LLMClient
from stepik_agent.llm import prompts
from stepik_agent.search.ddg import ddg_search


class RankSkill:
    """Freshness via DDG, then structured ranking with evidence."""

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
        rejected_det: list[dict],
    ) -> RankingResult:
        if not courses:
            return RankingResult(
                ranked=[],
                rejected=[],
                summary="На Stepik не найдено курсов по заданным запросам и фильтрам.",
            )

        courses_json = json.dumps(courses, ensure_ascii=False, indent=2)[:12000]
        user = prompts.RANK_USER_TEMPLATE.format(
            goal=goal_text,
            filters=filters_dict,
            freshness=freshness or "(not run)",
            courses=courses_json,
        )
        result = self.llm.complete_structured(
            prompts.RANK_SYSTEM, user, RankingResult
        )

        if self.llm.settings.mock_llm or not result.ranked:
            det = self._deterministic_rank(courses, rejected_det, goal_text)
            if result.summary and result.summary.strip():
                det.summary = result.summary
            return det

        return result

    def _deterministic_rank(
        self,
        courses: list[dict],
        rejected_det: list[dict],
        goal_text: str,
    ) -> RankingResult:
        from models.schemas import RankedCourse, RejectedCourse, CourseEvidence

        ranked = []
        for idx, course in enumerate(courses[:5], start=1):
            evidence = []
            for field in ("summary", "requirements", "target_audience"):
                val = course.get(field)
                if val:
                    evidence.append(
                        CourseEvidence(field=field, excerpt=str(val)[:120])
                    )
                    break
            ranked.append(
                RankedCourse(
                    course_id=course["id"],
                    title=course.get("title", ""),
                    rank=idx,
                    score=max(0.5, 1.0 - 0.1 * idx),
                    evidence=evidence,
                )
            )

        rejected = []
        for course in rejected_det[:10]:
            rejected.append(
                RejectedCourse(
                    course_id=course["id"],
                    title=course.get("title", ""),
                    reason=course.get("_reject_reason", "filter"),
                    evidence=[
                        CourseEvidence(
                            field="language",
                            excerpt=str(course.get("language", "")),
                        )
                    ],
                )
            )

        return RankingResult(
            ranked=ranked,
            rejected=rejected,
            summary=f"Ранжирование по соответствию цели: {goal_text[:80]}",
        )
