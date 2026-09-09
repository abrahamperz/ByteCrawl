"""Scraping subpackage: fetch a page, then extract data from it.

Public surface: :class:`Scraper` (the entry point), the :class:`Page` it
returns, :class:`Session` for authenticated flows, and :func:`normalize`
for turning hrefs into canonical URLs.
"""

from __future__ import annotations

from .page import Page
from .scraper import Scraper
from .session import Session
from .url import normalize

__all__ = ["Page", "Session", "Scraper", "normalize"]
