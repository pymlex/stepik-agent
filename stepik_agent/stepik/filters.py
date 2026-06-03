from models.schemas import DeterministicFilters


def parse_workload_hours(workload: str | None) -> float | None:
    if not workload:
        return None
    digits = "".join(ch if ch.isdigit() or ch == "." else " " for ch in workload)
    parts = [p for p in digits.split() if p]
    if not parts:
        return None
    return float(parts[0])


def apply_deterministic_filters(
    courses: list[dict],
    filters: DeterministicFilters,
) -> tuple[list[dict], list[dict]]:
    """Split courses into kept and rejected with explicit reasons."""
    kept = []
    rejected = []

    for course in courses:
        reason = _rejection_reason(course, filters)
        if reason:
            rejected.append({**course, "_reject_reason": reason})
        else:
            kept.append(course)
    return kept, rejected


def _rejection_reason(course: dict, filters: DeterministicFilters) -> str | None:
    if filters.language and course.get("language") != filters.language:
        return f"language mismatch: {course.get('language')}"

    if filters.is_paid is not None and course.get("is_paid") != filters.is_paid:
        paid_label = "paid" if filters.is_paid else "free"
        return f"not {paid_label}"

    if filters.min_learners is not None:
        count = course.get("learners_count") or 0
        if count < filters.min_learners:
            return f"learners_count {count} < {filters.min_learners}"

    if filters.min_rating is not None:
        rating = course.get("rating")
        if rating is None or float(rating) < filters.min_rating:
            return f"rating {rating} < {filters.min_rating}"

    if filters.max_workload_hours is not None:
        hours = parse_workload_hours(course.get("workload"))
        if hours is not None and hours > filters.max_workload_hours:
            return f"workload {hours}h > {filters.max_workload_hours}h"

    return None
