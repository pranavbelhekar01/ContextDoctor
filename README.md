# ContextLint

**A static analyzer for RAG systems and context engineering workflows.**
Think **ESLint, but for your context** — not your JavaScript.

ContextLint inspects your documents, chunks, and knowledge bases and flags the
structural, chunking, and context-quality problems that quietly wreck retrieval
quality — **before you ever call an LLM.**

- 🔌 **Fully offline.** No API keys. No cloud. No OpenAI / Anthropic / Gemini calls. No model downloads.
- ⚡ **Fast & deterministic.** Pure static analysis. Same input → same report, every time.
- 📦 **Zero runtime dependencies.** Just Python 3.11+ and the standard library.
- 🧰 **Opinionated but extensible.** A small set of sharp rules (CTX001–CTX006) with actionable fixes.
- 📊 **Multiple outputs.** A polished terminal report, plus JSON and Markdown for CI and sharing.

> **Why does this exist?** Most "my RAG is bad" problems are not model problems —
> they're *context* problems: chunks that are too big or too small, duplicated
> passages crowding out diverse results, tables shredded across chunk
> boundaries, and related facts scattered so far apart that no retriever can
> reassemble them. ContextLint helps you answer **"why is my RAG system
> performing poorly?"** *statically*, in seconds, for free.

---

## Install

```bash
pip install contextlint          # from PyPI (once published)

# or, from source:
git clone https://github.com/contextlint/contextlint
cd contextlint
pip install -e ".[dev]"
```

Requires **Python 3.11+**. No other runtime dependencies.

---

## Quick start

```bash
contextlint analyze ./docs
```

That's it. Point it at a file or a directory of Markdown, plain text, or JSON
chunk exports, and you get a report like this:

```text
  ContextLint  ·  static analysis for RAG
  ────────────────────────────────────────────────────────────────────
  root: examples/messy_docs
  files: 4   chunks: 15   generated: 2026-07-01T06:19:10Z

  Summary  1 error  4 warning  0 info

  Chunk statistics
                   chars    tokens
    min               10         2
    median           705       176
    mean           907.5     226.8
    p95           2166.2     541.8
    max             4199      1050
    overlap 35.48%   ·   duplicated 6.67%

  Context Fragmentation Index (experimental)
    CFI 0.030  █░░░░░░░░░░░░░░░░░░░  0=coherent  1=fragmented

  Findings

    ✖ CTX004 [broken-table]
      A markdown table in chunks_export.json is split between chunk 2 and chunk 3.
      → Keep tables intact within a single chunk. A table split across chunks
        loses its header row and column meaning...
        • chunks_export.json [chunk 2] (table continues)
        • chunks_export.json [chunk 3] (table continued)

    ▲ CTX001 [chunk-too-large]
      1 chunk(s) exceed the recommended maximum of 2000 characters (largest: 4199).
      → Split oversized chunks...

    ... (CTX002, CTX003, CTX005) ...
```

---

## What it checks

| Rule | Name | Severity | What it catches |
| --- | --- | --- | --- |
| **CTX001** | `chunk-too-large` | warning | Chunks bigger than `max_chunk_chars` — they dilute relevance and blow the context budget. |
| **CTX002** | `chunk-too-small` | warning | Chunks smaller than `min_chunk_chars` — fragments too small to carry standalone meaning. |
| **CTX003** | `duplicate-content` | warning | Exact (hash) and near (Jaccard / MinHash) duplicate chunks that crowd out diverse results. |
| **CTX004** | `broken-table` | error | Markdown tables split across a chunk boundary, losing their header row. |
| **CTX005** | `heading-fragmentation` | warning | A single section spanning too many chunks — a signal to use parent-child retrieval. |
| **CTX006** | `high-context-fragmentation` | warning · **experimental** | High **Context Fragmentation Index** (CFI) — related information scattered across distant chunks. |

Every finding includes a **severity**, a **description**, a concrete
**recommendation**, and **file/chunk references** wherever possible.

List them anytime:

```bash
contextlint rules
```

---

## The Context Fragmentation Index (CFI) — experimental 🧪

The CFI is ContextLint's flagship experimental signal. It asks a simple
question: **when the same named thing is discussed in multiple chunks, how far
apart are those chunks?** Information about one entity scattered across the whole
corpus is much harder for a retriever to reassemble than information kept close
together.

**How it's computed (v0.1):**

1. Extract lightweight, **local** entities per chunk (proper nouns / acronyms) — no models, no network.
2. For every entity that appears in ≥ `min_entity_freq` distinct chunks, record the chunk indices where it appears.
3. Compute the **mean gap** between consecutive appearances and normalise by the corpus size (`N − 1`) → a per-entity fragmentation in `[0, 1]`.
4. The CFI is the **occurrence-weighted mean** of per-entity fragmentation.

**Scale:** `0.0` = highly coherent · `1.0` = highly fragmented.

> ⚠️ **The CFI is experimental** and deliberately simple. It's a *signal to
> inspect*, not a hard pass/fail — treat a high CFI as "go look at how this topic
> is spread out," not "this corpus is broken." It is clearly labelled
> experimental everywhere it appears.

See it in action:

```bash
contextlint analyze ./examples/fragmented_kb
# CFI 0.750  ███████████████░░░░░   → CTX006 fires
```

---

## Inputs

ContextLint understands three kinds of input and traverses directories
recursively (skipping hidden files):

- **Markdown** (`.md`, `.markdown`) — chunked by ContextLint's structure-aware chunker.
- **Plain text** (`.txt`) — chunked the same way.
- **JSON exports** (`.json`) — read as **pre-existing chunks**, so metrics reflect *your* chunking, not ours.

Supported JSON shapes (auto-detected):

```jsonc
["chunk one", "chunk two"]                          // list of strings
[{"text": "..."}, {"content": "..."}]               // list of objects
{"chunks": [{"page_content": "..."}]}               // container object
```

Recognised text keys: `text`, `content`, `chunk`, `page_content`, `body`,
`passage`. Recognised container keys: `chunks`, `documents`, `nodes`, `data`,
`items`, `passages`.

---

## Output formats

```bash
contextlint analyze ./docs                              # rich terminal report (default)
contextlint analyze ./docs --format json                # machine-readable JSON
contextlint analyze ./docs --format markdown            # shareable Markdown
contextlint analyze ./docs --format markdown -o report.md
```

### CI usage

Fail the build when issues are found:

```bash
contextlint analyze ./docs --fail-on error     # exit 1 on any error-level finding
contextlint analyze ./docs --fail-on warning   # exit 1 on any warning or worse
```

```yaml
# .github/workflows/context.yml
- run: pip install contextlint
- run: contextlint analyze ./knowledge_base --fail-on error
```

---

## Configuration

ContextLint is opinionated but tunable. It auto-discovers a `.contextlint.json`
or a `[tool.contextlint]` table in `pyproject.toml` near your target, or you can
pass one explicitly with `--config`.

`.contextlint.json`:

```json
{
  "chunk_size": 1200,
  "chunk_overlap": 120,
  "max_chunk_chars": 2000,
  "min_chunk_chars": 200,
  "near_duplicate_threshold": 0.85,
  "max_chunks_per_heading": 5,
  "cfi_warning_threshold": 0.6,
  "min_entity_freq": 2
}
```

Or in `pyproject.toml`:

```toml
[tool.contextlint]
max_chunk_chars = 1500
cfi_warning_threshold = 0.5
```

Common thresholds can also be overridden on the command line:

```bash
contextlint analyze ./docs --chunk-size 800 --max-chunk-chars 1500 --cfi-threshold 0.5
```

| Key | Default | Meaning |
| --- | --- | --- |
| `chunk_size` | `1200` | Target chunk size (chars) when chunking raw `.md`/`.txt`. |
| `chunk_overlap` | `120` | Overlap (chars) carried between chunks. |
| `max_chunk_chars` | `2000` | CTX001 threshold. |
| `min_chunk_chars` | `200` | CTX002 threshold. |
| `shingle_size` | `5` | Word n-gram size for similarity/overlap. |
| `near_duplicate_threshold` | `0.85` | CTX003 near-duplicate Jaccard cutoff. |
| `duplicate_pct_warning` | `10.0` | Corpus-wide duplicate % that warns. |
| `max_chunks_per_heading` | `5` | CTX005 threshold. |
| `min_entity_freq` | `2` | Min distinct chunks an entity needs for CFI. |
| `cfi_warning_threshold` | `0.6` | CTX006 threshold. |

---

## Python API

Everything the CLI does is available programmatically:

```python
from contextlint import analyze_path, Config

report = analyze_path("./docs", Config(max_chunk_chars=1500))

print(report.total_chunks, "chunks")
print(report.counts_by_severity())        # {"info": 0, "warning": 4, "error": 1}
for f in report.findings:
    print(f.rule_id, f.severity.value, f.message)

# Metrics per analyzer, including the experimental CFI:
print(report.metrics["fragmentation"]["cfi"])

# Serialise:
from contextlint.reports import render_json, render_markdown
open("report.md", "w").write(render_markdown(report))
```

---

## How it works

```
contextlint/
├── cli.py            # argparse CLI: analyze / rules
├── config.py         # thresholds + config discovery (.json / pyproject.toml)
├── engine.py         # discover → chunk → analyze → assemble Report
├── models.py         # Chunk, Document, Finding, Report, Severity
├── chunking/         # structure-aware chunker (paragraphs, tables, code fences)
├── parsers/          # file discovery + markdown/text/json loaders
├── analyzers/        # one module per concern:
│   ├── chunk_stats.py    # CTX001 / CTX002 + size distribution + overlap
│   ├── duplicates.py     # CTX003 (hash + Jaccard/MinHash)
│   ├── tables.py         # CTX004
│   ├── headings.py       # CTX005
│   └── fragmentation.py  # CTX006 — the experimental CFI
├── rules/            # rule catalogue (id, severity, description, recommendation)
├── reports/          # terminal (ANSI) / json / markdown renderers
└── utils/            # text, hashing (MinHash), lightweight NLP, ANSI
```

The pipeline is a straight line: **discover files → build chunks → run each
analyzer over the shared corpus → collect findings + metrics → render.** No
step touches the network.

---

## Development

```bash
pip install -e ".[dev]"

pytest -q                 # run the test suite
ruff check .              # lint
ruff format .             # format
```

The project targets Python 3.11, 3.12, and 3.13, and is tested on Linux, macOS,
and Windows in CI.

### Adding a rule

1. Add the rule metadata to `contextlint/rules/registry.py`.
2. Emit findings for it from a new or existing analyzer in `contextlint/analyzers/`
   (subclass `Analyzer`, use `self._finding(...)`).
3. Register the analyzer in `contextlint/analyzers/__init__.py`.
4. Add tests and an example that triggers it.

---

## Examples

The [`examples/`](examples/) directory ships datasets you can run immediately:

- [`examples/clean_docs/`](examples/clean_docs) — well-structured docs; reports no issues.
- [`examples/messy_docs/`](examples/messy_docs) — triggers CTX001–CTX005 (oversized/tiny chunks, duplicates, a broken table, heading fragmentation).
- [`examples/fragmented_kb/`](examples/fragmented_kb) — a scattered knowledge base that triggers the experimental CFI (CTX006), with its own `.contextlint.json`.

```bash
contextlint analyze ./examples/messy_docs
contextlint analyze ./examples/fragmented_kb
```

---

## Roadmap

ContextLint is at **v0.1**. Ideas on the table:

- More rules: encoding artefacts, boilerplate/nav-chrome detection, orphaned references, language mixing.
- Pluggable, user-defined rules.
- Smarter chunkers and per-format parsers (HTML, PDF text dumps, CSV).
- A refined, better-validated CFI (the current one is intentionally experimental).
- Baseline files and inline ignores (`contextlint: disable=CTX003`).

Contributions and issues welcome.

---

## License

[MIT](LICENSE). Fully offline, forever. No LLM was called to produce your report.
