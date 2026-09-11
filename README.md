# ByteCrawl

[![MCP](https://img.shields.io/badge/MCP-6%20tools%2C%20hosted-0a0a0a)](https://bytecrawl.vercel.app/mcp)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue)](https://pypi.org/project/bytecrawl/)
[![PyPI](https://img.shields.io/pypi/v/bytecrawl)](https://pypi.org/project/bytecrawl/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![CI](https://github.com/abrahamperz/ByteCrawl/actions/workflows/ci.yml/badge.svg)](https://github.com/abrahamperz/ByteCrawl/actions/workflows/ci.yml)

*Léelo en [español](README.es.md).*

**Give your AI agent focused web crawling.** ByteCrawl is an MCP server (and a
small Python library) that doesn't just scrape a page — it crawls a whole site
and returns the pages *most relevant* to your topic first, using Shark-Search
and OPIC in pure Python.

- **Webpage**: https://bytecrawl.vercel.app/
- **Hosted MCP endpoint**: https://bytecrawl.vercel.app/mcp
- **Agent skill**: https://bytecrawl.vercel.app/agent-onboarding/SKILL.md
- **Latest release**: **1.4.0** — clearer errors when a site's bot protection
  (Cloudflare, DataDome, …) blocks a fetch ([changelog](https://github.com/abrahamperz/ByteCrawl/blob/main/CHANGELOG.md))

## Why focused crawling?

Most crawlers visit pages in whatever order they find them. Under a request
budget, order is everything. From `en.wikipedia.org/wiki/Silicon_Valley` with
query `san francisco`, 20 pages each:

| Strategy | Pages over 0.1 relevance | Best page |
|---|---|---|
| `shark` | **20** | **0.7774** |
| `opic` | 4 | 0.2799 |
| `bfs` | 1 | 0.1068 |

Same twenty requests; only the order changed. Reproduce it with
`result.relevant(0.1)`.

**That is a token argument as much as a quality one.** Those pages end up in a
context window. BFS spends nineteen of its twenty on whatever happened to be
linked first, and you pay for all nineteen. And each page arrives as Markdown
rather than raw HTML — around **6.5× fewer tokens** for the same content.
`fetch_markdown` reports both counts, so you can state the saving rather than
assume it.

**How it works.** Every link gets a score before it is visited. Shark-Search
takes how much the anchor text and the parent page look like your query, decayed
with depth so a branch that stops matching fades out on its own; OPIC scores by
importance instead, cash flowing along links. The frontier is a priority queue,
so the crawler always spends its next request on the best link it knows about —
which is why the budget lands on relevant pages instead of nearby ones.

```python
from bytecrawl import SharkSearch

result = SharkSearch(query="vector databases").crawl(url, max_pages=100)
result.top(10)          # [{url, title, relevance, depth, order}, ...]
```

- **Shark-Search** (Hersovici et al., 1998) — topical best-first; links inherit
  their parent's relevance with decay, so barren branches die out on their own.
- **OPIC** (Abiteboul et al., 2003) — live PageRank via "cash" flowing along
  links, no full graph needed. `pagerank()` is included to compare against.
- **BFS** — level by level. The honest baseline.

All three share one loop — pop, fetch, score links, push — so an equal page
budget is a fair comparison, and every surface takes the same three names.

Scrapy is a framework you wire up yourself and Firecrawl is a paid SaaS.
ByteCrawl is a library with a three-package core and these strategies built in.

## Quick start

One command, nothing installed:

```bash
claude mcp add --scope user --transport http bytecrawl https://bytecrawl.vercel.app/mcp
```

Your agent now has six tools — the same six the playground gives a human:

| Tool | What it does |
|---|---|
| `focused_crawl` | Crawl a site, rank pages by relevance to a query (Shark-Search / OPIC / BFS) |
| `compare_strategies` | Run all three on the same budget and see which one wins |
| `fetch_markdown` | One page → clean Markdown, around 6.5× fewer tokens than raw HTML |
| `extract` | Structured records via CSS selectors — or call it with just a URL and it tells you what the page offers |
| `list_links` | Every outbound link, absolute and deduplicated |
| `fetch_json_api` | Hit a hidden JSON API |

Then ask in plain language — you never call the tools yourself:

> Use **bytecrawl** to find everything on python.org about the packaging ecosystem

Say the name. Most agents ship their own single-page fetcher and reach for it by
default; **bytecrawl** is what gets you a crawl ranked by your query instead of
one page read in isolation.

The hosted server is static-only, rate-limited, capped at 10 pages per crawl,
and refuses non-public URLs. For JS-rendered pages or bigger crawls, run it
yourself:

```bash
pipx install "bytecrawl[mcp]"                           # a CLI app, hence pipx
claude mcp add --scope user bytecrawl -- bytecrawl-mcp
```

## `/bytecrawl` — the agent skill

The server gives your agent the tools; the skill gives it the judgment about
using them, and you a slash command:

```bash
mkdir -p ~/.claude/skills/bytecrawl && \
  curl -so ~/.claude/skills/bytecrawl/SKILL.md \
  https://bytecrawl.vercel.app/agent-onboarding/SKILL.md
```

The same command updates it. Installing copies the file, so later fixes never
reach your copy — the skill compares its hash against
[`/agent-onboarding/skill.json`](https://bytecrawl.vercel.app/agent-onboarding/skill.json)
once a session and tells you when yours is behind. It never overwrites anything
on its own.

No skills directory? Hand the file to any agent instead — it works for that
conversation, installs nothing:

```
Read and follow https://bytecrawl.vercel.app/agent-onboarding/SKILL.md
```

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
