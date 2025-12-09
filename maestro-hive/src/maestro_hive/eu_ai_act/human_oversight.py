"""
Human Oversight Module - EU AI Act Article 14 Compliance

Implements mechanisms for human intervention, override, and control
of AI decision-making processes.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
import threading
from collections import defaultdict
import uuid


class OversightStatus(Enum):
    """Status of oversight request."""
    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    OVERRIDDEN = "overridden"
    EXPIRED = "expired"
    ESCALATED = "escalated"


class OversightType(Enum):
    """Types of human oversight."""
    PRE_DECISION = "pre_decision"  # Human approval before AI decides
    POST_DECISION = "post_decision"  # Human review after AI decides
    ON_DEMAND = "on_demand"  # Manual review request
    THRESHOLD_TRIGGERED = "threshold_triggered"  # Automatic trigger
    PERIODIC = "periodic"  # Scheduled review


class InterventionType(Enum):
    """Types of human intervention."""
    APPROVE = "approve"
    REJECT = "reject"
    MODIFY = "modify"
    ESCALATE = "escalate"
    DEFER = "defer"


@dataclass
class OversightRequest:
    """Request for human oversight."""
    request_id: str
    oversight_type: OversightType
    decision_id: str
    ai_output: Any
    confidence_score: float
    reason: str
    context: Dict[str, Any]
    status: OversightStatus = OversightStatus.PENDING
    assigned_to: Optional[str] = None
    priority: int = 1  # 1=low, 5=critical
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    resolution: Optional[str] = None
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None

    def is_expired(self) -> bool:
        """Check if request has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "request_id": self.request_id,
            "oversight_type": self.oversight_type.value,
            "decision_id": self.decision_id,
            "ai_output_summary": str(self.ai_output)[:200],
            "confidence_score": self.confidence_score,
            "reason": self.reason,
            "status": self.status.value,
            "assigned_to": self.assigned_to,
            "priority": self.priority,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "resolution": self.resolution,
            "resolved_by": self.resolved_by,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None
        }


@dataclass
class InterventionRecord:
    """Record of human intervention."""
    intervention_id: str
    request_id: str
    intervention_type: InterventionType
    user_id: str
    original_output: Any
    modified_output: Optional[Any]
    rationale: str
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class OversightRule:
    """Rule defining when human oversight is required."""
    rule_id: str
    name: str
    description: str
    condition: Callable[[float, Dict[str, Any]], bool]
    oversight_type: OversightType
    priority: int
    auto_escalate_after: Optional[timedelta] = None
    active: bool = True


class HumanOversight:
    """
    Human Oversight manager for EU AI Act Article 14 compliance.

    Provides mechanisms for human intervention, override, and
    supervision of AI decision-making.
    """

    def __init__(
        self,
        ai_system_id: str,
        default_expiry_hours: int = 24,
        confidence_threshold: float = 0.7
    ):
        """
        Initialize human oversight manager.

        Args:
            ai_system_id: Unique identifier for the AI system
            default_expiry_hours: Default hours before request expires
            confidence_threshold: Confidence below which oversight is triggered
        """
        self.ai_system_id = ai_system_id
        self.default_expiry_hours = default_expiry_hours
        self.confidence_threshold = confidence_threshold

        self._requests: Dict[str, OversightRequest] = {}
        self._interventions: Dict[str, InterventionRecord] = {}
        self._rules: Dict[str, OversightRule] = {}
        self._callbacks: Dict[str, List[Callable]] = defaultdict(list)
        self._lock = threading.Lock()

        # Initialize default oversight rules
        self._initialize_default_rules()

    def _initialize_default_rules(self) -> None:
        """Initialize default oversight rules."""
        # Low confidence rule
        self.add_oversight_rule(
            rule_id="low_confidence",
            name="Low Confidence Override",
            description="Trigger oversight when confidence is below threshold",
            condition=lambda conf, ctx: conf < self.confidence_threshold,
            oversight_type=OversightType.THRESHOLD_TRIGGERED,
            priority=3
        )

        # High-risk decision rule
        self.add_oversight_rule(
            rule_id="high_risk",
            name="High Risk Decision",
            description="Trigger oversight for high-risk decisions",
            condition=lambda conf, ctx: ctx.get("risk_level", "low") == "high",
            oversight_type=OversightType.PRE_DECISION,
            priority=5
        )

    def add_oversight_rule(
        self,
        rule_id: str,
        name: str,
        description: str,
        condition: Callable[[float, Dict[str, Any]], bool],
        oversight_type: OversightType,
        priority: int = 1,
        auto_escalate_after: Optional[timedelta] = None
    ) -> OversightRule:
        """
        Add a custom oversight rule.

        Args:
            rule_id: Unique rule identifier
            name: Rule name
            description: Rule description
            condition: Function (confidence, context) -> bool
            oversight_type: Type of oversight to trigger
            priority: Rule priority
            auto_escalate_after: Auto-escalate if not resolved

        Returns:
            Created OversightRule
        """
        rule = OversightRule(
            rule_id=rule_id,
            name=name,
            description=description,
            condition=condition,
            oversight_type=oversight_type,
            priority=priority,
            auto_escalate_after=auto_escalate_after
        )
        self._rules[rule_id] = rule
        return rule

    def check_oversight_required(
        self,
        confidence_score: float,
        context: Dict[str, Any]
    ) -> List[OversightRule]:
        """
        Check if human oversight is required based on rules.

        Args:
            confidence_score: AI decision confidence
            context: Decision context

        Returns:
            List of triggered rules
        """
        triggered_rules = []
        for rule in self._rules.values():
            if rule.active:
                try:
                    if rule.condition(confidence_score, context):
                        triggered_rules.append(rule)
                except Exception:
                    pass  # Skip rules that error

        # Sort by priority (highest first)
        triggered_rules.sort(key=lambda r: r.priority, reverse=True)
        return triggered_rules

    def request_oversight(
        self,
        decision_id: str,
        ai_output: Any,
        confidence_score: float,
        reason: str,
        context: Optional[Dict[str, Any]] = None,
        oversight_type: OversightType = OversightType.POST_DECISION,
        priority: int = 1,
        expiry_hours: Optional[int] = None
    ) -> OversightRequest:
        """
        Create a request for human oversight.

        Args:
            decision_id: ID of the decision requiring oversight
            ai_output: The AI's output/decision
            confidence_score: Confidence score of the decision
            reason: Reason for oversight request
            context: Additional context
            oversight_type: Type of oversight
            priority: Request priority (1-5)
            expiry_hours: Hours until request expires

        Returns:
            Created OversightRequest
        """
        request_id = str(uuid.uuid4())
        expiry = expiry_hours or self.default_expiry_hours

        request = OversightRequest(
            request_id=request_id,
            oversight_type=oversight_type,
            decision_id=decision_id,
            ai_output=ai_output,
            confidence_score=confidence_score,
            reason=reason,
            context=context or {},
            priority=priority,
            expires_at=datetime.utcnow() + timedelta(hours=expiry)
        )

        with self._lock:
            self._requests[request_id] = request

        # Trigger callbacks
        self._trigger_callbacks("request_created", request)

        return request

    def submit_intervention(
        self,
        request_id: str,
        user_id: str,
        intervention_type: InterventionType,
        rationale: str,
        modified_output: Optional[Any] = None
    ) -> Optional[InterventionRecord]:
        """
        Submit a human intervention for an oversight request.

        Args:
            request_id: Oversight request ID
            user_id: ID of user making intervention
            intervention_type: Type of intervention
            rationale: Reason for the intervention
            modified_output: Modified output (if applicable)

        Returns:
            InterventionRecord or None if request not found
        """
        if request_id not in self._requests:
            return None

        request = self._requests[request_id]

        # Check if already resolved
        if request.status in [OversightStatus.APPROVED, OversightStatus.REJECTED,
                               OversightStatus.OVERRIDDEN]:
            return None

        # Check if expired
        if request.is_expired():
            request.status = OversightStatus.EXPIRED
            return None

        # Create intervention record
        intervention = InterventionRecord(
            intervention_id=str(uuid.uuid4()),
            request_id=request_id,
            intervention_type=intervention_type,
            user_id=user_id,
            original_output=request.ai_output,
            modified_output=modified_output,
            rationale=rationale
        )

        # Update request status based on intervention type
        status_map = {
            InterventionType.APPROVE: OversightStatus.APPROVED,
            InterventionType.REJECT: OversightStatus.REJECTED,
            InterventionType.MODIFY: OversightStatus.OVERRIDDEN,
            InterventionType.ESCALATE: OversightStatus.ESCALATED,
            InterventionType.DEFER: OversightStatus.PENDING
        }

        with self._lock:
            request.status = status_map.get(intervention_type, OversightStatus.PENDING)
            request.resolution = rationale
            request.resolved_by = user_id
            request.resolved_at = datetime.utcnow()
            request.updated_at = datetime.utcnow()
            self._interventions[intervention.intervention_id] = intervention

        # Trigger callbacks
        self._trigger_callbacks("intervention_submitted", intervention)

        return intervention

    def override_decision(
        self,
        decision_id: str,
        user_id: str,
        new_output: Any,
        rationale: str
    ) -> Optional[InterventionRecord]:
        """
        Override an AI decision with a human decision.

        Args:
            decision_id: ID of decision to override
            user_id: User making the override
            new_output: New output to use instead
            rationale: Reason for override

        Returns:
            InterventionRecord or None if no pending request
        """
        # Find pending request for this decision
        for request in self._requests.values():
            if (request.decision_id == decision_id and
                request.status == OversightStatus.PENDING):
                return self.submit_intervention(
                    request_id=request.request_id,
                    user_id=user_id,
                    intervention_type=InterventionType.MODIFY,
                    rationale=rationale,
                    modified_output=new_output
                )
        return None

    def assign_request(
        self,
        request_id: str,
        assignee: str
    ) -> bool:
        """
        Assign an oversight request to a reviewer.

        Args:
            request_id: Request ID
            assignee: User to assign to

        Returns:
            True if assigned successfully
        """
        if request_id not in self._requests:
            return False

        with self._lock:
            request = self._requests[request_id]
            request.assigned_to = assignee
            request.status = OversightStatus.IN_REVIEW
            request.updated_at = datetime.utcnow()

        return True

    def escalate_request(
        self,
        request_id: str,
        escalation_reason: str,
        new_priority: int = 5
    ) -> bool:
        """
        Escalate an oversight request.

        Args:
            request_id: Request ID
            escalation_reason: Reason for escalation
            new_priority: New priority level

        Returns:
            True if escalated successfully
        """
        if request_id not in self._requests:
            return False

        with self._lock:
            request = self._requests[request_id]
            request.status = OversightStatus.ESCALATED
            request.priority = new_priority
            request.context["escalation_reason"] = escalation_reason
            request.updated_at = datetime.utcnow()

        self._trigger_callbacks("request_escalated", request)
        return True

    def get_pending_requests(
        self,
        assignee: Optional[str] = None,
        min_priority: int = 1
    ) -> List[OversightRequest]:
        """
        Get pending oversight requests.

        Args:
            assignee: Filter by assignee
            min_priority: Minimum priority level

        Returns:
            List of pending requests
        """
        requests = []
        for request in self._requests.values():
            if request.status in [OversightStatus.PENDING, OversightStatus.IN_REVIEW]:
                if request.priority >= min_priority:
                    if assignee is None or request.assigned_to == assignee:
                        requests.append(request)

        # Sort by priority then by creation time
        requests.sort(key=lambda r: (-r.priority, r.created_at))
        return requests

    def get_request(self, request_id: str) -> Optional[OversightRequest]:
        """Get a specific oversight request."""
        return self._requests.get(request_id)

    def get_intervention(
        self,
        intervention_id: str
    ) -> Optional[InterventionRecord]:
        """Get a specific intervention record."""
        return self._interventions.get(intervention_id)

    def get_interventions_for_decision(
        self,
        decision_id: str
    ) -> List[InterventionRecord]:
        """Get all interventions for a decision."""
        return [
            i for i in self._interventions.values()
            if self._requests.get(i.request_id, OversightRequest(
                request_id="", oversight_type=OversightType.ON_DEMAND,
                decision_id="", ai_output=None, confidence_score=0, reason="", context={}
            )).decision_id == decision_id
        ]

    def register_callback(
        self,
        event_type: str,
        callback: Callable
    ) -> None:
        """
        Register a callback for oversight events.

        Args:
            event_type: Event type (request_created, intervention_submitted, etc.)
            callback: Callback function
        """
        self._callbacks[event_type].append(callback)

    def _trigger_callbacks(self, event_type: str, data: Any) -> None:
        """Trigger registered callbacks."""
        for callback in self._callbacks[event_type]:
            try:
                callback(data)
            except Exception:
                pass

    def process_expired_requests(self) -> List[str]:
        """
        Process and mark expired requests.

        Returns:
            List of expired request IDs
        """
        expired = []
        with self._lock:
            for request in self._requests.values():
                if request.status == OversightStatus.PENDING and request.is_expired():
                    request.status = OversightStatus.EXPIRED
                    request.updated_at = datetime.utcnow()
                    expired.append(request.request_id)

        return expired

    def get_statistics(self) -> Dict[str, Any]:
        """Get oversight statistics."""
        status_counts = defaultdict(int)
        type_counts = defaultdict(int)
        avg_resolution_time = []

        for request in self._requests.values():
            status_counts[request.status.value] += 1
            type_counts[request.oversight_type.value] += 1

            if request.resolved_at and request.created_at:
                resolution_time = (request.resolved_at - request.created_at).total_seconds()
                avg_resolution_time.append(resolution_time)

        return {
            "ai_system_id": self.ai_system_id,
            "total_requests": len(self._requests),
            "total_interventions": len(self._interventions),
            "requests_by_status": dict(status_counts),
            "requests_by_type": dict(type_counts),
            "average_resolution_time_seconds": (
                sum(avg_resolution_time) / len(avg_resolution_time)
                if avg_resolution_time else 0
            ),
            "active_rules": len([r for r in self._rules.values() if r.active]),
            "confidence_threshold": self.confidence_threshold,
            "statistics_timestamp": datetime.utcnow().isoformat()
        }

    def export_oversight_data(self) -> Dict[str, Any]:
        """Export all oversight data."""
        return {
            "ai_system_id": self.ai_system_id,
            "requests": [r.to_dict() for r in self._requests.values()],
            "interventions": [
                {
                    "intervention_id": i.intervention_id,
                    "request_id": i.request_id,
                    "type": i.intervention_type.value,
                    "user_id": i.user_id,
                    "rationale": i.rationale,
                    "timestamp": i.timestamp.isoformat()
                }
                for i in self._interventions.values()
            ],
            "rules": [
                {
                    "rule_id": r.rule_id,
                    "name": r.name,
                    "description": r.description,
                    "type": r.oversight_type.value,
                    "priority": r.priority,
                    "active": r.active
                }
                for r in self._rules.values()
            ],
            "export_date": datetime.utcnow().isoformat()
        }
