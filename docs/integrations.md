# Integrations

ContextDoctor is designed to run where you already work: your CI, your git hooks,
your RAG framework, and GitHub code scanning.

## GitHub Actions

A composite Action ships with the repo. It installs ContextDoctor, runs it, and
(by default) emits SARIF so findings appear inline on pull requests.

```yaml
# .github/workflows/context.yml
name: ContextDoctor
on: [pull_request]

jobs:
  contextdoctor:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pranavbelhekar01/ContextDoctor@v0.1
        with:
          path: ./knowledge_base
          fail-on: error          # optional: fail the job on error-level findings
      - uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: contextdoctor.sarif
```

**Action inputs:** `path` (default `.`), `format` (default `sarif`), `output`
(default `contextdoctor.sarif`), `fail-on` (empty = never fail), `version` (pin a
version specifier, e.g. `==0.1.1`), and `extra-args` (any extra CLI flags).

### Plain CI (no Action)

```yaml
- run: pip install contextdoctor
- run: contextdoctor analyze ./knowledge_base --fail-on error
```

## pre-commit

A hook is shipped in `.pre-commit-hooks.yaml`. Add to your
`.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/pranavbelhekar01/ContextDoctor
    rev: v0.1.1
    hooks:
      - id: contextdoctor
```

By default it runs on changed `.md`/`.txt`/`.json` files and fails on error-level
findings. Override with `args:` if you want different behavior.

## SARIF & GitHub code scanning

`--format sarif` emits SARIF 2.1.0. Upload it with
`github/codeql-action/upload-sarif` (see the Action example above) and each finding
becomes an annotation on the offending file in the PR, with the rule id, message,
and recommendation. Works from public and private repos.

## LangChain

Lint the chunks your splitter actually produced, before you embed them:

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter
from contextdoctor import analyze_chunks

docs = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100).split_documents(raw_docs)
report = analyze_chunks([d.page_content for d in docs])

if report.health_score < 80:
    raise SystemExit(f"Context health too low: {report.health_score}/100")
```

## LlamaIndex

```python
from llama_index.core.node_parser import SentenceSplitter
from contextdoctor import analyze_chunks

nodes = SentenceSplitter(chunk_size=512).get_nodes_from_documents(documents)
report = analyze_chunks([n.get_content() for n in nodes])
print(report.health_score, report.health_grade)
```

## Ingestion-pipeline test

Put a hard assertion in your ingestion test suite so a chunking regression fails
the build:

```python
def test_context_health():
    report = analyze_chunks(load_production_chunks())
    assert report.health_score >= 85, f"{report.health_score}/100: {[f.rule_id for f in report.findings]}"
```

## Badges

Generate a shields.io badge for your README:

```bash
contextdoctor analyze ./docs --format badge
```

This prints a shields.io **endpoint** JSON (host it and point a badge at it) plus a
ready-to-paste static Markdown snippet.
