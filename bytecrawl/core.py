"""
ByteCraw library core.

Design: a Scraper object that knows how to fetch a page with the strategy you
want (or the best one automatically) and gives you back a Page object from
which you extract data with simple CSS selectors.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any

import requests
from bs4 import BeautifulSoup

DEFAULT_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

def _decoded_html(r: requests.Response) -> str:
    """Response text with the correct encoding.

    requests falls back to ISO-8859-1 when the header has no charset
    (RFC 2616), which breaks UTF-8 (£ -> Â£). When that happens, use
    content-based detection instead.
    """
    if r.encoding is None or r.encoding.lower() == "iso-8859-1":
        r.encoding = r.apparent_encoding
    return r.text


def _split_selector(spec: str) -> tuple[str, str, str | None]:
    """Returns (css_selector, operation, argument).

    operation: "text" (default) or "attr". argument: the attribute name.
    Examples:
      "p.price_color::text"   -> ("p.price_color", "text", None)
      "h3 a::attr(title)"     -> ("h3 a", "attr", "title")
      "div.quote"             -> ("div.quote", "text", None)
    """
    spec = spec.strip()
    if "::attr(" in spec:
        sel, rest = spec.split("::attr(", 1)
        return sel.strip(), "attr", rest.rstrip(")").strip()
    if spec.endswith("::text"):
        return spec[: -len("::text")].strip(), "text", None
    return spec, "text", None


def _value_from(node, op: str, arg: str | None) -> str | None:
    if node is None:
        return None
    if op == "attr":
        return node.get(arg)
    return node.get_text(strip=True)


@dataclass
class Page:
    """An already-downloaded page. Extract data from it."""

    url: str
    html: str = ""
    data: Any = None          # JSON if it came from an API
    method: str = "static"    # static | api | browser
    elapsed: float = 0.0
    status: int = 200
    _soup: BeautifulSoup | None = field(default=None, repr=False)

    @property
    def soup(self) -> BeautifulSoup:
        if self._soup is None:
            self._soup = BeautifulSoup(self.html or "", "lxml")
        return self._soup

    # --- extraction ---------------------------------------------------------
    def css(self, spec: str) -> str | None:
        """First match of a selector. Supports ::text and ::attr(name)."""
        sel, op, arg = _split_selector(spec)
        return _value_from(self.soup.select_one(sel), op, arg)

    def css_all(self, spec: str) -> list[str]:
        """All matches of a selector."""
        sel, op, arg = _split_selector(spec)
        return [v for n in self.soup.select(sel) if (v := _value_from(n, op, arg)) is not None]

    def extract(self, item: str, fields: dict[str, str]) -> list[dict]:
        """Extracts a list of records.

        item:   CSS selector delimiting each record (e.g. "article.product_pod").
        fields: dict {name: relative_selector}. The selector is applied INSIDE
                each item. If a field name ends in "[]" it returns a list of values.

        Example:
            page.extract("div.quote", {
                "quote": "span.text::text",
                "author": "small.author::text",
                "tags[]": "a.tag::text",
            })
        """
        records = []
        for node in self.soup.select(item):
            row = {}
            for name, spec in fields.items():
                sel, op, arg = _split_selector(spec)
                if name.endswith("[]"):
                    row[name[:-2]] = [
                        v for n in node.select(sel) if (v := _value_from(n, op, arg)) is not None
                    ]
                else:
                    row[name] = _value_from(node.select_one(sel), op, arg)
            records.append(row)
        return records

    def links(self) -> list[str]:
        return [a["href"] for a in self.soup.select("a[href]")]

    def json(self) -> Any:
        return self.data

    # --- LLM ----------------------------------------------------------------
    def markdown(self, main_only: bool = True) -> str:
        """Converts the page to clean Markdown (saves tokens for LLMs)."""
        if main_only:
            try:
                import trafilatura

                # include_links keeps link boundaries; without it adjacent
                # nodes glue together ("Visit siteSierra")
                md = trafilatura.extract(self.html, output_format="markdown", include_links=True)
                if md:
                    return _clean_markdown(md)
            except ImportError:
                pass
        try:
            from markdownify import markdownify
        except ImportError as e:
            raise ImportError(
                "Page.markdown() needs the 'llm' extra: pip install bytecraw[llm]"
            ) from e

        return _clean_markdown(markdownify(self.html, strip=["script", "style"]))

    def tokens(self, of: str | None = None) -> int:
        """Quick token estimate (~4 chars/token)."""
        text = of if of is not None else (self.html or "")
        return len(text) // 4


def _clean_markdown(md: str) -> str:
    """Removes conversion noise from marketing/SPA pages.

    Carousels and marquees duplicate their content in the DOM to loop, so the
    same block appears 2-3 times; animated counters leave their initial state.
    Dedupe repeated blocks and merge headings split across lines.
    """
    blocks = re.split(r"\n{2,}", md)
    seen: set[str] = set()
    cleaned: list[str] = []
    prev_key = ""
    for block in blocks:
        # Headings broken inside the block: "## Start scraping\n today"
        if block.lstrip().startswith("#") and "\n" in block:
            lines = block.split("\n")
            joined = [lines[0].rstrip()]
            for ln in lines[1:]:
                s = ln.strip()
                continues = s[:1].islower() or joined[-1].rstrip().endswith(("'", ","))
                if s and len(s) < 60 and continues:
                    joined[-1] = joined[-1] + " " + s
                else:
                    joined.append(ln)
            block = "\n".join(joined)
        key = " ".join(block.split())
        if not key:
            continue
        # Consecutive duplicates (looping carousels repeat short labels too)
        if key == prev_key:
            continue
        # Carousel/marquee duplicates: same long block seen before
        if len(key) >= 40 and key in seen:
            continue
        seen.add(key)
        prev_key = key
        cleaned.append(block.rstrip())

    # Text split by animated spans: "# Power AI agents with" + "clean web data"
    merged: list[str] = []
    for block in cleaned:
        prev = merged[-1] if merged else ""
        frag = block.strip()
        joinable = (
            prev
            and not prev.startswith(("```", "-", "*", ">", "|"))
            and "\n" not in prev
            and "\n" not in frag
            and not frag.startswith(("#", "```", "-", "*", ">", "|", "["))
        )
        visible_len = len(re.sub(r"\]\([^)]*\)", "]", frag))  # ignore link URLs
        lower_continuation = (
            visible_len < 70
            and frag[:1].islower()
            and not prev.rstrip().endswith((".", "!", "?", ":", "`"))
        )
        # Headings cut mid-phrase keep capitalization: "## Easily connect with your" + "AI agents"
        heading_continuation = (
            re.match(r"#{1,6} ", prev) is not None
            and len(frag) < 30
            and not frag.rstrip().endswith((".", "!", "?", ":"))
            and not prev.rstrip().endswith((".", "!", "?", ":", "`"))
        )
        if joinable and (lower_continuation or heading_continuation):
            merged[-1] = prev.rstrip() + " " + frag
        else:
            merged.append(block)

    # Inline-span joins lose the space: "at scale.It's also open source"
    out = []
    for block in merged:
        if "```" not in block:
            block = re.sub(r"(?<=[a-z])([.!?])(?=[A-Z\[])", r"\1 ", block)
        out.append(block)
    return "\n\n".join(out).strip()


class Session:
    """Reusable authenticated session (cookies + headers persist)."""

    def __init__(self, scraper: Scraper):
        self._s = requests.Session()
        self._s.headers.update({"User-Agent": scraper.user_agent})
        self._scraper = scraper

    def login(self, url: str, data: dict, csrf_field: str | None = None) -> Session:
        """Logs in. If csrf_field is given, reads it from the form first."""
        if csrf_field:
            r = self._s.get(url, timeout=self._scraper.timeout)
            r.raise_for_status()
            form = BeautifulSoup(_decoded_html(r), "lxml")
            token = form.select_one(f'input[name="{csrf_field}"]')
            if token:
                data = {**data, csrf_field: token.get("value", "")}
        r = self._s.post(url, data=data, timeout=self._scraper.timeout)
        r.raise_for_status()
        return self

    def bearer(self, token: str) -> Session:
        self._s.headers["Authorization"] = f"Bearer {token}"
        return self

    def fetch(self, url: str) -> Page:
        t0 = time.perf_counter()
        r = self._s.get(url, timeout=self._scraper.timeout)
        r.raise_for_status()
        return Page(url=url, html=_decoded_html(r), method="static",
                    elapsed=round(time.perf_counter() - t0, 3), status=r.status_code)


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
                "pip install bytecraw[browser] && playwright install chromium"
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
