# CLI Reference

```
contextdoctor [--version] {analyze,compare,baseline,rules} ...
```

Run any command with `--help` for its options. ContextDoctor runs fully offline —
no API keys, no cloud, no LLM calls.

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Success. |
| `1` | `--fail-on` threshold met (findings at or above that severity exist). |
| `2` | Usage error, or a path was not found. |

---

## `analyze`

Analyze one or more files/directories as a single merged corpus.

```
contextdoctor analyze <path...> [options]
```

| Option | Description |
| --- | --- |
| `-f`, `--format {terminal,json,markdown,html,sarif,badge}` | Output format (default: `terminal`). |
| `-o`, `--output FILE` | Write the report to a file instead of stdout. |
| `-c`, `--config FILE` | Config file (`.json` or `pyproject.toml`). Auto-discovered if omitted. |
| `--fail-on {error,warning,info}` | Exit `1` if any finding is at or above this severity. |
| `--select CTX001,CTX003` | Run **only** these rule ids. |
| `--ignore CTX006` | Skip these rule ids. |
| `--plugin SPEC` | Load a plugin analyzer (`.py` path or module spec). Repeatable. |
| `--baseline FILE` | Suppress findings recorded in this baseline; report only new ones. |
| `--no-color` | Disable ANSI colour. |
| `--quiet` | Suppress stdout messages when using `--output`. |
| `--chunk-size N` | Target chunk size in characters (raw inputs). |
| `--chunk-overlap N` | Chunk overlap in characters (raw inputs). |
| `--max-chunk-chars N` | CTX001 threshold. |
| `--min-chunk-chars N` | CTX002 threshold. |
| `--embedding-token-limit N` | CTX010 threshold. |
| `--cfi-threshold F` | CTX006 CFI warning threshold (0..1). |

**Examples:**

```bash
contextdoctor analyze ./docs
contextdoctor analyze ./docs ./more_docs --format json
contextdoctor analyze export.json --format sarif -o results.sarif --fail-on error
contextdoctor analyze ./docs --ignore CTX006 --select CTX001,CTX003
contextdoctor analyze ./docs --embedding-token-limit 8192
contextdoctor analyze ./docs --plugin ./my_rules.py
```

---

## `compare`

Compare two corpora / chunking strategies side by side.

```
contextdoctor compare <before> <after> [options]
```

| Option | Description |
| --- | --- |
| `-c`, `--config FILE` | Config applied to **both** sides for a fair comparison. |
| `-f`, `--format {terminal,json}` | Output format (default: `terminal`). |
| `--no-color` | Disable ANSI colour. |

Shows health score, findings count, duplicate %, and CFI for both, with deltas and
a verdict.

```bash
contextdoctor compare recursive.json semantic.json
contextdoctor compare ./v1_docs ./v2_docs --format json
```

---

## `baseline`

Record current findings to a baseline file so CI only fails on new ones.

```
contextdoctor baseline <path...> [options]
```

| Option | Description |
| --- | --- |
| `-o`, `--output FILE` | Baseline file to write (default: `.contextdoctor-baseline.json`). |
| `-c`, `--config FILE` | Config file. |

```bash
contextdoctor baseline ./docs
contextdoctor analyze ./docs --baseline .contextdoctor-baseline.json --fail-on warning
```

---

## `rules`

List all rules (CTX001–CTX010 plus any plugin rules).

```
contextdoctor rules [--plugin SPEC]
```

| Option | Description |
| --- | --- |
| `--plugin SPEC` | Also list rules from this plugin. Repeatable. |

```bash
contextdoctor rules
contextdoctor rules --plugin ./my_rules.py
```

---

## Global

| Option | Description |
| --- | --- |
| `--version` | Print the version and exit. |
| `-h`, `--help` | Show help for the program or a subcommand. |

You can also invoke the tool as a module: `python -m contextdoctor ...`.
