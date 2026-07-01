"""JSON report renderer: a stable, machine-readable serialisation of a Report."""

from __future__ import annotations

import json

from contextlint.models import Finding, Report
from contextlint.rules import get_rule


def _finding_to_dict(finding: Finding) -> dict:
    rule = get_rule(finding.rule_id)
    return {
        "rule": finding.rule_id,
        "name": rule.name,
        "category": rule.category,
        "severity": finding.severity.value,
        "experimental": finding.experimental,
        "message": finding.message,
        "recommendation": finding.recommendation,
        "locations": [
            {
                "file": loc.file,
                "chunk_id": loc.chunk_id,
                "line": loc.line,
                "detail": loc.detail,
            }
            for loc in finding.locations
        ],
        "data": finding.data,
    }


def report_to_dict(report: Report) -> dict:
    """Convert a Report into a JSON-serialisable dict."""
    return {
        "tool": "contextlint",
        "version": _version(),
        "root": report.root,
        "generated_at": report.generated_at,
        "health": {
            "score": report.health_score,
            "grade": report.health_grade,
            "label": report.health_label,
        },
        "summary": {
            "files_analyzed": report.files_analyzed,
            "total_chunks": report.total_chunks,
            "findings": len(report.findings),
            "by_severity": report.counts_by_severity(),
        },
        "metrics": report.metrics,
        "findings": [_finding_to_dict(f) for f in report.findings],
        "config": report.config,
    }


def render_json(report: Report, *, indent: int = 2) -> str:
    return json.dumps(report_to_dict(report), indent=indent, sort_keys=False)


def _version() -> str:
    from contextlint import __version__

    return __version__
