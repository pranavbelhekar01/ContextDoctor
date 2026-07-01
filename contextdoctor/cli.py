"""Command-line interface for ContextDoctor.

Usage:
    contextdoctor analyze <path...> [options]
    contextdoctor compare <a> <b> [options]
    contextdoctor rules
    contextdoctor --version
"""

from __future__ import annotations

import argparse
import contextlib
import sys
from pathlib import Path

from contextdoctor import __version__
from contextdoctor.baseline import load_baseline, save_baseline
from contextdoctor.config import Config
from contextdoctor.engine import analyze_paths
from contextdoctor.models import Report, Severity
from contextdoctor.reports import FORMATS, render
from contextdoctor.reports.badge import badge_markdown
from contextdoctor.reports.json_report import report_to_dict
from contextdoctor.rules import BUILTIN_RULE_IDS, RULES
from contextdoctor.utils.ansi import Style, supports_color

_EPILOG = """\
examples:
  contextdoctor analyze ./docs
  contextdoctor analyze ./docs --format html --output report.html
  contextdoctor analyze export.json --format sarif -o results.sarif --fail-on error
  contextdoctor analyze ./docs --ignore CTX006 --select CTX001,CTX003
  contextdoctor compare recursive.json semantic.json
  contextdoctor rules

ContextDoctor runs fully offline: no API keys, no cloud, no LLM calls.
"""


def _csv(value: str) -> tuple[str, ...]:
    return tuple(part.strip().upper() for part in value.split(",") if part.strip())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="contextdoctor",
        description="A static analyzer for RAG systems and context engineering workflows.",
        epilog=_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"contextdoctor {__version__}")
    sub = parser.add_subparsers(dest="command")

    analyze = sub.add_parser(
        "analyze",
        help="Analyze one or more files/directories of documents or chunks.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    analyze.add_argument("paths", nargs="+", help="Files or directories to analyze.")
    analyze.add_argument(
        "-f",
        "--format",
        choices=FORMATS,
        default="terminal",
        help="Output format (default: terminal).",
    )
    analyze.add_argument("-o", "--output", help="Write the report to this file instead of stdout.")
    analyze.add_argument(
        "-c",
        "--config",
        help="Config file (.json or pyproject.toml). Auto-discovered if omitted.",
    )
    analyze.add_argument(
        "--fail-on",
        choices=[s.value for s in Severity],
        help="Exit 1 if any finding is at or above this severity (for CI).",
    )
    analyze.add_argument("--select", type=_csv, help="Only run these rule ids (comma-separated).")
    analyze.add_argument("--ignore", type=_csv, help="Skip these rule ids (comma-separated).")
    analyze.add_argument(
        "--plugin",
        action="append",
        default=[],
        metavar="SPEC",
        help="Load a plugin analyzer (module spec or .py path). Repeatable.",
    )
    analyze.add_argument(
        "--baseline",
        metavar="FILE",
        help="Suppress findings recorded in this baseline; report only new ones.",
    )
    analyze.add_argument("--no-color", action="store_true", help="Disable ANSI colour output.")
    analyze.add_argument(
        "--quiet", action="store_true", help="Suppress stdout when using --output."
    )

    analyze.add_argument("--chunk-size", type=int, help="Target chunk size in characters.")
    analyze.add_argument("--chunk-overlap", type=int, help="Chunk overlap in characters.")
    analyze.add_argument("--max-chunk-chars", type=int, help="CTX001 threshold (max chunk chars).")
    analyze.add_argument("--min-chunk-chars", type=int, help="CTX002 threshold (min chunk chars).")
    analyze.add_argument(
        "--embedding-token-limit", type=int, help="CTX010 threshold (embedding token limit)."
    )
    analyze.add_argument("--cfi-threshold", type=float, help="CTX006 CFI warning threshold (0..1).")

    compare = sub.add_parser(
        "compare",
        help="Compare two corpora / chunking strategies side by side.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    compare.add_argument("before", help="Baseline file or directory.")
    compare.add_argument("after", help="Candidate file or directory.")
    compare.add_argument(
        "-c", "--config", help="Config file applied to BOTH sides for a fair comparison."
    )
    compare.add_argument(
        "-f", "--format", choices=["terminal", "json"], default="terminal", help="Output format."
    )
    compare.add_argument("--no-color", action="store_true", help="Disable ANSI colour output.")

    baseline = sub.add_parser(
        "baseline",
        help="Record current findings to a baseline file so CI only fails on new ones.",
    )
    baseline.add_argument("paths", nargs="+", help="Files or directories to baseline.")
    baseline.add_argument(
        "-o", "--output", default=".contextdoctor-baseline.json", help="Baseline file to write."
    )
    baseline.add_argument("-c", "--config", help="Config file (.json or pyproject.toml).")

    rules = sub.add_parser("rules", help="List all rules (CTX001–CTX010 plus any plugins).")
    rules.add_argument(
        "--plugin",
        action="append",
        default=[],
        metavar="SPEC",
        help="Also list rules from this plugin (module spec or .py path). Repeatable.",
    )
    return parser


def _build_config(args: argparse.Namespace, discover_from: str) -> Config:
    config = Config.load(args.config) if args.config else Config.discover(discover_from)

    overrides = {
        "chunk_size": getattr(args, "chunk_size", None),
        "chunk_overlap": getattr(args, "chunk_overlap", None),
        "max_chunk_chars": getattr(args, "max_chunk_chars", None),
        "min_chunk_chars": getattr(args, "min_chunk_chars", None),
        "embedding_token_limit": getattr(args, "embedding_token_limit", None),
        "cfi_warning_threshold": getattr(args, "cfi_threshold", None),
    }
    for key, value in overrides.items():
        if value is not None:
            setattr(config, key, value)
    if getattr(args, "select", None):
        config.select = args.select
    if getattr(args, "ignore", None):
        config.ignore = args.ignore
    if getattr(args, "plugin", None):
        config.plugins = tuple(config.plugins) + tuple(args.plugin)
    return config


def _cmd_analyze(args: argparse.Namespace) -> int:
    missing = [p for p in args.paths if not Path(p).exists()]
    if missing:
        print(f"contextdoctor: error: path not found: {', '.join(missing)}", file=sys.stderr)
        return 2

    config = _build_config(args, discover_from=args.paths[0])

    baseline_set = None
    if args.baseline:
        if Path(args.baseline).exists():
            baseline_set = load_baseline(args.baseline)
        elif not args.quiet:
            print(
                f"contextdoctor: baseline '{args.baseline}' not found; reporting all findings.",
                file=sys.stderr,
            )

    report = analyze_paths(args.paths, config, baseline=baseline_set)

    use_color = args.format == "terminal" and not args.no_color and not args.output
    rendered = render(report, args.format, color=use_color)

    if args.output:
        text = rendered if rendered.endswith("\n") else rendered + "\n"
        Path(args.output).write_text(text, encoding="utf-8")
        if not args.quiet:
            print(f"contextdoctor: report written to {args.output}")
    else:
        print(rendered)

    if report.baseline_suppressed and not args.quiet:
        print(
            f"contextdoctor: {report.baseline_suppressed} finding(s) suppressed by baseline.",
            file=sys.stderr,
        )

    if args.format == "badge" and not args.quiet:
        print("\nPaste into your README:\n" + badge_markdown(report), file=sys.stderr)

    if args.fail_on and report.has_at_least(Severity.from_str(args.fail_on)):
        return 1
    return 0


def _cmd_baseline(args: argparse.Namespace) -> int:
    missing = [p for p in args.paths if not Path(p).exists()]
    if missing:
        print(f"contextdoctor: error: path not found: {', '.join(missing)}", file=sys.stderr)
        return 2
    config = Config.load(args.config) if args.config else Config.discover(args.paths[0])
    report = analyze_paths(args.paths, config)
    count = save_baseline(report, args.output)
    print(f"contextdoctor: wrote baseline with {count} finding(s) to {args.output}")
    return 0


def _cmd_compare(args: argparse.Namespace) -> int:
    for label, p in (("before", args.before), ("after", args.after)):
        if not Path(p).exists():
            print(f"contextdoctor: error: {label} path not found: {p}", file=sys.stderr)
            return 2

    config = Config.load(args.config) if args.config else Config()
    before = analyze_paths([args.before], config)
    after = analyze_paths([args.after], config)

    if args.format == "json":
        import json

        print(
            json.dumps(
                {
                    "before": report_to_dict(before),
                    "after": report_to_dict(after),
                    "delta": _compare_delta(before, after),
                },
                indent=2,
            )
        )
    else:
        print(_render_compare(before, after, color=not args.no_color))
    return 0


def _compare_delta(before: Report, after: Report) -> dict:
    def dup(r: Report) -> float:
        return r.metrics.get("duplicates", {}).get("duplicate_pct", 0.0)

    def cfi(r: Report) -> float:
        return r.metrics.get("fragmentation", {}).get("cfi", 0.0)

    return {
        "health_score": after.health_score - before.health_score,
        "findings": len(after.findings) - len(before.findings),
        "duplicate_pct": round(dup(after) - dup(before), 2),
        "cfi": round(cfi(after) - cfi(before), 3),
    }


def _render_compare(before: Report, after: Report, *, color: bool) -> str:
    s = Style(color and supports_color())
    delta = _compare_delta(before, after)

    def arrow(v: float, good_when_negative: bool = False) -> str:
        if v == 0:
            return s.gray("→ 0")
        better = (v > 0) ^ good_when_negative
        sign = "+" if v > 0 else ""
        text = f"{sign}{v}"
        return s.green(text) if better else s.red(text)

    lines = [
        "",
        "  " + s.bold("ContextDoctor compare"),
        s.gray(f"    before: {before.root}    after: {after.root}"),
        "",
        f"    {'metric':<18}{'before':>12}{'after':>12}{'Δ':>12}",
        s.gray("    " + "─" * 54),
        f"    {'health score':<18}{before.health_score:>12}{after.health_score:>12}"
        f"{'':>4}{arrow(delta['health_score']):>8}",
        f"    {'findings':<18}{len(before.findings):>12}{len(after.findings):>12}"
        f"{'':>4}{arrow(delta['findings'], good_when_negative=True):>8}",
        f"    {'duplicate %':<18}"
        f"{before.metrics.get('duplicates', {}).get('duplicate_pct', 0):>12}"
        f"{after.metrics.get('duplicates', {}).get('duplicate_pct', 0):>12}"
        f"{'':>4}{arrow(delta['duplicate_pct'], good_when_negative=True):>8}",
        f"    {'CFI':<18}"
        f"{before.metrics.get('fragmentation', {}).get('cfi', 0.0):>12}"
        f"{after.metrics.get('fragmentation', {}).get('cfi', 0.0):>12}"
        f"{'':>4}{arrow(delta['cfi'], good_when_negative=True):>8}",
        "",
    ]
    verdict = (
        s.green("  ✔ 'after' is healthier.")
        if after.health_score > before.health_score
        else s.red("  ✖ 'after' regressed.")
        if after.health_score < before.health_score
        else s.gray("  = no change in health score.")
    )
    lines.append(verdict)
    lines.append("")
    return "\n".join(lines)


def _cmd_rules(args: argparse.Namespace) -> int:
    # Surface plugin rules too: entry points always, plus any explicit --plugin.
    from contextdoctor.plugins import discover_entry_point_analyzers, load_module_analyzers

    discover_entry_point_analyzers()
    if getattr(args, "plugin", None):
        load_module_analyzers(list(args.plugin))

    print("ContextDoctor rules\n")
    for rule in RULES.values():
        builtin = rule.id in BUILTIN_RULE_IDS
        tags = []
        if rule.experimental:
            tags.append("experimental")
        if not builtin:
            tags.append("plugin")
        suffix = f" ({', '.join(tags)})" if tags else ""
        print(f"  {rule.id}  [{rule.default_severity.value}]  {rule.name}{suffix}")
        print(f"           {rule.description}")
    print("\nSee the README for detailed recommendations and configuration.")
    return 0


def _use_utf8_stdout() -> None:
    """Prefer UTF-8 on consoles that default to a legacy codepage (e.g. Windows)."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        with contextlib.suppress(Exception):  # pragma: no cover - stream may not reconfigure
            reconfigure(encoding="utf-8", errors="replace")


def main(argv: list[str] | None = None) -> int:
    _use_utf8_stdout()
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "analyze":
        return _cmd_analyze(args)
    if args.command == "compare":
        return _cmd_compare(args)
    if args.command == "baseline":
        return _cmd_baseline(args)
    if args.command == "rules":
        return _cmd_rules(args)

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
