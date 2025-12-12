#!/usr/bin/env python3
"""
escalation_handler.py

Escalation Handler for approval timeout scenarios.
Manages escalation paths, notifications, and automatic escalation.

Related EPIC: MD-3023 - Human-in-the-Loop Approval System
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from threading import RLock
from typing import Any, Callable, Dict, List, Optional

from .approval_workflow import (
    ApprovalRequest,
    ApprovalStatus,
    ApprovalType,
    Priority,
    get_approval_workflow
)
from .approval_queue import get_approval_queue

logger = logging.getLogger(__name__)


class EscalationReason(Enum):
    """Reasons for escalation."""
    TIMEOUT = "timeout"
    MANUAL = "manual"
    PRIORITY_UPGRADE = "priority_upgrade"
    APPROVER_UNAVAILABLE = "approver_unavailable"
    POLICY = "policy"


@dataclass
class EscalationLevel:
    """Defines a level in the escalation path."""
    level: int
    role: str
    approvers: List[str]
    timeout_seconds: Optional[int] = 3600
    priority_override: Optional[Priority] = None
    notification_channels: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "level": self.level,
            "role": self.role,
            "approvers": self.approvers,
            "timeout_seconds": self.timeout_seconds,
            "priority_override": self.priority_override.value if self.priority_override else None,
            "notification_channels": self.notification_channels
        }


@dataclass
class EscalationPath:
    """Complete escalation path configuration."""
    request_type: ApprovalType
    levels: List[EscalationLevel]
    final_action: str = "auto_reject"  # auto_reject, auto_approve, block

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "request_type": self.request_type.value,
            "levels": [l.to_dict() for l in self.levels],
            "final_action": self.final_action
        }


@dataclass
class EscalationResult:
    """Result of an escalation operation."""
    request_id: str
    success: bool
    new_level: int
    new_approvers: List[str]
    reason: EscalationReason
    message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class EscalationEvent:
    """Record of an escalation event."""
    request_id: str
    from_level: int
    to_level: int
    reason: EscalationReason
    triggered_by: str
    timestamp: datetime = field(default_factory=datetime.utcnow)


class EscalationHandler:
    """
    Manages escalation paths and handles timeout scenarios.

    Features:
    - Configurable escalation paths per request type
    - Automatic timeout-based escalation
    - Manual escalation triggers
    - Notification integration
    - Escalation history tracking
    """

    _instance: Optional['EscalationHandler'] = None
    _lock = RLock()

    def __new__(cls) -> 'EscalationHandler':
        """Singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the escalation handler."""
        if self._initialized:
            return

        self._escalation_paths: Dict[ApprovalType, EscalationPath] = {}
        self._escalation_history: List[EscalationEvent] = []
        self._notification_handlers: Dict[str, Callable] = {}
        self._workflow = get_approval_workflow()
        self._queue = get_approval_queue()
        self._initialized = True

        # Configure default escalation paths
        self._configure_defaults()

        logger.info("EscalationHandler initialized")

    def _configure_defaults(self) -> None:
        """Configure default escalation paths."""
        # Critical decisions get aggressive escalation
        self._escalation_paths[ApprovalType.CRITICAL] = EscalationPath(
            request_type=ApprovalType.CRITICAL,
            levels=[
                EscalationLevel(
                    level=1,
                    role="senior_engineer",
                    approvers=[],
                    timeout_seconds=1800,
                    notification_channels=["email", "slack"]
                ),
                EscalationLevel(
                    level=2,
                    role="tech_lead",
                    approvers=[],
                    timeout_seconds=3600,
                    priority_override=Priority.CRITICAL,
                    notification_channels=["email", "slack", "pager"]
                ),
                EscalationLevel(
                    level=3,
                    role="director",
                    approvers=[],
                    timeout_seconds=None,  # No further timeout
                    notification_channels=["email", "slack", "pager", "phone"]
                )
            ],
            final_action="block"
        )

        # Compliance requests need proper oversight chain
        self._escalation_paths[ApprovalType.COMPLIANCE] = EscalationPath(
            request_type=ApprovalType.COMPLIANCE,
            levels=[
                EscalationLevel(
                    level=1,
                    role="compliance_officer",
                    approvers=[],
                    timeout_seconds=7200,
                    notification_channels=["email"]
                ),
                EscalationLevel(
                    level=2,
                    role="legal_counsel",
                    approvers=[],
                    timeout_seconds=None,
                    notification_channels=["email", "phone"]
                )
            ],
            final_action="block"
        )

        # Standard decisions
        self._escalation_paths[ApprovalType.DECISION] = EscalationPath(
            request_type=ApprovalType.DECISION,
            levels=[
                EscalationLevel(
                    level=1,
                    role="team_lead",
                    approvers=[],
                    timeout_seconds=3600,
                    notification_channels=["email"]
                ),
                EscalationLevel(
                    level=2,
                    role="manager",
                    approvers=[],
                    timeout_seconds=7200,
                    notification_channels=["email", "slack"]
                )
            ],
            final_action="auto_reject"
        )

    def configure_escalation_path(
        self,
        request_type: ApprovalType,
        levels: List[Dict[str, Any]],
        final_action: str = "auto_reject"
    ) -> bool:
        """
        Configure escalation path for a request type.

        Args:
            request_type: Type of approval request
            levels: List of escalation level configurations
            final_action: Action when all levels exhausted

        Returns:
            True if successfully configured
        """
        with self._lock:
            try:
                escalation_levels = []
                for i, level_config in enumerate(levels):
                    level = EscalationLevel(
                        level=i + 1,
                        role=level_config["role"],
                        approvers=level_config.get("approvers", []),
                        timeout_seconds=level_config.get("timeout", 3600),
                        priority_override=Priority(level_config["priority"]) if "priority" in level_config else None,
                        notification_channels=level_config.get("notification_channels", ["email"])
                    )
                    escalation_levels.append(level)

                self._escalation_paths[request_type] = EscalationPath(
                    request_type=request_type,
                    levels=escalation_levels,
                    final_action=final_action
                )

                logger.info(
                    f"Configured escalation path for {request_type.value}: "
                    f"{len(escalation_levels)} levels"
                )
                return True

            except Exception as e:
                logger.error(f"Failed to configure escalation path: {e}")
                return False

    def get_escalation_path(self, request_type: ApprovalType) -> Optional[EscalationPath]:
        """Get the escalation path for a request type."""
        return self._escalation_paths.get(request_type)

    def escalate(
        self,
        request_id: str,
        reason: EscalationReason = EscalationReason.MANUAL,
        triggered_by: str = "system"
    ) -> EscalationResult:
        """
        Escalate a request to the next level.

        Args:
            request_id: ID of the request to escalate
            reason: Reason for escalation
            triggered_by: Who/what triggered the escalation

        Returns:
            EscalationResult with outcome details
        """
        with self._lock:
            request = self._workflow.get_request(request_id)
            if not request:
                return EscalationResult(
                    request_id=request_id,
                    success=False,
                    new_level=0,
                    new_approvers=[],
                    reason=reason,
                    message=f"Request not found: {request_id}"
                )

            if request.status != ApprovalStatus.PENDING:
                return EscalationResult(
                    request_id=request_id,
                    success=False,
                    new_level=request.escalation_level,
                    new_approvers=request.assigned_to,
                    reason=reason,
                    message=f"Request not pending: {request.status.value}"
                )

            path = self._escalation_paths.get(request.request_type)
            if not path:
                return EscalationResult(
                    request_id=request_id,
                    success=False,
                    new_level=request.escalation_level,
                    new_approvers=request.assigned_to,
                    reason=reason,
                    message=f"No escalation path for type: {request.request_type.value}"
                )

            current_level = request.escalation_level
            new_level = current_level + 1

            # Check if we've exhausted all levels
            if new_level > len(path.levels):
                return self._handle_final_action(request, path, reason)

            # Get next level configuration
            level_config = path.levels[new_level - 1]

            # Update request
            request.escalation_level = new_level
            request.status = ApprovalStatus.ESCALATED
            old_approvers = request.assigned_to.copy()

            # Update approvers
            if level_config.approvers:
                request.assigned_to = level_config.approvers
            else:
                # Keep existing approvers plus add role placeholder
                request.assigned_to = old_approvers + [f"role:{level_config.role}"]

            # Update priority if specified
            if level_config.priority_override:
                request.priority = level_config.priority_override

            # Update timeout
            if level_config.timeout_seconds:
                request.timeout_seconds = level_config.timeout_seconds
                request.created_at = datetime.utcnow()  # Reset timeout

            # Reset status to pending
            request.status = ApprovalStatus.PENDING

            # Update queue
            self._queue.reassign(request_id, request.assigned_to)
            self._queue.prioritize(request_id, request.priority)

            # Record escalation event
            event = EscalationEvent(
                request_id=request_id,
                from_level=current_level,
                to_level=new_level,
                reason=reason,
                triggered_by=triggered_by
            )
            self._escalation_history.append(event)

            # Send notifications
            self._send_escalation_notifications(request, level_config)

            logger.info(
                f"Request {request_id} escalated: level {current_level} -> {new_level}, "
                f"reason: {reason.value}"
            )

            return EscalationResult(
                request_id=request_id,
                success=True,
                new_level=new_level,
                new_approvers=request.assigned_to,
                reason=reason,
                message=f"Escalated to level {new_level} ({level_config.role})"
            )

    def _handle_final_action(
        self,
        request: ApprovalRequest,
        path: EscalationPath,
        reason: EscalationReason
    ) -> EscalationResult:
        """Handle when all escalation levels are exhausted."""
        if path.final_action == "auto_approve":
            from .approval_workflow import ApprovalDecision
            self._workflow.process_approval(
                request_id=request.id,
                decision=ApprovalDecision.APPROVED,
                approver_id="system:auto_approve",
                comments="Auto-approved after escalation exhausted"
            )
            message = "Auto-approved (escalation exhausted)"

        elif path.final_action == "auto_reject":
            from .approval_workflow import ApprovalDecision
            self._workflow.process_approval(
                request_id=request.id,
                decision=ApprovalDecision.REJECTED,
                approver_id="system:auto_reject",
                comments="Auto-rejected after escalation exhausted"
            )
            message = "Auto-rejected (escalation exhausted)"

        else:  # block
            request.status = ApprovalStatus.EXPIRED
            message = "Blocked (escalation exhausted, requires manual intervention)"

        logger.warning(f"Request {request.id} final action: {path.final_action}")

        return EscalationResult(
            request_id=request.id,
            success=True,
            new_level=request.escalation_level,
            new_approvers=request.assigned_to,
            reason=reason,
            message=message
        )

    def notify_escalation(
        self,
        request_id: str,
        target_approver: str,
        channel: str = "email"
    ) -> bool:
        """
        Send escalation notification to a specific approver.

        Args:
            request_id: ID of the escalated request
            target_approver: Approver to notify
            channel: Notification channel to use

        Returns:
            True if notification sent successfully
        """
        handler = self._notification_handlers.get(channel)
        if not handler:
            logger.warning(f"No handler registered for channel: {channel}")
            return False

        request = self._workflow.get_request(request_id)
        if not request:
            return False

        try:
            handler(request, target_approver)
            logger.info(f"Sent {channel} notification to {target_approver} for {request_id}")
            return True
        except Exception as e:
            logger.error(f"Notification failed: {e}")
            return False

    def _send_escalation_notifications(
        self,
        request: ApprovalRequest,
        level_config: EscalationLevel
    ) -> None:
        """Send notifications for escalation via all configured channels."""
        for channel in level_config.notification_channels:
            for approver in request.assigned_to:
                self.notify_escalation(request.id, approver, channel)

    def register_notification_handler(
        self,
        channel: str,
        handler: Callable[[ApprovalRequest, str], None]
    ) -> None:
        """
        Register a notification handler for a channel.

        Args:
            channel: Channel name (email, slack, pager, etc.)
            handler: Function to call with (request, approver_id)
        """
        self._notification_handlers[channel] = handler
        logger.info(f"Registered notification handler for channel: {channel}")

    def check_timeouts(self) -> List[str]:
        """
        Check for overdue requests and auto-escalate them.

        Returns:
            List of request IDs that were escalated
        """
        with self._lock:
            overdue = self._queue.get_overdue()
            escalated = []

            for request in overdue:
                result = self.escalate(
                    request_id=request.id,
                    reason=EscalationReason.TIMEOUT,
                    triggered_by="timeout_checker"
                )
                if result.success:
                    escalated.append(request.id)

            if escalated:
                logger.info(f"Auto-escalated {len(escalated)} overdue requests")

            return escalated

    def get_escalation_history(
        self,
        request_id: Optional[str] = None,
        limit: int = 100
    ) -> List[EscalationEvent]:
        """Get escalation history."""
        history = self._escalation_history
        if request_id:
            history = [e for e in history if e.request_id == request_id]
        return history[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Get escalation statistics."""
        history = self._escalation_history

        # Count by reason
        by_reason = {r.value: 0 for r in EscalationReason}
        for event in history:
            by_reason[event.reason.value] += 1

        # Count by level reached
        max_levels = {}
        for event in history:
            if event.request_id not in max_levels or event.to_level > max_levels[event.request_id]:
                max_levels[event.request_id] = event.to_level

        level_distribution = {}
        for level in max_levels.values():
            level_distribution[level] = level_distribution.get(level, 0) + 1

        return {
            "total_escalations": len(history),
            "by_reason": by_reason,
            "level_distribution": level_distribution,
            "configured_paths": len(self._escalation_paths),
            "notification_channels": list(self._notification_handlers.keys())
        }


# Singleton accessor
_handler_instance: Optional[EscalationHandler] = None


def get_escalation_handler() -> EscalationHandler:
    """Get the singleton EscalationHandler instance."""
    global _handler_instance
    if _handler_instance is None:
        _handler_instance = EscalationHandler()
    return _handler_instance
