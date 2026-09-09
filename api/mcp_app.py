"""Vercel serverless entrypoint for the hosted MCP server.

NOT named mcp.py: a serverless runtime puts the entrypoint's own directory
first on sys.path, so a file called mcp.py here shadows the installed `mcp`
package — bytecrawl.mcp_http's `from mcp.server...` would resolve back to
this file and fail as a circular import. tests/test_packaging.py guards it.

Routed from /mcp (see vercel.json). The ASGI app is created once per
instance; the rate limiter therefore counts per warm instance, which is the
documented best-effort behavior on serverless.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bytecrawl.mcp_http import create_app  # noqa: E402

app = create_app()
