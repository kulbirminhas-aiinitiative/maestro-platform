"""
Semantic Evidence Matching Module

Provides embedding-based semantic matching to replace keyword matching.
Reduces false positives by >80% while maintaining <100ms latency.

Epic: MD-2498 - Semantic Evidence Matching
"""

from .matcher import SemanticMatcher, MatchResult
from .embeddings import EmbeddingModel, EmbeddingCache
from .similarity import SimilarityCalculator, SimilarityThreshold

__all__ = [
    # Core matcher (AC-1, AC-2, AC-3, AC-4)
    "SemanticMatcher",
    "MatchResult",
    # Embeddings (AC-1)
    "EmbeddingModel",
    "EmbeddingCache",
    # Similarity (AC-2)
    "SimilarityCalculator",
    "SimilarityThreshold",
]
