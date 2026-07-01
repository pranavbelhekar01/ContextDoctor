"""Regex detectors for secrets, PII, and encoding artifacts.

Design rule: **never return the matched value.** Detectors report only the
*type* of thing found (and, for PII, a count) so ContextDoctor can warn without
itself echoing a secret or a person's data into logs or reports.
"""

from __future__ import annotations

import re

# --- Secrets / credentials ---------------------------------------------------
# Each entry: (human label, compiled pattern). Patterns target well-known,
# high-signal credential shapes to keep false positives low.
_SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("OpenAI API key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b")),
    ("Anthropic API key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}\b")),
    ("AWS access key id", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("Stripe secret key", re.compile(r"\b(?:sk|rk)_live_[A-Za-z0-9]{16,}\b")),
    (
        "private key block",
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----"),
    ),
    (
        "JSON Web Token",
        re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"),
    ),
    (
        "generic assigned secret",
        re.compile(
            r"""(?ix)
            \b(?:api[_-]?key|secret|token|passwd|password|access[_-]?token)\b
            \s*[:=]\s*
            ['"]?[A-Za-z0-9_\-/+]{16,}['"]?
            """
        ),
    ),
]

# --- PII ---------------------------------------------------------------------
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_PHONE_RE = re.compile(
    r"(?<!\d)(?:\+?\d{1,3}[\s.-]?)?(?:\(\d{3}\)|\d{3})[\s.-]\d{3}[\s.-]\d{4}(?!\d)"
)
_CARD_CANDIDATE_RE = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?<=\d)")

# --- Encoding artifacts ------------------------------------------------------
_REPLACEMENT_RE = re.compile("�")
# Classic UTF-8-decoded-as-Latin-1 mojibake bigrams.
_MOJIBAKE_RE = re.compile(r"Ã[\x80-\xbf©®¢£¤¥§]|â€[\x99\x9c\x9d\x93\x94˜™œ]|Â[\xa0-\xbf]|Ã¢â‚¬")
# Control characters excluding tab/newline/carriage-return.
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _luhn_ok(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = ord(ch) - 48
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def find_secrets(text: str) -> list[str]:
    """Return the labels of secret types found (deduplicated, order-stable)."""
    found: list[str] = []
    seen: set[str] = set()
    for label, pattern in _SECRET_PATTERNS:
        if pattern.search(text) and label not in seen:
            seen.add(label)
            found.append(label)
    return found


def find_pii(text: str) -> dict[str, int]:
    """Return a mapping of PII type -> occurrence count (values never returned)."""
    counts: dict[str, int] = {}
    emails = _EMAIL_RE.findall(text)
    if emails:
        counts["email"] = len(emails)
    ssns = _SSN_RE.findall(text)
    if ssns:
        counts["ssn"] = len(ssns)
    phones = _PHONE_RE.findall(text)
    if phones:
        counts["phone"] = len(phones)
    cards = 0
    for m in _CARD_CANDIDATE_RE.finditer(text):
        digits = re.sub(r"[ -]", "", m.group(0))
        if 13 <= len(digits) <= 19 and _luhn_ok(digits):
            cards += 1
    if cards:
        counts["credit_card"] = cards
    return counts


def find_encoding_issues(text: str) -> dict[str, int]:
    """Return a mapping of encoding-artifact type -> occurrence count."""
    counts: dict[str, int] = {}
    replacement = len(_REPLACEMENT_RE.findall(text))
    if replacement:
        counts["replacement_char"] = replacement
    mojibake = len(_MOJIBAKE_RE.findall(text))
    if mojibake:
        counts["mojibake"] = mojibake
    control = len(_CONTROL_RE.findall(text))
    if control:
        counts["control_char"] = control
    return counts
