"""Tests for the CLI and configuration loading."""

from __future__ import annotations

import json

from contextlint.cli import main
from contextlint.config import Config

# --- Config ------------------------------------------------------------------


def test_config_from_dict_ignores_unknown_keys():
    cfg = Config.from_dict({"chunk_size": 999, "not_a_real_key": 1})
    assert cfg.chunk_size == 999
    assert not hasattr(cfg, "not_a_real_key")


def test_config_load_json(tmp_path):
    p = tmp_path / ".contextlint.json"
    p.write_text(json.dumps({"max_chunk_chars": 4321}), encoding="utf-8")
    cfg = Config.load(p)
    assert cfg.max_chunk_chars == 4321


def test_config_discover_json(tmp_path):
    (tmp_path / ".contextlint.json").write_text(
        json.dumps({"min_chunk_chars": 7}), encoding="utf-8"
    )
    sub = tmp_path / "docs"
    sub.mkdir()
    cfg = Config.discover(sub)
    assert cfg.min_chunk_chars == 7


def test_config_discover_pyproject(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        "[tool.contextlint]\nmax_chunk_chars = 1234\n", encoding="utf-8"
    )
    cfg = Config.discover(tmp_path)
    assert cfg.max_chunk_chars == 1234


def test_config_discover_falls_back_to_defaults(tmp_path):
    cfg = Config.discover(tmp_path)
    assert cfg.chunk_size == Config().chunk_size


# --- CLI ---------------------------------------------------------------------


def test_cli_analyze_terminal(examples_dir, capsys):
    rc = main(["analyze", str(examples_dir / "clean_docs"), "--no-color"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "ContextLint" in out


def test_cli_analyze_json(examples_dir, capsys):
    rc = main(["analyze", str(examples_dir / "messy_docs"), "--format", "json"])
    out = capsys.readouterr().out
    assert rc == 0
    payload = json.loads(out)
    assert payload["tool"] == "contextlint"


def test_cli_fail_on_error(examples_dir, capsys):
    rc = main(
        ["analyze", str(examples_dir / "messy_docs"), "--format", "json", "--fail-on", "error"]
    )
    capsys.readouterr()
    assert rc == 1


def test_cli_fail_on_clean_passes(examples_dir, capsys):
    rc = main(["analyze", str(examples_dir / "clean_docs"), "--no-color", "--fail-on", "warning"])
    capsys.readouterr()
    assert rc == 0


def test_cli_missing_path(capsys):
    rc = main(["analyze", "does/not/exist"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "not found" in err


def test_cli_output_file(examples_dir, tmp_path, capsys):
    out_file = tmp_path / "report.md"
    rc = main(
        [
            "analyze",
            str(examples_dir / "messy_docs"),
            "--format",
            "markdown",
            "--output",
            str(out_file),
        ]
    )
    assert rc == 0
    assert out_file.exists()
    assert "# ContextLint Report" in out_file.read_text(encoding="utf-8")


def test_cli_threshold_override(examples_dir, capsys):
    # A tiny max-chunk-chars should make even clean docs report CTX001.
    rc = main(
        ["analyze", str(examples_dir / "clean_docs"), "--format", "json", "--max-chunk-chars", "10"]
    )
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert any(f["rule"] == "CTX001" for f in payload["findings"])


def test_cli_rules(capsys):
    rc = main(["rules"])
    out = capsys.readouterr().out
    assert rc == 0
    for rule_id in ("CTX001", "CTX002", "CTX003", "CTX004", "CTX005", "CTX006"):
        assert rule_id in out


def test_cli_no_command_prints_help(capsys):
    rc = main([])
    out = capsys.readouterr().out
    assert rc == 0
    assert "usage" in out.lower()


def test_cli_format_html(examples_dir, capsys):
    rc = main(["analyze", str(examples_dir / "messy_docs"), "--format", "html"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "<!doctype html>" in out.lower()


def test_cli_format_sarif(examples_dir, capsys):
    rc = main(["analyze", str(examples_dir / "messy_docs"), "--format", "sarif"])
    out = capsys.readouterr().out
    assert rc == 0
    assert json.loads(out)["version"] == "2.1.0"


def test_cli_format_badge(examples_dir, capsys):
    rc = main(["analyze", str(examples_dir / "clean_docs"), "--format", "badge"])
    out = capsys.readouterr().out
    assert rc == 0
    assert json.loads(out)["schemaVersion"] == 1


def test_cli_ignore_flag(examples_dir, capsys):
    rc = main(
        [
            "analyze",
            str(examples_dir / "messy_docs"),
            "--format",
            "json",
            "--ignore",
            "CTX003,CTX005",
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    ids = {f["rule"] for f in payload["findings"]}
    assert "CTX003" not in ids and "CTX005" not in ids


def test_cli_multiple_paths(examples_dir, capsys):
    rc = main(
        [
            "analyze",
            str(examples_dir / "clean_docs"),
            str(examples_dir / "messy_docs"),
            "--format",
            "json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["summary"]["files_analyzed"] >= 5


def test_cli_compare_terminal(examples_dir, capsys):
    rc = main(
        [
            "compare",
            str(examples_dir / "clean_docs"),
            str(examples_dir / "messy_docs"),
            "--no-color",
        ]
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "compare" in out.lower()
    assert "health score" in out.lower()


def test_cli_compare_json(examples_dir, capsys):
    rc = main(
        [
            "compare",
            str(examples_dir / "clean_docs"),
            str(examples_dir / "messy_docs"),
            "--format",
            "json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert "before" in payload and "after" in payload and "delta" in payload


def test_cli_risky_docs_flags_secrets(examples_dir, capsys):
    rc = main(["analyze", str(examples_dir / "risky_docs"), "--format", "json"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    ids = {f["rule"] for f in payload["findings"]}
    assert "CTX007" in ids  # secret detected
