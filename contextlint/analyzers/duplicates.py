"""Exact and near-duplicate detection across the corpus (CTX003)."""

from __future__ import annotations

from collections import defaultdict

from contextlint.analyzers.base import AnalysisContext, Analyzer
from contextlint.models import AnalyzerResult, Chunk, Location
from contextlint.utils.hashing import content_hash, minhash_signature, minhash_similarity
from contextlint.utils.text import shingles

# Above this many chunks we skip the exact O(n^2) Jaccard recomputation and rely
# on the MinHash approximation to keep large corpora fast.
_EXACT_JACCARD_LIMIT = 1500


class DuplicateAnalyzer(Analyzer):
    name = "duplicates"
    title = "Duplicate Detection"

    def analyze(self, ctx: AnalysisContext) -> AnalyzerResult:
        chunks = [c for c in ctx.chunks if c.text.strip()]
        if len(chunks) < 2:
            return self._result(metrics={"exact_groups": 0, "near_pairs": 0, "duplicate_pct": 0.0})

        exact_groups = self._exact_groups(chunks)
        duplicated_ids: set[str] = set()
        for group in exact_groups:
            for c in group[1:]:  # first occurrence is the canonical one
                duplicated_ids.add(c.id)

        near_pairs = self._near_pairs(chunks, ctx.config, self._exact_pair_ids(exact_groups))
        for _a, b, _sim in near_pairs:
            duplicated_ids.add(b.id)

        duplicate_pct = round(100.0 * len(duplicated_ids) / len(chunks), 2)
        metrics = {
            "exact_groups": len(exact_groups),
            "exact_duplicate_chunks": sum(len(g) - 1 for g in exact_groups),
            "near_pairs": len(near_pairs),
            "duplicate_pct": duplicate_pct,
        }

        findings = []
        if exact_groups:
            locations = [
                Location(file=c.source_file, chunk_id=c.id, line=c.start_line)
                for group in exact_groups[:20]
                for c in group
            ]
            findings.append(
                self._finding(
                    "CTX003",
                    f"{len(exact_groups)} group(s) of exact-duplicate chunks "
                    f"({metrics['exact_duplicate_chunks']} redundant chunk(s)).",
                    locations=locations,
                    data={"kind": "exact", "groups": len(exact_groups)},
                )
            )

        if near_pairs:
            threshold_pct = int(ctx.config.near_duplicate_threshold * 100)
            locations = [
                Location(
                    file=b.source_file,
                    chunk_id=b.id,
                    line=b.start_line,
                    detail=f"~{round(sim * 100)}% similar to {a.id.split('#')[-1]}",
                )
                for a, b, sim in near_pairs[:20]
            ]
            findings.append(
                self._finding(
                    "CTX003",
                    f"{len(near_pairs)} near-duplicate chunk pair(s) above "
                    f"{threshold_pct}% Jaccard similarity.",
                    locations=locations,
                    data={"kind": "near", "pairs": len(near_pairs)},
                )
            )

        if not findings and duplicate_pct >= ctx.config.duplicate_pct_warning:
            findings.append(
                self._finding(
                    "CTX003",
                    f"{duplicate_pct}% of chunks are duplicated across the corpus.",
                    data={"kind": "corpus", "duplicate_pct": duplicate_pct},
                )
            )

        ctx.shared["duplicate_ids"] = duplicated_ids
        return self._result(metrics=metrics, findings=findings)

    @staticmethod
    def _exact_groups(chunks: list[Chunk]) -> list[list[Chunk]]:
        buckets: dict[str, list[Chunk]] = defaultdict(list)
        for c in chunks:
            buckets[content_hash(c.text)].append(c)
        groups = [sorted(g, key=lambda c: c.index) for g in buckets.values() if len(g) > 1]
        return sorted(groups, key=lambda g: g[0].index)

    @staticmethod
    def _exact_pair_ids(groups: list[list[Chunk]]) -> set[frozenset[str]]:
        pairs: set[frozenset[str]] = set()
        for g in groups:
            for i in range(len(g)):
                for j in range(i + 1, len(g)):
                    pairs.add(frozenset({g[i].id, g[j].id}))
        return pairs

    @staticmethod
    def _near_pairs(
        chunks: list[Chunk], config, exclude: set[frozenset[str]]
    ) -> list[tuple[Chunk, Chunk, float]]:
        threshold = config.near_duplicate_threshold
        size = config.shingle_size
        shingle_sets = {c.id: shingles(c.text, size) for c in chunks}
        signatures = {c.id: minhash_signature(shingle_sets[c.id]) for c in chunks}

        n = len(chunks)
        use_exact = n <= _EXACT_JACCARD_LIMIT
        pairs: list[tuple[Chunk, Chunk, float]] = []
        for i in range(n):
            ci = chunks[i]
            for j in range(i + 1, n):
                cj = chunks[j]
                if frozenset({ci.id, cj.id}) in exclude:
                    continue
                approx = minhash_similarity(signatures[ci.id], signatures[cj.id])
                if approx < threshold - 0.1:  # cheap pre-filter
                    continue
                if use_exact:
                    a, b = shingle_sets[ci.id], shingle_sets[cj.id]
                    union = len(a | b)
                    sim = (len(a & b) / union) if union else 0.0
                else:
                    sim = approx
                if sim >= threshold:
                    pairs.append((ci, cj, sim))
        pairs.sort(key=lambda t: t[2], reverse=True)
        return pairs
