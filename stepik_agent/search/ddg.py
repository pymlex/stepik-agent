from duckduckgo_search import DDGS


def ddg_search(query: str, max_results: int = 3) -> list[dict]:
    with DDGS() as ddgs:
        return list(ddgs.text(query, max_results=max_results))
