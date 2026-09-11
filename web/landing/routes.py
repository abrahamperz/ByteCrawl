"""HTTP layer: the page views and the JSON endpoints, as two blueprints.

The handlers stay thin — parse the request, call into :mod:`landing.services`,
pick a status code, jsonify. All the scraping/crawling lives in services; all
the analytics in :mod:`landing.analytics`.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from flask import (
    Blueprint,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
)

import bytecrawl
from landing import analytics, services
from landing.content import TECHNIQUES

pages_bp = Blueprint("pages", __name__)
api_bp = Blueprint("api", __name__)


# --------------------------------------------------------------------------- #
# Pages
# --------------------------------------------------------------------------- #
@pages_bp.route("/")
def landing():
    return render_template("landing.html")


@pages_bp.route("/agent-onboarding/skill.json")
def agent_skill_version():
    """The hash of the file we are currently serving.

    Installing the skill copies it to disk, so it is a snapshot: fixing
    something here never reaches anyone who installed it earlier, and there is
    no way to push to them. An agent can hash its own copy and compare against
    this to find out it is stale — a hash rather than a version string because
    nobody has to remember to bump it, so it cannot drift from the file.
    """
    body = (Path(current_app.static_folder) / "SKILL.md").read_bytes()
    return jsonify({
        "sha256": hashlib.sha256(body).hexdigest(),
        "bytes": len(body),
        "url": "https://bytecrawl.vercel.app/agent-onboarding/SKILL.md",
    })


@pages_bp.route("/agent-onboarding/SKILL.md")
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
    skill = Path(current_app.static_folder) / "SKILL.md"
    from_browser = "text/html" in request.headers.get("Accept", "")
    return current_app.response_class(
        skill.read_text(encoding="utf-8"),
        mimetype="text/plain" if from_browser else "text/markdown",
        headers={
            "Cache-Control": "public, max-age=300",
            "Content-Disposition": "inline",
            "Vary": "Accept",
        },
    )


@pages_bp.route("/methods")
def methods():
    return render_template("index.html", techniques=TECHNIQUES)


@pages_bp.route("/playground")
def playground():
    return render_template("try.html", techniques=TECHNIQUES)


@pages_bp.route("/try")
def try_redirect():
    """The playground used to live at /try; links to it are already out there.

    308 rather than 302 so the redirect is cached and the query string
    (?url=… deep links from the landing page) survives.
    """
    qs = request.query_string.decode()
    return redirect("/playground" + ("?" + qs if qs else ""), code=308)


@pages_bp.route("/docs")
def docs():
    # Rendered, not written into the template: the pill said v1.0.0 through
    # three releases because nothing connected it to the package.
    return render_template("docs.html", version=bytecrawl.__version__)


# --------------------------------------------------------------------------- #
# JSON endpoints
# --------------------------------------------------------------------------- #
@api_bp.route("/analyze", methods=["POST"])
def analyze():
    """Runs the 'auto' strategy on a URL and explains what it did and why."""
    body = request.json or {}
    payload, status, props = services.analyze_url(
        body.get("url", "").strip(), body.get("lang", "en"))
    if props is not None:
        analytics.track("url_analyzed", props)
    return jsonify(payload), status


@api_bp.route("/crawl", methods=["POST"])
def crawl():
    """Runs ONE crawl strategy (the frontend compares by calling 3 in parallel)."""
    body = request.json or {}
    payload, status, props = services.run_crawl(
        body.get("url", "").strip(),
        body.get("strategy", "bfs"),
        body.get("query", "").strip())
    if props is not None:
        analytics.track("crawl_strategy_run", props)
    return jsonify(payload), status


@api_bp.route("/api", methods=["GET", "POST"])
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
    url = services.clean_url(src.get("url") or "")
    if not url:
        return jsonify({"error": "the 'url' parameter is required"}), 400

    method = (src.get("method") or "markdown").lower()
    cache_key = "|".join([url, method, src.get("query", ""), src.get("select", ""),
                          src.get("strategy", ""), str(src.get("pages", ""))])
    cached = services.cache_get(cache_key)
    if cached is not None:
        return jsonify(cached)

    try:
        # The SSRF guard runs in the same funnel as the fetch so its failures
        # get the same shaped answers: a non-public URL is a 400 ValueError,
        # but a host that simply doesn't resolve is UnreachableError — the same
        # 502 "couldn't open that page" a mistyped domain gets everywhere else,
        # instead of a raw "Cannot resolve host" only on this pre-checked path.
        services.assert_public_url(url)
        payload = services.run_api_method(method, url, src)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except bytecrawl.BlockedError as e:
        return jsonify({"error": str(e), "blocked": True, "wall": e.wall}), 403
    except bytecrawl.RateLimitError as e:
        # The seed is up but throttling us (429). An honest 429 back, with the
        # site's Retry-After echoed both in the body and the header so a client
        # can back off, instead of dressing a live-but-busy site as unreachable.
        resp = jsonify({"error": str(e), "rate_limited": True,
                        "retry_after": e.retry_after})
        if e.retry_after is not None:
            resp.headers["Retry-After"] = str(e.retry_after)
        return resp, 429
    except bytecrawl.UnreachableError as e:
        # The seed URL couldn't be opened at all (bad domain, refused, 404,
        # two links pasted into one) — an honest 502 with a clear flag, the
        # same answer every method and the MCP tools give.
        return jsonify({"error": str(e), "unreachable": True}), 502
    except Exception as e:
        return jsonify({"error": f"request failed: {e}"}), 502

    services.cache_put(cache_key, payload)  # errors above are never cached
    return jsonify(payload)
