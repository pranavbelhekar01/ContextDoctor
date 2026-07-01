"""Tests for baseline files (freeze existing findings, report only new ones)."""

from __future__ import annotations

from contextlint import Config, analyze_chunks
from contextlint.baseline import (
    collect_fingerprints,
    fingerprint,
    load_baseline,
    save_baseline,
)

_BIG = "word " * 4000  # ~3000 tokens, triggers CTX001 + CTX010


def _cfg():
    return Config(max_chunk_chars=100, min_chunk_chars=1, embedding_token_limit=50)


def test_fingerprint_is_stable():
    a = analyze_chunks([_BIG], _cfg())
    b = analyze_chunks([_BIG], _cfg())
    assert collect_fingerprints(a) == collect_fingerprints(b)
    assert all(isinstance(fingerprint(f), str) for f in a.findings)


def test_all_known_findings_are_in_baseline(tmp_path):
    report = analyze_chunks([_BIG], _cfg())
    assert report.findings  # there are findings to freeze
    path = tmp_path / "baseline.json"
    save_baseline(report, path)

    frozen = load_baseline(path)
    again = analyze_chunks([_BIG], _cfg())
    assert all(fingerprint(f) in frozen for f in again.findings)


def test_baseline_via_engine(tmp_path):
    from contextlint.engine import analyze_paths

    doc = tmp_path / "big.txt"
    doc.write_text(_BIG, encoding="utf-8")

    first = analyze_paths([tmp_path], _cfg())
    path = tmp_path / "bl.json"
    save_baseline(first, path)

    second = analyze_paths([tmp_path], _cfg(), baseline=load_baseline(path))
    assert second.findings == []
    assert second.baseline_suppressed == len(first.findings)
    assert second.health_score == 100  # nothing new -> perfect score


def test_new_finding_not_suppressed(tmp_path):
    from contextlint.engine import analyze_paths

    doc = tmp_path / "a.txt"
    doc.write_text(_BIG, encoding="utf-8")
    first = analyze_paths([tmp_path], _cfg())
    path = tmp_path / "bl.json"
    save_baseline(first, path)

    # Introduce a brand-new file with its own findings.
    (tmp_path / "b.txt").write_text(_BIG, encoding="utf-8")
    second = analyze_paths([tmp_path], _cfg(), baseline=load_baseline(path))
    # b.txt's findings are new (different file fingerprint) -> surfaced.
    assert any(f for f in second.findings)
