"""Run every strategy over one site on the same budget, side by side."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from .strategies import STRATEGIES


def _leg(
    name: str, start: str, query: str, max_pages: int, max_depth: int, delay: float, timeout: int
) -> dict:
    """One strategy's leg of a comparison. Never raises: a strategy that fails
    reports inside its own entry so the other two still come back."""
    try:
        result = STRATEGIES[name](query=query, delay=delay, timeout=timeout).crawl(
            start, max_pages=max_pages, max_depth=max_depth
        )
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}
    return {
        "stats": result.stats,
        "relevant": len(result.relevant()),
        "pages": result.top(max_pages),
    }


def compare(
    start: str,
    query: str,
    max_pages: int = 20,
    max_depth: int = 4,
    delay: float = 0.2,
    timeout: int = 10,
) -> dict:
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
            "strategies aren't comparable (use a single crawler instead)"
        )
    names = list(STRATEGIES)
    with ThreadPoolExecutor(max_workers=len(names)) as pool:
        legs = list(
            pool.map(
                lambda n: _leg(n, start, query, max_pages, max_depth, delay * len(names), timeout),
                names,
            )
        )
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
