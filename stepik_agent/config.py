import os
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


ROOT = Path(__file__).resolve().parents[1]


class UserPreferences(BaseModel):
    user_id: str = "default"
    display_name: str = "Learner"
    default_result_count: int = Field(default=5, ge=1, le=20)
    message_tone: str = "supportive"
    preferred_language: str | None = None
    max_workload_hours_per_week: float | None = None
    min_rating: float | None = None
    exclude_paid: bool = False
    topics_history: list[str] = Field(default_factory=list)


class AppSettings(BaseModel):
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.zveno.ai/v1"
    openai_model: str = "openai/gpt-oss-120b"
    stepik_token: str | None = None
    mock_llm: bool = False
    log_dir: Path = ROOT / "logs"
    data_dir: Path = ROOT / "data"
    preferences_path: Path = ROOT / "config" / "user_preferences.yaml"


def load_dotenv_file() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def load_api_key() -> str | None:
    key = os.environ.get("OPENAI_API_KEY") or os.environ.get("ZVENOAI_API_KEY")
    return key.strip() if key else None


def load_settings() -> AppSettings:
    load_dotenv_file()
    return AppSettings(
        openai_api_key=load_api_key(),
        openai_base_url=os.environ.get("OPENAI_BASE_URL", "https://api.zveno.ai/v1"),
        openai_model=os.environ.get("OPENAI_MODEL", "openai/gpt-oss-120b"),
        stepik_token=os.environ.get("STEPIK_API_TOKEN"),
        mock_llm=os.environ.get("STEPIK_AGENT_MOCK_LLM", "0") == "1",
        log_dir=Path(os.environ.get("STEPIK_AGENT_LOG_DIR", str(ROOT / "logs"))),
        data_dir=Path(os.environ.get("STEPIK_AGENT_DATA_DIR", str(ROOT / "data"))),
    )


def load_user_preferences(path: Path | None = None) -> UserPreferences:
    settings = load_settings()
    prefs_path = path or settings.preferences_path
    raw = yaml.safe_load(prefs_path.read_text(encoding="utf-8"))
    return UserPreferences.model_validate(raw)
