"""
Quarantine Manager - Agent Isolation (MD-3123)

Implements agent quarantine for the governance layer:
- AC-1: Quarantine misbehaving agents (block operations)
- AC-2: Automatic triggers from Auditor sybil detection
- AC-3: Review workflow for appeal and release
- AC-4: Audit logging of all quarantine actions
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


class QuarantineError(Exception):
    """Raised when a quarantined agent attempts an operation."""

    def __init__(self, agent_id: str, reason: str = "Agent is quarantined"):
        self.agent_id = agent_id
        self.reason = reason
        super().__init__(f"Agent {agent_id} is quarantined: {reason}")


class QuarantineStatus(Enum):
    """Status of an agent in quarantine."""
    ACTIVE = "active"  # Currently quarantined
    PENDING_REVIEW = "pending_review"  # Review requested
    RELEASED = "released"  # Released from quarantine
    PERMANENTLY_BANNED = "permanently_banned"  # Cannot be released


class QuarantineReason(Enum):
    """Reasons for quarantine."""
    SYBIL_DETECTED = "sybil_detected"
    POLICY_VIOLATION = "policy_violation"
    REPUTATION_TOO_LOW = "reputation_too_low"
    MANUAL_QUARANTINE = "manual_quarantine"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"


class ReviewDecision(Enum):
    """Decision on a quarantine review request."""
    APPROVED = "approved"  # Agent released
    REJECTED = "rejected"  # Agent remains quarantined
    ESCALATED = "escalated"  # Escalated to permanent ban


@dataclass
class QuarantineEntry:
    """Record of an agent's quarantine."""
    agent_id: str
    status: QuarantineStatus
    reason: QuarantineReason
    quarantined_at: datetime
    grace_period_ends: Optional[datetime] = None
    released_at: Optional[datetime] = None
    released_by: Optional[str] = None
    review_requested_at: Optional[datetime] = None
    review_notes: str = ""
    violation_count: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "agent_id": self.agent_id,
            "status": self.status.value,
            "reason": self.reason.value,
            "quarantined_at": self.quarantined_at.isoformat(),
            "grace_period_ends": self.grace_period_ends.isoformat() if self.grace_period_ends else None,
            "released_at": self.released_at.isoformat() if self.released_at else None,
            "released_by": self.released_by,
            "review_requested_at": self.review_requested_at.isoformat() if self.review_requested_at else None,
            "review_notes": self.review_notes,
            "violation_count": self.violation_count,
            "metadata": self.metadata
        }


@dataclass
class QuarantineAction:
    """Record of a quarantine-related action."""
    action_id: str
    agent_id: str
    action_type: str  # quarantine, release, review_request, etc.
    performed_by: str
    timestamp: datetime
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "action_id": self.action_id,
            "agent_id": self.agent_id,
            "action_type": self.action_type,
            "performed_by": self.performed_by,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details
        }


class QuarantineManager:
    """
    Quarantine Manager - Agent Isolation (MD-3123).

    Manages the quarantine lifecycle for agents:
    - AC-1: Quarantine blocking operations
    - AC-2: Automatic triggers from auditor
    - AC-3: Review and release workflow
    - AC-4: Audit logging
    """

    DEFAULT_GRACE_PERIOD_SECONDS = 60  # 1 minute grace period
    DEFAULT_SYBIL_THRESHOLD = 3  # 3 sybil flags = quarantine
    DEFAULT_MAX_REVIEWS = 3  # Max review attempts before permanent ban

    def __init__(
        self,
        grace_period_seconds: int = DEFAULT_GRACE_PERIOD_SECONDS,
        sybil_threshold: int = DEFAULT_SYBIL_THRESHOLD,
        max_reviews: int = DEFAULT_MAX_REVIEWS,
        audit_callback: Optional[Callable[[QuarantineAction], None]] = None
    ):
        """
        Initialize QuarantineManager.

        Args:
            grace_period_seconds: Grace period before quarantine takes effect
            sybil_threshold: Number of sybil flags before auto-quarantine
            max_reviews: Maximum review attempts before permanent ban
            audit_callback: Callback for audit logging (AC-4)
        """
        self._grace_period = timedelta(seconds=grace_period_seconds)
        self._sybil_threshold = sybil_threshold
        self._max_reviews = max_reviews
        self._audit_callback = audit_callback

        # Quarantine state
        self._quarantined: Dict[str, QuarantineEntry] = {}
        self._sybil_flags: Dict[str, int] = defaultdict(int)
        self._review_attempts: Dict[str, int] = defaultdict(int)
        self._action_counter = 0
        self._lock = asyncio.Lock()

        # Action history (AC-4)
        self._action_history: List[QuarantineAction] = []

        logger.info(
            f"QuarantineManager initialized (grace_period={grace_period_seconds}s, "
            f"sybil_threshold={sybil_threshold}, max_reviews={max_reviews})"
        )

    # ============================================================
    # AC-1: Quarantine Agent
    # ============================================================

    async def quarantine(
        self,
        agent_id: str,
        reason: QuarantineReason,
        performed_by: str = "system",
        metadata: Optional[Dict[str, Any]] = None,
        immediate: bool = False
    ) -> QuarantineEntry:
        """
        Place an agent in quarantine (AC-1).

        Args:
            agent_id: ID of agent to quarantine
            reason: Reason for quarantine
            performed_by: Who initiated the quarantine
            metadata: Additional metadata
            immediate: If True, skip grace period

        Returns:
            QuarantineEntry for the quarantined agent
        """
        async with self._lock:
            now = datetime.utcnow()

            # Check if already quarantined
            if agent_id in self._quarantined:
                existing = self._quarantined[agent_id]
                if existing.status in (QuarantineStatus.ACTIVE, QuarantineStatus.PENDING_REVIEW):
                    # Increment violation count
                    existing.violation_count += 1
                    logger.warning(f"Agent {agent_id} already quarantined (violations: {existing.violation_count})")
                    return existing

            # Calculate grace period end
            grace_period_ends = None if immediate else now + self._grace_period

            entry = QuarantineEntry(
                agent_id=agent_id,
                status=QuarantineStatus.ACTIVE,
                reason=reason,
                quarantined_at=now,
                grace_period_ends=grace_period_ends,
                metadata=metadata or {}
            )

            self._quarantined[agent_id] = entry

            # Log action (AC-4)
            await self._log_action(
                agent_id=agent_id,
                action_type="quarantine",
                performed_by=performed_by,
                details={
                    "reason": reason.value,
                    "immediate": immediate,
                    "grace_period_ends": grace_period_ends.isoformat() if grace_period_ends else None
                }
            )

            logger.warning(
                f"Agent {agent_id} quarantined: {reason.value} "
                f"(grace period: {'none' if immediate else str(self._grace_period)})"
            )

            return entry

    def is_quarantined(self, agent_id: str) -> bool:
        """
        Check if an agent is quarantined (AC-1).

        Returns True if agent is quarantined AND grace period has ended.
        """
        if agent_id not in self._quarantined:
            return False

        entry = self._quarantined[agent_id]

        # Check status
        if entry.status not in (QuarantineStatus.ACTIVE, QuarantineStatus.PENDING_REVIEW,
                                 QuarantineStatus.PERMANENTLY_BANNED):
            return False

        # Check grace period
        if entry.grace_period_ends and datetime.utcnow() < entry.grace_period_ends:
            return False  # Still in grace period

        return True

    def check_operation(self, agent_id: str, operation: str = "operation") -> None:
        """
        Check if an agent can perform an operation (AC-1).

        Raises QuarantineError if agent is quarantined.
        """
        if self.is_quarantined(agent_id):
            entry = self._quarantined.get(agent_id)
            reason = entry.reason.value if entry else "unknown"
            raise QuarantineError(agent_id, f"Cannot perform {operation}: {reason}")

    # ============================================================
    # AC-2: Automatic Triggers
    # ============================================================

    async def on_sybil_detected(
        self,
        agent_id: str,
        file_path: str,
        conflicting_agents: List[str]
    ) -> Optional[QuarantineEntry]:
        """
        Handle sybil detection from Auditor (AC-2).

        Automatically quarantines agent after threshold reached.

        Args:
            agent_id: Agent flagged for sybil activity
            file_path: File that was edited
            conflicting_agents: Other agents involved

        Returns:
            QuarantineEntry if quarantine was triggered, None otherwise
        """
        # Collect flag count under lock, but call quarantine() outside
        # to avoid deadlock (asyncio.Lock is not re-entrant)
        should_quarantine = False
        current_flags = 0

        async with self._lock:
            # Increment sybil flag counter
            self._sybil_flags[agent_id] += 1
            current_flags = self._sybil_flags[agent_id]

            logger.info(f"Sybil flag #{current_flags} for agent {agent_id} (threshold: {self._sybil_threshold})")

            # Check threshold (AC-2 configurable trigger)
            if current_flags >= self._sybil_threshold:
                logger.warning(f"Agent {agent_id} exceeded sybil threshold - auto-quarantine triggered")
                should_quarantine = True

        # Call quarantine outside the lock to avoid deadlock
        if should_quarantine:
            return await self.quarantine(
                agent_id=agent_id,
                reason=QuarantineReason.SYBIL_DETECTED,
                performed_by="auditor_auto",
                metadata={
                    "trigger": "sybil_threshold_exceeded",
                    "flag_count": current_flags,
                    "threshold": self._sybil_threshold,
                    "last_file": file_path,
                    "conflicting_agents": conflicting_agents
                }
            )

        return None

    async def on_policy_violation(
        self,
        agent_id: str,
        violation_type: str,
        details: Dict[str, Any]
    ) -> QuarantineEntry:
        """
        Handle policy violation from Enforcer (AC-2 extension).

        Args:
            agent_id: Agent that violated policy
            violation_type: Type of violation
            details: Violation details

        Returns:
            QuarantineEntry for the quarantined agent
        """
        return await self.quarantine(
            agent_id=agent_id,
            reason=QuarantineReason.POLICY_VIOLATION,
            performed_by="enforcer_auto",
            metadata={
                "violation_type": violation_type,
                **details
            }
        )

    async def on_low_reputation(
        self,
        agent_id: str,
        current_reputation: int,
        threshold: int
    ) -> QuarantineEntry:
        """
        Handle low reputation trigger (AC-2 extension).

        Args:
            agent_id: Agent with low reputation
            current_reputation: Current reputation score
            threshold: Threshold that was crossed

        Returns:
            QuarantineEntry for the quarantined agent
        """
        return await self.quarantine(
            agent_id=agent_id,
            reason=QuarantineReason.REPUTATION_TOO_LOW,
            performed_by="reputation_auto",
            metadata={
                "reputation": current_reputation,
                "threshold": threshold
            }
        )

    # ============================================================
    # AC-3: Review Workflow
    # ============================================================

    async def request_review(
        self,
        agent_id: str,
        notes: str = ""
    ) -> bool:
        """
        Request review of quarantine (AC-3).

        Args:
            agent_id: Agent requesting review
            notes: Optional notes for the review

        Returns:
            True if review request was accepted
        """
        async with self._lock:
            if agent_id not in self._quarantined:
                logger.warning(f"Review request for non-quarantined agent {agent_id}")
                return False

            entry = self._quarantined[agent_id]

            # Check if permanently banned
            if entry.status == QuarantineStatus.PERMANENTLY_BANNED:
                logger.warning(f"Agent {agent_id} is permanently banned - review denied")
                return False

            # Check review attempt limit
            attempts = self._review_attempts[agent_id]
            if attempts >= self._max_reviews:
                logger.warning(f"Agent {agent_id} exceeded max review attempts ({self._max_reviews})")
                return False

            # Update status
            entry.status = QuarantineStatus.PENDING_REVIEW
            entry.review_requested_at = datetime.utcnow()
            entry.review_notes = notes
            self._review_attempts[agent_id] += 1

            # Log action (AC-4)
            await self._log_action(
                agent_id=agent_id,
                action_type="review_request",
                performed_by=agent_id,
                details={
                    "notes": notes,
                    "attempt": self._review_attempts[agent_id]
                }
            )

            logger.info(f"Review requested for agent {agent_id} (attempt {self._review_attempts[agent_id]})")
            return True

    async def approve_release(
        self,
        agent_id: str,
        reviewer_id: str,
        notes: str = ""
    ) -> bool:
        """
        Approve release from quarantine (AC-3).

        Args:
            agent_id: Agent to release
            reviewer_id: Authorized reviewer approving release
            notes: Optional release notes

        Returns:
            True if release was approved
        """
        async with self._lock:
            if agent_id not in self._quarantined:
                logger.warning(f"Release approval for non-quarantined agent {agent_id}")
                return False

            entry = self._quarantined[agent_id]

            # Check status
            if entry.status == QuarantineStatus.PERMANENTLY_BANNED:
                logger.warning(f"Cannot release permanently banned agent {agent_id}")
                return False

            # Update entry
            entry.status = QuarantineStatus.RELEASED
            entry.released_at = datetime.utcnow()
            entry.released_by = reviewer_id
            entry.review_notes = notes

            # Reset counters
            self._sybil_flags[agent_id] = 0
            self._review_attempts[agent_id] = 0

            # Log action (AC-4)
            await self._log_action(
                agent_id=agent_id,
                action_type="release_approved",
                performed_by=reviewer_id,
                details={
                    "decision": ReviewDecision.APPROVED.value,
                    "notes": notes
                }
            )

            logger.info(f"Agent {agent_id} released from quarantine by {reviewer_id}")
            return True

    async def reject_release(
        self,
        agent_id: str,
        reviewer_id: str,
        notes: str = "",
        escalate_to_ban: bool = False
    ) -> bool:
        """
        Reject release and keep agent quarantined (AC-3).

        Args:
            agent_id: Agent to keep quarantined
            reviewer_id: Reviewer rejecting release
            notes: Rejection notes
            escalate_to_ban: If True, permanently ban the agent

        Returns:
            True if rejection was processed
        """
        async with self._lock:
            if agent_id not in self._quarantined:
                logger.warning(f"Release rejection for non-quarantined agent {agent_id}")
                return False

            entry = self._quarantined[agent_id]

            if escalate_to_ban or self._review_attempts[agent_id] >= self._max_reviews:
                # Escalate to permanent ban (AC-3 requirement)
                entry.status = QuarantineStatus.PERMANENTLY_BANNED
                decision = ReviewDecision.ESCALATED

                logger.warning(f"Agent {agent_id} permanently banned")
            else:
                # Keep in quarantine
                entry.status = QuarantineStatus.ACTIVE
                decision = ReviewDecision.REJECTED

            entry.review_notes = notes

            # Log action (AC-4)
            await self._log_action(
                agent_id=agent_id,
                action_type="release_rejected",
                performed_by=reviewer_id,
                details={
                    "decision": decision.value,
                    "notes": notes,
                    "escalated": decision == ReviewDecision.ESCALATED
                }
            )

            logger.info(f"Release rejected for agent {agent_id} by {reviewer_id} (decision: {decision.value})")
            return True

    # ============================================================
    # AC-4: Audit Logging
    # ============================================================

    async def _log_action(
        self,
        agent_id: str,
        action_type: str,
        performed_by: str,
        details: Dict[str, Any]
    ) -> QuarantineAction:
        """
        Log a quarantine action (AC-4).

        Args:
            agent_id: Agent involved
            action_type: Type of action
            performed_by: Who performed the action
            details: Action details

        Returns:
            QuarantineAction record
        """
        self._action_counter += 1

        action = QuarantineAction(
            action_id=f"qua_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{self._action_counter:04d}",
            agent_id=agent_id,
            action_type=action_type,
            performed_by=performed_by,
            timestamp=datetime.utcnow(),
            details=details
        )

        self._action_history.append(action)

        # Call audit callback if registered (AC-4)
        if self._audit_callback:
            try:
                self._audit_callback(action)
            except Exception as e:
                logger.error(f"Audit callback error: {e}")

        return action

    # ============================================================
    # Query Methods
    # ============================================================

    def get_quarantine_entry(self, agent_id: str) -> Optional[QuarantineEntry]:
        """Get quarantine entry for an agent."""
        return self._quarantined.get(agent_id)

    def get_quarantined_agents(
        self,
        status: Optional[QuarantineStatus] = None
    ) -> List[QuarantineEntry]:
        """Get all quarantined agents, optionally filtered by status."""
        entries = list(self._quarantined.values())

        if status:
            entries = [e for e in entries if e.status == status]

        return entries

    def get_pending_reviews(self) -> List[QuarantineEntry]:
        """Get all agents pending review."""
        return self.get_quarantined_agents(status=QuarantineStatus.PENDING_REVIEW)

    def get_action_history(
        self,
        agent_id: Optional[str] = None,
        limit: int = 100
    ) -> List[QuarantineAction]:
        """Get quarantine action history."""
        actions = self._action_history

        if agent_id:
            actions = [a for a in actions if a.agent_id == agent_id]

        return actions[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Get quarantine statistics."""
        by_status = defaultdict(int)
        by_reason = defaultdict(int)

        for entry in self._quarantined.values():
            by_status[entry.status.value] += 1
            by_reason[entry.reason.value] += 1

        return {
            "total_quarantined": len(self._quarantined),
            "by_status": dict(by_status),
            "by_reason": dict(by_reason),
            "total_actions": len(self._action_history),
            "sybil_threshold": self._sybil_threshold,
            "max_reviews": self._max_reviews,
            "grace_period_seconds": self._grace_period.total_seconds()
        }


# Factory function
def create_quarantine_manager(
    grace_period_seconds: int = QuarantineManager.DEFAULT_GRACE_PERIOD_SECONDS,
    sybil_threshold: int = QuarantineManager.DEFAULT_SYBIL_THRESHOLD,
    max_reviews: int = QuarantineManager.DEFAULT_MAX_REVIEWS,
    audit_callback: Optional[Callable[[QuarantineAction], None]] = None
) -> QuarantineManager:
    """
    Create a QuarantineManager instance.

    Args:
        grace_period_seconds: Grace period before quarantine takes effect
        sybil_threshold: Number of sybil flags before auto-quarantine
        max_reviews: Maximum review attempts before permanent ban
        audit_callback: Callback for audit logging

    Returns:
        Configured QuarantineManager instance
    """
    return QuarantineManager(
        grace_period_seconds=grace_period_seconds,
        sybil_threshold=sybil_threshold,
        max_reviews=max_reviews,
        audit_callback=audit_callback
    )
