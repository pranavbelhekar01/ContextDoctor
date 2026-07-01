# FAQ & Troubleshooting

## General

### Is ContextDoctor a replacement for RAGAS / DeepEval / TruLens?

No — it's **complementary**. Those tools are runtime, LLM-as-judge evaluators that
score the *answer* after retrieval. ContextDoctor is a **static, pre-retrieval**
linter that checks your corpus/chunks *before* you index. Use both: lint with
ContextDoctor before indexing, evaluate with RAGAS/DeepEval after answering.

### Does it call an LLM or send my data anywhere?

No. ContextDoctor is fully offline and deterministic — no API keys, no network
calls, no telemetry. The [browser playground](https://pranavbelhekar01.github.io/ContextDoctor/)
runs entirely client-side (WebAssembly); nothing is uploaded.

### Will it print my secrets or PII?

Never. CTX007/CTX008 report only the *type* of thing found (e.g. "OpenAI API key",
"email") — the matched value is always redacted and never written to any output
format.

## Usage

### It found "chunk-too-small" (CTX002) on every CSV/JSONL row — is that wrong?

For CSV/JSONL, each row/line is one chunk, so short records are expected. Raise
`min_chunk_chars`, or `--ignore CTX002` for those inputs.

### CTX010 fires but my embedding model handles long inputs.

The default `embedding_token_limit` is 512 (common for open models). Set it to your
model's real limit — e.g. `--embedding-token-limit 8192` for OpenAI
`text-embedding-3-*` — or in config.

### The CFI (CTX006) seems noisy.

The CFI is **experimental** and uses lightweight regex entity extraction. Treat it
as a signal to inspect, not a hard failure. Raise `cfi_warning_threshold`, or
`--ignore CTX006` if you don't want it gating anything yet.

### A document legitimately contains an example API key.

Opt that file out with an inline pragma at the top of the file:

```markdown
<!-- contextdoctor: disable=CTX007 -->
```

### How do I turn this on for a big existing corpus without drowning in findings?

Use a **baseline** — freeze today's findings and fail only on new ones:

```bash
contextdoctor baseline ./docs
contextdoctor analyze ./docs --baseline .contextdoctor-baseline.json --fail-on warning
```

### How do I only run some rules?

`--select CTX001,CTX003` runs only those; `--ignore CTX006` skips one. Or set
`select` / `ignore` in config.

## Inputs & formats

### PDF support isn't working.

PDF is optional to keep the core dependency-free. Install it:
`pip install "contextdoctor[pdf]"`. Unreadable/corrupt PDFs are skipped with a
warning rather than failing the run.

### My JSON export isn't being read as chunks.

ContextDoctor probes common shapes and text keys (`text`, `content`,
`page_content`, `body`, `chunk`, `passage`) and containers (`chunks`, `documents`,
`nodes`, `data`, `items`, `passages`). If yours differs, transform it to a list of
strings, or feed the chunks directly via `analyze_chunks()`.

## CI & exit codes

### The command exits 0 even though there are findings.

By design — reporting is separate from gating. Add `--fail-on error` (or
`warning`) to make CI fail. Exit codes: `0` success, `1` fail-on met, `2` usage/path
error.

## Windows

### The terminal report shows odd characters or errors on Windows.

ContextDoctor reconfigures stdout to UTF-8 and falls back to ASCII glyphs on
legacy consoles. If you still see issues, use a modern terminal (Windows Terminal)
or `--format json` / `--format markdown`.

## Contributing & support

- **Docs:** start at the [docs index](index.md).
- **Bugs / features:** open an issue on
  [GitHub](https://github.com/pranavbelhekar01/ContextDoctor/issues).
- **Contributing:** see [CONTRIBUTING.md](../CONTRIBUTING.md).
- **Security:** see [SECURITY.md](../SECURITY.md).
