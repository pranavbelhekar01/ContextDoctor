"""Inline directives that let a document opt out of specific rules.

Supported anywhere in a file's text (e.g. in a Markdown comment):

    <!-- contextdoctor: disable=CTX007 -->        # disable one or more rules for this file
    <!-- contextdoctor: disable=CTX007,CTX008 --> # comma-separated
    <!-- contextdoctor: disable-all -->           # disable every rule for this file
    # contextdoctor: disable=CTX003               # the marker works in any comment style

Pragmas are **file-scoped** (they apply to the whole document), which maps
cleanly onto ContextDoctor's aggregate, per-rule findings. ``"*"`` in the returned
set means "all rules".
"""

from __future__ import annotations

import re

_PRAGMA_RE = re.compile(
    r"contextdoctor:\s*disable(?P<all>-all)?(?:\s*=\s*(?P<ids>[A-Za-z0-9_,\s]+))?",
    re.IGNORECASE,
)


def parse_disabled_rules(text: str) -> set[str]:
    """Return the set of rule ids disabled by pragmas in ``text`` (``*`` == all)."""
    disabled: set[str] = set()
    for m in _PRAGMA_RE.finditer(text):
        if m.group("all"):
            disabled.add("*")
            continue
        ids = m.group("ids")
        if ids:
            for token in re.split(r"[,\s]+", ids.strip()):
                if token:
                    disabled.add(token.upper())
        else:
            # A bare "contextdoctor: disable" with no ids disables everything.
            disabled.add("*")
    return disabled
