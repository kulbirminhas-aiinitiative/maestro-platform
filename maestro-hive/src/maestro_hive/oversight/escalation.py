"""
Escalation Service
AC-3: Create escalation path for edge cases
EU AI Act Article 14 - Human oversight escalation
EPIC: MD-2158
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from .compliance_logger import ComplianceLogger, ComplianceContext


class EscalationTier(Enum):
    """Escalation tier levels."""
    TIER_1 = 1  # Team lead / immediate supervisor
    TIER_2 = 2  # Department head / senior manager
    TIER_3 = 3  # Executive / C-level


class EscalationPriority(Enum):
    """Escalation priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EscalationStatus(Enum):
    """Escalation status."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    EXPIRED = "expired"


@dataclass
class EscalationRequest:
    """Request for escalation."""
    context_id: str
    tier: EscalationTier
    reason: str
    priority: EscalationPriority
    context: Optional[ComplianceContext] = None


@dataclass
class Escalation:
    """Escalation record."""
    id: str
    context_id: str
    tier: EscalationTier
    reason: str
    priority: EscalationPriority
    status: EscalationStatus
    assigned_to: Optional[str] = None
    resolution: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    sla_deadline: datetime = field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    audit_log_id: str = ""

    def is_overdue(self) -> bool:
        """Check if escalation is past SLA deadline."""
        if self.status == EscalationStatus.RESOLVED:
            return False
        return datetime.utcnow() > self.sla_deadline


class EscalationService:
    """
    Escalation Service
    Provides multi-tier escalation paths for edge cases with SLA tracking.
    EU AI Act Article 14 compliant human oversight escalation.
    """

    def __init__(
        self,
        logger: ComplianceLogger,
        tier1_sla_mins: int = 30,
        tier2_sla_mins: int = 120,
        tier3_sla_mins: int = 480,
        db_client: Optional[Any] = None
    ):
        """
        Initialize escalation service.

        Args:
            logger: Compliance logger for audit trail
            tier1_sla_mins: Tier 1 SLA in minutes
            tier2_sla_mins: Tier 2 SLA in minutes
            tier3_sla_mins: Tier 3 SLA in minutes
            db_client: Optional database client
        """
        self._logger = logger
        self._sla_mins = {
            EscalationTier.TIER_1: tier1_sla_mins,
            EscalationTier.TIER_2: tier2_sla_mins,
            EscalationTier.TIER_3: tier3_sla_mins,
        }
        self._db = db_client
        self._escalations: Dict[str, Escalation] = {}

    def _generate_escalation_id(self) -> str:
        """Generate unique escalation ID."""
        return f"esc_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"

    def _calculate_sla_deadline(self, tier: EscalationTier, priority: EscalationPriority) -> datetime:
        """Calculate SLA deadline based on tier and priority."""
        base_mins = self._sla_mins[tier]
        # Critical priority halves the SLA
        if priority == EscalationPriority.CRITICAL:
            base_mins = base_mins // 2
        # Low priority doubles the SLA
        elif priority == EscalationPriority.LOW:
            base_mins = base_mins * 2
        return datetime.utcnow() + timedelta(minutes=base_mins)

    async def create_escalation(self, request: EscalationRequest) -> Escalation:
        """
        Create a new escalation.

        Args:
            request: Escalation request details

        Returns:
            Created Escalation
        """
        escalation_id = self._generate_escalation_id()
        sla_deadline = self._calculate_sla_deadline(request.tier, request.priority)

        escalation = Escalation(
            id=escalation_id,
            context_id=request.context_id,
            tier=request.tier,
            reason=request.reason,
            priority=request.priority,
            status=EscalationStatus.PENDING,
            sla_deadline=sla_deadline,
        )

        # Log to audit
        audit_entry = await self._logger.log_escalation(
            "system",
            request.context_id,
            request.tier.value,
            request.reason,
            request.priority.value,
            request.context
        )
        escalation.audit_log_id = audit_entry.id

        # Store escalation
        self._escalations[escalation_id] = escalation

        return escalation

    async def assign_escalation(
        self,
        escalation_id: str,
        assignee_id: str
    ) -> bool:
        """
        Assign an escalation to a handler.

        Args:
            escalation_id: Escalation to assign
            assignee_id: User to assign to

        Returns:
            True if assigned, False if not found or already resolved
        """
        escalation = self._escalations.get(escalation_id)
        if not escalation:
            return False

        if escalation.status == EscalationStatus.RESOLVED:
            return False

        escalation.assigned_to = assignee_id
        escalation.status = EscalationStatus.ASSIGNED

        return True

    async def update_status(
        self,
        escalation_id: str,
        new_status: EscalationStatus,
        notes: Optional[str] = None
    ) -> bool:
        """
        Update escalation status.

        Args:
            escalation_id: Escalation to update
            new_status: New status
            notes: Optional status notes

        Returns:
            True if updated, False if not found
        """
        escalation = self._escalations.get(escalation_id)
        if not escalation:
            return False

        escalation.status = new_status
        if notes:
            escalation.resolution = notes

        return True

    async def resolve_escalation(
        self,
        escalation_id: str,
        resolver_id: str,
        resolution: str
    ) -> bool:
        """
        Resolve an escalation.

        Args:
            escalation_id: Escalation to resolve
            resolver_id: User resolving the escalation
            resolution: Resolution description

        Returns:
            True if resolved, False if not found or already resolved
        """
        escalation = self._escalations.get(escalation_id)
        if not escalation:
            return False

        if escalation.status == EscalationStatus.RESOLVED:
            return False

        escalation.status = EscalationStatus.RESOLVED
        escalation.resolution = resolution
        escalation.resolved_at = datetime.utcnow()

        # Log resolution
        from .compliance_logger import OversightActionType
        await self._logger.log_action(
            OversightActionType.APPROVE,
            resolver_id,
            escalation.context_id,
            {
                "action_type": "escalation_resolution",
                "escalation_id": escalation_id,
                "tier": escalation.tier.value,
                "resolution": resolution,
            }
        )

        return True

    async def escalate_to_next_tier(self, escalation_id: str, reason: str) -> Optional[Escalation]:
        """
        Escalate to the next tier.

        Args:
            escalation_id: Current escalation ID
            reason: Reason for further escalation

        Returns:
            New escalation if created, None if already at max tier
        """
        current = self._escalations.get(escalation_id)
        if not current:
            return None

        # Check if already at max tier
        if current.tier == EscalationTier.TIER_3:
            return None

        # Create next tier escalation
        next_tier = EscalationTier(current.tier.value + 1)
        new_escalation = await self.create_escalation(EscalationRequest(
            context_id=current.context_id,
            tier=next_tier,
            reason=f"Escalated from Tier {current.tier.value}: {reason}",
            priority=current.priority,
        ))

        # Mark original as resolved with escalation
        current.status = EscalationStatus.RESOLVED
        current.resolution = f"Escalated to Tier {next_tier.value}"
        current.resolved_at = datetime.utcnow()

        return new_escalation

    def get_pending_escalations(
        self,
        tier: Optional[EscalationTier] = None,
        assignee_id: Optional[str] = None
    ) -> List[Escalation]:
        """
        Get pending escalations.

        Args:
            tier: Optional filter by tier
            assignee_id: Optional filter by assignee

        Returns:
            List of pending escalations
        """
        pending = []
        for escalation in self._escalations.values():
            if escalation.status in [EscalationStatus.PENDING, EscalationStatus.ASSIGNED, EscalationStatus.IN_PROGRESS]:
                if tier is not None and escalation.tier != tier:
                    continue
                if assignee_id is not None and escalation.assigned_to != assignee_id:
                    continue
                pending.append(escalation)

        # Sort by priority then by deadline
        priority_order = {
            EscalationPriority.CRITICAL: 0,
            EscalationPriority.HIGH: 1,
            EscalationPriority.MEDIUM: 2,
            EscalationPriority.LOW: 3,
        }
        pending.sort(key=lambda e: (priority_order[e.priority], e.sla_deadline))
        return pending

    def get_overdue_escalations(self) -> List[Escalation]:
        """Get all overdue escalations."""
        return [e for e in self._escalations.values() if e.is_overdue()]

    def get_escalation(self, escalation_id: str) -> Optional[Escalation]:
        """Get a specific escalation by ID."""
        return self._escalations.get(escalation_id)

    def get_statistics(self) -> Dict[str, Any]:
        """Get escalation statistics."""
        by_tier = {tier.value: 0 for tier in EscalationTier}
        by_status = {status.value: 0 for status in EscalationStatus}
        by_priority = {priority.value: 0 for priority in EscalationPriority}
        overdue_count = 0

        for escalation in self._escalations.values():
            by_tier[escalation.tier.value] += 1
            by_status[escalation.status.value] += 1
            by_priority[escalation.priority.value] += 1
            if escalation.is_overdue():
                overdue_count += 1

        return {
            "total_escalations": len(self._escalations),
            "by_tier": by_tier,
            "by_status": by_status,
            "by_priority": by_priority,
            "overdue_count": overdue_count,
            "sla_config": {k.value: v for k, v in self._sla_mins.items()},
        }
