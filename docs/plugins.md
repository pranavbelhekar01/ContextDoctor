# Writing Plugins (Custom Rules)

ContextDoctor is extensible. A plugin is just an `Analyzer` subclass that declares
the rules it emits. Its rules then flow through **everything** — the health score,
all report formats, SARIF, `contextdoctor rules`, and `--select` / `--ignore` —
exactly like the built-in `CTX*` rules.

A complete working example lives in
[`examples/plugin/`](https://github.com/pranavbelhekar01/ContextDoctor/tree/main/examples/plugin)
(rule `PLH001`, flagging unfinished/placeholder content).

## The contract

```python
from contextdoctor.analyzers import AnalysisContext, Analyzer
from contextdoctor.models import AnalyzerResult, Location, Severity
from contextdoctor.rules import Rule

class TodoAnalyzer(Analyzer):
    name = "todo"                 # unique short name (used to key metrics)
    title = "Unfinished content"  # shown as a report section title
    provides_rules = [            # registered automatically on load
        Rule(
            id="MYP001",
            name="unfinished-content",
            category="custom",
            default_severity=Severity.WARNING,
            description="Placeholder text found.",
            recommendation="Finish or remove it before indexing.",
        )
    ]

    def analyze(self, ctx: AnalysisContext) -> AnalyzerResult:
        findings = [
            self._finding(
                "MYP001",
                f"TODO marker in chunk {c.short_id}",
                locations=[Location(file=c.source_file, chunk_id=c.id, line=c.start_line)],
            )
            for c in ctx.chunks
            if "TODO" in c.text
        ]
        return self._result(metrics={"todo_chunks": len(findings)}, findings=findings)
```

### What you get

- `ctx.chunks` — every `Chunk` in the corpus (with `text`, `source_file`, `id`,
  `char_count`, `token_estimate`, `start_line`, …).
- `ctx.documents` — the parsed `Document`s (with `raw`, `kind`, `chunks`).
- `ctx.config` — the effective `Config` (read your own custom thresholds if you
  add them, or reuse existing ones).
- `self._finding(rule_id, message, *, recommendation=None, severity=None, locations=None, data=None)`
  — builds a `Finding`, pulling defaults from the registered rule.
- `self._result(metrics=..., findings=...)` — builds the `AnalyzerResult` to return.

## Loading a plugin

Three ways, in increasing order of packaging effort:

| How | Spec |
| --- | --- |
| **Local `.py` file** | `--plugin ./my_rules.py` or `{"plugins": ["./my_rules.py"]}` |
| **Importable module** | `--plugin my_pkg.rules` or `my_pkg.rules:TodoAnalyzer` |
| **Published package** (auto-discovered) | a `contextdoctor.analyzers` entry point |

```bash
contextdoctor analyze ./docs --plugin ./my_rules.py
contextdoctor rules --plugin ./my_rules.py     # see your rule listed, tagged (plugin)
```

Via config (`.contextdoctor.json`):

```json
{ "plugins": ["./my_rules.py"] }
```

### Publishing a plugin package

Expose an entry point in your `pyproject.toml`, and ContextDoctor discovers it
automatically once installed — no configuration needed by users:

```toml
[project.entry-points."contextdoctor.analyzers"]
my-rules = "contextdoctor_plugin_myrules:TodoAnalyzer"
```

A module may also export an `ANALYZERS = [Analyzer1, Analyzer2]` list instead of a
single class.

## Rules & guarantees

- **Rule ids** should be unique and not collide with `CTX*`. Built-in `CTX*` ids
  **cannot be silently overridden** by a plugin.
- Unknown rule ids still render — if you emit a finding for a rule you forgot to
  register, ContextDoctor synthesizes placeholder metadata rather than crashing.
- **Loading is best-effort**: a broken plugin prints a warning and is skipped; it
  never aborts the run.
- Keep plugins **offline and deterministic** to preserve ContextDoctor's
  guarantees.

## Testing your plugin

```python
from contextdoctor import analyze_chunks, Config

report = analyze_chunks(["hello TODO"], Config(plugins=["./my_rules.py"]))
assert any(f.rule_id == "MYP001" for f in report.findings)
```
