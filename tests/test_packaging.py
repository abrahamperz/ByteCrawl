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


def test_agent_skill_points_at_the_real_repo():
    """SKILL.md is handed to agents as the entry point ("Read and follow <url>").

    It shipped pointing at github.com/aperezdc-bytecrawl/bytecrawl, which 404s,
    while the other twelve mentions across the project use the real URL. An
    agent that wanted to read the source or file an issue hit a dead end, and
    nothing here would have caught it.
    """
    import re
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    canonical = re.search(r'Homepage = "(https://github\.com/[^"]+)"',
                          (root / "pyproject.toml").read_text()).group(1)
    skill = (root / "demo/static/SKILL.md").read_text()
    found = set(re.findall(r"https://github\.com/[A-Za-z0-9._/-]+", skill))
    wrong = {u for u in found if not u.startswith(canonical)}
    assert not wrong, f"SKILL.md links a repo that isn't {canonical}: {wrong}"
    assert found, "SKILL.md no longer points at the repo at all"


def test_skill_tells_the_agent_to_install_itself():
    """The "Setup for agents" button copies `Read and follow <url>`, which
    lasts one turn. The skill has to convert that into a real install or the
    button promises setup and delivers a single answer."""
    import re
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    skill = (root / "demo/static/SKILL.md").read_text()
    landing = (root / "demo/templates/landing.html").read_text()

    # the button still copies the line the skill expects to arrive by
    assert "Read and follow https://bytecrawl.vercel.app/agent-onboarding/SKILL.md" in landing

    head = skill.split("## ")[1]          # the first section an agent reads
    assert head.lower().startswith("first, install yourself"), \
        "self-install is no longer the first instruction"
    assert "~/.claude/skills/bytecrawl" in head
    # and it has to write the file the skills directory expects
    assert re.search(r"curl -so ~/\.claude/skills/bytecrawl/SKILL\.md", head)
