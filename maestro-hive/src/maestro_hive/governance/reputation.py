"""
Reputation System (MD-3203)

Implements the reputation scoring engine as defined in policy.yaml Section 6.
AC-2: An agent that breaks the build loses 20 points.

The reputation system tracks agent trustworthiness based on their actions,
with anti-gaming measures and decay models.
"""

from __future__ import annotations

import logging
import math
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class ReputationEvent(Enum):
    """Events that affect reputation (from policy.yaml Section 6)."""

    # Positive events
    TEST_PASSED = "test_passed"
    PR_MERGED = "pr_merged"
    BUG_FIXED = "bug_fixed"
    CODE_REVIEW_COMPLETED = "code_review_completed"

    # Negative events
    TEST_FAILED = "test_failed"
    BUILD_BROKEN = "build_broken"
    POLICY_VIOLATION = "policy_violation"
    SECURITY_VULNERABILITY = "security_vulnerability_introduced"
    APPEAL_REJECTED = "appeal_rejected"
    HALLUCINATION_DETECTED = "hallucination_detected"


# Default event scores from policy.yaml
DEFAULT_EVENT_SCORES = {
    ReputationEvent.TEST_PASSED: 5,
    ReputationEvent.PR_MERGED: 20,
    ReputationEvent.BUG_FIXED: 15,
    ReputationEvent.CODE_REVIEW_COMPLETED: 10,
    ReputationEvent.TEST_FAILED: -5,
    ReputationEvent.BUILD_BROKEN: -20,  # AC-2: Build broken = -20 points
    ReputationEvent.POLICY_VIOLATION: -30,
    ReputationEvent.SECURITY_VULNERABILITY: -50,
    ReputationEvent.APPEAL_REJECTED: -10,
    ReputationEvent.HALLUCINATION_DETECTED: -15,
}


@dataclass
class ReputationScore:
    """
    Current reputation score for an agent.

    Attributes:
        agent_id: Unique agent identifier
        score: Current reputation score
        role: Current role based on score
        last_activity: Last time agent was active
        total_events: Count of all reputation events
        daily_gain: Points gained today
        daily_loss: Points lost today
    """

    agent_id: str
    score: int = 50  # Initial score from policy
    role: str = "developer_agent"
    last_activity: datetime = field(default_factory=datetime.utcnow)
    created_at: datetime = field(default_factory=datetime.utcnow)
    total_events: int = 0
    daily_gain: int = 0
    daily_loss: int = 0
    last_daily_reset: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "agent_id": self.agent_id,
            "score": self.score,
            "role": self.role,
            "last_activity": self.last_activity.isoformat(),
            "created_at": self.created_at.isoformat(),
            "total_events": self.total_events,
            "daily_gain": self.daily_gain,
            "daily_loss": self.daily_loss,
        }


@dataclass
class ReputationChange:
    """Record of a reputation change."""

    agent_id: str
    event: ReputationEvent
    delta: int
    old_score: int
    new_score: int
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "agent_id": self.agent_id,
            "event": self.event.value,
            "delta": self.delta,
            "old_score": self.old_score,
            "new_score": self.new_score,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


class ReputationEngine:
    """
    The Reputation Engine - Tracks Agent Trust.

    MD-3203: Implements the scoring engine from policy.yaml Section 6.
    AC-2: Ensures build_broken event deducts 20 points.

    Features:
    - Anti-gaming rate limits (max daily gain/loss)
    - Exponential decay for inactive agents
    - Role promotion/demotion based on score
    - Cooldown between same event types
    """

    def __init__(
        self,
        initial_score: int = 50,
        min_score: int = 10,
        max_daily_gain: int = 100,
        max_daily_loss: int = -50,
        decay_half_life_days: int = 30,
        decay_floor: int = 20,
    ):
        """
        Initialize the reputation engine.

        Args:
            initial_score: Starting score for new agents
            min_score: Minimum score before decommission
            max_daily_gain: Cap on daily positive reputation
            max_daily_loss: Cap on daily negative reputation
            decay_half_life_days: Days for reputation to halve when inactive
            decay_floor: Minimum score from decay
        """
        self._scores: Dict[str, ReputationScore] = {}
        self._history: List[ReputationChange] = []
        self._lock = threading.RLock()

        # Configuration from policy.yaml
        self._initial_score = initial_score
        self._min_score = min_score
        self._max_daily_gain = max_daily_gain
        self._max_daily_loss = max_daily_loss
        self._decay_half_life_days = decay_half_life_days
        self._decay_floor = decay_floor

        # Anti-gaming: cooldown tracking
        self._last_event_time: Dict[str, Dict[str, datetime]] = {}
        self._cooldown_seconds = 60

        # Event callbacks
        self._on_score_change: List[Callable[[ReputationChange], None]] = []
        self._on_role_change: List[Callable[[str, str, str], None]] = []
        self._on_decommission: List[Callable[[str], None]] = []

        logger.info("ReputationEngine initialized")

    def get_score(self, agent_id: str) -> ReputationScore:
        """Get current score for an agent, creating if necessary."""
        with self._lock:
            if agent_id not in self._scores:
                self._scores[agent_id] = ReputationScore(
                    agent_id=agent_id,
                    score=self._initial_score,
                )
                logger.info(f"Created reputation record for agent {agent_id}")

            # Apply decay if inactive
            score = self._scores[agent_id]
            self._apply_decay(score)

            # Reset daily counters if new day
            self._maybe_reset_daily_counters(score)

            return score

    def record_event(
        self,
        agent_id: str,
        event: ReputationEvent,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ReputationChange:
        """
        Record a reputation event.

        AC-2: BUILD_BROKEN event deducts 20 points.

        Args:
            agent_id: Agent that triggered the event
            event: Type of event
            metadata: Optional event context (e.g., lines_changed for PR)

        Returns:
            ReputationChange record
        """
        with self._lock:
            score = self.get_score(agent_id)
            old_score = score.score

            # Check anti-gaming cooldown
            if not self._check_cooldown(agent_id, event):
                logger.warning(f"Event {event.value} blocked by cooldown for agent {agent_id}")
                return ReputationChange(
                    agent_id=agent_id,
                    event=event,
                    delta=0,
                    old_score=old_score,
                    new_score=old_score,
                    metadata={"blocked": "cooldown"},
                )

            # Calculate delta
            base_delta = DEFAULT_EVENT_SCORES.get(event, 0)
            delta = self._calculate_weighted_delta(event, base_delta, metadata or {})

            # Apply rate limits
            delta = self._apply_rate_limits(score, delta)

            # Update score
            score.score = max(0, score.score + delta)
            score.last_activity = datetime.utcnow()
            score.total_events += 1

            # Track daily gain/loss
            if delta > 0:
                score.daily_gain += delta
            else:
                score.daily_loss += delta

            # Record cooldown
            self._record_cooldown(agent_id, event)

            # Create change record
            change = ReputationChange(
                agent_id=agent_id,
                event=event,
                delta=delta,
                old_score=old_score,
                new_score=score.score,
                metadata=metadata or {},
            )
            self._history.append(change)

            logger.info(
                f"Agent {agent_id}: {event.value} -> score {old_score} + {delta} = {score.score}"
            )

            # Notify callbacks
            for callback in self._on_score_change:
                try:
                    callback(change)
                except Exception as e:
                    logger.error(f"Score change callback error: {e}")

            # Check for role changes
            self._check_role_promotion(score)

            # Check for decommission
            if score.score < self._min_score:
                logger.warning(f"Agent {agent_id} score below minimum - flagged for decommission")
                for callback in self._on_decommission:
                    try:
                        callback(agent_id)
                    except Exception as e:
                        logger.error(f"Decommission callback error: {e}")

            return change

    def build_broken(self, agent_id: str, metadata: Optional[Dict[str, Any]] = None) -> ReputationChange:
        """
        Convenience method for AC-2: Record a build broken event.

        Deducts 20 points from the agent's reputation.

        Args:
            agent_id: Agent that broke the build
            metadata: Optional context about the broken build

        Returns:
            ReputationChange record
        """
        return self.record_event(agent_id, ReputationEvent.BUILD_BROKEN, metadata)

    def pr_merged(self, agent_id: str, metadata: Optional[Dict[str, Any]] = None) -> ReputationChange:
        """
        Convenience method for AC-1: Record a PR merged event.

        Adds 20 points to the agent's reputation.

        Args:
            agent_id: Agent that merged the PR
            metadata: Optional context about the PR (pr_id, etc.)

        Returns:
            ReputationChange record
        """
        return self.record_event(agent_id, ReputationEvent.PR_MERGED, metadata)

    def test_passed(self, agent_id: str, metadata: Optional[Dict[str, Any]] = None) -> ReputationChange:
        """
        Convenience method for recording a test passed event.

        Adds 5 points to the agent's reputation.

        Args:
            agent_id: Agent whose tests passed
            metadata: Optional context about the test

        Returns:
            ReputationChange record
        """
        return self.record_event(agent_id, ReputationEvent.TEST_PASSED, metadata)

    def bug_fixed(self, agent_id: str, metadata: Optional[Dict[str, Any]] = None) -> ReputationChange:
        """
        Convenience method for recording a bug fix event.

        Adds 15 points to the agent's reputation.

        Args:
            agent_id: Agent that fixed the bug
            metadata: Optional context about the bug

        Returns:
            ReputationChange record
        """
        return self.record_event(agent_id, ReputationEvent.BUG_FIXED, metadata)

    def _calculate_weighted_delta(
        self,
        event: ReputationEvent,
        base_delta: int,
        metadata: Dict[str, Any],
    ) -> int:
        """Calculate weighted delta based on event context."""
        # PR merged: weight by lines changed
        if event == ReputationEvent.PR_MERGED:
            lines_changed = metadata.get("lines_changed", 50)
            min_lines = 10
            if lines_changed < min_lines:
                return 0  # Prevent 1-line PR spam
            weight = min(lines_changed / 50, 3)  # Cap at 3x
            return int(base_delta * weight)

        return base_delta

    def _check_cooldown(self, agent_id: str, event: ReputationEvent) -> bool:
        """Check if event is within cooldown period."""
        if agent_id not in self._last_event_time:
            return True

        last_time = self._last_event_time[agent_id].get(event.value)
        if last_time is None:
            return True

        elapsed = (datetime.utcnow() - last_time).total_seconds()
        return elapsed >= self._cooldown_seconds

    def _record_cooldown(self, agent_id: str, event: ReputationEvent) -> None:
        """Record event time for cooldown tracking."""
        if agent_id not in self._last_event_time:
            self._last_event_time[agent_id] = {}
        self._last_event_time[agent_id][event.value] = datetime.utcnow()

    def _apply_rate_limits(self, score: ReputationScore, delta: int) -> int:
        """Apply daily rate limits to prevent gaming."""
        if delta > 0:
            remaining_gain = self._max_daily_gain - score.daily_gain
            if remaining_gain <= 0:
                logger.warning(f"Agent {score.agent_id} hit daily gain limit")
                return 0
            return min(delta, remaining_gain)
        else:
            remaining_loss = self._max_daily_loss - score.daily_loss
            if remaining_loss >= 0:
                logger.warning(f"Agent {score.agent_id} hit daily loss limit")
                return 0
            return max(delta, remaining_loss)

    def _maybe_reset_daily_counters(self, score: ReputationScore) -> None:
        """Reset daily counters if it's a new day."""
        now = datetime.utcnow()
        if now.date() > score.last_daily_reset.date():
            score.daily_gain = 0
            score.daily_loss = 0
            score.last_daily_reset = now

    def _apply_decay(self, score: ReputationScore) -> None:
        """Apply exponential decay for inactive agents."""
        now = datetime.utcnow()
        inactive_days = (now - score.last_activity).days

        if inactive_days <= 0:
            return

        # Exponential decay: score * (0.5 ^ (days / half_life))
        decay_factor = math.pow(0.5, inactive_days / self._decay_half_life_days)
        decayed_score = int(score.score * decay_factor)

        # Apply floor
        score.score = max(decayed_score, self._decay_floor)

    def _check_role_promotion(self, score: ReputationScore) -> None:
        """Check if agent should be promoted or demoted."""
        old_role = score.role

        # Role thresholds (from policy.yaml role_progression)
        if score.score >= 500:
            new_role = "architect_agent"
        elif score.score >= 200:
            new_role = "senior_developer_agent"
        elif score.score >= 30:
            new_role = "developer_agent"
        else:
            new_role = "restricted_agent"

        if new_role != old_role:
            score.role = new_role
            logger.info(f"Agent {score.agent_id} role changed: {old_role} -> {new_role}")

            for callback in self._on_role_change:
                try:
                    callback(score.agent_id, old_role, new_role)
                except Exception as e:
                    logger.error(f"Role change callback error: {e}")

    def on_score_change(self, callback: Callable[[ReputationChange], None]) -> None:
        """Register callback for score changes."""
        self._on_score_change.append(callback)

    def on_role_change(self, callback: Callable[[str, str, str], None]) -> None:
        """Register callback for role changes."""
        self._on_role_change.append(callback)

    def on_decommission(self, callback: Callable[[str], None]) -> None:
        """Register callback for agent decommission."""
        self._on_decommission.append(callback)

    def get_history(
        self,
        agent_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[ReputationChange]:
        """Get reputation history."""
        with self._lock:
            history = self._history
            if agent_id:
                history = [h for h in history if h.agent_id == agent_id]
            return history[-limit:]

    def get_all_scores(self) -> Dict[str, ReputationScore]:
        """Get all agent scores."""
        with self._lock:
            return dict(self._scores)

    def get_leaderboard(self, limit: int = 10) -> List[ReputationScore]:
        """Get top agents by reputation."""
        with self._lock:
            sorted_scores = sorted(
                self._scores.values(),
                key=lambda s: s.score,
                reverse=True,
            )
            return sorted_scores[:limit]
