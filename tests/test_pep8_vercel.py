"""PEP 8 on the code Vercel actually deploys.

CI lints `bytecrawl tests` — never `demo/` or `api/`. But those two
directories are exactly what vercel.json builds and ships: the serverless
entrypoints a visitor's request runs through. They were held to a lower
bar than the library behind them, and drifted (long i18n strings, imports
after the sys.path shim) until nothing flagged it.

This checks pycodestyle — the E and W codes, which *are* PEP 8 — over the
Python sources vercel.json declares as builds, at the project's line
length (pyproject.toml, 100). Reading the file list from vercel.json means
a new entrypoint is covered the moment it's deployed, with no edit here.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def _deployed_python_sources() -> list[str]:
    cfg = json.loads((ROOT / "vercel.json").read_text())
    return [b["src"] for b in cfg.get("builds", []) if b["src"].endswith(".py")]


@pytest.mark.skipif(shutil.which("ruff") is None, reason="ruff not installed")
def test_vercel_entrypoints_follow_pep8():
    sources = _deployed_python_sources()
    assert sources, "vercel.json declares no Python builds — nothing to check"

    proc = subprocess.run(
        ["ruff", "check", "--select", "E,W", *sources], cwd=ROOT, capture_output=True, text=True
    )
    assert proc.returncode == 0, (
        "Vercel-deployed code violates PEP 8:\n" + proc.stdout + proc.stderr
    )
