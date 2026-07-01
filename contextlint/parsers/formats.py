"""Format-specific text extraction: HTML, CSV/TSV, JSONL, and (optional) PDF.

HTML, CSV, TSV, and JSONL are handled with the standard library only, preserving
ContextLint's zero-dependency core. PDF is *optional*: it uses ``pypdf`` if
installed (``pip install contextlint[pdf]``) and otherwise raises a clear error.
"""

from __future__ import annotations

import csv
import io
import json
import re
from html.parser import HTMLParser

_BLOCK_TAGS = {
    "p",
    "div",
    "section",
    "article",
    "header",
    "footer",
    "br",
    "hr",
    "li",
    "ul",
    "ol",
    "table",
    "tr",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "blockquote",
    "pre",
    "figure",
    "figcaption",
    "main",
    "aside",
}
_SKIP_TAGS = {"script", "style", "noscript", "head", "template", "svg"}


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
        elif tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP_TAGS and self._skip_depth:
            self._skip_depth -= 1
        elif tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            self.parts.append(data)


def html_to_text(raw: str) -> str:
    """Extract readable text from HTML, dropping scripts/styles and tags."""
    parser = _HTMLTextExtractor()
    parser.feed(raw)
    parser.close()
    text = "".join(parser.parts)
    # Collapse the runs of blank lines the block boundaries introduced.
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _row_to_text(header: list[str], row: list[str]) -> str:
    if not header:
        return " | ".join(cell.strip() for cell in row if cell.strip())
    pairs = []
    for i, cell in enumerate(row):
        key = header[i] if i < len(header) else f"col{i + 1}"
        value = cell.strip()
        if value:
            pairs.append(f"{key.strip()}: {value}")
    return "\n".join(pairs)


def csv_rows_to_chunks(raw: str, delimiter: str = ",") -> list[str]:
    """One chunk per data row, rendered as ``header: value`` lines."""
    reader = csv.reader(io.StringIO(raw), delimiter=delimiter)
    rows = [r for r in reader if any(c.strip() for c in r)]
    if not rows:
        return []
    header, data = rows[0], rows[1:]
    if not data:  # header-only or single row -> treat the row itself as content
        return [_row_to_text([], header)]
    return [_row_to_text(header, row) for row in data]


def jsonl_to_texts(raw: str) -> list[str]:
    """Extract chunk text from each non-empty line of a JSONL / NDJSON file."""
    from contextlint.parsers.loader import extract_chunk_text

    texts: list[str] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        text = extract_chunk_text(obj)
        if text is not None:
            texts.append(text)
    return texts


def pdf_to_text(path: str) -> str:
    """Extract text from a PDF using ``pypdf`` if available.

    Kept optional so the core stays dependency-free. Install with
    ``pip install "contextlint[pdf]"``.
    """
    try:
        import pypdf
    except ImportError as exc:  # pragma: no cover - depends on optional extra
        raise RuntimeError(
            "PDF support requires the optional 'pypdf' dependency. "
            'Install it with: pip install "contextlint[pdf]"'
        ) from exc

    reader = pypdf.PdfReader(path)
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(pages).strip()
