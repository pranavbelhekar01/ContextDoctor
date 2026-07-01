"""Tests for the chunker."""

from __future__ import annotations

from contextlint.chunking import chunk_document
from contextlint.config import Config


def test_empty_document_yields_no_chunks():
    assert chunk_document("", Config()) == []
    assert chunk_document("   \n  \n", Config()) == []


def test_single_small_document_is_one_chunk():
    pieces = chunk_document("A short note.", Config())
    assert len(pieces) == 1
    assert pieces[0].char_start == 0


def test_packs_paragraphs_and_respects_size():
    config = Config(chunk_size=120, chunk_overlap=0)
    paras = [f"Paragraph number {i} with a little bit of text to fill space." for i in range(10)]
    text = "\n\n".join(paras)
    pieces = chunk_document(text, config)
    assert len(pieces) > 1
    # No chunk's new content should greatly exceed the target size.
    for p in pieces:
        assert (p.char_end - p.char_start) <= config.chunk_size + 5


def test_oversized_block_is_hard_split():
    config = Config(chunk_size=100, chunk_overlap=0)
    text = "x" * 1000  # single block, no boundaries
    pieces = chunk_document(text, config)
    assert len(pieces) >= 10
    for p in pieces:
        assert (p.char_end - p.char_start) <= 100


def test_overlap_is_carried_between_chunks():
    config = Config(chunk_size=120, chunk_overlap=40)
    paras = [f"Paragraph {i} " + "content " * 10 for i in range(6)]
    text = "\n\n".join(paras)
    pieces = chunk_document(text, config)
    assert len(pieces) >= 2
    # Every chunk after the first carries an overlap prefix.
    assert all(p.overlap_chars > 0 for p in pieces[1:])


def test_char_spans_map_into_original_text():
    config = Config(chunk_size=80, chunk_overlap=0)
    text = "\n\n".join(f"Block {i} text here." for i in range(8))
    pieces = chunk_document(text, config)
    for p in pieces:
        # The new-content span should be a real slice of the source.
        assert text[p.char_start : p.char_end] in p.text
