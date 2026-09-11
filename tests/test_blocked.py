"""Bot-wall detection: a WAF block becomes a clear BlockedError, not a bare 403.

Covers the two things that matter: known walls (Cloudflare, DataDome, …) are
named in a human message, and ordinary errors (a plain 404, an unfingerprinted
403, a normal page served from behind Cloudflare) are left exactly as they were.
"""

from __future__ import annotations

import pytest
import requests

import bytecrawl
from bytecrawl import BlockedError, Scraper
from bytecrawl.scraping.url import _detect_bot_wall, _raise_for_status

from .conftest import FakeResponse


def _resp(status, headers=None, text="", url="https://blocked.test/page"):
    r = FakeResponse(status=status, headers=headers or {"content-type": "text/html"}, text=text)
    r.url = url
    return r


# --- detection: each vendor, by header and by body ---------------------------
@pytest.mark.parametrize(
    "headers, body, expected",
    [
        ({"server": "cloudflare", "cf-ray": "8a2b"}, "", "Cloudflare"),
        ({"cf-mitigated": "challenge"}, "", "Cloudflare"),
        ({}, "<title>Just a moment...</title>", "Cloudflare"),
        ({}, "Attention Required! | Cloudflare", "Cloudflare"),
        ({"x-datadome": "protected"}, "", "DataDome"),
        ({}, "please enable JS — datadome", "DataDome"),
        ({"x-px": "1"}, "", "PerimeterX / HUMAN"),
        ({}, "px-captcha challenge", "PerimeterX / HUMAN"),
        ({}, "Access Denied — AkamaiGHost", "Akamai"),
        ({"x-iinfo": "9-1"}, "", "Imperva Incapsula"),
    ],
)
def test_detects_named_walls(headers, body, expected):
    assert _detect_bot_wall(_resp(403, headers, body)) == expected


def test_ignores_walls_on_a_success_status():
    # A normal page served from behind Cloudflare must not look like a block.
    ok = _resp(200, {"server": "cloudflare", "cf-ray": "8a2b"}, "<html>real content</html>")
    assert _detect_bot_wall(ok) is None


def test_unfingerprinted_403_is_not_a_wall():
    assert _detect_bot_wall(_resp(403, {"server": "nginx"}, "Forbidden")) is None


def test_plain_access_denied_is_not_a_wall():
    # A credential/permission failure says "Access Denied" too — must NOT be
    # mislabelled as a bot wall without a real vendor signature.
    r = _resp(403, {"server": "Apache"}, "Access Denied. You lack permission.")
    assert _detect_bot_wall(r) is None


# --- _raise_for_status: what actually gets raised ----------------------------
def test_blocked_status_raises_blockederror_with_a_clear_message():
    r = _resp(403, {"server": "cloudflare", "cf-ray": "8a2b"}, "Just a moment...")
    with pytest.raises(BlockedError) as exc:
        _raise_for_status(r)
    msg = str(exc.value)
    assert "Cloudflare" in msg
    assert "HTTP 403" in msg
    assert "blocked.test" in msg  # host pulled from the response URL


def test_blockederror_carries_wall_and_status():
    # The frontend renders a structured notice from these, not a re-parsed string.
    r = _resp(429, {"x-datadome": "protected"}, "")
    err = _capture(r)
    assert err.wall == "DataDome"
    assert err.status == 429


def test_message_strips_www_prefix():
    r = _resp(403, {"cf-mitigated": "block"}, "", "https://www.example.com/x")
    with pytest.raises(BlockedError, match=r"example\.com"):
        _raise_for_status(r)
    assert "www." not in str(_capture(r))


def _capture(r):
    try:
        _raise_for_status(r)
    except BlockedError as e:
        return e
    return None


def test_blockederror_is_an_httperror():
    # Existing `except requests.HTTPError` handlers keep catching it.
    assert issubclass(BlockedError, requests.HTTPError)
    assert bytecrawl.BlockedError is BlockedError


def test_plain_404_stays_a_plain_httperror():
    r = _resp(404, {"server": "nginx"}, "Not Found")
    with pytest.raises(requests.HTTPError) as exc:
        _raise_for_status(r)
    assert not isinstance(exc.value, BlockedError)


def test_success_passes_through():
    _raise_for_status(_resp(200))  # does not raise


# --- through a crawl ---------------------------------------------------------
def test_crawl_records_the_wall_and_comes_back_empty(http):
    # A walled seed yields no pages, but the crawl remembers the wall so the
    # caller can say "blocked" instead of the misleading "nothing relevant".
    from bytecrawl.crawl import BFS

    url = "https://walled.test/"
    http.routes[url] = _resp(403, {"server": "cloudflare", "cf-ray": "1"}, "Just a moment...", url)
    result = BFS(query="anything").crawl(url, max_pages=5)
    assert result.pages == []
    assert isinstance(result.blocked, BlockedError)
    assert result.blocked.wall == "Cloudflare"


# --- through the public Scraper surface --------------------------------------
def test_scraper_static_surfaces_the_block(http):
    url = "https://walled.test/"
    http.routes[url] = _resp(403, {"server": "cloudflare", "cf-ray": "1"}, "Just a moment...", url)
    with pytest.raises(BlockedError, match="Cloudflare"):
        Scraper().static(url)


def test_scraper_static_still_raises_plain_404(http):
    url = "https://gone.test/"
    http.routes[url] = _resp(404, {"server": "nginx"}, "nope", url)
    with pytest.raises(requests.HTTPError) as exc:
        Scraper().static(url)
    assert not isinstance(exc.value, BlockedError)
