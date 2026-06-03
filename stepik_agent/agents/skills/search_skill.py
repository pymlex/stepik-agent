import logging

from models.schemas import DeterministicFilters, StepikSearchQuerySet
from stepik_agent.db.search_log import SearchLogStore
from stepik_agent.llm.client import LLMClient
from stepik_agent.llm import prompts
from stepik_agent.stepik.api import search_courses
from stepik_agent.stepik.filters import apply_deterministic_filters


logger = logging.getLogger("stepik_agent")


class SearchSkill:
    """Multi-query Stepik search with merge and deterministic filter."""

    def __init__(
        self,
        llm: LLMClient,
        search_log: SearchLogStore,
        token: str | None,
    ) -> None:
        self.llm = llm
        self.search_log = search_log
        self.token = token

    def generate_queries(
        self,
        goal_text: str,
        filters: DeterministicFilters,
        prefs: dict,
        count: int = 5,
    ) -> StepikSearchQuerySet:
        user = prompts.QUERY_USER_TEMPLATE.format(
            goal=goal_text,
            prefs=prefs,
            filters=filters.model_dump(exclude_none=True),
        )
        result = self.llm.complete_structured(
            prompts.QUERY_SYSTEM, user, StepikSearchQuerySet
        )
        return StepikSearchQuerySet(queries=result.queries[:count])

    def run_searches(
        self,
        queries: list[str],
        session_id: str,
        filters: DeterministicFilters,
        per_query_limit: int,
        stage: str,
    ) -> tuple[list[dict], list[dict]]:
        merged: dict[int, dict] = {}
        for query in queries:
            batch = search_courses(
                query,
                limit=per_query_limit,
                token=self.token,
                language=filters.language,
                is_paid=filters.is_paid,
            )
            ids = [c["id"] for c in batch]
            self.search_log.log_search(session_id, query, ids, stage=stage)
            logger.info("search query=%s ids=%s", query, ids)
            for course in batch:
                merged[course["id"]] = course

        all_courses = list(merged.values())
        kept, rejected = apply_deterministic_filters(all_courses, filters)
        return kept, rejected
