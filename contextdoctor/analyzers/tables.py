"""Detect markdown tables split across chunk boundaries (CTX004)."""

from __future__ import annotations

import re
from itertools import pairwise

from contextdoctor.analyzers.base import AnalysisContext, Analyzer
from contextdoctor.models import AnalyzerResult, Chunk, Location

_SEPARATOR_CELL = re.compile(r"^:?-{2,}:?$")


def _nonblank_lines(text: str) -> list[str]:
    return [ln for ln in text.splitlines() if ln.strip()]


def _is_table_row(line: str) -> bool:
    s = line.strip()
    return "|" in s and len(s) > 1


def _is_separator(line: str) -> bool:
    s = line.strip().strip("|").strip()
    if "|" not in line or "-" not in s:
        return False
    cells = [c.strip() for c in s.split("|")]
    real = [c for c in cells if c]
    return bool(real) and all(_SEPARATOR_CELL.match(c) for c in real)


def _has_separator(lines: list[str]) -> bool:
    return any(_is_separator(ln) for ln in lines)


def _ends_in_table(text: str) -> bool:
    lines = _nonblank_lines(text)
    if not lines or not _is_table_row(lines[-1]):
        return False
    if _has_separator(lines):
        return True
    # Two consecutive table rows at the tail also indicate an open table.
    return len(lines) >= 2 and _is_table_row(lines[-2])


def _starts_in_table(text: str) -> bool:
    """True when a chunk opens with table rows but no header separator nearby."""
    lines = _nonblank_lines(text)
    if not lines or not _is_table_row(lines[0]):
        return False
    return not _has_separator(lines[:2])


def _first_row_is_table(text: str) -> bool:
    lines = _nonblank_lines(text)
    return bool(lines) and _is_table_row(lines[0])


class TableAnalyzer(Analyzer):
    name = "tables"
    title = "Table Integrity"

    def analyze(self, ctx: AnalysisContext) -> AnalyzerResult:
        findings = []
        broken_boundaries = 0

        for doc in ctx.documents:
            chunks = doc.chunks
            for a, b in pairwise(chunks):
                broken = (
                    _ends_in_table(a.text) and _first_row_is_table(b.text)
                ) or _starts_in_table(b.text)
                if not broken:
                    continue
                broken_boundaries += 1
                findings.append(self._boundary_finding(doc.path, a, b))

        metrics = {"broken_boundaries": broken_boundaries}
        return self._result(metrics=metrics, findings=findings)

    def _boundary_finding(self, path: str, a: Chunk, b: Chunk):
        return self._finding(
            "CTX004",
            f"A markdown table in {path} is split between chunk "
            f"{a.id.split('#')[-1]} and chunk {b.id.split('#')[-1]}.",
            locations=[
                Location(file=path, chunk_id=a.id, line=a.end_line, detail="table continues"),
                Location(file=path, chunk_id=b.id, line=b.start_line, detail="table continued"),
            ],
            data={"chunk_a": a.id, "chunk_b": b.id},
        )
