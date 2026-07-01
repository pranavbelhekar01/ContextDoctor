# ContextDoctor Documentation

**A static analyzer for RAG systems and context-engineering workflows — "ESLint
for your context."** ContextDoctor inspects your documents, chunks, and knowledge
bases and reports structural, chunking, and content-quality problems *before* an
LLM is ever invoked. It runs fully offline, with zero API keys and zero runtime
dependencies.

```bash
pip install contextdoctor
contextdoctor analyze ./docs
```

## Start here

| Guide | What it covers |
| --- | --- |
| [Getting Started](getting-started.md) | Install, run your first analysis, and read the report. |
| [User Guide](user-guide.md) | Inputs, workflows, the health score, compare, baseline, and pragmas. |
| [Rules Reference](rules.md) | Every rule (CTX001–CTX010): what it means, why it matters, how to fix. |
| [Configuration](configuration.md) | Every config key, its default, and how to set it. |
| [CLI Reference](cli.md) | Every command and flag, with exit codes. |
| [Python API](api.md) | `analyze_chunks`, `analyze_path`, the `Report` object, and renderers. |
| [Plugins](plugins.md) | Write and ship custom rules. |
| [Integrations](integrations.md) | CI (GitHub Actions), pre-commit, SARIF, LangChain, LlamaIndex. |
| [FAQ & Troubleshooting](faq.md) | Common questions and fixes. |
| [Technical Overview](OVERVIEW.md) | A single verifiable description of the whole tool. |

## Where ContextDoctor fits

RAG-evaluation tools (RAGAS, TruLens, DeepEval, Phoenix) are **runtime,
LLM-as-judge, post-retrieval** — they score the *answer* and need a running
pipeline, test queries, and API calls. ContextDoctor owns the missing
**pre-retrieval, pre-index** layer: it checks whether your knowledge base was
worth retrieving from in the first place.

> **Lint with ContextDoctor before you index; evaluate with RAGAS/DeepEval after
> you answer.**

## Key properties

- **Fully offline** — no API keys, no cloud, no model downloads.
- **Zero runtime dependencies** — standard-library Python 3.11+.
- **Deterministic** — same input, same report, every time.
- **Extensible** — a plugin API for your own rules.

## Try it with zero install

The [browser playground](https://pranavbelhekar01.github.io/ContextDoctor/) runs
the entire analyzer in WebAssembly — paste chunks, get a score, nothing uploaded.
