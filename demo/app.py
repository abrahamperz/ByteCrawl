"""
Web dashboard for ByteCrawl: landing, methods, playground, docs, plus the
public /api endpoint and the /analyze and /crawl demos behind them.

Run:  python app.py   ->  open http://127.0.0.1:5000
"""

import atexit
import os
import re
import sys
import time
import uuid
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, render_template, request, session
from posthog import Posthog

BASE = Path(__file__).parent
EXAMPLES = BASE.parent / "examples"

sys.path.insert(0, str(BASE.parent))
import bytecrawl
from bytecrawl import Scraper
from bytecrawl.crawler import STRATEGIES as CRAWL_STRATEGIES
from bytecrawl.crawler import compare, pagerank
from bytecrawl.security import assert_public_url

load_dotenv()

posthog_client = Posthog(
    project_api_key=os.environ.get("POSTHOG_PROJECT_TOKEN", ""),
    host=os.environ.get("POSTHOG_HOST", "https://us.i.posthog.com"),
    enable_exception_autocapture=True,
)
atexit.register(posthog_client.shutdown)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "bytecrawl-dev-secret")
# Flask sorts JSON keys by default, which throws away orderings that mean
# something: the discovered fields come back ranked with the most useful
# selector first, and the playground offers exactly that one as the button.
# Sorted alphabetically, books.toscrape.com leads with `a::attr(href)`.
app.json.sort_keys = False


def _get_distinct_id() -> str:
    if "distinct_id" not in session:
        session["distinct_id"] = str(uuid.uuid4())
    return session["distinct_id"]


@app.after_request
def _flush_posthog(response):
    # On serverless (Vercel) the function freezes after responding and
    # posthog-python's background send can get lost: force the flush.
    # It must never break the response if PostHog fails (network, empty token, etc.).
    try:
        posthog_client.flush()
    except Exception:
        pass
    return response


# Each scraping technique: what it does, where to practise it, and how to
# call it through the public /api endpoint (None when the API cannot host it).
TECHNIQUES = {
    "static": {
        "title": "1 · Static HTML",
        "subtitle": "requests + BeautifulSoup",
        "site": "books.toscrape.com",
        "api": "?method=html",
        "description": "The server sends the full HTML. We fetch it and parse it with CSS selectors.",
    },
    "dynamic": {
        "title": "2 · Dynamic JS",
        "subtitle": "Playwright (real browser)",
        "site": "quotes.toscrape.com/js",
        "api": None,   # needs a real browser; not available on serverless
        "description": "JS fills the page. We launch a real browser and read the rendered DOM.",
    },
    "api": {
        "title": "3 · Intercepted API",
        "subtitle": "requests → JSON",
        "site": "quotes.toscrape.com/api",
        "api": "?method=json",
        "description": "Behind the JS there's an API with clean JSON. We hit it and skip the HTML.",
    },
    "crawl": {
        "title": "4 · Crawling at scale",
        "subtitle": "pagination + graph crawlers",
        "site": "quotes.toscrape.com",
        "description": "Hundreds of pages: walk a 'next' chain, or let BFS / Shark-Search / OPIC "
                       "order a whole site under a request budget.",
        "api": "?method=crawl&query=san+francisco",
    },
    "login": {
        "title": "5 · API with login",
        "subtitle": "session + CSRF token",
        "site": "quotes.toscrape.com/login",
        "api": None,   # needs credentials; local library only
        "description": "Data behind a login. We reuse the session cookie/token on every request.",
    },
    "markdown": {
        "title": "Extra · HTML → Markdown",
        "subtitle": "token savings for LLMs",
        "site": "quotes.toscrape.com",
        "api": "?method=markdown",
        "description": "Turns noisy HTML into clean Markdown: same info, a fraction of the tokens.",
    },
}


@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/agent-onboarding/SKILL.md")
def agent_skill():
    """Served as raw text/markdown so an agent handed the URL can just read it.

    render_template would try to parse Jinja braces in the code samples, so
    read the file straight off disk instead.

    One wrinkle: Chrome downloads `text/markdown` rather than rendering it, so
    a human clicking the link from /docs would get a file instead of the text.
    Browsers announce `Accept: text/html,...`; agents and curl do not. Serve
    them text/plain so the page just opens, and keep the correct Markdown type
    for everyone else.
    """
    skill = Path(app.static_folder) / "SKILL.md"
    from_browser = "text/html" in request.headers.get("Accept", "")
    return app.response_class(
        skill.read_text(encoding="utf-8"),
        mimetype="text/plain" if from_browser else "text/markdown",
        headers={
            "Cache-Control": "public, max-age=300",
            "Content-Disposition": "inline",
            "Vary": "Accept",
        },
    )


@app.route("/methods")
def methods():
    return render_template("index.html", techniques=TECHNIQUES)


@app.route("/playground")
def playground():
    return render_template("try.html", techniques=TECHNIQUES)


@app.route("/try")
def try_redirect():
    """The playground used to live at /try; links to it are already out there.

    308 rather than 302 so the redirect is cached and the query string
    (?url=… deep links from the landing page) survives.
    """
    qs = request.query_string.decode()
    return redirect("/playground" + ("?" + qs if qs else ""), code=308)


ANALYZE_I18N = {
    "en": {
        "bad_url": "Enter a URL that starts with http:// or https://",
        "download_err": "Could not download the page: {e}",
        "s1_t": "1 · Tried static HTML",
        "s1_d": "Fetched the page with requests (no browser). Status {status}, "
                "{elapsed}s, {chars} characters of visible text.",
        "s2_browser_t": "2 · Switched to a real browser",
        "s2_browser_d": "The HTML came back nearly empty, so I launched Chromium (Playwright) "
                        "and read the DOM already rendered by JavaScript. {elapsed}s.",
        "s2_missing_t": "2 · Wanted to use a browser",
        "s2_missing_d": "The HTML came back nearly empty (typical of an SPA), but Chromium isn't "
                        "installed. Run 'playwright install chromium' to enable this step.",
        "why_browser": "The static HTML had fewer than 200 characters of text: a typical sign of a page "
                       "that fills itself with JavaScript. So I dropped the fast path and opened a real "
                       "browser to see the final content.",
        "why_missing": "The page seems to need JavaScript, but Chromium is missing. I'm still showing "
                       "what did come through via static HTML.",
        "why_static": "The static HTML already had all the content, so no browser was needed. It's the "
                      "fastest, cheapest path: a single HTTP request, no Chromium.",
        "no_title": "(no title)",
    },
    "es": {
        "bad_url": "Escribe una URL que empiece con http:// o https://",
        "download_err": "No se pudo descargar la página: {e}",
        "s1_t": "1 · Probé HTML estático",
        "s1_d": "Pedí la página con requests (sin navegador). Estado {status}, "
                "{elapsed}s, {chars} caracteres de texto visible.",
        "s2_browser_t": "2 · Cambié a un navegador real",
        "s2_browser_d": "El HTML volvió casi vacío, así que lancé Chromium (Playwright) "
                        "y leí el DOM ya renderizado por JavaScript. {elapsed}s.",
        "s2_missing_t": "2 · Quería usar un navegador",
        "s2_missing_d": "El HTML volvió casi vacío (típico de una SPA), pero Chromium no está "
                        "instalado. Corre 'playwright install chromium' para habilitar este paso.",
        "why_browser": "El HTML estático tenía menos de 200 caracteres de texto: señal típica de una página "
                       "que se rellena con JavaScript. Así que dejé la vía rápida y abrí un navegador real "
                       "para ver el contenido final.",
        "why_missing": "La página parece necesitar JavaScript, pero falta Chromium. Aun así muestro "
                       "lo que sí llegó por HTML estático.",
        "why_static": "El HTML estático ya tenía todo el contenido, así que no hizo falta navegador. Es la "
                      "vía más rápida y barata: una sola petición HTTP, sin Chromium.",
        "no_title": "(sin título)",
    },
    "pt": {
        "bad_url": "Digite uma URL que comece com http:// ou https://",
        "download_err": "Não foi possível baixar a página: {e}",
        "s1_t": "1 · Tentei HTML estático",
        "s1_d": "Busquei a página com requests (sem navegador). Status {status}, "
                "{elapsed}s, {chars} caracteres de texto visível.",
        "s2_browser_t": "2 · Mudei para um navegador real",
        "s2_browser_d": "O HTML voltou quase vazio, então lancei o Chromium (Playwright) "
                        "e li o DOM já renderizado pelo JavaScript. {elapsed}s.",
        "s2_missing_t": "2 · Queria usar um navegador",
        "s2_missing_d": "O HTML voltou quase vazio (típico de uma SPA), mas o Chromium não está "
                        "instalado. Rode 'playwright install chromium' para habilitar este passo.",
        "why_browser": "O HTML estático tinha menos de 200 caracteres de texto: sinal típico de uma página "
                       "que se preenche com JavaScript. Então abandonei o caminho rápido e abri um navegador "
                       "real para ver o conteúdo final.",
        "why_missing": "A página parece precisar de JavaScript, mas falta o Chromium. Ainda assim mostro "
                       "o que veio pelo HTML estático.",
        "why_static": "O HTML estático já tinha todo o conteúdo, então não foi preciso navegador. É o "
                      "caminho mais rápido e barato: uma única requisição HTTP, sem Chromium.",
        "no_title": "(sem título)",
    },
}


@app.route("/analyze", methods=["POST"])
def analyze():
    """Runs the 'auto' strategy on a URL and explains what it did and why."""
    body = request.json or {}
    lang = body.get("lang", "en")
    tr = ANALYZE_I18N.get(lang, ANALYZE_I18N["en"])
    url = body.get("url", "").strip()
    if not url.startswith(("http://", "https://")):
        return jsonify({"ok": False, "error": tr["bad_url"]}), 400

    bot = Scraper(timeout=20)
    steps = []
    try:
        page = bot.static(url)
    except Exception as e:
        return jsonify({"ok": False, "error": tr["download_err"].format(e=e)})

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

    try:
        posthog_client.capture(
            _get_distinct_id(),
            "url_analyzed",
            properties={
                "method_used": page.method,
                "used_browser": used_browser,
                "chromium_missing": chromium_missing,
                "steps_count": len(steps),
                "has_markdown": bool(md),
                "token_reduction_ratio": round(md_tokens / page.tokens(), 2) if md_tokens else None,
            },
        )
    except Exception:
        pass
    return jsonify({
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
    })


@app.route("/crawl", methods=["POST"])
def crawl():
    """Runs ONE crawl strategy (the frontend compares by calling 3 in parallel).

    20 pages needs maxDuration=60 in vercel.json; no delay between requests
    to stay well inside the window.
    """
    body = request.json or {}
    url = body.get("url", "").strip()
    strategy = body.get("strategy", "bfs")
    query = body.get("query", "").strip()

    if not url.startswith(("http://", "https://")):
        return jsonify({"ok": False, "error": "URL must start with http:// or https://"}), 400
    if strategy not in CRAWL_STRATEGIES:
        return jsonify({"ok": False, "error": "unknown strategy"}), 400

    try:
        crawler = CRAWL_STRATEGIES[strategy](query=query, delay=0.0, timeout=6)
        result = crawler.crawl(url, max_pages=20, max_depth=4)
    except Exception as e:
        return jsonify({"ok": False, "error": f"crawl failed: {e}"})

    pr = pagerank(result.graph)
    try:
        posthog_client.capture(
            _get_distinct_id(),
            "crawl_strategy_run",
            properties={"strategy": strategy, **result.stats},
        )
    except Exception:
        pass

    return jsonify({
        "ok": True,
        "strategy": strategy,
        "pages": result.pages,
        "stats": result.stats,
        "pagerank": [{"url": u, "score": round(s, 4)} for u, s in list(pr.items())[:5]],
    })


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


def _cache_get(key: str):
    hit = _API_CACHE.get(key)
    if not hit:
        return None
    born, payload = hit
    if time.time() - born > _API_CACHE_TTL:
        _API_CACHE.pop(key, None)
        return None
    return payload


def _cache_put(key: str, payload: dict):
    if len(_API_CACHE) >= _API_CACHE_MAX:  # drop the oldest entry
        _API_CACHE.pop(min(_API_CACHE, key=lambda k: _API_CACHE[k][0]), None)
    _API_CACHE[key] = (time.time(), payload)


def _ok(cache_key: str, payload: dict):
    """Cache a successful result and return it. Errors are never cached."""
    _cache_put(cache_key, payload)
    return jsonify(payload)


def _clean_url(raw: str) -> str:
    """Tolerate URLs pasted out of prose: 'site.com · query: x' -> 'https://site.com'."""
    url = re.split(r"[\s·|,]", raw.strip())[0]
    url = re.sub(r"""[.,;:·)\]}'"]+$""", "", url)
    if url and "://" not in url:
        url = "https://" + url
    return url


@app.route("/api", methods=["GET", "POST"])
def api():
    """Dead-simple one-call HTTP API. Everything but `url` is optional.

      /api?url=quotes.toscrape.com                          -> clean Markdown
      /api?url=quotes.toscrape.com&method=text              -> plain text
      /api?url=…&method=extract&select=h3 a::attr(title)    -> matched values
      /api?url=…&method=json                                -> a JSON endpoint
      /api?url=…&method=crawl&query=san+francisco&strategy=shark  -> focused crawl
      /api?url=…&method=compare&query=san+francisco         -> all 3 strategies

    method:   markdown (default) | text | html | extract | links | json |
              crawl | compare
    query:    topic to rank pages by (method=crawl / compare)
    select:   a CSS selector to scrape (method=extract; ::text / ::attr(x))
    strategy: shark (default) | opic | bfs   ·   pages: crawl budget (<=10)

    Static-only and SSRF-guarded; crawls are capped at 10 pages, and compare
    (three crawls in one call) at API_MAX_COMPARE_PAGES per strategy.
    """
    src = request.args if request.method == "GET" else (request.form or request.args)
    url = _clean_url(src.get("url") or "")
    if not url:
        return jsonify({"error": "the 'url' parameter is required"}), 400
    try:
        assert_public_url(url)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    method = (src.get("method") or "markdown").lower()
    cache_key = "|".join([url, method, src.get("query", ""), src.get("select", ""),
                          src.get("strategy", ""), str(src.get("pages", ""))])
    cached = _cache_get(cache_key)
    if cached is not None:
        return jsonify(cached)

    bot = Scraper(timeout=15)
    try:
        if method in ("markdown", "md"):
            page = bot.static(url)
            return _ok(cache_key, {"url": url, "method": "markdown",
                            "markdown": page.markdown(),
                            "tokens": page.tokens(page.markdown())})
        if method == "text":
            page = bot.static(url)
            return _ok(cache_key, {"url": url, "method": "text",
                            "text": page.soup.get_text(" ", strip=True)})
        if method == "html":
            page = bot.static(url)
            return _ok(cache_key, {"url": url, "method": "html", "html": page.html})
        if method == "links":
            page = bot.static(url)
            return _ok(cache_key, {"url": url, "method": "links", "links": page.links()})
        if method == "json":
            page = bot.api(url)
            return _ok(cache_key, {"url": url, "method": "json", "data": page.json()})
        if method == "extract":
            select = (src.get("select") or "").strip()
            page = bot.static(url)
            if not select:
                # No selector is not an error, it is the question before it:
                # "what can I pull off this page?" Answering with the repeated
                # blocks lets the next call be a real extraction.
                return _ok(cache_key, {"url": url, "method": "extract",
                                "candidates": page.selectors()})
            return _ok(cache_key, {"url": url, "method": "extract", "select": select,
                            "values": page.css_all(select)})
        if method in ("crawl", "shark", "opic", "bfs"):
            strategy = method if method in CRAWL_STRATEGIES else \
                (src.get("strategy") or "shark").lower()
            if strategy not in CRAWL_STRATEGIES:
                return jsonify({"error": f"unknown strategy '{strategy}'"}), 400
            query = (src.get("query") or "").strip()
            try:
                pages = min(int(src.get("pages", API_MAX_PAGES)), API_MAX_PAGES)
            except ValueError:
                pages = API_MAX_PAGES
            crawler = CRAWL_STRATEGIES[strategy](query=query, delay=0.0, timeout=8)
            result = crawler.crawl(url, max_pages=pages, max_depth=4)
            ranked = result.top(pages) if query else result.pages
            return _ok(cache_key, {"url": url, "method": "crawl", "strategy": strategy,
                            "query": query, "stats": result.stats, "pages": ranked})
        if method == "compare":
            query = (src.get("query") or "").strip()
            if not query:
                return jsonify({"error": "method=compare needs a 'query' — with "
                                         "nothing to be relevant to the three "
                                         "strategies aren't comparable"}), 400
            try:
                pages = min(int(src.get("pages", API_MAX_COMPARE_PAGES)),
                            API_MAX_COMPARE_PAGES)
            except ValueError:
                pages = API_MAX_COMPARE_PAGES
            # The playground fires three /crawl requests in parallel from the
            # browser; a single API call has to do that fan-out itself or it
            # would take three times as long as one crawl.
            out = compare(url, query, max_pages=pages, delay=0.0, timeout=8)
            return _ok(cache_key, {"url": url, "method": "compare", "query": query,
                            "strategies": out["strategies"], "winner": out["winner"],
                            "tied": out["tied"]})
        return jsonify({"error": f"unknown method '{method}'"}), 400
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"request failed: {e}"}), 502


@app.route("/docs")
def docs():
    # Rendered, not written into the template: the pill said v1.0.0 through
    # three releases because nothing connected it to the package.
    return render_template("docs.html", version=bytecrawl.__version__)


if __name__ == "__main__":
    # 5000 is taken by AirPlay Receiver on macOS, so allow an override:
    #   PORT=5055 python demo/app.py
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
