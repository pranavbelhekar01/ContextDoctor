# Security Policy

## Reporting a vulnerability

Please **do not** open a public issue for security vulnerabilities.

Instead, report privately via one of:

- GitHub's [private vulnerability reporting](https://github.com/pranavbelhekar01/ContextDoctor/security/advisories/new)
  (Security → Report a vulnerability), or
- email **pranavbelhekar2002@gmail.com** with the details.

Please include: a description, reproduction steps, affected version, and impact.
We'll acknowledge your report as quickly as we can and keep you updated on the fix.

## Supported versions

ContextDoctor is pre-1.0; security fixes target the **latest released version** on
PyPI.

## Scope & threat model

ContextDoctor is a **static analyzer that runs fully offline** — no network calls,
no API keys, no telemetry. It reads local files you point it at. Relevant
considerations:

- **Untrusted input.** ContextDoctor parses arbitrary documents (Markdown, HTML,
  JSON, CSV, PDF via the optional extra). Report any parsing behavior that could
  cause crashes, resource exhaustion, or escapes (e.g. HTML that isn't properly
  escaped in the HTML report).
- **Secret/PII detection is best-effort.** CTX007/CTX008 use regular expressions
  and will have false positives and negatives. **Do not** rely on ContextDoctor as
  your only control for preventing secret/PII leakage into a vector store. Detected
  values are always redacted in output.
- **Plugins execute code.** Loading a plugin (`--plugin`, `plugins` config, or an
  installed entry point) imports and runs that Python. Only load plugins you trust.

Thanks for helping keep ContextDoctor and its users safe.
