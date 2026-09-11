"""The value a crawl returns."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CrawlResult:
    """What a crawl returns: pages, graph and numbers for comparison."""

    strategy: str
    pages: list[dict] = field(default_factory=list)  # url, title, score, relevance, depth, order
    graph: dict[str, list[str]] = field(default_factory=dict)
    stats: dict = field(default_factory=dict)

    def relevant(self, threshold: float = 0.1) -> list[dict]:
        return [p for p in self.pages if p["relevance"] >= threshold]

    def top(self, n: int = 10) -> list[dict]:
        return sorted(self.pages, key=lambda p: p["relevance"], reverse=True)[:n]
