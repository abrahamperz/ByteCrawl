"""
Graph crawlers for ByteCrawl: BFS, Shark-Search and OPIC.

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

    from bytecrawl.crawler import BFS, SharkSearch, OPIC, pagerank

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
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from functools import lru_cache
from urllib.parse import urlparse

# normalize() lives in core so Page.links() and the crawlers agree on what
# counts as a link; re-exported here because that is where it was first
# published and where the tests and docs import it from.
from .core import Scraper, normalize

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


@lru_cache(maxsize=4096)
def _trigrams(word: str) -> frozenset:
    padded = f"~{word}~"
    return frozenset(padded[i:i + 3] for i in range(len(padded) - 2))


def _dice(a: frozenset, b: frozenset) -> float:
    """Sørensen-Dice overlap of two trigram sets: 1.0 identical, 0.0 disjoint."""
    if not a or not b:
        return 0.0
    return 2 * len(a & b) / (len(a) + len(b))


# Thresholds measured against real pairs, not guessed. At 0.55 a one-letter
# slip is caught ("mistery"/"mystery" = 0.57) while genuinely different words
# stay out ("price"/"prize" = 0.40, "crawl"/"crown" = 0.20). Words shorter than
# 6 letters are matched exactly: they have too few trigrams to tell a typo from
# a different word ("data"/"date" and "news"/"newt" both score 0.50, the same
# as the real typo "travle"/"travel"), so fuzzy there would invent matches.
# Deliberately conservative: it misses heavier typos ("histroy") and
# inflections ("pricing"/"prices") rather than risk false hits.
_FUZZY_MIN = 0.55
_FUZZY_MIN_LEN = 6


def _resolve_terms(query: str, vocabulary: set) -> str:
    """Rewrites query words that are near-misses of a word the page uses.

    People typo their queries ("mistery"), and exact term matching scores that
    0.0 — which reads as "the crawler is broken" rather than "no match".
    Snapping each query term to its closest page term keeps the scoring itself
    on the plain cosine path.
    """
    resolved = []
    for term in _tokens(query):
        if term in vocabulary or len(term) < _FUZZY_MIN_LEN:
            resolved.append(term)
            continue
        grams = _trigrams(term)
        best, best_score = None, 0.0
        for word in vocabulary:
            if len(word) < _FUZZY_MIN_LEN or abs(len(word) - len(term)) > 2:
                continue
            score = _dice(grams, _trigrams(word))
            if score > best_score:
                best, best_score = word, score
        resolved.append(best if best_score >= _FUZZY_MIN else term)
    return " ".join(resolved)


def relevance(text: str, query: str, url: str = "") -> float:
    """How well a page answers a query.

    Scores the page text plus its URL path — a page at /category/mystery is
    about mystery even if the word is thin in the body — and tolerates typos
    and inflections in the query.
    """
    if not query:
        return 0.0
    haystack = f"{text} {' '.join(_tokens(urlparse(url).path))}" if url else text
    return cosine(haystack, _resolve_terms(query, set(_tokens(haystack))))


# Common second-level suffixes (bbc.co.uk → "bbc.co.uk", not "co.uk").
# A frozen shortlist instead of the full public-suffix list keeps us dependency-free.
_SECOND_LEVEL = frozenset({"co", "com", "org", "net", "ac", "gov", "edu"})


def _root_domain(netloc: str) -> str:
    """firecrawl.dev, www.firecrawl.dev and docs.firecrawl.dev are the same site."""
    labels = netloc.lower().split(":")[0].split(".")
    take = 3 if len(labels) >= 3 and labels[-2] in _SECOND_LEVEL else 2
    return ".".join(labels[-take:])


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
    def score_links(self, url: str, links: list[dict], page_relevance: float,
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
            page_relevance = relevance(text, self.query, url) if self.query else 0.0
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
                "relevance": round(page_relevance, 4), "depth": depth,
                "order": len(result.pages) + 1,
            })

            self.on_visit(url, links)

            if depth < max_depth:
                for child_url, child_score in self.score_links(url, links, page_relevance, depth):
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

    def score_links(self, url, links, page_relevance, depth):
        # Inheritance: if the parent was relevant, children inherit its
        # relevance; otherwise they inherit what the parent had inherited.
        # Either way with delta decay: a branch with no signal fades as delta^n.
        parent_inherited = self._inherited.get(url, 0.0)
        inherited = self.delta * (page_relevance if page_relevance > 0.05 else parent_inherited)
        scored = []
        for link in links:
            url_words = " ".join(_tokens(urlparse(link["url"]).path))
            local = relevance(f'{link["anchor"]} {url_words}', self.query)
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
    # Filter each node's out-links to known nodes once, not once per iteration.
    out = {u: [v for v in graph.get(u, ()) if v in nodes] for u in nodes}
    sinks = [u for u, outs in out.items() if not outs]
    rank = {u: 1.0 / n for u in nodes}
    for _ in range(iterations):
        # A sink has nowhere to send its rank, so it spreads evenly over every
        # node. Summing that mass first and adding it to the base keeps the
        # pass O(nodes + edges); pushing it per sink is O(sinks x nodes), which
        # is quadratic on a crawl graph, where most discovered URLs were never
        # visited and are therefore sinks.
        base = (1 - damping) / n + damping * sum(rank[u] for u in sinks) / n
        new = dict.fromkeys(nodes, base)
        for u, outs in out.items():
            if outs:
                share = damping * rank[u] / len(outs)
                for v in outs:
                    new[v] += share
        rank = new
    # Ties are the norm, not the exception: every sink holds the same rank, and
    # a crawl graph is mostly sinks. Break them by URL so the ranking is stable
    # across runs (set iteration order shifts with the per-process hash seed).
    return dict(sorted(rank.items(), key=lambda kv: (-kv[1], kv[0])))


# --- strategy comparison ----------------------------------------------------
# The registry the servers and the demo all needed a copy of. One name per
# strategy, so a crawl requested over HTTP, over MCP or in Python means the
# same thing everywhere.
STRATEGIES: dict[str, type[Crawler]] = {
    "bfs": BFS, "shark": SharkSearch, "opic": OPIC,
}


def _leg(name: str, start: str, query: str, max_pages: int, max_depth: int,
         delay: float, timeout: int) -> dict:
    """One strategy's leg of a comparison. Never raises: a strategy that fails
    reports inside its own entry so the other two still come back."""
    try:
        result = STRATEGIES[name](query=query, delay=delay, timeout=timeout).crawl(
            start, max_pages=max_pages, max_depth=max_depth)
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}
    return {
        "stats": result.stats,
        "relevant": len(result.relevant()),
        "pages": result.top(max_pages),
    }


def compare(start: str, query: str, max_pages: int = 20, max_depth: int = 4,
            delay: float = 0.2, timeout: int = 10) -> dict:
    """Run every strategy over one site on the same budget, side by side.

    A single ordering looks like any other crawler's. The case for having
    frontier strategies at all only shows up in the comparison: on a Wikipedia
    seed with a topical query, Shark-Search returns pages about the topic where
    BFS returns whatever was linked first.

    The three run concurrently — sequentially this is three times the wall
    clock, which is the difference between a usable API call and a timeout.
    Each Crawler builds its own Scraper, so its own requests Session; nothing
    is shared. The per-crawler delay is multiplied by the number of strategies
    because all of them hit the same host at once, which keeps the aggregate
    rate on that host the same as a single crawl's.

    Returns {"strategies": {name: {stats, relevant, pages} | {error}},
             "winner": name | None, "tied": [names sharing the top score]}.

    `tied` matters: on a small or uniformly relevant site every strategy finds
    the same pages, and reporting whichever one the dict happened to list first
    as "the winner" would read as a result when it is a coin flip.
    """
    if not query:
        raise ValueError(
            "compare needs a query: with nothing to be relevant to, the "
            "strategies aren't comparable (use a single crawler instead)")
    names = list(STRATEGIES)
    with ThreadPoolExecutor(max_workers=len(names)) as pool:
        legs = list(pool.map(
            lambda n: _leg(n, start, query, max_pages, max_depth,
                           delay * len(names), timeout),
            names))
    results = dict(zip(names, legs))

    ok = {n: r for n, r in results.items() if "error" not in r}

    def _score(name: str) -> tuple[int, float]:
        # Most relevant pages wins. A tie goes to whichever ranked them higher
        # on average — finding the same count but scoring it better is exactly
        # what a frontier strategy is for.
        pages = ok[name]["pages"]
        mean = sum(p["relevance"] for p in pages) / len(pages) if pages else 0.0
        return ok[name]["relevant"], mean

    if not ok:
        return {"strategies": results, "winner": None, "tied": []}
    best = max(_score(n) for n in ok)
    tied = sorted(n for n in ok if _score(n) == best)
    return {"strategies": results, "winner": tied[0], "tied": tied}
