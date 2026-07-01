# Releasing ContextDoctor

Publishing uses **PyPI Trusted Publishing (OIDC)** via
[`.github/workflows/release.yml`](.github/workflows/release.yml) — no API tokens
or stored secrets. Pushing a `vX.Y.Z` tag builds and publishes to PyPI; a manual
run publishes to TestPyPI first as a dry-run.

## One-time setup

1. **Make the GitHub repo usable by Actions**
   - The repo is `pranavbelhekar01/ContextDoctor`. It can stay private, but PyPI
     Trusted Publishing and the public playground/badges need it **public** for
     the full experience. Publishing itself works from a private repo.
   - Create two GitHub **Environments** (Settings → Environments): `pypi` and
     `testpypi`. (No secrets needed — OIDC handles auth.)

2. **Register the Trusted Publisher on PyPI** (and TestPyPI)
   - PyPI → your account → *Publishing* → *Add a pending publisher*:
     - PyPI Project Name: `contextdoctor`
     - Owner: `pranavbelhekar01`
     - Repository name: `ContextDoctor`
     - Workflow name: `release.yml`
     - Environment name: `pypi`
   - Repeat on **test.pypi.org** with Environment `testpypi`.

## Cut a release

```bash
# 0. Make sure everything is green locally
pytest -q && ruff check . && ruff format --check .

# 1. Dry-run to TestPyPI (Actions tab → Release → Run workflow), then verify:
pip install --index-url https://test.pypi.org/simple/ \
            --extra-index-url https://pypi.org/simple/ contextdoctor
contextdoctor --version

# 2. Tag and push -> publishes to real PyPI
git tag v0.1.0
git push origin v0.1.0
```

## After the first publish

- `pip install contextdoctor` now works — the playground's in-browser install,
  the pre-commit hook, and the GitHub Action all light up.
- The Action reference `pranavbelhekar01/ContextDoctor@v0.1` resolves once the tag
  exists (consider also moving a floating `v0.1` tag on each patch).
- Enable **GitHub Pages** (Settings → Pages → source: GitHub Actions) so
  `pages.yml` deploys the playground.
- Add badges to the README (PyPI version, CI status, license).

## Bumping the version

Update `version` in `pyproject.toml` **and** `__version__` in
`contextdoctor/__init__.py`, add a `CHANGELOG.md` section, then tag.
