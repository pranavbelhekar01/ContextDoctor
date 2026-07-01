# Rules Reference

ContextDoctor ships ten built-in rules. Each finding names a rule id (`CTX001`…),
a severity, a message, and a recommendation. This page explains what each rule
detects, why it matters for retrieval quality, how it's detected, and how to fix
or tune it.

List them from the CLI anytime:

```bash
contextdoctor rules
```

**Severities:** `error` (2) > `warning` (1) > `info` (0). Use `--fail-on` to gate
CI on a severity, and `--select` / `--ignore` / `severity` to control which rules
run and at what level (see [Configuration](configuration.md)).

| Rule | Name | Default severity | Category |
| --- | --- | --- | --- |
| [CTX001](#ctx001--chunk-too-large) | chunk-too-large | warning | chunk-stats |
| [CTX002](#ctx002--chunk-too-small) | chunk-too-small | warning | chunk-stats |
| [CTX003](#ctx003--duplicate-content) | duplicate-content | warning | duplicates |
| [CTX004](#ctx004--broken-table) | broken-table | **error** | tables |
| [CTX005](#ctx005--heading-fragmentation) | heading-fragmentation | warning | headings |
| [CTX006](#ctx006--high-context-fragmentation) | high-context-fragmentation | warning *(experimental)* | fragmentation |
| [CTX007](#ctx007--secret-detected) | secret-detected | **error** | content-quality |
| [CTX008](#ctx008--pii-detected) | pii-detected | warning | content-quality |
| [CTX009](#ctx009--encoding-artifacts) | encoding-artifacts | warning | content-quality |
| [CTX010](#ctx010--exceeds-embedding-limit) | exceeds-embedding-limit | warning | chunk-stats |

---

## CTX001 · chunk-too-large

**Detects:** chunks whose character count exceeds `max_chunk_chars` (default 2000).

**Why it matters:** oversized chunks dilute retrieval relevance (one vector has to
represent too many ideas) and can overflow the model's usable context window.

**How to fix:** reduce your chunk size or add semantic split points (headings,
paragraphs). If you're auditing a JSON export, re-chunk upstream.

**Configure:** `max_chunk_chars`. **Disable:** `--ignore CTX001`.

---

## CTX002 · chunk-too-small

**Detects:** non-empty chunks smaller than `min_chunk_chars` (default 200).
Whitespace-only chunks are ignored.

**Why it matters:** fragments too small to carry standalone meaning waste retrieval
slots and can't answer questions on their own.

**How to fix:** merge tiny chunks with their neighbours, or increase chunk size.
For CSV/JSONL where each row is a chunk, this is expected — consider raising
`min_chunk_chars` or `--ignore CTX002` for those inputs.

**Configure:** `min_chunk_chars`.

---

## CTX003 · duplicate-content

**Detects:** exact and near-duplicate chunks.
- **Exact:** SHA-256 of normalized (whitespace-collapsed, lowercased) text.
- **Near:** word n-gram shingles (size `shingle_size`, default 5) compared with a
  MinHash prefilter and exact Jaccard, flagged at/above `near_duplicate_threshold`
  (default 0.85).

**Why it matters:** duplicates crowd out diverse results, bias retrieval toward
repeated passages, and inflate index size and cost.

**How to fix:** deduplicate before indexing; merge templated/boilerplate content.

**Configure:** `near_duplicate_threshold`, `shingle_size`, `duplicate_pct_warning`.

---

## CTX004 · broken-table

**Detects:** a markdown table split across a chunk boundary — one chunk ends with
table rows and the next begins with table rows that have no header separator.

**Why it matters:** a table split across chunks loses its header row and column
meaning, so the rows become unusable at retrieval time.

**How to fix:** keep tables intact within one chunk — use a structure-aware
splitter, or increase chunk size for table-heavy documents.

**Severity:** `error` by default (structural corruption).

---

## CTX005 · heading-fragmentation

**Detects:** a single section (identified by its heading) spanning more than
`max_chunks_per_heading` chunks (default 5). Applies to Markdown that
ContextDoctor chunked itself.

**Why it matters:** when one heading spans many chunks, individual chunks lose the
section's framing and are harder to interpret in isolation.

**How to fix:** adopt **parent-child / hierarchical retrieval** — attach the parent
heading to each child chunk, or retrieve the parent section as additional context.

**Configure:** `max_chunks_per_heading`.

---

## CTX006 · high-context-fragmentation

> ⚠️ **Experimental metric.** Treat it as a signal to inspect, not a hard failure.

**Detects:** a high **Context Fragmentation Index (CFI)** — related information
scattered across distant chunks.

**How the CFI is computed (v0.1):**
1. Extract lightweight local entities per chunk (proper-noun phrases + acronyms)
   via regex — no models, no network.
2. For each entity appearing in ≥ `min_entity_freq` distinct chunks, take the
   sorted chunk indices where it appears.
3. Compute the **mean gap** between consecutive appearances, normalized by corpus
   size `(N − 1)` → per-entity fragmentation in `[0, 1]`.
4. **CFI = occurrence-weighted mean** of per-entity fragmentation.

Scale: `0.0` = coherent, `1.0` = fragmented. Triggers at `cfi_warning_threshold`
(default 0.6).

**Why it matters:** if a topic is introduced in one place and only revisited far
away, a retriever pulling the middle will miss the full picture.

**How to fix:** re-order or re-chunk so discussions of the same entity stay close;
add overlap or summaries so retrieval can reassemble context.

**Configure:** `cfi_warning_threshold`, `min_entity_freq`, `max_entities_reported`.

---

## CTX007 · secret-detected

**Detects:** embedded credentials/API keys — OpenAI, Anthropic, AWS, GitHub,
Google, Slack, Stripe keys, private-key blocks, JWTs, and generic
`api_key = "…"` assignments — via regular expressions.

**Why it matters:** a secret in your corpus gets stored in your vector database and
can be surfaced verbatim to users at retrieval time. This is a real data-leak
vector.

**How to fix:** remove the secret from the source, **rotate it**, and re-index. If a
document legitimately *shows* an example key, opt that file out with an
[inline pragma](user-guide.md#inline-disable-pragmas): `<!-- contextdoctor: disable=CTX007 -->`.

**Severity:** `error`. **Redaction:** the matched value is **never** printed — only
its type (e.g. "OpenAI API key").

**Configure:** `detect_secrets` (set `false` to disable the scan entirely).

---

## CTX008 · pii-detected

**Detects:** personally identifiable information — email addresses, phone numbers,
US Social Security Numbers, and credit-card-shaped numbers validated with the
Luhn checksum.

**Why it matters:** PII embedded in chunks can leak to users through retrieval and
creates compliance risk.

**How to fix:** redact or mask PII before indexing, or gate the affected documents.

**Redaction:** values are never printed — only the type and a count.

**Configure:** `detect_pii`. **Note:** patterns are US-centric (SSN, US phone
shapes) and regex-based, so expect some false positives/negatives.

---

## CTX009 · encoding-artifacts

**Detects:** mojibake (e.g. `Ã©`, `â€™`), Unicode replacement characters (`�`), and
stray control characters — signs of a broken text-extraction step.

**Why it matters:** garbled text degrades embeddings and makes retrieved passages
unreadable.

**How to fix:** re-extract the source with the correct encoding (usually UTF-8).

**Configure:** `detect_encoding_artifacts`.

---

## CTX010 · exceeds-embedding-limit

**Detects:** chunks whose estimated token count exceeds `embedding_token_limit`
(default 512).

**Why it matters:** many popular embedding models (e5, bge, MiniLM, and others)
**silently truncate** input beyond ~512 tokens — the tail of an oversized chunk is
never embedded and becomes unsearchable. This is a subtle, common bug.

**How to fix:** reduce chunk size, or set `embedding_token_limit` to match your
model's real limit (e.g. 8192 for OpenAI `text-embedding-3-*`).

**Configure:** `embedding_token_limit`. The token count is a heuristic estimate,
not a real tokenizer, so treat it as approximate.

---

## Plugin rules

Custom rules from [plugins](plugins.md) appear here too, tagged `(plugin)` in
`contextdoctor rules`, and flow through the health score, all report formats,
SARIF, and `--select` / `--ignore` exactly like built-in rules.
