import re

from models.schemas import RankingResult
from stepik_agent.ranking.weighted_scorer import DEFAULT_WEIGHTS


def normalize_markdown(text: str) -> str:
    text = text.replace("\r\n", "\n").strip()
    if not text:
        return ""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if len(paragraphs) <= 1 and len(text) > 180:
        sentences = re.split(r"(?<=[.!?])\s+", text)
        paragraphs = [s.strip() for s in sentences if len(s.strip()) > 20]
    return "\n\n".join(paragraphs)


def format_ranking_for_chat(
    ranking: RankingResult,
    courses: list[dict],
) -> str:
    if not ranking.ranked:
        blocks = [ranking.summary]
        if ranking.detailed_explanation:
            blocks.append(normalize_markdown(ranking.detailed_explanation))
        return "\n\n".join(blocks)

    weights = ranking.weights or DEFAULT_WEIGHTS
    sections: list[str] = [
        "## Подборка курсов",
        "",
        "Итоговый балл = $\\sum_i w_i \\cdot s_i$, каждый $s_i \\in [0,1]$.",
        "",
        "### Веса критериев",
        "",
    ]
    for name, weight in weights.items():
        sections.append(f"- **{name}**: {weight:.2f}")
    sections.append("")

    for item in sorted(ranking.ranked, key=lambda x: x.rank):
        url = ""
        for course in courses:
            if course["id"] == item.course_id:
                url = course.get("canonical_url", "")
                break

        sections.extend([
            "---",
            "",
            f"### {item.rank}. {item.title}",
            "",
            f"| Поле | Значение |",
            f"| --- | --- |",
            f"| id | {item.course_id} |",
            f"| Итоговый балл | **{item.score:.3f}** |",
        ])
        if url:
            sections.append(f"| Ссылка | {url} |")
        sections.extend(["", "#### Критерии", ""])
        for dim in item.dimensions:
            sections.append(
                f"- **{dim.name}** — вес {dim.weight:.2f}, "
                f"балл **{dim.score:.2f}**: {dim.note}"
            )
        if item.evidence:
            sections.extend(["", "#### Фрагменты карточки", ""])
            for ev in item.evidence:
                excerpt = ev.excerpt.replace("\n", " ").strip()
                sections.append(f"- `{ev.field}`: {excerpt}")
        sections.append("")

    sections.extend([
        "---",
        "",
        "## Краткое резюме",
        "",
        ranking.summary.strip(),
        "",
        "---",
        "",
        "## Подробное обоснование ранжирования",
        "",
        normalize_markdown(ranking.detailed_explanation.strip() or ranking.summary),
    ])

    if ranking.rejected:
        sections.extend(["", "---", "", "## Курсы с низким итоговым баллом", ""])
        for rej in ranking.rejected[:8]:
            sections.append(f"- **{rej.title}** (id={rej.course_id}): {rej.reason}")

    sections.extend([
        "",
        "---",
        "",
        "Дальше: переранжировать приоритеты, «ещё поиск», вопрос по id курса, «запись на курс N».",
    ])
    return "\n".join(sections)
