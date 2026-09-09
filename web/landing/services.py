"""Scraping/crawling orchestration behind the demo routes, plus the tiny
per-instance response cache.

The route handlers stay about HTTP (parse the request, pick a status code,
jsonify); everything that actually drives ByteCrawl lives here and returns
plain dicts. ``analyze_url`` and ``run_crawl`` return ``(payload, status,
analytics_props)`` — the route tracks ``analytics_props`` when it is not
``None``; ``run_api_method`` returns a payload dict and raises ``ValueError``
for bad input (which the route maps to 400).
"""

from __future__ import annotations

import re
import time

from bytecrawl import Scraper
from bytecrawl.crawler import STRATEGIES as CRAWL_STRATEGIES
from bytecrawl.crawler import compare, pagerank
from bytecrawl.security import assert_public_url  # re-exported for the routes
from landing.content import ANALYZE_I18N

__all__ = [
    "API_MAX_PAGES", "API_MAX_COMPARE_PAGES", "assert_public_url",
    "cache_get", "cache_put", "clean_url",
    "analyze_url", "run_crawl", "run_api_method",
]

API_MAX_PAGES = 10  # hard cap for the public crawl endpoint
# compare runs three crawls behind one request, so it gets a smaller
# per-strategy budget: 3 x 6 = 18 fetches, about two crawls' worth.
API_MAX_COMPARE_PAGES = 6


# The landing runs a demo crawl on load, so the same handful of queries repeat
# all day. Serving those from a short-lived cache keeps the page instant and
# spares the practice sites a burst of identical crawls. Per-instance and
# best-effort on serverless, which is all this needs to be.
_API_CACHE: dict[str, tuple[float, dict]] = {}
_API_CACHE_TTL = 600  # seconds
_API_CACHE_MAX = 64


def cache_get(key: str):
    hit = _API_CACHE.get(key)
    if not hit:
        return None
    born, payload = hit
    if time.time() - born > _API_CACHE_TTL:
        _API_CACHE.pop(key, None)
        return None
    return payload


def cache_put(key: str, payload: dict):
    if len(_API_CACHE) >= _API_CACHE_MAX:  # drop the oldest entry
        _API_CACHE.pop(min(_API_CACHE, key=lambda k: _API_CACHE[k][0]), None)
    _API_CACHE[key] = (time.time(), payload)


def clean_url(raw: str) -> str:
    """Tolerate URLs pasted out of prose: 'site.com · query: x' -> 'https://site.com'."""
    url = re.split(r"[\s·|,]", raw.strip())[0]
    url = re.sub(r"""[.,;:·)\]}'"]+$""", "", url)
    if url and "://" not in url:
        url = "https://" + url
    return url


def analyze_url(url: str, lang: str) -> tuple[dict, int, dict | None]:
    """Run the 'auto' strategy on a URL and explain what it did and why.

    Returns (payload, http_status, analytics_props). analytics_props is None
    when nothing should be tracked (bad URL, download failure).
    """
    tr = ANALYZE_I18N.get(lang, ANALYZE_I18N["en"])
    if not url.startswith(("http://", "https://")):
        return {"ok": False, "error": tr["bad_url"]}, 400, None

    bot = Scraper(timeout=20)
    steps = []
    try:
        page = bot.static(url)
    except Exception as e:
        return {"ok": False, "error": tr["download_err"].format(e=e)}, 200, None

    text = page.soup.get_text(strip=True)
    length = len(text)
    steps.append({
        "title": tr["s1_t"],
        "detail": tr["s1_d"].format(status=page.status, elapsed=page.elapsed, chars=length),
    })

    used_browser = False
    chromium_missing = False
    if length < 200:
        try:
            page = bot.browser(url)
            used_browser = True
            steps.append({
                "title": tr["s2_browser_t"],
                "detail": tr["s2_browser_d"].format(elapsed=page.elapsed),
            })
        except Exception:
            # Vercel has no Chromium (nor a Playwright binary). Any failure
            # opening the browser -> fall back to "static only".
            chromium_missing = True
            steps.append({
                "title": tr["s2_missing_t"],
                "detail": tr["s2_missing_d"],
            })

    if used_browser:
        why = tr["why_browser"]
    elif chromium_missing:
        why = tr["why_missing"]
    else:
        why = tr["why_static"]

    md = ""
    md_tokens = None
    try:
        md = page.markdown()
        md_tokens = page.tokens(of=md)
    except Exception:
        pass

    props = {
        "method_used": page.method,
        "used_browser": used_browser,
        "chromium_missing": chromium_missing,
        "steps_count": len(steps),
        "has_markdown": bool(md),
        "token_reduction_ratio": round(md_tokens / page.tokens(), 2) if md_tokens else None,
    }
    payload = {
        "ok": True,
        "url": url,
        "method": page.method,
        "steps": steps,
        "why": why,
        "title": page.css("title") or tr["no_title"],
        "links": len(page.links()),
        "tokens_html": page.tokens(),
        "tokens_md": md_tokens,
        "sample_md": md,
    }
    return payload, 200, props


def run_crawl(url: str, strategy: str, query: str) -> tuple[dict, int, dict | None]:
    """Run ONE crawl strategy (the frontend compares by calling 3 in parallel).

    20 pages needs maxDuration=60 in vercel.json; no delay between requests
    to stay well inside the window. Returns (payload, http_status, props).
    """
    if not url.startswith(("http://", "https://")):
        return {"ok": False, "error": "URL must start with http:// or https://"}, 400, None
    if strategy not in CRAWL_STRATEGIES:
        return {"ok": False, "error": "unknown strategy"}, 400, None

    try:
        crawler = CRAWL_STRATEGIES[strategy](query=query, delay=0.0, timeout=6)
        result = crawler.crawl(url, max_pages=20, max_depth=4)
    except Exception as e:
        return {"ok": False, "error": f"crawl failed: {e}"}, 200, None

    pr = pagerank(result.graph)
    props = {"strategy": strategy, **result.stats}
    payload = {
        "ok": True,
        "strategy": strategy,
        "pages": result.pages,
        "stats": result.stats,
        "pagerank": [{"url": u, "score": round(s, 4)} for u, s in list(pr.items())[:5]],
    }
    return payload, 200, props


def run_api_method(method: str, url: str, src) -> dict:
    """Dispatch one /api call to ByteCrawl and return its payload dict.

    ``src`` is the request's arg/form mapping (anything with ``.get``). Bad
    input raises ValueError (the route maps it to 400); everything else
    propagates for the route to turn into a 502.
    """
    bot = Scraper(timeout=15)
    if method in ("markdown", "md"):
        page = bot.static(url)
        return {"url": url, "method": "markdown",
                "markdown": page.markdown(),
                "tokens": page.tokens(page.markdown())}
    if method == "text":
        page = bot.static(url)
        return {"url": url, "method": "text",
                "text": page.soup.get_text(" ", strip=True)}
    if method == "html":
        page = bot.static(url)
        return {"url": url, "method": "html", "html": page.html}
    if method == "links":
        page = bot.static(url)
        return {"url": url, "method": "links", "links": page.links()}
    if method == "json":
        page = bot.api(url)
        return {"url": url, "method": "json", "data": page.json()}
    if method == "extract":
        select = (src.get("select") or "").strip()
        page = bot.static(url)
        if not select:
            # No selector is not an error, it is the question before it:
            # "what can I pull off this page?" Answering with the repeated
            # blocks lets the next call be a real extraction.
            return {"url": url, "method": "extract", "candidates": page.selectors()}
        return {"url": url, "method": "extract", "select": select,
                "values": page.css_all(select)}
    if method in ("crawl", "shark", "opic", "bfs"):
        strategy = method if method in CRAWL_STRATEGIES else \
            (src.get("strategy") or "shark").lower()
        if strategy not in CRAWL_STRATEGIES:
            raise ValueError(f"unknown strategy '{strategy}'")
        query = (src.get("query") or "").strip()
        try:
            pages = min(int(src.get("pages", API_MAX_PAGES)), API_MAX_PAGES)
        except ValueError:
            pages = API_MAX_PAGES
        crawler = CRAWL_STRATEGIES[strategy](query=query, delay=0.0, timeout=8)
        result = crawler.crawl(url, max_pages=pages, max_depth=4)
        ranked = result.top(pages) if query else result.pages
        return {"url": url, "method": "crawl", "strategy": strategy,
                "query": query, "stats": result.stats, "pages": ranked}
    if method == "compare":
        query = (src.get("query") or "").strip()
        if not query:
            raise ValueError("method=compare needs a 'query' — with "
                             "nothing to be relevant to the three "
                             "strategies aren't comparable")
        try:
            pages = min(int(src.get("pages", API_MAX_COMPARE_PAGES)),
                        API_MAX_COMPARE_PAGES)
        except ValueError:
            pages = API_MAX_COMPARE_PAGES
        # The playground fires three /crawl requests in parallel from the
        # browser; a single API call has to do that fan-out itself or it
        # would take three times as long as one crawl.
        out = compare(url, query, max_pages=pages, delay=0.0, timeout=8)
        return {"url": url, "method": "compare", "query": query,
                "strategies": out["strategies"], "winner": out["winner"],
                "tied": out["tied"]}
    raise ValueError(f"unknown method '{method}'")
