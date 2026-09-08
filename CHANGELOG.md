# Changelog

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
