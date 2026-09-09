# Changelog

## 1.2.0 — 2026-09-09

### Added
- **`Page.selectors()` — extraction without having read the markup.** Writing an
  `extract()` call means knowing the classes on the page, and an agent connected
  over MCP could not: `fetch_markdown` strips exactly the classes and attributes
  a selector is built from, and no tool returns HTML on purpose, since raw markup
  costs more tokens than the data it is meant to locate. So this reports the
  structure instead of the source — the blocks that repeat, the inner selectors
  that resolve across most instances, and a sample record for each, which is a
  runnable `item` + `fields` rather than something to interpret.

  Two heuristics do the work. A repeated wrapper and the card inside it appear
  equally often, so the one that offers nothing its own child does not is
  dropped: `article.product_pod` survives, `li.col-xs-6.col-sm-4.col-md-3` does
  not. And a column whose element contains another column's is thrown away,
  because its text is every child's text run together — `div.product_price`
  otherwise comes back as "£51.77In stockAdd to basket".

### Fixed
- **`markdown()` was throwing the page away on listings.** Main-content
  extraction is built to discard repetition — which on a listing page is the
  content. On `books.toscrape.com`, the first URL the README tells you to curl,
  it returned the price column and dropped all twenty book titles: 358
  characters out of 1,851 of visible text. It now checks what came back against
  the page's own text and falls back to full-page conversion when the
  extractor kept under a quarter of it. Measured, that floor sits far below
  every good case (1.14x of visible text on quotes.toscrape.com, 1.4-1.6x on
  Wikipedia) and just above the one that broke (0.19x), so an article buried in
  navigation still gets the boilerplate stripped.

  With the content back, the saving is 4.8x on books.toscrape.com, 5.8x on
  quotes and 6.6x on a Wikipedia article — the 5-10x the README claims. The
  broken version scored 144x, which was not a saving.

### Fixed
- **"Setup for agents" set nothing up.** The button copies `Read and follow
  <url>`, which makes an agent read the skill for exactly one turn — next
  message it has none of it, and `/bytecrawl` never appears. The skill showed
  the install command but never told the agent to run it, so the button promised
  setup and delivered a single answer. Installing itself is now the first
  instruction in the file — and it branches on what the agent is, because a
  skills directory is Claude Code's convention and telling Codex or Cursor to
  write `~/.claude/skills/` produces a file nobody reads. Claude Code installs
  the file and gets `/bytecrawl`; an MCP client with no skills directory adds
  the hosted server, which is the one path that persists everywhere and hands
  over the tools rather than instructions about them; an agent with an
  `AGENTS.md` adds one line pointing back; a sandbox with nothing to write to
  skips it silently. If a task came with the URL, the task comes first.

### Changed
- `fetch_markdown` returns `tokens_html` next to `tokens_estimate`, the pair the
  playground already showed. On its own the token count has nothing to compare
  against; beside the raw HTML it is the reason to have called the tool, and an
  agent can state the saving instead of asserting it.
- **`extract` called with only a url now discovers instead of failing.** It used
  to raise "extract needs 'item' and 'fields', or 'select'" — refusing the one
  question an agent can ask about a page it has not seen. The same call works on
  every surface: the MCP tool, `/api?method=extract` without `select`, and the
  playground's Extract chip with the field left empty, which lists the blocks it
  found and turns each into a button that fills the selector and runs it.
- The demo API no longer sorts JSON keys. The discovered fields come back ranked
  with the most useful selector first and the playground offers that one as the
  button; sorted alphabetically, `books.toscrape.com` led with `a::attr(href)`.

## 1.1.3 — 2026-09-09

### Added
- **`/bytecrawl` as a slash command.** The agent skill was only ever usable by
  pasting `Read and follow <url>`, which applies for one turn and is forgotten
  by the next. It already had the frontmatter a Claude Code skill needs but no
  install path, so one command now puts it in `~/.claude/skills/` and it is
  there in every session, with the agent reaching for it on its own. Same file
  the site serves — nothing to keep in sync.
- Invoked bare, `/bytecrawl` now asks what you want instead of reading its own
  documentation back at you. The six options are named by what you get — "find
  everything on a site about a topic", "get the data behind a page" — with the
  technical name in parentheses for whoever wants it: someone who needs a JSON
  endpoint does not recognise "hit a hidden JSON API", and someone who wants a
  price off a listing does not know what a CSS selector is. It asks in whatever
  language you wrote in. Invoked with a task, it skips the question and does it.
- The skill now tells the agent **how to run and present a crawl**, which it
  never covered. A crawl is the one slow thing here — 8 seconds for 10 pages,
  half a minute for 20 — and nothing streams progress, so it now states the
  budget and the wait before starting. It defaults to 20 pages, reads
  `stats.requests` to see whether the hosted cap clamped the request instead of
  reporting the number it asked for, and shows the ranking as titles, URLs and
  relevance plus one line of stats — including `frontier_left`, the URLs found
  but never visited, which is what tells you a bigger budget would find more.
  It also warns that relevance is cosine similarity, so short pages whose title
  repeats the query score highest and Wikipedia category pages tend to top the
  ranking.
- The skill now says **what to ask for**. It documented four surfaces and eight
  API methods without a single example of a request a person would make, so it
  told an agent how to call things and told a reader nothing.

### Changed
- The skill's `description` is one line instead of five. That field is what an
  agent reads to decide whether the skill applies, so it now says what it does
  and when to use it rather than describing the product.

## 1.1.2 — 2026-09-09

### Fixed
- **The agent skill sent agents to a repo that 404s.** `SKILL.md` — the file
  handed to an agent as the entry point — pointed at a GitHub URL that does not
  exist, so anything that went looking for the source or an issue tracker hit a
  dead end.
- **It documented API response fields that no method returns.** The skill
  promised `status` and `elapsed`; every response actually carries `url` and
  `method`, which were undocumented, and `compare` was not documented at all.
  The troubleshooting steps then told you to read `page.status` to diagnose a
  failed call — so the first debugging move the skill taught did not work over
  HTTP.

### Added
- A smoke suite against the deployed site (`pytest -m smoke`, excluded from CI
  like the browser tests). Every bug in this release and the last was invisible
  to the offline suite: they lived in the gap between what the project says and
  what the deploy does. These check that the skill's links resolve, that the
  API returns the fields it documents, that the hosted MCP server lists its six
  tools, and that the SSRF guard is live.

## 1.1.1 — 2026-09-09

### Fixed
- **The hosted MCP endpoint answered every request with `421 Invalid Host
  header`.** The transport enables DNS-rebinding protection whenever the app is
  built for its default `127.0.0.1` host, and then allows only localhost — so
  nothing reaching `bytecrawl.vercel.app` got through. That protection is for a
  server bound to your own machine; this one is public, unauthenticated and
  already behind an SSRF guard, so it now ships open. Set
  `BYTECRAWL_ALLOWED_HOSTS` (and `BYTECRAWL_ALLOWED_ORIGINS`) to turn it back on
  if you self-host on a domain that also serves authenticated apps.

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
