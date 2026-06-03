import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "stepik_config.json"


def load_config(course_url: str | None = None) -> dict:
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if course_url:
        data["course_url"] = course_url
    for key in ("email", "password", "course_url"):
        if not data.get(key):
            raise ValueError(f"Missing required config key: {key}")
    return data


def run_enrollment_browser(course_url: str) -> str:
    cfg = load_config(course_url)
    browser = None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()
            page.goto("https://stepik.org/login", wait_until="domcontentloaded")

            page.fill('input[type="email"], input[name="email"]', cfg["email"])
            page.fill('input[type="password"], input[name="password"]', cfg["password"])

            clicked = False
            for selector in [
                'button[type="submit"]',
                'button:has-text("Войти")',
                'button:has-text("Log in")',
            ]:
                try:
                    page.locator(selector).first.click(timeout=3000)
                    clicked = True
                    break
                except PlaywrightTimeoutError:
                    pass

            if not clicked:
                return "Кнопка входа не найдена. Войдите вручную в открытом окне."

            page.wait_for_load_state("networkidle")
            page.goto(cfg["course_url"], wait_until="domcontentloaded")
            page.wait_for_load_state("networkidle")

            for selector in [
                'button:has-text("Хочу пройти")',
                'button:has-text("Поступить на курс")',
                'a:has-text("Хочу пройти")',
                'a:has-text("Поступить на курс")',
            ]:
                try:
                    page.locator(selector).first.click(timeout=5000)
                    break
                except PlaywrightTimeoutError:
                    continue
            else:
                return "Кнопка записи не найдена. Завершите запись вручную в браузере."

            page.wait_for_load_state("networkidle")
            final_url = page.url
            return f"Запись выполнена или окно оставлено открытым. URL: {final_url}"
    except Exception as exc:
        return f"Браузер закрыт или прерван: {exc}"
    finally:
        if browser is not None:
            try:
                browser.close()
            except Exception:
                pass


def main() -> None:
    url = sys.argv[1] if len(sys.argv) > 1 else None
    cfg = load_config(url)
    print(run_enrollment_browser(cfg["course_url"]))


if __name__ == "__main__":
    main()
