import requests
from pprint import pprint


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
]


def stepik_get(url, params=None, token=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    response = requests.get(url, params=params, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()


def extract_text_card(course):
    card = {}
    for field in TEXT_FIELDS:
        if field in course:
            card[field] = course.get(field)
    return card


def search_courses(query, limit=5, token=None):
    page = 1
    found = []

    while len(found) < limit:
        data = stepik_get(BASE_URL, params={"search": query, "page": page}, token=token)
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

    params = [("ids[]", course_id) for course_id in ids]
    full_data = stepik_get(BASE_URL, params=params, token=token)
    full_courses = full_data.get("courses", [])

    by_id = {course["id"]: course for course in full_courses}

    result = []
    for course in top_courses:
        full_course = by_id.get(course["id"], course)
        result.append(extract_text_card(full_course))

    return result


if __name__ == "__main__":
    query = "python"
    cards = search_courses(query, limit=5)
    pprint(cards, width=140, sort_dicts=False)