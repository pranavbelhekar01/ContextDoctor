# Configuration Reference

ContextDoctor is opinionated but tunable. Every setting has a sensible default;
override only what you need.

## Where configuration comes from

In order of precedence (later wins):

1. **Defaults** (built in).
2. **A discovered config file** — the first of these found, walking up from the
   analyzed path:
   - `.contextdoctor.json`
   - a `pyproject.toml` containing a `[tool.contextdoctor]` table
3. **An explicit `--config <file>`** (`.json` or a `pyproject.toml`).
4. **CLI flags** (`--chunk-size`, `--max-chunk-chars`, `--select`, `--ignore`, …).

Unknown keys are ignored, so configs stay forward-compatible.

## Example config files

`.contextdoctor.json`:

```json
{
  "chunk_size": 1000,
  "max_chunk_chars": 1500,
  "min_chunk_chars": 150,
  "embedding_token_limit": 8192,
  "near_duplicate_threshold": 0.9,
  "cfi_warning_threshold": 0.5,
  "ignore": ["CTX006"],
  "severity": { "CTX002": "info" }
}
```

`pyproject.toml`:

```toml
[tool.contextdoctor]
max_chunk_chars = 1500
embedding_token_limit = 8192
ignore = ["CTX006"]
```

## All settings

### Chunking (raw `.md` / `.txt` / `.html` inputs only)

| Key | Type | Default | Meaning |
| --- | --- | --- | --- |
| `chunk_size` | int | `1200` | Target characters per chunk. |
| `chunk_overlap` | int | `120` | Characters of overlap carried between chunks. |

### Chunk statistics (CTX001 / CTX002 / CTX010)

| Key | Type | Default | Meaning |
| --- | --- | --- | --- |
| `max_chunk_chars` | int | `2000` | CTX001: chunks larger than this are "too large". |
| `min_chunk_chars` | int | `200` | CTX002: non-trivial chunks smaller than this are "too small". |
| `embedding_token_limit` | int | `512` | CTX010: flag chunks whose estimated tokens exceed this. Set to your embedding model's real limit. |

### Content quality (CTX007 / CTX008 / CTX009)

| Key | Type | Default | Meaning |
| --- | --- | --- | --- |
| `detect_secrets` | bool | `true` | CTX007: scan for embedded credentials / API keys. |
| `detect_pii` | bool | `true` | CTX008: scan for emails, phones, SSNs, card numbers. |
| `detect_encoding_artifacts` | bool | `true` | CTX009: scan for mojibake / control characters. |

### Duplicate detection (CTX003)

| Key | Type | Default | Meaning |
| --- | --- | --- | --- |
| `shingle_size` | int | `5` | Word n-gram length for near-duplicate comparison. |
| `near_duplicate_threshold` | float | `0.85` | Jaccard similarity at/above which a pair is a near-duplicate. |
| `duplicate_pct_warning` | float | `10.0` | Corpus-wide duplicate % that triggers a warning. |

### Heading continuity (CTX005)

| Key | Type | Default | Meaning |
| --- | --- | --- | --- |
| `max_chunks_per_heading` | int | `5` | A section spanning more chunks than this is over-fragmented. |

### Context Fragmentation Index (CTX006, experimental)

| Key | Type | Default | Meaning |
| --- | --- | --- | --- |
| `min_entity_freq` | int | `2` | An entity must appear in at least this many distinct chunks to count. |
| `cfi_warning_threshold` | float | `0.6` | CFI at/above this triggers CTX006. |
| `max_entities_reported` | int | `8` | Top fragmented entities to surface in the report. |

### Rule selection & severity

| Key | Type | Default | Meaning |
| --- | --- | --- | --- |
| `select` | list[str] | `[]` | If non-empty, **only** these rule ids run. |
| `ignore` | list[str] | `[]` | These rule ids are dropped. |
| `severity` | dict | `{}` | Per-rule severity override, e.g. `{"CTX006": "info"}`. Values: `error`, `warning`, `info`. |

### Plugins

| Key | Type | Default | Meaning |
| --- | --- | --- | --- |
| `plugins` | list[str] | `[]` | Custom analyzers to load: local `.py` paths or module specs (`pkg.mod` / `pkg.mod:Class`). See [Plugins](plugins.md). |

### File discovery

| Key | Type | Default | Meaning |
| --- | --- | --- | --- |
| `extensions` | list[str] | `.md .markdown .txt .json .jsonl .ndjson .html .htm .csv .tsv .pdf` | File extensions to analyze during directory traversal. |

## Tips

- **Match your embedding model.** The single most impactful setting is
  `embedding_token_limit` — set it to your model's real limit so CTX010 is
  meaningful (512 for many open models, 8192 for OpenAI `text-embedding-3-*`).
- **Per-directory configs.** A `.contextdoctor.json` in a subdirectory applies to
  analyses rooted there — handy when different corpora need different thresholds.
- **CI vs. local.** Keep defaults locally; in CI add `--fail-on` and a
  `--baseline` so only regressions break the build.
