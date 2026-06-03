from models.schemas import DeterministicFilters, DeterministicFormSchema, DeterministicFormField


FORM_SCHEMA = DeterministicFormSchema(
    fields=[
        DeterministicFormField(
            key="language",
            label="Язык курса (ru / en / de / …)",
            field_type="choice",
            options=["ru", "en", "de", "es", "fr"],
            required=False,
        ),
        DeterministicFormField(
            key="is_paid",
            label="Только бесплатные? (да / нет / пропустить)",
            field_type="choice",
            options=["да", "нет", "пропустить"],
            required=False,
        ),
        DeterministicFormField(
            key="min_learners",
            label="Минимум learners_count (число или пропустить)",
            field_type="number",
            required=False,
        ),
        DeterministicFormField(
            key="max_workload_hours",
            label="Максимум часов в неделю по workload (число или пропустить)",
            field_type="number",
            required=False,
        ),
        DeterministicFormField(
            key="min_rating",
            label="Минимальный rating (число или пропустить)",
            field_type="number",
            required=False,
        ),
    ]
)


def form_prompt_text() -> str:
    lines = [
        "Укажите параметры: по одной строке на поле, можно «пропустить».",
        "",
        "1) ru",
        "2) да — только бесплатные, нет — любые, пропустить — не фильтровать",
        "3) минимум learners_count",
        "4) максимум часов в неделю",
        "5) минимальный rating",
        "",
    ]
    for field in FORM_SCHEMA.fields:
        opts = f" ({', '.join(field.options)})" if field.options else ""
        lines.append(f"- {field.label}{opts}")
    return "\n".join(lines)


def parse_form_response(text: str) -> DeterministicFilters:
    """Parse user Q&A block into filters; empty means no constraint."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    values: dict[str, str] = {}
    keys = [f.key for f in FORM_SCHEMA.fields]
    for idx, line in enumerate(lines):
        if idx < len(keys):
            values[keys[idx]] = line

    return DeterministicFilters(
        language=_parse_language(values.get("language")),
        is_paid=_parse_paid(values.get("is_paid")),
        min_learners=_parse_int(values.get("min_learners")),
        max_workload_hours=_parse_float(values.get("max_workload_hours")),
        min_rating=_parse_float(values.get("min_rating")),
    )


def _parse_language(raw: str | None) -> str | None:
    if not raw or raw.lower() in {"пропустить", "skip", "-"}:
        return None
    return raw.strip().lower()[:8]


def _parse_paid(raw: str | None) -> bool | None:
    if not raw or raw.lower() in {"пропустить", "skip", "-"}:
        return None
    if raw.lower() in {"да", "yes", "true", "бесплатные", "free"}:
        return False
    if raw.lower() in {"нет", "no", "paid", "платные"}:
        return None
    return None


def _parse_int(raw: str | None) -> int | None:
    if not raw or raw.lower() in {"пропустить", "skip", "-"}:
        return None
    return int(float(raw.replace(",", ".")))


def _parse_float(raw: str | None) -> float | None:
    if not raw or raw.lower() in {"пропустить", "skip", "-"}:
        return None
    return float(raw.replace(",", "."))
