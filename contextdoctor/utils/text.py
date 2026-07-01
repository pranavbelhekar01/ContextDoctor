"""Text utilities: tokenisation, shingling, token estimation, offset mapping.

Everything here is deterministic and stdlib-only.
"""

from __future__ import annotations

import re

_WORD_RE = re.compile(r"\w+", re.UNICODE)
_WS_RE = re.compile(r"\s+")


def normalize_whitespace(text: str) -> str:
    """Collapse runs of whitespace and strip, for stable comparisons."""
    return _WS_RE.sub(" ", text).strip()


def normalize_for_hash(text: str) -> str:
    """Aggressive normalisation used for exact-duplicate hashing."""
    return normalize_whitespace(text).lower()


def words(text: str) -> list[str]:
    """Lowercased word tokens."""
    return [m.group(0).lower() for m in _WORD_RE.finditer(text)]


def word_count(text: str) -> int:
    return sum(1 for _ in _WORD_RE.finditer(text))


def estimate_tokens(text: str) -> int:
    """Rough token estimate.

    We use a blend of character- and word-based heuristics that lands close to
    common BPE tokenizers for English prose without needing any model files:
    ``~= max(chars / 4, words * 0.75)``.
    """
    chars = len(text)
    wc = word_count(text)
    est = max(chars / 4.0, wc * 0.75)
    return max(1, round(est)) if text.strip() else 0


def shingles(text: str, size: int = 5) -> set[str]:
    """Word n-gram shingle set, for Jaccard similarity."""
    toks = words(text)
    if len(toks) < size:
        # Fall back to the whole token sequence so short chunks still compare.
        return {" ".join(toks)} if toks else set()
    return {" ".join(toks[i : i + size]) for i in range(len(toks) - size + 1)}


def jaccard(a: set[str], b: set[str]) -> float:
    """Jaccard similarity between two sets. 0.0 when both empty."""
    if not a and not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def line_starts(text: str) -> list[int]:
    """Character offsets at which each line begins (index 0 == line 1)."""
    starts = [0]
    for i, ch in enumerate(text):
        if ch == "\n":
            starts.append(i + 1)
    return starts


def offset_to_line(offset: int, starts: list[int]) -> int:
    """1-based line number for a character offset (binary search)."""
    import bisect

    if offset < 0:
        offset = 0
    idx = bisect.bisect_right(starts, offset) - 1
    return max(1, idx + 1)


def sentences(text: str) -> list[str]:
    """Naive sentence splitter (deterministic, no models)."""
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if p]


def truncate(text: str, limit: int = 80) -> str:
    """Single-line preview of a piece of text."""
    flat = normalize_whitespace(text)
    if len(flat) <= limit:
        return flat
    return flat[: limit - 1].rstrip() + "…"
