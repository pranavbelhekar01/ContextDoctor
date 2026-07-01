"""Tests for Tier-1 additions: health score, new rules, new outputs, API, filtering."""

from __future__ import annotations

import json

from contextdoctor import Config, analyze_chunks, analyze_paths, compute_health
from contextdoctor.analyzers import ChunkStatsAnalyzer, ContentQualityAnalyzer
from contextdoctor.engine import analyze_path
from contextdoctor.models import Severity
from contextdoctor.reports import render_badge, render_html, render_sarif
from contextdoctor.scoring import compute_health as _ch
from helpers import build_context, make_chunk

# --- Health score ------------------------------------------------------------


def test_clean_corpus_scores_100():
    hs = compute_health([])
    assert hs.score == 100
    assert hs.grade == "A+"


def test_score_decreases_with_severity():
    from contextdoctor.models import Finding

    err = Finding("CTX004", Severity.ERROR, "m", "r")
    warn = Finding("CTX001", Severity.WARNING, "m", "r")
    assert _ch([err]).score < 100
    assert _ch([err, err, err]).score < _ch([err]).score
    assert _ch([warn]).score > _ch([err]).score
    for hs in (_ch([err] * 20), _ch([])):
        assert 0 <= hs.score <= 100


def test_report_carries_health(examples_dir):
    report = analyze_path(examples_dir / "clean_docs")
    assert report.health_score == 100
    assert report.health_grade in {"A", "A+"}
    messy = analyze_path(examples_dir / "messy_docs")
    assert messy.health_score < 100


# --- Content-quality rules (CTX007/008/009) ---------------------------------


def test_secret_detection():
    ctx = build_context(["OPENAI_API_KEY=sk-ABCDEFGHIJKLMNOPQRSTUVWX1234567890"])
    result = ContentQualityAnalyzer().analyze(ctx)
    ids = {f.rule_id for f in result.findings}
    assert "CTX007" in ids
    # The secret value must never appear in the finding output.
    blob = " ".join(f.message for f in result.findings)
    assert "sk-ABCDEFGHIJKLMNOPQRSTUVWX1234567890" not in blob


def test_pii_detection():
    ctx = build_context(["Contact jane.doe@example.com or SSN 123-45-6789."])
    result = ContentQualityAnalyzer().analyze(ctx)
    assert "CTX008" in {f.rule_id for f in result.findings}


def test_encoding_artifact_detection():
    ctx = build_context(["itâ€™s broken and there is a � replacement char"])
    result = ContentQualityAnalyzer().analyze(ctx)
    assert "CTX009" in {f.rule_id for f in result.findings}


def test_content_quality_clean_text():
    ctx = build_context(["A perfectly ordinary sentence about retrieval systems."])
    result = ContentQualityAnalyzer().analyze(ctx)
    assert result.findings == []


def test_detectors_can_be_disabled():
    cfg = Config(detect_secrets=False, detect_pii=False, detect_encoding_artifacts=False)
    ctx = build_context(["sk-ABCDEFGHIJKLMNOPQRSTUVWX jane@example.com"], config=cfg)
    result = ContentQualityAnalyzer().analyze(ctx)
    assert result.findings == []


# --- CTX010 embedding token limit -------------------------------------------


def test_embedding_limit_rule():
    cfg = Config(embedding_token_limit=10, max_chunk_chars=100_000, min_chunk_chars=1)
    big = "word " * 200  # ~150 tokens, well over 10
    ctx = build_context([big], config=cfg)
    result = ChunkStatsAnalyzer().analyze(ctx)
    assert "CTX010" in {f.rule_id for f in result.findings}


# --- Framework-agnostic API --------------------------------------------------


def test_analyze_chunks_strings():
    report = analyze_chunks(["duplicate text", "unique", "duplicate text"])
    assert report.total_chunks == 3
    assert any(f.rule_id == "CTX003" for f in report.findings)


def test_analyze_chunks_dicts():
    report = analyze_chunks([{"page_content": "hello world"}, {"text": "another chunk"}])
    assert report.total_chunks == 2


def test_analyze_paths_multiple(examples_dir):
    report = analyze_paths([examples_dir / "clean_docs", examples_dir / "messy_docs"])
    assert report.files_analyzed >= 5


# --- Rule selection & severity overrides ------------------------------------


def test_ignore_rule():
    report = analyze_chunks(["dup", "dup"], Config(ignore=("CTX003",), min_chunk_chars=1))
    assert not any(f.rule_id == "CTX003" for f in report.findings)


def test_select_rule():
    report = analyze_chunks(
        ["x" * 5000, "dup", "dup"], Config(select=("CTX001",), max_chunk_chars=100)
    )
    assert {f.rule_id for f in report.findings} <= {"CTX001"}


def test_severity_override():
    report = analyze_chunks(["dup", "dup"], Config(severity={"CTX003": "error"}, min_chunk_chars=1))
    ctx003 = [f for f in report.findings if f.rule_id == "CTX003"]
    assert ctx003 and all(f.severity == Severity.ERROR for f in ctx003)


# --- New report formats ------------------------------------------------------


def test_render_html(examples_dir):
    report = analyze_path(examples_dir / "messy_docs")
    html = render_html(report)
    assert "<!doctype html>" in html.lower()
    assert str(report.health_score) in html
    assert "Context Fragmentation Index" in html


def test_render_html_escapes(examples_dir):
    # A finding message with angle brackets must be escaped, not injected raw.
    report = analyze_chunks(["<script>alert(1)</script> " + "x" * 5000], Config(max_chunk_chars=10))
    html = render_html(report)
    assert "<script>alert(1)</script>" not in html


def test_render_sarif(examples_dir):
    report = analyze_path(examples_dir / "messy_docs")
    doc = json.loads(render_sarif(report))
    assert doc["version"] == "2.1.0"
    assert doc["runs"][0]["tool"]["driver"]["name"] == "ContextDoctor"
    assert len(doc["runs"][0]["results"]) == len(report.findings)


def test_render_badge(examples_dir):
    report = analyze_path(examples_dir / "clean_docs")
    doc = json.loads(render_badge(report))
    assert doc["schemaVersion"] == 1
    assert "100" in doc["message"]


def test_make_chunk_helper_smoke():
    c = make_chunk("s", 0, 0, "hello")
    assert c.char_count == 5
