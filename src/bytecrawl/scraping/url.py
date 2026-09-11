"""URL handling and HTTP-response decoding.

Leaf module: only stdlib + requests. Everything the scrapers and crawlers
need to turn a raw href into a canonical, fetchable URL lives here.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
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


class BlockedError(requests.HTTPError):
    """A site's bot-protection / WAF refused the request.

    Subclasses :class:`requests.HTTPError`, so code that already does
    ``except requests.HTTPError`` keeps catching it. Catch ``BlockedError``
    specifically to tell a bot wall (Cloudflare, DataDome, …) apart from an
    ordinary 404/500.

    Carries the ``wall`` name and ``status`` so a caller can render a
    structured message without re-parsing the string.
    """

    def __init__(self, *args: object, wall: str | None = None, status: int | None = None) -> None:
        super().__init__(*args)
        self.wall = wall
        self.status = status


# The one wording for "the seed never loaded", so the API, the MCP tools and
# the crawl path (via CrawlResult.raise_for_seed) all say the same thing and a
# reword lands everywhere at once. UnreachableError() with no message uses it.
UNREACHABLE_MESSAGE = (
    "Couldn't open that page — the site didn't respond. Check the URL is real and complete."
)


# The one wording for "the site is throttling us", shared like UNREACHABLE_MESSAGE
# so a 429 reads the same on every surface. RateLimitError() with no message uses
# it; the actual seconds-to-wait ride alongside on `.retry_after`.
RATE_LIMIT_MESSAGE = (
    "The site is rate-limiting us (HTTP 429 Too Many Requests). It's up and "
    "reachable — just asking for fewer requests. Wait a moment and try again."
)


def _retry_after_seconds(value: str | None) -> int | None:
    """Seconds to wait from a ``Retry-After`` header, or ``None``.

    RFC 7231 allows either a delta in seconds ("120") or an HTTP date. We read
    both: the numeric form directly, and the date form as the delta from now
    (clamped at zero, so a past date reads as "retry now" rather than negative).
    """
    if not value:
        return None
    value = value.strip()
    if value.isdigit():
        return int(value)
    try:
        when = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if when is None:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    delta = (when - datetime.now(timezone.utc)).total_seconds()
    return max(0, int(delta))


class RateLimitError(requests.HTTPError):
    """The seed answered 429 Too Many Requests — reachable, just throttled.

    Distinct from :class:`BlockedError` (a bot wall refusing automated access
    outright) and :class:`UnreachableError` (the page never loaded at all): a
    rate limit is temporary and often carries a ``Retry-After`` saying how long
    to wait. Subclasses :class:`requests.HTTPError`, so ``except
    requests.HTTPError`` keeps catching it; catch ``RateLimitError`` specifically
    to tell "slow down and retry" apart from a hard block or a dead seed.

    Raised with no message it carries :data:`RATE_LIMIT_MESSAGE`, the single
    wording every surface shares. ``retry_after`` is the seconds to wait when
    the site said so (else ``None``); ``status`` is 429.
    """

    def __init__(
        self,
        *args: object,
        retry_after: int | None = None,
        status: int = 429,
        url: str | None = None,
    ) -> None:
        if not args:
            args = (RATE_LIMIT_MESSAGE,)
        super().__init__(*args)
        self.retry_after = retry_after
        self.status = status
        self.url = url


class UnreachableError(requests.RequestException):
    """The seed URL couldn't be opened at all — the page never loaded.

    A domain that doesn't resolve, a refused connection, a 404, or two URLs
    pasted into one. Distinct from :class:`BlockedError` (a bot wall said no)
    and from a crawl that read the page fine but matched nothing (a real
    answer, ``pages`` non-empty). Subclasses :class:`requests.RequestException`
    so ``except requests.RequestException`` keeps catching it; catch
    ``UnreachableError`` specifically to tell "couldn't open it" apart from an
    ordinary request failure.

    Raised with no message it carries :data:`UNREACHABLE_MESSAGE`, the single
    wording every surface shares. Carries the offending ``url`` when a caller
    has it, for a structured message without re-parsing the string.
    """

    def __init__(self, *args: object, url: str | None = None) -> None:
        if not args:
            args = (UNREACHABLE_MESSAGE,)
        super().__init__(*args)
        self.url = url


def open_seed(fetch):
    """Run one seed fetch, turning a non-block failure into UnreachableError.

    A bot wall stays a :class:`BlockedError` (the caller still gets the named
    wall); anything else that stopped the page loading — a domain that doesn't
    resolve, a refused connection, a 404, two URLs pasted into one — becomes a
    single "couldn't open that page" answer instead of a raw traceback. The one
    place the single-fetch surfaces (the HTTP API, the MCP tools) share, so the
    fix lands in all of them at once; the crawl surfaces reach the same
    :class:`UnreachableError` through :meth:`CrawlResult.raise_for_seed`.

    ``fetch`` is a zero-arg callable returning a Page — e.g.
    ``lambda: scraper.static(url)`` or ``lambda: scraper.api(url)`` — so the
    caller keeps choosing the technique.
    """
    try:
        return fetch()
    except (BlockedError, RateLimitError):
        # A named wall and a 429 are both reachable-but-refused answers, more
        # specific than "couldn't open it" — let them through unchanged.
        raise
    except requests.RequestException as e:
        raise UnreachableError() from e


# WAF / bot-protection fingerprints: (label, response-header keys, body markers).
# Only consulted on a block-looking status, so serving a normal page from behind
# Cloudflare never trips it — just a challenge/deny does.
_BOT_WALLS = (
    (
        "Cloudflare",
        ("cf-mitigated", "cf-ray"),
        ("just a moment", "attention required", "cf-browser-verification", "cf_chl", "_cf_chl"),
    ),
    ("DataDome", ("x-datadome", "x-dd-b"), ("datadome",)),
    ("PerimeterX / HUMAN", ("x-px",), ("px-captcha", "perimeterx")),
    # "access denied" / "reference #" alone are too generic (a plain auth
    # failure says them too); "akamaighost" is Akamai's own edge signature.
    ("Akamai", (), ("akamaighost",)),
    ("Imperva Incapsula", ("x-iinfo",), ("incapsula", "_incap_", "incap_ses")),
)

# Statuses a bot wall actually uses to turn a request away.
_BLOCK_STATUS = frozenset({401, 403, 406, 429, 503})


def _detect_bot_wall(r: requests.Response) -> str | None:
    """Return the name of the bot wall that blocked ``r``, or ``None``.

    Gated on a block-looking status first, then sniffs response headers, the
    ``Server`` header and a slice of the body for known WAF signatures.
    """
    if r.status_code not in _BLOCK_STATUS:
        return None
    headers = {k.lower(): str(v).lower() for k, v in r.headers.items()}
    server = headers.get("server", "")
    try:
        body = r.text[:4096].lower()
    except Exception:  # a challenge page may not decode cleanly
        body = ""
    for label, header_keys, markers in _BOT_WALLS:
        vendor = label.split()[0].lower()  # "cloudflare", "datadome", "imperva", …
        if any(k in headers for k in header_keys):
            return label
        if vendor in server:
            return label
        if any(m in body for m in markers):
            return label
    return None


def _raise_for_status(r: requests.Response) -> None:
    """Like ``Response.raise_for_status()`` but clearer about bot walls.

    On an error status, if the response carries a bot-protection signature,
    raise :class:`BlockedError` with a human message naming the wall instead
    of a bare ``403 Client Error: Forbidden``. Everything else raises the
    ordinary :class:`requests.HTTPError`, unchanged.
    """
    try:
        r.raise_for_status()
    except requests.HTTPError as e:
        wall = _detect_bot_wall(r)
        if wall:
            host = urlparse(getattr(r, "url", "") or "").hostname or "the site"
            host = host.removeprefix("www.")
            raise BlockedError(
                f"Blocked by {wall} — {host} uses bot protection and refused "
                f"this request (HTTP {r.status_code}). Automated access isn't "
                f"allowed.",
                wall=wall,
                status=r.status_code,
            ) from e
        if r.status_code == 429:
            # A bare 429 (no WAF signature) is an honest "too many requests":
            # the site is up and answered, it just wants fewer of them. That is
            # not "couldn't open the page" — surface it as its own retryable
            # state, carrying the Retry-After wait when the site gave one.
            raise RateLimitError(
                retry_after=_retry_after_seconds(r.headers.get("Retry-After")),
                status=r.status_code,
                url=getattr(r, "url", None),
            ) from e
        raise
