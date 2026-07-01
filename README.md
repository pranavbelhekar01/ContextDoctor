# ContextDoctor

**A static analyzer for RAG systems and context engineering workflows.**
Think **ESLint, but for your context** — not your JavaScript.

ContextDoctor inspects your documents, chunks, and knowledge bases and flags the
structural, chunking, and context-quality problems that quietly wreck retrieval
quality — **before you ever call an LLM.**

- 🩺 **One braggable number.** A **Context Health Score** (0–100 + A–F grade), Lighthouse-style, with a README badge.
- 🔌 **Fully offline.** No API keys. No cloud. No OpenAI / Anthropic / Gemini calls. No model downloads.
- ⚡ **Fast & deterministic.** Pure static analysis. Same input → same report, every time.
- 📦 **Zero runtime dependencies.** Just Python 3.11+ and the standard library.
- 🧰 **Opinionated but extensible.** Ten sharp rules (CTX001–CTX010) with actionable fixes — plus a plugin API for your own.
- 📊 **Six output formats.** Terminal, JSON, Markdown, self-contained **HTML**, **SARIF** (GitHub code scanning), and a **badge**.
- 🔗 **Meets you where you are.** GitHub Action, pre-commit hook, and one-line LangChain / LlamaIndex integration.
- 📥 **Reads what you have.** Markdown, text, HTML, JSON, JSONL, CSV/TSV, and (optional) PDF.
- 🌐 **Try it with zero install.** A [browser playground](playground/) runs the whole analyzer in WebAssembly — nothing is uploaded.

> **Why does this exist?** Most "my RAG is bad" problems are not model problems —
> they're *context* problems: chunks that are too big or too small, duplicated
> passages crowding out diverse results, tables shredded across chunk
> boundaries, and related facts scattered so far apart that no retriever can
> reassemble them. ContextDoctor helps you answer **"why is my RAG system
> performing poorly?"** *statically*, in seconds, for free.

### Where it fits

RAG evaluation tools like **RAGAS, TruLens, DeepEval, and Phoenix** are runtime,
LLM-as-judge, *post-retrieval* — they need a running pipeline, test queries, and
API calls, and they measure the *answer*. None of them check whether your
**knowledge base was worth retrieving from in the first place.** ContextDoctor owns
that missing **pre-retrieval, pre-index** layer. It's complementary: **lint with
ContextDoctor before you index, evaluate with RAGAS/DeepEval after you answer.**

---

## The Context Health Score

Every run produces a single 0–100 score with an A–F grade — easy to track over
time, gate in CI, and show off:

```text
  Context Health Score
    69/100  D  █████████████████░░░░░░░  poor
```

Drop a live badge in your README (`--format badge` prints the snippet):

![Context Health](https://img.shields.io/badge/context%20health-92%2F100%20A-brightgreen)

---

## Install

```bash
pip install contextdoctor          # from PyPI (once published)

# or, from source:
git clone https://github.com/pranavbelhekar01/ContextDoctor
cd ContextDoctor
pip install -e ".[dev]"
```

Requires **Python 3.11+**. No other runtime dependencies.

---

## Quick start

```bash
contextdoctor analyze ./docs
```

That's it. Point it at a file or a directory of Markdown, plain text, or JSON
chunk exports, and you get a report like this:

```text
  ContextDoctor  ·  static analysis for RAG
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
| **CTX007** | `secret-detected` | error | API keys, tokens, or private keys embedded in the corpus — you're about to index a secret into your vector DB. |
| **CTX008** | `pii-detected` | warning | Emails, phone numbers, SSNs, or card numbers in the content (values are redacted, never echoed). |
| **CTX009** | `encoding-artifacts` | warning | Mojibake (`Ã©`, `â€™`), replacement chars (`�`), or control characters from a broken extraction step. |
| **CTX010** | `exceeds-embedding-limit` | warning | Chunks likely over your embedding model's token limit — the tail is silently truncated and never embedded. |

Every finding includes a **severity**, a **description**, a concrete
**recommendation**, and **file/chunk references** wherever possible.

List them anytime:

```bash
contextdoctor rules
```

---

## The Context Fragmentation Index (CFI) — experimental 🧪

The CFI is ContextDoctor's flagship experimental signal. It asks a simple
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
contextdoctor analyze ./examples/fragmented_kb
# CFI 0.750  ███████████████░░░░░   → CTX006 fires
```

---

## Inputs

ContextDoctor understands many input types and traverses directories recursively
(skipping hidden files):

- **Markdown** (`.md`, `.markdown`) — chunked by ContextDoctor's structure-aware chunker.
- **Plain text** (`.txt`) — chunked the same way.
- **HTML** (`.html`, `.htm`) — tags/scripts/styles stripped, then chunked.
- **JSON exports** (`.json`) — read as **pre-existing chunks**, so metrics reflect *your* chunking, not ours.
- **JSONL / NDJSON** (`.jsonl`, `.ndjson`) — one chunk per line.
- **CSV / TSV** (`.csv`, `.tsv`) — one chunk per row, rendered as `header: value`.
- **PDF** (`.pdf`) — *optional*: `pip install "contextdoctor[pdf]"` (keeps the core dependency-free).

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
contextdoctor analyze ./docs                          # rich terminal report (default)
contextdoctor analyze ./docs --format json            # machine-readable JSON
contextdoctor analyze ./docs --format markdown -o report.md
contextdoctor analyze ./docs --format html -o report.html   # self-contained visual report
contextdoctor analyze ./docs --format sarif -o results.sarif  # GitHub code scanning
contextdoctor analyze ./docs --format badge           # shields.io endpoint JSON + snippet
```

The **HTML report** is a single self-contained file (inline CSS + SVG, no JS, no
network) — open it, screenshot the score card, share it.

### Compare two chunking strategies

Answer *"is recursive or semantic chunking better for my corpus?"* — statically,
no LLM:

```bash
contextdoctor compare recursive_export.json semantic_export.json
```

```text
  ContextDoctor compare
    metric               before       after         Δ
    ──────────────────────────────────────────────────
    health score             71          88       +17
    findings                  6           2        -4
    duplicate %            9.10        1.20     -7.90
    CFI                    0.41        0.22     -0.19
  ✔ 'after' is healthier.
```

### CI usage

Fail the build when issues are found:

```bash
contextdoctor analyze ./docs --fail-on error     # exit 1 on any error-level finding
contextdoctor analyze ./docs --fail-on warning   # exit 1 on any warning or worse
```

**GitHub Action** (findings appear inline on the PR via SARIF):

```yaml
# .github/workflows/context.yml
name: ContextDoctor
on: [pull_request]
jobs:
  contextdoctor:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pranavbelhekar01/ContextDoctor@v0.1        # composite action (action.yml)
        with:
          path: ./knowledge_base
          fail-on: error
      - uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: contextdoctor.sarif
```

**pre-commit** (`.pre-commit-hooks.yaml` is shipped):

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pranavbelhekar01/ContextDoctor
    rev: v0.1.0
    hooks:
      - id: contextdoctor
```

---

## Configuration

ContextDoctor is opinionated but tunable. It auto-discovers a `.contextdoctor.json`
or a `[tool.contextdoctor]` table in `pyproject.toml` near your target, or you can
pass one explicitly with `--config`.

`.contextdoctor.json`:

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
[tool.contextdoctor]
max_chunk_chars = 1500
cfi_warning_threshold = 0.5
```

Common thresholds can also be overridden on the command line:

```bash
contextdoctor analyze ./docs --chunk-size 800 --max-chunk-chars 1500 --cfi-threshold 0.5
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
| `embedding_token_limit` | `512` | CTX010 threshold — set to your embedding model's context. |
| `detect_secrets` / `detect_pii` / `detect_encoding_artifacts` | `true` | Toggle CTX007 / CTX008 / CTX009. |
| `select` / `ignore` | `[]` | Only-run / skip rule ids (also `--select` / `--ignore`). |
| `severity` | `{}` | Per-rule severity override, e.g. `{"CTX006": "info"}`. |

---

## Python API

Everything the CLI does is available programmatically:

```python
from contextdoctor import analyze_path, Config

report = analyze_path("./docs", Config(max_chunk_chars=1500))

print(report.health_score, report.health_grade)   # 82 B
print(report.counts_by_severity())                 # {"info": 0, "warning": 4, "error": 1}
for f in report.findings:
    print(f.rule_id, f.severity.value, f.message)

print(report.metrics["fragmentation"]["cfi"])      # experimental CFI

from contextdoctor.reports import render_html, render_json
open("report.html", "w").write(render_html(report))
```

### Lint the chunks your pipeline actually produced

`analyze_chunks()` is a framework-agnostic bridge — hand it the exact chunks your
splitter emitted, before you embed them:

```python
from contextdoctor import analyze_chunks

# LangChain
from langchain_text_splitters import RecursiveCharacterTextSplitter
docs = RecursiveCharacterTextSplitter(chunk_size=800).split_documents(raw_docs)
report = analyze_chunks([d.page_content for d in docs])

# LlamaIndex
nodes = SentenceSplitter(chunk_size=512).get_nodes_from_documents(documents)
report = analyze_chunks([n.get_content() for n in nodes])

if report.health_score < 80:
    raise SystemExit(f"Context health too low: {report.health_score}/100")
```

This is the assertion you can put in your ingestion pipeline's tests: **fail the
build if your chunking regresses.**

---

## Adopting on an existing corpus

Turning a linter on a large, pre-existing knowledge base usually floods you with
issues. Two mechanisms make adoption incremental:

**Baseline** — freeze today's findings; fail only on *new* ones:

```bash
contextdoctor baseline ./docs                       # writes .contextdoctor-baseline.json
contextdoctor analyze ./docs --baseline .contextdoctor-baseline.json --fail-on warning
# -> pre-existing findings are suppressed; only regressions surface (and count against the score)
```

**Inline disable pragmas** — opt a specific file out of a rule (file-scoped),
for the legitimate cases (e.g. a doc that *shows* an example API key):

```markdown
<!-- contextdoctor: disable=CTX007 -->        # disable one or more rules for this file
<!-- contextdoctor: disable=CTX003,CTX008 --> # comma-separated
<!-- contextdoctor: disable-all -->           # disable everything for this file
```

## Playground

Want to try it without installing anything? The
[browser playground](playground/) runs the entire ContextDoctor engine in
WebAssembly (Pyodide) — paste your chunks, get a score and a full report, and
**nothing is uploaded**. It works because the core has zero dependencies. Deploy
your own to GitHub Pages with the included workflow, or run it locally:

```bash
python -m http.server -d playground 8000   # then open http://localhost:8000
```

## Custom rules & plugins

ContextDoctor is extensible. A plugin is just an `Analyzer` subclass that declares
the rules it emits — and those rules then flow through **everything**: the health
score, all report formats, SARIF, `contextdoctor rules`, and `--select` /
`--ignore`, exactly like the built-in `CTX*` rules.

The lowest-friction path is a single local file:

```python
# my_rules.py
from contextdoctor.analyzers import AnalysisContext, Analyzer
from contextdoctor.models import AnalyzerResult, Location, Severity
from contextdoctor.rules import Rule

class TodoAnalyzer(Analyzer):
    name = "todo"
    provides_rules = [Rule(id="MYP001", name="unfinished-content", category="custom",
                           default_severity=Severity.WARNING,
                           description="Placeholder text found.",
                           recommendation="Finish or remove it before indexing.")]

    def analyze(self, ctx: AnalysisContext) -> AnalyzerResult:
        findings = [
            self._finding("MYP001", "TODO marker in chunk",
                          locations=[Location(file=c.source_file, chunk_id=c.id)])
            for c in ctx.chunks if "TODO" in c.text
        ]
        return self._result(findings=findings)
```

```bash
contextdoctor analyze ./docs --plugin ./my_rules.py
```

Three ways to load, in increasing order of packaging effort:

| How | Spec |
| --- | --- |
| Local `.py` file | `--plugin ./my_rules.py` or `{"plugins": ["./my_rules.py"]}` |
| Importable module | `--plugin my_pkg.rules` or `my_pkg.rules:TodoAnalyzer` |
| Published package (auto-discovered) | entry point `contextdoctor.analyzers` in `pyproject.toml` |

```toml
# a distributable plugin package advertises itself; no config needed by users
[project.entry-points."contextdoctor.analyzers"]
my-rules = "contextdoctor_plugin_myrules:TodoAnalyzer"
```

A complete, working example lives in
[`examples/plugin/`](examples/plugin) (rule `PLH001`, flagging unfinished
content). Plugin loading is best-effort and offline — a broken plugin warns and
is skipped, and built-in `CTX*` ids can't be silently overridden.

## Documentation

Full guides live in [`docs/`](docs/):

- [Getting Started](docs/getting-started.md) · [User Guide](docs/user-guide.md)
- [Rules Reference](docs/rules.md) — every rule, why it matters, how to fix it
- [Configuration](docs/configuration.md) · [CLI Reference](docs/cli.md) · [Python API](docs/api.md)
- [Plugins](docs/plugins.md) · [Integrations](docs/integrations.md) · [FAQ & Troubleshooting](docs/faq.md)
- [Technical Overview](docs/OVERVIEW.md) — a single verifiable description of the whole tool

## How it works

```
contextdoctor/
├── cli.py            # argparse CLI: analyze / compare / rules
├── config.py         # thresholds + config discovery (.json / pyproject.toml)
├── engine.py         # discover → chunk → analyze → filter → score → Report
├── scoring.py        # the Context Health Score
├── baseline.py       # freeze findings; report only new ones
├── plugins.py        # load custom analyzers/rules (files, modules, entry points)
├── models.py         # Chunk, Document, Finding, Report, Severity
├── chunking/         # structure-aware chunker (paragraphs, tables, code fences)
├── parsers/          # discovery + md/txt/html/json/jsonl/csv/pdf loaders + pragmas
├── analyzers/        # one module per concern:
│   ├── chunk_stats.py      # CTX001 / CTX002 / CTX010 + distribution + overlap
│   ├── duplicates.py       # CTX003 (hash + Jaccard/MinHash)
│   ├── tables.py           # CTX004
│   ├── headings.py         # CTX005
│   ├── content_quality.py  # CTX007 / CTX008 / CTX009 (secrets, PII, encoding)
│   └── fragmentation.py    # CTX006 — the experimental CFI
├── rules/            # rule catalogue (id, severity, description, recommendation)
├── reports/          # terminal / json / markdown / html / sarif / badge
└── utils/            # text, hashing (MinHash), NLP, ANSI, secret/PII patterns
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

1. Add the rule metadata to `contextdoctor/rules/registry.py`.
2. Emit findings for it from a new or existing analyzer in `contextdoctor/analyzers/`
   (subclass `Analyzer`, use `self._finding(...)`).
3. Register the analyzer in `contextdoctor/analyzers/__init__.py`.
4. Add tests and an example that triggers it.

---

## Examples

The [`examples/`](examples/) directory ships datasets you can run immediately:

- [`examples/clean_docs/`](examples/clean_docs) — well-structured docs; scores 100/100.
- [`examples/messy_docs/`](examples/messy_docs) — triggers CTX001–CTX005 and CTX010 (oversized/tiny chunks, duplicates, a broken table, heading fragmentation, embedding-limit).
- [`examples/risky_docs/`](examples/risky_docs) — a support log that leaked secrets, PII, and mojibake into the KB (CTX007–CTX009). Values are always redacted.
- [`examples/fragmented_kb/`](examples/fragmented_kb) — a scattered knowledge base that triggers the experimental CFI (CTX006), with its own `.contextdoctor.json`.

```bash
contextdoctor analyze ./examples/messy_docs
contextdoctor analyze ./examples/risky_docs
contextdoctor analyze ./examples/fragmented_kb
```

---

## Roadmap

ContextDoctor is at **v0.1**. Ideas on the table:

- More rules: boilerplate/nav-chrome detection, orphaned references, language mixing.
- More parsers: `.rst`, DOCX, and richer HTML (readability-style main-content extraction).
- A refined, better-validated CFI (the current one is intentionally experimental).
- Line-scoped disable pragmas (today's pragmas are file-scoped) and autofix suggestions.
- A VS Code extension surfacing findings inline as you edit docs.

Contributions and issues welcome.

---

## Contributing & community

Contributions are welcome — bug reports, docs, new rules, parsers, and plugins.

- [CONTRIBUTING.md](CONTRIBUTING.md) — dev setup, the test loop, and how to add a rule
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- [SECURITY.md](SECURITY.md) — report vulnerabilities privately
- [Open an issue](https://github.com/pranavbelhekar01/ContextDoctor/issues)

## License

[MIT](LICENSE). Fully offline, forever. No LLM was called to produce your report.
