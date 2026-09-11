"""Offline graph analysis over a completed crawl.

``pagerank`` is the offline counterpart of what OPIC approximates online:
running both over the same crawl graph and comparing the rankings is the
interesting experiment.
"""

from __future__ import annotations


def pagerank(
    graph: dict[str, list[str]], damping: float = 0.85, iterations: int = 30
) -> dict[str, float]:
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
