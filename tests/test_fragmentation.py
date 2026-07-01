"""Tests for the experimental Context Fragmentation Index (CFI / CTX006)."""

from __future__ import annotations

from contextlint.analyzers import FragmentationAnalyzer
from contextlint.config import Config
from helpers import build_context


def _cfi(result):
    return result.metrics["cfi"]


def test_coherent_corpus_has_low_cfi():
    # Entity appears in adjacent chunks -> minimal gaps -> low fragmentation.
    texts = [
        "Zephyr starts the job.",
        "Zephyr continues the job.",
        "Zephyr finishes the job.",
        "Unrelated closing remarks about the weather and nothing else at all.",
    ]
    result = FragmentationAnalyzer().analyze(build_context(texts))
    assert _cfi(result) < 0.35
    assert not any(f.rule_id == "CTX006" for f in result.findings)


def test_fragmented_corpus_has_high_cfi():
    # Filler starts lowercase and repeats no proper noun, so it introduces no
    # tracked entity that would otherwise dilute the weighted CFI.
    filler = "assorted background material at position {} covering routine minutiae only"
    texts = (
        ["Zephyr and Nimbus and Quasar are introduced here at the very beginning."]
        + [filler.format(i) for i in range(8)]
        + ["Finally Zephyr and Nimbus and Quasar return at the very end of the corpus."]
    )
    config = Config(min_entity_freq=2, cfi_warning_threshold=0.6)
    result = FragmentationAnalyzer().analyze(build_context(texts, config=config))
    assert _cfi(result) >= 0.6
    assert any(f.rule_id == "CTX006" for f in result.findings)
    assert result.metrics["experimental"] is True


def test_cfi_is_zero_for_trivial_corpus():
    result = FragmentationAnalyzer().analyze(build_context(["only one chunk"]))
    assert _cfi(result) == 0.0
    assert result.findings == []


def test_cfi_deterministic():
    texts = ["Apollo here.", "nothing.", "nothing else.", "Apollo again at the end."]
    a = FragmentationAnalyzer().analyze(build_context(texts)).metrics["cfi"]
    b = FragmentationAnalyzer().analyze(build_context(texts)).metrics["cfi"]
    assert a == b


def test_top_fragmented_is_reported():
    filler = [f"padding text here without entities {i}" for i in range(6)]
    texts = ["Orion appears.", *filler, "Orion reappears far away."]
    result = FragmentationAnalyzer().analyze(build_context(texts))
    assert result.metrics["top_fragmented"]
    assert result.metrics["top_fragmented"][0]["entity"] == "orion"
