"""Report renderers: terminal, JSON, and markdown."""

from contextlint.reports.json_report import render_json, report_to_dict
from contextlint.reports.markdown_report import render_markdown
from contextlint.reports.terminal import render_terminal

FORMATS = ("terminal", "json", "markdown")


def render(report, fmt: str = "terminal", *, color: bool = True) -> str:
    if fmt == "terminal":
        return render_terminal(report, color=color)
    if fmt == "json":
        return render_json(report)
    if fmt == "markdown":
        return render_markdown(report)
    raise ValueError(f"Unknown report format: {fmt!r}. Choose from {FORMATS}.")


__all__ = [
    "FORMATS",
    "render",
    "render_json",
    "render_markdown",
    "render_terminal",
    "report_to_dict",
]
