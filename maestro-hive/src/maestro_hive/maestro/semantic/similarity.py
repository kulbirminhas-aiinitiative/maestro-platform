"""
Similarity Calculator

Implements AC-2: Cosine similarity threshold for matching

Provides similarity calculation and threshold-based filtering.

Epic: MD-2498
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum
import numpy as np
import logging

logger = logging.getLogger(__name__)


class ConfidenceLevel(str, Enum):
    """Confidence level based on similarity score"""
    VERY_HIGH = "very_high"   # >0.9
    HIGH = "high"             # 0.7-0.9
    MEDIUM = "medium"         # 0.5-0.7
    LOW = "low"               # 0.3-0.5
    NONE = "none"             # <0.3


@dataclass
class SimilarityThreshold:
    """
    Configurable similarity thresholds.

    AC-2 Implementation: Defines thresholds for match classification.
    """
    very_high: float = 0.9
    high: float = 0.7
    medium: float = 0.5
    low: float = 0.3

    def get_confidence(self, score: float) -> ConfidenceLevel:
        """
        Get confidence level for a similarity score.

        Args:
            score: Cosine similarity score (0-1)

        Returns:
            ConfidenceLevel based on thresholds
        """
        if score >= self.very_high:
            return ConfidenceLevel.VERY_HIGH
        elif score >= self.high:
            return ConfidenceLevel.HIGH
        elif score >= self.medium:
            return ConfidenceLevel.MEDIUM
        elif score >= self.low:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.NONE

    def is_match(self, score: float, min_confidence: ConfidenceLevel = ConfidenceLevel.HIGH) -> bool:
        """
        Check if score meets minimum confidence.

        Args:
            score: Similarity score
            min_confidence: Minimum required confidence level

        Returns:
            True if score meets threshold
        """
        confidence = self.get_confidence(score)
        confidence_order = [
            ConfidenceLevel.NONE,
            ConfidenceLevel.LOW,
            ConfidenceLevel.MEDIUM,
            ConfidenceLevel.HIGH,
            ConfidenceLevel.VERY_HIGH
        ]
        return confidence_order.index(confidence) >= confidence_order.index(min_confidence)

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary"""
        return {
            "very_high": self.very_high,
            "high": self.high,
            "medium": self.medium,
            "low": self.low
        }


class SimilarityCalculator:
    """
    Similarity calculation engine.

    AC-2 Implementation: Cosine similarity with configurable thresholds.

    Features:
    - Cosine similarity calculation
    - Batch similarity computation
    - Threshold-based filtering
    - Similarity ranking
    """

    def __init__(self, thresholds: Optional[SimilarityThreshold] = None):
        """
        Initialize calculator.

        Args:
            thresholds: Similarity thresholds (uses defaults if None)
        """
        self.thresholds = thresholds or SimilarityThreshold()

    def cosine_similarity(
        self,
        vec1: np.ndarray,
        vec2: np.ndarray
    ) -> float:
        """
        Calculate cosine similarity between two vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Cosine similarity (0-1)
        """
        # Normalize vectors
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        # Calculate cosine similarity
        similarity = np.dot(vec1, vec2) / (norm1 * norm2)

        # Clamp to [0, 1] to handle floating point errors
        return float(max(0.0, min(1.0, similarity)))

    def similarity_to_many(
        self,
        query_vec: np.ndarray,
        candidate_vecs: List[np.ndarray]
    ) -> List[float]:
        """
        Calculate similarity of query to multiple candidates.

        Args:
            query_vec: Query embedding vector
            candidate_vecs: List of candidate vectors

        Returns:
            List of similarity scores
        """
        return [
            self.cosine_similarity(query_vec, candidate)
            for candidate in candidate_vecs
        ]

    def batch_similarity_matrix(
        self,
        vectors: List[np.ndarray]
    ) -> np.ndarray:
        """
        Calculate pairwise similarity matrix.

        Args:
            vectors: List of embedding vectors

        Returns:
            NxN similarity matrix
        """
        n = len(vectors)
        matrix = np.zeros((n, n))

        # Stack vectors for efficient computation
        stacked = np.array(vectors)

        # Normalize all vectors
        norms = np.linalg.norm(stacked, axis=1, keepdims=True)
        norms[norms == 0] = 1  # Avoid division by zero
        normalized = stacked / norms

        # Compute similarity matrix
        matrix = np.dot(normalized, normalized.T)

        # Clamp values
        matrix = np.clip(matrix, 0.0, 1.0)

        return matrix

    def rank_by_similarity(
        self,
        query_vec: np.ndarray,
        candidate_vecs: List[np.ndarray],
        top_k: Optional[int] = None,
        min_score: float = 0.0
    ) -> List[Tuple[int, float, ConfidenceLevel]]:
        """
        Rank candidates by similarity to query.

        Args:
            query_vec: Query embedding
            candidate_vecs: Candidate embeddings
            top_k: Maximum number of results (None for all)
            min_score: Minimum similarity score

        Returns:
            List of (index, score, confidence) tuples, sorted by score descending
        """
        scores = self.similarity_to_many(query_vec, candidate_vecs)

        # Create ranked results
        results = []
        for idx, score in enumerate(scores):
            if score >= min_score:
                confidence = self.thresholds.get_confidence(score)
                results.append((idx, score, confidence))

        # Sort by score descending
        results.sort(key=lambda x: x[1], reverse=True)

        # Apply top_k limit
        if top_k is not None:
            results = results[:top_k]

        return results

    def filter_by_threshold(
        self,
        scores: List[float],
        min_confidence: ConfidenceLevel = ConfidenceLevel.HIGH
    ) -> List[Tuple[int, float]]:
        """
        Filter scores by minimum confidence level.

        Args:
            scores: List of similarity scores
            min_confidence: Minimum required confidence

        Returns:
            List of (index, score) tuples that meet threshold
        """
        results = []
        for idx, score in enumerate(scores):
            if self.thresholds.is_match(score, min_confidence):
                results.append((idx, score))
        return results

    def find_best_match(
        self,
        query_vec: np.ndarray,
        candidate_vecs: List[np.ndarray],
        min_confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    ) -> Optional[Tuple[int, float, ConfidenceLevel]]:
        """
        Find the best matching candidate.

        Args:
            query_vec: Query embedding
            candidate_vecs: Candidate embeddings
            min_confidence: Minimum required confidence

        Returns:
            (index, score, confidence) of best match, or None if no match
        """
        ranked = self.rank_by_similarity(query_vec, candidate_vecs, top_k=1)

        if not ranked:
            return None

        idx, score, confidence = ranked[0]

        if not self.thresholds.is_match(score, min_confidence):
            return None

        return (idx, score, confidence)

    def get_similarity_stats(
        self,
        scores: List[float]
    ) -> Dict[str, Any]:
        """
        Get statistics about similarity scores.

        Args:
            scores: List of similarity scores

        Returns:
            Statistics dictionary
        """
        if not scores:
            return {
                "count": 0,
                "mean": 0.0,
                "std": 0.0,
                "min": 0.0,
                "max": 0.0,
                "confidence_distribution": {}
            }

        arr = np.array(scores)

        # Count by confidence level
        distribution = {level.value: 0 for level in ConfidenceLevel}
        for score in scores:
            conf = self.thresholds.get_confidence(score)
            distribution[conf.value] += 1

        return {
            "count": len(scores),
            "mean": float(np.mean(arr)),
            "std": float(np.std(arr)),
            "min": float(np.min(arr)),
            "max": float(np.max(arr)),
            "confidence_distribution": distribution
        }
