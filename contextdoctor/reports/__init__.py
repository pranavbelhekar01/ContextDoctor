"""Report renderers: terminal, JSON, markdown, HTML, SARIF, and badge."""

from contextdoctor.reports.badge import badge_markdown, render_badge
from contextdoctor.reports.html_report import render_html
from contextdoctor.reports.json_report import render_json, report_to_dict
from contextdoctor.reports.markdown_report import render_markdown
from contextdoctor.reports.sarif_report import render_sarif
from contextdoctor.reports.terminal import render_terminal

FORMATS = ("terminal", "json", "markdown", "html", "sarif", "badge")


def render(report, fmt: str = "terminal", *, color: bool = True) -> str:
    if fmt == "terminal":
        return render_terminal(report, color=color)
    if fmt == "json":
        return render_json(report)
    if fmt == "markdown":
        return render_markdown(report)
    if fmt == "html":
        return render_html(report)
    if fmt == "sarif":
        return render_sarif(report)
    if fmt == "badge":
        return render_badge(report)
    raise ValueError(f"Unknown report format: {fmt!r}. Choose from {FORMATS}.")


__all__ = [
    "FORMATS",
    "badge_markdown",
    "render",
    "render_badge",
    "render_html",
    "render_json",
    "render_markdown",
    "render_sarif",
    "render_terminal",
    "report_to_dict",
]
