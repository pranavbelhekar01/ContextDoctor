# Getting Started

This guide takes you from zero to a full analysis in about five minutes.

## 1. Install

```bash
pip install contextdoctor
```

Requires **Python 3.11+**. There are no other runtime dependencies. Optional PDF
support: `pip install "contextdoctor[pdf]"`.

Verify it:

```bash
contextdoctor --version
contextdoctor --help
```

## 2. Run your first analysis

Point ContextDoctor at a file or a directory. It works on Markdown, plain text,
HTML, JSON/JSONL chunk exports, and CSV/TSV.

```bash
contextdoctor analyze ./docs
```

You'll get a terminal report with a **Context Health Score**, chunk statistics,
the experimental Context Fragmentation Index, and a list of findings — each with a
severity, a message, a recommendation, and file/chunk locations.

```text
  ContextDoctor  ·  static analysis for RAG

  Context Health Score
    69/100  D  █████████████████░░░░░░░  poor

  Issues  1 error  5 warning  0 info

  Findings
    ✖ CTX004 [broken-table]
      A markdown table in export.json is split between chunk 2 and chunk 3.
      → Keep tables intact within a single chunk...
```

## 3. Read the report

- **Context Health Score (0–100 + A–F grade):** one number summarizing corpus
  health. See [the health score](user-guide.md#the-context-health-score).
- **Chunk statistics:** size distribution (min/median/mean/p95/max), overlap %,
  and duplicate %.
- **Context Fragmentation Index (CFI):** experimental — how scattered related
  information is. [Details](rules.md#ctx006--high-context-fragmentation).
- **Findings:** each is a rule violation. Every rule is documented in the
  [Rules Reference](rules.md), including how to fix it.

## 4. Analyze the chunks your pipeline produced

If you already chunk documents in code (LangChain, LlamaIndex, a custom
splitter), hand ContextDoctor those exact chunks so the report reflects *your*
chunking:

```python
from contextdoctor import analyze_chunks

# LangChain
report = analyze_chunks([d.page_content for d in documents])

# LlamaIndex
report = analyze_chunks([n.get_content() for n in nodes])

print(report.health_score, report.health_grade)
for f in report.findings:
    print(f.rule_id, f.severity.value, f.message)
```

## 5. Get a shareable or machine-readable report

```bash
contextdoctor analyze ./docs --format html   -o report.html   # self-contained visual report
contextdoctor analyze ./docs --format json                     # machine-readable
contextdoctor analyze ./docs --format sarif  -o results.sarif  # GitHub code scanning
contextdoctor analyze ./docs --format markdown -o report.md
```

## 6. Gate it in CI

Fail the build when problems appear:

```bash
contextdoctor analyze ./docs --fail-on error      # exit 1 on any error-level finding
contextdoctor analyze ./docs --fail-on warning    # exit 1 on any warning or worse
```

See [Integrations](integrations.md) for a ready-made GitHub Action and pre-commit
hook.

## Next steps

- [User Guide](user-guide.md) — inputs, chunking, compare, baseline, pragmas.
- [Rules Reference](rules.md) — understand and fix every finding.
- [Configuration](configuration.md) — tune thresholds to your embedding model.
