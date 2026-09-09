"""
Technique 1 — Static HTML with requests + BeautifulSoup
=======================================================
The server returns the complete HTML. We request it, parse it
and extract data with CSS selectors.

Practice site: https://books.toscrape.com (static book catalogue)

How to know this technique applies:
  - Open the page, right click -> "View page source".
  - If the data you want already shows up there (not empty), this works.

Run:  python 01_html_estatico.py
"""

import csv
import time

import requests
from bs4 import BeautifulSoup

BASE = "https://books.toscrape.com/catalogue/"
START = "https://books.toscrape.com/catalogue/page-1.html"

# Real-browser header: many servers reject requests' default User-Agent
# ("python-requests/2.x"). This is basic good practice.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}

# Maps the rating CSS class to a number
RATING = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}


def parse_page(html: str):
    """Extracts every book from a catalogue page."""
    soup = BeautifulSoup(html, "lxml")
    books = []
    for card in soup.select("article.product_pod"):
        title = card.h3.a["title"]
        price = card.select_one("p.price_color").text.strip()
        rating_class = card.select_one("p.star-rating")["class"][1]  # e.g. "Three"
        availability = card.select_one("p.instock.availability").text.strip()
        books.append(
            {
                "title": title,
                "price": price,
                "rating": RATING.get(rating_class, 0),
                "availability": availability,
            }
        )
    return books


def next_url(html: str):
    """Returns the next page URL, or None if this is the last one."""
    soup = BeautifulSoup(html, "lxml")
    nxt = soup.select_one("li.next a")
    return BASE + nxt["href"] if nxt else None


def main():
    url = START
    results = []
    # Reuse the TCP connection with a Session -> faster across many requests
    with requests.Session() as s:
        s.headers.update(HEADERS)
        while url:
            print(f"Downloading: {url}")
            r = s.get(url, timeout=15)
            r.raise_for_status()
            results.extend(parse_page(r.text))
            url = next_url(r.text)
            time.sleep(0.5)  # basic rate limit: don't hammer the server

    print(f"\nTotal books: {len(results)}")
    with open("libros.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["title", "price", "rating", "availability"])
        w.writeheader()
        w.writerows(results)
    print("Saved to libros.csv")


if __name__ == "__main__":
    main()
