"""The shared crawl loop.

``Crawler`` implements one loop (pop → fetch → extract links → score →
push) that every strategy reuses; subclasses change only how links are
scored. Keeping the loop identical is what makes the strategy comparison
fair — same code, different ordering function.
"""

from __future__ import annotations

import time
from urllib.parse import urlparse

# normalize() lives in the scraping subpackage so Page.links() and the
# crawlers agree on what counts as a link; the crawler module re-exports it
# because that is where the tests and docs import it from.
from ..scraping.scraper import Scraper
from ..scraping.url import normalize
from .frontier import Frontier, _root_domain
from .result import CrawlResult
from .text import relevance


class Crawler:
    """BFS crawler. Subclasses only change HOW links are scored.

    The loop is identical for every strategy (pop → fetch → extract links →
    score → push); that keeps the comparison between strategies fair:
    same code, different ordering function.
    """

    name = "bfs"

    def __init__(
        self, query: str = "", delay: float = 0.2, timeout: int = 10, same_domain: bool = True
    ):
        self.query = query
        self.same_domain = same_domain
        self.scraper = Scraper(delay=delay, timeout=timeout)

    # --- extension point -------------------------------------------------------
    def score_links(
        self, url: str, links: list[dict], page_relevance: float, depth: int
    ) -> list[tuple[str, float]]:
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
                child = normalize(str(a["href"]), url)
                if not child or child == url:
                    continue
                if self.same_domain and _root_domain(urlparse(child).netloc) != domain:
                    continue
                links.append({"url": child, "anchor": a.get_text(" ", strip=True)})

            result.graph[url] = [link["url"] for link in links]
            result.pages.append(
                {
                    "url": url,
                    "title": title[:120],
                    "score": round(score, 4),
                    "relevance": round(page_relevance, 4),
                    "depth": depth,
                    "order": len(result.pages) + 1,
                }
            )

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
            "avg_relevance": round(sum(p["relevance"] for p in result.pages) / len(result.pages), 4)
            if result.pages
            else 0.0,
        }
        return result
