"""Crawl strategies over the in-memory site (see conftest.SITE).

The fake site has a branch relevant to "machine learning" (/ml/*) and an
irrelevant one (/cats/*), so best-first strategies should visibly prefer
the former.
"""

import pytest

from bytecrawl import BFS, OPIC, SharkSearch

SEED = "https://s.test/"


def crawler_kwargs():
    return {"delay": 0.0}


class TestBFS:
    def test_visits_level_by_level(self, fake_site):
        BFS(**crawler_kwargs()).crawl(SEED, max_pages=5)
        # Seed first, then both depth-1 pages before any depth-2 page.
        assert fake_site[0] == SEED
        assert set(fake_site[1:3]) == {"https://s.test/ml", "https://s.test/cats"}
        assert set(fake_site[3:5]) == {"https://s.test/ml/deep", "https://s.test/cats/more"}

    def test_max_depth_excludes_deeper_pages(self, fake_site):
        result = BFS(**crawler_kwargs()).crawl(SEED, max_pages=10, max_depth=1)
        urls = {p["url"] for p in result.pages}
        assert "https://s.test/ml/deep" not in urls
        assert "https://s.test/cats/more" not in urls

    def test_graph_matches_site_edges(self, fake_site):
        result = BFS(**crawler_kwargs()).crawl(SEED, max_pages=5)
        assert result.graph[SEED] == ["https://s.test/ml", "https://s.test/cats"]

    def test_same_domain_filters_external_links(self, fake_site):
        result = BFS(**crawler_kwargs()).crawl(SEED, max_pages=10)
        for targets in result.graph.values():
            assert not any("other.test" in t for t in targets)

    def test_stats(self, fake_site):
        result = BFS(**crawler_kwargs()).crawl(SEED, max_pages=3)
        assert result.stats["requests"] == 3
        assert result.stats["errors"] == 0
        assert result.strategy == "bfs"

    def test_invalid_url_raises(self):
        with pytest.raises(ValueError):
            BFS(**crawler_kwargs()).crawl("mailto:nope@x.test")


class TestSharkSearch:
    def test_relevant_branch_visited_before_irrelevant(self, fake_site):
        SharkSearch(query="machine learning", **crawler_kwargs()).crawl(SEED, max_pages=4)
        assert fake_site.index("https://s.test/ml") < fake_site.index("https://s.test/cats")

    def test_irrelevant_branch_decays_geometrically(self, fake_site):
        shark = SharkSearch(query="machine learning", delta=0.5, **crawler_kwargs())
        shark.crawl(SEED, max_pages=5)
        # /cats has no query overlap, so /cats/more inherits delta * inherited(/cats).
        cats = shark._inherited["https://s.test/cats"]
        assert shark._inherited["https://s.test/cats/more"] == pytest.approx(shark.delta * cats)

    def test_relevance_scores_favor_ml_pages(self, fake_site):
        result = SharkSearch(query="machine learning", **crawler_kwargs()).crawl(SEED, max_pages=5)
        by_url = {p["url"]: p["relevance"] for p in result.pages}
        assert by_url["https://s.test/ml"] > by_url["https://s.test/cats"]

    def test_top_orders_by_relevance(self, fake_site):
        result = SharkSearch(query="machine learning", **crawler_kwargs()).crawl(SEED, max_pages=5)
        top = result.top(3)
        assert top[0]["relevance"] >= top[1]["relevance"] >= top[2]["relevance"]


class TestOPIC:
    def test_cash_is_conserved(self, fake_site):
        # The paper's invariant: circulating cash always sums to the initial
        # 1.0 (history is a ledger of what passed through, not part of it).
        opic = OPIC(**crawler_kwargs())
        opic.crawl(SEED, max_pages=3)
        assert sum(opic.cash.values()) == pytest.approx(1.0)

    def test_cash_conserved_after_full_crawl_with_sinks(self, fake_site):
        opic = OPIC(**crawler_kwargs())
        opic.crawl(SEED, max_pages=10)  # includes sink pages (no outlinks)
        assert sum(opic.cash.values()) == pytest.approx(1.0)

    def test_history_accumulates_importance(self, fake_site):
        opic = OPIC(**crawler_kwargs())
        opic.crawl(SEED, max_pages=5)
        # The seed received the full initial cash, so it leads the ledger.
        assert opic.history[SEED] == max(opic.history.values())

    def test_visits_all_reachable_pages(self, fake_site):
        result = OPIC(**crawler_kwargs()).crawl(SEED, max_pages=10)
        assert {p["url"] for p in result.pages} == set(u for u in fake_site)


class TestErrorHandling:
    def test_fetch_errors_counted_not_fatal(self, fake_site, monkeypatch):
        from bytecrawl.crawler import Crawler

        original = Crawler.score_links

        def with_broken_link(self, url, links, relevance, depth):
            scored = original(self, url, links, relevance, depth)
            if url == SEED:  # inject a URL that will 404 in fake_static
                scored.append(("https://s.test/broken", 99.0))
            return scored

        monkeypatch.setattr(Crawler, "score_links", with_broken_link)
        result = BFS(**crawler_kwargs()).crawl(SEED, max_pages=10)
        assert result.stats["errors"] == 1
        assert len(result.pages) == 5  # the 5 real pages still crawled
