"""Chunk statistics: size distribution, outliers, and overlap (CTX001/CTX002)."""

from __future__ import annotations

import statistics
from itertools import pairwise

from contextlint.analyzers.base import AnalysisContext, Analyzer
from contextlint.models import AnalyzerResult, Location
from contextlint.utils.text import shingles


def _percentile(sorted_values: list[int], pct: float) -> float:
    """Linear-interpolation percentile (pct in [0, 100])."""
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    rank = (pct / 100.0) * (len(sorted_values) - 1)
    low = int(rank)
    high = min(low + 1, len(sorted_values) - 1)
    frac = rank - low
    return sorted_values[low] + (sorted_values[high] - sorted_values[low]) * frac


class ChunkStatsAnalyzer(Analyzer):
    name = "chunk_stats"
    title = "Chunk Statistics"

    def analyze(self, ctx: AnalysisContext) -> AnalyzerResult:
        chunks = ctx.chunks
        if not chunks:
            return self._result(metrics={"count": 0})

        char_sizes = sorted(c.char_count for c in chunks)
        token_sizes = sorted(c.token_estimate for c in chunks)

        metrics = {
            "count": len(chunks),
            "char": self._distribution(char_sizes),
            "token": self._distribution(token_sizes),
            "overlap_pct": round(self._overlap_pct(ctx), 2),
        }

        findings = []
        cfg = ctx.config

        large = [c for c in chunks if c.char_count > cfg.max_chunk_chars]
        if large:
            largest = max(c.char_count for c in large)
            metrics["oversized_count"] = len(large)
            findings.append(
                self._finding(
                    "CTX001",
                    f"{len(large)} chunk(s) exceed the recommended maximum of "
                    f"{cfg.max_chunk_chars} characters (largest: {largest}).",
                    locations=[
                        Location(
                            file=c.source_file,
                            chunk_id=c.id,
                            line=c.start_line,
                            detail=f"{c.char_count} chars",
                        )
                        for c in large[:20]
                    ],
                    data={
                        "threshold": cfg.max_chunk_chars,
                        "count": len(large),
                        "largest": largest,
                    },
                )
            )

        # Ignore near-empty chunks (likely trailing whitespace) for the "too small" rule.
        small = [c for c in chunks if 0 < c.char_count < cfg.min_chunk_chars]
        if small:
            smallest = min(c.char_count for c in small)
            metrics["undersized_count"] = len(small)
            findings.append(
                self._finding(
                    "CTX002",
                    f"{len(small)} chunk(s) are smaller than the recommended minimum of "
                    f"{cfg.min_chunk_chars} characters (smallest: {smallest}).",
                    locations=[
                        Location(
                            file=c.source_file,
                            chunk_id=c.id,
                            line=c.start_line,
                            detail=f"{c.char_count} chars",
                        )
                        for c in small[:20]
                    ],
                    data={
                        "threshold": cfg.min_chunk_chars,
                        "count": len(small),
                        "smallest": smallest,
                    },
                )
            )

        return self._result(metrics=metrics, findings=findings)

    @staticmethod
    def _distribution(sorted_sizes: list[int]) -> dict:
        return {
            "min": sorted_sizes[0],
            "max": sorted_sizes[-1],
            "mean": round(statistics.fmean(sorted_sizes), 1),
            "median": round(statistics.median(sorted_sizes), 1),
            "p95": round(_percentile(sorted_sizes, 95), 1),
            "stdev": round(statistics.pstdev(sorted_sizes), 1) if len(sorted_sizes) > 1 else 0.0,
        }

    def _overlap_pct(self, ctx: AnalysisContext) -> float:
        """Average shingle overlap between consecutive chunks within each document."""
        size = ctx.config.shingle_size
        ratios: list[float] = []
        for doc in ctx.documents:
            doc_chunks = doc.chunks
            for prev, cur in pairwise(doc_chunks):
                a = shingles(prev.text, size)
                b = shingles(cur.text, size)
                if not b:
                    continue
                # Fraction of the current chunk's shingles already seen in the previous one.
                shared = len(a & b) / len(b)
                ratios.append(shared)
        if not ratios:
            return 0.0
        return 100.0 * (sum(ratios) / len(ratios))
