"""Graph crawlers subpackage: BFS, Shark-Search and OPIC.

The web is a graph (pages = nodes, links = edges); a crawler decides in which
ORDER to visit URLs on a limited request budget, and each strategy answers a
different question:

    BFS           level by level: closest to the seed first.
    Shark-Search  topical best-first: chases pages relevant to the query
                  (Hersovici et al., 1998). Links inherit a score from the
                  parent with decay; bad branches die out on their own.
    OPIC          On-line Page Importance Computation (Abiteboul et al., 2003):
                  each page holds "cash" it distributes to its links as it is
                  visited. PageRank computed live, without the full graph.

``compare()`` runs all three over one site on the same budget, and
``pagerank()`` is the offline ranking to hold the online one against.
"""

from __future__ import annotations

from .base import Crawler
from .compare import compare
from .frontier import Frontier
from .graph import pagerank
from .result import CrawlResult
from .strategies import BFS, OPIC, STRATEGIES, SharkSearch
from .text import cosine, relevance

__all__ = [
    "Crawler", "BFS", "SharkSearch", "OPIC", "CrawlResult", "Frontier",
    "STRATEGIES", "cosine", "relevance", "pagerank", "compare",
]
