"""Pure graph/text utilities: cosine, normalize, _root_domain, pagerank."""

import pytest

from bytecrawl.crawler import (
    CrawlResult,
    _root_domain,
    cosine,
    normalize,
    pagerank,
    relevance,
)


class TestCosine:
    def test_identical_text_is_one(self):
        assert cosine("machine learning", "machine learning") == pytest.approx(1.0)

    def test_disjoint_text_is_zero(self):
        assert cosine("cats dogs", "quantum physics") == 0.0

    def test_empty_is_zero(self):
        assert cosine("", "anything") == 0.0

    def test_known_value(self):
        # a = {x:1, y:1}, b = {x:1, z:1} → dot=1, norms=sqrt(2)*sqrt(2)=2
        assert cosine("x y", "x z") == pytest.approx(1 / 2)

    def test_accents_tokenized(self):
        assert cosine("análisis de datos", "análisis de datos") == pytest.approx(1.0)


class TestRelevance:
    TEXT = "Books about crime and detective stories"
    URL = "https://books.toscrape.com/catalogue/category/books/mystery_3/index.html"

    def test_exact_term_matches(self):
        assert relevance(self.TEXT, "mystery", self.URL) > 0

    @pytest.mark.parametrize("typo", ["mistery", "mustery", "mystry"])
    def test_one_letter_typos_still_match(self, typo):
        # A slipped keystroke used to score 0.0, which reads as "broken"
        # rather than "no match".
        assert relevance(self.TEXT, typo, self.URL) == pytest.approx(
            relevance(self.TEXT, "mystery", self.URL)
        )

    @pytest.mark.parametrize("miss", ["travel", "poetry", "zzzzzz"])
    def test_absent_topics_stay_zero(self, miss):
        assert relevance(self.TEXT, miss, self.URL) == 0.0

    def test_url_path_counts_as_signal(self):
        # The word appears only in the URL, not the body.
        assert relevance("Some unrelated body copy", "mystery", self.URL) > 0

    def test_short_words_require_exact_match(self):
        # "data"/"date" are as close in trigrams as a real typo, so fuzzy
        # matching on short words would invent hits.
        assert relevance("the date of release", "data") == 0.0

    def test_empty_query_is_zero(self):
        assert relevance(self.TEXT, "", self.URL) == 0.0


class TestNormalize:
    def test_resolves_relative(self):
        assert normalize("/docs", "https://x.test/a/b") == "https://x.test/docs"

    def test_strips_fragment(self):
        assert normalize("https://x.test/p#section", "https://x.test") == "https://x.test/p"

    def test_bare_host_and_root_are_the_same_page(self):
        # Otherwise the crawler burns two budget slots on one page.
        seed = "https://x.test"
        assert normalize(seed, seed) == normalize("/", seed) == "https://x.test/"

    def test_rejects_non_http(self):
        assert normalize("mailto:a@x.test", "https://x.test") is None

    def test_rejects_asset_extensions(self):
        assert normalize("/logo.png", "https://x.test") is None
        assert normalize("/style.css", "https://x.test") is None
        assert normalize("/paper.pdf", "https://x.test") is None


class TestRootDomain:
    def test_subdomains_share_root(self):
        assert _root_domain("www.firecrawl.dev") == _root_domain("docs.firecrawl.dev")

    def test_port_ignored(self):
        assert _root_domain("x.test:8080") == "x.test"

    def test_second_level_tld(self):
        assert _root_domain("www.bbc.co.uk") == "bbc.co.uk"
        assert _root_domain("bbc.co.uk") == "bbc.co.uk"
        assert _root_domain("news.bbc.co.uk") != _root_domain("guardian.co.uk")


class TestPagerank:
    def test_empty_graph(self):
        assert pagerank({}) == {}

    def test_ranks_sum_to_one(self):
        graph = {"A": ["B", "C"], "B": ["C"], "C": ["A"]}
        ranks = pagerank(graph)
        assert sum(ranks.values()) == pytest.approx(1.0)

    def test_most_linked_node_ranks_highest(self):
        # C receives links from both A and B → highest rank.
        graph = {"A": ["B", "C"], "B": ["C"], "C": ["A"]}
        ranks = pagerank(graph)
        assert max(ranks, key=ranks.get) == "C"

    def test_sink_distributes_to_all(self):
        # B has no outlinks; mass must not leak (ranks still sum to 1).
        ranks = pagerank({"A": ["B"], "B": []})
        assert sum(ranks.values()) == pytest.approx(1.0)

    def test_symmetric_graph_equal_ranks(self):
        ranks = pagerank({"A": ["B"], "B": ["A"]})
        assert ranks["A"] == pytest.approx(ranks["B"])


class TestCrawlResult:
    def _result(self):
        return CrawlResult(
            strategy="test",
            pages=[
                {"url": "a", "relevance": 0.9},
                {"url": "b", "relevance": 0.05},
                {"url": "c", "relevance": 0.5},
            ],
        )

    def test_relevant_filters_by_threshold(self):
        assert [p["url"] for p in self._result().relevant(0.1)] == ["a", "c"]

    def test_top_sorts_descending(self):
        assert [p["url"] for p in self._result().top(2)] == ["a", "c"]
