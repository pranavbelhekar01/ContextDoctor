"""Tiny ANSI colour helper so the terminal report needs zero dependencies."""

from __future__ import annotations

import os
import sys

_CODES = {
    "reset": "0",
    "bold": "1",
    "dim": "2",
    "red": "31",
    "green": "32",
    "yellow": "33",
    "blue": "34",
    "magenta": "35",
    "cyan": "36",
    "white": "37",
    "gray": "90",
    "bright_red": "91",
    "bright_green": "92",
    "bright_yellow": "93",
    "bright_cyan": "96",
}


def supports_color(stream=sys.stdout) -> bool:
    """Best-effort detection of colour support, honouring NO_COLOR."""
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    if not hasattr(stream, "isatty") or not stream.isatty():
        return False
    if sys.platform == "win32":
        # Modern Windows Terminal / VS Code set this; older consoles may not.
        return "WT_SESSION" in os.environ or "ANSICON" in os.environ or bool(os.environ.get("TERM"))
    return True


class Style:
    """Callable colouriser that can be globally disabled."""

    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled

    def _wrap(self, text: str, *names: str) -> str:
        if not self.enabled or not names:
            return text
        prefix = "".join(f"\033[{_CODES[n]}m" for n in names if n in _CODES)
        return f"{prefix}{text}\033[0m"

    def bold(self, text: str) -> str:
        return self._wrap(text, "bold")

    def dim(self, text: str) -> str:
        return self._wrap(text, "dim")

    def red(self, text: str) -> str:
        return self._wrap(text, "bright_red")

    def green(self, text: str) -> str:
        return self._wrap(text, "bright_green")

    def yellow(self, text: str) -> str:
        return self._wrap(text, "bright_yellow")

    def cyan(self, text: str) -> str:
        return self._wrap(text, "bright_cyan")

    def gray(self, text: str) -> str:
        return self._wrap(text, "gray")

    def bold_color(self, text: str, color: str) -> str:
        return self._wrap(text, "bold", color)
