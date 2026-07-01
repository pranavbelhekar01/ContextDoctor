"""Analyzer protocol and the shared analysis context."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import ClassVar

from contextdoctor.config import Config
from contextdoctor.models import AnalyzerResult, Chunk, Document, Finding, Location, Severity
from contextdoctor.rules import get_rule


@dataclass
class AnalysisContext:
    """Everything an analyzer needs: the corpus, the documents, and config."""

    documents: list[Document]
    chunks: list[Chunk]
    config: Config
    #: Scratch space for cross-analyzer data sharing (e.g. duplicate clusters).
    shared: dict = field(default_factory=dict)

    def chunks_for(self, document: Document) -> list[Chunk]:
        return document.chunks


class Analyzer(ABC):
    """Base class for all analyzers.

    Plugins subclass this and may declare the rules they emit via
    :attr:`provides_rules`; the plugin loader registers them automatically so
    they appear in reports, SARIF, ``contextdoctor rules``, and ``--select`` /
    ``--ignore``.
    """

    name: str = "analyzer"
    title: str = "Analyzer"
    #: Rule metadata this analyzer emits (registered on plugin load).
    provides_rules: ClassVar[list] = []

    @abstractmethod
    def analyze(self, ctx: AnalysisContext) -> AnalyzerResult:
        """Compute metrics and findings for the corpus."""

    # --- Convenience helpers for subclasses -------------------------------

    def _result(
        self, metrics: dict | None = None, findings: list[Finding] | None = None
    ) -> AnalyzerResult:
        return AnalyzerResult(
            name=self.name,
            title=self.title,
            metrics=metrics or {},
            findings=findings or [],
        )

    def _finding(
        self,
        rule_id: str,
        message: str,
        *,
        recommendation: str | None = None,
        severity: Severity | None = None,
        locations: list[Location] | None = None,
        data: dict | None = None,
    ) -> Finding:
        rule = get_rule(rule_id)
        return Finding(
            rule_id=rule_id,
            severity=severity or rule.default_severity,
            message=message,
            recommendation=recommendation or rule.recommendation,
            locations=locations or [],
            experimental=rule.experimental,
            data=data or {},
        )
