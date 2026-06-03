from models.schemas import DeterministicFilters
from stepik_agent.stepik.filters import parse_workload_hours


MISSING_FIELD_SCORE = 0.35
SOFT_MISMATCH_SCORE = 0.25

DEFAULT_WEIGHTS = {
    "relevance_to_goal": 0.32,
    "freshness_2026": 0.14,
    "language_fit": 0.12,
    "price_fit": 0.10,
    "workload_fit": 0.10,
    "rating_quality": 0.08,
    "learners_fit": 0.08,
    "popularity": 0.06,
}


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _language_score(course: dict, filters: DeterministicFilters) -> tuple[float, str]:
    if not filters.language:
        return MISSING_FIELD_SCORE, "язык не задан пользователем"
    lang = course.get("language")
    if lang == filters.language:
        return 1.0, f"язык {lang} совпадает"
    return SOFT_MISMATCH_SCORE, f"язык {lang}, ожидался {filters.language}"


def _price_score(course: dict, filters: DeterministicFilters) -> tuple[float, str]:
    if filters.is_paid is None:
        return MISSING_FIELD_SCORE, "платность не задана"
    paid = course.get("is_paid")
    if paid == filters.is_paid:
        label = "платный" if paid else "бесплатный"
        return 1.0, f"курс {label}"
    if filters.is_paid is False and paid:
        return 0.22, "нужны бесплатные, курс платный"
    return 0.55, "платность отличается от предпочтения"


def _learners_score(course: dict, filters: DeterministicFilters) -> tuple[float, str]:
    if filters.min_learners is None:
        return MISSING_FIELD_SCORE, "порог learners_count не задан"
    count = course.get("learners_count") or 0
    if count >= filters.min_learners:
        return 1.0, f"learners_count={count}"
    ratio = count / filters.min_learners if filters.min_learners else 0
    return _clamp(0.2 + 0.6 * ratio), f"learners_count={count} ниже порога {filters.min_learners}"


def _rating_score(course: dict, filters: DeterministicFilters) -> tuple[float, str]:
    rating = course.get("rating")
    if filters.min_rating is None:
        if rating is None:
            return MISSING_FIELD_SCORE, "rating в карточке отсутствует"
        return _clamp(float(rating) / 5.0), f"rating={rating}"
    if rating is None:
        return MISSING_FIELD_SCORE, "rating в карточке отсутствует"
    val = float(rating)
    if val >= filters.min_rating:
        return 1.0, f"rating={val}"
    gap = filters.min_rating - val
    return _clamp(0.3 - 0.15 * gap), f"rating={val} ниже порога {filters.min_rating}"


def _workload_score(course: dict, filters: DeterministicFilters) -> tuple[float, str]:
    hours = parse_workload_hours(course.get("workload"))
    if filters.max_workload_hours is None:
        if hours is None:
            return MISSING_FIELD_SCORE, "workload не указан"
        return _clamp(1.0 - hours / 20.0), f"workload≈{hours}ч"
    if hours is None:
        return MISSING_FIELD_SCORE, "workload не указан"
    if hours <= filters.max_workload_hours:
        return 1.0, f"workload≈{hours}ч"
    over = hours - filters.max_workload_hours
    return _clamp(0.35 - 0.08 * over), f"workload≈{hours}ч выше лимита {filters.max_workload_hours}"


def _popularity_score(course: dict) -> tuple[float, str]:
    count = course.get("learners_count")
    if count is None:
        return MISSING_FIELD_SCORE, "learners_count отсутствует"
    return _clamp(float(count) / 5000.0), f"learners_count={count}"


def _relevance_score(course: dict, goal_text: str) -> tuple[float, str]:
    text = " ".join(
        str(course.get(k, ""))
        for k in ("title", "summary", "description", "requirements")
    ).lower()
    tokens = [t for t in goal_text.lower().split() if len(t) > 3]
    if not tokens:
        return MISSING_FIELD_SCORE, "цель слишком короткая для overlap"
    hits = sum(1 for t in tokens if t in text)
    score = _clamp(hits / max(len(tokens), 1))
    return score, f"совпадение ключевых слов {hits}/{len(tokens)}"


def _freshness_score(freshness_note: str | None) -> tuple[float, str]:
    if not freshness_note:
        return MISSING_FIELD_SCORE, "проверка актуальности не выполнялась"
    low = freshness_note.lower()
    if "no web results" in low:
        return 0.3, "внешних подтверждений актуальности нет"
    if "2026" in low or "2025" in low or "2024" in low:
        return 0.85, "есть свежие упоминания в веб-поиске"
    return 0.55, "косвенные данные по актуальности"


def score_course(
    course: dict,
    goal_text: str,
    filters: DeterministicFilters,
    freshness_note: str | None = None,
    weights: dict[str, float] | None = None,
) -> dict:
    w = weights or DEFAULT_WEIGHTS
    dims: dict[str, tuple[float, str]] = {
        "relevance_to_goal": _relevance_score(course, goal_text),
        "freshness_2026": _freshness_score(freshness_note),
        "language_fit": _language_score(course, filters),
        "price_fit": _price_score(course, filters),
        "workload_fit": _workload_score(course, filters),
        "rating_quality": _rating_score(course, filters),
        "learners_fit": _learners_score(course, filters),
        "popularity": _popularity_score(course),
    }
    total = 0.0
    weight_sum = 0.0
    breakdown = []
    for name, weight in w.items():
        score, note = dims.get(name, (MISSING_FIELD_SCORE, "критерий не вычислен"))
        total += weight * score
        weight_sum += weight
        breakdown.append(
            {"name": name, "weight": weight, "score": round(score, 3), "note": note}
        )
    final = total / weight_sum if weight_sum else 0.0
    return {
        "_weighted_score": round(final, 4),
        "_score_breakdown": breakdown,
        "_weights": w,
    }


def rank_courses_soft(
    courses: list[dict],
    goal_text: str,
    filters: DeterministicFilters,
    freshness_global: str = "",
) -> list[dict]:
    enriched = []
    for course in courses:
        scored = dict(course)
        scored.update(
            score_course(course, goal_text, filters, freshness_global, DEFAULT_WEIGHTS)
        )
        enriched.append(scored)
    enriched.sort(key=lambda c: c["_weighted_score"], reverse=True)
    return enriched
