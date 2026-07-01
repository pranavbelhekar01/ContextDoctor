# Contributing to ContextDoctor

Thanks for your interest in improving ContextDoctor! This project is a fully
offline, zero-dependency static analyzer for RAG systems, and contributions of all
kinds are welcome — bug reports, docs, new rules, parsers, and plugins.

## Development setup

Requires **Python 3.11+**.

```bash
git clone https://github.com/pranavbelhekar01/ContextDoctor
cd ContextDoctor
python -m venv .venv && . .venv/Scripts/activate   # or source .venv/bin/activate
pip install -e ".[dev]"
```

## The core loop

```bash
pytest -q                 # run the test suite (should stay green)
ruff check .              # lint
ruff format .             # format
```

Please keep all three green before opening a PR. The project targets Python 3.11,
3.12, and 3.13 on Linux, macOS, and Windows (see `.github/workflows/ci.yml`).

## Ground rules (what keeps ContextDoctor, ContextDoctor)

1. **No runtime dependencies.** The core must import only the standard library.
   Optional features may use extras (e.g. `[pdf]`), gated with a clear error when
   missing.
2. **Fully offline & deterministic.** No network calls, no randomness or wall-clock
   in analysis paths, no telemetry. Same input → same report.
3. **Never echo secrets or PII.** Detectors report only the *type* of a match.
4. **Type hints + tests** for new code.

## Project layout

```
contextdoctor/
├── cli.py            # argparse CLI
├── engine.py         # discover → chunk → analyze → filter → score → Report
├── analyzers/        # one module per concern (chunk_stats, duplicates, ...)
├── rules/            # rule catalogue + registration
├── reports/          # terminal / json / markdown / html / sarif / badge
├── parsers/          # file discovery + format loaders + pragmas
├── chunking/         # the structure-aware chunker
└── utils/            # text, hashing, nlp, ansi, patterns
```

See [docs/OVERVIEW.md](docs/OVERVIEW.md) for the full technical map.

## Adding a rule

1. Add rule metadata to `contextdoctor/rules/registry.py`.
2. Emit findings from a new or existing analyzer (subclass `Analyzer`, use
   `self._finding(...)`).
3. Register the analyzer in `contextdoctor/analyzers/__init__.py`.
4. Add tests and an example under `examples/` that triggers it.
5. Document it in [docs/rules.md](docs/rules.md).

Prefer shipping niche or opinionated rules as **plugins** (see
[docs/plugins.md](docs/plugins.md)) rather than built-ins.

## Pull requests

- Keep PRs focused; describe the motivation and the change.
- Include tests and doc updates.
- Add a `CHANGELOG.md` entry under the unreleased/next version.
- Ensure `pytest`, `ruff check`, and `ruff format --check` pass.

## Commit messages

Short imperative subject line; explain the "why" in the body when it isn't obvious.

## Reporting bugs & requesting features

Open an issue with the provided templates. For security issues, **do not** open a
public issue — see [SECURITY.md](SECURITY.md).

## License

By contributing, you agree that your contributions are licensed under the project's
[MIT License](LICENSE).
