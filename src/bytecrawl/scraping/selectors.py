"""CSS-selector parsing shared by Page extraction and the crawlers.

A selector spec is a normal CSS selector optionally suffixed with ``::text``
(the default) or ``::attr(name)`` to say what to pull out of the match.
"""

from __future__ import annotations


def _split_selector(spec: str) -> tuple[str, str, str | None]:
    """Returns (css_selector, operation, argument).

    operation: "text" (default) or "attr". argument: the attribute name.
    Examples:
      "p.price_color::text"   -> ("p.price_color", "text", None)
      "h3 a::attr(title)"     -> ("h3 a", "attr", "title")
      "div.quote"             -> ("div.quote", "text", None)
    """
    spec = spec.strip()
    if "::attr(" in spec:
        sel, rest = spec.split("::attr(", 1)
        return sel.strip(), "attr", rest.rstrip(")").strip()
    if spec.endswith("::text"):
        return spec[: -len("::text")].strip(), "text", None
    return spec, "text", None


def _value_from(node, op: str, arg: str | None) -> str | None:
    if node is None:
        return None
    if op == "attr":
        return node.get(arg)
    return node.get_text(strip=True)
