import json
from pathlib import Path

from models.schemas import EnrollmentRequest


from stepik_agent.config import ROOT


CONFIG_PATH = ROOT / "stepik_config.json"


class EnrollSkill:
    """Course enrollment requires explicit user confirmation."""

    def confirmation_message(self, course_id: int, title: str, url: str) -> str:
        return (
            f"Запись на курс «{title}» (id={course_id}).\n"
            f"URL: {url}\n"
            "Ответьте «подтверждаю запись» для запуска браузера или «отмена»."
        )

    def parse_confirmation(self, text: str, pending: EnrollmentRequest) -> EnrollmentRequest:
        lowered = text.strip().lower()
        if lowered in {"подтверждаю запись", "confirm", "yes"}:
            return EnrollmentRequest(
                course_id=pending.course_id,
                course_url=pending.course_url,
                confirmed=True,
            )
        return EnrollmentRequest(
            course_id=pending.course_id,
            course_url=pending.course_url,
            confirmed=False,
        )

    def run_enrollment(self, request: EnrollmentRequest) -> str:
        if not request.confirmed:
            return "Запись отменена."

        from scripts.enroll_course import run_enrollment_browser

        return run_enrollment_browser(request.course_url)

    @staticmethod
    def load_config_template() -> dict:
        if not CONFIG_PATH.exists():
            return {
                "email": "",
                "password": "",
                "course_url": "https://stepik.org/course/0/promo",
            }
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
