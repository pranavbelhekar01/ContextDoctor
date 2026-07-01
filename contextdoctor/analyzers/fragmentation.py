"""Experimental Context Fragmentation Index — CFI (CTX006).

The CFI is ContextDoctor's flagship *experimental* signal. It asks: when the same
named thing is discussed in multiple chunks, how far apart are those chunks?
Information about one entity scattered across the whole corpus is harder for a
retriever to reassemble than information kept close together.

Method (v0.1):
  1. Extract lightweight, local entities per chunk (proper nouns / acronyms).
  2. For every entity appearing in >= ``min_entity_freq`` distinct chunks,
     record the sorted chunk indices where it appears.
  3. Compute the mean gap between consecutive appearances and normalise it by
     the corpus size (``N - 1``), giving a per-entity fragmentation in [0, 1].
  4. CFI is the occurrence-weighted mean of per-entity fragmentation.

Scale: 0.0 = highly coherent, 1.0 = highly fragmented.

This metric is deliberately simple and offline. It is a *signal to inspect*, not
a hard pass/fail. It is clearly labelled experimental everywhere it surfaces.
"""

from __future__ import annotations

from collections import defaultdict
from itertools import pairwise

from contextdoctor.analyzers.base import AnalysisContext, Analyzer
from contextdoctor.models import AnalyzerResult
from contextdoctor.utils.nlp import entity_set


class FragmentationAnalyzer(Analyzer):
    name = "fragmentation"
    title = "Context Fragmentation Index (experimental)"

    def analyze(self, ctx: AnalysisContext) -> AnalyzerResult:
        chunks = ctx.chunks
        n = len(chunks)
        base_metrics = {
            "cfi": 0.0,
            "experimental": True,
            "entities_tracked": 0,
            "repeated_entities": 0,
            "top_fragmented": [],
        }
        if n < 2:
            return self._result(metrics=base_metrics)

        # entity -> set of chunk indices in which it appears
        occurrences: dict[str, set[int]] = defaultdict(set)
        for chunk in chunks:
            for entity in entity_set(chunk.text):
                occurrences[entity].add(chunk.index)

        # Normalise indices to a dense 0..n-1 range (global indices already are,
        # but this keeps CFI stable if a subset of chunks was analyzed).
        index_order = {c.index: pos for pos, c in enumerate(sorted(chunks, key=lambda c: c.index))}

        repeated = {
            e: sorted(index_order[i] for i in idxs)
            for e, idxs in occurrences.items()
            if len(idxs) >= ctx.config.min_entity_freq
        }

        per_entity: list[tuple[str, float, int]] = []
        weighted_sum = 0.0
        weight_total = 0
        denom = n - 1
        for entity, positions in repeated.items():
            gaps = [b - a for a, b in pairwise(positions)]
            mean_gap = sum(gaps) / len(gaps)
            frag = (mean_gap - 1.0) / denom if denom > 0 else 0.0
            frag = max(0.0, min(1.0, frag))
            weight = len(positions)
            per_entity.append((entity, frag, weight))
            weighted_sum += frag * weight
            weight_total += weight

        cfi = round(weighted_sum / weight_total, 3) if weight_total else 0.0

        per_entity.sort(key=lambda t: (t[1], t[2]), reverse=True)
        top = [
            {"entity": e, "fragmentation": round(f, 3), "chunks": w}
            for e, f, w in per_entity[: ctx.config.max_entities_reported]
        ]

        metrics = {
            "cfi": cfi,
            "experimental": True,
            "entities_tracked": len(occurrences),
            "repeated_entities": len(repeated),
            "top_fragmented": top,
        }

        findings = []
        if cfi >= ctx.config.cfi_warning_threshold and repeated:
            worst = ", ".join(f"{e['entity']} ({e['fragmentation']})" for e in top[:3])
            findings.append(
                self._finding(
                    "CTX006",
                    f"Experimental Context Fragmentation Index is {cfi:.3f} "
                    f"(threshold {ctx.config.cfi_warning_threshold}). "
                    f"Most scattered entities: {worst}.",
                    data={"cfi": cfi, "top_fragmented": top},
                )
            )

        return self._result(metrics=metrics, findings=findings)
