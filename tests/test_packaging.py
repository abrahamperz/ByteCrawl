"""Package surface: version single-sourcing and top-level exports."""

import importlib.metadata

import bytecraw


def test_version_matches_installed_metadata():
    assert bytecraw.__version__ == importlib.metadata.version("bytecraw")


def test_top_level_exports():
    from bytecraw import (  # noqa: F401
        BFS,
        OPIC,
        Crawler,
        CrawlResult,
        Page,
        Scraper,
        Session,
        SharkSearch,
        cosine,
        pagerank,
    )


def test_all_is_importable():
    for name in bytecraw.__all__:
        assert hasattr(bytecraw, name), name
