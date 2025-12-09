"""
Quality Gate Bypass Service
AC-2: Add manual quality gate bypass with audit trail
EU AI Act Article 14 - Human override capability
EPIC: MD-2158
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from .compliance_logger import ComplianceLogger, ComplianceContext


class BypassScope(Enum):
    """Scope of quality gate bypass."""
    SINGLE = "single"      # Single use
    SESSION = "session"    # Valid for session
    WORKFLOW = "workflow"  # Valid for workflow


class BypassStatus(Enum):
    """Status of quality gate bypass."""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    USED = "used"


@dataclass
class QualityGateBypassRequest:
    """Request to bypass a quality gate."""
    gate_id: str
    justification: str
    approver_id: str
    expiry_hours: int
    scope: BypassScope
    context: Optional[ComplianceContext] = None


@dataclass
class QualityGateBypass:
    """Quality gate bypass record."""
    id: str
    gate_id: str
    justification: str
    approver_id: str
    expiry: datetime
    scope: BypassScope
    status: BypassStatus
    created_at: datetime = field(default_factory=datetime.utcnow)
    used_at: Optional[datetime] = None
    audit_log_id: str = ""

    def is_valid(self) -> bool:
        """Check if bypass is still valid."""
        if self.status != BypassStatus.ACTIVE:
            return False
        if datetime.utcnow() > self.expiry:
            return False
        return True


class QualityGateBypassService:
    """
    Quality Gate Bypass Service
    Allows authorized users to bypass quality gates with full audit trail.
    EU AI Act Article 14 compliant human override capability.
    """

    def __init__(
        self,
        logger: ComplianceLogger,
        max_duration_hours: int = 72,
        db_client: Optional[Any] = None
    ):
        """
        Initialize quality gate bypass service.

        Args:
            logger: Compliance logger for audit trail
            max_duration_hours: Maximum bypass duration
            db_client: Optional database client
        """
        self._logger = logger
        self._max_duration_hours = max_duration_hours
        self._db = db_client
        self._bypasses: Dict[str, QualityGateBypass] = {}

    def _generate_bypass_id(self) -> str:
        """Generate unique bypass ID."""
        return f"bypass_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"

    async def create_bypass(self, request: QualityGateBypassRequest) -> QualityGateBypass:
        """
        Create a quality gate bypass.

        Args:
            request: Bypass request details

        Returns:
            Created QualityGateBypass

        Raises:
            ValueError: If justification missing or duration exceeded
        """
        # Validate justification
        if not request.justification or len(request.justification) < 10:
            raise ValueError("Justification must be at least 10 characters")

        # Validate duration
        if request.expiry_hours > self._max_duration_hours:
            raise ValueError(f"Bypass duration cannot exceed {self._max_duration_hours} hours")

        bypass_id = self._generate_bypass_id()
        expiry = datetime.utcnow() + timedelta(hours=request.expiry_hours)

        bypass = QualityGateBypass(
            id=bypass_id,
            gate_id=request.gate_id,
            justification=request.justification,
            approver_id=request.approver_id,
            expiry=expiry,
            scope=request.scope,
            status=BypassStatus.ACTIVE,
        )

        # Log to audit
        audit_entry = await self._logger.log_bypass(
            request.approver_id,
            request.gate_id,
            request.justification,
            request.scope.value,
            expiry,
            request.context
        )
        bypass.audit_log_id = audit_entry.id

        # Store bypass
        self._bypasses[bypass_id] = bypass

        return bypass

    def check_bypass(self, gate_id: str) -> Optional[QualityGateBypass]:
        """
        Check if there's an active bypass for a gate.

        Args:
            gate_id: Gate to check

        Returns:
            Active bypass if found, None otherwise
        """
        for bypass in self._bypasses.values():
            if bypass.gate_id == gate_id and bypass.is_valid():
                return bypass
        return None

    async def use_bypass(self, bypass_id: str) -> bool:
        """
        Mark a bypass as used.

        Args:
            bypass_id: Bypass to use

        Returns:
            True if bypass was used, False if invalid
        """
        bypass = self._bypasses.get(bypass_id)
        if not bypass or not bypass.is_valid():
            return False

        # For single-use bypasses, mark as used
        if bypass.scope == BypassScope.SINGLE:
            bypass.status = BypassStatus.USED
            bypass.used_at = datetime.utcnow()

        return True

    async def revoke_bypass(self, bypass_id: str, revoker_id: str, reason: str) -> bool:
        """
        Revoke an active bypass.

        Args:
            bypass_id: Bypass to revoke
            revoker_id: User revoking the bypass
            reason: Reason for revocation

        Returns:
            True if revoked, False if not found or already inactive
        """
        bypass = self._bypasses.get(bypass_id)
        if not bypass:
            return False

        if bypass.status != BypassStatus.ACTIVE:
            return False

        bypass.status = BypassStatus.REVOKED

        # Log revocation
        from .compliance_logger import OversightActionType
        await self._logger.log_action(
            OversightActionType.BYPASS,
            revoker_id,
            bypass.gate_id,
            {
                "action_type": "bypass_revocation",
                "bypass_id": bypass_id,
                "reason": reason,
            }
        )

        return True

    def list_active_bypasses(self, gate_id: Optional[str] = None) -> List[QualityGateBypass]:
        """
        List active bypasses.

        Args:
            gate_id: Optional filter by gate

        Returns:
            List of active bypasses
        """
        active = []
        for bypass in self._bypasses.values():
            if bypass.status == BypassStatus.ACTIVE:
                if gate_id is None or bypass.gate_id == gate_id:
                    active.append(bypass)
        return active

    def cleanup_expired(self) -> int:
        """
        Mark expired bypasses.

        Returns:
            Number of bypasses expired
        """
        expired_count = 0
        now = datetime.utcnow()
        for bypass in self._bypasses.values():
            if bypass.status == BypassStatus.ACTIVE and now > bypass.expiry:
                bypass.status = BypassStatus.EXPIRED
                expired_count += 1
        return expired_count

    def get_bypass(self, bypass_id: str) -> Optional[QualityGateBypass]:
        """Get a specific bypass by ID."""
        return self._bypasses.get(bypass_id)

    def get_statistics(self) -> Dict[str, Any]:
        """Get bypass statistics."""
        by_status = {status.value: 0 for status in BypassStatus}
        by_scope = {scope.value: 0 for scope in BypassScope}

        for bypass in self._bypasses.values():
            by_status[bypass.status.value] += 1
            by_scope[bypass.scope.value] += 1

        return {
            "total_bypasses": len(self._bypasses),
            "by_status": by_status,
            "by_scope": by_scope,
            "max_duration_hours": self._max_duration_hours,
        }
