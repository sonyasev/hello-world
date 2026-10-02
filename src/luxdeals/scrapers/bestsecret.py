"""BestSecret (members-only). Logs in with a headless browser and reuses the saved session.

Credentials come from the BESTSECRET_EMAIL / BESTSECRET_PASSWORD environment variables.
Kept deliberately slow (1 run/day, few pages) to stay close to normal member browsing.
UNVERIFIED: login form selectors and listing structure have not been checked against the live site.
"""
from __future__ import annotations

import os
import random
import time
from pathlib import Path

from .base import Scraper
from .fetch import UA

STATE = Path("data/bestsecret_state.json")  # session cookies; gitignored
LOGIN_URL = "https://www.bestsecret.com/login"


class BestSecretScraper(Scraper):
    _page = None

    @classmethod
    def has_credentials(cls) -> bool:
        return bool(os.environ.get("BESTSECRET_EMAIL") and os.environ.get("BESTSECRET_PASSWORD"))

    def _ensure_page(self):
        if self._page:
            return self._page
        from playwright.sync_api import sync_playwright

        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch()
        self._ctx = self._browser.new_context(
            user_agent=UA, storage_state=str(STATE) if STATE.exists() else None, locale="en-GB")
        self._page = self._ctx.new_page()
        return self._page

    def _login_if_needed(self, page):
        if "login" not in page.url:
            return
        page.fill('input[type="email"], input[name="username"], input[name="email"]', os.environ["BESTSECRET_EMAIL"])
        page.fill('input[type="password"]', os.environ["BESTSECRET_PASSWORD"])
        page.click('button[type="submit"]')
        page.wait_for_load_state("networkidle", timeout=45000)
        if "login" in page.url:
            raise RuntimeError("BestSecret login failed – check credentials or login selectors")
        STATE.parent.mkdir(parents=True, exist_ok=True)
        self._ctx.storage_state(path=str(STATE))

    def _get(self, url: str) -> str | None:
        page = self._ensure_page()
        time.sleep(random.uniform(4, 9))  # human-like pacing
        page.goto(url, wait_until="networkidle", timeout=45000)
        if "login" in page.url:
            self._login_if_needed(page)
            page.goto(url, wait_until="networkidle", timeout=45000)
        return page.content()

    def scrape(self):
        self.fetcher = _BrowserFetcher(self._get)  # route the generic scrape loop through the logged-in page
        return super().scrape()

    def close(self):
        if self._page:
            self._browser.close()
            self._pw.stop()
            self._page = None


class _BrowserFetcher:
    def __init__(self, get):
        self.get = get
