"""Smoke tests against the deployed site. Not run by CI.

    pytest -m smoke

Every bug found on release day was invisible to the offline suite, because
each one lived in the gap between what the project says and what the deploy
does: a serverless entrypoint that shadowed its own dependency, two builds
pruning each other's venv, a transport that answered 421 to every real host,
a skill file pointing at a repo that 404s, and documented response fields
that no method returns. All five needed a request to production to see.

These hit the real service, so they need the network and they cost the site
a handful of requests. Keep them few and keep them cheap.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

import pytest

pytestmark = pytest.mark.smoke

BASE = "https://bytecrawl.vercel.app"
TIMEOUT = 60


def _get(path: str, **params) -> tuple[dict, str]:
    url = f"{BASE}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=TIMEOUT) as r:  # noqa: S310
        return json.loads(r.read()), r.headers.get("content-type", "")


def _rpc(method: str, params: dict | None = None) -> dict:
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method,
                       "params": params or {}}).encode()
    req = urllib.request.Request(
        f"{BASE}/mcp", data=body,
        headers={"Content-Type": "application/json",
                 "Accept": "application/json, text/event-stream"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:  # noqa: S310
        return json.loads(r.read().decode())


class TestAgentSkill:
    """The file agents are handed as the entry point ("Read and follow <url>")."""

    def test_served_as_markdown(self):
        req = urllib.request.Request(f"{BASE}/agent-onboarding/SKILL.md")
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:  # noqa: S310
            body = r.read().decode()
            assert "markdown" in r.headers.get("content-type", "")
        assert len(body) > 5000

    def test_every_link_it_gives_out_resolves(self):
        """It shipped pointing at a repo that 404s, and nothing caught it."""
        import re
        req = urllib.request.Request(f"{BASE}/agent-onboarding/SKILL.md")
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:  # noqa: S310
            body = r.read().decode()
        for url in sorted(set(re.findall(r"https://github\.com/[A-Za-z0-9._/-]+", body))):
            try:
                urllib.request.urlopen(  # noqa: S310
                    urllib.request.Request(url, method="HEAD"), timeout=TIMEOUT)
            except urllib.error.HTTPError as e:
                pytest.fail(f"SKILL.md points at {url} — HTTP {e.code}")


class TestHttpApi:
    """The fields the skill promises are the fields the API returns.

    These drifted apart once already: the skill documented `status` and
    `elapsed`, which no method has ever returned.
    """

    @pytest.mark.parametrize("method,extra,expected", [
        ("markdown", {}, {"markdown", "tokens"}),
        ("text", {}, {"text"}),
        ("links", {}, {"links"}),
        ("extract", {"select": "h3 a::attr(title)"}, {"values", "select"}),
    ])
    def test_documented_fields(self, method, extra, expected):
        out, _ = _get("/api", url="books.toscrape.com", method=method, **extra)
        assert {"url", "method"} <= set(out), "url and method are on every response"
        assert expected <= set(out)
        assert "status" not in out and "elapsed" not in out

    def test_compare_returns_a_verdict(self):
        out, _ = _get("/api", url="books.toscrape.com", method="compare",
                      query="fiction", pages=3)
        assert set(out["strategies"]) == {"bfs", "shark", "opic"}
        assert out["winner"] in out["tied"]

    def test_compare_without_a_query_is_rejected(self):
        with pytest.raises(urllib.error.HTTPError) as e:
            _get("/api", url="books.toscrape.com", method="compare")
        assert e.value.code == 400


class TestHostedMcp:
    def test_six_tools(self):
        """Deployed once answering 421 to every request, and once not at all."""
        names = {t["name"] for t in _rpc("tools/list")["result"]["tools"]}
        assert names == {"fetch_markdown", "extract", "list_links",
                         "focused_crawl", "compare_strategies", "fetch_json_api"}

    def test_ssrf_guard_is_live(self):
        """The one property that must never regress: a hosted scraper that
        forwards to link-local addresses is an open door to cloud metadata."""
        out = _rpc("tools/call", {"name": "fetch_markdown",
                                  "arguments": {"url": "http://169.254.169.254/"}})
        text = json.dumps(out)
        assert "non-public" in text, text[:200]


class TestPublishedVersion:
    """What the repo advertises has to be installable — to the minor.

    Patch releases here are often copy: a reworded skill, a grid that did not
    fit on a phone. None of that reaches `pip install`, and publishing a
    PyPI release whose code is byte-identical to the last one is noise. So the
    check is on major.minor, which is what actually describes the feature set.

    What that gives up: a patch that *does* change the library — the hosted
    server once refused every request with a 421 and the fix shipped as
    1.1.1 — would go unpublished without this failing. Publishing is still the
    right move for those; this test just stops policing the ones that are only
    words.
    """

    @staticmethod
    def _mm(v: str) -> tuple[int, int]:
        major, minor = v.split(".")[:2]
        return int(major), int(minor)

    def _pypi(self) -> str:
        with urllib.request.urlopen(  # noqa: S310
                "https://pypi.org/pypi/bytecrawl/json", timeout=TIMEOUT) as r:
            return json.loads(r.read())["info"]["version"]

    def test_the_readme_version_is_installable(self):
        """The README states a "Latest release" to people who will never open
        the changelog. If it names a feature set that is not on PyPI, everyone
        who follows it installs something older and never learns why."""
        import re
        from pathlib import Path

        import bytecrawl

        root = Path(__file__).resolve().parent.parent
        advertised = re.search(r"\*\*Latest release\*\*: \*\*([\d.]+)\*\*",
                               (root / "README.md").read_text()).group(1)
        assert advertised == bytecrawl.__version__      # offline suite covers this
        published = self._pypi()
        assert self._mm(advertised) == self._mm(published), (
            f"README and the package say {advertised}, PyPI serves {published} — "
            "publish it, or the docs describe a release nobody can install")
        assert self._mm(published) <= self._mm(advertised), (
            f"PyPI is ahead of the repo: {published} vs {advertised}")

    def test_the_site_shows_the_published_version(self):
        """/docs renders it from the package, so a deploy behind PyPI shows a
        version people cannot get."""
        import re
        req = urllib.request.Request(f"{BASE}/docs")
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:  # noqa: S310
            shown = re.search(r'<span class="pill">v([\d.]+)</span>',
                              r.read().decode()).group(1)
        assert self._mm(shown) == self._mm(self._pypi()), \
            f"/docs shows v{shown}, PyPI serves {self._pypi()}"
