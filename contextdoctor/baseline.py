"""Baseline files: freeze today's findings so CI only fails on *new* ones.

Adopting a linter on an existing corpus is painful if it floods you with
pre-existing issues. A baseline records the current findings; subsequent runs
suppress anything already in the baseline and report only what's new.

Fingerprints are intentionally coarse — ``rule_id`` + the set of files a finding
touches — so they survive minor edits (line moves, re-chunking) while still
catching genuinely new problems.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from contextdoctor.models import Finding, Report


def fingerprint(finding: Finding) -> str:
    files = sorted({loc.file for loc in finding.locations})
    basis = finding.rule_id + "|" + "|".join(files)
    return hashlib.sha1(basis.encode("utf-8")).hexdigest()[:16]


def collect_fingerprints(report: Report) -> list[str]:
    return sorted({fingerprint(f) for f in report.findings})


def save_baseline(report: Report, path: str | Path) -> int:
    fingerprints = collect_fingerprints(report)
    data = {
        "tool": "contextdoctor",
        "version": 1,
        "generated_at": report.generated_at,
        "count": len(fingerprints),
        "fingerprints": fingerprints,
    }
    Path(path).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return len(fingerprints)


def load_baseline(path: str | Path) -> set[str]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return set(data.get("fingerprints", []))
