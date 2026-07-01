# Writing a ContextLint plugin

A plugin is just an `Analyzer` subclass that (optionally) declares the rules it
emits. ContextLint registers those rules automatically, so they flow through the
health score, every report format, SARIF, `contextlint rules`, and
`--select` / `--ignore` — exactly like the built-in `CTX*` rules.

[`contextlint_placeholder_plugin.py`](contextlint_placeholder_plugin.py) is a
complete, working example: it adds rule **`PLH001`**, which flags unfinished
content (`TODO`, `FIXME`, `lorem ipsum`, …) that shouldn't be in a knowledge base.

## Try it

```bash
# Point --plugin at the file, then analyze anything:
contextlint analyze ./examples/messy_docs \
  --plugin examples/plugin/contextlint_placeholder_plugin.py

# See the plugin's rule listed alongside the built-ins:
contextlint rules --plugin examples/plugin/contextlint_placeholder_plugin.py
```

## The three ways to load a plugin

| Effort | How | Spec |
| --- | --- | --- |
| Lowest | Local `.py` file | `--plugin path/to/rules.py` or `{"plugins": ["path/to/rules.py"]}` |
| Medium | Importable module | `--plugin my_pkg.rules` or `my_pkg.rules:MyAnalyzer` |
| Published | Entry point (auto-discovered) | see below |

For a distributable package, expose an entry point in your `pyproject.toml`:

```toml
[project.entry-points."contextlint.analyzers"]
placeholder = "contextlint_placeholder_plugin:PlaceholderAnalyzer"
```

Once installed, ContextLint discovers it with no configuration at all.

## The contract

```python
from contextlint.analyzers import AnalysisContext, Analyzer
from contextlint.models import AnalyzerResult, Location, Severity
from contextlint.rules import Rule

class MyAnalyzer(Analyzer):
    name = "my_rules"
    title = "My custom rules"
    provides_rules = [Rule(id="MYP001", name="my-rule", category="custom",
                           default_severity=Severity.WARNING,
                           description="...", recommendation="...")]

    def analyze(self, ctx: AnalysisContext) -> AnalyzerResult:
        findings = []
        for chunk in ctx.chunks:
            ...  # inspect chunk.text, chunk.source_file, chunk.token_estimate, ...
            findings.append(self._finding("MYP001", "message", locations=[Location(...)]))
        return self._result(metrics={}, findings=findings)
```

Plugin loading is best-effort and offline: a broken plugin prints a warning and
is skipped rather than crashing the run. Built-in `CTX*` rule ids cannot be
silently overridden.
