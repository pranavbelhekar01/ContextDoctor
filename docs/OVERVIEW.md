# ContextDoctor — Complete Technical Overview

*A verifiable, self-contained description of what ContextDoctor is, what it provides,
and how everything works. Every claim here can be checked against the code in this
repository or reproduced with the commands in the "Verify it yourself" section at
the end.*

- **Name / version:** ContextDoctor `0.1.0`
- **Language / runtime:** Python `>= 3.11` (developed and tested on 3.13)
- **Runtime dependencies:** **none** (standard library only)
- **License:** MIT
- **Size:** ~4,056 lines across 38 Python modules in the package; ~1,273 lines of tests
- **Tests:** **115 passing, 0 failing; 93% line coverage**
- **Distributable:** pure-Python wheel, ~66 KB (`contextdoctor-0.1.0-py3-none-any.whl`)

---

## 1. What it is (one paragraph)

ContextDoctor is a **static analyzer for RAG (Retrieval-Augmented Generation)
systems and context-engineering workflows** — "ESLint for your context." It
inspects documents, chunks, and knowledge bases and reports structural,
chunking, and content-quality problems **before an LLM is ever invoked**. It runs
**fully offline**: no API keys, no cloud calls, no OpenAI/Anthropic/Gemini usage,
no model downloads. Results are **deterministic and reproducible** — the same
input always produces the same report.

## 2. The problem and the market position

Modern RAG-evaluation tools — **RAGAS, TruLens, DeepEval, Arize Phoenix,
Braintrust, Promptfoo** — are **runtime, LLM-as-judge, and post-retrieval**: they
require a running pipeline, test queries, and API calls, and they score the
generated *answer* (faithfulness, relevance, groundedness). None of them assess
whether the **knowledge base itself was worth retrieving from** — i.e.
pre-retrieval data quality (stale, duplicated, mis-chunked, secret-leaking, or
fragmented content).

ContextDoctor occupies that **pre-retrieval, pre-index** layer. It is
**complementary, not competitive**: *lint with ContextDoctor before you index;
evaluate with RAGAS/DeepEval after you answer.* This is the central design thesis
and the differentiator you can cross-check against the feature sets of the tools
named above (they are all runtime evaluators; ContextDoctor is a static linter).

## 3. Design principles

1. **Static analysis only** — no LLM inference of any kind.
2. **Fully local & offline** — verified: there are **zero imports** of
   `requests`, `urllib.request`, `socket`, `httpx`, `openai`, `anthropic`,
   `boto3`, etc. anywhere in the package.
3. **Zero runtime dependencies** — the whole analyzer is standard-library Python.
4. **Deterministic** — no `Date.now()`/random in analysis paths; stable hashing.
5. **Opinionated but extensible** — a curated rule set plus a plugin API.

---

## 4. Complete feature inventory

### 4.1 Context Health Score
A single **0–100 score with an A+…F letter grade** (Lighthouse-style), present in
every report. Computed deterministically from the findings via a smooth
exponential decay of accumulated severity penalty:

```
penalty = 15·(#errors) + 6·(#warnings) + 1.5·(#infos)
score   = round(100 · exp(-penalty / 120))   # clamped to [0,100]
```

Grade bands: **A+** ≥97, **A** ≥90, **B** ≥80, **C** ≥70, **D** ≥60, **F** <60.
The model gives diminishing marginal damage (the 10th warning hurts less than the
1st) and any rule — including plugin rules — contributes automatically.

### 4.2 The ten rules (CTX001–CTX010)

| Rule | Name | Severity | What it detects | How |
| --- | --- | --- | --- | --- |
| CTX001 | chunk-too-large | warning | Chunks over `max_chunk_chars` (default 2000) | char count |
| CTX002 | chunk-too-small | warning | Non-empty chunks under `min_chunk_chars` (default 200) | char count |
| CTX003 | duplicate-content | warning | Exact + near-duplicate chunks | SHA-256 hash + Jaccard/MinHash |
| CTX004 | broken-table | **error** | Markdown tables split across a chunk boundary | table-row/separator heuristics |
| CTX005 | heading-fragmentation | warning | A section spanning > `max_chunks_per_heading` chunks (default 5) | heading offsets → chunk mapping |
| CTX006 | high-context-fragmentation | warning *(experimental)* | High Context Fragmentation Index | see §4.3 |
| CTX007 | secret-detected | **error** | Embedded API keys / credentials | regex patterns (values redacted) |
| CTX008 | pii-detected | warning | Emails, phones, SSNs, card numbers | regex + Luhn (values redacted) |
| CTX009 | encoding-artifacts | warning | Mojibake, replacement chars, control chars | regex |
| CTX010 | exceeds-embedding-limit | warning | Chunks over `embedding_token_limit` (default 512) | token estimate |

Every finding carries a **severity, message, recommendation, and file/chunk/line
locations**.

### 4.3 Context Fragmentation Index (CFI) — flagship experimental metric
Measures how far apart the same named entity appears across chunks. Algorithm
(v0.1):
1. Extract lightweight **local** entities per chunk (proper-noun phrases +
   acronyms) via regex — no models, no network.
2. For each entity in ≥ `min_entity_freq` distinct chunks, take the sorted chunk
   indices where it appears.
3. Compute the **mean gap** between consecutive appearances, normalized by
   corpus size `(N − 1)` → per-entity fragmentation in `[0, 1]`.
4. **CFI = occurrence-weighted mean** of per-entity fragmentation.

Scale: `0.0` = highly coherent, `1.0` = highly fragmented. Labeled **experimental**
everywhere; triggers CTX006 at `cfi_warning_threshold` (default 0.6). It is a
*signal to inspect*, not a hard pass/fail.

### 4.4 How the other analyzers work
- **Chunk statistics:** min/median/mean/p95/max/stdev for characters and estimated
  tokens; a 12-bucket size histogram; and an **overlap %** computed as average
  word-shingle Jaccard between consecutive chunks in a document.
- **Duplicate detection:** exact via SHA-256 of normalized text; near via word
  n-gram shingles (default size 5) with a **MinHash** (32-permutation) prefilter,
  then exact Jaccard for corpora ≤ 1500 chunks (default threshold 0.85). Reports
  a corpus-wide duplicate %.
- **Table integrity:** detects whether a chunk ends "inside" a markdown table and
  the next chunk begins with table rows lacking a header separator.
- **Heading continuity:** parses ATX headings (with offsets, skipping code
  fences), maps each chunk to its section, flags sections spanning too many
  chunks, and recommends parent-child retrieval.
- **Content quality:** regex detectors for secrets (OpenAI/Anthropic/AWS/GitHub/
  Google/Slack/Stripe keys, private-key blocks, JWTs, generic assigned secrets),
  PII (email/phone/SSN/credit-card with **Luhn** validation), and encoding
  artifacts. **Detected values are never echoed** — only the *type* is reported.
- **Token estimate:** heuristic blend `max(chars/4, words·0.75)` (no tokenizer
  dependency), which powers CTX010.

### 4.5 Input formats (7 families)
Directory traversal is recursive and skips hidden files.
- **Markdown** (`.md`, `.markdown`) — chunked by a structure-aware chunker.
- **Plain text** (`.txt`) — chunked the same way.
- **HTML** (`.html`, `.htm`) — scripts/styles/tags stripped, then chunked.
- **JSON** (`.json`) — read as **pre-existing chunks** (your chunking, not ours).
- **JSONL / NDJSON** (`.jsonl`, `.ndjson`) — one chunk per line.
- **CSV / TSV** (`.csv`, `.tsv`) — one chunk per row, rendered as `header: value`.
- **PDF** (`.pdf`) — **optional** (`pip install "contextdoctor[pdf]"`, uses `pypdf`);
  the core stays dependency-free. Unreadable files are skipped with a warning,
  never fatal.

JSON auto-detected shapes: a list of strings; a list of objects; or a container
object. Recognized text keys: `text, content, chunk, page_content, body,
passage`. Recognized container keys: `chunks, documents, nodes, data, items,
passages`.

### 4.6 Output formats (6)
- **terminal** — colored ANSI report (hand-rolled, zero deps; ASCII fallback on
  legacy consoles; UTF-8 reconfigured on Windows).
- **json** — machine-readable, includes health, per-analyzer metrics, findings.
- **markdown** — shareable report.
- **html** — a **single self-contained file** (inline CSS + SVG, no JS, no
  network): score ring, KPI cards, severity bar, chunk-size histogram, CFI
  section, findings. Dark/light via `prefers-color-scheme`.
- **sarif** — SARIF 2.1.0 for **GitHub code scanning** (findings inline on PRs).
- **badge** — shields.io endpoint JSON + a paste-ready Markdown snippet.

### 4.7 Commands (CLI)
- `contextdoctor analyze <path...>` — analyze one or more files/dirs.
- `contextdoctor compare <a> <b>` — side-by-side A/B of two corpora / chunking
  strategies with health-score and metric deltas (terminal or JSON).
- `contextdoctor baseline <path...>` — write a baseline of current findings.
- `contextdoctor rules` — list all rules (including plugin rules).

Key `analyze` flags: `--format`, `--output/-o`, `--config/-c`, `--fail-on`
(CI gating; exit 1 at/above a severity), `--select` / `--ignore` (rule ids),
`--plugin` (repeatable), `--baseline`, `--no-color`, `--quiet`, and threshold
overrides (`--chunk-size`, `--max-chunk-chars`, `--min-chunk-chars`,
`--embedding-token-limit`, `--cfi-threshold`). Exit codes: `0` success, `1`
fail-on triggered, `2` usage/path error.

### 4.8 Python API
- `analyze_path(path, config=None, *, baseline=None) -> Report`
- `analyze_paths(paths, config=None, *, baseline=None) -> Report`
- `analyze_chunks(chunks, config=None, *, source="chunks") -> Report` — the
  framework-agnostic bridge; accepts a list of strings or dicts. One-liners:
  - LangChain: `analyze_chunks([d.page_content for d in docs])`
  - LlamaIndex: `analyze_chunks([n.get_content() for n in nodes])`
- `compute_health(findings) -> HealthScore`
- Report renderers in `contextdoctor.reports`: `render_json/markdown/html/sarif/
  terminal/badge`.

### 4.9 Configuration
Auto-discovered from `.contextdoctor.json` or a `[tool.contextdoctor]` table in
`pyproject.toml` (walking up from the target), or passed via `--config`. Keys
include: `chunk_size`, `chunk_overlap`, `max_chunk_chars`, `min_chunk_chars`,
`embedding_token_limit`, `shingle_size`, `near_duplicate_threshold`,
`duplicate_pct_warning`, `max_chunks_per_heading`, `min_entity_freq`,
`cfi_warning_threshold`, `detect_secrets`, `detect_pii`,
`detect_encoding_artifacts`, `select`, `ignore`, `severity`, `plugins`,
`extensions`. Unknown keys are ignored (forward-compatible).

### 4.10 Adoption mechanisms
- **Baseline files** — freeze existing findings; only *new* ones are reported and
  affect the score. Coarse `rule + files` fingerprints survive edits/re-chunking.
- **Inline disable pragmas** — file-scoped `<!-- contextdoctor: disable=CTX007 -->`
  (comma lists supported) and `disable-all`, for legit cases like a doc that
  *shows* an example key.
- **Rule selection & severity** — `select`/`ignore` and per-rule `severity`
  overrides (config or CLI).

### 4.11 Plugin system (extensibility / the "moat")
A plugin is an `Analyzer` subclass that declares `provides_rules = [Rule(...)]`.
Its rules flow through the health score, **all** report formats, SARIF,
`contextdoctor rules`, and `--select`/`--ignore` — identical to built-in rules.
Three loading paths:
1. **Local `.py` file** — `--plugin ./my_rules.py` or `{"plugins": ["./my_rules.py"]}`.
2. **Importable module** — `my_pkg.rules` or `my_pkg.rules:MyAnalyzer`.
3. **Published package** — a `contextdoctor.analyzers` entry point (auto-discovered).

Loading is best-effort (a broken plugin warns and is skipped); built-in `CTX*`
ids cannot be silently overridden. A complete working example ships in
`examples/plugin/` (rule `PLH001`, flagging unfinished/placeholder content).

### 4.12 CI / ecosystem integrations
- **GitHub Action** (`action.yml`, composite) — run in a workflow, emit SARIF.
- **pre-commit hook** (`.pre-commit-hooks.yaml`) — `id: contextdoctor`.
- **SARIF upload** — findings appear inline on pull requests.
- **GitHub Pages workflow** (`.github/workflows/pages.yml`) — deploys the playground.
- **CI matrix** (`.github/workflows/ci.yml`) — Python 3.11/3.12/3.13 on Linux,
  plus Windows and macOS; runs ruff (lint + format) and pytest, and a CLI smoke test.

### 4.13 Browser playground (WASM)
`playground/index.html` is a **static, zero-server, zero-upload** page that runs
the **entire ContextDoctor engine in the browser** via Pyodide (WebAssembly). Paste
chunks (blank-line blocks or JSON/JSONL), click Analyze, and it renders the
self-contained HTML report inline. It works precisely because the core has zero
dependencies. *(Verified end-to-end in a real browser: Pyodide loaded, the wheel
installed via micropip, `import contextdoctor` succeeded, and an analysis produced a
correct, redacted report entirely client-side.)*

---

## 5. Architecture (module map)

```
contextdoctor/
├── cli.py            # argparse CLI: analyze / compare / baseline / rules
├── config.py         # thresholds + config discovery (.json / pyproject.toml)
├── engine.py         # discover → chunk → analyze → pragmas → filter → baseline → score → Report
├── scoring.py        # the Context Health Score
├── baseline.py       # freeze findings; report only new ones
├── plugins.py        # load custom analyzers/rules (files, modules, entry points)
├── models.py         # Chunk, Document, Finding, Report, Severity, Location
├── chunking/         # structure-aware chunker (paragraphs, tables, code fences, overlap)
├── parsers/          # discovery + md/txt/html/json/jsonl/csv/pdf loaders + inline pragmas
├── analyzers/        # chunk_stats, duplicates, tables, headings, content_quality, fragmentation
├── rules/            # rule catalogue + registration (id, severity, description, recommendation)
├── reports/          # terminal / json / markdown / html / sarif / badge
└── utils/            # text, hashing (MinHash), NLP, ANSI, secret/PII/encoding patterns
```

Pipeline is a straight line and never touches the network:
**discover files → build chunks → run analyzers over the shared corpus → apply
pragmas/select/severity/baseline → compute score → render.**

---

## 6. Packaging & tech facts

- `pyproject.toml`, setuptools build backend; console entry point
  `contextdoctor = contextdoctor.cli:main`; also runnable as `python -m contextdoctor`.
- Ships `py.typed` (PEP 561) — fully type-hinted.
- Runtime deps: `[]`. Optional extras: `pdf` (`pypdf>=4`), `dev`
  (`pytest`, `pytest-cov`, `ruff`).
- Ruff configured (lint rules E/F/I/UP/B/C4/SIM/RUF; line length 100).

---

## 7. Testing & verification (what was actually checked)

- **115 unit/integration tests pass**, **93% line coverage** (ruff lint + format
  clean across 52 files).
- **Full CLI matrix** exercised: every command/format/flag; exit codes verified
  (`--fail-on error` → 1, missing path/arg → 2, else 0).
- **All 6 output formats** content-validated on all example corpora: JSON/SARIF/
  badge parse and are structurally correct; SARIF carries rule metadata for every
  finding; Markdown/terminal/HTML contain required sections.
- **Security properties verified across every renderer:**
  - **XSS/HTML injection** — a `<script>`/`onerror=` chunk is escaped, never raw.
  - **Secret/PII redaction** — the raw value never appears in json/md/html/sarif/
    terminal, confirmed both in code output and in the **live browser DOM**.
- **HTML reports verified visually in a real browser** (via a served gallery):
  DOM-inspected score/grade/badges/rule-ids/histogram/CFI for clean, messy,
  risky, and mixed-format corpora; checked **dark + light** themes and
  **desktop + mobile** responsive layouts.
- **Playground verified end-to-end in WebAssembly**: built a wheel, served it,
  Pyodide booted, `import contextdoctor` succeeded, and an in-browser analysis
  produced score 76/C with the expected rules and **redaction intact**. A
  narrow-viewport layout bug (report iframe collapsing to 152px) was found and
  fixed (now 86vh / ~608px) and re-verified from source.

---

## 8. Known limitations (stated honestly for cross-verification)

- **CFI is experimental and unvalidated** — regex proper-noun entities; a signal,
  not ground truth.
- **Token estimate is a heuristic** (`chars/4` blend), not a real tokenizer, so
  CTX010 is approximate.
- **Health-score weights are hand-tuned**, not calibrated against labeled corpora.
- **Secrets/PII are regex-based** → false positives/negatives; no entropy
  detection; PII patterns are **US-centric** (SSN, US phone shapes).
- **Baseline fingerprints are coarse** (`rule + files`); moving a finding to a new
  file reads as "new." No location-level baseline.
- **Pragmas are file-scoped** (no line-scoped disable yet).
- **Table/HTML/CSV parsing are heuristic** (HTML has no readability main-content
  extraction; CSV assumes row 1 is the header).
- **Duplicate detection is O(n²)** with a MinHash prefilter (fine to ~1.5k chunks;
  no full LSH banding beyond that).

## 9. Release status

The code is feature-complete for v0.1 and **release-ready**. The repository lives
at **https://github.com/pranavbelhekar01/ContextLint** (private at time of
writing) and all in-code URLs point there. A tag-triggered **PyPI publish
workflow** (`.github/workflows/release.yml`, OIDC Trusted Publishing) is included;
see `RELEASING.md` for the step-by-step.

Still pending until the first public release: the package is **not on PyPI yet**,
so `pip install contextdoctor`, the GitHub Action reference, the pre-commit `rev`,
and the playground's in-browser install only work **after** `v0.1.0` is published
and the repo is public.

---

## 10. Verify it yourself

From the repository root (Python 3.11+):

```bash
# Install (editable) with dev tools
pip install -e ".[dev]"

# Prove: no network / no LLM imports anywhere in the package
python - <<'PY'
import ast, pathlib
bad=[]
for f in pathlib.Path("contextdoctor").rglob("*.py"):
    for n in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
        if isinstance(n,(ast.Import,ast.ImportFrom)):
            names=[a.name for a in n.names] if isinstance(n,ast.Import) else [n.module or ""]
            for nm in names:
                if any(nm==m or nm.startswith(m+".") for m in
                       ("requests","urllib.request","socket","openai","anthropic","httpx","boto3")):
                    bad.append((f.name,nm))
print("network/LLM imports:", bad or "NONE")
PY

# Prove: zero runtime dependencies
python -c "import tomllib; print('deps =', tomllib.load(open('pyproject.toml','rb'))['project']['dependencies'])"

# Tests + coverage (expect 115 passed, ~93%)
pytest --cov=contextdoctor -q
ruff check . && ruff format --check .

# The 10 rules
contextdoctor rules

# All output formats on the demo corpora
contextdoctor analyze ./examples/messy_docs                       # terminal + health score
contextdoctor analyze ./examples/messy_docs --format json
contextdoctor analyze ./examples/messy_docs --format html   -o report.html
contextdoctor analyze ./examples/messy_docs --format sarif  -o results.sarif
contextdoctor analyze ./examples/risky_docs --format json          # CTX007/008/009, values redacted
contextdoctor analyze ./examples/mixed_formats                     # html + csv + jsonl parsers
contextdoctor analyze ./examples/pragma_demo                       # CTX007 suppressed by inline pragma

# Compare, baseline, plugin
contextdoctor compare ./examples/messy_docs ./examples/clean_docs
contextdoctor baseline ./examples/messy_docs -o bl.json
contextdoctor analyze ./examples/messy_docs --baseline bl.json     # 0 new findings
contextdoctor analyze ./examples/messy_docs \
  --plugin examples/plugin/contextdoctor_placeholder_plugin.py     # custom rule PLH001

# Confirm no raw secret leaks in any format
python - <<'PY'
from contextdoctor import analyze_chunks
from contextdoctor.reports import render_json, render_html, render_sarif, render_markdown
r = analyze_chunks(["OPENAI_API_KEY=sk-LEAKTESTABCDEFGHIJKLMNOP1234567890"])
for f in (render_json, render_html, render_sarif, render_markdown):
    assert "sk-LEAKTESTABCDEFGHIJKLMNOP1234567890" not in f(r)
print("secret never appears in any rendered format: OK")
PY

# Try the playground locally (runs the whole engine in your browser via Pyodide)
python -m http.server -d playground 8000   # open http://localhost:8000
```

Expected demo scores (default config): `clean_docs` 100/A+, `messy_docs` 69/D,
`risky_docs` 80/B, `mixed_formats` 90/A, `pragma_demo` 100/A+.

---

*This document is exhaustive as of ContextDoctor v0.1.0. If any statement here does
not match the code in this repository, treat the code as the source of truth.*
