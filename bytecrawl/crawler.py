"""
Graph crawlers for ByteCraw: BFS, Shark-Search and OPIC.

The web is a graph (pages = nodes, links = edges). A crawler decides in
what ORDER to visit URLs with a limited request budget. Each strategy is
a different answer to that question:

  BFS          — level by level: closest to the seed first.
  Shark-Search — topical best-first: chases pages relevant to a query
                 (Hersovici et al., 1998). Links inherit score from their
                 parent with decay; bad branches die out on their own.
  OPIC         — On-line Page Importance Computation (Abiteboul et al., 2003):
                 each page holds "cash" that it distributes to its links when
                 visited. It is PageRank computed live, without the full graph.

Usage:

    from bytecraw.crawler import BFS, SharkSearch, OPIC, pagerank

    result = SharkSearch(query="machine learning").crawl(
        "https://example.com", max_pages=100)
    result.pages          # visited, in order
    result.graph          # {url: [links]} for offline analysis
    pagerank(result.graph)
"""

from __future__ import annotations

import heapq
import math
import re
import time
from collections import Counter
from dataclasses import dataclass, field
from urllib.parse import urldefrag, urljoin, urlparse

from .core import Scraper

# Non-HTML extensions: not worth spending a request on them.
_SKIP_EXT = re.compile(
    r"\.(png|jpe?g|gif|svg|webp|ico|css|js|pdf|zip|gz|tar|mp[34]|avi|mov|woff2?|ttf|xml|rss)$",
    re.IGNORECASE,
)

_WORD = re.compile(r"[a-záéíóúüñ0-9]+", re.IGNORECASE)


def _tokens(text: str) -> list[str]:
    return [w.lower() for w in _WORD.findall(text or "")]


def cosine(text_a: str, text_b: str) -> float:
    """Cosine similarity between two texts using term-frequency (TF) vectors.

    The classic information-retrieval metric: 1.0 = same vocabulary in the
    same proportions, 0.0 = not a single word in common.
    """
    a, b = Counter(_tokens(text_a)), Counter(_tokens(text_b))
    if not a or not b:
        return 0.0
    common = set(a) & set(b)
    dot = sum(a[w] * b[w] for w in common)
    norm = math.sqrt(sum(v * v for v in a.values())) * math.sqrt(sum(v * v for v in b.values()))
    return dot / norm if norm else 0.0


# Common second-level suffixes (bbc.co.uk → "bbc.co.uk", not "co.uk").
# A frozen shortlist instead of the full public-suffix list keeps us dependency-free.
_SECOND_LEVEL = frozenset({"co", "com", "org", "net", "ac", "gov", "edu"})


def _root_domain(netloc: str) -> str:
    """firecrawl.dev, www.firecrawl.dev and docs.firecrawl.dev are the same site."""
    labels = netloc.lower().split(":")[0].split(".")
    take = 3 if len(labels) >= 3 and labels[-2] in _SECOND_LEVEL else 2
    return ".".join(labels[-take:])


def normalize(url: str, base: str) -> str | None:
    """Resolve relative URLs, strip #fragments and filter out non-web-page URLs."""
    absolute, _ = urldefrag(urljoin(base, url))
    parsed = urlparse(absolute)
    if parsed.scheme not in ("http", "https"):
        return None
    if _SKIP_EXT.search(parsed.path):
        return None
    return absolute


class Frontier:
    """Priority queue of pending URLs with dedup.

    heapq is a min-heap, so we store -score to always pop the URL with the
    HIGHEST score. If a URL gets re-pushed with a new score (happens in OPIC,
    where cash accumulates), we use lazy deletion: stale entries are discarded
    on pop by comparing against the current score.
    """

    def __init__(self):
        self._heap: list[tuple[float, int, str]] = []
        self._score: dict[str, float] = {}
        self._counter = 0  # FIFO tie-break between equal scores

    def push(self, url: str, score: float):
        current = self._score.get(url)
        if current is not None and score <= current:
            return
        self._score[url] = score
        self._counter += 1
        heapq.heappush(self._heap, (-score, self._counter, url))

    def pop(self) -> tuple[str, float] | None:
        while self._heap:
            neg, _, url = heapq.heappop(self._heap)
            if url in self._score and -neg == self._score[url]:
                del self._score[url]
                return url, -neg
        return None

    def __contains__(self, url: str) -> bool:
        return url in self._score

    def __len__(self) -> int:
        return len(self._score)


@dataclass
class CrawlResult:
    """What a crawl returns: pages, graph and numbers for comparison."""

    strategy: str
    pages: list[dict] = field(default_factory=list)   # url, title, score, relevance, depth, order
    graph: dict[str, list[str]] = field(default_factory=dict)
    stats: dict = field(default_factory=dict)

    def relevant(self, threshold: float = 0.1) -> list[dict]:
        return [p for p in self.pages if p["relevance"] >= threshold]

    def top(self, n: int = 10) -> list[dict]:
        return sorted(self.pages, key=lambda p: p["relevance"], reverse=True)[:n]


class Crawler:
    """BFS crawler. Subclasses only change HOW links are scored.

    The loop is identical for every strategy (pop → fetch → extract links →
    score → push); that keeps the comparison between strategies fair:
    same code, different ordering function.
    """

    name = "bfs"

    def __init__(self, query: str = "", delay: float = 0.2, timeout: int = 10,
                 same_domain: bool = True):
        self.query = query
        self.same_domain = same_domain
        self.scraper = Scraper(delay=delay, timeout=timeout)

    # --- extension point -------------------------------------------------------
    def score_links(self, url: str, links: list[dict], relevance: float,
                    depth: int) -> list[tuple[str, float]]:
        """BFS: the score only encodes depth (shallower = visited sooner).

        links: [{url, anchor}]. Returns [(url, score)] for the frontier.
        """
        return [(link["url"], -(depth + 1)) for link in links]

    def on_visit(self, url: str, links: list[dict]):
        """Hook for strategy-specific state (OPIC distributes cash here)."""

    def initial_score(self, url: str) -> float:
        return 0.0

    # --- shared loop -------------------------------------------------------------
    def crawl(self, start: str, max_pages: int = 50, max_depth: int = 10) -> CrawlResult:
        start_norm = normalize(start, start)
        if not start_norm:
            raise ValueError(f"Invalid URL: {start}")
        domain = _root_domain(urlparse(start_norm).netloc)

        frontier = Frontier()
        frontier.push(start_norm, self.initial_score(start_norm))
        visited: set[str] = set()
        depth_of = {start_norm: 0}
        result = CrawlResult(strategy=self.name)
        errors = 0
        t0 = time.perf_counter()

        while len(visited) < max_pages:
            item = frontier.pop()
            if item is None:
                break
            url, score = item
            if url in visited:
                continue
            visited.add(url)
            depth = depth_of.get(url, 0)

            try:
                page = self.scraper.static(url)
            except Exception:
                errors += 1
                continue

            text = page.soup.get_text(" ", strip=True)
            relevance = cosine(text, self.query) if self.query else 0.0
            title = page.css("title") or url

            links = []
            for a in page.soup.select("a[href]"):
                child = normalize(a["href"], url)
                if not child or child == url:
                    continue
                if self.same_domain and _root_domain(urlparse(child).netloc) != domain:
                    continue
                links.append({"url": child, "anchor": a.get_text(" ", strip=True)})

            result.graph[url] = [link["url"] for link in links]
            result.pages.append({
                "url": url, "title": title[:120], "score": round(score, 4),
                "relevance": round(relevance, 4), "depth": depth,
                "order": len(result.pages) + 1,
            })

            self.on_visit(url, links)

            if depth < max_depth:
                for child_url, child_score in self.score_links(url, links, relevance, depth):
                    if child_url not in visited:
                        depth_of.setdefault(child_url, depth + 1)
                        frontier.push(child_url, child_score)

        result.stats = {
            "requests": len(visited),
            "errors": errors,
            "elapsed": round(time.perf_counter() - t0, 2),
            "frontier_left": len(frontier),
            "relevant_found": len(result.relevant()) if self.query else None,
            "avg_relevance": round(
                sum(p["relevance"] for p in result.pages) / len(result.pages), 4
            ) if result.pages else 0.0,
        }
        return result


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

    def score_links(self, url, links, relevance, depth):
        # Inheritance: if the parent was relevant, children inherit its
        # relevance; otherwise they inherit what the parent had inherited.
        # Either way with delta decay: a branch with no signal fades as delta^n.
        parent_inherited = self._inherited.get(url, 0.0)
        inherited = self.delta * (relevance if relevance > 0.05 else parent_inherited)
        scored = []
        for link in links:
            url_words = " ".join(_tokens(urlparse(link["url"]).path))
            local = cosine(f'{link["anchor"]} {url_words}', self.query)
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

    def score_links(self, url, links, relevance, depth):
        # Cash was already distributed in on_visit; the score IS the accumulated cash.
        return [(link["url"], self.cash.get(link["url"], 0.0)) for link in links]


def pagerank(graph: dict[str, list[str]], damping: float = 0.85,
             iterations: int = 30) -> dict[str, float]:
    """PageRank via power iteration over the crawled graph.

    Offline version of the same concept OPIC approximates online: comparing
    both rankings over the same graph is the interesting experiment.
    """
    nodes = set(graph) | {v for vs in graph.values() for v in vs}
    if not nodes:
        return {}
    n = len(nodes)
    rank = {u: 1.0 / n for u in nodes}
    for _ in range(iterations):
        new = {u: (1 - damping) / n for u in nodes}
        for u in nodes:
            out = [v for v in graph.get(u, []) if v in nodes]
            if out:
                share = damping * rank[u] / len(out)
                for v in out:
                    new[v] += share
            else:  # sink: distribute to all (virtual node)
                share = damping * rank[u] / n
                for v in nodes:
                    new[v] += share
        rank = new
    return dict(sorted(rank.items(), key=lambda kv: kv[1], reverse=True))
