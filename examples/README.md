# ContextLint examples

Runnable datasets that demonstrate what ContextLint catches. All analysis is
fully offline.

| Directory | What it shows | Rules triggered |
| --- | --- | --- |
| [`clean_docs/`](clean_docs) | Well-structured, self-contained documentation. | _none_ — a clean bill of health |
| [`messy_docs/`](messy_docs) | Oversized & tiny chunks, duplicate passages, a table split across a JSON chunk boundary, and one giant heading section. | CTX001, CTX002, CTX003, CTX004, CTX005 |
| [`fragmented_kb/`](fragmented_kb) | A knowledge base where key systems are introduced at the top and only revisited at the very bottom, maximising fragmentation. Ships its own `.contextlint.json`. | CTX006 (experimental CFI) |

## Try them

```bash
# A clean corpus — no findings
contextlint analyze ./examples/clean_docs

# A messy corpus — structural findings across CTX001–CTX005
contextlint analyze ./examples/messy_docs

# High Context Fragmentation Index (experimental)
contextlint analyze ./examples/fragmented_kb

# Machine-readable / shareable output
contextlint analyze ./examples/messy_docs --format json
contextlint analyze ./examples/messy_docs --format markdown -o report.md
```
