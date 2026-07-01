"""Integration tests for the engine and report renderers."""

from __future__ import annotations

import json

from contextlint.config import Config
from contextlint.engine import analyze_path, worst_severity
from contextlint.models import Severity
from contextlint.reports import render, render_json, render_markdown, render_terminal
from contextlint.reports.json_report import report_to_dict


def test_analyze_examples_messy(examples_dir):
    report = analyze_path(examples_dir / "messy_docs", Config())
    rule_ids = {f.rule_id for f in report.findings}
    # The messy corpus is designed to trigger these structural rules.
    assert {"CTX001", "CTX002", "CTX003", "CTX004"} <= rule_ids
    assert report.total_chunks > 0
    assert report.files_analyzed >= 4


def test_analyze_examples_clean_has_no_errors(examples_dir):
    report = analyze_path(examples_dir / "clean_docs", Config())
    assert not report.has_at_least(Severity.ERROR)


def test_analyze_fragmented_kb_triggers_cfi(examples_dir):
    # Uses the directory's own .contextlint.json via discovery in the CLI; here we
    # pass an equivalent config explicitly.
    config = Config(chunk_size=520, chunk_overlap=0, cfi_warning_threshold=0.6)
    report = analyze_path(examples_dir / "fragmented_kb", config)
    assert any(f.rule_id == "CTX006" for f in report.findings)


def test_determinism(examples_dir):
    a = report_to_dict(analyze_path(examples_dir / "messy_docs", Config()))
    b = report_to_dict(analyze_path(examples_dir / "messy_docs", Config()))
    a.pop("generated_at")
    b.pop("generated_at")
    assert a == b


def test_worst_severity(examples_dir):
    report = analyze_path(examples_dir / "messy_docs", Config())
    assert worst_severity(report) == Severity.ERROR


def test_render_json_is_valid(examples_dir):
    report = analyze_path(examples_dir / "messy_docs", Config())
    payload = json.loads(render_json(report))
    assert payload["tool"] == "contextlint"
    assert "summary" in payload
    assert "findings" in payload
    assert payload["summary"]["findings"] == len(report.findings)


def test_render_markdown_contains_sections(examples_dir):
    report = analyze_path(examples_dir / "messy_docs", Config())
    md = render_markdown(report)
    assert "# ContextLint Report" in md
    assert "## Findings" in md
    assert "Context Fragmentation Index" in md


def test_render_terminal_plain(examples_dir):
    report = analyze_path(examples_dir / "clean_docs", Config())
    text = render_terminal(report, color=False)
    assert "ContextLint" in text
    assert "\033[" not in text  # no ANSI when colour disabled


def test_render_dispatch_unknown_format(examples_dir):
    report = analyze_path(examples_dir / "clean_docs", Config())
    try:
        render(report, "xml")
    except ValueError as exc:
        assert "Unknown report format" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected ValueError")


def test_empty_directory(tmp_path):
    report = analyze_path(tmp_path, Config())
    assert report.files_analyzed == 0
    assert report.total_chunks == 0
    assert report.findings == []
