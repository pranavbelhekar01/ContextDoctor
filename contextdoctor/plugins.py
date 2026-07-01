"""Plugin loading: discover custom analyzers/rules from packages or local files.

Three ways to add rules, in increasing order of packaging effort:

1. **A local file** — point ``plugins`` at a ``.py`` path in your repo::

       {"plugins": ["./rules/my_rules.py"]}

2. **An importable module** — ``"my_package.rules"`` or ``"my_package.rules:MyAnalyzer"``.

3. **A published package** — expose an entry point so it's picked up automatically::

       [project.entry-points."contextdoctor.analyzers"]
       my-rules = "contextdoctor_plugin_myrules:MyAnalyzer"

A plugin is just an :class:`~contextdoctor.analyzers.base.Analyzer` subclass (or a
module/object exposing an ``ANALYZERS`` list of them). Each analyzer may declare
``provides_rules = [Rule(...)]`` and those are registered automatically.

Plugin loading is best-effort: a broken plugin emits a warning and is skipped
rather than crashing the whole run. Everything stays local and offline.
"""

from __future__ import annotations

import importlib
import importlib.util
import warnings
from importlib import metadata
from pathlib import Path

from contextdoctor.analyzers.base import Analyzer
from contextdoctor.rules import register_rule

ENTRY_POINT_GROUP = "contextdoctor.analyzers"


def _register_rules(cls: type[Analyzer]) -> None:
    for rule in getattr(cls, "provides_rules", []) or []:
        register_rule(rule)


def _coerce_analyzers(obj: object) -> list[type[Analyzer]]:
    """Turn a loaded object (class, module, or ANALYZERS holder) into analyzers."""
    if isinstance(obj, type) and issubclass(obj, Analyzer) and obj is not Analyzer:
        return [obj]
    declared = getattr(obj, "ANALYZERS", None)
    if declared:
        return [
            a
            for a in declared
            if isinstance(a, type) and issubclass(a, Analyzer) and a is not Analyzer
        ]
    # Fall back to scanning a module's namespace for Analyzer subclasses.
    found: list[type[Analyzer]] = []
    for value in vars(obj).values() if hasattr(obj, "__dict__") else []:
        if isinstance(value, type) and issubclass(value, Analyzer) and value is not Analyzer:
            found.append(value)
    return found


def _load_from_file(path: Path) -> object:
    spec = importlib.util.spec_from_file_location(f"contextdoctor_plugin_{path.stem}", path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise ImportError(f"cannot load plugin file: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_spec(spec: str) -> object:
    """Resolve a plugin spec to a class or module object."""
    if spec.endswith(".py") or ("/" in spec and Path(spec).exists()):
        return _load_from_file(Path(spec))
    if ":" in spec:
        module_name, attr = spec.split(":", 1)
        module = importlib.import_module(module_name)
        return getattr(module, attr)
    return importlib.import_module(spec)


def load_module_analyzers(specs: list[str]) -> list[type[Analyzer]]:
    """Load analyzers from module/file specs, registering their rules."""
    found: list[type[Analyzer]] = []
    for spec in specs:
        try:
            obj = _load_spec(spec)
        except Exception as exc:  # plugin isolation: never let one plugin crash the run
            warnings.warn(f"ContextDoctor: failed to load plugin '{spec}': {exc}", stacklevel=2)
            continue
        classes = _coerce_analyzers(obj)
        if not classes:
            warnings.warn(f"ContextDoctor: no Analyzer found in plugin '{spec}'", stacklevel=2)
        for cls in classes:
            _register_rules(cls)
            found.append(cls)
    return found


def discover_entry_point_analyzers() -> list[type[Analyzer]]:
    """Discover analyzers published under the ``contextdoctor.analyzers`` group."""
    found: list[type[Analyzer]] = []
    try:
        entry_points = metadata.entry_points(group=ENTRY_POINT_GROUP)
    except Exception:  # pragma: no cover - importlib.metadata quirks
        return found
    for ep in entry_points:
        try:
            obj = ep.load()
        except Exception as exc:  # plugin isolation: never let one plugin crash the run
            warnings.warn(f"ContextDoctor: failed to load plugin '{ep.name}': {exc}", stacklevel=2)
            continue
        for cls in _coerce_analyzers(obj):
            _register_rules(cls)
            found.append(cls)
    return found


def load_all(config) -> list[type[Analyzer]]:
    """All plugin analyzers: entry points + config ``plugins``, de-duplicated."""
    analyzers = discover_entry_point_analyzers()
    analyzers += load_module_analyzers(list(getattr(config, "plugins", ()) or ()))
    seen: set[type[Analyzer]] = set()
    unique: list[type[Analyzer]] = []
    for cls in analyzers:
        if cls not in seen:
            seen.add(cls)
            unique.append(cls)
    return unique
