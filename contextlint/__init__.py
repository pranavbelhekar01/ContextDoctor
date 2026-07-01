"""ContextLint: a static analyzer for RAG systems and context engineering workflows.

ContextLint inspects documents, chunks, and knowledge bases and reports
structural, chunking, and context-quality issues *before* an LLM is ever
invoked. It runs fully offline, with zero API keys and zero cloud dependencies.
"""

from __future__ import annotations

__version__ = "0.1.0"

from contextlint.config import Config
from contextlint.engine import analyze_path
from contextlint.models import (
    AnalyzerResult,
    Chunk,
    Document,
    Finding,
    Location,
    Report,
    Severity,
)

__all__ = [
    "AnalyzerResult",
    "Chunk",
    "Config",
    "Document",
    "Finding",
    "Location",
    "Report",
    "Severity",
    "__version__",
    "analyze_path",
]
