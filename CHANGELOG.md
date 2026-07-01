# Changelog

All notable changes to ContextLint are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] — 2026-07-01

Initial release. Fully offline static analysis for RAG systems — zero API keys,
zero cloud, zero runtime dependencies.

### Added

- `contextlint analyze <path>` CLI with terminal, JSON, and Markdown reports.
- `contextlint rules` to list the rule catalogue.
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
- Configuration via `.contextlint.json`, `[tool.contextlint]` in
  `pyproject.toml`, or CLI flags, with auto-discovery.
- `--fail-on` for CI gating; deterministic, reproducible output.
- Example datasets under `examples/` and a full pytest + ruff test suite.
