"""Input parsers: turn files on disk into :class:`~contextdoctor.models.Document`."""

from contextdoctor.parsers.loader import discover_files, load_document

__all__ = ["discover_files", "load_document"]
