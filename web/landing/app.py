"""
Web dashboard for ByteCrawl: landing, methods, playground, docs, plus the
public /api endpoint and the /analyze and /crawl demos behind them.

Run: python web/landing/app.py  ->  open http://127.0.0.1:5000

This is the app factory. It assembles the app from its parts, which live in
sibling modules:

    content    the static copy (technique cards, /analyze i18n)
    analytics  the PostHog client, distinct id, and per-response flush
    services   the scraping/crawling orchestration and the response cache
    routes     the HTTP layer (pages_bp + api_bp blueprints)

``app = create_app()`` is exposed at module level because Vercel imports the
WSGI app as ``landing.app:app``.
"""

import sys
from pathlib import Path

BASE = Path(__file__).parent
# Serverless (Vercel) doesn't `pip install` the library, so put `web/` (which
# holds the `landing` package) and the src layout (the `bytecrawl` package) on
# the path before importing either. Local and CI use `pip install -e .`, so
# these inserts are harmless no-ops there.
sys.path.insert(0, str(BASE.parent))                 # web/: the `landing` package
sys.path.insert(0, str(BASE.parent.parent / "src"))  # src layout: `bytecrawl`

import os  # noqa: E402

from dotenv import load_dotenv  # noqa: E402
from flask import Flask  # noqa: E402

from landing import analytics  # noqa: E402
from landing.routes import api_bp, pages_bp  # noqa: E402


def create_app() -> Flask:
    """Build and configure the Flask app."""
    load_dotenv()
    # template_folder / static_folder default to web/landing/templates and
    # web/landing/static (relative to this file) — keep it that way: agent_skill()
    # reads SKILL.md out of app.static_folder.
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", "bytecrawl-dev-secret")
    # Flask sorts JSON keys by default, but here the orderings mean something:
    # discovered fields come ranked most-useful selector first, so the
    # playground offers exactly one button. Sorted alphabetically,
    # books.toscrape.com would lead with `a::attr(href)`.
    app.json.sort_keys = False

    app.register_blueprint(pages_bp)
    app.register_blueprint(api_bp)
    analytics.register(app)
    return app


app = create_app()


if __name__ == "__main__":
    # 5000 is taken by AirPlay Receiver on macOS, so allow an override:
    # PORT=5055 python web/landing/app.py
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
