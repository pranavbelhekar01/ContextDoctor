# Python API

Everything the CLI does is available as a library. Import from the top-level
`contextdoctor` package.

```python
from contextdoctor import (
    analyze_path, analyze_paths, analyze_chunks,
    compute_health, Config, Report, Finding, Chunk, Location, Severity,
)
```

## Entry points

### `analyze_chunks(chunks, config=None, *, source="chunks") -> Report`

The framework-agnostic entry point. Pass the exact chunks your pipeline produced —
a list of strings, or dicts with a recognized text key.

```python
from contextdoctor import analyze_chunks

report = analyze_chunks([d.page_content for d in documents])   # LangChain
report = analyze_chunks([n.get_content() for n in nodes])      # LlamaIndex
report = analyze_chunks([{"text": "..."}, {"content": "..."}]) # dicts
```

### `analyze_path(path, config=None, *, baseline=None) -> Report`

Analyze a single file or directory (recursive).

### `analyze_paths(paths, config=None, *, baseline=None) -> Report`

Analyze several files/directories as one merged corpus. `baseline` is a set of
fingerprints (see [Baselines](#baselines)).

```python
from contextdoctor import analyze_path, Config

report = analyze_path("./docs", Config(max_chunk_chars=1500))
```

### `compute_health(findings) -> HealthScore`

Compute the score/grade from a list of findings. Returns an object with
`.score` (int), `.grade` (str), `.label` (str).

## The `Config` object

A dataclass of all thresholds — see the [Configuration Reference](configuration.md)
for every field. Construct directly or load from a file:

```python
from contextdoctor import Config

cfg = Config(max_chunk_chars=1500, embedding_token_limit=8192, ignore=("CTX006",))
cfg = Config.load("./.contextdoctor.json")     # from JSON or pyproject.toml
cfg = Config.discover("./docs")                # walk up from a path
cfg = Config.from_dict({"chunk_size": 800})    # unknown keys ignored
```

## The `Report` object

| Attribute | Type | Description |
| --- | --- | --- |
| `root` | str | The analyzed path (or "N paths"). |
| `generated_at` | str | UTC ISO-8601 timestamp. |
| `files_analyzed` | int | Number of files. |
| `total_chunks` | int | Number of chunks. |
| `health_score` | int | 0–100. |
| `health_grade` | str | `A+`…`F`. |
| `health_label` | str | e.g. "excellent", "poor". |
| `baseline_suppressed` | int | Findings hidden by a baseline. |
| `findings` | list[Finding] | Sorted by severity then rule id. |
| `analyzers` | list[AnalyzerResult] | Per-analyzer output. |
| `metrics` | dict | Per-analyzer metrics (chunk_stats, duplicates, fragmentation, …). |
| `config` | dict | The effective config used. |

Methods: `report.counts_by_severity()` → `{"info": n, "warning": n, "error": n}`;
`report.has_at_least(Severity.ERROR)` → bool.

```python
print(report.health_score, report.health_grade)
print(report.counts_by_severity())
print(report.metrics["fragmentation"]["cfi"])
```

## The `Finding` object

| Attribute | Type | Description |
| --- | --- | --- |
| `rule_id` | str | e.g. `"CTX004"`. |
| `severity` | Severity | `INFO` / `WARNING` / `ERROR`. |
| `message` | str | Human-readable summary. |
| `recommendation` | str | How to fix it. |
| `locations` | list[Location] | Where it was found. |
| `experimental` | bool | True for experimental rules (CFI). |
| `data` | dict | Rule-specific structured data. |

`Severity` is a `str` enum with values `"info"`, `"warning"`, `"error"` and a
`.rank` (0/1/2). `Location` has `file`, `chunk_id`, `line`, `detail`, and a
`.render()` helper.

## Rendering reports

```python
from contextdoctor.reports import (
    render_json, render_markdown, render_html, render_sarif,
    render_terminal, render_badge, report_to_dict,
)

open("report.html", "w", encoding="utf-8").write(render_html(report))
data = report_to_dict(report)          # plain dict, JSON-serializable
text = render_terminal(report, color=False)
```

## Baselines

```python
from contextdoctor.baseline import save_baseline, load_baseline, fingerprint
from contextdoctor import analyze_path

first = analyze_path("./docs")
save_baseline(first, ".contextdoctor-baseline.json")

# Later: only new findings appear, and only they affect the score.
report = analyze_path("./docs", baseline=load_baseline(".contextdoctor-baseline.json"))
print(report.baseline_suppressed, "suppressed")
```

## A complete example

```python
from contextdoctor import analyze_chunks, Config, Severity
from contextdoctor.reports import render_html

chunks = [d.page_content for d in my_documents]
report = analyze_chunks(chunks, Config(embedding_token_limit=8192))

if report.has_at_least(Severity.ERROR):
    open("context-report.html", "w", encoding="utf-8").write(render_html(report))
    raise SystemExit(f"Context health {report.health_score}/100 — see context-report.html")
```
