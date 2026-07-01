"""Hashing helpers for exact-duplicate detection and MinHash signatures."""

from __future__ import annotations

import hashlib

from contextlint.utils.text import normalize_for_hash


def content_hash(text: str) -> str:
    """Stable SHA-256 of normalised text (whitespace-collapsed, lowercased)."""
    norm = normalize_for_hash(text)
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


def _hash_u32(token: str, seed: int) -> int:
    """Deterministic 32-bit hash of a token under a seed."""
    h = hashlib.blake2b(token.encode("utf-8"), digest_size=8, salt=seed.to_bytes(2, "little"))
    return int.from_bytes(h.digest()[:4], "little")


def minhash_signature(shingle_set: set[str], num_perm: int = 32) -> tuple[int, ...]:
    """Compute a MinHash signature for a shingle set.

    Deterministic across runs and platforms. Two signatures can be compared
    with :func:`minhash_similarity` to estimate Jaccard similarity in O(k)
    instead of O(|shingles|).
    """
    if not shingle_set:
        return tuple(0xFFFFFFFF for _ in range(num_perm))
    sig = []
    for seed in range(num_perm):
        sig.append(min(_hash_u32(s, seed) for s in shingle_set))
    return tuple(sig)


def minhash_similarity(a: tuple[int, ...], b: tuple[int, ...]) -> float:
    """Estimate Jaccard similarity from two equal-length MinHash signatures."""
    if not a or not b or len(a) != len(b):
        return 0.0
    equal = sum(1 for x, y in zip(a, b, strict=False) if x == y)
    return equal / len(a)
