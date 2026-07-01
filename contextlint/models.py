"""Core data structures shared across parsers, analyzers, and reports."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Severity(str, Enum):
    """Ordered severity levels for findings."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"

    @property
    def rank(self) -> int:
        """Numeric rank; higher is more severe. Useful for sorting/filtering."""
        return {"info": 0, "warning": 1, "error": 2}[self.value]

    @classmethod
    def from_str(cls, value: str) -> Severity:
        return cls(value.strip().lower())


@dataclass(frozen=True)
class Chunk:
    """A single unit of retrievable context.

    Chunks are either produced by ContextLint's own chunker (for raw ``.md`` /
    ``.txt`` inputs) or read directly from a pre-chunked JSON export.
    """

    id: str
    source_file: str
    index: int  # global position across the whole corpus (analysis order)
    doc_index: int  # position within the chunk's own source document
    text: str
    char_count: int
    word_count: int
    token_estimate: int
    char_start: int | None = None  # offset into the source document (raw inputs only)
    char_end: int | None = None
    start_line: int | None = None
    end_line: int | None = None

    @property
    def short_id(self) -> str:
        return self.id.split(":")[-1]


@dataclass
class Document:
    """A parsed source file plus the chunks derived from it."""

    path: str
    kind: str  # "markdown" | "text" | "json" | "html" | "csv" | "jsonl"
    raw: str
    chunks: list[Chunk] = field(default_factory=list)
    pre_chunked: bool = False  # True when chunks came from the input (JSON), not our chunker
    disabled_rules: set[str] = field(
        default_factory=set
    )  # from inline `contextlint: disable=` pragmas


@dataclass(frozen=True)
class Location:
    """A reference back to the place a finding was detected."""

    file: str
    chunk_id: str | None = None
    line: int | None = None
    detail: str | None = None

    def render(self) -> str:
        parts = [self.file]
        if self.line is not None:
            parts.append(f":{self.line}")
        suffix = ""
        if self.chunk_id is not None:
            suffix += f" [chunk {self.chunk_id.split(':')[-1]}]"
        if self.detail:
            suffix += f" ({self.detail})"
        return "".join(parts) + suffix


@dataclass
class Finding:
    """A single rule violation with actionable context."""

    rule_id: str
    severity: Severity
    message: str
    recommendation: str
    locations: list[Location] = field(default_factory=list)
    experimental: bool = False
    data: dict = field(default_factory=dict)


@dataclass
class AnalyzerResult:
    """Output of one analyzer: computed metrics plus any findings."""

    name: str
    title: str
    metrics: dict = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)


@dataclass
class Report:
    """The complete result of an analysis run."""

    root: str
    generated_at: str
    files_analyzed: int
    total_chunks: int
    health_score: int = 100
    health_grade: str = "A"
    health_label: str = "excellent"
    baseline_suppressed: int = 0
    findings: list[Finding] = field(default_factory=list)
    analyzers: list[AnalyzerResult] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)
    config: dict = field(default_factory=dict)

    def counts_by_severity(self) -> dict[str, int]:
        counts = {s.value: 0 for s in Severity}
        for finding in self.findings:
            counts[finding.severity.value] += 1
        return counts

    def has_at_least(self, severity: Severity) -> bool:
        return any(f.severity.rank >= severity.rank for f in self.findings)
