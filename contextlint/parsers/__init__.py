"""Input parsers: turn files on disk into :class:`~contextlint.models.Document`."""

from contextlint.parsers.loader import discover_files, load_document

__all__ = ["discover_files", "load_document"]
