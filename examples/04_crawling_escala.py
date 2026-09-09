"""
Technique 4 — Crawling at scale, with ByteCrawl
===============================================
When it stops being one page and becomes hundreds. Two shapes of the same
problem:

  a) Pagination — the pages are a known chain ("next" links). Walk it and
     extract records as you go: Scraper.crawl(..., next_page=...).

  b) A whole site — you don't know the pages, only the topic you care about.
     Give the crawler a request budget and let it decide the order:
     SharkSearch chases the topic, OPIC chases importance, BFS sweeps evenly.

The graph crawlers all share one loop (pop -> fetch -> score links -> push),
so comparing them on the same site is a fair experiment.

Practice site: https://quotes.toscrape.com (paginated, and tag-rich)
Run:           python 04_crawling_escala.py
Generates:     frases_crawl.json
"""

import json
from pathlib import Path

from bytecrawl import BFS, OPIC, Scraper, SharkSearch, pagerank

OUT = Path(__file__).parent / "frases_crawl.json"

# --- a) pagination: follow the "next" link and extract typed records --------
bot = Scraper(delay=0.2)
quotes = bot.crawl(
    "https://quotes.toscrape.com",
    item="div.quote",
    fields={
        "quote": "span.text::text",
        "author": "small.author::text",
        "tags[]": "a.tag::text",
    },
    next_page="li.next a::attr(href)",
    pages=3,                      # budget: stop after 3 pages
)
print(f"pagination -> {len(quotes)} quotes across 3 pages")
print("  first:", quotes[0]["author"], "|", quotes[0]["quote"][:48], "...")

# --- b) whole site: same budget, three different orderings -----------------
QUERY, BUDGET = "love", 12
results = {}
for name, crawler in [
    ("shark", SharkSearch(query=QUERY, delay=0.2)),
    ("opic", OPIC(delay=0.2)),
    ("bfs", BFS(query=QUERY, delay=0.2)),
]:
    result = crawler.crawl("https://quotes.toscrape.com", max_pages=BUDGET)
    relevant = result.relevant(0.1)
    results[name] = {
        "requests": result.stats["requests"],
        "relevant_pages": len(relevant),
        "top": [
            {"url": p["url"], "relevance": p["relevance"]} for p in result.top(3)
        ],
    }
    print(f"{name:6} -> {len(relevant):2} relevant pages of {result.stats['requests']} crawled")

# Shark-Search should find the topic that BFS walks straight past.
best = max(results, key=lambda k: results[k]["relevant_pages"])
print(f"\nbest for '{QUERY}' with {BUDGET} requests: {best}")

# The crawl also hands back the link graph, so importance can be computed
# offline and compared against OPIC's online estimate.
graph = SharkSearch(query=QUERY, delay=0.2).crawl(
    "https://quotes.toscrape.com", max_pages=BUDGET).graph
ranks = pagerank(graph)
top_ranked = sorted(ranks.items(), key=lambda kv: kv[1], reverse=True)[:3]
print("pagerank (offline) top 3:")
for url, rank in top_ranked:
    print(f"  {rank:.4f}  {url}")

OUT.write_text(json.dumps({"quotes": quotes, "strategies": results}, indent=2,
                          ensure_ascii=False), encoding="utf-8")
print(f"\nsaved -> {OUT.name}")
