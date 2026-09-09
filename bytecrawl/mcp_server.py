"""MCP server: exposes ByteCrawl to AI agents (Claude Code, Claude Desktop, Cursor...).

Any MCP-capable agent gets six tools that map to what ByteCrawl does well:
clean Markdown for LLM ingestion, structured extraction with CSS selectors,
the outbound link set, focused crawling and its strategy comparison (the
differentiator) and hidden JSON APIs. They are the same six things the
playground at bytecrawl.vercel.app lets a human do.

Run it:            bytecrawl-mcp                 (stdio transport)
Claude Code:       claude mcp add bytecrawl -- bytecrawl-mcp
Requires:          pip install bytecrawl[mcp]
"""

from __future__ import annotations

try:
    from mcp.server.mcpserver import MCPServer
except ImportError as e:  # pragma: no cover - exercised only without the extra
    raise ImportError(
        "The MCP server needs the 'mcp' extra: pip install bytecrawl[mcp]"
    ) from e

from .core import Scraper
from .crawler import STRATEGIES as _STRATEGIES
from .crawler import compare, pagerank

DELAY = 0.2  # seconds between requests, per crawler

# One polite scraper shared by every tool call.
_scraper = Scraper(delay=DELAY)

server = MCPServer(
    "bytecrawl",
    instructions=(
        "Web scraping and focused crawling. Use fetch_markdown to read a page, "
        "extract for structured records, list_links for a page's outbound links, "
        "focused_crawl to find the pages most relevant to a topic within a site, "
        "compare_strategies to see which frontier strategy wins on a given site, "
        "and fetch_json_api for JSON endpoints."
    ),
)


@server.tool(
    description=(
        "Fetch a web page and return it as clean Markdown, ready for LLM "
        "consumption. Reports tokens_estimate against tokens_html so you "
        "can state the saving rather than assume it (typically 5-10x)."
    )
)
def fetch_markdown(url: str) -> dict:
    page = _scraper.fetch(url)
    md = page.markdown()
    # tokens_html alongside it, the same pair the playground shows. On its own
    # tokens_estimate is a number with nothing to compare against; next to the
    # raw HTML it is the reason to have called this instead of reading the
    # page, and the agent can say so rather than assert it.
    return {
        "url": url,
        "markdown": md,
        "tokens_estimate": page.tokens(md),
        "tokens_html": page.tokens(),
        "method": page.method,
        "status": page.status,
    }


@server.tool(
    description=(
        "Extract data from a page with CSS selectors. Three shapes. Call it "
        "with ONLY the url to discover what is extractable: it returns the "
        "page's repeated blocks, each with a ready-to-use item + fields and a "
        "sample record — use this whenever you have not seen the markup. "
        "Then call it with 'item' (the selector delimiting one record, e.g. "
        "'article.product') and 'fields' (names to relative selectors "
        'supporting ::text and ::attr(name), e.g. {"title": '
        '"h3 a::attr(title)", "price": "p.price::text"}; a name ending in [] '
        "collects a list). Or pass 'select' alone for a flat list of one "
        "selector's values across the page, e.g. 'h3 a::attr(title)'."
    )
)
def extract(url: str, item: str = "", fields: dict[str, str] | None = None,
            select: str = "") -> dict:
    # Three shapes, one tool. Agents reach for a single selector far more
    # often than for a record schema, and an agent that has never seen the
    # page can produce neither: fetch_markdown strips exactly the classes a
    # selector is built from, and no tool here returns HTML — deliberately,
    # since raw markup costs more tokens than the data it is meant to locate.
    # So the bare call answers the question the agent actually has, which is
    # "what is on this page and how do I ask for it?"
    if select and (item or fields):
        raise ValueError("pass either 'select' or 'item'+'fields', not both")
    if bool(item) != bool(fields):
        raise ValueError("'item' and 'fields' go together — or pass neither "
                         "to see what this page offers")
    # Checked before the fetch: a malformed call shouldn't cost the site a
    # request.
    page = _scraper.fetch(url)
    if select:
        values = page.css_all(select)
        return {"url": url, "select": select, "count": len(values),
                "values": values}
    if item:
        records = page.extract(item, fields)
        return {"url": url, "count": len(records), "records": records}
    candidates = page.selectors()
    return {
        "url": url,
        "candidates": candidates,
        "hint": ("call extract again with the item and fields of whichever "
                 "candidate holds what you want" if candidates else
                 "no repeated blocks here — this page is probably not a "
                 "listing; pass 'select' with a specific selector instead"),
    }


@server.tool(
    description=(
        "Every outbound link on a page as an absolute, deduplicated URL, with "
        "#fragments, mailto: and asset files dropped — the set of pages you "
        "could actually visit next. Pass raw=true for the untouched href "
        "attribute values instead."
    )
)
def list_links(url: str, raw: bool = False) -> dict:
    page = _scraper.fetch(url)
    links = page.links(raw=raw)
    return {"url": url, "count": len(links), "raw": raw, "links": links}


@server.tool(
    description=(
        "Crawl a site starting from 'url', visiting the pages most relevant to "
        "'query' first (focused crawling). strategy: 'shark' (topical "
        "best-first, default), 'opic' (structural importance) or 'bfs' "
        "(level by level). Returns pages ranked by relevance plus crawl stats."
    )
)
def focused_crawl(url: str, query: str = "", strategy: str = "shark",
                  max_pages: int = 20) -> dict:
    if strategy not in _STRATEGIES:
        raise ValueError(f"strategy must be one of {sorted(_STRATEGIES)}")
    max_pages = min(max_pages, 50)  # keep agent calls bounded and polite
    crawler = _STRATEGIES[strategy](query=query, delay=DELAY)
    result = crawler.crawl(url, max_pages=max_pages)
    ranks = pagerank(result.graph)
    return {
        "strategy": strategy,
        "stats": result.stats,
        "pages": result.top(max_pages) if query else result.pages,
        "pagerank_top": [
            {"url": u, "rank": round(r, 4)} for u, r in list(ranks.items())[:10]
        ],
    }


@server.tool(
    description=(
        "Run all three frontier strategies (Shark-Search, OPIC, BFS) over the "
        "same site on the same page budget and return them side by side, so "
        "you can see which one actually finds pages about 'query'. Costs three "
        "crawls; when you just want the relevant pages, use focused_crawl. "
        "Returns per-strategy stats, relevant-page counts and rankings, plus "
        "the winner."
    )
)
def compare_strategies(url: str, query: str, max_pages: int = 20) -> dict:
    max_pages = min(max_pages, 50)  # same bound as focused_crawl, per strategy
    out = compare(url, query, max_pages=max_pages, delay=DELAY)
    return {"url": url, "query": query, "max_pages": max_pages, **out}


@server.tool(
    description="Fetch a JSON API endpoint (the 'hidden API' scraping technique)."
)
def fetch_json_api(url: str, params: dict | None = None) -> dict:
    page = _scraper.api(url, params=params)
    return {"url": url, "status": page.status, "data": page.json()}


def main() -> None:
    """Entry point for the bytecrawl-mcp console script (stdio transport)."""
    server.run()


if __name__ == "__main__":
    main()
