"""Configuration for analysis thresholds and chunking behaviour.

All values are plain data with sensible, opinionated defaults. A config can be
loaded from a JSON file (``--config``) or a ``[tool.contextlint]`` table in
``pyproject.toml``. Unknown keys are ignored so configs stay forward-compatible.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any


@dataclass
class Config:
    """Tunable thresholds for ContextLint's analyzers and chunker."""

    # --- Chunking (applied when chunking raw .md / .txt inputs) ---
    chunk_size: int = 1200  # target characters per chunk
    chunk_overlap: int = 120  # characters of overlap carried between chunks

    # --- Chunk statistics (CTX001 / CTX002 / CTX010) ---
    max_chunk_chars: int = 2000  # chunks larger than this are "too large"
    min_chunk_chars: int = 200  # non-trivial chunks smaller than this are "too small"
    embedding_token_limit: int = 512  # CTX010: many embedding models truncate beyond this

    # --- Content quality (CTX007 / CTX008 / CTX009) ---
    detect_secrets: bool = True  # scan for embedded credentials / API keys
    detect_pii: bool = True  # scan for emails, phone numbers, SSNs, card numbers
    detect_encoding_artifacts: bool = True  # scan for mojibake / control chars

    # --- Duplicate detection (CTX003) ---
    shingle_size: int = 5  # word-shingle length for near-duplicate comparison
    near_duplicate_threshold: float = 0.85  # Jaccard similarity to flag a near-duplicate
    duplicate_pct_warning: float = 10.0  # % of duplicated chunks that triggers a warning

    # --- Heading continuity (CTX005) ---
    max_chunks_per_heading: int = 5  # a section spanning more chunks is over-fragmented

    # --- Context Fragmentation Index / CFI (CTX006, experimental) ---
    min_entity_freq: int = 2  # entity must appear in at least this many chunks
    cfi_warning_threshold: float = 0.6  # CFI at/above this triggers a warning
    max_entities_reported: int = 8  # top fragmented entities to surface

    # --- Rule selection & severity ---
    select: tuple[str, ...] = ()  # if non-empty, ONLY these rule ids run
    ignore: tuple[str, ...] = ()  # these rule ids are dropped
    severity: dict[str, str] = field(default_factory=dict)  # rule_id -> severity override

    # --- Plugins (custom analyzers/rules; module specs or local .py paths) ---
    plugins: tuple[str, ...] = ()

    # --- File discovery ---
    extensions: tuple[str, ...] = (".md", ".markdown", ".txt", ".json")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def _field_names(cls) -> set[str]:
        return {f.name for f in fields(cls)}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Config:
        """Build a Config from a dict, ignoring unknown keys."""
        allowed = cls._field_names()
        tuple_fields = {"extensions", "select", "ignore", "plugins"}
        clean: dict[str, Any] = {}
        for key, value in data.items():
            if key not in allowed:
                continue
            if key in tuple_fields and isinstance(value, list):
                value = tuple(value)
            clean[key] = value
        return cls(**clean)

    @classmethod
    def load(cls, path: str | Path) -> Config:
        """Load config from a JSON file, or a pyproject.toml with [tool.contextlint]."""
        path = Path(path)
        text = path.read_text(encoding="utf-8")
        if path.suffix == ".toml" or path.name == "pyproject.toml":
            import tomllib

            data = tomllib.loads(text)
            data = data.get("tool", {}).get("contextlint", {})
        else:
            data = json.loads(text)
        return cls.from_dict(data)

    @classmethod
    def discover(cls, start: str | Path) -> Config:
        """Look for a config file near ``start``; fall back to defaults.

        Search order (first hit wins): ``.contextlint.json`` then
        ``pyproject.toml`` (with a ``[tool.contextlint]`` table), walking up
        from ``start`` to the filesystem root.
        """
        start = Path(start).resolve()
        base = start if start.is_dir() else start.parent
        for directory in [base, *base.parents]:
            candidate = directory / ".contextlint.json"
            if candidate.is_file():
                return cls.load(candidate)
            pyproject = directory / "pyproject.toml"
            if pyproject.is_file():
                try:
                    import tomllib

                    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
                except Exception:  # pragma: no cover - malformed toml
                    data = {}
                if data.get("tool", {}).get("contextlint"):
                    return cls.from_dict(data["tool"]["contextlint"])
        return cls()
