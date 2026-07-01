# ContextLint examples

Runnable datasets that demonstrate what ContextLint catches. All analysis is
fully offline.

| Directory | What it shows | Rules triggered |
| --- | --- | --- |
| [`clean_docs/`](clean_docs) | Well-structured, self-contained documentation. Scores 100/100. | _none_ — a clean bill of health |
| [`messy_docs/`](messy_docs) | Oversized & tiny chunks, duplicate passages, a table split across a JSON chunk boundary, one giant heading section, and a chunk over the embedding token limit. | CTX001, CTX002, CTX003, CTX004, CTX005, CTX010 |
| [`risky_docs/`](risky_docs) | A support log that leaked API keys, PII, and mojibake into the knowledge base. All detected values are redacted, never echoed. | CTX007, CTX008, CTX009 |
| [`fragmented_kb/`](fragmented_kb) | A knowledge base where key systems are introduced at the top and only revisited at the very bottom, maximising fragmentation. Ships its own `.contextlint.json`. | CTX006 (experimental CFI) |

## Try them

```bash
# A clean corpus — scores 100/100
contextlint analyze ./examples/clean_docs

# A messy corpus — structural findings + embedding-limit
contextlint analyze ./examples/messy_docs

# Secrets, PII, and encoding artifacts (redacted)
contextlint analyze ./examples/risky_docs

# High Context Fragmentation Index (experimental)
contextlint analyze ./examples/fragmented_kb

# Compare two corpora / chunking strategies
contextlint compare ./examples/messy_docs ./examples/clean_docs

# Shareable / machine-readable output
contextlint analyze ./examples/messy_docs --format html -o report.html
contextlint analyze ./examples/messy_docs --format sarif -o results.sarif
```
