"""Tests for file discovery and document loading."""

from __future__ import annotations

import json

from contextdoctor.config import Config
from contextdoctor.parsers import discover_files, load_document


def test_discover_skips_hidden_and_unsupported(tmp_path):
    (tmp_path / "a.md").write_text("# A", encoding="utf-8")
    (tmp_path / "b.txt").write_text("b", encoding="utf-8")
    (tmp_path / "c.json").write_text("[]", encoding="utf-8")
    (tmp_path / "ignore.py").write_text("x = 1", encoding="utf-8")
    (tmp_path / ".contextdoctor.json").write_text("{}", encoding="utf-8")
    hidden = tmp_path / ".hidden"
    hidden.mkdir()
    (hidden / "secret.md").write_text("no", encoding="utf-8")

    files = {p.name for p in discover_files(tmp_path, Config())}
    assert files == {"a.md", "b.txt", "c.json"}


def test_discover_single_file(tmp_path):
    f = tmp_path / "only.md"
    f.write_text("# Hello", encoding="utf-8")
    assert discover_files(f, Config()) == [f]


def test_markdown_document_is_chunked_with_lines(tmp_path):
    f = tmp_path / "doc.md"
    f.write_text("# Title\n\n" + "\n\n".join(f"Para {i}." for i in range(20)), encoding="utf-8")
    doc = load_document(f, "doc.md", Config(chunk_size=100, chunk_overlap=0))
    assert doc.kind == "markdown"
    assert not doc.pre_chunked
    assert len(doc.chunks) > 1
    assert doc.chunks[0].start_line is not None


def test_json_list_of_strings(tmp_path):
    f = tmp_path / "chunks.json"
    f.write_text(json.dumps(["first chunk", "second chunk"]), encoding="utf-8")
    doc = load_document(f, "chunks.json", Config())
    assert doc.pre_chunked
    assert [c.text for c in doc.chunks] == ["first chunk", "second chunk"]


def test_json_list_of_objects_various_keys(tmp_path):
    f = tmp_path / "chunks.json"
    payload = [
        {"text": "alpha"},
        {"content": "beta"},
        {"page_content": "gamma"},
    ]
    f.write_text(json.dumps(payload), encoding="utf-8")
    doc = load_document(f, "chunks.json", Config())
    assert [c.text for c in doc.chunks] == ["alpha", "beta", "gamma"]


def test_json_container_key(tmp_path):
    f = tmp_path / "export.json"
    f.write_text(json.dumps({"chunks": [{"text": "one"}, {"text": "two"}]}), encoding="utf-8")
    doc = load_document(f, "export.json", Config())
    assert len(doc.chunks) == 2


def test_global_index_offset(tmp_path):
    f = tmp_path / "chunks.json"
    f.write_text(json.dumps(["a", "b"]), encoding="utf-8")
    doc = load_document(f, "chunks.json", Config(), start_index=10)
    assert [c.index for c in doc.chunks] == [10, 11]
    assert [c.doc_index for c in doc.chunks] == [0, 1]
