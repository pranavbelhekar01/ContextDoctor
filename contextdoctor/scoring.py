"""The Context Health Score — a single, braggable 0–100 grade for a corpus.

Inspired by Lighthouse / PageSpeed: one number, one letter grade, easy to put in
a README badge and easy to compare across chunking strategies. The score is a
deterministic function of the findings, so any rule (including community plugin
rules) contributes automatically.

The model is a smooth exponential decay of accumulated severity penalty, which
gives diminishing marginal damage (the 10th warning hurts less than the 1st) and
never leaves the ``0..100`` range.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from contextdoctor.models import Finding, Severity

# Penalty "units" per finding severity. Errors dominate; info barely nudges.
_WEIGHTS = {
    Severity.ERROR: 15.0,
    Severity.WARNING: 6.0,
    Severity.INFO: 1.5,
}

# Larger => more forgiving. Tuned so a single error ≈ 88, five errors ≈ F.
_DECAY = 120.0


@dataclass(frozen=True)
class HealthScore:
    score: int  # 0..100
    grade: str  # A+ .. F
    label: str  # human summary


def _grade(score: int) -> tuple[str, str]:
    if score >= 97:
        return "A+", "pristine"
    if score >= 90:
        return "A", "excellent"
    if score >= 80:
        return "B", "good"
    if score >= 70:
        return "C", "fair"
    if score >= 60:
        return "D", "poor"
    return "F", "critical"


def compute_health(findings: list[Finding]) -> HealthScore:
    penalty = sum(_WEIGHTS.get(f.severity, 0.0) for f in findings)
    score = round(100.0 * math.exp(-penalty / _DECAY))
    score = max(0, min(100, score))
    grade, label = _grade(score)
    return HealthScore(score=score, grade=grade, label=label)
