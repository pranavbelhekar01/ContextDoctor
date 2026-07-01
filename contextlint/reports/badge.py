"""Shields.io-compatible badge output for the Context Health Score.

``--format badge`` emits a small JSON document you can host and point a
shields.io *endpoint* badge at, plus a ready-to-paste Markdown snippet on stderr.
"""

from __future__ import annotations

import json

from contextlint.models import Report


def _color(score: int) -> str:
    if score >= 90:
        return "brightgreen"
    if score >= 80:
        return "green"
    if score >= 70:
        return "yellowgreen"
    if score >= 60:
        return "yellow"
    if score >= 40:
        return "orange"
    return "red"


def render_badge(report: Report) -> str:
    """Return a shields.io endpoint JSON for the health score."""
    return json.dumps(
        {
            "schemaVersion": 1,
            "label": "context health",
            "message": f"{report.health_score}/100 {report.health_grade}",
            "color": _color(report.health_score),
        },
        indent=2,
    )


def badge_markdown(report: Report, endpoint_url: str = "<URL-to-your-hosted-badge.json>") -> str:
    label = "context%20health"
    color = _color(report.health_score)
    static = (
        f"https://img.shields.io/badge/{label}-"
        f"{report.health_score}%2F100%20{report.health_grade}-{color}"
    )
    return (
        f"![Context Health]({static})\n"
        f"<!-- or a live endpoint badge: "
        f"https://img.shields.io/endpoint?url={endpoint_url} -->"
    )
