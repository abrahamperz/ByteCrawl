"""Live browser tests against quotes.toscrape.com/js (JS-only rendering).

These hit the real network and need Playwright + Chromium, so they are
excluded from the default run. Execute them with:

    pip install bytecrawl[browser] && playwright install chromium
    pytest -m live
"""

import pytest

from bytecrawl import Scraper

pytestmark = pytest.mark.live

playwright = pytest.importorskip("playwright", reason="browser extra not installed")

JS_URL = "https://quotes.toscrape.com/js/"


@pytest.fixture(scope="module")
def chromium_available():
    from playwright.sync_api import sync_playwright
    try:
        with sync_playwright() as p:
            p.chromium.launch(headless=True).close()
    except Exception:
        pytest.skip("Chromium not installed (run: playwright install chromium)")


def test_static_sees_nothing_on_js_site(chromium_available):
    page = Scraper().static(JS_URL)
    assert page.soup.select("div.quote") == []


def test_browser_renders_js_site(chromium_available):
    page = Scraper().browser(JS_URL)
    quotes = page.extract("div.quote", {"author": "small.author::text"})
    assert len(quotes) == 10
    assert page.method == "browser"
    assert page.status == 200  # real HTTP status, not the old fake default


def test_fetch_auto_falls_back_to_browser(chromium_available):
    page = Scraper().fetch(JS_URL)
    assert page.method == "browser"
    assert len(page.soup.select("div.quote")) == 10
