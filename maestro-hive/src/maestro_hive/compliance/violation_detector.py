#!/usr/bin/env python3
"""
Violation Detector: Real-time policy violation detection.

Monitors actions and detects policy violations for alerting.
"""

import json
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
from .policy_enforcer import PolicyEnforcer, PolicyEvaluation, PolicyDecision

logger = logging.getLogger(__name__)


@dataclass
class PolicyViolation:
    """A detected policy violation."""
    id: str
    resource: str
    action: str
    principal: Optional[str]
    evaluation: PolicyEvaluation
    severity: str  # critical, high, medium, low
    detected_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    acknowledged: bool = False
    resolved: bool = False
    resolution_notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['evaluation'] = self.evaluation.to_dict()
        return data


class ViolationDetector:
    """Detects and tracks policy violations."""

    def __init__(
        self,
        storage_dir: Optional[str] = None,
        enforcer: Optional[PolicyEnforcer] = None,
        alert_callback: Optional[Callable[[PolicyViolation], None]] = None
    ):
        self.storage_dir = Path(storage_dir) if storage_dir else \
            Path.home() / '.maestro' / 'violations'
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.enforcer = enforcer or PolicyEnforcer()
        self.alert_callback = alert_callback
        self._violations: Dict[str, PolicyViolation] = {}
        self._violation_counter = 0

    def check_and_detect(
        self,
        resource: str,
        action: str,
        context: Optional[Dict[str, Any]] = None,
        principal: Optional[str] = None
    ) -> Optional[PolicyViolation]:
        """Check action and detect violation if any."""
        evaluation = self.enforcer.check(resource, action, context, principal)

        if evaluation.decision in (PolicyDecision.DENY, PolicyDecision.REQUIRE_APPROVAL):
            violation = self._create_violation(resource, action, principal, evaluation)

            if self.alert_callback:
                try:
                    self.alert_callback(violation)
                except Exception as e:
                    logger.error(f"Alert callback error: {e}")

            return violation

        return None

    def _create_violation(
        self,
        resource: str,
        action: str,
        principal: Optional[str],
        evaluation: PolicyEvaluation
    ) -> PolicyViolation:
        """Create a violation record."""
        self._violation_counter += 1
        violation_id = f"VIO-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{self._violation_counter:04d}"

        # Determine severity based on resource and action
        severity = 'medium'
        if 'production' in resource.lower() or action == 'delete':
            severity = 'critical'
        elif 'sensitive' in resource.lower():
            severity = 'high'

        violation = PolicyViolation(
            id=violation_id,
            resource=resource,
            action=action,
            principal=principal,
            evaluation=evaluation,
            severity=severity
        )

        self._violations[violation_id] = violation
        self._save_violation(violation)

        logger.warning(f"Violation detected: {violation_id} - {resource}/{action}")

        return violation

    def get_violations(
        self,
        resolved: Optional[bool] = None,
        severity: Optional[str] = None,
        limit: int = 100
    ) -> List[PolicyViolation]:
        """Get violations with filters."""
        violations = list(self._violations.values())

        if resolved is not None:
            violations = [v for v in violations if v.resolved == resolved]
        if severity:
            violations = [v for v in violations if v.severity == severity]

        return sorted(violations, key=lambda v: v.detected_at, reverse=True)[:limit]

    def resolve_violation(
        self,
        violation_id: str,
        notes: Optional[str] = None
    ) -> Optional[PolicyViolation]:
        """Mark a violation as resolved."""
        violation = self._violations.get(violation_id)
        if violation:
            violation.resolved = True
            violation.resolution_notes = notes
            self._save_violation(violation)
        return violation

    def _save_violation(self, violation: PolicyViolation):
        """Save violation to storage."""
        file_path = self.storage_dir / f"{violation.id}.json"
        with open(file_path, 'w') as f:
            json.dump(violation.to_dict(), f, indent=2)


def get_violation_detector(**kwargs) -> ViolationDetector:
    """Get violation detector instance."""
    return ViolationDetector(**kwargs)
