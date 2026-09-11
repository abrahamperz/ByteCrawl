"""Shared safety helpers for public-facing servers (MCP + REST API).

A hosted scraper must not become an open proxy into the host's private
network, so every URL a public endpoint is asked to fetch goes through
`assert_public_url` first.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse


def assert_public_url(url: str) -> None:
    """Reject URLs that could reach private infrastructure.

    Resolves the hostname and requires every returned address to be globally
    routable. Blocks localhost, RFC1918 ranges, link-local (cloud metadata
    endpoints like 169.254.169.254) and other reserved space.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Only http(s) URLs are allowed, got: {parsed.scheme or 'none'}")
    host = parsed.hostname
    if not host:
        raise ValueError("URL has no hostname")
    try:
        infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
    except socket.gaierror as e:
        raise ValueError(f"Cannot resolve host: {host}") from e
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global or ip.is_multicast:
            raise ValueError(f"URL resolves to a non-public address ({ip}) — refusing to fetch it")
