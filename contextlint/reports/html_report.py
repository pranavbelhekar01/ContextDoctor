"""Self-contained HTML report with inline CSS + SVG (no external assets, no JS).

This is the shareable artifact: open it in a browser, screenshot the score card,
post it. Everything is embedded so a single ``report.html`` works offline.
"""

from __future__ import annotations

import html
import math

from contextlint.models import Report, Severity
from contextlint.rules import get_rule

_SEV_COLOR = {
    Severity.ERROR: "#e5484d",
    Severity.WARNING: "#f5a623",
    Severity.INFO: "#3b82f6",
}


def _score_color(score: int) -> str:
    if score >= 80:
        return "#30a46c"
    if score >= 60:
        return "#f5a623"
    return "#e5484d"


def _esc(text: object) -> str:
    return html.escape(str(text))


def _score_ring(score: int) -> str:
    r = 66
    circ = 2 * math.pi * r
    offset = circ * (1 - max(0, min(100, score)) / 100)
    color = _score_color(score)
    return f"""
    <svg viewBox="0 0 160 160" width="160" height="160" role="img" aria-label="score">
      <circle cx="80" cy="80" r="{r}" fill="none" stroke="var(--track)" stroke-width="14"/>
      <circle cx="80" cy="80" r="{r}" fill="none" stroke="{color}" stroke-width="14"
        stroke-linecap="round" stroke-dasharray="{circ:.1f}" stroke-dashoffset="{offset:.1f}"
        transform="rotate(-90 80 80)"/>
      <text x="80" y="76" text-anchor="middle" font-size="38" font-weight="700"
        fill="var(--fg)">{score}</text>
      <text x="80" y="100" text-anchor="middle" font-size="14" fill="var(--muted)">/ 100</text>
    </svg>
    """


def _histogram_svg(hist: dict) -> str:
    counts = hist.get("counts", [])
    edges = hist.get("edges", [])
    if not counts:
        return "<p class='muted'>No chunk-size data.</p>"
    peak = max(counts) or 1
    n = len(counts)
    width, height = 520, 160
    gap = 4
    bar_w = (width - gap * (n - 1)) / n
    bars = []
    for i, c in enumerate(counts):
        h = (c / peak) * (height - 24)
        x = i * (bar_w + gap)
        y = height - h
        bars.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" '
            f'rx="3" fill="var(--accent)"><title>{c} chunks</title></rect>'
        )
    lo = edges[0] if edges else 0
    hi = edges[-1] if edges else 0
    return f"""
    <svg viewBox="0 0 {width} {height + 22}" width="100%" height="auto" class="hist">
      {"".join(bars)}
      <text x="0" y="{height + 16}" font-size="12" fill="var(--muted)">{lo} chars</text>
      <text x="{width}" y="{height + 16}" font-size="12" fill="var(--muted)"
        text-anchor="end">{hi} chars</text>
    </svg>
    """


def _kpi(label: str, value: str) -> str:
    return f'<div class="kpi"><div class="kpi-v">{_esc(value)}</div><div class="kpi-l">{_esc(label)}</div></div>'


def _severity_bar(report: Report) -> str:
    counts = report.counts_by_severity()
    total = sum(counts.values()) or 1
    segs = []
    for sev in (Severity.ERROR, Severity.WARNING, Severity.INFO):
        c = counts[sev.value]
        if not c:
            continue
        pct = 100 * c / total
        segs.append(
            f'<span class="seg" style="width:{pct:.1f}%;background:{_SEV_COLOR[sev]}" '
            f'title="{c} {sev.value}"></span>'
        )
    chips = "  ".join(
        f'<span class="chip"><span class="dot" style="background:{_SEV_COLOR[s]}"></span>'
        f"{counts[s.value]} {s.value}</span>"
        for s in (Severity.ERROR, Severity.WARNING, Severity.INFO)
    )
    return f'<div class="bar">{"".join(segs)}</div><div class="chips">{chips}</div>'


def _cfi_section(report: Report) -> str:
    frag = report.metrics.get("fragmentation", {})
    if not frag:
        return ""
    cfi = frag.get("cfi", 0.0)
    color = "#30a46c" if cfi < 0.35 else ("#f5a623" if cfi < 0.6 else "#e5484d")
    rows = "".join(
        f"<tr><td>{_esc(t['entity'])}</td><td>{t['fragmentation']:.3f}</td>"
        f"<td>{t['chunks']}</td></tr>"
        for t in frag.get("top_fragmented", [])
    )
    table = (
        f"<table><thead><tr><th>Entity</th><th>Fragmentation</th><th>Chunks</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
        if rows
        else "<p class='muted'>No repeated entities tracked.</p>"
    )
    return f"""
    <section class="card">
      <h2>Context Fragmentation Index <span class="tag">experimental</span></h2>
      <div class="cfi"><span class="cfi-num" style="color:{color}">{cfi:.3f}</span>
        <div class="track"><div class="fill" style="width:{cfi * 100:.0f}%;background:{color}"></div></div>
        <span class="muted">0 = coherent · 1 = fragmented</span></div>
      {table}
    </section>
    """


def _findings_section(report: Report) -> str:
    if not report.findings:
        return (
            '<section class="card"><h2>Findings</h2>'
            '<p class="ok">✔ No issues found — your context looks clean.</p></section>'
        )
    items = []
    for f in report.findings:
        rule = get_rule(f.rule_id)
        color = _SEV_COLOR[f.severity]
        exp = '<span class="tag">experimental</span>' if f.experimental else ""
        locs = "".join(f"<li><code>{_esc(loc.render())}</code></li>" for loc in f.locations[:8])
        more = len(f.locations) - 8
        if more > 0:
            locs += f"<li class='muted'>…and {more} more</li>"
        loc_block = f"<ul class='locs'>{locs}</ul>" if locs else ""
        items.append(
            f"""
      <div class="finding" style="border-left-color:{color}">
        <div class="f-head">
          <span class="badge" style="background:{color}">{_esc(f.severity.value)}</span>
          <strong>{_esc(f.rule_id)}</strong> <span class="muted">{_esc(rule.name)}</span> {exp}
        </div>
        <p class="f-msg">{_esc(f.message)}</p>
        <p class="f-rec"><strong>Recommendation:</strong> {_esc(f.recommendation)}</p>
        {loc_block}
      </div>"""
        )
    return f'<section class="card"><h2>Findings</h2>{"".join(items)}</section>'


def render_html(report: Report) -> str:
    stats = report.metrics.get("chunk_stats", {})
    dup = report.metrics.get("duplicates", {})
    frag = report.metrics.get("fragmentation", {})
    char = stats.get("char", {})
    token = stats.get("token", {})

    kpis = "".join(
        [
            _kpi("Files", report.files_analyzed),
            _kpi("Chunks", report.total_chunks),
            _kpi("Median chars", char.get("median", 0)),
            _kpi("Median tokens", token.get("median", 0)),
            _kpi("Duplicated", f"{dup.get('duplicate_pct', 0)}%"),
            _kpi("Overlap", f"{stats.get('overlap_pct', 0)}%"),
            _kpi("CFI", f"{frag.get('cfi', 0.0):.3f}"),
        ]
    )
    grade_color = _score_color(report.health_score)

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ContextLint Report — {_esc(report.root)}</title>
<style>
  :root {{
    --bg:#f6f7f9; --card:#ffffff; --fg:#1a1d24; --muted:#6b7280; --track:#e5e7eb;
    --accent:#6366f1; --border:#e5e7eb;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{ --bg:#0f1115; --card:#171a21; --fg:#e8eaed; --muted:#9aa0aa;
      --track:#2a2f3a; --accent:#818cf8; --border:#252a34; }}
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--fg);
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif; }}
  .wrap {{ max-width:880px; margin:0 auto; padding:32px 20px 64px; }}
  header {{ display:flex; justify-content:space-between; align-items:baseline; margin-bottom:20px; }}
  header h1 {{ font-size:22px; margin:0; }} header .sub {{ color:var(--muted); font-size:13px; }}
  .card {{ background:var(--card); border:1px solid var(--border); border-radius:14px;
    padding:22px; margin-bottom:18px; }}
  .hero {{ display:flex; gap:24px; align-items:center; }}
  .hero .grade {{ font-size:44px; font-weight:800; color:{grade_color}; line-height:1; }}
  .hero .label {{ color:var(--muted); text-transform:capitalize; }}
  .kpis {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(96px,1fr)); gap:12px; margin-top:18px; }}
  .kpi {{ background:var(--bg); border:1px solid var(--border); border-radius:10px; padding:12px; text-align:center; }}
  .kpi-v {{ font-size:20px; font-weight:700; }} .kpi-l {{ font-size:11px; color:var(--muted); margin-top:2px; }}
  h2 {{ font-size:16px; margin:0 0 14px; }}
  .tag {{ font-size:10px; text-transform:uppercase; letter-spacing:.05em; color:var(--muted);
    border:1px solid var(--border); border-radius:6px; padding:2px 6px; vertical-align:middle; }}
  .bar {{ display:flex; height:12px; border-radius:6px; overflow:hidden; background:var(--track); }}
  .bar .seg {{ height:100%; }}
  .chips {{ margin-top:10px; display:flex; gap:16px; font-size:13px; color:var(--muted); }}
  .chip .dot {{ display:inline-block; width:9px; height:9px; border-radius:50%; margin-right:6px; }}
  .cfi {{ display:flex; align-items:center; gap:14px; margin-bottom:14px; flex-wrap:wrap; }}
  .cfi-num {{ font-size:30px; font-weight:800; }}
  .track {{ flex:1; min-width:140px; height:10px; background:var(--track); border-radius:6px; overflow:hidden; }}
  .fill {{ height:100%; }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; }}
  th,td {{ text-align:left; padding:7px 10px; border-bottom:1px solid var(--border); }}
  th {{ color:var(--muted); font-weight:600; }}
  .finding {{ border-left:4px solid; padding:12px 14px; margin:12px 0; background:var(--bg); border-radius:0 10px 10px 0; }}
  .f-head {{ display:flex; align-items:center; gap:8px; margin-bottom:6px; }}
  .badge {{ color:#fff; font-size:11px; text-transform:uppercase; border-radius:6px; padding:2px 7px; font-weight:700; }}
  .f-msg {{ margin:4px 0; }} .f-rec {{ margin:4px 0; color:var(--muted); font-size:14px; }}
  .locs {{ margin:8px 0 0; padding-left:18px; font-size:12px; color:var(--muted); }}
  code {{ background:var(--track); padding:1px 5px; border-radius:5px; font-size:12px; }}
  .muted {{ color:var(--muted); }} .ok {{ color:#30a46c; font-weight:600; }}
  .hist {{ margin-top:6px; }}
  footer {{ color:var(--muted); font-size:12px; text-align:center; margin-top:24px; }}
</style></head>
<body><div class="wrap">
  <header>
    <h1>🔎 ContextLint</h1>
    <div class="sub">{_esc(report.root)} · {_esc(report.generated_at)}</div>
  </header>

  <section class="card hero">
    {_score_ring(report.health_score)}
    <div>
      <div class="grade">{_esc(report.health_grade)}</div>
      <div class="label">Context Health — {_esc(report.health_label)}</div>
      <div class="kpis">{kpis}</div>
    </div>
  </section>

  <section class="card">
    <h2>Issues</h2>
    {_severity_bar(report)}
  </section>

  <section class="card">
    <h2>Chunk-size distribution</h2>
    {_histogram_svg(stats.get("histogram", {}))}
  </section>

  {_cfi_section(report)}
  {_findings_section(report)}

  <footer>Generated by ContextLint — fully offline static analysis for RAG. No LLM was called.</footer>
</div></body></html>
"""
