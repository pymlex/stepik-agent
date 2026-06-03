"""Non-Gradio pipeline demo: goal -> filters -> search -> rank."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import bootstrap_path

bootstrap_path.setup()

from stepik_agent.agents.orchestrator import AgentOrchestrator
from stepik_agent.config import load_settings
from stepik_agent.logging_setup import setup_logging
from models.schemas import AgentStage


def main() -> None:
    settings = load_settings()
    settings.mock_llm = os.environ.get("STEPIK_AGENT_MOCK_LLM", "0") == "1"
    setup_logging(settings.log_dir)
    agent = AgentOrchestrator(settings)
    agent.bootstrap_preferences()

    goal = os.environ.get("DEMO_GOAL", "хочу изучить Python для анализа данных")
    form = os.environ.get(
        "DEMO_FORM",
        "ru\nда\nпропустить\nпропустить\nпропустить",
    )

    print(agent.handle_message(goal))
    print("---")
    print(agent.handle_message(form))


if __name__ == "__main__":
    main()
