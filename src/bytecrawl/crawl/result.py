"""The value a crawl returns."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..scraping.url import BlockedError, RateLimitError, UnreachableError


@dataclass
class CrawlResult:
    """What a crawl returns: pages, graph and numbers for comparison."""

    strategy: str
    pages: list[dict] = field(default_factory=list)  # url, title, score, relevance, depth, order
    graph: dict[str, list[str]] = field(default_factory=dict)
    stats: dict = field(default_factory=dict)
    # The bot wall that turned the crawl away, if any. A crawl swallows a
    # per-page block and keeps going, but when the seed is walled it comes
    # back empty — callers read this to tell "walled" apart from "nothing here".
    blocked: BlockedError | None = None
    # Same idea for a throttled seed: the crawl swallows a per-page 429 and
    # keeps going, but a rate-limited *seed* comes back empty — remembered here
    # so the caller can say "slow down and retry" instead of "nothing here".
    rate_limited: RateLimitError | None = None

    def relevant(self, threshold: float = 0.1) -> list[dict]:
        return [p for p in self.pages if p["relevance"] >= threshold]

    def top(self, n: int = 10) -> list[dict]:
        return sorted(self.pages, key=lambda p: p["relevance"], reverse=True)[:n]

    @property
    def unreachable(self) -> bool:
        """Every fetch failed: the crawl never read a single page.

        A crawl swallows per-page errors and keeps going, so an empty result
        is ambiguous — the seed was unreachable (a domain that doesn't
        resolve, a refused connection, a 404, or two URLs pasted into one), or
        it read fine and simply matched nothing. When every request failed
        (``requests - errors <= 0``) it is the former. A walled seed also
        lands here, but is reported through :attr:`blocked` first.
        """
        reqs = self.stats.get("requests", 0)
        return reqs >= 1 and reqs - self.stats.get("errors", 0) <= 0

    def raise_for_seed(self) -> None:
        """Raise if the crawl never got off the ground; return quietly otherwise.

        Turns a dead-on-arrival crawl into the same exception a single fetch
        would have raised, so every caller (the HTTP API, the MCP tools) can
        report a walled or unreachable seed uniformly instead of dressing an
        empty crawl up as "found nothing relevant". A crawl that read at least
        one page returns quietly — even one that matched nothing, which is a
        real answer, not a failure.

        Precedence, most specific first: a bot wall (blocked), then a rate limit
        (throttled but reachable), then a dead seed (unreachable). A walled seed
        can set both blocked and unreachable; "a bot wall refused you" is the
        more actionable answer, and a 429 sits between the two.
        """
        if self.blocked is not None and not self.pages:
            raise self.blocked
        if self.rate_limited is not None and not self.pages:
            raise self.rate_limited
        if self.unreachable:
            raise UnreachableError()  # default message: the one shared wording
