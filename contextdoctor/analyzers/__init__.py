"""Analyzers turn a corpus of chunks into metrics and findings."""

from contextdoctor.analyzers.base import AnalysisContext, Analyzer
from contextdoctor.analyzers.chunk_stats import ChunkStatsAnalyzer
from contextdoctor.analyzers.content_quality import ContentQualityAnalyzer
from contextdoctor.analyzers.duplicates import DuplicateAnalyzer
from contextdoctor.analyzers.fragmentation import FragmentationAnalyzer
from contextdoctor.analyzers.headings import HeadingAnalyzer
from contextdoctor.analyzers.tables import TableAnalyzer

#: Analyzers run in this order; report sections follow the same order.
DEFAULT_ANALYZERS: list[type[Analyzer]] = [
    ChunkStatsAnalyzer,
    DuplicateAnalyzer,
    TableAnalyzer,
    HeadingAnalyzer,
    ContentQualityAnalyzer,
    FragmentationAnalyzer,
]

__all__ = [
    "DEFAULT_ANALYZERS",
    "AnalysisContext",
    "Analyzer",
    "ChunkStatsAnalyzer",
    "ContentQualityAnalyzer",
    "DuplicateAnalyzer",
    "FragmentationAnalyzer",
    "HeadingAnalyzer",
    "TableAnalyzer",
]
