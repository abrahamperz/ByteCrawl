"""Hosted (HTTP) MCP server: ByteCrawl tools behind a public URL.

Same six tools as the local stdio server (bytecrawl.mcp_server), hardened
for the open internet:

  1. SSRF guard    — every URL is resolved and rejected if any of its IPs is
                     private/loopback/link-local (a hosted scraper must not be
                     an open proxy into the host's network).
  2. Hard caps     — focused_crawl is clamped to MAX_PAGES pages and
                     compare_strategies (three crawls in one call) to the
                     smaller MAX_COMPARE_PAGES; the shared scraper keeps a
                     polite delay. The cost of one request is bounded no
                     matter what the client asks for.
  3. Rate limit    — sliding-window per client IP, in memory. Best-effort on
                     serverless (each warm instance counts separately); good
                     enough to keep one abuser from exhausting the free tier.

Serverless notes: runs stateless (no session affinity) and static-only —
Playwright is not available on Vercel, so JS-heavy sites should use the local
`bytecrawl-mcp` instead. Redirect chains are not re-validated hop by hop; the
guard checks the URL each tool receives (and the crawler stays on the seed's
registered domain).

Self-host:  bytecrawl-mcp-http            (serves http://0.0.0.0:8000/mcp)
Connect:    claude mcp add --transport http bytecrawl https://bytecrawl.vercel.app/mcp
"""

from __future__ import annotations

import os
import time
from collections import defaultdict, deque

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings

from . import mcp_server as local
from .security import assert_public_url

MAX_PAGES = 10  # hard cap per focused_crawl call (local allows 50)
# compare_strategies is three crawls that the rate limiter charges as one
# request, so it gets a smaller budget: 3 x 6 = 18 fetches, about two
# focused_crawls' worth. Same bounded-cost rule, applied to a heavier call.
MAX_COMPARE_PAGES = 6
RATE_LIMIT = 20  # requests per window per client IP
RATE_WINDOW = 60.0  # seconds


def _guarded(url: str) -> None:
    """SSRF check, re-raised as ToolError so MCP clients see the reason
    (plain exceptions are masked as a generic 'error executing tool')."""
    try:
        assert_public_url(url)
    except ValueError as e:
        raise ToolError(str(e)) from e


# --- 3. rate limit ----------------------------------------------------------
class RateLimiter:
    """Sliding-window counter per key. In-memory: per-instance on serverless."""

    def __init__(self, limit: int = RATE_LIMIT, window: float = RATE_WINDOW):
        self.limit = limit
        self.window = window
        self._hits: dict[str, deque] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        hits = self._hits[key]
        while hits and now - hits[0] > self.window:
            hits.popleft()
        if len(hits) >= self.limit:
            return False
        hits.append(now)
        return True


class RateLimitMiddleware:
    """ASGI wrapper: answers 429 before the MCP app sees the request."""

    def __init__(self, app, limiter: RateLimiter | None = None):
        self.app = app
        self.limiter = limiter or RateLimiter()

    @staticmethod
    def _client_ip(scope) -> str:
        for name, value in scope.get("headers", []):
            if name == b"x-forwarded-for":
                return value.decode().split(",")[0].strip()
        client = scope.get("client")
        return client[0] if client else "unknown"

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and not self.limiter.allow(self._client_ip(scope)):
            await send(
                {
                    "type": "http.response.start",
                    "status": 429,
                    "headers": [(b"content-type", b"application/json"), (b"retry-after", b"60")],
                }
            )
            await send(
                {
                    "type": "http.response.body",
                    "body": b'{"error": "rate limit exceeded, try again in a minute"}',
                }
            )
            return
        await self.app(scope, receive, send)


# --- the hardened server ----------------------------------------------------
server = MCPServer(
    "bytecrawl",
    instructions=(
        "Hosted ByteCrawl: web scraping and focused crawling. Static HTML only "
        "(no JS rendering here — run bytecrawl-mcp locally for that). "
        f"Crawls are capped at {MAX_PAGES} pages per call, and "
        f"compare_strategies at {MAX_COMPARE_PAGES} pages per strategy."
    ),
)


@server.tool(
    description=(
        "Fetch a public web page and return it as clean Markdown for LLM "
        "consumption, with tokens_estimate against tokens_html so you can "
        "state the saving. Static HTML only on the hosted server."
    )
)
def fetch_markdown(url: str) -> dict:
    _guarded(url)
    return local.fetch_markdown(url)


@server.tool(
    description=(
        "Extract data from a public page with CSS selectors. Call it with ONLY the "
        "url to discover what is extractable — it returns the page's repeated "
        "blocks with ready-to-use item + fields and a sample record each, which is "
        "what you need when you have not seen the markup. Then 'item'+'fields' for "
        "structured records (::text / ::attr(name); a field name ending in [] "
        "collects a list), or 'select' on its own for a flat list of one "
        "selector's values."
    )
)
def extract(
    url: str, item: str = "", fields: dict[str, str] | None = None, select: str = ""
) -> dict:
    _guarded(url)
    return local.extract(url, item=item, fields=fields, select=select)


@server.tool(
    description=(
        "Every outbound link on a public page as an absolute, deduplicated URL "
        "(#fragments, mailto: and asset files dropped). raw=true returns the "
        "untouched href values."
    )
)
def list_links(url: str, raw: bool = False) -> dict:
    _guarded(url)
    return local.list_links(url, raw=raw)


@server.tool(
    description=(
        "Focused crawl of a public site: visit the pages most relevant to 'query' "
        "first. strategy: shark (default) | opic | bfs. Capped at "
        f"{MAX_PAGES} pages per call on the hosted server."
    )
)
def focused_crawl(
    url: str, query: str = "", strategy: str = "shark", max_pages: int = MAX_PAGES
) -> dict:
    _guarded(url)
    return local.focused_crawl(
        url, query=query, strategy=strategy, max_pages=min(max_pages, MAX_PAGES)
    )


@server.tool(
    description=(
        "Run Shark-Search, OPIC and BFS over the same public site on the same "
        "budget and return them side by side with a winner. Three crawls in one "
        f"call, so it is capped at {MAX_COMPARE_PAGES} pages per strategy on the "
        "hosted server."
    )
)
def compare_strategies(url: str, query: str, max_pages: int = MAX_COMPARE_PAGES) -> dict:
    _guarded(url)
    return local.compare_strategies(url, query=query, max_pages=min(max_pages, MAX_COMPARE_PAGES))


@server.tool(description="Fetch a public JSON API endpoint.")
def fetch_json_api(url: str, params: dict | None = None) -> dict:
    _guarded(url)
    return local.fetch_json_api(url, params=params)


def _transport_security() -> TransportSecuritySettings:
    """Host/Origin validation for the streamable-HTTP transport.

    The SDK turns DNS-rebinding protection on by itself whenever the app is
    built for the default 127.0.0.1 host, and then allows only localhost — so
    the deployed server answered every real request with

        421  Invalid Host header

    That protection is for MCP servers bound to a developer's machine, where a
    malicious page could otherwise reach a service the browser can see and the
    internet cannot. This server is the opposite: public, unauthenticated, no
    cookies, and behind an SSRF guard that already refuses anything a caller
    could not fetch directly. Validating Host buys nothing here.

    Set BYTECRAWL_ALLOWED_HOSTS (comma-separated; `host:*` wildcards allowed,
    and BYTECRAWL_ALLOWED_ORIGINS alongside it) to turn it back on — worth
    doing if you self-host on a domain that also serves authenticated apps.
    """
    hosts = [
        h.strip() for h in os.environ.get("BYTECRAWL_ALLOWED_HOSTS", "").split(",") if h.strip()
    ]
    if not hosts:
        return TransportSecuritySettings(enable_dns_rebinding_protection=False)
    origins = [
        o.strip() for o in os.environ.get("BYTECRAWL_ALLOWED_ORIGINS", "").split(",") if o.strip()
    ]
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=hosts,
        allowed_origins=origins,
    )


def create_app(limiter: RateLimiter | None = None):
    """ASGI app: streamable-HTTP MCP at /mcp, rate-limited. Stateless for
    serverless (json_response avoids long-lived SSE streams on Vercel)."""
    app = server.streamable_http_app(
        streamable_http_path="/mcp",
        stateless_http=True,
        json_response=True,
        transport_security=_transport_security(),
    )
    return RateLimitMiddleware(app, limiter)


def main() -> None:
    """Entry point for bytecrawl-mcp-http (self-hosted)."""
    import uvicorn

    # nosec B104 — an MCP HTTP server must bind all interfaces to be reachable
    # inside a container or serverless host.
    uvicorn.run(create_app(), host="0.0.0.0", port=8000)  # nosec B104


if __name__ == "__main__":
    main()
