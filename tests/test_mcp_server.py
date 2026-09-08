"""MCP server: tool registration and tool behavior (no network).

Skipped entirely when the mcp extra isn't installed (e.g. Python 3.9 CI).
"""

import pytest

mcp = pytest.importorskip("mcp")

from bytecrawl import mcp_server  # noqa: E402
from tests.conftest import SITE, FakeResponse  # noqa: E402


@pytest.fixture(autouse=True)
def _no_delay():
    """The module-level scraper shouldn't sleep in tests."""
    mcp_server._scraper.delay = 0.0
    yield


@pytest.mark.anyio
async def test_all_tools_registered():
    tools = await mcp_server.server.list_tools()
    names = {t.name for t in tools}
    assert names == {"fetch_markdown", "extract", "focused_crawl", "fetch_json_api"}


def test_extract_tool(http):
    http.routes["https://x.test/"] = FakeResponse(
        text="<p>" + "enough visible text to stay static " * 10 + "</p>"
        + '<article class="p"><h3>Widget</h3><span class="c">9</span></article>' * 20)
    out = mcp_server.extract("https://x.test/", item="article.p",
                             fields={"name": "h3::text", "cost": "span.c::text"})
    assert out["count"] == 20
    assert out["records"][0] == {"name": "Widget", "cost": "9"}


def test_focused_crawl_tool(fake_site):
    out = mcp_server.focused_crawl("https://s.test/", query="machine learning",
                                   strategy="shark", max_pages=5)
    assert out["strategy"] == "shark"
    assert out["stats"]["requests"] == len(SITE)
    assert out["pages"][0]["relevance"] >= out["pages"][-1]["relevance"]
    assert out["pagerank_top"]  # pagerank computed over the crawled graph

def test_focused_crawl_rejects_unknown_strategy():
    with pytest.raises(ValueError, match="strategy"):
        mcp_server.focused_crawl("https://s.test/", strategy="dfs")


def test_focused_crawl_caps_max_pages(fake_site):
    out = mcp_server.focused_crawl("https://s.test/", strategy="bfs",
                                   max_pages=9999)
    assert out["stats"]["requests"] <= 50


def test_fetch_json_api_tool(http):
    http.routes["https://api.test/x"] = FakeResponse(
        json_data={"ok": True}, headers={"content-type": "application/json"})
    out = mcp_server.fetch_json_api("https://api.test/x")
    assert out["data"] == {"ok": True}
