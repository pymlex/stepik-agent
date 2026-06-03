"""End-to-end pipeline: goal, form, search, rank. Exit 0 on success."""

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from stepik_agent.agents.orchestrator import AgentOrchestrator
from stepik_agent.config import load_settings
from stepik_agent.logging_setup import setup_logging


GOAL = os.environ.get(
    "E2E_GOAL",
    "Изучить Python для анализа данных: pandas, визуализация",
)
FORM = os.environ.get(
    "E2E_FORM",
    "ru\nда\nпропустить\n8\n4.0",
)


def main() -> None:
    settings = load_settings()
    if not settings.openai_api_key:
        print("E2E FAIL: OPENAI_API_KEY missing in .env")
        sys.exit(1)

    setup_logging(settings.log_dir)
    agent = AgentOrchestrator(settings)
    agent.bootstrap_preferences()

    print("=== E2E step 1: goal ===")
    out1 = agent.handle_message(GOAL)
    print(out1[:800])
    print()

    print("=== E2E step 2: deterministic form ===")
    out2 = agent.handle_message(FORM)
    print(out2[:4000])
    print()

    queries = agent.search_log.all_queries()
    print(f"=== E2E search_log events: {len(queries)} ===")

    ok_output = (
        "## Подборка курсов" in out2
        or "не найдено" in out2.lower()
        or "не найден" in out2.lower()
    )
    ok_queries = len(queries) > 0

    if ok_output and ok_queries:
        print("E2E PASS")
        sys.exit(0)

    print(f"E2E FAIL ok_output={ok_output} ok_queries={ok_queries}")
    sys.exit(1)


if __name__ == "__main__":
    main()
