"""
Novelty Scorer

Calculates novelty scores for events and patterns to detect
when the system has learned enough.
"""

import logging
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque
import math

logger = logging.getLogger(__name__)


@dataclass
class NoveltyResult:
    """Result of novelty calculation."""
    score: float  # 0.0 = completely familiar, 1.0 = completely novel
    similar_patterns: List[str]
    explanation: str
    timestamp: datetime = field(default_factory=datetime.now)


class NoveltyScorer:
    """
    Scores the novelty of incoming events and patterns.
    
    Uses embedding similarity and pattern frequency to determine
    how "new" a pattern is relative to existing learnings.
    """
    
    def __init__(
        self,
        similarity_threshold: float = 0.85,
        recency_weight: float = 0.3,
        frequency_weight: float = 0.3,
        window_size: int = 1000,
    ):
        """
        Initialize the novelty scorer.
        
        Args:
            similarity_threshold: Threshold for considering patterns similar
            recency_weight: Weight for recency in novelty calculation
            frequency_weight: Weight for frequency in novelty calculation
            window_size: Number of patterns to keep in memory
        """
        self.similarity_threshold = similarity_threshold
        self.recency_weight = recency_weight
        self.frequency_weight = frequency_weight
        self.window_size = window_size
        
        self._patterns: deque = deque(maxlen=window_size)
        self._pattern_counts: Dict[str, int] = {}
        self._embedding_cache: Dict[str, List[float]] = {}
        
        logger.info("NoveltyScorer initialized")
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between vectors."""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        
        dot = sum(a * b for a, b in zip(vec1, vec2))
        mag1 = sum(a * a for a in vec1) ** 0.5
        mag2 = sum(b * b for b in vec2) ** 0.5
        
        if mag1 == 0 or mag2 == 0:
            return 0.0
        return dot / (mag1 * mag2)
    
    def _find_similar_patterns(
        self,
        embedding: List[float],
        top_k: int = 5
    ) -> List[Tuple[str, float]]:
        """Find patterns similar to the given embedding."""
        similarities = []
        
        for pattern_id, pattern_embedding in self._embedding_cache.items():
            sim = self._cosine_similarity(embedding, pattern_embedding)
            if sim >= self.similarity_threshold:
                similarities.append((pattern_id, sim))
        
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]
    
    def _calculate_recency_factor(self, pattern_id: str) -> float:
        """Calculate recency factor (0 = old, 1 = recent)."""
        # Check when pattern was last seen
        for i, (pid, _, ts) in enumerate(reversed(self._patterns)):
            if pid == pattern_id:
                # More recent = lower factor (less novel)
                position_factor = i / max(len(self._patterns), 1)
                return position_factor
        
        # Never seen = fully novel
        return 1.0
    
    def _calculate_frequency_factor(self, pattern_id: str) -> float:
        """Calculate frequency factor (high freq = less novel)."""
        count = self._pattern_counts.get(pattern_id, 0)
        total = sum(self._pattern_counts.values()) or 1
        
        # Inverse frequency: rare = novel
        frequency = count / total
        return 1.0 - min(frequency * 10, 1.0)  # Scale and cap
    
    def score_pattern(
        self,
        pattern_id: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> NoveltyResult:
        """
        Calculate novelty score for a pattern.
        
        Args:
            pattern_id: Unique identifier for the pattern
            embedding: Vector embedding of the pattern
            metadata: Optional metadata about the pattern
            
        Returns:
            NoveltyResult with score and explanation
        """
        similar = self._find_similar_patterns(embedding)
        
        if not similar:
            # Completely novel pattern
            novelty_score = 1.0
            explanation = "No similar patterns found"
        else:
            # Calculate base similarity (inverse = novelty)
            max_similarity = similar[0][1]
            similarity_novelty = 1.0 - max_similarity
            
            # Factor in recency
            recency_factor = self._calculate_recency_factor(pattern_id)
            
            # Factor in frequency
            frequency_factor = self._calculate_frequency_factor(pattern_id)
            
            # Weighted combination
            base_weight = 1.0 - self.recency_weight - self.frequency_weight
            novelty_score = (
                base_weight * similarity_novelty +
                self.recency_weight * recency_factor +
                self.frequency_weight * frequency_factor
            )
            
            explanation = (
                f"Similar to {len(similar)} patterns "
                f"(max sim: {max_similarity:.2f}), "
                f"recency: {recency_factor:.2f}, "
                f"freq: {frequency_factor:.2f}"
            )
        
        # Record pattern
        self._patterns.append((pattern_id, embedding, datetime.now()))
        self._embedding_cache[pattern_id] = embedding
        self._pattern_counts[pattern_id] = self._pattern_counts.get(pattern_id, 0) + 1
        
        return NoveltyResult(
            score=min(max(novelty_score, 0.0), 1.0),
            similar_patterns=[s[0] for s in similar],
            explanation=explanation,
        )
    
    def get_average_novelty(self, window: int = 100) -> float:
        """Get average novelty score over recent patterns."""
        # This would be calculated from stored novelty scores
        # For now, return based on pattern diversity
        if not self._patterns:
            return 1.0
        
        recent = list(self._patterns)[-window:]
        unique_patterns = len(set(p[0] for p in recent))
        diversity = unique_patterns / len(recent)
        
        return diversity
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get scorer statistics."""
        return {
            "total_patterns": len(self._patterns),
            "unique_patterns": len(set(p[0] for p in self._patterns)),
            "cached_embeddings": len(self._embedding_cache),
            "avg_novelty": self.get_average_novelty(),
        }
