#!/usr/bin/env python3
"""
Approval Engine: Multi-stage approval workflow for compliance.

Implements configurable approval chains for sensitive operations.

SOC2 CC5.2: Segregation of duties.
SOX Section 404: Internal controls.
GDPR Article 5: Accountability.
"""

import json
import hashlib
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable, Set
import threading

logger = logging.getLogger(__name__)


class ApprovalStatus(Enum):
    """Approval request status."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ApprovalType(Enum):
    """Types of approvals."""
    SINGLE = "single"           # Any one approver
    ALL = "all"                 # All approvers must approve
    MAJORITY = "majority"       # More than half must approve
    SEQUENTIAL = "sequential"   # Approvers in order


@dataclass
class Approver:
    """An approver in the workflow."""
    id: str
    name: str
    email: str
    role: Optional[str] = None
    delegate: Optional[str] = None
    notification_channels: List[str] = field(default_factory=lambda: ["email"])

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ApprovalDecision:
    """A decision made by an approver."""
    approver_id: str
    status: ApprovalStatus
    timestamp: str
    comment: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['status'] = self.status.value
        return data


@dataclass
class ApprovalRule:
    """Rule defining when approval is required."""
    id: str
    name: str
    description: str
    resource_pattern: str
    action_pattern: str
    conditions: Dict[str, Any] = field(default_factory=dict)
    approval_type: ApprovalType = ApprovalType.SINGLE
    required_approvers: List[str] = field(default_factory=list)
    approver_roles: List[str] = field(default_factory=list)
    timeout_hours: int = 72
    auto_approve_conditions: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['approval_type'] = self.approval_type.value
        return data


@dataclass
class ApprovalRequest:
    """An approval request."""
    id: str
    rule_id: str
    requester_id: str
    resource: str
    action: str
    status: ApprovalStatus
    approval_type: ApprovalType
    required_approvers: List[str]
    decisions: List[ApprovalDecision] = field(default_factory=list)
    current_stage: int = 0
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    expires_at: Optional[str] = None
    completed_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if request has expired."""
        if not self.expires_at:
            return False
        expires = datetime.fromisoformat(self.expires_at.replace('Z', '+00:00').replace('+00:00', ''))
        return datetime.utcnow() > expires

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['status'] = self.status.value
        data['approval_type'] = self.approval_type.value
        data['decisions'] = [d.to_dict() for d in self.decisions]
        return data


class ApprovalEngine:
    """
    Approval workflow engine.

    Features:
    - Configurable approval rules
    - Multiple approval types (single, all, majority, sequential)
    - Timeout and escalation
    - Audit trail
    """

    def __init__(
        self,
        storage_dir: Optional[str] = None,
        notification_callback: Optional[Callable[[ApprovalRequest, str], None]] = None,
        audit_callback: Optional[Callable[[ApprovalRequest], None]] = None
    ):
        """
        Initialize approval engine.

        Args:
            storage_dir: Directory for approval data
            notification_callback: Callback for notifications
            audit_callback: Callback for audit logging
        """
        self.storage_dir = Path(storage_dir) if storage_dir else \
            Path.home() / '.maestro' / 'approvals'
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.notification_callback = notification_callback
        self.audit_callback = audit_callback

        self._rules: Dict[str, ApprovalRule] = {}
        self._requests: Dict[str, ApprovalRequest] = {}
        self._approvers: Dict[str, Approver] = {}
        self._lock = threading.RLock()
        self._request_counter = 0

        self._load_data()

        logger.info(f"ApprovalEngine initialized: {len(self._rules)} rules, "
                   f"{len(self._requests)} pending requests")

    def requires_approval(
        self,
        resource: str,
        action: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[ApprovalRule]:
        """
        Check if an action requires approval.

        Args:
            resource: Resource path
            action: Action being performed
            context: Additional context

        Returns:
            ApprovalRule if approval required, None otherwise
        """
        import fnmatch

        context = context or {}

        for rule in sorted(self._rules.values(), key=lambda r: r.priority, reverse=True):
            if not rule.enabled:
                continue

            if not fnmatch.fnmatch(resource, rule.resource_pattern):
                continue

            if not fnmatch.fnmatch(action, rule.action_pattern):
                continue

            # Check conditions
            if rule.conditions:
                if not self._evaluate_conditions(rule.conditions, context):
                    continue

            # Check auto-approve conditions
            if rule.auto_approve_conditions:
                if self._evaluate_conditions(rule.auto_approve_conditions, context):
                    continue

            return rule

        return None

    def create_request(
        self,
        requester_id: str,
        resource: str,
        action: str,
        rule: ApprovalRule,
        context: Optional[Dict[str, Any]] = None
    ) -> ApprovalRequest:
        """
        Create an approval request.

        Args:
            requester_id: Who is requesting
            resource: Resource
            action: Action
            rule: Applicable rule
            context: Context

        Returns:
            ApprovalRequest
        """
        with self._lock:
            self._request_counter += 1
            request_id = f"APR-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{self._request_counter:04d}"

        expires_at = (datetime.utcnow() + timedelta(hours=rule.timeout_hours)).isoformat()

        request = ApprovalRequest(
            id=request_id,
            rule_id=rule.id,
            requester_id=requester_id,
            resource=resource,
            action=action,
            status=ApprovalStatus.PENDING,
            approval_type=rule.approval_type,
            required_approvers=rule.required_approvers.copy(),
            context=context or {},
            expires_at=expires_at
        )

        with self._lock:
            self._requests[request_id] = request
            self._save_request(request)

        # Send notifications
        if self.notification_callback:
            for approver_id in rule.required_approvers:
                try:
                    self.notification_callback(request, approver_id)
                except Exception as e:
                    logger.error(f"Notification error: {e}")

        # Audit
        if self.audit_callback:
            self.audit_callback(request)

        logger.info(f"Created approval request: {request_id} for {resource}/{action}")

        return request

    def decide(
        self,
        request_id: str,
        approver_id: str,
        approved: bool,
        comment: Optional[str] = None
    ) -> ApprovalRequest:
        """
        Record an approval decision.

        Args:
            request_id: Request to decide on
            approver_id: Who is deciding
            approved: Approve or reject
            comment: Optional comment

        Returns:
            Updated ApprovalRequest

        Raises:
            ValueError: If request not found or already completed
        """
        with self._lock:
            request = self._requests.get(request_id)
            if not request:
                raise ValueError(f"Request not found: {request_id}")

            if request.status != ApprovalStatus.PENDING:
                raise ValueError(f"Request already completed: {request.status.value}")

            if request.is_expired():
                request.status = ApprovalStatus.EXPIRED
                self._save_request(request)
                raise ValueError("Request has expired")

            # Check if approver is authorized
            if approver_id not in request.required_approvers:
                # Check if delegate
                for required in request.required_approvers:
                    if required in self._approvers:
                        if self._approvers[required].delegate == approver_id:
                            break
                else:
                    raise ValueError(f"Not authorized to approve: {approver_id}")

            # Record decision
            decision = ApprovalDecision(
                approver_id=approver_id,
                status=ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED,
                timestamp=datetime.utcnow().isoformat(),
                comment=comment
            )
            request.decisions.append(decision)

            # Evaluate request status
            self._evaluate_request(request)

            self._save_request(request)

            # Audit
            if self.audit_callback:
                self.audit_callback(request)

        logger.info(f"Decision recorded: {request_id} - "
                   f"{'approved' if approved else 'rejected'} by {approver_id}")

        return request

    def cancel_request(
        self,
        request_id: str,
        cancelled_by: str,
        reason: Optional[str] = None
    ) -> ApprovalRequest:
        """Cancel an approval request."""
        with self._lock:
            request = self._requests.get(request_id)
            if not request:
                raise ValueError(f"Request not found: {request_id}")

            if request.status != ApprovalStatus.PENDING:
                raise ValueError(f"Cannot cancel: {request.status.value}")

            request.status = ApprovalStatus.CANCELLED
            request.completed_at = datetime.utcnow().isoformat()
            request.metadata['cancelled_by'] = cancelled_by
            request.metadata['cancel_reason'] = reason

            self._save_request(request)

        return request

    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """Get a request by ID."""
        return self._requests.get(request_id)

    def get_pending_requests(
        self,
        approver_id: Optional[str] = None,
        requester_id: Optional[str] = None
    ) -> List[ApprovalRequest]:
        """Get pending requests with filters."""
        requests = []

        for request in self._requests.values():
            if request.status != ApprovalStatus.PENDING:
                continue

            if request.is_expired():
                request.status = ApprovalStatus.EXPIRED
                self._save_request(request)
                continue

            if approver_id and approver_id not in request.required_approvers:
                continue

            if requester_id and request.requester_id != requester_id:
                continue

            requests.append(request)

        return sorted(requests, key=lambda r: r.created_at, reverse=True)

    def add_rule(self, rule: ApprovalRule) -> None:
        """Add an approval rule."""
        with self._lock:
            self._rules[rule.id] = rule
            self._save_rule(rule)

    def remove_rule(self, rule_id: str) -> bool:
        """Remove an approval rule."""
        with self._lock:
            if rule_id in self._rules:
                del self._rules[rule_id]
                file_path = self.storage_dir / "rules" / f"{rule_id}.json"
                if file_path.exists():
                    file_path.unlink()
                return True
        return False

    def register_approver(self, approver: Approver) -> None:
        """Register an approver."""
        self._approvers[approver.id] = approver

    def _evaluate_request(self, request: ApprovalRequest) -> None:
        """Evaluate request status based on decisions."""
        approved_count = sum(
            1 for d in request.decisions if d.status == ApprovalStatus.APPROVED
        )
        rejected_count = sum(
            1 for d in request.decisions if d.status == ApprovalStatus.REJECTED
        )
        total_required = len(request.required_approvers)

        if request.approval_type == ApprovalType.SINGLE:
            if approved_count >= 1:
                request.status = ApprovalStatus.APPROVED
                request.completed_at = datetime.utcnow().isoformat()
            elif rejected_count >= 1:
                request.status = ApprovalStatus.REJECTED
                request.completed_at = datetime.utcnow().isoformat()

        elif request.approval_type == ApprovalType.ALL:
            if rejected_count >= 1:
                request.status = ApprovalStatus.REJECTED
                request.completed_at = datetime.utcnow().isoformat()
            elif approved_count >= total_required:
                request.status = ApprovalStatus.APPROVED
                request.completed_at = datetime.utcnow().isoformat()

        elif request.approval_type == ApprovalType.MAJORITY:
            required_majority = (total_required // 2) + 1
            if approved_count >= required_majority:
                request.status = ApprovalStatus.APPROVED
                request.completed_at = datetime.utcnow().isoformat()
            elif rejected_count > total_required - required_majority:
                request.status = ApprovalStatus.REJECTED
                request.completed_at = datetime.utcnow().isoformat()

        elif request.approval_type == ApprovalType.SEQUENTIAL:
            if rejected_count >= 1:
                request.status = ApprovalStatus.REJECTED
                request.completed_at = datetime.utcnow().isoformat()
            elif len(request.decisions) >= total_required:
                if all(d.status == ApprovalStatus.APPROVED for d in request.decisions):
                    request.status = ApprovalStatus.APPROVED
                    request.completed_at = datetime.utcnow().isoformat()
            else:
                # Update current stage
                request.current_stage = len(request.decisions)

    def _evaluate_conditions(
        self,
        conditions: Dict[str, Any],
        context: Dict[str, Any]
    ) -> bool:
        """Evaluate conditions against context."""
        for key, expected in conditions.items():
            actual = context.get(key)

            if isinstance(expected, dict):
                if 'gt' in expected and not (actual > expected['gt']):
                    return False
                if 'lt' in expected and not (actual < expected['lt']):
                    return False
                if 'gte' in expected and not (actual >= expected['gte']):
                    return False
                if 'lte' in expected and not (actual <= expected['lte']):
                    return False
                if 'in' in expected and actual not in expected['in']:
                    return False
            elif actual != expected:
                return False

        return True

    def _save_rule(self, rule: ApprovalRule) -> None:
        """Save rule to storage."""
        file_path = self.storage_dir / "rules" / f"{rule.id}.json"
        file_path.parent.mkdir(exist_ok=True)
        with open(file_path, 'w') as f:
            json.dump(rule.to_dict(), f, indent=2)

    def _save_request(self, request: ApprovalRequest) -> None:
        """Save request to storage."""
        file_path = self.storage_dir / "requests" / f"{request.id}.json"
        file_path.parent.mkdir(exist_ok=True)
        with open(file_path, 'w') as f:
            json.dump(request.to_dict(), f, indent=2)

    def _load_data(self) -> None:
        """Load rules and requests from storage."""
        # Load rules
        rules_dir = self.storage_dir / "rules"
        if rules_dir.exists():
            for file_path in rules_dir.glob("*.json"):
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                        data['approval_type'] = ApprovalType(data['approval_type'])
                        self._rules[data['id']] = ApprovalRule(**data)
                except Exception as e:
                    logger.error(f"Error loading rule {file_path}: {e}")

        # Load requests
        requests_dir = self.storage_dir / "requests"
        if requests_dir.exists():
            for file_path in requests_dir.glob("*.json"):
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                        data['status'] = ApprovalStatus(data['status'])
                        data['approval_type'] = ApprovalType(data['approval_type'])
                        data['decisions'] = [
                            ApprovalDecision(
                                approver_id=d['approver_id'],
                                status=ApprovalStatus(d['status']),
                                timestamp=d['timestamp'],
                                comment=d.get('comment'),
                                metadata=d.get('metadata', {})
                            ) for d in data.get('decisions', [])
                        ]
                        self._requests[data['id']] = ApprovalRequest(**data)
                except Exception as e:
                    logger.error(f"Error loading request {file_path}: {e}")


def get_approval_engine(**kwargs) -> ApprovalEngine:
    """Get approval engine instance."""
    return ApprovalEngine(**kwargs)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    engine = ApprovalEngine()

    # Create a rule
    rule = ApprovalRule(
        id="budget-increase",
        name="Budget Increase Approval",
        description="Requires approval for budget increases",
        resource_pattern="budget/*",
        action_pattern="increase",
        approval_type=ApprovalType.SINGLE,
        required_approvers=["finance-lead", "cfo"],
        conditions={"amount": {"gt": 1000}},
        auto_approve_conditions={"amount": {"lte": 500}}
    )
    engine.add_rule(rule)

    # Check if approval required
    needs_approval = engine.requires_approval(
        "budget/engineering",
        "increase",
        {"amount": 5000}
    )
    print(f"Needs approval: {needs_approval is not None}")

    # Create request
    if needs_approval:
        request = engine.create_request(
            requester_id="user-001",
            resource="budget/engineering",
            action="increase",
            rule=needs_approval,
            context={"amount": 5000, "reason": "Scaling infrastructure"}
        )
        print(f"Created request: {request.id}")

        # Approve
        request = engine.decide(request.id, "finance-lead", True, "Approved for Q4 expansion")
        print(f"Status: {request.status.value}")
