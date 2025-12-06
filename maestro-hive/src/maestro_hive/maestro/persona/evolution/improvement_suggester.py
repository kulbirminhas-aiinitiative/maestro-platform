"""
Improvement Suggester for Persona Evolution.

EPIC: MD-2556
AC-1: Execution outcomes feed into persona improvement suggestions.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .models import (
    ExecutionOutcome,
    ImprovementSuggestion,
    SuggestionCategory,
    SuggestionStatus,
)

logger = logging.getLogger(__name__)


@dataclass
class SuggestionRule:
    """Rule for generating suggestions."""
    name: str
    category: SuggestionCategory
    condition: str  # Human-readable condition
    min_samples: int
    min_confidence: float


class ImprovementSuggester:
    """
    Generates improvement suggestions from execution outcomes.

    AC-1: Execution outcomes feed into persona improvement suggestions.
    """

    # Minimum samples needed before generating suggestions
    MIN_SAMPLE_SIZE = 10
    IDEAL_SAMPLE_SIZE = 50

    # Confidence decay half-life in days
    RECENCY_HALF_LIFE = 7

    def __init__(
        self,
        min_confidence: float = 0.6,
        quality_threshold: float = 80.0,
    ):
        """
        Initialize the suggester.

        Args:
            min_confidence: Minimum confidence to create suggestion
            quality_threshold: Target quality score threshold
        """
        self.min_confidence = min_confidence
        self.quality_threshold = quality_threshold
        self._suggestions: Dict[str, ImprovementSuggestion] = {}

        logger.info(f"ImprovementSuggester initialized (min_confidence={min_confidence})")

    def analyze_outcomes(
        self,
        persona_id: str,
        outcomes: List[ExecutionOutcome],
    ) -> List[ImprovementSuggestion]:
        """
        Analyze outcomes and generate improvement suggestions.

        Args:
            persona_id: Persona to analyze
            outcomes: Recent execution outcomes

        Returns:
            List of improvement suggestions
        """
        if len(outcomes) < self.MIN_SAMPLE_SIZE:
            logger.debug(f"Insufficient samples for {persona_id}: {len(outcomes)}")
            return []

        suggestions = []

        # Analyze different aspects
        suggestions.extend(self._analyze_quality(persona_id, outcomes))
        suggestions.extend(self._analyze_success_rate(persona_id, outcomes))
        suggestions.extend(self._analyze_error_patterns(persona_id, outcomes))
        suggestions.extend(self._analyze_performance(persona_id, outcomes))

        # Store and return
        for suggestion in suggestions:
            self._suggestions[suggestion.suggestion_id] = suggestion

        logger.info(f"Generated {len(suggestions)} suggestions for {persona_id}")
        return suggestions

    def _analyze_quality(
        self,
        persona_id: str,
        outcomes: List[ExecutionOutcome],
    ) -> List[ImprovementSuggestion]:
        """Analyze quality scores for improvements."""
        suggestions = []

        quality_scores = [o.quality_score for o in outcomes]
        avg_quality = sum(quality_scores) / len(quality_scores)

        # Check if quality is consistently below threshold
        if avg_quality < self.quality_threshold:
            low_quality_outcomes = [o for o in outcomes if o.quality_score < self.quality_threshold]
            confidence = self._calculate_confidence(
                len(low_quality_outcomes),
                len(outcomes),
                outcomes,
            )

            if confidence >= self.min_confidence:
                suggestions.append(ImprovementSuggestion(
                    suggestion_id=f"sug_{uuid.uuid4().hex[:12]}",
                    persona_id=persona_id,
                    category=SuggestionCategory.CAPABILITY,
                    description=f"Improve quality output (current avg: {avg_quality:.1f}, target: {self.quality_threshold})",
                    current_value=avg_quality,
                    suggested_value=self.quality_threshold,
                    confidence=confidence,
                    evidence_outcomes=[f"out_{o.persona_id}_{o.task_id}" for o in low_quality_outcomes[:10]],
                ))

        # Check for quality variance
        if len(quality_scores) >= 20:
            variance = sum((q - avg_quality) ** 2 for q in quality_scores) / len(quality_scores)
            if variance > 100:  # High variance
                confidence = self._calculate_confidence(len(outcomes), len(outcomes), outcomes)
                if confidence >= self.min_confidence:
                    suggestions.append(ImprovementSuggestion(
                        suggestion_id=f"sug_{uuid.uuid4().hex[:12]}",
                        persona_id=persona_id,
                        category=SuggestionCategory.BEHAVIOR,
                        description=f"Reduce quality variance (current: {variance:.1f})",
                        current_value=variance,
                        suggested_value=50.0,
                        confidence=confidence,
                        evidence_outcomes=[f"out_{o.persona_id}_{o.task_id}" for o in outcomes[:10]],
                    ))

        return suggestions

    def _analyze_success_rate(
        self,
        persona_id: str,
        outcomes: List[ExecutionOutcome],
    ) -> List[ImprovementSuggestion]:
        """Analyze success rate for improvements."""
        suggestions = []

        success_count = sum(1 for o in outcomes if o.success)
        success_rate = success_count / len(outcomes)

        if success_rate < 0.9:  # Below 90% success rate
            failed_outcomes = [o for o in outcomes if not o.success]
            confidence = self._calculate_confidence(
                len(failed_outcomes),
                len(outcomes),
                outcomes,
            )

            if confidence >= self.min_confidence:
                suggestions.append(ImprovementSuggestion(
                    suggestion_id=f"sug_{uuid.uuid4().hex[:12]}",
                    persona_id=persona_id,
                    category=SuggestionCategory.CAPABILITY,
                    description=f"Improve success rate (current: {success_rate:.1%}, target: 90%)",
                    current_value=success_rate,
                    suggested_value=0.9,
                    confidence=confidence,
                    evidence_outcomes=[f"out_{o.persona_id}_{o.task_id}" for o in failed_outcomes[:10]],
                ))

        return suggestions

    def _analyze_error_patterns(
        self,
        persona_id: str,
        outcomes: List[ExecutionOutcome],
    ) -> List[ImprovementSuggestion]:
        """Analyze error patterns for improvements."""
        suggestions = []

        # Count error types
        error_counts: Dict[str, List[ExecutionOutcome]] = {}
        for outcome in outcomes:
            if not outcome.success and outcome.error_type:
                if outcome.error_type not in error_counts:
                    error_counts[outcome.error_type] = []
                error_counts[outcome.error_type].append(outcome)

        # Suggest fixes for common errors
        for error_type, error_outcomes in error_counts.items():
            error_rate = len(error_outcomes) / len(outcomes)
            if error_rate >= 0.1:  # At least 10% of executions
                confidence = self._calculate_confidence(
                    len(error_outcomes),
                    len(outcomes),
                    outcomes,
                )

                if confidence >= self.min_confidence:
                    suggestions.append(ImprovementSuggestion(
                        suggestion_id=f"sug_{uuid.uuid4().hex[:12]}",
                        persona_id=persona_id,
                        category=SuggestionCategory.BEHAVIOR,
                        description=f"Address recurring error: {error_type} (rate: {error_rate:.1%})",
                        current_value=error_rate,
                        suggested_value=0.0,
                        confidence=confidence,
                        evidence_outcomes=[f"out_{o.persona_id}_{o.task_id}" for o in error_outcomes[:10]],
                    ))

        return suggestions

    def _analyze_performance(
        self,
        persona_id: str,
        outcomes: List[ExecutionOutcome],
    ) -> List[ImprovementSuggestion]:
        """Analyze performance for improvements."""
        suggestions = []

        times = [o.completion_time for o in outcomes]
        avg_time = sum(times) / len(times)
        max_time = max(times)

        # Check for slow executions
        slow_threshold = avg_time * 2
        slow_outcomes = [o for o in outcomes if o.completion_time > slow_threshold]

        if len(slow_outcomes) >= len(outcomes) * 0.2:  # 20% or more are slow
            confidence = self._calculate_confidence(
                len(slow_outcomes),
                len(outcomes),
                outcomes,
            )

            if confidence >= self.min_confidence:
                suggestions.append(ImprovementSuggestion(
                    suggestion_id=f"sug_{uuid.uuid4().hex[:12]}",
                    persona_id=persona_id,
                    category=SuggestionCategory.PARAMETER,
                    description=f"Improve execution speed (avg: {avg_time:.1f}s, slow: {len(slow_outcomes)} executions)",
                    current_value=avg_time,
                    suggested_value=avg_time * 0.7,
                    confidence=confidence,
                    evidence_outcomes=[f"out_{o.persona_id}_{o.task_id}" for o in slow_outcomes[:10]],
                ))

        return suggestions

    def _calculate_confidence(
        self,
        relevant_count: int,
        total_count: int,
        outcomes: List[ExecutionOutcome],
    ) -> float:
        """
        Calculate confidence based on:
        - Sample size (more outcomes = higher confidence)
        - Consistency (similar outcomes = higher confidence)
        - Recency (recent outcomes weighted more)
        """
        if total_count < self.MIN_SAMPLE_SIZE:
            return 0.0

        # Sample size factor
        sample_factor = min(1.0, total_count / self.IDEAL_SAMPLE_SIZE)

        # Relevance factor
        relevance_factor = relevant_count / total_count

        # Recency factor (more recent outcomes weighted higher)
        now = datetime.utcnow()
        recency_weights = []
        for outcome in outcomes:
            days_old = (now - outcome.timestamp).days
            weight = 0.5 ** (days_old / self.RECENCY_HALF_LIFE)
            recency_weights.append(weight)

        avg_recency = sum(recency_weights) / len(recency_weights) if recency_weights else 0.5

        # Combine factors
        confidence = sample_factor * relevance_factor * avg_recency

        return min(1.0, confidence)

    def get_suggestion(self, suggestion_id: str) -> Optional[ImprovementSuggestion]:
        """Get a suggestion by ID."""
        return self._suggestions.get(suggestion_id)

    def get_pending_suggestions(
        self,
        persona_id: Optional[str] = None,
    ) -> List[ImprovementSuggestion]:
        """Get all pending suggestions."""
        suggestions = list(self._suggestions.values())

        if persona_id:
            suggestions = [s for s in suggestions if s.persona_id == persona_id]

        return [s for s in suggestions if s.status == SuggestionStatus.PENDING]

    def clear_suggestions(self, persona_id: Optional[str] = None) -> int:
        """Clear suggestions."""
        if persona_id:
            to_remove = [k for k, v in self._suggestions.items() if v.persona_id == persona_id]
            for key in to_remove:
                del self._suggestions[key]
            return len(to_remove)
        else:
            count = len(self._suggestions)
            self._suggestions = {}
            return count
