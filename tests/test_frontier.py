"""Frontier: max-heap ordering, FIFO tie-break, lazy deletion on re-push."""

from bytecraw.crawler import Frontier


class TestOrdering:
    def test_pops_highest_score_first(self):
        f = Frontier()
        f.push("low", 0.1)
        f.push("high", 0.9)
        f.push("mid", 0.5)
        assert [f.pop()[0] for _ in range(3)] == ["high", "mid", "low"]

    def test_fifo_tie_break_on_equal_scores(self):
        f = Frontier()
        f.push("first", 1.0)
        f.push("second", 1.0)
        assert f.pop()[0] == "first"
        assert f.pop()[0] == "second"

    def test_empty_pop_returns_none(self):
        assert Frontier().pop() is None


class TestLazyDeletion:
    def test_repush_higher_score_wins_single_pop(self):
        # OPIC re-pushes URLs as cash accumulates: the heap holds a stale
        # entry which must be discarded on pop, not returned twice.
        f = Frontier()
        f.push("u", 1.0)
        f.push("u", 3.0)
        assert f.pop() == ("u", 3.0)
        assert f.pop() is None
        assert len(f) == 0

    def test_repush_lower_score_ignored(self):
        f = Frontier()
        f.push("u", 3.0)
        f.push("u", 1.0)
        assert f.pop() == ("u", 3.0)
        assert f.pop() is None

    def test_contains_and_len(self):
        f = Frontier()
        f.push("a", 1.0)
        f.push("b", 2.0)
        assert "a" in f and "b" in f and len(f) == 2
        f.pop()
        assert "b" not in f and len(f) == 1
