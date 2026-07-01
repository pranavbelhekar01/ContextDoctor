"""Detect sections (headings) that span too many chunks (CTX005)."""

from __future__ import annotations

import re

from contextlint.analyzers.base import AnalysisContext, Analyzer
from contextlint.models import AnalyzerResult, Chunk, Document, Location
from contextlint.utils.text import truncate

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")


def _find_headings(raw: str) -> list[tuple[int, int, str]]:
    """Return (char_offset, level, title) for each ATX heading, skipping fences."""
    headings: list[tuple[int, int, str]] = []
    offset = 0
    in_fence = False
    for line in raw.splitlines(keepends=True):
        stripped = line.strip()
        if stripped.startswith(("```", "~~~")):
            in_fence = not in_fence
        elif not in_fence:
            m = _HEADING_RE.match(line.rstrip("\n"))
            if m:
                headings.append((offset, len(m.group(1)), m.group(2).strip()))
        offset += len(line)
    return headings


class HeadingAnalyzer(Analyzer):
    name = "headings"
    title = "Heading Continuity"

    def analyze(self, ctx: AnalysisContext) -> AnalyzerResult:
        findings = []
        max_span = 0
        sections_checked = 0

        for doc in ctx.documents:
            if doc.kind != "markdown" or doc.pre_chunked:
                continue
            headings = _find_headings(doc.raw)
            if not headings:
                continue
            for _offset, level, title, span_chunks in self._sections(doc, headings):
                sections_checked += 1
                max_span = max(max_span, len(span_chunks))
                if len(span_chunks) > ctx.config.max_chunks_per_heading:
                    findings.append(self._section_finding(doc, level, title, span_chunks, ctx))

        metrics = {"sections_checked": sections_checked, "max_section_span": max_span}
        return self._result(metrics=metrics, findings=findings)

    @staticmethod
    def _sections(doc: Document, headings: list[tuple[int, int, str]]):
        """Yield (offset, level, title, chunks) for each heading section."""
        bounds = [h[0] for h in headings] + [len(doc.raw) + 1]
        for i, (offset, level, title) in enumerate(headings):
            start, end = offset, bounds[i + 1]
            in_section = [
                c for c in doc.chunks if c.char_start is not None and start <= c.char_start < end
            ]
            yield offset, level, title, in_section

    def _section_finding(
        self, doc: Document, level: int, title: str, chunks: list[Chunk], ctx: AnalysisContext
    ):
        first = chunks[0]
        return self._finding(
            "CTX005",
            f'Section "{truncate(title, 60)}" (H{level}) in {doc.path} spans '
            f"{len(chunks)} chunks (limit {ctx.config.max_chunks_per_heading}).",
            locations=[
                Location(
                    file=doc.path,
                    chunk_id=first.id,
                    line=first.start_line,
                    detail=f"{len(chunks)} chunks under this heading",
                )
            ],
            data={"heading": title, "level": level, "span": len(chunks)},
        )
