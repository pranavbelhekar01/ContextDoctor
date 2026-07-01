"""Lightweight, local, dependency-free entity extraction for the CFI metric.

This is intentionally simple: no spaCy, no model downloads, no network. It uses
regular expressions to surface capitalised proper-noun phrases and acronyms,
which is a reasonable proxy for "named things" in technical documentation. It is
good enough to power an *experimental* fragmentation signal and keeps ContextDoctor
fully offline.
"""

from __future__ import annotations

import re

# Common words that frequently start sentences and would otherwise masquerade as
# single-word proper nouns. Kept deliberately small and general.
_STOPWORD_CAPS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "but",
    "if",
    "then",
    "else",
    "when",
    "while",
    "for",
    "to",
    "of",
    "in",
    "on",
    "at",
    "by",
    "with",
    "as",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "this",
    "that",
    "these",
    "those",
    "it",
    "its",
    "we",
    "you",
    "they",
    "he",
    "she",
    "i",
    "our",
    "your",
    "their",
    "his",
    "her",
    "there",
    "here",
    "how",
    "why",
    "what",
    "which",
    "who",
    "whom",
    "can",
    "could",
    "should",
    "would",
    "may",
    "might",
    "must",
    "will",
    "shall",
    "do",
    "does",
    "did",
    "not",
    "no",
    "yes",
    "so",
    "such",
    "than",
    "too",
    "very",
    "just",
    "also",
    "however",
    "therefore",
    "thus",
    "hence",
    "note",
    "see",
    "use",
    "using",
    "used",
    "each",
    "every",
    "some",
    "any",
    "all",
    "both",
    "either",
    "neither",
    "more",
    "most",
    "less",
    "least",
    "first",
    "second",
    "next",
    "last",
    "one",
    "two",
    "three",
    "new",
    "old",
    "good",
    "bad",
    "example",
    "step",
}

# A proper-noun phrase: one or more Capitalised tokens (optionally containing
# internal capitals/digits, e.g. "PostgreSQL", "GPT4"), joined by spaces.
_PROPER_RE = re.compile(
    r"\b([A-Z][A-Za-z0-9]*(?:[-'][A-Za-z0-9]+)?(?:\s+[A-Z][A-Za-z0-9]*(?:[-'][A-Za-z0-9]+)?){0,4})\b"
)

# Acronyms / all-caps tokens like RAG, LLM, API, HTTP2.
_ACRONYM_RE = re.compile(r"\b([A-Z]{2,}[0-9]*)\b")

# snake_case / CamelCase identifiers that often name entities in tech docs.
_IDENT_RE = re.compile(r"\b([a-z]+(?:_[a-z0-9]+)+|[a-z]+[A-Z][A-Za-z0-9]+)\b")


def _clean(term: str) -> str:
    return re.sub(r"\s+", " ", term).strip(" .,:;\"'()[]{}")


def extract_entities(text: str) -> list[str]:
    """Return normalised entity surface forms found in ``text``.

    The result is lowercased for stable cross-chunk matching. Duplicates within
    the same text are preserved so callers can weight by frequency if desired.
    """
    found: list[str] = []

    for m in _ACRONYM_RE.finditer(text):
        term = _clean(m.group(1))
        if len(term) >= 2:
            found.append(term.lower())

    for m in _PROPER_RE.finditer(text):
        phrase = _clean(m.group(1))
        if not phrase:
            continue
        tokens = phrase.split(" ")
        if len(tokens) == 1:
            single = tokens[0]
            # Drop single capitalised words that are common sentence starters
            # or all-caps (already captured as acronyms), or too short.
            if single.lower() in _STOPWORD_CAPS or len(single) < 3 or single.isupper():
                continue
            found.append(single.lower())
        else:
            # Multi-word phrase: strip leading stopword-ish tokens.
            while tokens and tokens[0].lower() in _STOPWORD_CAPS:
                tokens.pop(0)
            if len(tokens) >= 1:
                phrase = " ".join(tokens)
                if len(phrase) >= 3:
                    found.append(phrase.lower())

    for m in _IDENT_RE.finditer(text):
        term = _clean(m.group(1))
        if len(term) >= 4:
            found.append(term.lower())

    return found


def entity_set(text: str) -> set[str]:
    """Distinct entities in ``text``."""
    return set(extract_entities(text))
