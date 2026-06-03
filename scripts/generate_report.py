"""Run E2E pipeline and save report for DELIVERABLE_RU."""

import io
import sys
from datetime import datetime, timezone
from pathlib import Path


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import bootstrap_path

bootstrap_path.setup()

from stepik_agent.agents.orchestrator import AgentOrchestrator
from stepik_agent.config import load_settings
from stepik_agent.logging_setup import setup_logging


GOAL = "Хочу изучить Python для анализа данных: pandas, визуализация, основы статистики"
FORM = "ru\nпропустить\nпропустить\nпропустить\nпропустить"


def main() -> None:
    settings = load_settings()
    setup_logging(settings.log_dir)
    agent = AgentOrchestrator(settings)
    agent.bootstrap_preferences()

    buffer = io.StringIO()
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    def writeln(text: str = "") -> None:
        line = text + "\n"
        buffer.write(line)
        sys.stdout.buffer.write(line.encode("utf-8", errors="replace"))

    writeln(f"# Прогон stepik-agent — {stamp}")
    writeln()
    writeln("## Вход: цель")
    writeln(GOAL)
    writeln()
    writeln("## Вход: форма")
    writeln(FORM.replace("\n", " | "))
    writeln()
    writeln("## Шаг 1 — ответ агента")
    writeln(agent.handle_message(GOAL))
    writeln()
    writeln("## Шаг 2 — поиск и ранжирование")
    out2 = agent.handle_message(FORM)
    writeln(out2)

    queries = agent.search_log.all_queries()
    writeln()
    writeln(f"## Метрики: событий в search_log = {len(queries)}")
    writeln(f"## Статус: E2E PASS" if len(queries) > 0 else "## Статус: E2E FAIL")

    artifacts = ROOT / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    report_path = artifacts / "report_run.txt"
    report_path.write_text(buffer.getvalue(), encoding="utf-8")
    writeln()
    writeln(f"Сохранено: {report_path}")


if __name__ == "__main__":
    main()
