"""The two seed-failure states, reported identically on every surface.

A crawl swallows per-page failures and keeps going, so an empty result is
ambiguous: the seed was *walled* (a bot wall said no), *unreachable* (the page
never loaded — bad domain, refused connection, 404, two URLs pasted into one),
or read fine and simply matched nothing. The first two are failures the caller
should hear about plainly; the third is a real answer.

The point of this file is that the *same* two failures come back the *same*
way whether you go through the core primitives, the MCP tools, or the HTTP
API — so the tests are written as parallel triples: one core assertion, the MCP
tool, the /api method, against the same fake walled and dead seeds. If a
surface ever drifts (an empty crawl dressed up as "nothing relevant" again, a
raw traceback for a dead domain), exactly one of these fails.

The single seam is ``requests.Session.get`` (the ``http`` fixture): every
surface — ``Scraper.static``/``.api``/``.fetch``, and the crawlers on top of
them — funnels through it, so one routing table drives all three.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import requests

import bytecrawl
from bytecrawl import BlockedError, RateLimitError, UnreachableError
from bytecrawl.crawl import BFS
from bytecrawl.crawl.result import CrawlResult
from bytecrawl.crawler import compare

from .conftest import FakeResponse

# The Flask landing app lives under web/, outside the importable package tree.
# create_app() puts web/ and src/ on sys.path at import, but importing the
# module to *reach* create_app needs web/ on the path first.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "web"))


SEED = "https://seed.test/"


def _walled(url=SEED):
    """A Cloudflare wall on `url` — a real vendor signature, not a bare 403."""
    r = FakeResponse(
        status=403,
        headers={"server": "cloudflare", "cf-ray": "1a2b"},
        text="<title>Just a moment...</title>",
    )
    r.url = url
    return r


def _dead(url=SEED):
    """A seed that 404s: the page never loaded. Distinct from a wall."""
    r = FakeResponse(status=404, headers={"server": "nginx"}, text="Not Found")
    r.url = url
    return r


def _throttled(url=SEED, retry_after="30"):
    """A bare 429 with a Retry-After: reachable, just asking us to slow down.

    No WAF signature — a plain "Too Many Requests" from a live site, which must
    read as a rate limit, not a dead seed and not a bot wall.
    """
    r = FakeResponse(
        status=429,
        headers={"server": "nginx", "retry-after": retry_after},
        text="Too Many Requests",
    )
    r.url = url
    return r


def _walled_429(url=SEED):
    """A 429 that also carries a Cloudflare signature — a wall, not a rate limit.

    Locks the precedence: a bot wall answer is more specific than "slow down".
    """
    r = FakeResponse(
        status=429,
        headers={"server": "cloudflare", "cf-ray": "9z9z"},
        text="<title>Just a moment...</title>",
    )
    r.url = url
    return r


# --------------------------------------------------------------------------- #
# Core: the shared primitives every surface is built on.
# --------------------------------------------------------------------------- #
class TestCorePrimitives:
    def test_unreachable_is_true_when_every_fetch_failed(self):
        r = CrawlResult(strategy="bfs", stats={"requests": 3, "errors": 3})
        assert r.unreachable is True

    def test_unreachable_is_false_when_a_page_was_read(self):
        # One good read among failures is a real (if thin) answer, not a
        # dead seed.
        r = CrawlResult(strategy="bfs", stats={"requests": 3, "errors": 2})
        assert r.unreachable is False

    def test_unreachable_is_false_before_any_request(self):
        # An empty stats dict (nothing ran) must not read as "unreachable".
        assert CrawlResult(strategy="bfs", stats={}).unreachable is False

    def test_raise_for_seed_raises_unreachable_on_a_dead_seed(self):
        r = CrawlResult(strategy="bfs", stats={"requests": 1, "errors": 1})
        with pytest.raises(UnreachableError):
            r.raise_for_seed()

    def test_raise_for_seed_is_quiet_when_a_page_was_read(self):
        r = CrawlResult(
            strategy="bfs",
            pages=[{"url": SEED, "relevance": 0.0}],
            stats={"requests": 1, "errors": 0},
        )
        r.raise_for_seed()  # does not raise

    def test_block_wins_over_unreachable(self):
        # A walled seed sets both flags; "a bot wall refused you" is the more
        # specific, more actionable answer, so it takes precedence.
        wall = BlockedError("Cloudflare wall", wall="Cloudflare", status=403)
        r = CrawlResult(strategy="bfs", stats={"requests": 1, "errors": 1}, blocked=wall)
        with pytest.raises(BlockedError):
            r.raise_for_seed()

    def test_unreachable_error_is_a_requestexception(self):
        # `except requests.RequestException` handlers keep catching it.
        assert issubclass(UnreachableError, requests.RequestException)
        assert bytecrawl.UnreachableError is UnreachableError

    def test_rate_limit_error_is_an_httperror(self):
        # `except requests.HTTPError` keeps catching a 429, and it is exported
        # at the top level like the other two seed errors.
        assert issubclass(RateLimitError, requests.HTTPError)
        assert bytecrawl.RateLimitError is RateLimitError

    def test_raise_for_seed_raises_rate_limit_on_a_throttled_seed(self):
        throttle = RateLimitError(retry_after=30)
        r = CrawlResult(strategy="bfs", stats={"requests": 1, "errors": 1}, rate_limited=throttle)
        with pytest.raises(RateLimitError) as exc:
            r.raise_for_seed()
        assert exc.value.retry_after == 30

    def test_block_wins_over_rate_limit(self):
        # A seed can look both walled and throttled; the bot-wall answer is the
        # more specific, more actionable one, so it takes precedence.
        wall = BlockedError("Cloudflare wall", wall="Cloudflare", status=429)
        r = CrawlResult(
            strategy="bfs",
            stats={"requests": 1, "errors": 1},
            blocked=wall,
            rate_limited=RateLimitError(),
        )
        with pytest.raises(BlockedError):
            r.raise_for_seed()

    def test_rate_limit_wins_over_unreachable(self):
        # A throttled seed also has every fetch failing (so `unreachable` is
        # true), but "slow down and retry" is the more specific answer than
        # "couldn't open it".
        r = CrawlResult(
            strategy="bfs", stats={"requests": 1, "errors": 1}, rate_limited=RateLimitError()
        )
        assert r.unreachable is True  # every fetch failed…
        with pytest.raises(RateLimitError):  # …but the rate limit is reported
            r.raise_for_seed()

    def test_crawl_over_a_throttled_seed_reports_rate_limited(self, http):
        http.routes[SEED] = _throttled()
        result = BFS(query="anything").crawl(SEED, max_pages=5)
        assert result.pages == []
        assert result.rate_limited is not None
        assert result.rate_limited.retry_after == 30
        with pytest.raises(RateLimitError):
            result.raise_for_seed()

    def test_compare_surfaces_a_throttled_seed_once(self, http):
        http.routes[SEED] = _throttled()
        with pytest.raises(RateLimitError):
            compare(SEED, query="machine learning", max_pages=3, delay=0.0)

    def test_retry_after_parses_numeric_and_http_date(self):
        # Both RFC 7231 forms: a delta in seconds, and an absolute HTTP date
        # read as the delta from now (clamped at zero for a past date).
        from datetime import datetime, timedelta, timezone
        from email.utils import format_datetime

        from bytecrawl.scraping.url import _retry_after_seconds

        assert _retry_after_seconds("30") == 30
        assert _retry_after_seconds(None) is None
        assert _retry_after_seconds("soon") is None

        future = datetime.now(timezone.utc) + timedelta(seconds=120)
        secs = _retry_after_seconds(format_datetime(future))
        assert 110 <= secs <= 120  # ~120s out, allowing for clock drift

        past = datetime.now(timezone.utc) - timedelta(hours=1)
        assert _retry_after_seconds(format_datetime(past)) == 0

    def test_throttle_with_http_date_retry_after_is_reported(self, http):
        # A 429 whose Retry-After is an HTTP date still yields a positive wait.
        from datetime import datetime, timedelta, timezone
        from email.utils import format_datetime

        when = format_datetime(datetime.now(timezone.utc) + timedelta(seconds=60))
        http.routes[SEED] = _throttled(retry_after=when)
        result = BFS(query="anything").crawl(SEED, max_pages=5)
        assert result.rate_limited is not None
        assert 50 <= result.rate_limited.retry_after <= 60

    def test_crawl_over_a_dead_seed_reports_unreachable(self, http):
        http.routes[SEED] = _dead()
        result = BFS(query="anything").crawl(SEED, max_pages=5)
        assert result.pages == []
        assert result.unreachable is True
        with pytest.raises(UnreachableError):
            result.raise_for_seed()

    def test_compare_surfaces_a_dead_seed_once(self, http):
        # A dead seed fails all three legs identically; compare() re-raises it
        # once instead of burying three fake-empty "winners".
        http.routes[SEED] = _dead()
        with pytest.raises(UnreachableError):
            compare(SEED, query="machine learning", max_pages=3, delay=0.0)

    def test_compare_surfaces_a_walled_seed_once(self, http):
        http.routes[SEED] = _walled()
        with pytest.raises(BlockedError):
            compare(SEED, query="machine learning", max_pages=3, delay=0.0)


# --------------------------------------------------------------------------- #
# MCP tools: every tool raises the right seed error.
# --------------------------------------------------------------------------- #
# Guard on the exact submodule these tests import, not the top-level `mcp`
# package: on Python 3.9 (CI installs no mcp extra there) a shallow `mcp` can be
# importable without `mcp.server`, so importorskip("mcp") would pass and then the
# line below would ImportError at collection. Naming the submodule skips the
# module cleanly instead, the way the sibling MCP test files do.
pytest.importorskip("mcp.server.mcpserver.exceptions")
from mcp.server.mcpserver.exceptions import ToolError, UnexpectedToolError  # noqa: E402

from bytecrawl import mcp_server  # noqa: E402


@pytest.fixture(autouse=True)
def _no_delay():
    """The module-level scraper shouldn't sleep in tests."""
    mcp_server._scraper.delay = 0.0
    yield


# (tool callable, kwargs) for each of the six tools. Single-fetch tools and
# crawl tools reach the seed by different code paths (_open vs raise_for_seed);
# both must land on the same two exceptions.
MCP_TOOLS = [
    (mcp_server.fetch_markdown, {}),
    (mcp_server.extract, {}),
    (mcp_server.list_links, {}),
    (mcp_server.fetch_json_api, {}),
    (mcp_server.focused_crawl, {"query": "x", "max_pages": 3}),
    (mcp_server.compare_strategies, {"query": "x", "max_pages": 3}),
]


# A seed error escaping a tool is re-raised as a ToolError so the SDK returns
# it to the agent as an is_error result carrying our message (a bare requests
# exception would be a crash, masked to "Error executing tool <name>"). The
# typed seed error is preserved as __cause__, so the classification still holds.
@pytest.mark.parametrize("tool, kw", MCP_TOOLS)
def test_mcp_tool_reports_blocked_on_a_walled_seed(http, tool, kw):
    http.routes[SEED] = _walled()
    with pytest.raises(ToolError) as exc:
        tool(SEED, **kw)
    assert isinstance(exc.value.__cause__, BlockedError)


@pytest.mark.parametrize("tool, kw", MCP_TOOLS)
def test_mcp_tool_reports_unreachable_on_a_dead_seed(http, tool, kw):
    http.routes[SEED] = _dead()
    with pytest.raises(ToolError) as exc:
        tool(SEED, **kw)
    assert isinstance(exc.value.__cause__, UnreachableError)


@pytest.mark.parametrize("tool, kw", MCP_TOOLS)
def test_mcp_tool_reports_rate_limit_on_a_throttled_seed(http, tool, kw):
    http.routes[SEED] = _throttled()
    with pytest.raises(ToolError) as exc:
        tool(SEED, **kw)
    assert isinstance(exc.value.__cause__, RateLimitError)
    assert "retry after ~30s" in str(exc.value)  # the wait folds into the text


@pytest.mark.parametrize(
    "route, needle",
    [
        (_throttled(), "retry after ~30s"),
        (_walled(), "Blocked"),
        (_dead(), "Couldn't open"),
    ],
)
def test_mcp_client_receives_the_seed_message(http, route, needle):
    # The real SDK path: call_tool raises an *anticipated* ToolError (not the
    # UnexpectedToolError a crash would raise), whose str carries our message.
    # The RPC handler turns exactly this into an is_error result with the text
    # intact — whereas a crash is masked to a bare "Error executing tool <name>".
    import asyncio

    http.routes[SEED] = route
    with pytest.raises(ToolError) as exc:
        asyncio.run(mcp_server.server.call_tool("fetch_markdown", {"url": SEED}))
    assert not isinstance(exc.value, UnexpectedToolError)  # not a masked crash
    assert needle in str(exc.value)  # our message survives to the client


# --------------------------------------------------------------------------- #
# HTTP API: /api returns 403 {blocked} and 502 {unreachable} for every method.
# --------------------------------------------------------------------------- #
@pytest.fixture
def public_dns(monkeypatch):
    """Let the SSRF guard resolve the fake seed host, offline.

    ``assert_public_url`` calls ``socket.getaddrinfo`` and requires a globally
    routable address; a made-up ``.test`` host would fail to resolve (a real
    network call, which the suite forbids) and 400 before the fetch we're
    testing ever runs. Pin resolution to a fixed public IP so the guard passes
    and control reaches the walled/dead response.
    """
    import socket

    from bytecrawl import security

    def fake_getaddrinfo(host, *a, **kw):
        return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", 0))]

    monkeypatch.setattr(security.socket, "getaddrinfo", fake_getaddrinfo)


@pytest.fixture
def client(public_dns):
    from landing.app import create_app

    app = create_app()
    app.config.update(TESTING=True)
    return app.test_client()


# Every /api method that reaches the seed. `select` gives extract a real
# selector so it takes the fetch path rather than the (fetch-first) discovery
# path — both fetch, but this keeps the call unambiguous.
API_METHODS = [
    {"method": "markdown"},
    {"method": "text"},
    {"method": "html"},
    {"method": "links"},
    {"method": "extract", "select": "h3::text"},
    {"method": "json"},
    {"method": "crawl", "query": "x", "strategy": "bfs"},
    {"method": "compare", "query": "x"},
]


def _api_ids(params):
    return params["method"]


@pytest.mark.parametrize("params", API_METHODS, ids=_api_ids)
def test_api_reports_a_walled_seed_as_403_blocked(client, http, params):
    http.routes[SEED] = _walled()
    resp = client.get("/api", query_string={"url": SEED, **params})
    assert resp.status_code == 403
    body = resp.get_json()
    assert body["blocked"] is True
    assert body["wall"] == "Cloudflare"


@pytest.mark.parametrize("params", API_METHODS, ids=_api_ids)
def test_api_reports_a_dead_seed_as_502_unreachable(client, http, params):
    http.routes[SEED] = _dead()
    resp = client.get("/api", query_string={"url": SEED, **params})
    assert resp.status_code == 502
    body = resp.get_json()
    assert body["unreachable"] is True


@pytest.mark.parametrize("params", API_METHODS, ids=_api_ids)
def test_api_reports_a_throttled_seed_as_429_rate_limited(client, http, params):
    http.routes[SEED] = _throttled()
    resp = client.get("/api", query_string={"url": SEED, **params})
    assert resp.status_code == 429
    body = resp.get_json()
    assert body["rate_limited"] is True
    # The site's Retry-After is echoed in the body and the HTTP header so a
    # client can back off by the amount the site actually asked for.
    assert body["retry_after"] == 30
    assert resp.headers.get("Retry-After") == "30"


def test_api_walled_429_is_blocked_not_rate_limited(client, http):
    """A 429 that carries a WAF signature is a wall, not a rate limit.

    Precedence in one place: the bot-wall answer (403 {blocked}) is more
    specific than "slow down", so a walled 429 must not slip through as a 429
    {rate_limited}.
    """
    http.routes[SEED] = _walled_429()
    resp = client.get("/api", query_string={"url": SEED, "method": "markdown"})
    assert resp.status_code == 403
    body = resp.get_json()
    assert body["blocked"] is True
    assert body.get("rate_limited") is None
    assert body["wall"] == "Cloudflare"


def test_api_walled_and_mcp_walled_agree(client, http):
    """The contract in one place: the same walled seed, the tool and the
    endpoint, the same named wall — one raised (as a ToolError wrapping the
    typed BlockedError), one flagged in a 403 body."""
    http.routes[SEED] = _walled()

    with pytest.raises(ToolError) as exc:
        mcp_server.fetch_markdown(SEED)
    blocked = exc.value.__cause__
    assert isinstance(blocked, BlockedError)

    resp = client.get("/api", query_string={"url": SEED, "method": "markdown"})
    assert resp.status_code == 403
    assert resp.get_json()["wall"] == blocked.wall == "Cloudflare"


def test_auto_analyze_reports_a_dead_seed_as_unreachable(http):
    """The 'auto' surface (/analyze) classifies a dead seed like the rest.

    Markdown in the playground runs /analyze, not /api?method=markdown. That
    path used to swallow every fetch failure into a raw "Could not download the
    page: <traceback>" with no flag — so a mistyped domain showed red text there
    while /api?method=links showed the friendly card on the same page. Now it
    funnels the seed fetch through open_seed like every other surface, so it
    raises UnreachableError and the response carries the `unreachable` flag and
    the one shared wording the calm card renders from.
    """
    http.routes[SEED] = _dead()

    from landing.app import create_app

    app = create_app()
    app.config.update(TESTING=True)
    resp = app.test_client().post("/analyze", json={"url": SEED, "lang": "en"})

    body = resp.get_json()
    assert body["ok"] is False
    assert body["unreachable"] is True
    assert body["error"] == bytecrawl.UNREACHABLE_MESSAGE


def test_auto_analyze_reports_a_walled_seed_as_blocked(http):
    """And a bot wall on the 'auto' surface stays a named block, not unreachable."""
    http.routes[SEED] = _walled()

    from landing.app import create_app

    app = create_app()
    app.config.update(TESTING=True)
    resp = app.test_client().post("/analyze", json={"url": SEED, "lang": "en"})

    body = resp.get_json()
    assert body["ok"] is False
    assert body["blocked"] is True
    assert body["wall"] == "Cloudflare"


def test_auto_analyze_reports_a_throttled_seed_as_rate_limited(http):
    """A 429 on the 'auto' surface (/analyze) reads as a rate limit, not a dead
    seed — the same `rate_limited` flag, Retry-After and 429 status the rest give."""
    http.routes[SEED] = _throttled()

    from landing.app import create_app

    app = create_app()
    app.config.update(TESTING=True)
    resp = app.test_client().post("/analyze", json={"url": SEED, "lang": "en"})

    assert resp.status_code == 429
    body = resp.get_json()
    assert body["ok"] is False
    assert body["rate_limited"] is True
    assert body["retry_after"] == 30
    assert body["error"] == bytecrawl.RATE_LIMIT_MESSAGE


def test_api_unresolvable_host_is_502_unreachable_not_a_raw_400(monkeypatch):
    """A host that doesn't resolve must get the friendly unreachable card too.

    The SSRF guard resolves DNS before the fetch. A mistyped domain fails that
    resolution, and it used to escape as a raw ``400 {"error": "Cannot resolve
    host: …"}`` — the one path that pre-checks, so the landing rendered red
    error text while the playground (which never pre-checks) showed the card.
    Now the guard reports an unresolvable host as UnreachableError, so /api
    answers 502 {unreachable} with the one shared wording, matching every
    other surface. This is the exact regression the landing showed.
    """
    import socket

    from bytecrawl import UNREACHABLE_MESSAGE, security

    def boom(host, *a, **kw):
        raise socket.gaierror("Name or service not known")

    monkeypatch.setattr(security.socket, "getaddrinfo", boom)

    from landing.app import create_app

    app = create_app()
    app.config.update(TESTING=True)
    resp = app.test_client().get("/api", query_string={"url": "https://en.wikipedi2a.org/wiki/x"})

    assert resp.status_code == 502
    body = resp.get_json()
    assert body["unreachable"] is True
    # The friendly shared wording, not a raw "Cannot resolve host".
    assert body["error"] == UNREACHABLE_MESSAGE
    assert "Cannot resolve host" not in body["error"]
