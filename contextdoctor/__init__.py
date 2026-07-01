"""ContextDoctor: a static analyzer for RAG systems and context engineering workflows.

ContextDoctor inspects documents, chunks, and knowledge bases and reports
structural, chunking, and context-quality issues *before* an LLM is ever
invoked. It runs fully offline, with zero API keys and zero cloud dependencies.
"""

from __future__ import annotations

__version__ = "0.1.1"

from contextdoctor.config import Config
from contextdoctor.engine import analyze_chunks, analyze_path, analyze_paths
from contextdoctor.models import (
    AnalyzerResult,
    Chunk,
    Document,
    Finding,
    Location,
    Report,
    Severity,
)
from contextdoctor.scoring import compute_health

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
    "analyze_chunks",
    "analyze_path",
    "analyze_paths",
    "compute_health",
]
