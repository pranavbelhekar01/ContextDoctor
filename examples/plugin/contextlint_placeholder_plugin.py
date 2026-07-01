"""Example ContextLint plugin: flag unfinished / placeholder content.

Unfinished text ("TODO", "FIXME", "lorem ipsum", "coming soon") that slips into a
knowledge base gets embedded and retrieved as if it were real content. This
plugin adds a single rule, ``PLH001``, that flags it.

Use it three ways:

  # ad-hoc, from the CLI
  contextlint analyze ./docs --plugin examples/plugin/contextlint_placeholder_plugin.py

  # via config (.contextlint.json)
  { "plugins": ["examples/plugin/contextlint_placeholder_plugin.py"] }

  # as a published package (pyproject.toml)
  [project.entry-points."contextlint.analyzers"]
  placeholder = "contextlint_placeholder_plugin:PlaceholderAnalyzer"
"""

from __future__ import annotations

import re
from typing import ClassVar

from contextlint.analyzers import AnalysisContext, Analyzer
from contextlint.models import AnalyzerResult, Location, Severity
from contextlint.rules import Rule

PLACEHOLDER_RULE = Rule(
    id="PLH001",
    name="placeholder-content",
    category="content-quality",
    default_severity=Severity.WARNING,
    description="Unfinished or placeholder text was found in the content.",
    recommendation=(
        "Remove or complete placeholder content before indexing. Markers like TODO, "
        "FIXME, TBD, and lorem-ipsum filler get embedded and can be retrieved as if they "
        "were real answers."
    ),
)

_MARKER_RE = re.compile(
    r"\b(TODO|FIXME|TBD|WIP|XXX|lorem ipsum|coming soon|placeholder)\b",
    re.IGNORECASE,
)


class PlaceholderAnalyzer(Analyzer):
    name = "placeholder"
    title = "Placeholder Content"
    provides_rules: ClassVar[list] = [PLACEHOLDER_RULE]

    def analyze(self, ctx: AnalysisContext) -> AnalyzerResult:
        locations: list[Location] = []
        markers: set[str] = set()
        for chunk in ctx.chunks:
            hits = _MARKER_RE.findall(chunk.text)
            if not hits:
                continue
            markers.update(h.lower() for h in hits)
            locations.append(
                Location(
                    file=chunk.source_file,
                    chunk_id=chunk.id,
                    line=chunk.start_line,
                    detail=", ".join(sorted({h.lower() for h in hits})),
                )
            )

        findings = []
        if locations:
            findings.append(
                self._finding(
                    "PLH001",
                    f"Placeholder content in {len(locations)} chunk(s): "
                    f"{', '.join(sorted(markers))}.",
                    locations=locations[:20],
                    data={"markers": sorted(markers)},
                )
            )
        return self._result(metrics={"placeholder_chunks": len(locations)}, findings=findings)


# Optional: a module-level ANALYZERS list is also recognised by the loader.
ANALYZERS = [PlaceholderAnalyzer]
