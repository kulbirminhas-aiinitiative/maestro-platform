"""
Outcome Collector for Persona Evolution.

EPIC: MD-2556
AC-1: Execution outcomes feed into persona improvement suggestions.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from .models import ExecutionOutcome

logger = logging.getLogger(__name__)


@dataclass
class OutcomeFilter:
    """Filter criteria for querying outcomes."""
    persona_id: Optional[str] = None
    min_date: Optional[datetime] = None
    max_date: Optional[datetime] = None
    success_only: bool = False
    failure_only: bool = False
    min_quality: Optional[float] = None
    max_quality: Optional[float] = None


class OutcomeCollector:
    """
    Collects and stores execution outcomes for persona evolution.

    AC-1: Execution outcomes feed into persona improvement suggestions.
    """

    def __init__(
        self,
        retention_days: int = 90,
        on_outcome: Optional[Callable[[ExecutionOutcome], None]] = None,
    ):
        """
        Initialize the outcome collector.

        Args:
            retention_days: How long to keep outcomes
            on_outcome: Callback when outcome is collected
        """
        self._outcomes: Dict[str, List[ExecutionOutcome]] = {}  # persona_id -> outcomes
        self._outcome_index: Dict[str, ExecutionOutcome] = {}  # outcome_id -> outcome
        self._retention_days = retention_days
        self._on_outcome = on_outcome

        logger.info(f"OutcomeCollector initialized with {retention_days} day retention")

    def collect(self, outcome: ExecutionOutcome) -> str:
        """
        Collect an execution outcome.

        Args:
            outcome: The execution outcome to collect

        Returns:
            Unique outcome ID
        """
        # Generate outcome ID
        outcome_id = f"out_{outcome.persona_id}_{outcome.task_id}_{int(outcome.timestamp.timestamp())}"

        # Store by persona
        if outcome.persona_id not in self._outcomes:
            self._outcomes[outcome.persona_id] = []
        self._outcomes[outcome.persona_id].append(outcome)

        # Index by ID
        self._outcome_index[outcome_id] = outcome

        logger.info(
            f"Collected outcome {outcome_id}: "
            f"success={outcome.success}, quality={outcome.quality_score}"
        )

        # Trigger callback
        if self._on_outcome:
            try:
                self._on_outcome(outcome)
            except Exception as e:
                logger.error(f"Outcome callback failed: {e}")

        # Cleanup old outcomes
        self._cleanup_old_outcomes()

        return outcome_id

    def get_outcome(self, outcome_id: str) -> Optional[ExecutionOutcome]:
        """Get an outcome by ID."""
        return self._outcome_index.get(outcome_id)

    def get_outcomes(
        self,
        filter_criteria: Optional[OutcomeFilter] = None,
        limit: int = 100,
    ) -> List[ExecutionOutcome]:
        """
        Get outcomes matching filter criteria.

        Args:
            filter_criteria: Filter to apply
            limit: Maximum outcomes to return

        Returns:
            List of matching outcomes
        """
        if filter_criteria is None:
            filter_criteria = OutcomeFilter()

        # Start with all outcomes or persona-specific
        if filter_criteria.persona_id:
            outcomes = self._outcomes.get(filter_criteria.persona_id, [])
        else:
            outcomes = [o for outcomes in self._outcomes.values() for o in outcomes]

        # Apply filters
        filtered = []
        for outcome in outcomes:
            if filter_criteria.min_date and outcome.timestamp < filter_criteria.min_date:
                continue
            if filter_criteria.max_date and outcome.timestamp > filter_criteria.max_date:
                continue
            if filter_criteria.success_only and not outcome.success:
                continue
            if filter_criteria.failure_only and outcome.success:
                continue
            if filter_criteria.min_quality and outcome.quality_score < filter_criteria.min_quality:
                continue
            if filter_criteria.max_quality and outcome.quality_score > filter_criteria.max_quality:
                continue
            filtered.append(outcome)

        # Sort by timestamp descending and limit
        filtered.sort(key=lambda o: o.timestamp, reverse=True)
        return filtered[:limit]

    def get_recent_outcomes(
        self,
        persona_id: str,
        days: int = 7,
    ) -> List[ExecutionOutcome]:
        """
        Get recent outcomes for a persona.

        Args:
            persona_id: Persona to query
            days: Number of days to look back

        Returns:
            List of recent outcomes
        """
        min_date = datetime.utcnow() - timedelta(days=days)
        return self.get_outcomes(
            OutcomeFilter(persona_id=persona_id, min_date=min_date)
        )

    def get_statistics(self, persona_id: str) -> Dict[str, Any]:
        """
        Get statistics for a persona's outcomes.

        Args:
            persona_id: Persona to analyze

        Returns:
            Statistics dictionary
        """
        outcomes = self._outcomes.get(persona_id, [])
        if not outcomes:
            return {
                "total": 0,
                "success_count": 0,
                "failure_count": 0,
                "success_rate": 0.0,
                "avg_quality": 0.0,
                "avg_time": 0.0,
            }

        success_count = sum(1 for o in outcomes if o.success)
        quality_scores = [o.quality_score for o in outcomes]
        completion_times = [o.completion_time for o in outcomes]

        return {
            "total": len(outcomes),
            "success_count": success_count,
            "failure_count": len(outcomes) - success_count,
            "success_rate": success_count / len(outcomes),
            "avg_quality": sum(quality_scores) / len(quality_scores),
            "avg_time": sum(completion_times) / len(completion_times),
            "min_quality": min(quality_scores),
            "max_quality": max(quality_scores),
        }

    def get_error_patterns(self, persona_id: str) -> Dict[str, int]:
        """
        Analyze error patterns for a persona.

        Args:
            persona_id: Persona to analyze

        Returns:
            Error type to count mapping
        """
        outcomes = self._outcomes.get(persona_id, [])
        error_counts: Dict[str, int] = {}

        for outcome in outcomes:
            if not outcome.success and outcome.error_type:
                error_counts[outcome.error_type] = error_counts.get(outcome.error_type, 0) + 1

        return error_counts

    def _cleanup_old_outcomes(self) -> None:
        """Remove outcomes older than retention period."""
        cutoff = datetime.utcnow() - timedelta(days=self._retention_days)

        for persona_id in list(self._outcomes.keys()):
            original_count = len(self._outcomes[persona_id])
            self._outcomes[persona_id] = [
                o for o in self._outcomes[persona_id]
                if o.timestamp >= cutoff
            ]
            removed = original_count - len(self._outcomes[persona_id])
            if removed > 0:
                logger.debug(f"Removed {removed} old outcomes for {persona_id}")

        # Cleanup index
        for outcome_id in list(self._outcome_index.keys()):
            if self._outcome_index[outcome_id].timestamp < cutoff:
                del self._outcome_index[outcome_id]

    def clear(self, persona_id: Optional[str] = None) -> int:
        """
        Clear outcomes.

        Args:
            persona_id: If provided, clear only for this persona

        Returns:
            Number of outcomes cleared
        """
        if persona_id:
            count = len(self._outcomes.get(persona_id, []))
            self._outcomes[persona_id] = []
            # Cleanup index
            self._outcome_index = {
                k: v for k, v in self._outcome_index.items()
                if v.persona_id != persona_id
            }
        else:
            count = sum(len(o) for o in self._outcomes.values())
            self._outcomes = {}
            self._outcome_index = {}

        logger.info(f"Cleared {count} outcomes")
        return count
