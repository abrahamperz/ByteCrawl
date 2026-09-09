"""Vercel serverless entrypoint for the hosted MCP server.

Routed from /mcp (see vercel.json). The ASGI app is created once per
instance; the rate limiter therefore counts per warm instance, which is the
documented best-effort behavior on serverless.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bytecrawl.mcp_http import create_app  # noqa: E402

app = create_app()
