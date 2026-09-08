"""Package surface: version single-sourcing and top-level exports."""

import importlib.metadata

import bytecrawl


def test_version_matches_installed_metadata():
    assert bytecrawl.__version__ == importlib.metadata.version("bytecrawl")


def test_top_level_exports():
    from bytecrawl import (  # noqa: F401
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
    for name in bytecrawl.__all__:
        assert hasattr(bytecrawl, name), name
