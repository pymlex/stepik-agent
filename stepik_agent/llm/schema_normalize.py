import json


def coerce_str(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, list):
        parts = [coerce_str(item) for item in value]
        return " ".join(p for p in parts if p)[:2000]
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)[:2000]
    return str(value).strip()[:2000]


def coerce_str_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            if isinstance(item, str):
                chunk = item.strip()
                if chunk:
                    out.append(chunk)
                continue
            if isinstance(item, dict):
                for key in ("query", "text", "q", "search", "value"):
                    if key in item:
                        chunk = coerce_str(item[key])
                        if chunk:
                            out.append(chunk)
                        break
        return out
    return []


def normalize_payload(data: dict, model_name: str) -> dict:
    if model_name == "StepikSearchQuerySet":
        queries = coerce_str_list(
            data.get("queries", data.get("search_queries", data.get("keywords")))
        )
        if not queries:
            queries = ["курс stepik"]
        return {"queries": queries[:8]}

    if model_name == "StepikSearchQueryRefinement":
        queries = coerce_str_list(
            data.get("queries", data.get("search_queries", data.get("refined_queries")))
        )
        rationale = coerce_str(
            data.get("rationale", data.get("analysis", data.get("reason", "")))
        )
        if not rationale:
            rationale = "Уточнение запросов по первичной выдаче Stepik."
        if not queries:
            queries = ["продуктовая аналитика", "аналитика продукта"]
        return {"queries": queries[:5], "rationale": rationale[:2000]}

    if model_name == "FreshnessQuerySet":
        queries = coerce_str_list(data.get("queries", data.get("search_queries")))
        if not queries:
            queries = ["актуальность технологий 2026"]
        return {"queries": queries[:5]}

    if model_name == "RankingResult":
        data.setdefault("ranked", data.get("ranked", []))
        data.setdefault("rejected", data.get("rejected", []))
        summary = coerce_str(data.get("summary", ""))
        detail = coerce_str(
            data.get("detailed_explanation", data.get("analysis", ""))
        )
        if not summary:
            summary = detail[:800] if detail else "Ранжирование по взвешенным критериям."
        if not detail:
            detail = summary
        weights = data.get("weights")
        if not isinstance(weights, dict):
            weights = {}
        return {
            "ranked": data.get("ranked", []),
            "rejected": data.get("rejected", []),
            "summary": summary,
            "detailed_explanation": detail,
            "weights": weights,
        }

    return data
