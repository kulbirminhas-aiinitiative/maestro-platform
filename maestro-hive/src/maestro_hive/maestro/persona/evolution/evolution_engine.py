"""
Persona Evolution Engine.

EPIC: MD-2556 - [PERSONA-ENGINE] Persona Evolution Algorithm - Learn and Improve

Main orchestrator for persona evolution based on execution outcomes.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from .models import (
    ExecutionOutcome,
    ImprovementSuggestion,
    CapabilityMatrix,
    EvolutionMetrics,
    SuggestionStatus,
)
from .outcome_collector import OutcomeCollector
from .improvement_suggester import ImprovementSuggester
from .approval_gate import ApprovalGate, ApprovalRequest
from .capability_tracker import CapabilityTracker
from .metrics_tracker import MetricsTracker

logger = logging.getLogger(__name__)


@dataclass
class EvolutionResult:
    """Result of an evolution check."""
    persona_id: str
    suggestions_generated: int
    pending_approvals: int
    applied_changes: int
    capability_score: float
    success_rate: float
    timestamp: datetime


class PersonaEvolutionEngine:
    """
    Main engine for persona evolution.

    Integrates all evolution components to:
    - AC-1: Collect execution outcomes and generate improvement suggestions
    - AC-2: Require human approval before applying changes
    - AC-3: Track evolution metrics over time
    - AC-4: Update capability matrix based on performance
    - AC-5: Integrate with Learning Engine for feedback loop
    """

    def __init__(
        self,
        min_outcomes_for_suggestion: int = 10,
        min_confidence: float = 0.6,
        quality_threshold: float = 80.0,
        auto_approve_threshold: Optional[float] = None,
        learning_engine_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        """
        Initialize the evolution engine.

        Args:
            min_outcomes_for_suggestion: Minimum outcomes before generating suggestions
            min_confidence: Minimum confidence for suggestions
            quality_threshold: Target quality score threshold
            auto_approve_threshold: Confidence for auto-approval (None = disabled)
            learning_engine_callback: Callback for Learning Engine integration (AC-5)
        """
        # Initialize components
        self.outcome_collector = OutcomeCollector(
            retention_days=90,
            on_outcome=self._on_outcome_collected,
        )

        self.suggester = ImprovementSuggester(
            min_confidence=min_confidence,
            quality_threshold=quality_threshold,
        )

        self.approval_gate = ApprovalGate(
            on_approval=self._on_approval,
            on_rejection=self._on_rejection,
            auto_approve_threshold=auto_approve_threshold,
        )

        self.capability_tracker = CapabilityTracker()
        self.metrics_tracker = MetricsTracker()

        self._min_outcomes = min_outcomes_for_suggestion
        self._learning_engine_callback = learning_engine_callback
        self._evolution_history: List[EvolutionResult] = []

        logger.info(
            f"PersonaEvolutionEngine initialized "
            f"(min_outcomes={min_outcomes_for_suggestion}, "
            f"min_confidence={min_confidence})"
        )

    def record_outcome(
        self,
        persona_id: str,
        task_id: str,
        success: bool,
        quality_score: float,
        completion_time: float,
        error_type: Optional[str] = None,
        feedback: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Record an execution outcome.

        AC-1: Execution outcomes feed into persona improvement suggestions.

        Args:
            persona_id: ID of the persona
            task_id: ID of the task executed
            success: Whether execution succeeded
            quality_score: Quality score (0-100)
            completion_time: Time in seconds
            error_type: Error type if failed
            feedback: Optional feedback
            metadata: Additional metadata

        Returns:
            Outcome ID
        """
        outcome = ExecutionOutcome(
            persona_id=persona_id,
            task_id=task_id,
            success=success,
            quality_score=quality_score,
            completion_time=completion_time,
            error_type=error_type,
            feedback=feedback,
            metadata=metadata or {},
        )

        outcome_id = self.outcome_collector.collect(outcome)

        # Update metrics (AC-3)
        self.metrics_tracker.record_outcome(outcome)

        # Update capabilities (AC-4)
        self.capability_tracker.update_from_outcome(outcome)

        logger.info(
            f"Recorded outcome {outcome_id} for {persona_id}: "
            f"success={success}, quality={quality_score}"
        )

        return outcome_id

    def check_for_improvements(
        self,
        persona_id: str,
    ) -> List[ImprovementSuggestion]:
        """
        Analyze outcomes and generate improvement suggestions.

        AC-1: Execution outcomes feed into persona improvement suggestions.

        Args:
            persona_id: Persona to analyze

        Returns:
            List of new suggestions
        """
        # Get recent outcomes
        outcomes = self.outcome_collector.get_recent_outcomes(persona_id, days=30)

        if len(outcomes) < self._min_outcomes:
            logger.debug(
                f"Not enough outcomes for {persona_id}: "
                f"{len(outcomes)}/{self._min_outcomes}"
            )
            return []

        # Generate suggestions
        suggestions = self.suggester.analyze_outcomes(persona_id, outcomes)

        # Submit for approval (AC-2)
        for suggestion in suggestions:
            self.approval_gate.submit(suggestion)

        logger.info(
            f"Generated {len(suggestions)} suggestions for {persona_id}"
        )

        # Notify Learning Engine (AC-5)
        if self._learning_engine_callback and suggestions:
            self._notify_learning_engine({
                "event": "suggestions_generated",
                "persona_id": persona_id,
                "suggestion_count": len(suggestions),
                "outcome_count": len(outcomes),
            })

        return suggestions

    def approve_suggestion(
        self,
        suggestion_id: str,
        reviewer: str,
        notes: Optional[str] = None,
    ) -> ApprovalRequest:
        """
        Approve an improvement suggestion.

        AC-2: Human approval required before persona changes applied.

        Args:
            suggestion_id: ID of the suggestion
            reviewer: Who is approving
            notes: Approval notes

        Returns:
            The approval request
        """
        request_id = f"apr_{suggestion_id}"
        request = self.approval_gate.approve(request_id, reviewer, notes)

        logger.info(
            f"Suggestion {suggestion_id} approved by {reviewer}"
        )

        return request

    def reject_suggestion(
        self,
        suggestion_id: str,
        reviewer: str,
        reason: str,
    ) -> ApprovalRequest:
        """
        Reject an improvement suggestion.

        AC-2: Human approval required before persona changes applied.

        Args:
            suggestion_id: ID of the suggestion
            reviewer: Who is rejecting
            reason: Rejection reason

        Returns:
            The approval request
        """
        request_id = f"apr_{suggestion_id}"
        request = self.approval_gate.reject(request_id, reviewer, reason)

        logger.info(
            f"Suggestion {suggestion_id} rejected by {reviewer}: {reason}"
        )

        return request

    def get_pending_approvals(
        self,
        persona_id: Optional[str] = None,
    ) -> List[ApprovalRequest]:
        """
        Get pending approval requests.

        AC-2: Human approval required before persona changes applied.

        Args:
            persona_id: Filter by persona (optional)

        Returns:
            List of pending approval requests
        """
        return self.approval_gate.get_pending(persona_id)

    def get_metrics(self, persona_id: str) -> EvolutionMetrics:
        """
        Get evolution metrics for a persona.

        AC-3: Evolution metrics tracked (success rate improvement over time).

        Args:
            persona_id: Persona ID

        Returns:
            Evolution metrics
        """
        return self.metrics_tracker.get_metrics(persona_id)

    def get_capability_matrix(self, persona_id: str) -> CapabilityMatrix:
        """
        Get capability matrix for a persona.

        AC-4: Capability matrix updated based on demonstrated performance.

        Args:
            persona_id: Persona ID

        Returns:
            Capability matrix
        """
        return self.capability_tracker.get_matrix(persona_id)

    def evolve(self, persona_id: str) -> EvolutionResult:
        """
        Run full evolution cycle for a persona.

        Combines all ACs:
        - Collects outcomes (AC-1)
        - Generates suggestions (AC-1)
        - Tracks metrics (AC-3)
        - Updates capabilities (AC-4)
        - Integrates with Learning Engine (AC-5)

        Args:
            persona_id: Persona to evolve

        Returns:
            Evolution result
        """
        logger.info(f"Running evolution cycle for {persona_id}")

        # Check for improvements (AC-1)
        suggestions = self.check_for_improvements(persona_id)

        # Get current state
        pending = self.approval_gate.get_pending(persona_id)
        metrics = self.metrics_tracker.get_metrics(persona_id)
        capabilities = self.capability_tracker.get_matrix(persona_id)

        # Count applied changes
        applied = len([
            s for s in self.suggester._suggestions.values()
            if s.persona_id == persona_id and s.status == SuggestionStatus.APPLIED
        ])

        result = EvolutionResult(
            persona_id=persona_id,
            suggestions_generated=len(suggestions),
            pending_approvals=len(pending),
            applied_changes=applied,
            capability_score=capabilities.overall_score,
            success_rate=metrics.success_rate,
            timestamp=datetime.utcnow(),
        )

        self._evolution_history.append(result)

        # Record evolution event in metrics (AC-3)
        if suggestions:
            self.metrics_tracker.record_evolution(persona_id)

        # Notify Learning Engine (AC-5)
        if self._learning_engine_callback:
            self._notify_learning_engine({
                "event": "evolution_cycle",
                "persona_id": persona_id,
                "suggestions": len(suggestions),
                "capability_score": capabilities.overall_score,
                "success_rate": metrics.success_rate,
            })

        logger.info(
            f"Evolution cycle complete for {persona_id}: "
            f"suggestions={len(suggestions)}, pending={len(pending)}"
        )

        return result

    def get_evolution_history(
        self,
        persona_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[EvolutionResult]:
        """Get evolution history."""
        history = self._evolution_history.copy()

        if persona_id:
            history = [h for h in history if h.persona_id == persona_id]

        history.sort(key=lambda h: h.timestamp, reverse=True)
        return history[:limit]

    def get_statistics(self) -> Dict[str, Any]:
        """Get overall evolution statistics."""
        return {
            "outcomes_collected": sum(
                len(outcomes)
                for outcomes in self.outcome_collector._outcomes.values()
            ),
            "suggestions_generated": len(self.suggester._suggestions),
            "pending_approvals": len(self.approval_gate._pending),
            "personas_tracked": len(self.metrics_tracker._metrics),
            "approval_statistics": self.approval_gate.get_statistics(),
        }

    def _on_outcome_collected(self, outcome: ExecutionOutcome) -> None:
        """Handle new outcome collection."""
        # Could trigger automatic suggestion check
        pass

    def _on_approval(self, request: ApprovalRequest) -> None:
        """Handle suggestion approval."""
        suggestion = request.suggestion
        suggestion.apply()

        logger.info(
            f"Suggestion {suggestion.suggestion_id} applied for {suggestion.persona_id}"
        )

        # Notify Learning Engine (AC-5)
        if self._learning_engine_callback:
            self._notify_learning_engine({
                "event": "suggestion_applied",
                "persona_id": suggestion.persona_id,
                "suggestion_id": suggestion.suggestion_id,
                "category": suggestion.category.value,
            })

    def _on_rejection(self, request: ApprovalRequest) -> None:
        """Handle suggestion rejection."""
        logger.info(
            f"Suggestion {request.suggestion.suggestion_id} rejected: "
            f"{request.rejection_reason}"
        )

    def _notify_learning_engine(self, data: Dict[str, Any]) -> None:
        """
        Notify the Learning Engine of evolution events.

        AC-5: Integration with Learning Engine for feedback loop.
        """
        if self._learning_engine_callback:
            try:
                self._learning_engine_callback(data)
                logger.debug(f"Notified Learning Engine: {data['event']}")
            except Exception as e:
                logger.error(f"Failed to notify Learning Engine: {e}")
