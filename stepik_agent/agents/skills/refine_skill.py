from models.schemas import StepikSearchQueryRefinement
from stepik_agent.llm.client import LLMClient
from stepik_agent.llm import prompts


class RefineSkill:
    """After initial results, propose tighter Stepik queries."""

    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def refine(
        self,
        goal_text: str,
        initial_queries: list[str],
        courses: list[dict],
        max_samples: int = 5,
    ) -> StepikSearchQueryRefinement:
        samples = []
        for course in courses[:max_samples]:
            title = course.get("title", "")
            summary = (course.get("summary") or "")[:300]
            samples.append(f"- {title}: {summary}")

        user = prompts.REFINE_USER_TEMPLATE.format(
            goal=goal_text,
            queries=", ".join(initial_queries),
            samples="\n".join(samples) or "(empty)",
        )
        return self.llm.complete_structured(
            prompts.REFINE_SYSTEM, user, StepikSearchQueryRefinement
        )
