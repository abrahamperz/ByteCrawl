"""ByteCrawl web frontend (Flask): landing, methods, playground, docs, /api.

An app-factory package: :func:`landing.app.create_app` builds the Flask app
from its parts — ``content`` (copy), ``analytics`` (PostHog), ``services``
(scraping/crawling + cache), and ``routes`` (the two blueprints). Vercel and
local runs import ``landing.app:app``.
"""
