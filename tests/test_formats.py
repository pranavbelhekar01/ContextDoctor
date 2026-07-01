"""Tests for the HTML/CSV/TSV/JSONL/PDF parsers and inline pragmas."""

from __future__ import annotations

from pathlib import Path

import pytest

from contextdoctor import Config, analyze_path, analyze_paths
from contextdoctor.parsers.formats import csv_rows_to_chunks, html_to_text, jsonl_to_texts
from contextdoctor.parsers.loader import load_document
from contextdoctor.parsers.pragmas import parse_disabled_rules

REPO_ROOT = Path(__file__).resolve().parents[1]
MIXED = REPO_ROOT / "examples" / "mixed_formats"


# --- HTML --------------------------------------------------------------------


def test_html_to_text_strips_scripts_and_tags():
    html = "<html><script>evil()</script><style>x{}</style><p>Hello <b>world</b></p></html>"
    text = html_to_text(html)
    assert "evil()" not in text
    assert "x{}" not in text
    assert "Hello" in text and "world" in text
    assert "<p>" not in text


def test_html_document_is_chunked(tmp_path):
    f = tmp_path / "page.html"
    f.write_text("<h1>Title</h1><p>" + "some body text " * 40 + "</p>", encoding="utf-8")
    doc = load_document(f, "page.html", Config())
    assert doc.kind == "html"
    assert len(doc.chunks) >= 1
    assert "some body text" in doc.chunks[0].text


# --- CSV / TSV ---------------------------------------------------------------


def test_csv_rows_to_chunks():
    raw = "name,role\nAda,engineer\nGrace,admiral\n"
    chunks = csv_rows_to_chunks(raw)
    assert len(chunks) == 2
    assert "name: Ada" in chunks[0]
    assert "role: engineer" in chunks[0]


def test_tsv_delimiter(tmp_path):
    f = tmp_path / "data.tsv"
    f.write_text("a\tb\n1\t2\n3\t4\n", encoding="utf-8")
    doc = load_document(f, "data.tsv", Config())
    assert doc.kind == "tsv"
    assert len(doc.chunks) == 2
    assert "a: 1" in doc.chunks[0].text


# --- JSONL -------------------------------------------------------------------


def test_jsonl_to_texts():
    raw = '{"text": "one"}\n\n{"content": "two"}\ninvalid line\n{"text": "three"}'
    assert jsonl_to_texts(raw) == ["one", "two", "three"]


def test_jsonl_document(tmp_path):
    f = tmp_path / "c.jsonl"
    f.write_text('{"text":"alpha"}\n{"text":"beta"}\n', encoding="utf-8")
    doc = load_document(f, "c.jsonl", Config())
    assert doc.kind == "jsonl"
    assert [c.text for c in doc.chunks] == ["alpha", "beta"]


# --- Mixed-format example directory ------------------------------------------


def test_mixed_formats_example():
    report = analyze_path(MIXED)
    assert report.files_analyzed == 3  # html, csv, jsonl
    assert report.total_chunks > 0


# --- PDF resilience ----------------------------------------------------------


def test_unreadable_pdf_is_skipped(tmp_path):
    (tmp_path / "broken.pdf").write_bytes(b"%PDF-1.4 not really a pdf")
    (tmp_path / "ok.md").write_text("# Fine\n\nSome content here.", encoding="utf-8")
    with pytest.warns(UserWarning, match="skipped"):
        report = analyze_paths([tmp_path])
    # The markdown still analyzed; the bad PDF was skipped, not fatal.
    assert report.files_analyzed == 1


# --- Inline pragmas ----------------------------------------------------------


def test_parse_disabled_rules():
    assert parse_disabled_rules("<!-- contextdoctor: disable=CTX007 -->") == {"CTX007"}
    assert parse_disabled_rules("contextdoctor: disable=CTX003, CTX008") == {"CTX003", "CTX008"}
    assert parse_disabled_rules("contextdoctor: disable-all") == {"*"}
    assert parse_disabled_rules("nothing here") == set()


def test_pragma_suppresses_finding(tmp_path):
    f = tmp_path / "doc.md"
    f.write_text(
        "<!-- contextdoctor: disable=CTX007 -->\n\nkey=sk-ABCDEFGHIJKLMNOPQRSTUVWX1234567890\n",
        encoding="utf-8",
    )
    report = analyze_path(tmp_path)
    assert not any(fnd.rule_id == "CTX007" for fnd in report.findings)


def test_pragma_demo_example():
    report = analyze_path(REPO_ROOT / "examples" / "pragma_demo")
    assert not any(f.rule_id == "CTX007" for f in report.findings)
