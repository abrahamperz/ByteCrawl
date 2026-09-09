---
name: bytecrawl
description: |
  ByteCrawl gives agents clean Markdown from any page, typed extraction
  with CSS selectors, and focused crawling that ranks pages by topic
  (Shark-Search, OPIC, BFS) instead of walking a site blindly. Use this
  skill to pick the path that matches the work: a hosted API with no
  install, an MCP connection, or the Python library.
---

# ByteCrawl

ByteCrawl turns web pages into LLM-ready context. Three things it does that a
plain fetch does not: it strips boilerplate down to clean Markdown (~6x fewer
tokens), it extracts typed records with CSS selectors, and it crawls a site
under a request budget while ranking what to visit next by how relevant it is
to your topic.

Source: https://github.com/abrahamperz/ByteCrawl · PyPI: `bytecrawl` · MIT

## Choose your path

- **Need page content right now, install nothing** → Path A (hosted API)
- **Your client speaks MCP** → Path B
- **You are writing Python app code** → Path C
- **The page is JavaScript-rendered and comes back empty** → Path D (browser)

No API key, no account, no sign-up on any path.

---

## Path A: Hosted API (no install)

One GET. Everything except `url` is optional.

```bash
curl "https://bytecrawl.vercel.app/api?url=books.toscrape.com"
```

Every response carries `url` and `method` (`static`, `browser` or `api` — the
strategy that actually ran), plus the payload for what you asked for:

| method | you also get |
|---|---|
| markdown (default) | `markdown`, `tokens` |
| text / html | `text` / `html` |
| links | `links` |
| json | `data` |
| extract | `values`, `select` |
| crawl | `pages`, `stats`, `query`, `strategy` |
| compare | `strategies`, `winner`, `tied`, `query` |

There is no `status` field: a fetch that fails comes back as `error` instead.

| Goal | Call |
|---|---|
| Clean Markdown (default) | `?url=SITE` |
| Plain text | `?url=SITE&method=text` |
| Raw HTML | `?url=SITE&method=html` |
| All links | `?url=SITE&method=links` |
| A JSON endpoint | `?url=SITE&method=json` |
| Typed extraction | `?url=SITE&method=extract&select=h3 a::attr(title)` |
| Focused crawl | `?url=SITE&method=crawl&query=TOPIC&strategy=shark` |
| Compare all three strategies | `?url=SITE&method=compare&query=TOPIC` |

Crawl params: `strategy` = `shark` (default) \| `opic` \| `bfs`, `pages` ≤ 10.
Selector syntax: `div.price::text`, `a::attr(href)`, or a bare selector for the
element's text.

Limits: static HTML only, 10 pages per crawl, rate-limited, responses cached
10 minutes. Private and loopback addresses are refused. If you need a real
browser or a bigger budget, go to Path C.

---

## Path B: MCP

Hosted, nothing to install:

```bash
claude mcp add --transport http bytecrawl https://bytecrawl.vercel.app/mcp
```

Local (stdio), if you want no request cap and browser support:

```bash
pip install "bytecrawl[mcp]"
claude mcp add bytecrawl -- bytecrawl-mcp
```

Or in any MCP client config:

```json
{"mcpServers": {"bytecrawl": {"command": "bytecrawl-mcp"}}}
```

The local server needs Python 3.10+ (the `mcp` package floor). The hosted one
has no such requirement — it is just HTTP.

Both expose six tools:

- `fetch_markdown(url)` — clean Markdown plus a token count
- `extract(url, item, fields)` — typed records from repeated blocks;
  or `extract(url, select)` for a flat list of one selector's values
- `list_links(url)` — every outbound link, absolute and deduplicated
- `focused_crawl(url, query, strategy, max_pages)` — ranked pages
- `compare_strategies(url, query, max_pages)` — all three strategies on one
  budget, side by side, with the winner (and `tied` when nothing separates
  them). Three crawls: reach for `focused_crawl` when you just want pages
- `fetch_json_api(url)` — parsed JSON from an endpoint

---

## Path C: Python library

```bash
pip install bytecrawl
```

The core has three dependencies (`requests`, `beautifulsoup4`, `lxml`).
Add what you actually need:

| Extra | Command | Unlocks |
|---|---|---|
| Markdown | `pip install "bytecrawl[llm]"` | `page.markdown()`, `page.tokens()` |
| Browser | `pip install "bytecrawl[browser]"` | `Scraper.browser()` — see Path D |
| MCP | `pip install "bytecrawl[mcp]"` | the local `bytecrawl-mcp` server (Python 3.10+) |
| Everything | `pip install "bytecrawl[all]"` | all of the above |

A missing extra never fails silently: each one raises an ImportError naming the
exact command to run.

```python
from bytecrawl import Scraper, SharkSearch

bot = Scraper(delay=0.5)          # delay is politeness, use it

page = bot.fetch(url)             # auto: static HTML, browser only if needed
page.markdown()                   # LLM-ready text
page.links()                      # every link, absolute
page.css("h1::text")              # one value
page.extract(item="div.quote", fields={
    "quote": "span.text::text",
    "author": "small.author::text",
    "tags[]": "a.tag::text",      # [] suffix collects a list
})

# Follow pagination and extract as you go
bot.crawl(url, item="div.quote", fields={...},
          next_page="li.next a::attr(href)", pages=3)

# Crawl a whole site under a budget, ranked by topic
result = SharkSearch(query="machine learning", delay=0.5).crawl(url, max_pages=50)
result.top(10)          # highest-relevance pages
result.relevant(0.1)    # everything above a threshold
result.stats            # requests, errors, elapsed
```

`page.method` tells you which strategy actually ran (`static`, `browser`,
`api`). Check it when a result looks wrong.

---

## Path D: JavaScript-rendered pages (install the browser)

`bot.fetch(url)` always tries static HTML first, and escalates to a real
browser only when the page comes back with under 200 characters of text — the
signature of a client-rendered SPA. That escalation needs a browser on the
machine, and it is not installed by default.

**Install it the first time you hit a JS-rendered page:**

```bash
pip install "bytecrawl[browser]"
playwright install chromium
```

The second command downloads Chromium (~150 MB) and is the one people forget.
Without it, `browser()` raises an ImportError telling you to run exactly that.

```python
page = bot.fetch(url)        # auto: escalates on its own
page = bot.browser(url)      # force the browser
page = bot.browser(url, wait=".results", scroll=True)   # wait for a selector, lazy-load
print(page.method)           # "static" or "browser" — always check
```

Under the hood this is Playwright driving headless Chromium over CDP, the same
protocol Puppeteer uses. If you already run Node, you do not need Puppeteer as
well; one browser is enough.

**The hosted API (Path A) cannot do this.** It runs on serverless with no
Chromium binary, so JS-rendered pages return their empty static HTML. Browser
rendering requires Path C on your own machine or a container.

---

## Choosing a crawl strategy

All three share one loop (pop → fetch → score links → push), so the same
budget across strategies is a fair comparison.

| Strategy | Ranks the frontier by | Use when |
|---|---|---|
| `SharkSearch` | Topic similarity, inherited by children with decay | You know the topic. Best default. |
| `OPIC` | Importance — cash flowing along links | You want the hubs, no topic in mind |
| `BFS` | Distance from the seed | You want even coverage, or a baseline |

### Picking one explicitly

Every surface takes the same three names — `shark` (default), `opic`, `bfs`:

| Surface | How |
|---|---|
| API | `?method=crawl&query=TOPIC&strategy=opic` (or `?method=opic` as a shorthand) |
| MCP | `focused_crawl(url, query, strategy="opic", max_pages=20)` |
| Python | Instantiate the class: `OPIC(delay=0.5).crawl(url, max_pages=50)` |

An unknown name is rejected, not silently defaulted: the API returns 400 and the
MCP tool raises `ValueError` listing the valid names.

`SharkSearch` requires `query` — without a topic it has nothing to rank, so it is
a required argument, not an optional one. `BFS` and `OPIC` take `query` too, but
only to score the pages in the result; it does not change their traversal order.

```python
from bytecrawl import BFS, OPIC, SharkSearch, pagerank

result = SharkSearch(query="san francisco", delay=0.5).crawl(url, max_pages=20)
result.relevant(0.1)       # pages above a relevance threshold
pagerank(result.graph)     # offline importance, to compare against OPIC
```

### What the choice actually buys you

Measured from `en.wikipedia.org/wiki/Silicon_Valley`, query `san francisco`,
20 pages and 20 requests each:

| Strategy | Pages over 0.1 relevance | Top page | Mean of top 5 |
|---|---|---|---|
| `shark` | 20 | 0.7774 | 0.6523 |
| `opic` | 4 | 0.2799 | 0.1715 |
| `bfs` | 1 | 0.1068 | 0.0733 |

Reproduce it with `result.relevant(0.1)` on each. All three spent the same 20
requests; only the order changed. Shark's best page scores 7.3x BFS's and its
top five average 8.9x. A lower threshold will not rescue BFS here: 20 pages
against Wikipedia leaves thousands of URLs still queued (3.8k for Shark, 8.6k
for BFS, 16.8k for OPIC), so coverage never converges. That is the case worth
designing for — on a site small enough to exhaust, the ordering barely matters.

### Tuning SharkSearch (optional)

Two parameters from the original paper, both exposed:

```python
SharkSearch(query="san francisco", delta=0.5, gamma=0.8)
```

- `delta` (0.5) — how fast a branch with no signal fades. The decay is `δⁿ` with
  depth, so 0.3 abandons unpromising branches faster and 0.7 gives them longer.
- `gamma` (0.8) — how much a link's score comes from its parent versus its own
  anchor text: `score = γ·inherited + (1−γ)·local`. Lower it when anchor text on
  the target site is descriptive and you trust it more than the site structure.

Defaults are reasonable; change them only if a crawl is drifting off-topic
(lower `delta`) or ignoring obviously relevant links (lower `gamma`).

## Etiquette and limits

- Always pass `delay=` (0.5s is a reasonable floor). The default is 0.
- Check `robots.txt` and terms of service before crawling a site you do not own.
- `max_pages` is a hard budget; there is no unbounded crawl.
- Crawls stay on the seed's root domain unless you pass `same_domain=False`.
- The hosted API refuses private, loopback, and link-local addresses.

Practice sites that allow scraping: `books.toscrape.com`, `quotes.toscrape.com`
(and `quotes.toscrape.com/js/` for a JS-rendered page to test Path D).

## When something looks wrong

1. Check which strategy ran before anything else — most surprises are a 403
   or a page that needed the browser. On Path C that is `page.method` and
   `page.status`; over the API it is the `method` field (the API does not
   return a status, so a failed fetch comes back as an `error` instead).
2. Empty Markdown with `method="static"` → the page is JS-rendered, go to Path D.
3. `extract()` returns empty → the selector is wrong. Fetch `page.html` and
   check the real markup before changing anything else.
4. A crawl returns nothing relevant → your `query` shares no vocabulary with
   the site. Relevance is cosine similarity over the page text and URL path.
