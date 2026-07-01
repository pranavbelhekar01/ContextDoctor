"""The analysis engine: discover files, build chunks, run analyzers, assemble a report."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

from contextlint.analyzers import DEFAULT_ANALYZERS, AnalysisContext
from contextlint.config import Config
from contextlint.models import Chunk, Document, Finding, Report, Severity
from contextlint.parsers import discover_files, load_document


def _display_path(path: Path, root: Path) -> str:
    try:
        rel = path.relative_to(root)
        return str(rel).replace(os.sep, "/")
    except ValueError:  # pragma: no cover - path outside root
        return str(path).replace(os.sep, "/")


def _sort_findings(findings: list[Finding]) -> list[Finding]:
    return sorted(
        findings,
        key=lambda f: (-f.severity.rank, f.rule_id),
    )


def analyze_path(path: str | Path, config: Config | None = None) -> Report:
    """Analyze a file or directory and return a :class:`Report`.

    Fully local and deterministic — no network, no API keys, no model files.
    """
    path = Path(path)
    config = config or Config()
    root = path if path.is_dir() else path.parent

    files = discover_files(path, config)

    documents: list[Document] = []
    all_chunks: list[Chunk] = []
    global_index = 0
    for file in files:
        display = _display_path(file, root)
        doc = load_document(file, display, config, start_index=global_index)
        documents.append(doc)
        all_chunks.extend(doc.chunks)
        global_index += len(doc.chunks)

    ctx = AnalysisContext(documents=documents, chunks=all_chunks, config=config)

    results = [analyzer_cls().analyze(ctx) for analyzer_cls in DEFAULT_ANALYZERS]

    findings: list[Finding] = []
    metrics: dict = {}
    for result in results:
        findings.extend(result.findings)
        metrics[result.name] = result.metrics

    return Report(
        root=_display_path(path.resolve(), path.resolve().parent)
        if path.is_file()
        else str(path).replace(os.sep, "/"),
        generated_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        files_analyzed=len(documents),
        total_chunks=len(all_chunks),
        findings=_sort_findings(findings),
        analyzers=results,
        metrics=metrics,
        config=config.to_dict(),
    )


def worst_severity(report: Report) -> Severity | None:
    if not report.findings:
        return None
    return max((f.severity for f in report.findings), key=lambda s: s.rank)
