from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class AgentStage(str, Enum):
    WELCOME = "welcome"
    COLLECT_GOAL = "collect_goal"
    COLLECT_DETERMINISTIC = "collect_deterministic"
    GENERATE_QUERIES = "generate_queries"
    SEARCH_INITIAL = "search_initial"
    REVIEW_RESULTS = "review_results"
    REFINE_QUERIES = "refine_queries"
    SEARCH_REFINED = "search_refined"
    FRESHNESS_CHECK = "freshness_check"
    RANK = "rank"
    PRESENT = "present"
    FOLLOW_UP = "follow_up"
    ENROLL_CONFIRM = "enroll_confirm"


class DeterministicFilters(BaseModel):
    """Fields filled via explicit Q&A, not inferred from free text."""

    language: str | None = None
    is_paid: bool | None = None
    min_learners: int | None = None
    max_workload_hours: float | None = None
    min_rating: float | None = None


class LearningGoal(BaseModel):
    """Free-text learning intent from the user."""

    raw_text: str = Field(min_length=1)
    topics: list[str] = Field(default_factory=list)


class StepikSearchQuerySet(BaseModel):
    """LLM output: search strings only, no hallucinated filters."""

    queries: list[str] = Field(min_length=1, max_length=8)


class StepikSearchQueryRefinement(BaseModel):
    queries: list[str] = Field(min_length=1, max_length=5)
    rationale: str = Field(min_length=1)


class CourseEvidence(BaseModel):
    field: str
    excerpt: str


class RankedCourse(BaseModel):
    course_id: int
    title: str
    rank: int
    score: float = Field(ge=0.0, le=1.0)
    evidence: list[CourseEvidence] = Field(default_factory=list)
    freshness_note: str | None = None


class RejectedCourse(BaseModel):
    course_id: int
    title: str
    reason: str
    evidence: list[CourseEvidence] = Field(default_factory=list)


class RankingResult(BaseModel):
    ranked: list[RankedCourse] = Field(default_factory=list)
    rejected: list[RejectedCourse] = Field(default_factory=list)
    summary: str = Field(min_length=1)


class FreshnessQuerySet(BaseModel):
    queries: list[str] = Field(min_length=1, max_length=5)


class JudgeVerdict(BaseModel):
    passed: bool
    score: float = Field(ge=0.0, le=1.0)
    rationale: str


class ChatAction(str, Enum):
    CONTINUE = "continue"
    RERANK = "rerank"
    SEARCH_MORE = "search_more"
    ASK_COURSE = "ask_course"
    ENROLL = "enroll"


class SessionMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class DeterministicFormField(BaseModel):
    key: str
    label: str
    field_type: Literal["choice", "number", "bool"]
    options: list[str] | None = None
    required: bool = False


class DeterministicFormSchema(BaseModel):
    fields: list[DeterministicFormField]


class EnrollmentRequest(BaseModel):
    course_id: int
    course_url: str
    confirmed: bool = False
