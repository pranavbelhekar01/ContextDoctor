"""The analysis engine: discover files, build chunks, run analyzers, assemble a report."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

from contextlint.analyzers import DEFAULT_ANALYZERS, AnalysisContext
from contextlint.config import Config
from contextlint.models import Chunk, Document, Finding, Report, Severity
from contextlint.parsers import discover_files, load_document
from contextlint.parsers.loader import build_chunks_from_texts, extract_chunk_text
from contextlint.plugins import load_all as load_plugins
from contextlint.scoring import compute_health


def _display_path(path: Path, root: Path) -> str:
    try:
        rel = path.relative_to(root)
        return str(rel).replace(os.sep, "/")
    except ValueError:  # pragma: no cover - path outside root
        return str(path).replace(os.sep, "/")


def _sort_findings(findings: list[Finding]) -> list[Finding]:
    return sorted(findings, key=lambda f: (-f.severity.rank, f.rule_id))


def _apply_rule_config(findings: list[Finding], config: Config) -> list[Finding]:
    """Filter by select/ignore and apply per-rule severity overrides."""
    select = set(config.select)
    ignore = set(config.ignore)
    overrides = {k: Severity.from_str(v) for k, v in (config.severity or {}).items()}

    kept: list[Finding] = []
    for f in findings:
        if select and f.rule_id not in select:
            continue
        if f.rule_id in ignore:
            continue
        if f.rule_id in overrides:
            f.severity = overrides[f.rule_id]
        kept.append(f)
    return kept


def _run_analyzers(ctx: AnalysisContext) -> tuple[list[Finding], dict, list]:
    analyzer_classes = list(DEFAULT_ANALYZERS) + load_plugins(ctx.config)
    results = [analyzer_cls().analyze(ctx) for analyzer_cls in analyzer_classes]
    findings: list[Finding] = []
    metrics: dict = {}
    for result in results:
        findings.extend(result.findings)
        metrics[result.name] = result.metrics
    return findings, metrics, results


def _assemble(
    *,
    root: str,
    documents: list[Document],
    chunks: list[Chunk],
    config: Config,
) -> Report:
    ctx = AnalysisContext(documents=documents, chunks=chunks, config=config)
    findings, metrics, results = _run_analyzers(ctx)
    findings = _apply_rule_config(findings, config)
    health = compute_health(findings)
    return Report(
        root=root,
        generated_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        files_analyzed=len(documents),
        total_chunks=len(chunks),
        health_score=health.score,
        health_grade=health.grade,
        health_label=health.label,
        findings=_sort_findings(findings),
        analyzers=results,
        metrics=metrics,
        config=config.to_dict(),
    )


def analyze_paths(paths: list[str | Path], config: Config | None = None) -> Report:
    """Analyze one or more files/directories as a single merged corpus."""
    config = config or Config()
    documents: list[Document] = []
    all_chunks: list[Chunk] = []
    global_index = 0
    for raw in paths:
        p = Path(raw)
        root = p if p.is_dir() else p.parent
        for file in discover_files(p, config):
            display = _display_path(file, root)
            doc = load_document(file, display, config, start_index=global_index)
            documents.append(doc)
            all_chunks.extend(doc.chunks)
            global_index += len(doc.chunks)

    if len(paths) == 1:
        root_label = str(Path(paths[0])).replace(os.sep, "/")
    else:
        root_label = f"{len(paths)} paths"
    return _assemble(root=root_label, documents=documents, chunks=all_chunks, config=config)


def analyze_path(path: str | Path, config: Config | None = None) -> Report:
    """Analyze a single file or directory and return a :class:`Report`.

    Fully local and deterministic — no network, no API keys, no model files.
    """
    return analyze_paths([path], config)


def analyze_chunks(
    chunks: list[str | dict],
    config: Config | None = None,
    *,
    source: str = "chunks",
) -> Report:
    """Analyze an in-memory list of chunks (strings or dicts).

    This is the framework-agnostic entry point. It lets you point ContextLint at
    the exact chunks your pipeline produced, for example::

        from contextlint import analyze_chunks

        # LangChain
        report = analyze_chunks([d.page_content for d in documents])
        # LlamaIndex
        report = analyze_chunks([n.get_content() for n in nodes])

    Dicts are probed for common text keys (``text``, ``content``,
    ``page_content``, ...). Returns the same :class:`Report` as ``analyze_path``.
    """
    config = config or Config()
    texts: list[str] = []
    for item in chunks:
        if isinstance(item, str):
            texts.append(item)
        else:
            text = extract_chunk_text(item)
            if text is not None:
                texts.append(text)
    built = build_chunks_from_texts(texts, source=source, start_index=0)
    doc = Document(
        path=source, kind="chunks", raw="\n\n".join(texts), chunks=built, pre_chunked=True
    )
    return _assemble(root=source, documents=[doc], chunks=built, config=config)


def worst_severity(report: Report) -> Severity | None:
    if not report.findings:
        return None
    return max((f.severity for f in report.findings), key=lambda s: s.rank)
