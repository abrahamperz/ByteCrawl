"""Package surface: version single-sourcing and top-level exports."""

import importlib.metadata
import re
from pathlib import Path

import bytecrawl

_ROOT = Path(__file__).resolve().parent.parent


def test_version_matches_installed_metadata():
    assert bytecrawl.__version__ == importlib.metadata.version("bytecrawl")


def test_changelog_top_entry_matches_version():
    """The newest CHANGELOG heading is the version being shipped —
    __init__.py is the single source, everything else tracks it."""
    text = (_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    top = re.search(r"^## (\d+\.\d+\.\d+)", text, re.M)
    assert top, "no `## X.Y.Z` heading found in CHANGELOG.md"
    assert top.group(1) == bytecrawl.__version__, (
        f"CHANGELOG top is {top.group(1)} but __version__ is {bytecrawl.__version__}"
    )


def test_readmes_advertise_current_version():
    """Both READMEs' 'latest release' line must name the shipped version."""
    for name in ("README.md", "README.es.md"):
        text = (_ROOT / name).read_text(encoding="utf-8")
        assert bytecrawl.__version__ in text, (
            f"{name} does not mention the current version {bytecrawl.__version__}"
        )


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
    so web/mcp/mcp.py would make `from mcp.server...` resolve back to the
    entrypoint and die as a circular import — a failure that only shows up on
    deploy, never locally, because nothing imports through that path here.
    """
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    third_party = {
        "mcp",
        "flask",
        "requests",
        "bs4",
        "lxml",
        "uvicorn",
        "starlette",
        "anyio",
        "pydantic",
        "posthog",
        "dotenv",
        "markdownify",
        "trafilatura",
        "playwright",
        "bytecrawl",
    }
    clashes = [p.name for p in (root / "web/mcp").glob("*.py") if p.stem in third_party]
    assert not clashes, f"web/mcp/ entrypoints shadow installed packages: {clashes}"

    # and every path vercel.json points at has to exist
    cfg = json.loads((root / "vercel.json").read_text())
    srcs = {b["src"] for b in cfg.get("builds", [])}
    srcs |= {r["dest"] for r in cfg.get("routes", []) if "dest" in r}
    missing = [s for s in srcs if not s.startswith("/") and not (root / s).exists()]
    assert not missing, f"vercel.json points at missing files: {missing}"


def test_serverless_requirements_stay_in_sync():
    """Both Vercel builds share one venv, and each install prunes it.

    @vercel/python gives web/landing/app.py and web/mcp/mcp_app.py a single virtualenv;
    uv treats each requirements file as a sync, so whichever build runs second
    removes every package the other one needed and the first is packaged
    against a venv missing its dependencies. A deploy died on a missing
    babel dist-info this way. The two files carry the union and have to stay
    identical.
    """
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent

    def pkgs(path):
        return [
            ln.strip()
            for ln in (root / path).read_text().splitlines()
            if ln.strip() and not ln.startswith("#")
        ]

    demo, api = pkgs("web/landing/requirements.txt"), pkgs("web/mcp/requirements.txt")
    assert demo == api, (
        "web/landing/requirements.txt and web/mcp/requirements.txt must match — they "
        f"install into the same venv.\n  demo only: {set(demo) - set(api)}\n"
        f"  api only:  {set(api) - set(demo)}"
    )
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
    canonical = re.search(
        r'Homepage = "(https://github\.com/[^"]+)"', (root / "pyproject.toml").read_text()
    ).group(1)
    skill = (root / "web/landing/static/SKILL.md").read_text()
    found = set(re.findall(r"https://github\.com/[A-Za-z0-9._/-]+", skill))
    wrong = {u for u in found if not u.startswith(canonical)}
    assert not wrong, f"SKILL.md links a repo that isn't {canonical}: {wrong}"
    assert found, "SKILL.md no longer points at the repo at all"


def test_the_skill_does_not_order_the_agent_around():
    """A document fetched from a URL must not command an agent to modify the
    machine it is running on.

    An earlier version opened with "install yourself before anything else",
    and agents refused it — correctly. One told its user the page was trying
    to auto-trigger persistent changes to their config, which leaves the
    project looking like the attack rather than the tool. The install is now
    offered to the person, near the end, and only when they ask.
    """
    import re
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    skill = (root / "web/landing/static/SKILL.md").read_text()
    sections = skill.split("## ")
    head, opening = sections[0], sections[1]

    # nothing about writing to the machine before the reader knows what this is
    for probe in ("~/.claude/skills", "mcpServers", "mcp add"):
        assert probe not in head + opening, (
            f"{probe!r} appears before the skill has said what it does"
        )

    # the option still has to exist, and be framed as the person's choice
    assert "~/.claude/skills/bytecrawl" in skill, "no way to install it at all"
    flat = " ".join(skill.split())  # the prose is hard-wrapped
    assert "do not change their configuration on your own" in flat
    assert "ask first" in flat

    # The button has to carry the instruction, because this file must not.
    # "Read and follow <url>" only asked the agent to read, so it read and then
    # asked what to do — correct, and not what someone pressing "Setup for
    # agents" wanted. Pasted by the user, a request to install is their own
    # instruction, which an agent can act on; the same words on this page would
    # be a prompt injection.
    landing = (root / "web/landing/templates/landing.html").read_text()
    setup = re.search(r"const SETUP_CMD = (.+?);\n", landing, re.S).group(1)
    assert "agent-onboarding/SKILL.md" in setup, "the button lost the URL"
    assert "MCP server" in setup and "skill" in setup, (
        "the button must ask for both — the server alone leaves /bytecrawl missing"
    )


def _repo_version():
    import bytecrawl

    return bytecrawl.__version__


def test_every_version_in_the_repo_agrees():
    """One number, four places. The /docs page said v1.0.0 through three
    releases because it was written into the template and nothing connected it
    to the package — a reader trusting it installed a version behind.
    """
    import re
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    version = _repo_version()
    wrong = {}

    # the changelog's top section is the release being prepared
    changelog = (root / "CHANGELOG.md").read_text()
    top = re.search(r"^## (\d+\.\d+\.\d+)", changelog, re.M)
    assert top, "CHANGELOG has no versioned section"
    if top.group(1) != version:
        wrong["CHANGELOG.md"] = top.group(1)

    # both READMEs advertise it to anyone who never opens the changelog
    for name, label in (
        ("README.md", r"\*\*Latest release\*\*: \*\*([\d.]+)\*\*"),
        ("README.es.md", r"\*\*Última versión\*\*: \*\*([\d.]+)\*\*"),
    ):
        m = re.search(label, (root / name).read_text())
        assert m, f"{name} no longer states a version"
        if m.group(1) != version:
            wrong[name] = m.group(1)

    # the docs page renders it now; a literal here means it can drift again
    docs = (root / "web/landing/templates/docs.html").read_text()
    hardcoded = re.search(r'<span class="pill">v(\d+\.\d+\.\d+)</span>', docs)
    if hardcoded:
        wrong["docs.html (hardcoded)"] = hardcoded.group(1)

    assert not wrong, f"version is {version}, but: {wrong}"


def test_the_skill_can_tell_it_is_stale():
    """Installing the skill copies it, so it is a snapshot and nothing pushes
    fixes to it — a repo URL that 404s stayed on disk until it was fetched
    again. /agent-onboarding/skill.json publishes the hash of the served file so
    an agent can hash its own copy and find out. A hash, not a version string,
    because nobody has to remember to bump it.
    """
    import hashlib
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    body = (root / "web/landing/static/SKILL.md").read_bytes()
    app_py = (root / "web/landing/routes.py").read_text()
    assert '"/agent-onboarding/skill.json"' in app_py, "the version endpoint is gone"

    # the skill has to tell the agent how to use it, and to report rather than act
    skill = body.decode()
    flat = " ".join(skill.split())
    assert "skill.json" in skill, "the skill never mentions how to check"
    assert "shasum -a 256" in skill
    assert "do not fetch it yourself" in flat, (
        "an agent overwriting a file in someone's home because a hash differed "
        "is what the rest of this document tells it to refuse"
    )
    # and it has to look on its own, not wait for a symptom: the failure that
    # prompted this was a link that 404s, which errors nothing
    assert "Check once, the first time you use this in a session" in flat

    # The endpoint must hash the file, not a copy of it. Asserted by reading the
    # route rather than running it: importing the landing app drags in Flask,
    # which the package does not depend on and CI does not install — the landing
    # site is a separate application that happens to live in this repository.
    route = app_py[app_py.index('"/agent-onboarding/skill.json"') :]
    route = route[: route.index("@pages_bp.route", 1)]
    assert "read_bytes()" in route and "hashlib.sha256" in route, (
        "the endpoint must hash the file it serves, not a stored value"
    )
    assert "SKILL.md" in route

    # a stored hash would be the drift this is meant to prevent
    assert hashlib.sha256(body).hexdigest()[:8] not in app_py, (
        "the current hash is hardcoded somewhere — it has to be computed"
    )
