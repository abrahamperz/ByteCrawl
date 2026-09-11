"""The concrete frontier strategies and their registry.

Each subclass overrides only the link-scoring policy:
  BFS          — depth only (shallower first).
  SharkSearch  — topical best-first with score inheritance and decay.
  OPIC         — online importance: cash flows along links as pages are visited.
"""

from __future__ import annotations

from urllib.parse import urlparse

from .base import Crawler
from .frontier import Frontier
from .text import _tokens, relevance


class BFS(Crawler):
    """Explicit alias of the base behavior."""

    name = "bfs"


class SharkSearch(Crawler):
    """Topical best-first with score inheritance (Hersovici et al., 1998).

    score(link) = γ·inherited + (1−γ)·local_signal
      inherited    = δ·relevance(parent) if the parent was relevant,
                     otherwise δ·inherited(parent)  → bad branches decay as δ^n.
      local_signal = cosine(anchor + URL words, query).
    """

    name = "shark"

    def __init__(self, query: str, delta: float = 0.5, gamma: float = 0.8, **kw):
        super().__init__(query=query, **kw)
        self.delta = delta
        self.gamma = gamma
        self._inherited: dict[str, float] = {}

    def initial_score(self, url: str) -> float:
        self._inherited[url] = 1.0
        return 1.0

    def score_links(self, url, links, page_relevance, depth):
        # Inheritance: if the parent was relevant, children inherit its
        # relevance; otherwise they inherit what the parent had inherited.
        # Either way with delta decay: a branch with no signal fades as delta^n.
        parent_inherited = self._inherited.get(url, 0.0)
        inherited = self.delta * (page_relevance if page_relevance > 0.05 else parent_inherited)
        scored = []
        for link in links:
            url_words = " ".join(_tokens(urlparse(link["url"]).path))
            local = relevance(f"{link['anchor']} {url_words}", self.query)
            score = self.gamma * inherited + (1 - self.gamma) * local
            self._inherited[link["url"]] = inherited
            scored.append((link["url"], score))
        return scored


class OPIC(Crawler):
    """Online structural importance (Abiteboul et al., 2003).

    Each page holds cash. On visit: its cash is added to its history
    (accumulated importance), reset to 0 and split evenly among its outgoing
    links. The URL with the most pending cash is always visited next.
    Total system cash is conserved (the algorithm's invariant).
    Pages with no outgoing links (sinks) return their cash to the known
    unvisited URLs: the paper's "virtual node", immediate version.
    """

    name = "opic"

    def __init__(self, query: str = "", **kw):
        super().__init__(query=query, **kw)
        self.cash: dict[str, float] = {}
        self.history: dict[str, float] = {}
        self._known_unvisited: set[str] = set()
        self._frontier_ref: Frontier | None = None

    def initial_score(self, url: str) -> float:
        self.cash[url] = 1.0
        return 1.0

    def on_visit(self, url: str, links: list[dict]):
        amount = self.cash.pop(url, 0.0)
        self.history[url] = self.history.get(url, 0.0) + amount
        self._known_unvisited.discard(url)
        targets = [link["url"] for link in links] or list(self._known_unvisited)
        if not targets:
            return
        share = amount / len(targets)
        for t in targets:
            self.cash[t] = self.cash.get(t, 0.0) + share
            self._known_unvisited.add(t)

    def score_links(self, url, links, page_relevance, depth):
        # Cash was already distributed in on_visit; the score IS the accumulated cash.
        return [(link["url"], self.cash.get(link["url"], 0.0)) for link in links]


# --- strategy registry ------------------------------------------------------
# The registry the servers and the demo all needed a copy of. One name per
# strategy, so a crawl requested over HTTP, over MCP or in Python means the
# same thing everywhere.
STRATEGIES: dict[str, type[Crawler]] = {
    "bfs": BFS,
    "shark": SharkSearch,
    "opic": OPIC,
}
