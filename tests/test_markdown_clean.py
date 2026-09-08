"""_clean_markdown heuristics: carousel dedup, heading merges, spacing."""

from bytecrawl.core import _clean_markdown

LONG_BLOCK = "Power your AI agents with clean structured web data at any scale"


class TestCarouselDedup:
    def test_repeated_long_block_kept_once(self):
        md = "\n\n".join([LONG_BLOCK, "Something else entirely different here",
                          LONG_BLOCK, LONG_BLOCK])
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
