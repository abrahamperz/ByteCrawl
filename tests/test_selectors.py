"""Selector parsing and Page extraction (pure, no network)."""

from bytecraw.core import Page, _split_selector

HTML = """
<html><body>
  <div class="quote">
    <span class="text">To be or not to be</span>
    <small class="author">Shakespeare</small>
    <a class="tag" href="/tag/life">life</a>
    <a class="tag" href="/tag/doubt">doubt</a>
  </div>
  <div class="quote">
    <span class="text">I think therefore I am</span>
    <small class="author">Descartes</small>
    <a class="tag" href="/tag/mind">mind</a>
  </div>
</body></html>
"""


def page():
    return Page(url="https://x.test", html=HTML)


class TestSplitSelector:
    def test_explicit_text(self):
        assert _split_selector("p.price::text") == ("p.price", "text", None)

    def test_attr(self):
        assert _split_selector("h3 a::attr(title)") == ("h3 a", "attr", "title")

    def test_default_is_text(self):
        assert _split_selector("div.quote") == ("div.quote", "text", None)

    def test_strips_whitespace(self):
        assert _split_selector("  a::attr(href) ") == ("a", "attr", "href")


class TestPageExtraction:
    def test_css_first_match(self):
        assert page().css("span.text::text") == "To be or not to be"

    def test_css_attr(self):
        assert page().css("a.tag::attr(href)") == "/tag/life"

    def test_css_no_match_is_none(self):
        assert page().css("h1.missing") is None

    def test_css_all(self):
        assert page().css_all("small.author::text") == ["Shakespeare", "Descartes"]

    def test_css_all_no_match_is_empty(self):
        assert page().css_all("h1.missing") == []

    def test_extract_records_with_list_field(self):
        rows = page().extract("div.quote", {
            "quote": "span.text::text",
            "author": "small.author::text",
            "tags[]": "a.tag::text",
        })
        assert rows == [
            {"quote": "To be or not to be", "author": "Shakespeare",
             "tags": ["life", "doubt"]},
            {"quote": "I think therefore I am", "author": "Descartes",
             "tags": ["mind"]},
        ]

    def test_extract_missing_field_is_none(self):
        rows = page().extract("div.quote", {"missing": "h1.nope::text"})
        assert rows[0]["missing"] is None

    def test_links(self):
        assert page().links() == ["/tag/life", "/tag/doubt", "/tag/mind"]

    def test_tokens_estimate(self):
        p = Page(url="https://x.test", html="a" * 400)
        assert p.tokens() == 100
