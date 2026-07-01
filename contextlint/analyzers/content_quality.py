"""Content-quality checks: secrets, PII, and encoding artifacts (CTX007-009)."""

from __future__ import annotations

from collections import Counter

from contextlint.analyzers.base import AnalysisContext, Analyzer
from contextlint.models import AnalyzerResult, Location
from contextlint.utils.patterns import find_encoding_issues, find_pii, find_secrets


class ContentQualityAnalyzer(Analyzer):
    name = "content_quality"
    title = "Content Quality"

    def analyze(self, ctx: AnalysisContext) -> AnalyzerResult:
        cfg = ctx.config
        findings = []

        secret_locations: list[Location] = []
        secret_types: Counter[str] = Counter()
        pii_locations: list[Location] = []
        pii_types: Counter[str] = Counter()
        enc_locations: list[Location] = []
        enc_types: Counter[str] = Counter()

        for chunk in ctx.chunks:
            if cfg.detect_secrets:
                for label in find_secrets(chunk.text):
                    secret_types[label] += 1
                    secret_locations.append(
                        Location(
                            file=chunk.source_file,
                            chunk_id=chunk.id,
                            line=chunk.start_line,
                            detail=label,
                        )
                    )
            if cfg.detect_pii:
                for kind, count in find_pii(chunk.text).items():
                    pii_types[kind] += count
                    pii_locations.append(
                        Location(
                            file=chunk.source_file,
                            chunk_id=chunk.id,
                            line=chunk.start_line,
                            detail=f"{kind} x{count}",
                        )
                    )
            if cfg.detect_encoding_artifacts:
                for kind, count in find_encoding_issues(chunk.text).items():
                    enc_types[kind] += count
                    enc_locations.append(
                        Location(
                            file=chunk.source_file,
                            chunk_id=chunk.id,
                            line=chunk.start_line,
                            detail=f"{kind} x{count}",
                        )
                    )

        n_secret_chunks = len({loc.chunk_id for loc in secret_locations})
        n_pii_chunks = len({loc.chunk_id for loc in pii_locations})
        n_enc_chunks = len({loc.chunk_id for loc in enc_locations})

        if secret_locations:
            kinds = ", ".join(sorted(secret_types))
            findings.append(
                self._finding(
                    "CTX007",
                    f"Possible embedded secret(s) — {len(secret_locations)} occurrence(s) "
                    f"across {n_secret_chunks} chunk(s): {kinds}. "
                    f"(Values are redacted and never shown.)",
                    locations=secret_locations[:20],
                    data={"types": dict(secret_types)},
                )
            )
        if pii_locations:
            kinds = ", ".join(sorted(pii_types))
            findings.append(
                self._finding(
                    "CTX008",
                    f"PII detected — {len(pii_locations)} occurrence(s) across "
                    f"{n_pii_chunks} chunk(s): {kinds}. (Values are redacted and never shown.)",
                    locations=pii_locations[:20],
                    data={"types": dict(pii_types)},
                )
            )
        if enc_locations:
            kinds = ", ".join(sorted(enc_types))
            findings.append(
                self._finding(
                    "CTX009",
                    f"Encoding artifacts — {len(enc_locations)} occurrence(s) across "
                    f"{n_enc_chunks} chunk(s): {kinds}.",
                    locations=enc_locations[:20],
                    data={"types": dict(enc_types)},
                )
            )

        metrics = {
            "chunks_with_secrets": n_secret_chunks,
            "chunks_with_pii": n_pii_chunks,
            "chunks_with_encoding_issues": n_enc_chunks,
        }
        return self._result(metrics=metrics, findings=findings)
