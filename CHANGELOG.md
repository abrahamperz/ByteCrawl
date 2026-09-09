# Changelog
## 1.2.1 — 2026-09-09

Wording, and one change to how the agent skill behaves. Nothing in the library
changed — `pip install bytecrawl` gets the same code as 1.2.0.

### Changed
- **The agent skill no longer instructs an agent to install it.** It opened by
  telling whatever read it to write to `~/.claude/skills/`, add MCP servers and
  edit `CLAUDE.md` "before anything else" — and agents refused, correctly. A
  document fetched from a URL is not a licence to change someone's machine, and
  one agent warned its user that the page was trying to trigger persistent
  changes, which leaves the project looking like the attack rather than the
  tool. Installing is now offered to the person, at the end, and only when they
  ask for it — starting with the hosted MCP server, which writes nothing into
  their home directory and works in every client, with the skill file second
  and the Python package last, since it is only worth installing for JS pages
  or crawls past the hosted cap.
- `/bytecrawl` invoked bare lists all six options in full instead of folding
  four of them onto one line. "clean text" is not something you can choose
  without guessing what it does. The extraction option now also says you do not
  need to know the selectors.
- The tools section on the landing page is three columns instead of four: there
  are six tools, and four columns left an orphan row of two.

## 1.2.0 — 2026-09-09

**Extraction without having read the markup.** Call `extract` with only a URL
and it tells you what the page offers: the blocks that repeat, a ready-to-run
`item` + `fields` for each, and a sample record. Same on every surface — the
MCP tool, `/api?method=extract` with no selector, and the playground's Extract
chip left empty, which turns each block into a button that fills the field and
runs it.

```python
page.selectors()[0]["fields"]
{'price_color': 'p.price_color::text', 'thumbnail': 'img.thumbnail::attr(src)', ...}
```

### Fixed
- **Markdown was throwing away listing pages.** On `books.toscrape.com` — the
  first URL the README tells you to curl — it returned the price column and
  dropped all twenty book titles. Article extraction discards repetition, and on
  a listing the repetition is the content. Affected every surface: the hosted
  API, the playground and `fetch_markdown`. With the content back, the saving is
  the 5-10x the README claims, not the 144x that meant most of the page was gone.
- **"Setup for agents" set nothing up.** The button copies a line that makes an
  agent read the skill for one turn; `/bytecrawl` never appeared. The skill now
  installs itself, choosing the right way for the agent it is talking to — a
  skills directory, the MCP server, or a project instruction file.
- **`/docs` advertised v1.0.0** through three releases. It reads the real
  version now.

### Changed
- `fetch_markdown` reports `tokens_html` beside `tokens_estimate`, so you can
  state the token saving instead of assuming it.

## 1.1.3 — 2026-09-09

### Added
- **`/bytecrawl` as a slash command.** One line installs the agent skill, and it
  is there in every session instead of for one turn. Run it bare and it asks
  what you want — crawl a site for a topic, compare the strategies, read a page,
  pull fields, list links, get the JSON behind a page — in whatever language you
  wrote in. Give it a task and it just does it.

## 1.1.2 — 2026-09-09

### Fixed
- The agent skill linked to a repository that 404s, and documented API response
  fields that no method returns — including telling you to read a `status` field
  the API has never sent, which was the first debugging step it taught.

## 1.1.1 — 2026-09-09

### Fixed
- **The hosted MCP endpoint refused every request** with `421 Invalid Host
  header`. It ships open now; set `BYTECRAWL_ALLOWED_HOSTS` to restrict it if
  you self-host on a domain that also serves authenticated apps.

## 1.1.0 — 2026-09-09

**MCP: six tools instead of four.** Point any MCP-capable agent at ByteCrawl and
it can now do everything the playground does. Nothing to install:

```bash
claude mcp add --transport http bytecrawl https://bytecrawl.vercel.app/mcp
```

| Tool | What it does |
|---|---|
| `focused_crawl` | Crawl a site, rank pages by relevance to a query |
| `compare_strategies` | **New.** All three strategies, one budget, side by side |
| `fetch_markdown` | One page → clean Markdown |
| `extract` | Structured records, or a flat list from one selector |
| `list_links` | **New.** Every outbound link, absolute and deduplicated |
| `fetch_json_api` | Hit a hidden JSON API |

Local (`pip install bytecrawl[mcp]`, then `claude mcp add bytecrawl -- bytecrawl-mcp`)
exposes the identical six, with no page cap and browser support.

### Added
- `compare(url, query)` — run Shark-Search, OPIC and BFS over one site on the
  same budget and see which actually finds the topic. On Wikipedia + "san
  francisco" that is 6 relevant pages out of 6 for Shark-Search against 1 of 6
  for BFS. The three run concurrently, so it costs about as long as one crawl.
  Returns a winner, or `tied` when nothing separates them.
- `extract` accepts a single `select` selector for a flat list of values, as an
  alternative to `item` + `fields`.
- HTTP API: `/api?url=SITE&method=compare&query=TOPIC` for the same comparison
  without any install.

### Changed
- **`Page.links()` now returns absolute, deduplicated URLs** and drops
  `#fragments`, `mailto:` and asset files — the same normalisation the crawlers
  already used. On a long Wikipedia article that is 2,222 raw hrefs down to
  1,408 pages you can actually visit. Pass `raw=True` for the old output.
- `normalize()` moved to `bytecrawl.core` (still importable from
  `bytecrawl.crawler`), so links and crawling share one definition of a link.

### Fixed
- The demo site: a jumping footer, a webfont that resized the logo on first
  paint, and the strategy comparison now looks the same on every page.

## 1.0.0 — 2026-09-08

First stable release. The public API (`Scraper`, `Page`, `Session`, the
`BFS`/`SharkSearch`/`OPIC` crawlers and `pagerank`) is settled.

### Added
- **Hosted MCP server** at `https://bytecrawl.vercel.app/mcp` — point any
  MCP-capable agent at it, nothing to install:
  `claude mcp add --transport http bytecrawl https://bytecrawl.vercel.app/mcp`.
  Same four tools as the local server, hardened for the open internet:
  - **SSRF guard**: resolves each URL and refuses private/loopback/link-local
    addresses (blocks cloud metadata endpoints like `169.254.169.254`).
  - **Hard caps**: `focused_crawl` is clamped to 10 pages per call.
  - **Rate limit**: sliding-window per client IP (in-memory).
  It is static-only (no Playwright on serverless); use the local server for
  JS-rendered sites.
- `bytecrawl-mcp-http` command to self-host the hosted server.
- **Agent skill** at `https://bytecrawl.vercel.app/agent-onboarding/SKILL.md` —
  a single Markdown file an agent can be pointed at
  (`Read and follow <url>`). It routes to the right surface for the job
  (hosted API, MCP, Python library, or a real browser for JS-rendered pages),
  documents strategy selection and the Shark-Search `delta`/`gamma` knobs, and
  states the etiquette and limits. Served with the correct Markdown MIME type.
- `bytecraw.vercel.app` now 308-redirects to `bytecrawl.vercel.app`.

### Documentation
- `/docs` gains an **Agent skill** section, a **Focused crawlers** API reference
  (the graph crawlers were previously undocumented on the site), and the hosted
  MCP endpoint alongside the local one — all three in English, Spanish and
  Portuguese.
- `README.es.md` brought to parity with the English README.
- Removed a stale pointer to a Scrapy playground method that no longer exists.

## 0.3.0 — 2026-09-08

### Changed
- **Project renamed: ByteCraw → ByteCrawl** ("craw" read like a typo; "crawl"
  matches what the library does and the naming of the space it lives in).
  New identity everywhere: package `bytecrawl` on PyPI, repo
  `github.com/abrahamperz/ByteCrawl` (the old URL redirects), demo at
  `bytecrawl.vercel.app`, MCP command `bytecrawl-mcp`. The old `bytecraw`
  0.1.1 package on PyPI is unmaintained — install `bytecrawl`.

## 0.2.1 — 2026-09-08

### Changed
- Docs only: README and changelog now state explicitly that the MCP server is
  **local** (stdio transport) — no hosted/remote endpoint ships yet.

## 0.2.0 — 2026-09-08

### Changed
- **Slim core install**: `pip install bytecrawl` now brings only
  `requests + beautifulsoup4 + lxml`. Playwright and the Markdown stack moved
  to the `[browser]` / `[llm]` / `[all]` extras (they were both hard
  dependencies *and* extras before, which defeated the point of the extras).
- `Scraper.crawl()`: the pagination-selector parameter was renamed
  `next` → `next_page` (it shadowed the Python builtin).
- Graph crawlers are now importable from the top level:
  `from bytecrawl import BFS, SharkSearch, OPIC, pagerank`.
- Version is single-sourced from `bytecrawl.__version__` (0.1.1 shipped with
  mismatched versions in `pyproject.toml` and `__init__.py`).

### Fixed
- `Session.login()` no longer fails silently: HTTP errors on the CSRF fetch
  and on the login POST now raise; a CSRF `<input>` without a `value`
  attribute no longer crashes with `KeyError`.
- `Scraper.browser()` reports the real HTTP status from Playwright instead of
  always claiming 200.
- `Scraper.api()` raises a clear `ValueError` (including the content-type)
  when the endpoint doesn't return JSON, instead of a bare decode error.
- `_root_domain()` handles second-level TLDs: `news.bbc.co.uk` and
  `guardian.co.uk` are no longer considered the same site.
- Missing optional dependencies now raise helpful errors pointing at the
  right extra (`bytecrawl[llm]`, `bytecrawl[browser]`).
- Removed dead code (unused `_PSEUDO` regex in `core.py`).

### Added
- **MCP server — local only** (`bytecrawl-mcp`, `pip install bytecrawl[mcp]`):
  runs on your machine over stdio and exposes `fetch_markdown`, `extract`,
  `focused_crawl` and `fetch_json_api` to any MCP-capable agent (Claude Code,
  Claude Desktop, Cursor). Python 3.10+. A hosted (remote HTTP) version is
  planned but NOT included in this release.
- Test suite: 89 tests covering selectors, extraction, encoding fallback,
  sessions/CSRF, markdown cleanup, the crawl frontier (lazy deletion),
  BFS/Shark-Search/OPIC behavior (including OPIC's cash-conservation
  invariant) and PageRank — all offline, no network needed. Plus 3 opt-in
  live browser tests (`pytest -m live`) that render a JS-only site through
  Playwright.
- CI on GitHub Actions (Python 3.9 and 3.12) with ruff linting.
- Release automation: every merge to main with a new version publishes a
  GitHub Release (tag + this changelog's section as notes).
- English README (`README.md`); the Spanish version lives in `README.es.md`.

## 0.1.1 — 2026-08

Initial public release.
