"""PostHog analytics for the demo, isolated so the routes stay about HTTP.

One process-wide client, a per-session distinct id, a ``track`` helper that
never lets analytics break a request, and ``register(app)`` to wire the
per-response flush the factory calls.
"""

from __future__ import annotations

import atexit
import os
import uuid

from flask import Flask, Response, session
from posthog import Posthog

posthog_client = Posthog(
    project_api_key=os.environ.get("POSTHOG_PROJECT_TOKEN", ""),
    host=os.environ.get("POSTHOG_HOST", "https://us.i.posthog.com"),
    enable_exception_autocapture=True,
)
atexit.register(posthog_client.shutdown)


def _get_distinct_id() -> str:
    if "distinct_id" not in session:
        session["distinct_id"] = str(uuid.uuid4())
    return session["distinct_id"]


def track(event: str, properties: dict) -> None:
    """Capture an event for the current visitor. Never raises: analytics must
    not break a response (network, empty token, etc.)."""
    try:
        posthog_client.capture(_get_distinct_id(), event, properties=properties)
    except Exception:
        pass


def register(app: Flask) -> None:
    """Flush PostHog after every response.

    On serverless (Vercel) the function freezes after responding and
    posthog-python's background send can get lost, so force the flush. It must
    never break the response if PostHog fails.
    """

    @app.after_request
    def _flush_posthog(response: Response) -> Response:
        try:
            posthog_client.flush()
        except Exception:
            pass
        return response
