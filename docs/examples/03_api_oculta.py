"""
Technique 3 — Intercepted API / network
=======================================
The PRO trick. Almost every time a page loads data with JS, under the hood
it's asking an API that returns clean JSON. If you copy that call, you skip
ALL the HTML and get data that's already structured.

How to find the API (do it in your browser):
  1. Open DevTools (F12) -> "Network" tab.
  2. Filter by "Fetch/XHR".
  3. Reload or interact with the page.
  4. Look for requests returning JSON. That's the API.
  5. Right click the request -> "Copy as cURL" to see headers/tokens.

Practice site: quotes.toscrape.com has a hidden JSON endpoint its own
frontend consumes:  https://quotes.toscrape.com/api/quotes?page=N

Run:  python 03_api_oculta.py
"""

import json
import time

import requests

API = "https://quotes.toscrape.com/api/quotes"
HEADERS = {"User-Agent": "Mozilla/5.0 (scraping-practice)"}


def main():
    results = []
    page = 1
    with requests.Session() as s:
        s.headers.update(HEADERS)
        while True:
            r = s.get(API, params={"page": page}, timeout=15)
            r.raise_for_status()
            data = r.json()  # clean JSON, no HTML parsing

            for q in data["quotes"]:
                results.append(
                    {
                        "quote": q["text"],
                        "author": q["author"]["name"],
                        "tags": q["tags"],
                    }
                )

            if not data.get("has_next"):
                break
            page += 1
            time.sleep(0.3)

    print(f"Total quotes: {len(results)}")
    with open("frases_api.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("Saved to frases_api.json")
    print("\nNote: compare this script's SPEED vs 02_js_dinamico.py.")
    print("Same data, but no browser = far faster and more stable.")


if __name__ == "__main__":
    main()
