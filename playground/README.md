# ContextDoctor Playground

A zero-install, zero-server web playground: paste your chunks, get a **Context
Health Score** and a full report — **entirely in the browser**. It runs the real
`contextdoctor` engine compiled to WebAssembly via
[Pyodide](https://pyodide.org/), so **nothing is uploaded** anywhere.

This works precisely because ContextDoctor has **zero runtime dependencies** — the
whole analyzer is pure Python and drops straight into Pyodide.

## Run it locally

It's a single static file. Serve the folder with any static server:

```bash
python -m http.server -d playground 8000
# open http://localhost:8000
```

The page installs ContextDoctor at runtime with `micropip.install("contextdoctor")`,
so it needs the package to be published on PyPI (or reachable as a wheel URL).

### Before the package is on PyPI

Build a wheel and point `micropip` at it:

```bash
pip install build && python -m build   # produces dist/contextdoctor-*.whl
python -m http.server 8000             # serve repo root so dist/ is reachable
```

Then change the install line in `index.html` from
`micropip.install("contextdoctor")` to
`micropip.install("http://localhost:8000/dist/contextdoctor-0.1.0-py3-none-any.whl")`.

## Deploy it

The included [`../.github/workflows/pages.yml`](../.github/workflows/pages.yml)
publishes this folder to GitHub Pages on every push to `main`, giving you a
public URL like `https://<org>.github.io/contextdoctor/`. Share that link and
anyone can score their corpus in one click — the top-of-funnel growth lever.
