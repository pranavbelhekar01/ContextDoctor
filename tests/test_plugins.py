"""Tests for the plugin system (custom analyzers + rules)."""

from __future__ import annotations

from pathlib import Path

import pytest

from contextlint import Config, analyze_chunks
from contextlint.engine import analyze_path
from contextlint.models import Severity
from contextlint.plugins import discover_entry_point_analyzers, load_module_analyzers
from contextlint.rules import RULES, Rule, get_rule, register_rule

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_PLUGIN = REPO_ROOT / "examples" / "plugin" / "contextlint_placeholder_plugin.py"

_PLUGIN_SRC = """
from contextlint.analyzers import AnalysisContext, Analyzer
from contextlint.models import AnalyzerResult, Location, Severity
from contextlint.rules import Rule

class BananaAnalyzer(Analyzer):
    name = "banana"
    title = "Banana"
    provides_rules = [Rule(id="BAN001", name="banana", category="custom",
                           default_severity=Severity.ERROR,
                           description="Contains banana.", recommendation="Remove bananas.")]

    def analyze(self, ctx: AnalysisContext) -> AnalyzerResult:
        findings = []
        for c in ctx.chunks:
            if "banana" in c.text.lower():
                findings.append(self._finding("BAN001", "banana found",
                                              locations=[Location(file=c.source_file, chunk_id=c.id)]))
        return self._result(metrics={"bananas": len(findings)}, findings=findings)
"""


# --- Registry robustness -----------------------------------------------------


def test_get_rule_fallback_for_unknown():
    rule = get_rule("ZZZ999")
    assert rule.id == "ZZZ999"
    assert rule.category == "plugin"


def test_register_rule_does_not_override_builtin():
    fake = Rule(
        id="CTX001",
        name="hijack",
        category="x",
        default_severity=Severity.INFO,
        description="d",
        recommendation="r",
    )
    register_rule(fake)
    assert RULES["CTX001"].name == "chunk-too-large"  # unchanged


def test_register_rule_adds_new():
    register_rule(
        Rule(
            id="NEW777",
            name="new",
            category="x",
            default_severity=Severity.WARNING,
            description="d",
            recommendation="r",
        )
    )
    assert "NEW777" in RULES


# --- Loading local file plugins ---------------------------------------------


def _write_plugin(tmp_path: Path) -> Path:
    p = tmp_path / "banana_plugin.py"
    p.write_text(_PLUGIN_SRC, encoding="utf-8")
    return p


def test_local_file_plugin_via_config(tmp_path):
    plugin = _write_plugin(tmp_path)
    cfg = Config(plugins=(str(plugin),), min_chunk_chars=1)
    report = analyze_chunks(["I like banana bread", "nothing here"], cfg)
    assert any(f.rule_id == "BAN001" for f in report.findings)
    assert "BAN001" in RULES
    # The plugin's error-severity finding should drag the health score down.
    assert report.health_score < 100


def test_plugin_rule_respects_ignore(tmp_path):
    plugin = _write_plugin(tmp_path)
    cfg = Config(plugins=(str(plugin),), ignore=("BAN001",), min_chunk_chars=1)
    report = analyze_chunks(["banana"], cfg)
    assert not any(f.rule_id == "BAN001" for f in report.findings)


def test_broken_plugin_is_skipped(tmp_path):
    bad = tmp_path / "broken.py"
    bad.write_text("this is not valid python !!!", encoding="utf-8")
    cfg = Config(plugins=(str(bad),))
    # Should not raise; simply warns and continues.
    with pytest.warns(UserWarning, match="failed to load plugin"):
        report = analyze_chunks(["hello world"], cfg)
    assert report is not None


def test_load_module_analyzers_returns_classes(tmp_path):
    plugin = _write_plugin(tmp_path)
    classes = load_module_analyzers([str(plugin)])
    assert classes and classes[0].__name__ == "BananaAnalyzer"


# --- The shipped example plugin ---------------------------------------------


def test_example_placeholder_plugin(examples_dir):
    # tiny.md contains "TODO", which PLH001 should flag.
    cfg = Config(plugins=(str(EXAMPLE_PLUGIN),))
    report = analyze_path(examples_dir / "messy_docs", cfg)
    assert any(f.rule_id == "PLH001" for f in report.findings)


# --- Entry-point discovery (monkeypatched) ----------------------------------


def test_entry_point_discovery(monkeypatch, tmp_path):
    plugin = _write_plugin(tmp_path)
    loaded = load_module_analyzers([str(plugin)])
    banana_cls = loaded[0]

    class FakeEP:
        name = "banana"

        def load(self):
            return banana_cls

    monkeypatch.setattr("contextlint.plugins.metadata.entry_points", lambda group: [FakeEP()])
    found = discover_entry_point_analyzers()
    assert banana_cls in found
