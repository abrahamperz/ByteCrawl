"""
Technique 2 — Dynamic JS with Playwright (real browser)
========================================================
When the initial HTML arrives nearly empty and JavaScript fills in the
content (React/Vue-style apps), requests is not enough. We launch a real
browser, let it run the JS and read the already-rendered DOM.

Practice site: https://quotes.toscrape.com/js (quotes are loaded via JS)

How to know you need this:
  - "View page source" looks empty BUT you do see the data on screen.
  - That means the JS injected it after loading.

Before running (once):
  pip install playwright
  playwright install chromium

Run:  python 02_js_dinamico.py
"""

import json

from playwright.sync_api import sync_playwright


def main():
    results = []
    with sync_playwright() as p:
        # headless=False to SEE the browser (useful while learning / debugging)
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto("https://quotes.toscrape.com/js", wait_until="networkidle")

        while True:
            # Wait for the JS to render the quotes before reading them
            page.wait_for_selector("div.quote")

            for q in page.query_selector_all("div.quote"):
                text = q.query_selector("span.text").inner_text()
                author = q.query_selector("small.author").inner_text()
                tags = [t.inner_text() for t in q.query_selector_all("a.tag")]
                results.append({"quote": text, "author": author, "tags": tags})

            # Pagination: if there's a "Next" button, click and repeat
            next_link = page.query_selector("li.next a")
            if not next_link:
                break
            next_link.click()
            page.wait_for_load_state("networkidle")

        browser.close()

    print(f"Total quotes: {len(results)}")
    with open("frases.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("Saved to frases.json")


if __name__ == "__main__":
    main()
