"""The crawl frontier and domain grouping.

A priority queue of pending URLs (highest score popped first, with lazy
deletion for re-scored URLs), plus the root-domain helper the crawlers use
to decide whether a link stays on-site.
"""

from __future__ import annotations

import heapq

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
