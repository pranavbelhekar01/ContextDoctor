"""Human-friendly terminal report with optional ANSI colour (zero dependencies)."""

import sys

from contextlint.models import Report, Severity
from contextlint.rules import get_rule
from contextlint.utils.ansi import Style, supports_color
from contextlint.utils.text import truncate


def _unicode_capable() -> bool:
    enc = (getattr(sys.stdout, "encoding", None) or "").lower()
    return "utf" in enc


# Glyph sets: fancy Unicode where the console supports it, ASCII otherwise.
_UNICODE = {
    "bar": "─",
    "error": "✖",
    "warning": "▲",
    "info": "ℹ",
    "check": "✔",
    "bullet": "•",
    "arrow": "→",
    "fill": "█",
    "empty": "░",
}
_ASCII = {
    "bar": "-",
    "error": "x",
    "warning": "!",
    "info": "i",
    "check": "OK",
    "bullet": "*",
    "arrow": "->",
    "fill": "#",
    "empty": ".",
}


def render_terminal(report: Report, *, color: bool | None = None) -> str:
    enabled = supports_color() if color is None else color
    s = Style(enabled)
    g = _UNICODE if _unicode_capable() else _ASCII
    out: list[str] = []

    _header(report, s, out, g)
    _summary(report, s, out, g)
    _chunk_stats(report, s, out, g)
    _cfi(report, s, out, g)
    _findings(report, s, out, g)
    _footer(report, s, out, g)

    return "\n".join(out)


def _bar(g: dict) -> str:
    return g["bar"] * 68


def _header(report: Report, s: Style, out: list[str], g: dict) -> None:
    out.append("")
    out.append(s.bold_color("  ContextLint", "cyan") + s.dim("  ·  static analysis for RAG"))
    out.append(s.gray(f"  {_bar(g)}"))
    out.append(s.gray(f"  root: {report.root}"))
    out.append(
        s.gray(
            f"  files: {report.files_analyzed}   chunks: {report.total_chunks}"
            f"   generated: {report.generated_at}"
        )
    )
    out.append("")


def _score_color(score: int, s: Style, text: str) -> str:
    if score >= 80:
        return s.green(text)
    if score >= 60:
        return s.yellow(text)
    return s.red(text)


def _summary(report: Report, s: Style, out: list[str], g: dict) -> None:
    score = report.health_score
    gauge = _gauge(score / 100.0, s, g, width=24)
    big = _score_color(score, s, s.bold(f"{score}/100  {report.health_grade}"))
    out.append("  " + s.bold("Context Health Score"))
    out.append(f"    {big}  {gauge}  " + s.gray(report.health_label))
    out.append("")

    counts = report.counts_by_severity()
    parts = [
        s.red(f"{counts['error']} error"),
        s.yellow(f"{counts['warning']} warning"),
        s.cyan(f"{counts['info']} info"),
    ]
    out.append("  " + s.bold("Issues  ") + "  ".join(parts))
    out.append("")


def _fmt(n) -> str:
    if isinstance(n, float):
        return f"{n:g}"
    return str(n)


def _chunk_stats(report: Report, s: Style, out: list[str], g: dict) -> None:
    stats = report.metrics.get("chunk_stats", {})
    if not stats or not stats.get("count"):
        return
    char = stats.get("char", {})
    token = stats.get("token", {})
    dup = report.metrics.get("duplicates", {})

    out.append("  " + s.bold("Chunk statistics"))
    header = f"    {'':10}{'chars':>10}{'tokens':>10}"
    out.append(s.gray(header))
    for label, key in [
        ("min", "min"),
        ("median", "median"),
        ("mean", "mean"),
        ("p95", "p95"),
        ("max", "max"),
    ]:
        out.append(f"    {label:<10}{_fmt(char.get(key, 0)):>10}{_fmt(token.get(key, 0)):>10}")
    out.append(
        s.gray(
            f"    overlap {_fmt(stats.get('overlap_pct', 0))}%"
            f"   ·   duplicated {_fmt(dup.get('duplicate_pct', 0))}%"
        )
    )
    out.append("")


def _cfi_color(cfi: float, s: Style) -> str:
    text = f"{cfi:.3f}"
    if cfi >= 0.6:
        return s.red(text)
    if cfi >= 0.35:
        return s.yellow(text)
    return s.green(text)


def _cfi(report: Report, s: Style, out: list[str], g: dict) -> None:
    frag = report.metrics.get("fragmentation", {})
    if not frag:
        return
    cfi = frag.get("cfi", 0.0)
    out.append("  " + s.bold("Context Fragmentation Index") + s.dim(" (experimental)"))
    bar = _gauge(cfi, s, g)
    out.append(f"    CFI {_cfi_color(cfi, s)}  {bar}  " + s.gray("0=coherent  1=fragmented"))
    top = frag.get("top_fragmented", [])
    if top:
        preview = ", ".join(f"{t['entity']} ({t['fragmentation']:.2f})" for t in top[:4])
        out.append(s.gray(f"    most scattered: {truncate(preview, 60)}"))
    out.append("")


def _gauge(value: float, s: Style, g: dict, width: int = 20) -> str:
    value = max(0.0, min(1.0, value))
    filled = round(value * width)
    bar = g["fill"] * filled + g["empty"] * (width - filled)
    if value >= 0.6:
        return s.red(bar)
    if value >= 0.35:
        return s.yellow(bar)
    return s.green(bar)


def _findings(report: Report, s: Style, out: list[str], g: dict) -> None:
    glyph_by_sev = {
        Severity.ERROR: (g["error"], "red"),
        Severity.WARNING: (g["warning"], "yellow"),
        Severity.INFO: (g["info"], "cyan"),
    }
    out.append("  " + s.bold("Findings"))
    if not report.findings:
        out.append("    " + s.green(f"{g['check']} No issues found — your context looks clean."))
        out.append("")
        return
    out.append("")
    for finding in report.findings:
        rule = get_rule(finding.rule_id)
        glyph, colorname = glyph_by_sev[finding.severity]
        head = s.bold_color(f"{glyph} {finding.rule_id}", colorname)
        tag = s.dim(f"[{rule.name}]")
        exp = s.dim(" (experimental)") if finding.experimental else ""
        out.append(f"    {head} {tag}{exp}")
        out.append(f"      {finding.message}")
        out.append(s.gray(f"      {g['arrow']} {finding.recommendation}"))
        for loc in finding.locations[:6]:
            out.append(s.dim(f"        {g['bullet']} {loc.render()}"))
        extra = len(finding.locations) - 6
        if extra > 0:
            out.append(s.dim(f"        {g['bullet']} …and {extra} more"))
        out.append("")


def _footer(report: Report, s: Style, out: list[str], g: dict) -> None:
    out.append(s.gray(f"  {_bar(g)}"))
    if report.findings:
        out.append(
            s.gray("  Fully offline analysis — no LLM was called. ")
            + s.dim("Run with --format markdown for a shareable report.")
        )
    else:
        out.append(s.gray("  Fully offline analysis — no LLM was called."))
    out.append("")
