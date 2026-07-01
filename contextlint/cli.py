"""Command-line interface for ContextLint.

Usage:
    contextlint analyze <path> [options]
    contextlint rules
    contextlint --version
"""

from __future__ import annotations

import argparse
import contextlib
import sys
from pathlib import Path

from contextlint import __version__
from contextlint.config import Config
from contextlint.engine import analyze_path
from contextlint.models import Severity
from contextlint.reports import FORMATS, render
from contextlint.rules import RULES

_EPILOG = """\
examples:
  contextlint analyze ./docs
  contextlint analyze ./docs --format markdown --output report.md
  contextlint analyze export.json --format json --fail-on warning
  contextlint rules

ContextLint runs fully offline: no API keys, no cloud, no LLM calls.
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="contextlint",
        description="A static analyzer for RAG systems and context engineering workflows.",
        epilog=_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"contextlint {__version__}")
    sub = parser.add_subparsers(dest="command")

    analyze = sub.add_parser(
        "analyze",
        help="Analyze a file or directory of documents / chunks.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    analyze.add_argument("path", help="File or directory to analyze.")
    analyze.add_argument(
        "-f",
        "--format",
        choices=FORMATS,
        default="terminal",
        help="Output format (default: terminal).",
    )
    analyze.add_argument(
        "-o",
        "--output",
        help="Write the report to this file instead of stdout.",
    )
    analyze.add_argument(
        "-c",
        "--config",
        help="Path to a config file (.json or pyproject.toml). "
        "If omitted, ContextLint auto-discovers one near the target.",
    )
    analyze.add_argument(
        "--fail-on",
        choices=[s.value for s in Severity],
        help="Exit with code 1 if any finding is at or above this severity (for CI).",
    )
    analyze.add_argument("--no-color", action="store_true", help="Disable ANSI colour output.")
    analyze.add_argument(
        "--quiet", action="store_true", help="Suppress stdout when using --output."
    )

    # Common threshold overrides.
    analyze.add_argument("--chunk-size", type=int, help="Target chunk size in characters.")
    analyze.add_argument("--chunk-overlap", type=int, help="Chunk overlap in characters.")
    analyze.add_argument("--max-chunk-chars", type=int, help="CTX001 threshold (max chunk chars).")
    analyze.add_argument("--min-chunk-chars", type=int, help="CTX002 threshold (min chunk chars).")
    analyze.add_argument(
        "--cfi-threshold", type=float, help="CTX006 warning threshold for the CFI (0..1)."
    )

    sub.add_parser("rules", help="List all ContextLint rules (CTX001–CTX006).")
    return parser


def _build_config(args: argparse.Namespace) -> Config:
    config = Config.load(args.config) if args.config else Config.discover(args.path)

    overrides = {
        "chunk_size": args.chunk_size,
        "chunk_overlap": args.chunk_overlap,
        "max_chunk_chars": args.max_chunk_chars,
        "min_chunk_chars": args.min_chunk_chars,
        "cfi_warning_threshold": args.cfi_threshold,
    }
    for key, value in overrides.items():
        if value is not None:
            setattr(config, key, value)
    return config


def _cmd_analyze(args: argparse.Namespace) -> int:
    target = Path(args.path)
    if not target.exists():
        print(f"contextlint: error: path not found: {args.path}", file=sys.stderr)
        return 2

    config = _build_config(args)
    report = analyze_path(target, config)

    # Colour only ever applies to the terminal format; never colourise a file.
    use_color = args.format == "terminal" and not args.no_color and not args.output
    rendered = render(report, args.format, color=use_color)

    if args.output:
        text = rendered if rendered.endswith("\n") else rendered + "\n"
        Path(args.output).write_text(text, encoding="utf-8")
        if not args.quiet:
            print(f"contextlint: report written to {args.output}")
    else:
        print(rendered)

    if args.fail_on:
        threshold = Severity.from_str(args.fail_on)
        if report.has_at_least(threshold):
            return 1
    return 0


def _cmd_rules() -> int:
    print("ContextLint rules\n")
    for rule in RULES.values():
        flag = " (experimental)" if rule.experimental else ""
        print(f"  {rule.id}  [{rule.default_severity.value}]  {rule.name}{flag}")
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
    if args.command == "rules":
        return _cmd_rules()

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
