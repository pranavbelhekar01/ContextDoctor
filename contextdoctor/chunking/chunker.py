"""A deterministic, structure-aware chunker for raw text and markdown.

The chunker groups a document into blocks (paragraphs, tables, fenced code)
and greedily packs those blocks into chunks up to a target size, carrying a
configurable character overlap between consecutive chunks. It keeps tables and
code fences intact where possible, but will hard-split any single block that is
larger than the target size — which is exactly the kind of "table broken across
a boundary" situation ContextDoctor is designed to detect downstream.

The output preserves each chunk's character span in the original document so
later analyzers can map findings back to precise line numbers.
"""

from __future__ import annotations

from dataclasses import dataclass

from contextdoctor.config import Config

_FENCE_PREFIXES = ("```", "~~~")


@dataclass(frozen=True)
class ChunkPiece:
    """One chunk emitted by the chunker.

    ``text`` includes any overlap prefix carried from the previous chunk.
    ``char_start`` / ``char_end`` mark the *new* content's span in the original
    document (excluding the overlap prefix), enabling accurate line mapping.
    """

    text: str
    char_start: int
    char_end: int
    overlap_chars: int


def _line_spans(text: str) -> list[tuple[int, int, bool]]:
    """Return (start, end_excl_newline, is_blank) for every line."""
    spans: list[tuple[int, int, bool]] = []
    pos = 0
    n = len(text)
    while pos <= n:
        nl = text.find("\n", pos)
        if nl == -1:
            line = text[pos:]
            spans.append((pos, n, line.strip() == ""))
            break
        line = text[pos:nl]
        spans.append((pos, nl, line.strip() == ""))
        pos = nl + 1
        if pos == n:  # trailing newline -> final empty line, ignore
            break
    return spans


def _segment(text: str, max_block: int) -> list[tuple[int, int]]:
    """Split text into atomic blocks, hard-splitting oversized ones."""
    blocks: list[tuple[int, int]] = []
    cur_start: int | None = None
    cur_end = 0
    in_fence = False

    for start, end, is_blank in _line_spans(text):
        stripped = text[start:end].lstrip()
        is_fence = stripped.startswith(_FENCE_PREFIXES)

        if in_fence:
            cur_end = end
            if is_fence:
                in_fence = False
            continue

        if is_blank:
            if cur_start is not None:
                blocks.append((cur_start, cur_end))
                cur_start = None
            continue

        if cur_start is None:
            cur_start = start
        cur_end = end
        if is_fence:
            in_fence = True

    if cur_start is not None:
        blocks.append((cur_start, cur_end))

    # Hard-split any block that exceeds the target size.
    result: list[tuple[int, int]] = []
    for s, e in blocks:
        if e - s <= max_block:
            result.append((s, e))
            continue
        pos = s
        while pos < e:
            result.append((pos, min(pos + max_block, e)))
            pos += max_block
    return result


def chunk_document(text: str, config: Config) -> list[ChunkPiece]:
    """Chunk ``text`` into :class:`ChunkPiece` objects using ``config``."""
    chunk_size = max(1, config.chunk_size)
    overlap = max(0, config.chunk_overlap)
    blocks = _segment(text, chunk_size)

    pieces: list[ChunkPiece] = []
    cur_start: int | None = None
    cur_end = 0
    prev_real: str | None = None

    def overlap_prefix() -> str:
        if overlap <= 0 or not prev_real:
            return ""
        return prev_real[-overlap:]

    def flush() -> None:
        nonlocal cur_start, cur_end, prev_real
        if cur_start is None:
            return
        real = text[cur_start:cur_end]
        prefix = overlap_prefix()
        full = f"{prefix}\n{real}" if prefix else real
        pieces.append(
            ChunkPiece(
                text=full,
                char_start=cur_start,
                char_end=cur_end,
                overlap_chars=len(prefix) + (1 if prefix else 0),
            )
        )
        prev_real = real
        cur_start = None

    for b_start, b_end in blocks:
        b_len = b_end - b_start
        if cur_start is not None and (cur_end - cur_start) + b_len > chunk_size:
            flush()
        if cur_start is None:
            cur_start = b_start
        cur_end = b_end

    flush()

    if not pieces and text.strip():
        # Whole document is a single (possibly tiny) chunk.
        pieces.append(ChunkPiece(text=text, char_start=0, char_end=len(text), overlap_chars=0))
    return pieces
