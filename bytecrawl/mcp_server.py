"""MCP server: exposes ByteCrawl to AI agents (Claude Code, Claude Desktop, Cursor...).

Any MCP-capable agent gets four tools that map to what ByteCrawl does well:
clean Markdown for LLM ingestion, structured extraction with CSS selectors,
focused crawling (the differentiator) and hidden JSON APIs.

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
from .crawler import BFS, OPIC, SharkSearch, pagerank

# One polite scraper shared by every tool call.
_scraper = Scraper(delay=0.2)

_STRATEGIES = {"bfs": BFS, "shark": SharkSearch, "opic": OPIC}

server = MCPServer(
    "bytecrawl",
    instructions=(
        "Web scraping and focused crawling. Use fetch_markdown to read a page, "
        "extract for structured records, focused_crawl to find the pages most "
        "relevant to a topic within a site, and fetch_json_api for JSON endpoints."
    ),
)


@server.tool(
    description=(
        "Fetch a web page and return it as clean Markdown, ready for LLM "
        "consumption (5-10x fewer tokens than raw HTML)."
    )
)
def fetch_markdown(url: str) -> dict:
    page = _scraper.fetch(url)
    md = page.markdown()
    return {
        "url": url,
        "markdown": md,
        "tokens_estimate": page.tokens(md),
        "method": page.method,
        "status": page.status,
    }


@server.tool(
    description=(
        "Extract structured records from a page with CSS selectors. "
        "'item' delimits each record (e.g. 'article.product'); 'fields' maps "
        "names to relative selectors supporting ::text and ::attr(name), e.g. "
        '{"title": "h3 a::attr(title)", "price": "p.price::text"}. '
        "A field name ending in [] collects a list."
    )
)
def extract(url: str, item: str, fields: dict[str, str]) -> dict:
    page = _scraper.fetch(url)
    records = page.extract(item, fields)
    return {"url": url, "count": len(records), "records": records}


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
    crawler = _STRATEGIES[strategy](query=query, delay=0.2)
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
