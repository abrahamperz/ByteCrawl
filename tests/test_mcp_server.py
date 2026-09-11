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
    # One per playground mode, with graph crawl split into the cheap
    # single-strategy call and the three-way comparison.
    assert names == {
        "fetch_markdown",
        "extract",
        "list_links",
        "focused_crawl",
        "compare_strategies",
        "fetch_json_api",
    }


def test_extract_tool(http):
    http.routes["https://x.test/"] = FakeResponse(
        text="<p>"
        + "enough visible text to stay static " * 10
        + "</p>"
        + '<article class="p"><h3>Widget</h3><span class="c">9</span></article>' * 20
    )
    out = mcp_server.extract(
        "https://x.test/", item="article.p", fields={"name": "h3::text", "cost": "span.c::text"}
    )
    assert out["count"] == 20
    assert out["records"][0] == {"name": "Widget", "cost": "9"}


def test_extract_by_single_selector(http):
    """The playground's Extract chip: one selector, a flat list of values."""
    http.routes["https://x.test/"] = FakeResponse(
        text="<p>"
        + "enough visible text to stay static " * 10
        + "</p>"
        + "".join(f'<article class="p"><h3>W{i}</h3></article>' for i in range(5))
    )
    out = mcp_server.extract("https://x.test/", select="article.p h3::text")
    assert out["values"] == ["W0", "W1", "W2", "W3", "W4"]
    assert out["count"] == 5
    assert "records" not in out


def test_extract_rejects_both_shapes(http):
    with pytest.raises(ValueError, match="not both"):
        mcp_server.extract("https://x.test/", item="a", fields={"x": "y"}, select="h3")


def test_extract_with_nothing_is_discovery_not_an_error(http):
    """This used to raise. Refusing a bare call was refusing the only question
    an agent can ask about a page it has not seen."""
    http.routes["https://x.test/"] = FakeResponse(
        text="<p>" + "enough visible text to stay static " * 10 + "</p>"
    )
    out = mcp_server.extract("https://x.test/")
    assert "candidates" in out


def test_list_links_tool(http):
    http.routes["https://x.test/"] = FakeResponse(
        text="<p>" + "enough visible text to stay static " * 10 + "</p>"
        '<a href="/a">a</a><a href="/a">dupe</a><a href="#cite">frag</a>'
        '<a href="mailto:x@y.z">mail</a><a href="/b.png">asset</a>'
    )
    out = mcp_server.list_links("https://x.test/")
    # Absolute and deduplicated; mailto: and assets gone. A bare "#cite"
    # collapses onto the page itself rather than becoming its own entry —
    # which is how hundreds of citation anchors turn into one link.
    assert out["links"] == ["https://x.test/a", "https://x.test/"]
    assert out["count"] == 2 and out["raw"] is False


def test_list_links_raw_passes_hrefs_through(http):
    http.routes["https://x.test/"] = FakeResponse(
        text="<p>" + "enough visible text to stay static " * 10 + "</p>"
        '<a href="/a">a</a><a href="#cite">frag</a>'
    )
    out = mcp_server.list_links("https://x.test/", raw=True)
    assert out["links"] == ["/a", "#cite"] and out["raw"] is True


def test_compare_strategies_tool(fake_site):
    out = mcp_server.compare_strategies("https://s.test/", query="machine learning", max_pages=3)
    assert set(out["strategies"]) == {"bfs", "shark", "opic"}
    assert out["query"] == "machine learning"
    for leg in out["strategies"].values():
        assert leg["relevant"] == 2  # "/" and "/ml" on this site
        assert leg["pages"][0]["url"] == "https://s.test/ml"  # ranked, not visit order
    # Five pages is too small a site to separate them: all three find the same
    # two relevant pages, so this is a real tie and the tool has to say so
    # rather than crown whichever came first.
    assert out["tied"] == ["bfs", "opic", "shark"]
    assert out["winner"] in out["tied"]


def test_compare_strategies_spends_its_budget_differently(fake_site):
    """The tie is in the score, not the behaviour: with 3 pages Shark-Search
    stays in the relevant branch (/ml/deep) where BFS takes the level (/cats)."""
    out = mcp_server.compare_strategies("https://s.test/", query="machine learning", max_pages=3)
    visited = {n: {p["url"] for p in leg["pages"]} for n, leg in out["strategies"].items()}
    assert "https://s.test/ml/deep" in visited["shark"]
    assert "https://s.test/cats" in visited["bfs"]


def test_compare_strategies_needs_a_query():
    with pytest.raises(ValueError, match="query"):
        mcp_server.compare_strategies("https://s.test/", query="")


def test_compare_strategies_survives_one_failing_strategy(fake_site, monkeypatch):
    """A strategy that blows up reports inside its own entry; the others still
    come back — same contract the playground's per-card errors rely on."""
    from bytecrawl import crawler

    def boom(*a, **kw):
        raise RuntimeError("frontier exploded")

    monkeypatch.setitem(crawler.STRATEGIES, "opic", boom)
    out = mcp_server.compare_strategies("https://s.test/", query="machine learning", max_pages=3)
    assert "frontier exploded" in out["strategies"]["opic"]["error"]
    assert "stats" in out["strategies"]["shark"]
    assert out["winner"] in ("bfs", "shark")  # the failed leg can't win


def test_focused_crawl_tool(fake_site):
    out = mcp_server.focused_crawl(
        "https://s.test/", query="machine learning", strategy="shark", max_pages=5
    )
    assert out["strategy"] == "shark"
    assert out["stats"]["requests"] == len(SITE)
    assert out["pages"][0]["relevance"] >= out["pages"][-1]["relevance"]
    assert out["pagerank_top"]  # pagerank computed over the crawled graph


def test_focused_crawl_rejects_unknown_strategy():
    with pytest.raises(ValueError, match="strategy"):
        mcp_server.focused_crawl("https://s.test/", strategy="dfs")


def test_focused_crawl_caps_max_pages(fake_site):
    out = mcp_server.focused_crawl("https://s.test/", strategy="bfs", max_pages=9999)
    assert out["stats"]["requests"] <= 50


def test_fetch_json_api_tool(http):
    http.routes["https://api.test/x"] = FakeResponse(
        json_data={"ok": True}, headers={"content-type": "application/json"}
    )
    out = mcp_server.fetch_json_api("https://api.test/x")
    assert out["data"] == {"ok": True}


def test_extract_with_only_a_url_discovers(http):
    """The bare call is not an error, it is the question before the extraction:
    an agent that has not seen the markup cannot invent a selector, and no tool
    here returns HTML for it to read."""
    http.routes["https://x.test/"] = FakeResponse(
        text="<p>"
        + "enough visible text to stay static " * 10
        + "</p>"
        + "".join(
            f"<article class='card'><h3>W{i}</h3><p class='price'>£{i}</p></article>"
            for i in range(5)
        )
    )
    out = mcp_server.extract("https://x.test/")
    assert "candidates" in out and out["candidates"]
    top = out["candidates"][0]
    assert top["item"] == "article.card" and top["count"] == 5
    assert "hint" in out and "extract again" in out["hint"]


def test_extract_rejects_item_without_fields(http):
    with pytest.raises(ValueError, match="go together"):
        mcp_server.extract("https://x.test/", item="article.card")


def test_fetch_markdown_tool(http):
    """The one tool with no offline test at all. The smoke suite only ever
    called it to check the SSRF guard refused it, never that it worked."""
    body = "".join(
        f"<article class='p'><h3>Book {i}</h3><p class='price'>£{i}.00</p></article>"
        for i in range(20)
    )
    http.routes["https://x.test/"] = FakeResponse(
        text=f"<html><body><nav>Home Shop</nav>{body}</body></html>"
    )
    out = mcp_server.fetch_markdown("https://x.test/")
    assert out["method"] == "static" and out["status"] == 200
    # a listing is all repetition, which is what an article extractor discards;
    # the titles have to survive or the tool returns a gutted page
    assert "Book 0" in out["markdown"] and "Book 19" in out["markdown"]
    # both counts, so a caller can state the saving rather than assume it
    assert out["tokens_html"] > out["tokens_estimate"] > 0
