#!/usr/bin/env python3

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

CONFIG_PATH = Path(__file__).with_name("stepik_config.json")


def load_config():
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    for key in ("email", "password", "course_url"):
        if not data.get(key):
            raise ValueError(f"Missing required config key: {key}")
    return data


def main():
    cfg = load_config()

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
            raise RuntimeError("Login button not found")

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
            raise RuntimeError("Enrollment button not found")

        page.wait_for_load_state("networkidle")
        print(page.url)
        browser.close()


if __name__ == "__main__":
    main()