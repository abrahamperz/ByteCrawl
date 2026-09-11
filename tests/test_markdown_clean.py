"""_clean_markdown heuristics: carousel dedup, heading merges, spacing."""

import pytest

from bytecrawl.core import _clean_markdown

LONG_BLOCK = "Power your AI agents with clean structured web data at any scale"


class TestCarouselDedup:
    def test_repeated_long_block_kept_once(self):
        md = "\n\n".join(
            [LONG_BLOCK, "Something else entirely different here", LONG_BLOCK, LONG_BLOCK]
        )
        out = _clean_markdown(md)
        assert out.count(LONG_BLOCK) == 1

    def test_consecutive_short_duplicates_collapse(self):
        out = _clean_markdown("Read more\n\nRead more\n\nRead more")
        assert out == "Read more"

    def test_non_consecutive_short_labels_survive(self):
        # Short repeats far apart are legit content (e.g. section labels).
        md = "Docs\n\n" + LONG_BLOCK + "\n\nDocs"
        out = _clean_markdown(md)
        assert out.count("Docs") == 2


class TestHeadingMerge:
    def test_heading_split_across_lines_is_joined(self):
        out = _clean_markdown("## Start scraping\n today")
        assert "## Start scraping today" in out

    def test_heading_fragment_in_next_block_is_joined(self):
        out = _clean_markdown("# Power AI agents with\n\nclean web data")
        assert "# Power AI agents with clean web data" in out


class TestSpacingFix:
    def test_lost_space_after_sentence_restored(self):
        out = _clean_markdown("We scrape at scale.It's also open source.")
        assert "at scale. It's also open source." in out

    def test_code_blocks_untouched(self):
        code = "```\nresult = fetch(url)#comment.Keep as-is\n```"
        assert _clean_markdown(code) == code

    def test_empty_input(self):
        assert _clean_markdown("") == ""


class TestMainContentFallback:
    """Article extraction is built to discard repetition — which on a listing
    page is the content. It returned the price column of books.toscrape.com
    and dropped all twenty book titles, and the token count then advertised
    that as a 144x saving.
    """

    LISTING = (
        "<html><body><nav>Home Shop</nav>"
        + "".join(
            f"<article class='p'><h3><a title='Book {i}'>Book {i}</a></h3>"
            f"<p class='price'>£{i}.00</p></article>"
            for i in range(20)
        )
        + "</body></html>"
    )

    def test_falls_back_when_extraction_guts_the_page(self, monkeypatch):
        from bytecrawl.core import Page

        page = Page(url="https://x.test/", html=self.LISTING)
        trafilatura = pytest.importorskip("trafilatura")
        # stand in for what it really does here: return a sliver of the page
        monkeypatch.setattr(trafilatura, "extract", lambda *a, **kw: "£0.00\n\n£1.00")
        md = page.markdown()
        assert "Book 0" in md and "Book 19" in md, "titles were dropped"

    def test_keeps_extraction_when_it_looks_sane(self, monkeypatch):
        from bytecrawl.core import Page

        page = Page(url="https://x.test/", html=self.LISTING)
        trafilatura = pytest.importorskip("trafilatura")
        full = page.soup.get_text(" ", strip=True)
        monkeypatch.setattr(trafilatura, "extract", lambda *a, **kw: full)
        assert page.markdown().startswith("Home Shop")

    def test_the_floor_sits_well_below_real_pages(self):
        """Measured: 1.14x of visible text on quotes.toscrape.com and 1.4-1.6x
        on Wikipedia, against 0.19x on the page that broke. A higher floor
        would fire on an article buried in navigation and hand back the
        navigation that was correctly removed."""
        from bytecrawl.core import Page

        assert Page._MAIN_CONTENT_FLOOR < 0.5
