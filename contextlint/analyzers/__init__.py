"""Analyzers turn a corpus of chunks into metrics and findings."""

from contextlint.analyzers.base import AnalysisContext, Analyzer
from contextlint.analyzers.chunk_stats import ChunkStatsAnalyzer
from contextlint.analyzers.content_quality import ContentQualityAnalyzer
from contextlint.analyzers.duplicates import DuplicateAnalyzer
from contextlint.analyzers.fragmentation import FragmentationAnalyzer
from contextlint.analyzers.headings import HeadingAnalyzer
from contextlint.analyzers.tables import TableAnalyzer

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
