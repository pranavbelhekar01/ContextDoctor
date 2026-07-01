"""Tests for text, hashing, and NLP utilities."""

from __future__ import annotations

from contextlint.utils.hashing import (
    content_hash,
    minhash_signature,
    minhash_similarity,
)
from contextlint.utils.nlp import entity_set, extract_entities
from contextlint.utils.text import (
    estimate_tokens,
    jaccard,
    line_starts,
    offset_to_line,
    shingles,
    truncate,
    word_count,
)


def test_word_count_and_tokens():
    assert word_count("hello world foo") == 3
    assert estimate_tokens("") == 0
    assert estimate_tokens("hello world") >= 1
    # Longer text -> more tokens.
    assert estimate_tokens("a" * 400) > estimate_tokens("a" * 40)


def test_shingles_and_jaccard():
    a = shingles("the quick brown fox jumps", size=2)
    b = shingles("the quick brown fox leaps", size=2)
    assert 0 < jaccard(a, b) < 1
    assert jaccard(a, a) == 1.0
    assert jaccard(set(), set()) == 0.0


def test_shingles_short_text_fallback():
    # Fewer tokens than the shingle size still yields a comparable set.
    s = shingles("hello world", size=5)
    assert s == {"hello world"}


def test_line_mapping():
    text = "line1\nline2\nline3"
    starts = line_starts(text)
    assert offset_to_line(0, starts) == 1
    assert offset_to_line(6, starts) == 2
    assert offset_to_line(12, starts) == 3


def test_truncate():
    assert truncate("short", 80) == "short"
    long = truncate("word " * 50, 20)
    assert long.endswith("…")
    assert len(long) <= 20


def test_content_hash_normalisation():
    assert content_hash("Hello   World") == content_hash("hello world")
    assert content_hash("a") != content_hash("b")


def test_minhash_similarity():
    a = shingles("the quick brown fox jumps over the lazy dog today", 3)
    b = shingles("the quick brown fox jumps over the lazy dog today", 3)
    c = shingles("completely different content with no shared phrases here", 3)
    sig_a = minhash_signature(a)
    sig_b = minhash_signature(b)
    sig_c = minhash_signature(c)
    assert minhash_similarity(sig_a, sig_b) == 1.0
    assert minhash_similarity(sig_a, sig_c) < 0.5


def test_extract_entities_proper_nouns_and_acronyms():
    text = "The Zephyr scheduler uses RAG and talks to PostgreSQL via the LLM gateway."
    ents = entity_set(text)
    assert "zephyr" in ents
    assert "rag" in ents
    assert "llm" in ents
    assert "postgresql" in ents
    # Sentence-initial common word should be filtered out.
    assert "the" not in ents


def test_extract_entities_is_deterministic():
    text = "Nimbus and Quasar and Nimbus again."
    assert extract_entities(text) == extract_entities(text)
