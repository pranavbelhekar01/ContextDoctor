# User Guide

An in-depth tour of everything ContextDoctor does. For a quick start see
[Getting Started](getting-started.md); for exact flags see the
[CLI Reference](cli.md).

## Inputs

ContextDoctor traverses directories recursively (skipping hidden files) and
understands many formats:

| Format | Extensions | How it's handled |
| --- | --- | --- |
| Markdown | `.md`, `.markdown` | Chunked by the structure-aware chunker. |
| Plain text | `.txt` | Chunked the same way. |
| HTML | `.html`, `.htm` | Scripts/styles/tags stripped, then chunked. |
| JSON | `.json` | Read as **pre-existing chunks** (your chunking, not ours). |
| JSONL / NDJSON | `.jsonl`, `.ndjson` | One chunk per line. |
| CSV / TSV | `.csv`, `.tsv` | One chunk per row (`header: value`). |
| PDF | `.pdf` | Optional (`pip install "contextdoctor[pdf]"`). |

**JSON shapes** are auto-detected — a list of strings, a list of objects, or a
container object:

```jsonc
["chunk one", "chunk two"]                    // list of strings
[{"text": "..."}, {"content": "..."}]          // list of objects
{"chunks": [{"page_content": "..."}]}          // container object
```

Recognized text keys: `text`, `content`, `chunk`, `page_content`, `body`,
`passage`. Recognized container keys: `chunks`, `documents`, `nodes`, `data`,
`items`, `passages`.

> **Two modes:** for `.md`/`.txt`/`.html`, ContextDoctor **chunks the text itself**;
> for JSON/JSONL/CSV, it reads **your** chunks so the report reflects your pipeline.

## Chunking (for raw text inputs)

When ContextDoctor chunks raw Markdown/text, it uses a structure-aware chunker
that keeps paragraphs, tables, and fenced code blocks intact where possible, packs
them up to `chunk_size` characters, and carries `chunk_overlap` characters between
chunks. Tune both in [configuration](configuration.md); they do not affect
pre-chunked JSON/CSV inputs.

## The Context Health Score

Every run produces a single **0–100 score with an A+…F grade**, computed
deterministically from the findings:

```
penalty = 15·(#errors) + 6·(#warnings) + 1.5·(#infos)
score   = round(100 · exp(-penalty / 120))     # clamped to [0, 100]
```

Grade bands: **A+** ≥97 · **A** ≥90 · **B** ≥80 · **C** ≥70 · **D** ≥60 · **F** <60.

It's stable across runs, easy to gate in CI, and easy to show off:

```bash
contextdoctor analyze ./docs --format badge   # shields.io endpoint JSON + a Markdown snippet
```

## Output formats

```bash
contextdoctor analyze ./docs                          # terminal (default)
contextdoctor analyze ./docs --format json            # machine-readable
contextdoctor analyze ./docs --format markdown -o report.md
contextdoctor analyze ./docs --format html   -o report.html   # self-contained, screenshot-friendly
contextdoctor analyze ./docs --format sarif  -o results.sarif # GitHub code scanning
contextdoctor analyze ./docs --format badge
```

The **HTML** report is a single file (inline CSS + SVG, no JS, no network): score
ring, KPI cards, severity bar, chunk-size histogram, CFI section, and findings.
It respects `prefers-color-scheme` (dark/light).

## Selecting and re-leveling rules

```bash
contextdoctor analyze ./docs --select CTX001,CTX003    # ONLY these rules
contextdoctor analyze ./docs --ignore CTX006           # skip these rules
```

Per-rule severity overrides go in config (see [Configuration](configuration.md)):

```json
{ "severity": { "CTX006": "info", "CTX002": "error" } }
```

## Comparing two corpora (A/B chunking)

Answer *"is recursive or semantic chunking better for my corpus?"* — statically,
no LLM:

```bash
contextdoctor compare recursive_export.json semantic_export.json
```

You get a side-by-side of health score, findings count, duplicate %, and CFI, with
deltas and a verdict. Add `--format json` for machine output.

## Baselines: adopt on an existing corpus

Turning a linter on a large knowledge base usually floods you with issues. A
**baseline** freezes today's findings so CI fails only on *new* ones:

```bash
contextdoctor baseline ./docs                                    # writes .contextdoctor-baseline.json
contextdoctor analyze ./docs --baseline .contextdoctor-baseline.json --fail-on warning
```

Suppressed findings don't count against the score. Fingerprints are coarse
(`rule + files`) so they survive edits and re-chunking; genuinely new problems
still surface.

## Inline disable pragmas

For legitimate cases — e.g. a doc that *shows* an example API key — opt a single
file out of specific rules. Pragmas are **file-scoped** and work in any comment
style:

```markdown
<!-- contextdoctor: disable=CTX007 -->        # disable one or more rules for this file
<!-- contextdoctor: disable=CTX003,CTX008 --> # comma-separated
<!-- contextdoctor: disable-all -->           # disable everything for this file
```

## Configuration discovery

ContextDoctor auto-discovers `.contextdoctor.json` or a `[tool.contextdoctor]`
table in `pyproject.toml`, walking up from the target path. Override with
`--config`. See the [Configuration Reference](configuration.md).

## Custom rules

Add your own rules with a plugin — a local `.py` file, an importable module, or a
published package. See the [Plugin Guide](plugins.md).

## Determinism & privacy

ContextDoctor is fully offline and deterministic: no network calls, no API keys,
no telemetry, and the same input always yields the same report. Detected secrets
and PII are **never** echoed — only their type is reported.
