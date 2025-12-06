"""
Capability Tracker for Persona Evolution.

EPIC: MD-2556
AC-4: Capability matrix updated based on demonstrated performance.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .models import (
    CapabilityMatrix,
    CapabilityScore,
    ExecutionOutcome,
    Trend,
)

logger = logging.getLogger(__name__)


class CapabilityTracker:
    """
    Tracks and updates persona capability matrices.

    AC-4: Capability matrix updated based on demonstrated performance.
    """

    # Default capabilities tracked for all personas
    DEFAULT_CAPABILITIES = [
        "task_completion",
        "code_quality",
        "response_time",
        "error_handling",
        "documentation",
    ]

    def __init__(
        self,
        default_capabilities: Optional[List[str]] = None,
    ):
        """
        Initialize the capability tracker.

        Args:
            default_capabilities: List of default capabilities to track
        """
        self._matrices: Dict[str, CapabilityMatrix] = {}
        self._default_capabilities = default_capabilities or self.DEFAULT_CAPABILITIES

        logger.info(f"CapabilityTracker initialized with {len(self._default_capabilities)} default capabilities")

    def get_matrix(self, persona_id: str) -> CapabilityMatrix:
        """
        Get or create capability matrix for a persona.

        Args:
            persona_id: Persona ID

        Returns:
            The capability matrix
        """
        if persona_id not in self._matrices:
            self._matrices[persona_id] = CapabilityMatrix(
                persona_id=persona_id,
                capabilities={
                    cap: CapabilityScore(capability_name=cap, current_score=50.0)
                    for cap in self._default_capabilities
                },
            )
            logger.info(f"Created new capability matrix for {persona_id}")

        return self._matrices[persona_id]

    def update_from_outcome(
        self,
        outcome: ExecutionOutcome,
        capability_mapping: Optional[Dict[str, float]] = None,
    ) -> CapabilityMatrix:
        """
        Update capability matrix from an execution outcome.

        Args:
            outcome: The execution outcome
            capability_mapping: Optional explicit capability scores

        Returns:
            Updated capability matrix
        """
        matrix = self.get_matrix(outcome.persona_id)

        if capability_mapping:
            # Use explicit mapping
            for capability, score in capability_mapping.items():
                self._update_capability(matrix, capability, score)
        else:
            # Infer capabilities from outcome
            self._infer_capabilities(matrix, outcome)

        matrix.last_updated = datetime.utcnow()

        logger.debug(
            f"Updated capability matrix for {outcome.persona_id}: "
            f"overall={matrix.overall_score:.1f}"
        )

        return matrix

    def _infer_capabilities(
        self,
        matrix: CapabilityMatrix,
        outcome: ExecutionOutcome,
    ) -> None:
        """Infer capability scores from outcome."""
        # Task completion: based on success and quality
        completion_score = 100.0 if outcome.success else 0.0
        self._update_capability(matrix, "task_completion", completion_score)

        # Code quality: directly from quality score
        self._update_capability(matrix, "code_quality", outcome.quality_score)

        # Response time: inverse of completion time (capped)
        # Assume 10 seconds is excellent, 60+ seconds is poor
        time_score = max(0.0, 100.0 - (outcome.completion_time - 10) * 2)
        time_score = min(100.0, time_score)
        self._update_capability(matrix, "response_time", time_score)

        # Error handling: based on success and error type
        if outcome.success:
            error_score = 100.0
        elif outcome.error_type:
            # Penalize more for certain error types
            recoverable_errors = {"timeout", "retry", "rate_limit"}
            if outcome.error_type.lower() in recoverable_errors:
                error_score = 40.0
            else:
                error_score = 20.0
        else:
            error_score = 30.0
        self._update_capability(matrix, "error_handling", error_score)

        # Documentation: from feedback if available
        if outcome.feedback:
            doc_keywords = ["documented", "clear", "explained", "comments"]
            has_doc = any(kw in outcome.feedback.lower() for kw in doc_keywords)
            doc_score = 80.0 if has_doc else 50.0
            self._update_capability(matrix, "documentation", doc_score)

    def _update_capability(
        self,
        matrix: CapabilityMatrix,
        capability: str,
        new_score: float,
    ) -> None:
        """Update a single capability with exponential moving average."""
        # Clamp score
        new_score = max(0.0, min(100.0, new_score))

        if capability in matrix.capabilities:
            cap = matrix.capabilities[capability]
            # Use exponential moving average
            alpha = 0.3  # Weight for new value
            smoothed = alpha * new_score + (1 - alpha) * cap.current_score
            cap.update(smoothed)
        else:
            matrix.capabilities[capability] = CapabilityScore(
                capability_name=capability,
                current_score=new_score,
                sample_count=1,
            )

    def add_capability(
        self,
        persona_id: str,
        capability: str,
        initial_score: float = 50.0,
    ) -> CapabilityScore:
        """
        Add a new capability to track.

        Args:
            persona_id: Persona ID
            capability: Capability name
            initial_score: Initial score

        Returns:
            The new capability score
        """
        matrix = self.get_matrix(persona_id)

        if capability not in matrix.capabilities:
            matrix.capabilities[capability] = CapabilityScore(
                capability_name=capability,
                current_score=initial_score,
            )
            logger.info(f"Added capability '{capability}' to {persona_id}")

        return matrix.capabilities[capability]

    def remove_capability(
        self,
        persona_id: str,
        capability: str,
    ) -> bool:
        """
        Remove a capability from tracking.

        Args:
            persona_id: Persona ID
            capability: Capability name

        Returns:
            True if removed, False if not found
        """
        matrix = self.get_matrix(persona_id)

        if capability in matrix.capabilities:
            del matrix.capabilities[capability]
            logger.info(f"Removed capability '{capability}' from {persona_id}")
            return True

        return False

    def get_capability(
        self,
        persona_id: str,
        capability: str,
    ) -> Optional[CapabilityScore]:
        """Get a specific capability score."""
        matrix = self.get_matrix(persona_id)
        return matrix.capabilities.get(capability)

    def get_weak_capabilities(
        self,
        persona_id: str,
        threshold: float = 60.0,
    ) -> List[CapabilityScore]:
        """
        Get capabilities below threshold.

        Args:
            persona_id: Persona ID
            threshold: Score threshold

        Returns:
            List of weak capabilities
        """
        matrix = self.get_matrix(persona_id)
        weak = [
            cap for cap in matrix.capabilities.values()
            if cap.current_score < threshold
        ]
        weak.sort(key=lambda c: c.current_score)
        return weak

    def get_improving_capabilities(
        self,
        persona_id: str,
    ) -> List[CapabilityScore]:
        """Get capabilities with improving trend."""
        matrix = self.get_matrix(persona_id)
        return [
            cap for cap in matrix.capabilities.values()
            if cap.get_trend() == Trend.IMPROVING
        ]

    def get_declining_capabilities(
        self,
        persona_id: str,
    ) -> List[CapabilityScore]:
        """Get capabilities with declining trend."""
        matrix = self.get_matrix(persona_id)
        return [
            cap for cap in matrix.capabilities.values()
            if cap.get_trend() == Trend.DECLINING
        ]

    def get_all_matrices(self) -> Dict[str, CapabilityMatrix]:
        """Get all capability matrices."""
        return self._matrices.copy()

    def export(self, persona_id: str) -> Dict[str, Any]:
        """Export capability matrix as dictionary."""
        matrix = self.get_matrix(persona_id)
        return matrix.to_dict()

    def clear(self, persona_id: Optional[str] = None) -> int:
        """Clear capability matrices."""
        if persona_id:
            if persona_id in self._matrices:
                del self._matrices[persona_id]
                return 1
            return 0
        else:
            count = len(self._matrices)
            self._matrices = {}
            return count
