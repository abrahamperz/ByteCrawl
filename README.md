# ByteCrawl

[![CI](https://github.com/abrahamperz/ByteCrawl/actions/workflows/ci.yml/badge.svg)](https://github.com/abrahamperz/ByteCrawl/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/bytecrawl)](https://pypi.org/project/bytecrawl/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue)](https://pypi.org/project/bytecrawl/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

*Léelo en [español](README.es.md).*

**Give your AI agent focused web crawling.** ByteCrawl is an MCP server (and a
small Python library) that doesn't just scrape a page — it crawls a whole site
and returns the pages *most relevant* to your topic first, using Shark-Search
and OPIC in pure Python.

- **Webpage**: https://bytecrawl.vercel.app/
- **Hosted MCP endpoint**: https://bytecrawl.vercel.app/mcp
- **Agent skill**: https://bytecrawl.vercel.app/agent-onboarding/SKILL.md
- **Latest release**: **1.2.0** — six MCP tools, strategy comparison,
  absolute `Page.links()` ([changelog](https://github.com/abrahamperz/ByteCrawl/blob/main/CHANGELOG.md))

## Point an agent at it (no install, no key)

If you work through an AI agent, the fastest route is neither of the sections
below — hand it the skill and let it choose:

```
Read and follow https://bytecrawl.vercel.app/agent-onboarding/SKILL.md
```

One Markdown file, readable by Claude Code, Cursor, or anything that can fetch a
URL. It routes to the right path for the job (hosted API, MCP, Python library,
or a real browser for JS-rendered pages), documents how to select a crawl
strategy, and includes measured numbers for what that choice buys you.
[Read it yourself](https://bytecrawl.vercel.app/agent-onboarding/SKILL.md).

That line works for one turn. Install it once and `/bytecrawl` is there in every
session, with the agent reaching for it on its own:

```bash
mkdir -p ~/.claude/skills/bytecrawl && \
  curl -so ~/.claude/skills/bytecrawl/SKILL.md \
  https://bytecrawl.vercel.app/agent-onboarding/SKILL.md
```

Run it bare and it asks what you want — crawl a site for a topic, compare the
strategies, read a page, extract fields, list links, or pull a JSON API. Give it
a task instead and it just does it.

## Quick start (MCP — nothing to install)

Point any MCP-capable agent (Claude Code, Claude Desktop, Cursor...) at the
hosted endpoint:

```bash
claude mcp add --transport http bytecrawl https://bytecrawl.vercel.app/mcp
```

Now the agent has six tools — the same six things the playground lets a human do:

| Tool | What it does |
|---|---|
| `focused_crawl` | Crawl a site, rank pages by relevance to a query (Shark-Search / OPIC / BFS) |
| `compare_strategies` | Run all three over the same site on the same budget and see which one wins |
| `fetch_markdown` | One page → clean Markdown (5–10× fewer tokens than raw HTML) |
| `extract` | Structured records via CSS selectors — or call it with just a URL and it tells you what the page offers |
| `list_links` | Every outbound link, absolute and deduplicated |
| `fetch_json_api` | Hit a hidden JSON API |

### Then just ask

You don't call the tools yourself. Once the server is connected you ask in plain
language and the agent picks one:

> Use **bytecrawl** to find everything on python.org about the packaging ecosystem

> Read https://example.com/pricing with **bytecrawl** and give me the plans as a table

> Which crawl strategy does best on wikipedia.org for "san francisco"? Compare them

Saying the name is worth the two syllables: most agents ship their own
single-page fetcher and will reach for that by default. Naming **bytecrawl** is
what gets you a focused crawl instead of one page read in isolation.

The hosted server is static-only, rate-limited per IP, caps crawls at 10 pages,
and refuses non-public URLs (SSRF guard). For heavy use or JS-rendered sites,
run it locally:

```bash
pip install bytecrawl[mcp]
claude mcp add bytecrawl -- bytecrawl-mcp                 # full power, on your machine
pip install bytecrawl[browser] && playwright install chromium   # + JS rendering
```

## Why focused crawling?

Most crawlers visit pages in whatever order they find them. With a limited
request budget, order is everything — Shark-Search chases the branches that
smell like your query and lets the rest decay, so 100 requests get you the 100
*most useful* pages, not the 100 closest to the seed.

```python
from bytecrawl import SharkSearch

result = SharkSearch(query="vector databases").crawl(
    "https://example.com", max_pages=100)

for page in result.top(10):
    print(f'{page["relevance"]:.3f}  {page["url"]}')
```

- **BFS** — level by level, closest to the seed first.
- **Shark-Search** (Hersovici et al., 1998) — topical best-first; links inherit
  their parent's relevance with decay.
- **OPIC** (Abiteboul et al., 2003) — live PageRank via "cash" flow, no full
  graph needed (a `pagerank()` implementation is included to compare against).

All three share one loop — pop, fetch, score links, push — so the same page
budget across strategies is a fair comparison. Every surface takes the same
three names, `shark` (default) / `opic` / `bfs`:

| Surface | How |
|---|---|
| MCP | `focused_crawl(url, query, strategy="opic", max_pages=20)` |
| HTTP API | `?url=SITE&method=crawl&query=TOPIC&strategy=opic` |
| Python | instantiate the class: `OPIC(delay=0.5).crawl(url, max_pages=50)` |

An unknown name is rejected rather than silently defaulted: the API returns 400,
the MCP tool raises `ValueError`. `SharkSearch` requires `query` — without a
topic it has nothing to rank. `BFS` and `OPIC` accept `query` too, but only to
score the pages in the result; it does not change their traversal order.

From `en.wikipedia.org/wiki/Silicon_Valley` with query `san francisco` and 20
pages each, Shark returns 20 pages above 0.1 relevance against 4 for OPIC and 1
for BFS, and its best page scores 0.7774 against BFS's 0.1068 — 7.3x on the same
request budget. Reproduce it with `result.relevant(0.1)`. A lower threshold will
not close the gap: 20 pages leaves thousands of URLs still queued, so coverage
never converges the way it does on a site small enough to exhaust.

Shark-Search exposes both parameters from the paper — `delta` (0.5) sets how
fast a branch with no signal fades (decay is `δⁿ` with depth) and `gamma` (0.8)
splits a link's score between its parent and its own anchor text,
`score = γ·inherited + (1−γ)·local`.

Versus the alternatives: Scrapy is a framework you wire up yourself, Firecrawl
is a paid SaaS — ByteCrawl is a plain library with a 3-package core and these
frontier strategies built in.

## Library API

```python
from bytecrawl import Scraper

bot = Scraper()
page = bot.fetch("https://books.toscrape.com")   # auto: static, browser fallback
books = page.extract("article.product_pod",
                     {"title": "h3 a::attr(title)", "price": "p.price_color::text"})
page.markdown()   # clean Markdown for LLMs   ·   page.tokens()   # token estimate
```

```python
bot.static(url)                                   # plain HTML
bot.api(url, params={...})                        # hidden JSON API
bot.browser(url, wait="div.results")              # JS via Playwright
bot.crawl(url, item="article", fields={...},
          next_page="li.next a::attr(href)")      # pagination
bot.session().login(url, data, csrf_field="csrf_token")   # authenticated
```

## Install

```bash
pip install bytecrawl            # slim core (requests + beautifulsoup4 + lxml)
pip install bytecrawl[llm]       # + Markdown for LLMs
pip install bytecrawl[browser]   # + Playwright (then: playwright install chromium)
pip install bytecrawl[mcp]       # + local MCP server (Python 3.10+)
pip install bytecrawl[all]
```

A missing extra never fails silently — each one raises an ImportError naming the
exact command to run.

## HTTP API (no install)

The same engine behind one hosted GET endpoint. Everything except `url` is
optional; no key, no account.

```bash
curl "https://bytecrawl.vercel.app/api?url=books.toscrape.com"
curl "https://bytecrawl.vercel.app/api?url=en.wikipedia.org/wiki/Silicon_Valley&method=crawl&query=san+francisco&strategy=shark"
```

`method` is one of `markdown` (default), `text`, `html`, `links`, `json`,
`extract`, `crawl`. Static HTML only, crawls capped at 10 pages, rate-limited,
responses cached 10 minutes, private and loopback addresses refused. Full
reference: https://bytecrawl.vercel.app/docs

## Learn each scraping technique

A guided walkthrough (in Spanish) with a runnable example against a practice
site:
[static HTML](docs/01-html-estatico.md) ·
[dynamic JS](docs/02-js-dinamico.md) ·
[hidden APIs](docs/03-api-oculta.md) ·
[pagination](docs/04-crawling-paginacion.md) ·
[login](docs/05-login-sesion.md) ·
[graph crawling](docs/06-crawling-grafos.md) ·
[Markdown for LLMs](docs/markdown-llms.md) ·
[ethics](docs/nota-etica.md)

## Contributing

```bash
pip install -e ".[llm,dev,mcp]"
pytest              # 120 tests, no network required
pytest -m live      # + live browser tests (needs the browser extra)
ruff check bytecrawl tests
```

Scrape responsibly: respect `robots.txt`, terms of service and rate limits.
ByteCrawl ships with a configurable delay between requests.

## License

MIT — see [LICENSE](LICENSE).
