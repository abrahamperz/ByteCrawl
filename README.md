# ByteCraw

[![CI](https://github.com/abrahamperz/ByteCraw/actions/workflows/ci.yml/badge.svg)](https://github.com/abrahamperz/ByteCraw/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/bytecraw)](https://pypi.org/project/bytecraw/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue)](https://pypi.org/project/bytecraw/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

**Focused crawling for LLM data collection** — Shark-Search and OPIC in pure
Python, on a 3-dependency core. Plus one small API for everyday scraping:
static HTML, JS-rendered pages, hidden JSON APIs, session login, pagination,
and Markdown conversion that cuts LLM token costs 5–10×.

*Léelo en [español](README.es.md).*

- **Live demo**: https://byte-craw.vercel.app/
- **PyPI**: https://pypi.org/project/bytecraw/

## Why another crawler?

Most crawlers visit pages in whatever order they find them. When you're
collecting data on a topic with a limited request budget, order is everything:

```python
from bytecraw import SharkSearch

result = SharkSearch(query="vector databases").crawl(
    "https://example.com", max_pages=100)

for page in result.top(10):
    print(f'{page["relevance"]:.3f}  {page["url"]}')

result.graph  # {url: [links]} — feed it to pagerank() for offline analysis
```

Shark-Search chases the branches of a site that smell like your query and
lets irrelevant ones decay geometrically — so 100 requests get you the 100
*most useful* pages, not the 100 closest to the seed.

|  | Scrapy | Firecrawl | ByteCraw |
|---|---|---|---|
| Shape | framework (projects, pipelines) | SaaS API | plain library |
| Core install | ~20 packages | — | 3 packages |
| Crawl ordering | FIFO/priority you write yourself | managed | **BFS · Shark-Search · OPIC built in** |
| Cost | free | per-credit | free |

The three strategies share one loop (`pop → fetch → score links → push`), so
comparing them on the same site is a fair experiment — the demo does exactly
that, live.

- **BFS** — level by level, closest to the seed first.
- **Shark-Search** (Hersovici et al., 1998) — topical best-first: links
  inherit their parent's relevance with decay; bad branches die out on their own.
- **OPIC** (Abiteboul et al., 2003) — each page holds "cash" it distributes to
  its links when visited: PageRank computed live, without the full graph.
  A `pagerank()` power-iteration implementation is included to compare against.

## Everyday scraping

```python
from bytecraw import Scraper

bot = Scraper()
page = bot.fetch("https://books.toscrape.com")   # auto: static, falls back to browser
books = page.extract("article.product_pod", {
    "title": "h3 a::attr(title)",
    "price": "p.price_color::text",
})
```

```python
page.markdown()   # clean Markdown for LLM ingestion (needs the llm extra)
page.tokens()     # quick token estimate
```

Explicit strategies when you know what you're dealing with:

```python
bot.static(url)                          # plain HTML
bot.api(url, params={...})               # hidden JSON APIs
bot.browser(url, wait="div.results")     # JS rendering via Playwright
bot.crawl(url, item="article", fields={...},
          next_page="li.next a::attr(href)")   # follow pagination
bot.session().login(url, data, csrf_field="csrf_token")  # authenticated
```

## Use it from an AI agent (MCP)

ByteCraw ships an MCP server that **runs locally on your machine** (stdio
transport — there is no hosted/remote endpoint yet), so any MCP-capable agent
(Claude Code, Claude Desktop, Cursor...) can scrape and focused-crawl directly:

```bash
pip install bytecraw[mcp]
claude mcp add bytecraw -- bytecraw-mcp     # Claude Code
```

Or in any MCP client config:

```json
{"mcpServers": {"bytecraw": {"command": "bytecraw-mcp"}}}
```

The agent gets four tools: `fetch_markdown` (page → LLM-ready Markdown),
`extract` (CSS-selector records), `focused_crawl` (Shark-Search/OPIC/BFS with
relevance ranking) and `fetch_json_api`.

For JS-rendered sites, also install the browser extra — `fetch_markdown` and
`extract` then fall back to a real browser automatically when a page comes
back empty:

```bash
pip install bytecraw[browser] && playwright install chromium
```

## Install

```bash
pip install bytecraw            # slim core: requests + beautifulsoup4 + lxml
pip install bytecraw[llm]       # + Markdown conversion (trafilatura, markdownify)
pip install bytecraw[browser]   # + Playwright (then: playwright install chromium)
pip install bytecraw[all]       # everything
```

## Docs

Teaching docs (Spanish) — each scraping technique explained with a runnable
example against a practice site:

1. [Static HTML](docs/01-html-estatico.md) ·
2. [Dynamic JS](docs/02-js-dinamico.md) ·
3. [Hidden APIs](docs/03-api-oculta.md) ·
4. [Pagination](docs/04-crawling-paginacion.md) ·
5. [Session login](docs/05-login-sesion.md) ·
6. [Graph crawling](docs/06-crawling-grafos.md) ·
[Markdown for LLMs](docs/markdown-llms.md) ·
[Strategy](docs/estrategia.md) ·
[Ethics](docs/nota-etica.md)

## Development

```bash
pip install -e ".[llm,dev]"
pytest --cov=bytecraw   # 89 tests, no network required
ruff check bytecraw tests

# live browser tests (real network + Chromium):
pip install -e ".[browser]" && playwright install chromium
pytest -m live
```

## Ethics

Respect `robots.txt`, terms of service and rate limits. ByteCraw ships with a
configurable delay between requests and the docs include an
[ethics note](docs/nota-etica.md). Scrape responsibly.

## License

MIT
