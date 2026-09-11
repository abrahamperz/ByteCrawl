"""Reusable authenticated sessions.

A Session persists cookies and headers across requests: log in once (with
optional CSRF handling) or attach a bearer token, then fetch pages behind
the auth wall.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import requests
from bs4 import BeautifulSoup

from .page import Page
from .url import _decoded_html, _raise_for_status

if TYPE_CHECKING:
    from .scraper import Scraper


class Session:
    """Reusable authenticated session (cookies + headers persist)."""

    def __init__(self, scraper: Scraper):
        self._s = requests.Session()
        self._s.headers.update({"User-Agent": scraper.user_agent})
        self._scraper = scraper

    def login(self, url: str, data: dict, csrf_field: str | None = None) -> Session:
        """Logs in. If csrf_field is given, reads it from the form first."""
        if csrf_field:
            r = self._s.get(url, timeout=self._scraper.timeout)
            _raise_for_status(r)
            form = BeautifulSoup(_decoded_html(r), "lxml")
            token = form.select_one(f'input[name="{csrf_field}"]')
            if token:
                data = {**data, csrf_field: token.get("value", "")}
        r = self._s.post(url, data=data, timeout=self._scraper.timeout)
        _raise_for_status(r)
        return self

    def bearer(self, token: str) -> Session:
        self._s.headers["Authorization"] = f"Bearer {token}"
        return self

    def fetch(self, url: str) -> Page:
        t0 = time.perf_counter()
        r = self._s.get(url, timeout=self._scraper.timeout)
        _raise_for_status(r)
        return Page(
            url=url,
            html=_decoded_html(r),
            method="static",
            elapsed=round(time.perf_counter() - t0, 3),
            status=r.status_code,
        )
