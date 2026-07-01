# Changelog

All notable changes to ContextDoctor are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1] — 2026-07-01

### Changed

- Renamed the distribution and import package to **`contextdoctor`** (the CLI is
  now `contextdoctor`; the GitHub repository is `pranavbelhekar01/ContextDoctor`).
- Updated all project URLs, the SARIF `informationUri`, and documentation to point
  at the `ContextDoctor` repository. No functional changes.

## [0.1.0] — 2026-07-01

The first release: fully offline static analysis for RAG systems — zero API keys,
zero cloud, zero runtime dependencies. Ten rules, a Context Health Score, six
output formats, a plugin API, and a browser playground.

### Added — analysis & scoring

- **Context Health Score** — a single 0–100 score with an A–F grade in every
  report, plus a `badge` output format (shields.io endpoint JSON + Markdown snippet).
- New content-quality rules:
  - **CTX007** — embedded secret / API-key detection (values are always redacted).
  - **CTX008** — PII detection (emails, phones, SSNs, card numbers via Luhn; redacted).
  - **CTX009** — encoding-artifact detection (mojibake, replacement chars, control chars).
  - **CTX010** — chunks exceeding the embedding model's token limit.
- New output formats: self-contained **HTML** (inline CSS + SVG) and **SARIF 2.1.0**
  for GitHub code scanning.
- `contextdoctor compare <a> <b>` — side-by-side comparison of two corpora / chunking
  strategies with health-score and metric deltas.
- Framework-agnostic `analyze_chunks()` API for one-line LangChain / LlamaIndex use,
  plus `analyze_paths()` for multi-path analysis (the CLI now accepts multiple paths).
- Rule selection and severity control: `select` / `ignore` config + `--select` /
  `--ignore` flags, and per-rule `severity` overrides.
- Integrations: a composite **GitHub Action** (`action.yml`) and a **pre-commit**
  hook (`.pre-commit-hooks.yaml`).
- **Plugin system** — add custom analyzers and rules via a local `.py` file, an
  importable module, or a published package's `contextdoctor.analyzers` entry point.
  Plugin rules flow through the score, all reports, SARIF, and `--select`/`--ignore`.
  Loading is best-effort (a broken plugin warns and is skipped); built-in `CTX*`
  ids cannot be silently overridden. See `examples/plugin/`.
- **More input formats**: HTML (`.html`/`.htm`, tags/scripts stripped), JSONL/NDJSON,
  CSV/TSV (one chunk per row), and optional **PDF** (`pip install "contextdoctor[pdf]"`).
  Unreadable files are skipped with a warning instead of aborting the run.
- **Baseline files** — `contextdoctor baseline <path>` records current findings;
  `analyze --baseline <file>` suppresses them so CI fails only on *new* issues.
- **Inline disable pragmas** — file-scoped `<!-- contextdoctor: disable=CTX007 -->`
  (and `disable-all`) to opt a document out of specific rules.
- **Browser playground** (`playground/`) — the full analyzer running in WebAssembly
  via Pyodide, plus a GitHub Pages deploy workflow. Nothing is uploaded.

### Added — core engine

- `contextdoctor analyze <path>` CLI with terminal, JSON, and Markdown reports.
- `contextdoctor rules` to list the rule catalogue.
- Inputs: Markdown (`.md`), plain text (`.txt`), and JSON chunk exports, with
  recursive directory traversal.
- Structure-aware chunker (paragraphs, tables, code fences) with configurable
  size and overlap.
- Analyzers and rules:
  - **CTX001 / CTX002** — chunk too large / too small, with a full size
    distribution (min, median, mean, p95, max) and overlap %.
  - **CTX003** — exact (SHA-256) and near (Jaccard + MinHash) duplicate detection.
  - **CTX004** — markdown tables broken across chunk boundaries.
  - **CTX005** — heading/section fragmentation across too many chunks.
  - **CTX006** — the experimental **Context Fragmentation Index (CFI)**.
- Configuration via `.contextdoctor.json`, `[tool.contextdoctor]` in
  `pyproject.toml`, or CLI flags, with auto-discovery.
- `--fail-on` for CI gating; deterministic, reproducible output.
- Example datasets under `examples/` and a full pytest + ruff test suite.
