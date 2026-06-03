"""Query agent.log and search_log SQLite for audit."""

import argparse
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from stepik_agent.config import load_settings
from stepik_agent.db.search_log import SearchLogStore


def grep_agent_log(log_path: Path, pattern: str) -> list[str]:
    regex = re.compile(pattern, re.IGNORECASE)
    lines = log_path.read_text(encoding="utf-8").splitlines()
    return [ln for ln in lines if regex.search(ln)]


def main() -> None:
    parser = argparse.ArgumentParser(description="Search agent logs and DB")
    parser.add_argument(
        "--mode",
        choices=["queries", "log", "all"],
        default="queries",
    )
    parser.add_argument("--pattern", default="search query=")
    parser.add_argument("--session", default=None)
    args = parser.parse_args()

    settings = load_settings()
    log_path = settings.log_dir / "agent.log"

    if args.mode in {"queries", "all"}:
        store = SearchLogStore(settings.data_dir / "search_log.db")
        if args.session:
            rows = [
                {"query": q}
                for q in store.queries_for_session(args.session)
            ]
        else:
            rows = store.all_queries()
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        store.close()

    if args.mode in {"log", "all"}:
        if log_path.exists():
            hits = grep_agent_log(log_path, args.pattern)
            for line in hits:
                print(line)
        else:
            print(f"No log file at {log_path}")


if __name__ == "__main__":
    main()
