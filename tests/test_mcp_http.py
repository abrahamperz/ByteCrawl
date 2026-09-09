"""Hosted MCP hardening: SSRF guard, rate limiter, per-call caps.

Skipped when the mcp extra isn't installed (e.g. Python 3.9 CI).
"""

import pytest

mcp = pytest.importorskip("mcp")

from bytecrawl import mcp_http  # noqa: E402
from bytecrawl.mcp_http import RateLimiter, RateLimitMiddleware, assert_public_url  # noqa: E402


class TestSSRFGuard:
    """IP literals only — no DNS needed except localhost (hosts file)."""

    @pytest.mark.parametrize("url", [
        "http://127.0.0.1/admin",          # loopback
        "http://localhost:8080/",          # loopback via hosts file
        "http://10.0.0.5/internal",        # RFC1918
        "http://172.16.3.1/",              # RFC1918
        "http://192.168.1.1/router",       # RFC1918
        "http://169.254.169.254/latest/meta-data/",  # cloud metadata
        "http://[::1]/",                   # IPv6 loopback
        "http://0.0.0.0/",                 # unspecified
    ])
    def test_rejects_non_public_addresses(self, url):
        with pytest.raises(ValueError, match="non-public|resolve"):
            assert_public_url(url)

    @pytest.mark.parametrize("url", ["ftp://example.com/x", "file:///etc/passwd",
                                     "javascript:alert(1)"])
    def test_rejects_non_http_schemes(self, url):
        with pytest.raises(ValueError, match="http"):
            assert_public_url(url)

    def test_rejects_missing_hostname(self):
        with pytest.raises(ValueError, match="hostname"):
            assert_public_url("http:///just-a-path")

    def test_allows_global_address(self):
        assert_public_url("http://8.8.8.8/")  # global IP literal, no DNS

    def test_tools_guard_before_fetching(self, monkeypatch):
        from mcp.server.mcpserver.exceptions import ToolError
        called = []
        monkeypatch.setattr(mcp_http.local, "fetch_markdown",
                            lambda url: called.append(url))
        # tools re-raise as ToolError so the client sees the reason
        with pytest.raises(ToolError, match="non-public"):
            mcp_http.fetch_markdown("http://169.254.169.254/")
        assert called == []  # the underlying fetch never ran

    @pytest.mark.parametrize("tool,kwargs", [
        ("list_links", {}),
        ("compare_strategies", {"query": "anything"}),
        ("extract", {"select": "h3"}),
        ("fetch_json_api", {}),
        ("focused_crawl", {}),
    ])
    def test_every_tool_guards_before_fetching(self, monkeypatch, tool, kwargs):
        """A new tool that forgets _guarded() would be an open proxy into the
        host's network, so every one of them is checked, not just the first."""
        from mcp.server.mcpserver.exceptions import ToolError
        called = []
        monkeypatch.setattr(mcp_http.local, tool,
                            lambda *a, **kw: called.append(a))
        with pytest.raises(ToolError, match="non-public"):
            getattr(mcp_http, tool)("http://10.0.0.5/internal", **kwargs)
        assert called == []


class TestRateLimiter:
    def test_allows_up_to_limit(self):
        rl = RateLimiter(limit=3, window=60)
        assert [rl.allow("ip"), rl.allow("ip"), rl.allow("ip")] == [True] * 3
        assert rl.allow("ip") is False

    def test_window_slides(self, monkeypatch):
        t = [1000.0]
        monkeypatch.setattr(mcp_http.time, "monotonic", lambda: t[0])
        rl = RateLimiter(limit=2, window=10)
        assert rl.allow("ip") and rl.allow("ip")
        assert rl.allow("ip") is False
        t[0] += 11  # window passed
        assert rl.allow("ip") is True

    def test_keys_are_independent(self):
        rl = RateLimiter(limit=1, window=60)
        assert rl.allow("a") is True
        assert rl.allow("b") is True
        assert rl.allow("a") is False


@pytest.mark.anyio
async def test_middleware_returns_429_over_limit():
    async def inner(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    mw = RateLimitMiddleware(inner, RateLimiter(limit=1, window=60))
    scope = {"type": "http", "headers": [(b"x-forwarded-for", b"1.2.3.4")],
             "client": ("9.9.9.9", 1234)}

    async def receive():  # pragma: no cover - never called
        return {"type": "http.request"}

    async def run_once():
        events = []

        async def send(ev):
            events.append(ev)
        await mw(scope, receive, send)
        return events[0]["status"]

    assert await run_once() == 200
    assert await run_once() == 429  # same forwarded IP, over the limit


class TestCaps:
    def test_focused_crawl_clamped(self, monkeypatch):
        seen = {}

        def spy(url, query="", strategy="shark", max_pages=0):
            seen["max_pages"] = max_pages
            return {}
        monkeypatch.setattr(mcp_http.local, "focused_crawl", spy)
        mcp_http.focused_crawl("http://8.8.8.8/", max_pages=9999)
        assert seen["max_pages"] == mcp_http.MAX_PAGES

    def test_compare_strategies_clamped_lower(self, monkeypatch):
        """Three crawls behind one rate-limited request, so a tighter cap."""
        seen = {}

        def spy(url, query="", max_pages=0):
            seen["max_pages"] = max_pages
            return {}
        monkeypatch.setattr(mcp_http.local, "compare_strategies", spy)
        mcp_http.compare_strategies("http://8.8.8.8/", query="x", max_pages=9999)
        assert seen["max_pages"] == mcp_http.MAX_COMPARE_PAGES
        assert mcp_http.MAX_COMPARE_PAGES < mcp_http.MAX_PAGES


@pytest.mark.anyio
async def test_hosted_server_registers_same_tools():
    """Same six as the local server: an agent that learned the hosted surface
    can point at a local install and every call still resolves."""
    from bytecrawl import mcp_server as local_server
    hosted = {t.name for t in await mcp_http.server.list_tools()}
    assert hosted == {"fetch_markdown", "extract", "list_links",
                      "focused_crawl", "compare_strategies", "fetch_json_api"}
    assert hosted == {t.name for t in await local_server.server.list_tools()}
