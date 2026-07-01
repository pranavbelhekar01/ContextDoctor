"""Tests for the chunk-stats, duplicate, table, and heading analyzers."""

from __future__ import annotations

from contextlint.analyzers import (
    ChunkStatsAnalyzer,
    DuplicateAnalyzer,
    TableAnalyzer,
)
from contextlint.config import Config
from contextlint.engine import analyze_path
from helpers import build_context


def _rule_ids(result):
    return {f.rule_id for f in result.findings}


# --- Chunk statistics (CTX001 / CTX002) --------------------------------------


def test_chunk_stats_flags_large_and_small():
    config = Config(max_chunk_chars=100, min_chunk_chars=20)
    ctx = build_context(["x" * 500, "y" * 5, "z" * 60], config=config)
    result = ChunkStatsAnalyzer().analyze(ctx)
    assert "CTX001" in _rule_ids(result)
    assert "CTX002" in _rule_ids(result)
    assert result.metrics["char"]["max"] == 500


def test_chunk_stats_clean_when_within_bounds():
    config = Config(max_chunk_chars=10_000, min_chunk_chars=1)
    ctx = build_context(["a normal sized chunk of text " * 5], config=config)
    result = ChunkStatsAnalyzer().analyze(ctx)
    assert result.findings == []


def test_percentiles_present():
    ctx = build_context([f"chunk {i} " * (i + 1) for i in range(10)])
    result = ChunkStatsAnalyzer().analyze(ctx)
    dist = result.metrics["char"]
    assert dist["min"] <= dist["median"] <= dist["max"]
    assert "p95" in dist


# --- Duplicates (CTX003) -----------------------------------------------------


def test_exact_duplicates_detected():
    ctx = build_context(["identical content here", "unique one", "identical content here"])
    result = DuplicateAnalyzer().analyze(ctx)
    assert "CTX003" in _rule_ids(result)
    assert result.metrics["exact_groups"] == 1
    assert result.metrics["duplicate_pct"] > 0


def test_near_duplicates_detected():
    config = Config(near_duplicate_threshold=0.6, shingle_size=3)
    base = "the retrieval pipeline reranks candidate passages using a cross encoder model today"
    variant = "the retrieval pipeline reranks candidate passages using a cross encoder model now"
    ctx = build_context(
        [base, variant, "totally different unrelated sentence about weather"], config=config
    )
    result = DuplicateAnalyzer().analyze(ctx)
    assert result.metrics["near_pairs"] >= 1
    assert "CTX003" in _rule_ids(result)


def test_no_duplicates_is_clean():
    ctx = build_context(["alpha beta gamma", "delta epsilon zeta", "eta theta iota"])
    result = DuplicateAnalyzer().analyze(ctx)
    assert result.findings == []
    assert result.metrics["duplicate_pct"] == 0.0


# --- Tables (CTX004) ---------------------------------------------------------


def test_broken_table_across_chunks():
    head = "| Model | Size |\n| --- | --- |\n| mini | 1B |"
    tail = "| base | 7B |\n| large | 70B |"
    ctx = build_context([head, tail])
    result = TableAnalyzer().analyze(ctx)
    assert "CTX004" in _rule_ids(result)
    assert result.metrics["broken_boundaries"] == 1


def test_intact_table_not_flagged():
    whole = "| Model | Size |\n| --- | --- |\n| mini | 1B |\n| base | 7B |"
    ctx = build_context([whole, "Some following prose that is unrelated to tables entirely."])
    result = TableAnalyzer().analyze(ctx)
    assert result.findings == []


# --- Headings (CTX005) -------------------------------------------------------


def test_heading_fragmentation(tmp_path):
    body = "\n\n".join(f"Paragraph {i} discussing the topic at hand." for i in range(20))
    (tmp_path / "big.md").write_text("# One Big Section\n\n" + body, encoding="utf-8")
    report = analyze_path(
        tmp_path, Config(chunk_size=120, chunk_overlap=0, max_chunks_per_heading=3)
    )
    assert any(f.rule_id == "CTX005" for f in report.findings)


def test_heading_ok_when_sections_short(tmp_path):
    md = "# A\n\nShort a.\n\n# B\n\nShort b.\n"
    (tmp_path / "small.md").write_text(md, encoding="utf-8")
    report = analyze_path(tmp_path, Config(max_chunks_per_heading=5))
    assert not any(f.rule_id == "CTX005" for f in report.findings)
