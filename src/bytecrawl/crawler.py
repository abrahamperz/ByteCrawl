"""Backward-compatibility shim for ``bytecrawl.crawler``.

The graph crawlers moved into the :mod:`bytecrawl.crawl` subpackage (one
module per responsibility: text, frontier, result, base, strategies, graph,
compare). This module re-exports the full former surface — public classes
and functions plus the private helpers the tests import, and ``normalize``,
which is published from here — so ``from bytecrawl.crawler import ...`` keeps
working unchanged.

Usage:

    from bytecrawl.crawler import BFS, SharkSearch, OPIC, pagerank

    result = SharkSearch(query="machine learning").crawl(
        "https://example.com", max_pages=100)
    result.pages   # visited, in order
    result.graph   # {url: [links]} for offline analysis
    pagerank(result.graph)
"""

from __future__ import annotations

# normalize() is published from here because that is where the tests and docs
# import it from; its home is the scraping subpackage.
from .crawl.base import Crawler
from .crawl.compare import _leg, compare
from .crawl.frontier import Frontier, _root_domain
from .crawl.graph import pagerank
from .crawl.result import CrawlResult
from .crawl.strategies import BFS, OPIC, STRATEGIES, SharkSearch
from .crawl.text import _dice, _resolve_terms, _tokens, _trigrams, cosine, relevance
from .scraping.url import normalize

__all__ = [
    "Crawler",
    "BFS",
    "SharkSearch",
    "OPIC",
    "CrawlResult",
    "Frontier",
    "STRATEGIES",
    "cosine",
    "relevance",
    "pagerank",
    "compare",
    "normalize",
    "_root_domain",
    "_tokens",
    "_trigrams",
    "_dice",
    "_resolve_terms",
    "_leg",
]
