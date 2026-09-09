"""The Scraper entry point.

Scraper picks a fetch strategy (static HTML, real browser, or JSON API) —
or decides automatically — and returns a Page. It also carries the
single-page-following `crawl()` helper and hands out authenticated Sessions.
"""

from __future__ import annotations

import time

import requests

from .page import Page
from .selectors import _split_selector, _value_from
from .session import Session
from .url import DEFAULT_UA, _decoded_html


class Scraper:
    """Entry point. Pick a strategy or let it decide on its own."""

    def __init__(self, user_agent: str = DEFAULT_UA, delay: float = 0.0, timeout: int = 15):
        self.user_agent = user_agent
        self.delay = delay
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": user_agent})

    # --- strategies -----------------------------------------------------------
    def static(self, url: str) -> Page:
        """Technique 1: static HTML with requests."""
        t0 = time.perf_counter()
        r = self._session.get(url, timeout=self.timeout)
        r.raise_for_status()
        self._wait()
        return Page(url=url, html=_decoded_html(r), method="static",
                    elapsed=round(time.perf_counter() - t0, 3), status=r.status_code)

    def api(self, url: str, params: dict | None = None) -> Page:
        """Technique 3: requests an API and stores the JSON."""
        t0 = time.perf_counter()
        r = self._session.get(url, params=params, timeout=self.timeout)
        r.raise_for_status()
        self._wait()
        try:
            data = r.json()
        except ValueError as e:
            ctype = r.headers.get("content-type", "unknown")
            raise ValueError(f"{url} did not return JSON (content-type: {ctype})") from e
        return Page(url=url, data=data, method="api",
                    elapsed=round(time.perf_counter() - t0, 3), status=r.status_code)

    def browser(self, url: str, wait: str | None = None, scroll: bool = False) -> Page:
        """Technique 2: real browser (Playwright) for JS-rendered sites."""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as e:
            raise ImportError(
                "Scraper.browser() needs the 'browser' extra: "
                "pip install bytecrawl[browser] && playwright install chromium"
            ) from e

        t0 = time.perf_counter()
        with sync_playwright() as p:
            nav = p.chromium.launch(headless=True)
            pg = nav.new_page()
            resp = pg.goto(url, wait_until="networkidle")
            if wait:
                pg.wait_for_selector(wait)
            if scroll:
                pg.mouse.wheel(0, 100000)
                pg.wait_for_timeout(500)
            html = pg.content()
            status = resp.status if resp else 0
            nav.close()
        self._wait()
        return Page(url=url, html=html, method="browser",
                    elapsed=round(time.perf_counter() - t0, 3), status=status)

    def fetch(self, url: str, strategy: str = "auto") -> Page:
        """Fetches the page. strategy: auto | static | browser.

        'auto' downloads statically and, if the page looks empty (typical of
        SPAs that render with JS), retries with a browser.
        """
        if strategy == "static":
            return self.static(url)
        if strategy == "browser":
            return self.browser(url)
        # auto
        page = self.static(url)
        text = page.soup.get_text(strip=True)
        if len(text) < 200:  # heuristic: almost no content -> probably JS
            return self.browser(url)
        return page

    # --- crawling -----------------------------------------------------------
    def crawl(
        self,
        start: str,
        item: str,
        fields: dict[str, str],
        next_page: str | None = None,
        pages: int | None = None,
        base: str | None = None,
    ) -> list[dict]:
        """Walks multiple pages following the next-page link and extracts 'fields'.

        start:     initial URL.
        item:      selector for each record.
        fields:    fields to extract (see Page.extract).
        next_page: selector for the next-page link (e.g. "li.next a::attr(href)").
        pages:     optional page limit.
        base:      prefix for relative URLs (otherwise inferred from the host).
        """
        from urllib.parse import urljoin

        url = start
        results: list[dict] = []
        n = 0
        while url:
            page = self.static(url)
            results.extend(page.extract(item, fields))
            n += 1
            if pages and n >= pages:
                break
            if not next_page:
                break
            sel, op, arg = _split_selector(next_page)
            node = page.soup.select_one(sel)
            op = op if op != "text" else "attr"
            href = _value_from(node, op, arg or "href") if node else None
            url = urljoin(base or url, href) if href else None
        return results

    # --- session --------------------------------------------------------------
    def session(self) -> Session:
        return Session(self)

    def _wait(self):
        if self.delay:
            time.sleep(self.delay)
