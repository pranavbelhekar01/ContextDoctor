"""SARIF 2.1.0 renderer for GitHub code scanning / any SARIF-aware viewer.

Uploading this to GitHub (``github/codeql-action/upload-sarif``) surfaces each
ContextDoctor finding as an annotation inline on the offending file in the PR.
"""

from __future__ import annotations

import json

from contextdoctor.models import Finding, Report, Severity
from contextdoctor.rules import RULES

_LEVEL = {
    Severity.ERROR: "error",
    Severity.WARNING: "warning",
    Severity.INFO: "note",
}

_HELP_URI = "https://github.com/pranavbelhekar01/ContextDoctor#what-it-checks"


def _rules_metadata() -> list[dict]:
    return [
        {
            "id": rule.id,
            "name": rule.name,
            "shortDescription": {"text": rule.description},
            "fullDescription": {"text": rule.recommendation},
            "helpUri": _HELP_URI,
            "properties": {
                "category": rule.category,
                "experimental": rule.experimental,
            },
            "defaultConfiguration": {"level": _LEVEL[rule.default_severity]},
        }
        for rule in RULES.values()
    ]


def _result(finding: Finding) -> dict:
    locations = []
    for loc in finding.locations:
        region = {}
        if loc.line is not None:
            region = {"startLine": max(1, loc.line)}
        locations.append(
            {
                "physicalLocation": {
                    "artifactLocation": {"uri": loc.file},
                    **({"region": region} if region else {}),
                }
            }
        )
    result = {
        "ruleId": finding.rule_id,
        "level": _LEVEL[finding.severity],
        "message": {"text": f"{finding.message} {finding.recommendation}"},
    }
    if locations:
        result["locations"] = locations
    return result


def render_sarif(report: Report) -> str:
    from contextdoctor import __version__

    doc = {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "ContextDoctor",
                        "informationUri": "https://github.com/pranavbelhekar01/ContextDoctor",
                        "version": __version__,
                        "rules": _rules_metadata(),
                    }
                },
                "results": [_result(f) for f in report.findings],
                "properties": {
                    "healthScore": report.health_score,
                    "healthGrade": report.health_grade,
                },
            }
        ],
    }
    return json.dumps(doc, indent=2)
