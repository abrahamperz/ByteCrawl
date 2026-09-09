"""Backward-compatibility shim for ``bytecrawl.core``.

The core scraping code moved into the :mod:`bytecrawl.scraping` subpackage
(one module per responsibility: url, selectors, markdown, page, session,
scraper). This module re-exports the full former surface — public classes
and the private helpers the tests import — so ``from bytecrawl.core import
...`` keeps working unchanged.
"""

from __future__ import annotations

from .scraping.markdown import _clean_markdown
from .scraping.page import Page
from .scraping.scraper import Scraper
from .scraping.selectors import _split_selector, _value_from
from .scraping.session import Session
from .scraping.url import _SKIP_EXT, DEFAULT_UA, _decoded_html, normalize

__all__ = [
    "Page",
    "Session",
    "Scraper",
    "normalize",
    "DEFAULT_UA",
    "_SKIP_EXT",
    "_decoded_html",
    "_split_selector",
    "_value_from",
    "_clean_markdown",
]
