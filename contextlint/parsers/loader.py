"""File discovery and document loading.

For ``.md`` / ``.txt`` inputs ContextLint chunks the raw text itself. For
``.json`` inputs it reads chunks that already exist in the export (the common
case when auditing a vector store dump), so the reported metrics reflect *your*
chunking, not ours.
"""

from __future__ import annotations

import json
from pathlib import Path

from contextlint.chunking import chunk_document
from contextlint.config import Config
from contextlint.models import Chunk, Document
from contextlint.utils.text import (
    estimate_tokens,
    line_starts,
    offset_to_line,
    word_count,
)

_MARKDOWN_EXT = {".md", ".markdown"}
_TEXT_EXT = {".txt"}
_JSON_EXT = {".json"}

# Keys we probe when a JSON export stores chunk text inside objects.
_TEXT_KEYS = ("text", "content", "chunk", "page_content", "body", "passage")
_CHUNK_CONTAINER_KEYS = ("chunks", "documents", "nodes", "data", "items", "passages")


def discover_files(path: str | Path, config: Config) -> list[Path]:
    """Return a sorted list of analyzable files under ``path``."""
    path = Path(path)
    if path.is_file():
        return [path]
    if not path.exists():
        raise FileNotFoundError(f"Path does not exist: {path}")
    exts = {e.lower() for e in config.extensions}
    files = [
        p
        for p in path.rglob("*")
        if p.is_file() and p.suffix.lower() in exts and not _is_hidden(p, path)
    ]
    return sorted(files, key=lambda p: str(p).lower())


def _is_hidden(file: Path, root: Path) -> bool:
    """Skip dotfiles and dot-directories (e.g. .contextlint.json, .git/)."""
    try:
        rel = file.relative_to(root)
    except ValueError:  # pragma: no cover
        rel = file
    return any(part.startswith(".") for part in rel.parts)


def _make_chunk(
    *,
    source: str,
    global_index: int,
    doc_index: int,
    text: str,
    char_start: int | None = None,
    char_end: int | None = None,
    start_line: int | None = None,
    end_line: int | None = None,
) -> Chunk:
    return Chunk(
        id=f"{source}#{doc_index}",
        source_file=source,
        index=global_index,
        doc_index=doc_index,
        text=text,
        char_count=len(text),
        word_count=word_count(text),
        token_estimate=estimate_tokens(text),
        char_start=char_start,
        char_end=char_end,
        start_line=start_line,
        end_line=end_line,
    )


def build_chunks_from_texts(texts: list[str], source: str, start_index: int = 0) -> list[Chunk]:
    """Build pre-chunked :class:`Chunk` objects from raw texts (no re-chunking)."""
    return [
        _make_chunk(source=source, global_index=start_index + i, doc_index=i, text=text)
        for i, text in enumerate(texts)
    ]


def extract_chunk_text(item: object) -> str | None:
    """Pull chunk text out of a string or a dict with a known text key."""
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        for key in _TEXT_KEYS:
            val = item.get(key)
            if isinstance(val, str) and val.strip():
                return val
    return None


def _load_chunked_text(
    raw: str, source: str, kind: str, config: Config, start_index: int
) -> Document:
    pieces = chunk_document(raw, config)
    starts = line_starts(raw)
    chunks: list[Chunk] = []
    for doc_index, piece in enumerate(pieces):
        chunks.append(
            _make_chunk(
                source=source,
                global_index=start_index + doc_index,
                doc_index=doc_index,
                text=piece.text,
                char_start=piece.char_start,
                char_end=piece.char_end,
                start_line=offset_to_line(piece.char_start, starts),
                end_line=offset_to_line(max(piece.char_start, piece.char_end - 1), starts),
            )
        )
    return Document(path=source, kind=kind, raw=raw, chunks=chunks, pre_chunked=False)


def _extract_json_texts(data: object) -> list[str]:
    """Best-effort extraction of chunk texts from a decoded JSON structure."""
    # A bare list of chunks (strings or objects).
    if isinstance(data, list):
        texts = [t for t in (extract_chunk_text(i) for i in data) if t is not None]
        if texts:
            return texts

    # An object that contains a list of chunks under a known key.
    if isinstance(data, dict):
        for key in _CHUNK_CONTAINER_KEYS:
            container = data.get(key)
            if isinstance(container, list):
                collected: list[str] = []
                for item in container:
                    t = extract_chunk_text(item)
                    if t is not None:
                        collected.append(t)
                    elif isinstance(item, dict):
                        # e.g. {"documents": [{"chunks": [...]}]}
                        collected.extend(_extract_json_texts(item))
                if collected:
                    return collected
        # Single chunk object.
        single = extract_chunk_text(data)
        if single is not None:
            return [single]
    return []


def _load_json(raw: str, source: str, config: Config, start_index: int) -> Document:
    data = json.loads(raw)
    texts = _extract_json_texts(data)
    chunks = build_chunks_from_texts(texts, source=source, start_index=start_index)
    return Document(path=source, kind="json", raw=raw, chunks=chunks, pre_chunked=True)


def load_document(
    path: str | Path,
    display_path: str,
    config: Config,
    start_index: int = 0,
) -> Document:
    """Load and chunk a single file into a :class:`Document`.

    ``start_index`` is the global chunk index the first chunk should receive so
    indices stay unique across the whole corpus.
    """
    path = Path(path)
    raw = path.read_text(encoding="utf-8", errors="replace")
    suffix = path.suffix.lower()
    if suffix in _JSON_EXT:
        return _load_json(raw, display_path, config, start_index)
    if suffix in _MARKDOWN_EXT:
        return _load_chunked_text(raw, display_path, "markdown", config, start_index)
    if suffix in _TEXT_EXT:
        return _load_chunked_text(raw, display_path, "text", config, start_index)
    # Unknown extensions are treated as plain text.
    return _load_chunked_text(raw, display_path, "text", config, start_index)
