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


def test_serverless_entrypoints_do_not_shadow_dependencies():
    """A file in api/ named after an installed package shadows it.

    Serverless runtimes put the entrypoint's own directory first on sys.path,
    so api/mcp.py would make `from mcp.server...` resolve back to the
    entrypoint and die as a circular import — a failure that only shows up on
    deploy, never locally, because nothing imports through that path here.
    """
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    third_party = {"mcp", "flask", "requests", "bs4", "lxml", "uvicorn",
                   "starlette", "anyio", "pydantic", "posthog", "dotenv",
                   "markdownify", "trafilatura", "playwright", "bytecrawl"}
    clashes = [p.name for p in (root / "api").glob("*.py")
               if p.stem in third_party]
    assert not clashes, f"api/ entrypoints shadow installed packages: {clashes}"

    # and every path vercel.json points at has to exist
    cfg = json.loads((root / "vercel.json").read_text())
    srcs = {b["src"] for b in cfg.get("builds", [])}
    srcs |= {r["dest"] for r in cfg.get("routes", []) if "dest" in r}
    missing = [s for s in srcs if not s.startswith("/") and not (root / s).exists()]
    assert not missing, f"vercel.json points at missing files: {missing}"


def test_serverless_requirements_stay_in_sync():
    """Both Vercel builds share one venv, and each install prunes it.

    @vercel/python gives demo/app.py and api/mcp_app.py a single virtualenv;
    uv treats each requirements file as a sync, so whichever build runs second
    removes every package the other one needed and the first is packaged
    against a venv missing its dependencies. A deploy died on a missing
    babel dist-info this way. The two files carry the union and have to stay
    identical.
    """
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent

    def pkgs(path):
        return [ln.strip() for ln in (root / path).read_text().splitlines()
                if ln.strip() and not ln.startswith("#")]

    demo, api = pkgs("demo/requirements.txt"), pkgs("api/requirements.txt")
    assert demo == api, (
        "demo/requirements.txt and api/requirements.txt must match — they "
        f"install into the same venv.\n  demo only: {set(demo) - set(api)}\n"
        f"  api only:  {set(api) - set(demo)}")
    # the hosted MCP server cannot start without these
    assert any(p.startswith("mcp") for p in api)
    assert "trafilatura" in api and "flask" in api
