"""Polite page fetching: robots.txt, rate limiting, optional headless browser."""
from __future__ import annotations

import time
import urllib.robotparser
from urllib.parse import urlparse

import httpx

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36 luxdeals-personal"


class Fetcher:
    def __init__(self, use_browser: bool = False, delay: float = 3.0, respect_robots: bool = True):
        self.delay = delay
        self.respect_robots = respect_robots
        self.use_browser = use_browser
        self._robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}
        self._last = 0.0
        self._client = httpx.Client(headers={"User-Agent": UA, "Accept-Language": "en"}, follow_redirects=True, timeout=30)
        self._pw = self._browser = None

    def allowed(self, url: str) -> bool:
        if not self.respect_robots:
            return True
        host = "{0.scheme}://{0.netloc}".format(urlparse(url))
        if host not in self._robots:
            rp = urllib.robotparser.RobotFileParser()
            try:
                r = self._client.get(f"{host}/robots.txt")
                rp.parse(r.text.splitlines()) if r.status_code == 200 else rp.parse([])
                self._robots[host] = rp
            except httpx.HTTPError:
                self._robots[host] = None  # unreachable robots.txt: let the page fetch fail on its own
        rp = self._robots[host]
        return True if rp is None else rp.can_fetch(UA, url)

    def _wait(self):
        gap = time.monotonic() - self._last
        if gap < self.delay:
            time.sleep(self.delay - gap)
        self._last = time.monotonic()

    def get(self, url: str) -> str | None:
        """Return page HTML, or None if disallowed / blocked."""
        if not self.allowed(url):
            print(f"  robots.txt disallows {url}")
            return None
        self._wait()
        if self.use_browser:
            return self._get_browser(url)
        r = self._client.get(url)
        if r.status_code != 200:
            print(f"  HTTP {r.status_code} for {url}")
            return None
        return r.text

    def _get_browser(self, url: str) -> str | None:
        if self._browser is None:
            from playwright.sync_api import sync_playwright  # optional dependency

            self._pw = sync_playwright().start()
            self._browser = self._pw.chromium.launch()
        page = self._browser.new_page(user_agent=UA)
        try:
            resp = page.goto(url, wait_until="networkidle", timeout=45000)
            if resp and resp.status >= 400:
                print(f"  HTTP {resp.status} for {url}")
                return None
            return page.content()
        finally:
            page.close()

    def close(self):
        self._client.close()
        if self._browser:
            self._browser.close()
            self._pw.stop()
