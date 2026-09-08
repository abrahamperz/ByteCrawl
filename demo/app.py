"""
Web dashboard to visualize the scraping techniques.
Runs each script on demand and shows the results in tables/charts.

Run:  python app.py   ->  open http://127.0.0.1:5000
"""

import atexit
import csv
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, session
from posthog import Posthog

BASE = Path(__file__).parent
EXAMPLES = BASE.parent / "examples"

sys.path.insert(0, str(BASE.parent))
from bytecrawl import Scraper
from bytecrawl.crawler import BFS, OPIC, SharkSearch, pagerank

load_dotenv()

posthog_client = Posthog(
    project_api_key=os.environ.get("POSTHOG_PROJECT_TOKEN", ""),
    host=os.environ.get("POSTHOG_HOST", "https://us.i.posthog.com"),
    enable_exception_autocapture=True,
)
atexit.register(posthog_client.shutdown)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "bytecrawl-dev-secret")


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


# Definition of each technique: the script it runs and the output file it generates.
TECHNIQUES = {
    "static": {
        "title": "1 · Static HTML",
        "subtitle": "requests + BeautifulSoup",
        "site": "books.toscrape.com",
        "script": "01_estatico_bs4.py",
        "output": "libros.csv",
        "description": "The server sends the full HTML. We fetch it and parse it with CSS selectors.",
    },
    "dynamic": {
        "title": "2 · Dynamic JS",
        "subtitle": "Playwright (real browser)",
        "site": "quotes.toscrape.com/js",
        "script": "02_dinamico_playwright.py",
        "output": "frases.json",
        "description": "JS fills the page. We launch a real browser and read the rendered DOM.",
    },
    "api": {
        "title": "3 · Intercepted API",
        "subtitle": "requests → JSON",
        "site": "quotes.toscrape.com/api",
        "script": "03_api_red.py",
        "output": "frases_api.json",
        "description": "Behind the JS there's an API with clean JSON. We hit it and skip the HTML.",
    },
    "scrapy": {
        "title": "4 · Scrapy at scale",
        "subtitle": "crawler with queue + concurrency",
        "site": "quotes.toscrape.com",
        "script": "04_scrapy_spider.py",
        "output": "frases_scrapy.json",
        "description": "Industrial framework: handles URL queue, parallelism, retries and export.",
    },
    "login": {
        "title": "5 · API with login",
        "subtitle": "session + CSRF token",
        "site": "quotes.toscrape.com/login",
        "script": "05_api_con_login.py",
        "output": None,  # prints to console only
        "description": "Data behind a login. We reuse the session cookie/token on every request.",
    },
    "markdown": {
        "title": "Extra · HTML → Markdown",
        "subtitle": "token savings for LLMs",
        "site": "quotes.toscrape.com",
        "script": "extra_html_a_markdown.py",
        "output": "pagina.md",
        "description": "Turns noisy HTML into clean Markdown: same info, a fraction of the tokens.",
    },
}


def read_output(name: str):
    """Reads the results file and returns it as a structure for the UI."""
    if not name:
        return None
    path = EXAMPLES / name
    if not path.exists():
        return None
    if name.endswith(".json"):
        return json.loads(path.read_text(encoding="utf-8"))
    if name.endswith(".csv"):
        with path.open(encoding="utf-8") as f:
            return list(csv.DictReader(f))
    if name.endswith(".md"):
        return path.read_text(encoding="utf-8")
    return None


@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/methods")
def methods():
    return render_template("index.html", techniques=TECHNIQUES)


@app.route("/try")
def try_playground():
    return render_template("try.html", techniques=TECHNIQUES)


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


CRAWL_STRATEGIES = {"bfs": BFS, "shark": SharkSearch, "opic": OPIC}


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


@app.route("/docs")
def docs():
    return render_template("docs.html")


@app.route("/run/<key>", methods=["POST"])
def run(key):
    if key not in TECHNIQUES:
        return jsonify({"ok": False, "error": "unknown technique"}), 404

    t = TECHNIQUES[key]
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            [sys.executable, t["script"]],
            cwd=EXAMPLES,
            capture_output=True,
            text=True,
            timeout=180,
        )
    except subprocess.TimeoutExpired:
        return jsonify({"ok": False, "error": "the script took too long (timeout)"}), 504
    seconds = round(time.perf_counter() - t0, 2)

    data = read_output(t["output"])
    posthog_client.capture(
        _get_distinct_id(),
        "scrape_technique_run",
        properties={
            "technique": key,
            "technique_title": t["title"],
            "success": proc.returncode == 0,
            "duration_seconds": seconds,
            "record_count": len(data) if isinstance(data, list) else None,
        },
    )
    return jsonify(
        {
            "ok": proc.returncode == 0,
            "stdout": proc.stdout[-4000:],
            "stderr": proc.stderr[-2000:],
            "output": t["output"],
            "data": data,
            "seconds": seconds,
        }
    )


@app.route("/data/<key>")
def data(key):
    """Returns already-generated results without re-running the script."""
    if key not in TECHNIQUES:
        return jsonify({"ok": False}), 404
    data = read_output(TECHNIQUES[key]["output"])
    posthog_client.capture(
        _get_distinct_id(),
        "scrape_data_retrieved",
        properties={
            "technique": key,
            "has_data": data is not None,
            "record_count": len(data) if isinstance(data, list) else None,
        },
    )
    return jsonify({"ok": True, "data": data})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
