"""The Page object: an already-downloaded page you extract data from.

A Page wraps HTML (or JSON, for API responses) and exposes CSS-selector
extraction, link discovery, structure inference (``selectors()``) and
Markdown conversion for LLMs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from bs4 import BeautifulSoup

from .markdown import _clean_markdown
from .selectors import _split_selector, _value_from
from .url import normalize


@dataclass
class Page:
    """An already-downloaded page. Extract from it."""

    url: str
    html: str = ""
    data: Any = None  # for JSON APIs
    method: str = "static"  # static | api | browser
    elapsed: float = 0.0
    status: int = 200
    _soup: BeautifulSoup | None = field(default=None, repr=False)

    @property
    def soup(self) -> BeautifulSoup:
        if self._soup is None:
            self._soup = BeautifulSoup(self.html or "", "lxml")
        return self._soup

    # --- extraction ---------------------------------------------------------
    def css(self, spec: str) -> str | None:
        """First match of a selector. Supports ::text and ::attr(name)."""
        sel, op, arg = _split_selector(spec)
        return _value_from(self.soup.select_one(sel), op, arg)

    def css_all(self, spec: str) -> list[str]:
        """All matches of a selector."""
        sel, op, arg = _split_selector(spec)
        return [v for n in self.soup.select(sel) if (v := _value_from(n, op, arg)) is not None]

    def extract(self, item: str, fields: dict[str, str]) -> list[dict]:
        """Extracts a list of records.

        item: CSS selector delimiting each record (e.g. "article.product_pod").
        fields: dict {name: relative_selector}. The selector is applied INSIDE
                each item. If a field name ends in "[]" it returns a list of values.

        Example:
            page.extract("div.quote", {
                "quote": "span.text::text",
                "author": "small.author::text",
                "tags[]": "a.tag::text",
            })
        """
        records = []
        for node in self.soup.select(item):
            row: dict[str, Any] = {}
            for name, spec in fields.items():
                sel, op, arg = _split_selector(spec)
                if name.endswith("[]"):
                    row[name[:-2]] = [
                        v for n in node.select(sel) if (v := _value_from(n, op, arg)) is not None
                    ]
                else:
                    row[name] = _value_from(node.select_one(sel), op, arg)
            records.append(row)
        return records

    def selectors(self, min_repeats: int = 3, limit: int = 3) -> list[dict]:
        """The page's repeated blocks and a ready-to-run `extract()` for each.

        Writing an extract() means knowing the markup, which means reading the
        HTML — and an agent on the MCP server cannot: markdown() strips exactly
        the classes and attributes a selector is built from, and handing back
        raw HTML would cost more tokens than the data it is meant to find.

        So this reports the structure instead of the source. It looks for
        elements whose tag+class signature repeats, which is what a listing of
        products, quotes or search results looks like, and for the best
        candidates works out which inner selectors resolve across most of the
        instances — a field that only appears in one row is a coincidence, not
        a column.

            page.selectors()[0]["fields"]
            {'title': 'h3 a::attr(title)', 'price': 'p.price_color::text', ...}

        Returns, per candidate: `item` (the repeating selector), `count`,
        `fields` (name -> relative selector) and `sample` (the first record),
        so the caller can check it got the right block before crawling with it.
        """
        from collections import defaultdict

        def sig(node) -> str | None:
            classes = [c for c in (node.get("class") or []) if not c.isdigit()]
            return f"{node.name}.{'.'.join(classes[:3])}" if classes else None

        groups: dict[str, list] = defaultdict(list)
        for node in self.soup.find_all(True):
            if (s := sig(node)) and node.get_text(strip=True):
                groups[s].append(node)

        scored = []
        for s, nodes in groups.items():
            if len(nodes) < min_repeats:
                continue
            # A repeated wrapper holding one field is a layout div; a record
            # holds several. Weigh richness, but cap it so a deep container
            # cannot outrank the actual row.
            depth = sum(1 for c in nodes[0].find_all(True) if c.get_text(strip=True))
            scored.append((min(depth, 8), len(nodes), s, nodes))
        scored.sort(reverse=True, key=lambda t: (t[0], t[1]))

        found = []
        for _, count, s, nodes in scored[: limit * 4]:
            fields = self._fields_of(nodes[:20])
            if fields:
                found.append((s, count, fields, nodes[0]))

        # A grid wrapper and the card inside it repeat equally often and carry
        # the same fields, so both score the same and the wrapper wins on depth
        # because it contains the card. Drop it: `article.product_pod` is the
        # record, and its selector survives a layout change that the
        # `li.col-xs-6.col-sm-4` around it will not.
        #
        # Same count and containment alone is not enough to call it a wrapper —
        # `div.quote` contains `div.tags`, also ten of them, but they describe
        # different records. A wrapper is the one that offers nothing its own
        # child does not: same count, contains it, and its columns are a subset.
        items = {s for s, _, _, _ in found}
        out = []
        for s, count, fields, node in found:
            if any(
                count == c2 and set(fields) <= set(f2) and node in n2.parents
                for s2, c2, f2, n2 in found
                if s2 != s
            ):
                continue
            # The other tell of a wrapper: one of its columns is an entire
            # other record. `li.col-xs-6` offers `article.product_pod::text`
            # as a field — that is not a column, that is the card it wraps.
            if any(spec.split("::")[0] in items for spec in fields.values()):
                continue
            sample = self.extract(s, fields)
            out.append(
                {"item": s, "count": count, "fields": fields, "sample": sample[0] if sample else {}}
            )
            if len(out) == limit:
                break
        return out

    @staticmethod
    def _fields_of(nodes: list, coverage: float = 0.6) -> dict[str, str]:
        """Inner selectors that resolve across most instances of a block."""
        from collections import defaultdict

        hits: dict[str, int] = defaultdict(int)
        for node in nodes:
            seen = set()
            for child in node.find_all(True):
                classes = [c for c in (child.get("class") or []) if not c.isdigit()]
                base = f"{child.name}.{'.'.join(classes[:2])}" if classes else child.name
                # An attribute is only a field if it actually carries a value,
                # and text is only a field if the element has its own — an <a>
                # wrapping an <img> reports the image's alt as text on some
                # pages and nothing on others, which is how `a::text` ends up
                # proposed for a column that is always empty.
                for attr in ("title", "href", "src"):
                    if (child.get(attr) or "").strip():
                        seen.add(f"{base}::attr({attr})")
                if child.get_text(strip=True):
                    seen.add(f"{base}::text")
            for spec in seen:
                hits[spec] += 1

        need = max(1, int(len(nodes) * coverage))
        # Named classes before bare tags, then shortest: `p.price_color::text`
        # is a column, `p::text` is whichever paragraph happened to be first.
        keep = sorted(
            (s for s, n in hits.items() if n >= need),
            key=lambda s: ("." not in s.split("::")[0], len(s)),
        )

        fields, used = {}, set()
        for spec in keep:
            sel, _, _ = _split_selector(spec)
            root = sel.split(".")[-1] or sel.split(".")[0]
            name = re.sub(r"[^a-z0-9]+", "_", root.lower()).strip("_") or "field"
            # One column per element: the same node's text and its href are the
            # same column asked two ways, and a record with both is noise.
            if sel in used or name in fields:
                continue
            # A selector that resolves everywhere but is blank everywhere is
            # not a column. Check against the instances, not the markup.
            op, arg = _split_selector(spec)[1:]
            if not any(
                _value_from(n.select_one(sel), op, arg) for n in nodes[:5] if n.select_one(sel)
            ):
                continue
            used.add(sel)
            fields[name] = spec
            if len(fields) == 8:
                break

        # Drop a column whose element contains another column's: its ::text is
        # every child's text run together, so `div.product_price` comes back as
        # "£51.77In stockAdd to basket" — three fields glued into one, and
        # never what the caller wanted from any of them.
        probe = nodes[0]
        inner = {
            sel
            for sel in used
            if (n := probe.select_one(sel)) is not None
            and any(
                n is not m and m in n.descendants
                for other in used
                if (m := probe.select_one(other)) is not None
            )
        }
        return {
            k: v for k, v in fields.items() if _split_selector(v)[0] not in inner or "::attr" in v
        }

    def links(self, raw: bool = False) -> list[str]:
        """Every link on the page as an absolute URL, deduplicated in order.

        Raw hrefs are almost never what you want: a long article yields
        hundreds of "#cite_note-4" fragments, repeated navigation and
        mailto:/asset links. This runs the same normalisation the crawlers
        use, so what you get back is the set of pages you could visit next.
        Pass raw=True for the untouched attribute values.
        """
        hrefs = [str(a["href"]) for a in self.soup.select("a[href]")]
        if raw:
            return hrefs
        out: list[str] = []
        seen: set[str] = set()
        for href in hrefs:
            target = normalize(href, self.url)
            if target and target not in seen:
                seen.add(target)
                out.append(target)
        return out

    def json(self) -> Any:
        return self.data

    # --- LLM ----------------------------------------------------------------
    def _extraction_gutted_it(self, md: str) -> bool:
        """Did main-content extraction discard the page instead of trimming it?

        Two signals, because one was not enough. Length alone caught
        books.toscrape.com, where the extractor returns the price column and
        drops all twenty titles — but only because that page carries enough
        navigation to put the ratio at 0.19. Strip the chrome and the same
        failure scores 0.51, sailing past a threshold set low enough to spare
        an article buried in navigation.

        So also look at headings. On a listing the item titles are headings, so
        losing nearly all of them means the rows went with them. Count matters:
        quotes.toscrape.com has two headings, both site chrome, and drops both
        while keeping every quote — correct behaviour that a bare ratio of
        surviving headings would call a failure. A page with many headings and
        almost none left is the one that lost its content.
        """
        visible = len(self.soup.get_text(" ", strip=True))
        if visible and len(md) / visible < self._MAIN_CONTENT_FLOOR:
            return True
        headings = [
            h.get_text(strip=True)
            for h in self.soup.select("h1,h2,h3,h4")
            if h.get_text(strip=True)
        ]
        if len(headings) < self._MANY_HEADINGS:
            return False
        kept = sum(1 for h in headings if h[:30] in md)
        return kept / len(headings) < self._HEADINGS_FLOOR

    # A page with at least this many headings is structured enough that losing
    # them means something. Below it they are a title and a sidebar label.
    _MANY_HEADINGS = 5
    _HEADINGS_FLOOR = 0.25

    # Below this share of the page's visible text, main-content extraction has
    # not trimmed boilerplate — it has thrown the content away. Measured:
    # trafilatura keeps 1.14x the visible text on quotes.toscrape.com and 1.4-1.6x
    # on Wikipedia articles (markdown adds link syntax), but 0.19x on
    # books.toscrape.com, where it returns the price column and drops all
    # twenty book titles. The threshold sits far below every good case on
    # purpose: a news article buried in navigation legitimately scores low, and
    # falling back there would hand back the navigation it correctly removed.
    _MAIN_CONTENT_FLOOR = 0.25

    def markdown(self, main_only: bool = True) -> str:
        """Converts the page to clean Markdown (saves tokens for LLMs)."""
        if main_only:
            try:
                import trafilatura

                # include_links keeps link boundaries; without it adjacent
                # nodes glue together ("Visit siteSierra")
                md = trafilatura.extract(self.html, output_format="markdown", include_links=True)
                # A listing is all repetition, which is exactly what an
                # article extractor is built to discard, so check what came
                # back before trusting it.
                if md and not self._extraction_gutted_it(md):
                    return _clean_markdown(md)
            except ImportError:
                pass
        try:
            from markdownify import markdownify
        except ImportError as e:
            raise ImportError(
                "Page.markdown() needs the 'llm' extra: pip install bytecrawl[llm]"
            ) from e

        # markdownify's strip=[...] only removes the tag itself, not its
        # contents — a <script> survives as loose text, so a JS-heavy page
        # (ad tech, consent stubs) leaks straight into the "clean" Markdown.
        # Decompose script/style/noscript on a scratch soup before handing
        # it off, instead of relying on strip= to do it.
        scratch = BeautifulSoup(self.html or "", "lxml")
        for tag in scratch(["script", "style", "noscript"]):
            tag.decompose()
        return _clean_markdown(markdownify(str(scratch)))

    def tokens(self, of: str | None = None) -> int:
        """Quick token estimate (~4 chars/token)."""
        text = of if of is not None else (self.html or "")
        return len(text) // 4
