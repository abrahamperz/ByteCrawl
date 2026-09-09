"""
ByteCrawl — Universal scraping layer
===================================
A single API to scrape any site: static HTML, dynamic JS, hidden APIs,
session login, crawling at scale and Markdown conversion for LLMs.

Quickstart:

    from bytecrawl import Scraper

    bot = Scraper()
    page = bot.fetch("https://books.toscrape.com")
    books = page.extract("article.product_pod", {
        "title": "h3 a::attr(title)",
        "price": "p.price_color::text",
    })

Explicit strategies:  bot.static(url) · bot.api(url) · bot.browser(url)
Crawling:             bot.crawl(url, item=..., fields=..., next_page=...)
Graph crawling:       SharkSearch(query=...).crawl(url) · BFS · OPIC
Comparing them:       compare(url, query) -> the three side by side
LLM:                  page.markdown() · page.tokens()
"""

from .core import Page, Scraper, Session
from .crawler import (
    BFS,
    OPIC,
    STRATEGIES,
    Crawler,
    CrawlResult,
    SharkSearch,
    compare,
    cosine,
    pagerank,
)

__all__ = [
    "Scraper", "Page", "Session",
    "Crawler", "BFS", "SharkSearch", "OPIC", "CrawlResult", "STRATEGIES",
    "pagerank", "cosine", "compare",
]
__version__ = "0.3.0"
