"""
EXTRA — HTML to Markdown to save LLM tokens
===========================================
If you're going to feed a page to an LLM for data extraction, raw HTML is
FULL of noise (<div>, classes, styles, scripts) that burns tons of tokens
without adding information.

Converting that HTML to clean Markdown:
  - removes tags, attributes, styles and scripts,
  - keeps the content and structure (headings, lists, tables, links),
  - typically cuts the token count by 5x to 10x.

Two tools:
  - markdownify: converts HTML -> Markdown directly.
  - trafilatura: additionally detects and extracts ONLY the main content
                 (drops menus, banners, footers) -> even fewer tokens.

Before running:  pip install requests markdownify trafilatura
Run:             python 07_html_a_markdown.py
"""

import requests
from markdownify import markdownify
import trafilatura

URL = "https://quotes.toscrape.com/"
HEADERS = {"User-Agent": "Mozilla/5.0 (scraping-practice)"}


def estimate_tokens(text: str) -> int:
    """Quick approximation: ~4 characters per token in English/Spanish."""
    return len(text) // 4


def main():
    html = requests.get(URL, headers=HEADERS, timeout=15).text

    # Option A: markdownify (converts the whole HTML)
    md_full = markdownify(html, strip=["script", "style"])

    # Option B: trafilatura (extracts only the main content, as markdown)
    md_main = trafilatura.extract(html, output_format="markdown") or ""

    print("=== Size comparison (approximate tokens) ===")
    print(f"Raw HTML:              ~{estimate_tokens(html):>6} tokens")
    print(f"Markdown (markdownify):~{estimate_tokens(md_full):>6} tokens")
    print(f"Markdown (trafilatura):~{estimate_tokens(md_main):>6} tokens")

    with open("pagina.md", "w", encoding="utf-8") as f:
        f.write(md_main or md_full)
    print("\nClean markdown saved to pagina.md")
    print("That .md is what you'd hand to an LLM: same info, a fraction of the tokens.")


if __name__ == "__main__":
    main()
