import sys
from duckduckgo_search import DDGS


DEFAULT_QUERY = "актуальны ли агентские системы в 2026"


def ddg_search(query: str, max_results: int = 3):
    with DDGS() as ddgs:
        return list(ddgs.text(query, max_results=max_results))


def main():
    query = " ".join(sys.argv[1:]).strip() if len(sys.argv) > 1 else DEFAULT_QUERY

    try:
        results = ddg_search(query, max_results=3)

        if not results:
            print("No results found.")
            return

        for i, r in enumerate(results, start=1):
            title = r.get("title", "").strip()
            href = r.get("href", "").strip()
            body = r.get("body", "").strip()

            print(f"{i}. {title}")
            print(f"   {href}")
            if body:
                print(f"   {body}")
            print()

    except Exception as e:
        print(f"Search error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()