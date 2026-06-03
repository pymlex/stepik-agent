import requests


BASE_URL = "https://stepik.org/api/courses"

TEXT_FIELDS = [
    "id",
    "title",
    "title_en",
    "summary",
    "intro",
    "description",
    "requirements",
    "course_format",
    "target_audience",
    "certificate",
    "certificate_footer",
    "workload",
    "language",
    "slug",
    "canonical_url",
    "is_paid",
    "learners_count",
    "rating",
    "time_to_complete",
]


def stepik_get(url: str, params=None, token: str | None = None) -> dict:
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = requests.get(url, params=params, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()


def extract_text_card(course: dict) -> dict:
    card = {}
    for field in TEXT_FIELDS:
        if field in course:
            card[field] = course.get(field)
    return card


def search_courses(
    query: str,
    limit: int = 5,
    token: str | None = None,
    language: str | None = None,
    is_paid: bool | None = None,
) -> list[dict]:
    """Search Stepik API and return full text cards."""
    page = 1
    found = []
    params_base: dict = {"search": query}
    if language:
        params_base["language"] = language
    if is_paid is not None:
        params_base["is_paid"] = str(is_paid).lower()

    while len(found) < limit:
        params = {**params_base, "page": page}
        data = stepik_get(BASE_URL, params=params, token=token)
        courses = data.get("courses", [])
        if not courses:
            break
        found.extend(courses)
        if not data.get("meta", {}).get("has_next", False):
            break
        page += 1

    top_courses = found[:limit]
    ids = [course["id"] for course in top_courses]
    if not ids:
        return []

    id_params = [("ids[]", course_id) for course_id in ids]
    full_data = stepik_get(BASE_URL, params=id_params, token=token)
    full_courses = full_data.get("courses", [])
    by_id = {course["id"]: course for course in full_courses}

    result = []
    for course in top_courses:
        full_course = by_id.get(course["id"], course)
        result.append(extract_text_card(full_course))
    return result
