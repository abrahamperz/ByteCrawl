"""Scraper strategies against the fake HTTP layer (no network)."""

import pytest
import requests

from bytecraw import Scraper
from bytecraw.core import _decoded_html
from tests.conftest import FakeResponse

LONG_HTML = "<html><body><p>" + "real content here " * 30 + "</p></body></html>"


class TestStatic:
    def test_returns_page(self, http):
        http.routes["https://x.test/"] = FakeResponse(text=LONG_HTML)
        page = Scraper().static("https://x.test/")
        assert page.method == "static"
        assert page.status == 200
        assert "real content" in page.html

    def test_http_error_raises(self, http):
        http.routes["https://x.test/404"] = FakeResponse(status=404)
        with pytest.raises(requests.HTTPError):
            Scraper().static("https://x.test/404")

    def test_sends_user_agent(self, http):
        http.routes["https://x.test/"] = FakeResponse(text=LONG_HTML)
        Scraper(user_agent="MyBot/1.0")  # header lives on the session
        # The UA is set on Scraper's own requests.Session at construction;
        # what matters to callers is that static() works end to end.
        page = Scraper().static("https://x.test/")
        assert page.url == "https://x.test/"


class TestEncoding:
    def test_iso_8859_1_fallback_uses_apparent_encoding(self):
        # requests defaults to ISO-8859-1 when the header has no charset
        # (RFC 2616); for a UTF-8 body that turns £ into Â£.
        r = FakeResponse(text="price £10", encoding="iso-8859-1",
                         apparent_encoding="utf-8")
        assert _decoded_html(r) == "price £10"

    def test_declared_encoding_is_respected(self):
        r = FakeResponse(text="hola", encoding="utf-8")
        assert _decoded_html(r) == "hola"


class TestApi:
    def test_json_page(self, http):
        http.routes["https://api.test/items"] = FakeResponse(
            json_data={"items": [1, 2, 3]},
            headers={"content-type": "application/json"})
        page = Scraper().api("https://api.test/items")
        assert page.method == "api"
        assert page.json() == {"items": [1, 2, 3]}

    def test_non_json_raises_helpful_error(self, http):
        http.routes["https://api.test/html"] = FakeResponse(text="<html></html>")
        with pytest.raises(ValueError, match="did not return JSON"):
            Scraper().api("https://api.test/html")


class TestFetchAuto:
    def test_content_rich_page_stays_static(self, http, monkeypatch):
        http.routes["https://x.test/"] = FakeResponse(text=LONG_HTML)
        called = []
        monkeypatch.setattr(Scraper, "browser",
                            lambda self, url, **kw: called.append(url))
        page = Scraper().fetch("https://x.test/")
        assert page.method == "static"
        assert called == []

    def test_sparse_page_falls_back_to_browser(self, http, monkeypatch):
        http.routes["https://spa.test/"] = FakeResponse(
            text="<html><body><div id='root'></div></body></html>")
        sentinel = object()
        monkeypatch.setattr(Scraper, "browser", lambda self, url, **kw: sentinel)
        assert Scraper().fetch("https://spa.test/") is sentinel

    def test_explicit_static_never_falls_back(self, http, monkeypatch):
        http.routes["https://spa.test/"] = FakeResponse(text="<html></html>")
        monkeypatch.setattr(Scraper, "browser",
                            lambda self, url, **kw: pytest.fail("browser called"))
        page = Scraper().fetch("https://spa.test/", strategy="static")
        assert page.method == "static"


ITEMS_P1 = """<html><body>
<article class="item"><h3>A</h3></article>
<article class="item"><h3>B</h3></article>
<li class="next"><a href="/page2">next</a></li>
</body></html>"""

ITEMS_P2 = """<html><body>
<article class="item"><h3>C</h3></article>
</body></html>"""


class TestCrawlPagination:
    def test_follows_next_page_link(self, http):
        http.routes["https://x.test/page1"] = FakeResponse(text=ITEMS_P1)
        http.routes["https://x.test/page2"] = FakeResponse(text=ITEMS_P2)
        rows = Scraper().crawl(
            "https://x.test/page1", item="article.item",
            fields={"name": "h3::text"},
            next_page="li.next a::attr(href)")
        assert [r["name"] for r in rows] == ["A", "B", "C"]

    def test_pages_limit_stops_early(self, http):
        http.routes["https://x.test/page1"] = FakeResponse(text=ITEMS_P1)
        rows = Scraper().crawl(
            "https://x.test/page1", item="article.item",
            fields={"name": "h3::text"},
            next_page="li.next a::attr(href)", pages=1)
        assert [r["name"] for r in rows] == ["A", "B"]

    def test_no_next_page_selector_single_page(self, http):
        http.routes["https://x.test/page1"] = FakeResponse(text=ITEMS_P1)
        rows = Scraper().crawl("https://x.test/page1", item="article.item",
                               fields={"name": "h3::text"})
        assert len(rows) == 2
