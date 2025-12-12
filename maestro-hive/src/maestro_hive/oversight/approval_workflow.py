#!/usr/bin/env python3
"""
approval_workflow.py

Human-in-the-Loop Approval Workflow Engine for critical AI decisions.
Provides workflow creation, suspension, approval processing, and resumption.

Related EPIC: MD-3023 - Human-in-the-Loop Approval System
EU AI Act Compliance: Article 14 (Human Oversight)
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from threading import RLock
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ApprovalType(Enum):
    """Types of approval requests."""
    DECISION = "decision"           # Standard AI decision approval
    OVERRIDE = "override"           # Human override of AI recommendation
    CRITICAL = "critical"           # High-stakes decisions
    COMPLIANCE = "compliance"       # EU AI Act compliance checkpoints


class ApprovalStatus(Enum):
    """Status of an approval request."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class Priority(Enum):
    """Priority levels for approval requests."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class ApprovalDecision(Enum):
    """Possible decisions for an approval request."""
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass
class ApprovalRequest:
    """Represents a human approval request."""
    id: str
    workflow_id: str
    request_type: ApprovalType
    context: Dict[str, Any]
    requester: str
    assigned_to: List[str]
    priority: Priority = Priority.NORMAL
    timeout_seconds: int = 3600
    created_at: datetime = field(default_factory=datetime.utcnow)
    status: ApprovalStatus = ApprovalStatus.PENDING
    decision: Optional[ApprovalDecision] = None
    decided_by: Optional[str] = None
    decided_at: Optional[datetime] = None
    comments: Optional[str] = None
    escalation_level: int = 0
    resume_callback: Optional[Callable] = field(default=None, repr=False)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'id': self.id,
            'workflow_id': self.workflow_id,
            'request_type': self.request_type.value,
            'context': self.context,
            'requester': self.requester,
            'assigned_to': self.assigned_to,
            'priority': self.priority.value,
            'timeout_seconds': self.timeout_seconds,
            'created_at': self.created_at.isoformat(),
            'status': self.status.value,
            'decision': self.decision.value if self.decision else None,
            'decided_by': self.decided_by,
            'decided_at': self.decided_at.isoformat() if self.decided_at else None,
            'comments': self.comments,
            'escalation_level': self.escalation_level
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ApprovalRequest':
        """Create from dictionary."""
        return cls(
            id=data['id'],
            workflow_id=data['workflow_id'],
            request_type=ApprovalType(data['request_type']),
            context=data['context'],
            requester=data['requester'],
            assigned_to=data['assigned_to'],
            priority=Priority(data['priority']),
            timeout_seconds=data['timeout_seconds'],
            created_at=datetime.fromisoformat(data['created_at']),
            status=ApprovalStatus(data['status']),
            decision=ApprovalDecision(data['decision']) if data.get('decision') else None,
            decided_by=data.get('decided_by'),
            decided_at=datetime.fromisoformat(data['decided_at']) if data.get('decided_at') else None,
            comments=data.get('comments'),
            escalation_level=data.get('escalation_level', 0)
        )

    def is_overdue(self) -> bool:
        """Check if request has exceeded its timeout."""
        if self.status != ApprovalStatus.PENDING:
            return False
        deadline = self.created_at + timedelta(seconds=self.timeout_seconds)
        return datetime.utcnow() > deadline

    def time_remaining_seconds(self) -> int:
        """Get seconds remaining before timeout."""
        if self.status != ApprovalStatus.PENDING:
            return 0
        deadline = self.created_at + timedelta(seconds=self.timeout_seconds)
        remaining = (deadline - datetime.utcnow()).total_seconds()
        return max(0, int(remaining))


@dataclass
class ApprovalResult:
    """Result of processing an approval."""
    request_id: str
    success: bool
    decision: ApprovalDecision
    workflow_resumed: bool
    message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SuspendedWorkflow:
    """Represents a suspended workflow awaiting approval."""
    workflow_id: str
    request_id: str
    suspended_at: datetime
    state: Dict[str, Any]
    resume_callback: Optional[Callable] = None


class ApprovalWorkflow:
    """
    Core workflow engine for human-in-the-loop approvals.

    Manages the lifecycle of approval requests including:
    - Creating new approval requests
    - Suspending workflows pending approval
    - Processing approvals/rejections
    - Resuming workflows after approval
    - Audit logging for compliance
    """

    _instance: Optional['ApprovalWorkflow'] = None
    _lock = RLock()

    def __new__(cls) -> 'ApprovalWorkflow':
        """Singleton pattern for workflow engine."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the approval workflow engine."""
        if self._initialized:
            return

        self._requests: Dict[str, ApprovalRequest] = {}
        self._workflow_requests: Dict[str, List[str]] = {}  # workflow_id -> request_ids
        self._suspended_workflows: Dict[str, SuspendedWorkflow] = {}
        self._audit_log: List[Dict[str, Any]] = []
        self._initialized = True

        logger.info("ApprovalWorkflow initialized")

    def create_request(
        self,
        request_type: ApprovalType,
        context: Dict[str, Any],
        assigned_to: List[str],
        workflow_id: Optional[str] = None,
        requester: str = "system",
        priority: Priority = Priority.NORMAL,
        timeout_seconds: int = 3600,
        resume_callback: Optional[Callable] = None
    ) -> ApprovalRequest:
        """
        Create a new approval request.

        Args:
            request_type: Type of approval (DECISION, OVERRIDE, CRITICAL, COMPLIANCE)
            context: Dictionary containing decision context
            assigned_to: List of approver IDs
            workflow_id: Optional parent workflow ID
            requester: ID of the requesting system/user
            priority: Request priority level
            timeout_seconds: Seconds before auto-escalation
            resume_callback: Optional callback to invoke on approval

        Returns:
            Created ApprovalRequest
        """
        with self._lock:
            request_id = f"apr_{uuid.uuid4().hex[:12]}"
            wf_id = workflow_id or f"wf_{uuid.uuid4().hex[:8]}"

            request = ApprovalRequest(
                id=request_id,
                workflow_id=wf_id,
                request_type=request_type,
                context=context,
                requester=requester,
                assigned_to=assigned_to,
                priority=priority,
                timeout_seconds=timeout_seconds,
                resume_callback=resume_callback
            )

            self._requests[request_id] = request

            if wf_id not in self._workflow_requests:
                self._workflow_requests[wf_id] = []
            self._workflow_requests[wf_id].append(request_id)

            self._log_audit_event("request_created", request)
            logger.info(f"Created approval request: {request_id} for workflow {wf_id}")

            return request

    def process_approval(
        self,
        request_id: str,
        decision: ApprovalDecision,
        approver_id: str,
        comments: Optional[str] = None
    ) -> ApprovalResult:
        """
        Process an approval or rejection decision.

        Args:
            request_id: ID of the approval request
            decision: APPROVED or REJECTED
            approver_id: ID of the approver
            comments: Optional comments/rationale

        Returns:
            ApprovalResult with outcome details
        """
        with self._lock:
            if request_id not in self._requests:
                return ApprovalResult(
                    request_id=request_id,
                    success=False,
                    decision=decision,
                    workflow_resumed=False,
                    message=f"Request not found: {request_id}"
                )

            request = self._requests[request_id]

            if request.status != ApprovalStatus.PENDING:
                return ApprovalResult(
                    request_id=request_id,
                    success=False,
                    decision=decision,
                    workflow_resumed=False,
                    message=f"Request not pending: {request.status.value}"
                )

            # Allow system approvers (for auto-approve/reject after escalation exhausted)
            is_system_approver = approver_id.startswith("system:")
            if not is_system_approver and approver_id not in request.assigned_to:
                return ApprovalResult(
                    request_id=request_id,
                    success=False,
                    decision=decision,
                    workflow_resumed=False,
                    message=f"Not authorized to approve: {approver_id}"
                )

            # Update request
            request.decision = decision
            request.decided_by = approver_id
            request.decided_at = datetime.utcnow()
            request.comments = comments
            request.status = ApprovalStatus.APPROVED if decision == ApprovalDecision.APPROVED else ApprovalStatus.REJECTED

            self._log_audit_event("decision_made", request)

            # Resume workflow if approved
            workflow_resumed = False
            if decision == ApprovalDecision.APPROVED:
                workflow_resumed = self.resume_workflow(
                    request.workflow_id,
                    request
                )

            logger.info(
                f"Processed approval {request_id}: {decision.value} by {approver_id}, "
                f"workflow_resumed={workflow_resumed}"
            )

            return ApprovalResult(
                request_id=request_id,
                success=True,
                decision=decision,
                workflow_resumed=workflow_resumed,
                message="Decision processed successfully"
            )

    def suspend_workflow(
        self,
        workflow_id: str,
        request_id: str,
        state: Optional[Dict[str, Any]] = None,
        resume_callback: Optional[Callable] = None
    ) -> bool:
        """
        Suspend a workflow pending approval.

        Args:
            workflow_id: ID of the workflow to suspend
            request_id: ID of the blocking approval request
            state: Optional workflow state to preserve
            resume_callback: Optional callback for resumption

        Returns:
            True if successfully suspended
        """
        with self._lock:
            if request_id not in self._requests:
                logger.error(f"Cannot suspend: request {request_id} not found")
                return False

            suspended = SuspendedWorkflow(
                workflow_id=workflow_id,
                request_id=request_id,
                suspended_at=datetime.utcnow(),
                state=state or {},
                resume_callback=resume_callback
            )

            self._suspended_workflows[workflow_id] = suspended

            self._log_audit_event("workflow_suspended", {
                "workflow_id": workflow_id,
                "request_id": request_id
            })

            logger.info(f"Workflow {workflow_id} suspended pending approval {request_id}")
            return True

    def resume_workflow(
        self,
        workflow_id: str,
        approval_result: ApprovalRequest
    ) -> bool:
        """
        Resume a suspended workflow after approval.

        Args:
            workflow_id: ID of the workflow to resume
            approval_result: The approved request

        Returns:
            True if successfully resumed
        """
        with self._lock:
            if workflow_id not in self._suspended_workflows:
                logger.warning(f"No suspended workflow found: {workflow_id}")
                return False

            suspended = self._suspended_workflows[workflow_id]

            # Invoke resume callback if provided
            callback = suspended.resume_callback or approval_result.resume_callback
            if callback:
                try:
                    callback(approval_result, suspended.state)
                    logger.info(f"Resume callback executed for workflow {workflow_id}")
                except Exception as e:
                    logger.error(f"Resume callback failed: {e}")
                    return False

            # Clean up
            del self._suspended_workflows[workflow_id]

            self._log_audit_event("workflow_resumed", {
                "workflow_id": workflow_id,
                "request_id": approval_result.id
            })

            logger.info(f"Workflow {workflow_id} resumed after approval")
            return True

    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """Get an approval request by ID."""
        return self._requests.get(request_id)

    def get_workflow_requests(self, workflow_id: str) -> List[ApprovalRequest]:
        """Get all requests for a workflow."""
        request_ids = self._workflow_requests.get(workflow_id, [])
        return [self._requests[rid] for rid in request_ids if rid in self._requests]

    def cancel_request(self, request_id: str, reason: str = "Cancelled") -> bool:
        """Cancel a pending request."""
        with self._lock:
            if request_id not in self._requests:
                return False

            request = self._requests[request_id]
            if request.status != ApprovalStatus.PENDING:
                return False

            request.status = ApprovalStatus.CANCELLED
            request.comments = reason

            self._log_audit_event("request_cancelled", request)
            logger.info(f"Request {request_id} cancelled: {reason}")
            return True

    def get_pending_requests(self, approver_id: Optional[str] = None) -> List[ApprovalRequest]:
        """Get all pending requests, optionally filtered by approver."""
        pending = [r for r in self._requests.values() if r.status == ApprovalStatus.PENDING]
        if approver_id:
            pending = [r for r in pending if approver_id in r.assigned_to]
        return sorted(pending, key=lambda r: (r.priority.value, r.created_at), reverse=True)

    def get_stats(self) -> Dict[str, Any]:
        """Get workflow statistics."""
        requests = list(self._requests.values())
        pending = [r for r in requests if r.status == ApprovalStatus.PENDING]
        approved = [r for r in requests if r.status == ApprovalStatus.APPROVED]
        rejected = [r for r in requests if r.status == ApprovalStatus.REJECTED]

        return {
            "total_requests": len(requests),
            "pending": len(pending),
            "approved": len(approved),
            "rejected": len(rejected),
            "suspended_workflows": len(self._suspended_workflows),
            "approval_rate": len(approved) / max(len(approved) + len(rejected), 1),
            "audit_log_entries": len(self._audit_log)
        }

    def get_audit_log(
        self,
        limit: int = 100,
        request_id: Optional[str] = None,
        workflow_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get audit log entries for compliance review."""
        log = self._audit_log

        if request_id:
            log = [e for e in log if self._get_request_id_from_entry(e) == request_id]
        if workflow_id:
            log = [e for e in log if self._get_workflow_id_from_entry(e) == workflow_id]

        return log[-limit:]

    def _get_request_id_from_entry(self, entry: Dict[str, Any]) -> Optional[str]:
        """Extract request_id from an audit log entry."""
        data = entry.get('data', {})
        if isinstance(data, dict):
            return data.get('id') or data.get('request_id')
        return None

    def _get_workflow_id_from_entry(self, entry: Dict[str, Any]) -> Optional[str]:
        """Extract workflow_id from an audit log entry."""
        data = entry.get('data', {})
        if isinstance(data, dict):
            return data.get('workflow_id')
        return None

    def _log_audit_event(self, event_type: str, data: Any) -> None:
        """Log an audit event for compliance."""
        entry = {
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data.to_dict() if hasattr(data, 'to_dict') else data
        }
        self._audit_log.append(entry)


# Singleton accessor
_workflow_instance: Optional[ApprovalWorkflow] = None


def get_approval_workflow() -> ApprovalWorkflow:
    """Get the singleton ApprovalWorkflow instance."""
    global _workflow_instance
    if _workflow_instance is None:
        _workflow_instance = ApprovalWorkflow()
    return _workflow_instance


def create_approval_request(
    request_type: ApprovalType,
    context: Dict[str, Any],
    assigned_to: List[str],
    **kwargs
) -> ApprovalRequest:
    """Convenience function to create an approval request."""
    workflow = get_approval_workflow()
    return workflow.create_request(
        request_type=request_type,
        context=context,
        assigned_to=assigned_to,
        **kwargs
    )
