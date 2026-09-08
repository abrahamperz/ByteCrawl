"""Shared fixtures: fake HTTP layer and an in-memory site for crawler tests.

No test in this suite touches the network. Scraper/Session tests monkeypatch
requests.Session.get/post (the single seam everything funnels through);
crawler tests monkeypatch Scraper.static (the crawler's natural contract).
"""

from __future__ import annotations

import pytest
import requests

from bytecrawl.core import Page, Scraper


class FakeResponse:
    """Minimal stand-in for requests.Response."""

    def __init__(self, text="", status=200, json_data=None, headers=None,
                 encoding="utf-8", apparent_encoding="utf-8"):
        self.status_code = status
        self.content = text.encode(apparent_encoding)
        self.encoding = encoding
        self.apparent_encoding = apparent_encoding
        self._json = json_data
        self.headers = headers or {"content-type": "text/html"}

    @property
    def text(self):
        enc = self.encoding or "utf-8"
        return self.content.decode(enc, errors="replace")

    def json(self):
        if self._json is None:
            raise ValueError("No JSON object could be decoded")
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} error")


class FakeHttp:
    """Routes GET/POST to canned responses and records every call."""

    def __init__(self):
        self.routes: dict[str, FakeResponse] = {}
        self.calls: list[tuple[str, str, dict]] = []


@pytest.fixture
def http(monkeypatch):
    fake = FakeHttp()

    def _get(self, url, **kw):
        fake.calls.append(("GET", url, kw))
        return fake.routes.get(url, FakeResponse(status=404))

    def _post(self, url, **kw):
        fake.calls.append(("POST", url, kw))
        return fake.routes.get("POST " + url, FakeResponse())

    monkeypatch.setattr(requests.Session, "get", _get)
    monkeypatch.setattr(requests.Session, "post", _post)
    return fake


# --- in-memory site for crawler strategy tests ------------------------------
# Two branches from the seed: /ml/* is relevant to "machine learning",
# /cats/* is not. One external link tests the same_domain filter.
SITE = {
    "https://s.test/": (
        "Home", "welcome to the machine learning intro site",
        [("/ml", "machine learning"), ("/cats", "cat pictures"),
         ("https://other.test/x", "external")],
    ),
    "https://s.test/ml": (
        "ML", "machine learning and deep learning models machine learning",
        [("/ml/deep", "deep learning"), ("/", "home")],
    ),
    "https://s.test/cats": (
        "Cats", "cats cats cats pictures of cats",
        [("/cats/more", "more cats")],
    ),
    "https://s.test/ml/deep": ("Deep", "deep neural networks training", []),
    "https://s.test/cats/more": ("More", "even more cats", []),
}


def render(url: str) -> str:
    title, text, links = SITE[url]
    anchors = "".join(f'<a href="{h}">{a}</a>' for h, a in links)
    return (f"<html><head><title>{title}</title></head>"
            f"<body><p>{text}</p>{anchors}</body></html>")


@pytest.fixture
def fake_site(monkeypatch):
    """Serves SITE through Scraper.static; returns the visit order."""
    visited: list[str] = []

    def fake_static(self, url):
        if url not in SITE:
            raise requests.HTTPError("404")
        visited.append(url)
        return Page(url=url, html=render(url), method="static", status=200)

    monkeypatch.setattr(Scraper, "static", fake_static)
    return visited
