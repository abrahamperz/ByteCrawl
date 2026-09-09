"""URL handling and HTTP-response decoding.

Leaf module: only stdlib + requests. Everything the scrapers and crawlers
need to turn a raw href into a canonical, fetchable URL lives here.
"""

from __future__ import annotations

import re
from urllib.parse import urldefrag, urljoin, urlparse

import requests

DEFAULT_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

# Non-HTML extensions: not worth spending a request on them.
_SKIP_EXT = re.compile(
    r"\.(png|jpe?g|gif|svg|webp|ico|css|js|pdf|zip|gz|tar|mp[34]|avi|mov|woff2?|ttf|xml|rss)$",
    re.IGNORECASE,
)


def normalize(url: str, base: str) -> str | None:
    """Resolve relative URLs, strip #fragments and filter out non-web-page URLs.

    Also canonicalises the empty path to "/": a seed given as
    "https://site.com" and a link to "/" are the same page, and without this
    the crawler spends two requests of its budget to fetch it twice.
    """
    absolute, _ = urldefrag(urljoin(base, url))
    parsed = urlparse(absolute)
    if parsed.scheme not in ("http", "https"):
        return None
    if _SKIP_EXT.search(parsed.path):
        return None
    if not parsed.path:
        absolute = parsed._replace(path="/").geturl()
    return absolute


def _decoded_html(r: requests.Response) -> str:
    """Response text with the correct encoding.

    requests falls back to ISO-8859-1 when the header has no charset
    (RFC 2616), which breaks UTF-8 (£ -> Â£). When that happens, use
    content-based detection instead.
    """
    if r.encoding is None or r.encoding.lower() == "iso-8859-1":
        r.encoding = r.apparent_encoding
    return r.text
