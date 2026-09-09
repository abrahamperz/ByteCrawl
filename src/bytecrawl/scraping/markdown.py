"""Markdown post-processing.

Whatever converter produced the Markdown (trafilatura or markdownify),
marketing and SPA pages leave conversion noise behind. This is the cleanup
pass Page.markdown() runs on the result.
"""

from __future__ import annotations

import re


def _clean_markdown(md: str) -> str:
    """Removes conversion noise from marketing/SPA pages.

    Carousels and marquees duplicate their content in the DOM to loop, so the
    same block appears 2-3 times; animated counters leave their initial state.
    Dedupe repeated blocks and merge headings split across lines.
    """
    blocks = re.split(r"\n{2,}", md)
    seen: set[str] = set()
    cleaned: list[str] = []
    prev_key = ""
    for block in blocks:
        # Headings broken inside the block: "## Start scraping\n today"
        if block.lstrip().startswith("#") and "\n" in block:
            lines = block.split("\n")
            joined = [lines[0].rstrip()]
            for ln in lines[1:]:
                s = ln.strip()
                continues = s[:1].islower() or joined[-1].rstrip().endswith(("'", ","))
                if s and len(s) < 60 and continues:
                    joined[-1] = joined[-1] + " " + s
                else:
                    joined.append(ln)
            block = "\n".join(joined)
        key = " ".join(block.split())
        if not key:
            continue
        # Consecutive duplicates (looping carousels repeat short labels too)
        if key == prev_key:
            continue
        # Carousel/marquee duplicates: same long block seen before
        if len(key) >= 40 and key in seen:
            continue
        seen.add(key)
        prev_key = key
        cleaned.append(block.rstrip())

    # Text split by animated spans: "# Power AI agents with" + "clean web data"
    merged: list[str] = []
    for block in cleaned:
        prev = merged[-1] if merged else ""
        frag = block.strip()
        joinable = (
            prev
            and not prev.startswith(("```", "-", "*", ">", "|"))
            and "\n" not in prev
            and "\n" not in frag
            and not frag.startswith(("#", "```", "-", "*", ">", "|", "["))
        )
        visible_len = len(re.sub(r"\]\([^)]*\)", "]", frag))  # ignore link URLs
        lower_continuation = (
            visible_len < 70
            and frag[:1].islower()
            and not prev.rstrip().endswith((".", "!", "?", ":", "`"))
        )
        # Headings cut mid-phrase keep capitalization: "## Easily connect with your" + "AI agents"
        heading_continuation = (
            re.match(r"#{1,6} ", prev) is not None
            and len(frag) < 30
            and not frag.rstrip().endswith((".", "!", "?", ":"))
            and not prev.rstrip().endswith((".", "!", "?", ":", "`"))
        )
        if joinable and (lower_continuation or heading_continuation):
            merged[-1] = prev.rstrip() + " " + frag
        else:
            merged.append(block)

    # Inline-span joins lose the space: "at scale.It's also open source"
    out = []
    for block in merged:
        if "```" not in block:
            block = re.sub(r"(?<=[a-z])([.!?])(?=[A-Z\[])", r"\1 ", block)
        out.append(block)
    return "\n\n".join(out).strip()
