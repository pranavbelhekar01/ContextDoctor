"""Plain helper functions shared by tests (imported, not fixtures)."""

from __future__ import annotations

from contextlint.analyzers.base import AnalysisContext
from contextlint.config import Config
from contextlint.models import Chunk, Document
from contextlint.utils.text import estimate_tokens, word_count


def make_chunk(source: str, index: int, doc_index: int, text: str) -> Chunk:
    return Chunk(
        id=f"{source}#{doc_index}",
        source_file=source,
        index=index,
        doc_index=doc_index,
        text=text,
        char_count=len(text),
        word_count=word_count(text),
        token_estimate=estimate_tokens(text),
    )


def build_context(
    texts: list[str],
    *,
    config: Config | None = None,
    source: str = "doc.txt",
    kind: str = "text",
    pre_chunked: bool = True,
) -> AnalysisContext:
    """Build an AnalysisContext from a list of chunk texts (each text = one chunk)."""
    config = config or Config()
    chunks = [make_chunk(source, i, i, t) for i, t in enumerate(texts)]
    doc = Document(
        path=source, kind=kind, raw="\n\n".join(texts), chunks=chunks, pre_chunked=pre_chunked
    )
    return AnalysisContext(documents=[doc], chunks=chunks, config=config)
