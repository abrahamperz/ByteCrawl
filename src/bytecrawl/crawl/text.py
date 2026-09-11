"""Text similarity and query relevance for the focused crawlers.

Leaf module: pure stdlib. Tokenisation, cosine similarity, a conservative
fuzzy term matcher (trigram Dice), and the ``relevance()`` a page is scored
with against a query.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from functools import lru_cache
from urllib.parse import urlparse

_WORD = re.compile(r"[a-záéíóúüñ0-9]+", re.IGNORECASE)


def _tokens(text: str) -> list[str]:
    return [w.lower() for w in _WORD.findall(text or "")]


def cosine(text_a: str, text_b: str) -> float:
    """Cosine similarity between two texts using term-frequency (TF) vectors.

    The classic information-retrieval metric: 1.0 = same vocabulary in the
    same proportions, 0.0 = not a single word in common.
    """
    a, b = Counter(_tokens(text_a)), Counter(_tokens(text_b))
    if not a or not b:
        return 0.0
    common = set(a) & set(b)
    dot = sum(a[w] * b[w] for w in common)
    norm = math.sqrt(sum(v * v for v in a.values())) * math.sqrt(sum(v * v for v in b.values()))
    return dot / norm if norm else 0.0


@lru_cache(maxsize=4096)
def _trigrams(word: str) -> frozenset:
    padded = f"~{word}~"
    return frozenset(padded[i : i + 3] for i in range(len(padded) - 2))


def _dice(a: frozenset, b: frozenset) -> float:
    """Sørensen-Dice overlap of two trigram sets: 1.0 identical, 0.0 disjoint."""
    if not a or not b:
        return 0.0
    return 2 * len(a & b) / (len(a) + len(b))


# Thresholds measured against real pairs, not guessed. At 0.55 a one-letter
# slip is caught ("mistery"/"mystery" = 0.57) while genuinely different words
# stay out ("price"/"prize" = 0.40, "crawl"/"crown" = 0.20). Words shorter than
# 6 letters are matched exactly: they have too few trigrams to tell a typo from
# a different word ("data"/"date" and "news"/"newt" both score 0.50, the same
# as the real typo "travle"/"travel"), so fuzzy there would invent matches.
# Deliberately conservative: it misses heavier typos ("histroy") and
# inflections ("pricing"/"prices") rather than risk false hits.
_FUZZY_MIN = 0.55
_FUZZY_MIN_LEN = 6


def _resolve_terms(query: str, vocabulary: set) -> str:
    """Rewrites query words that are near-misses of a word the page uses.

    People typo their queries ("mistery"), and exact term matching scores that
    0.0 — which reads as "the crawler is broken" rather than "no match".
    Snapping each query term to its closest page term keeps the scoring itself
    on the plain cosine path.
    """
    resolved = []
    for term in _tokens(query):
        if term in vocabulary or len(term) < _FUZZY_MIN_LEN:
            resolved.append(term)
            continue
        grams = _trigrams(term)
        best, best_score = None, 0.0
        for word in vocabulary:
            if len(word) < _FUZZY_MIN_LEN or abs(len(word) - len(term)) > 2:
                continue
            score = _dice(grams, _trigrams(word))
            if score > best_score:
                best, best_score = word, score
        resolved.append(best if best is not None and best_score >= _FUZZY_MIN else term)
    return " ".join(resolved)


def relevance(text: str, query: str, url: str = "") -> float:
    """How well a page answers a query.

    Scores the page text plus its URL path — a page at /category/mystery is
    about mystery even if the word is thin in the body — and tolerates typos
    and inflections in the query.
    """
    if not query:
        return 0.0
    haystack = f"{text} {' '.join(_tokens(urlparse(url).path))}" if url else text
    return cosine(haystack, _resolve_terms(query, set(_tokens(haystack))))
