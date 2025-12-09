#!/usr/bin/env python3
"""
Risk Mitigation: Track and manage risk mitigations.

Provides mitigation tracking, effectiveness measurement, and recommendations.
"""

import json
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from .risk_scorer import RiskScorer, RiskMitigation

logger = logging.getLogger(__name__)


@dataclass
class MitigationPlan:
    """A comprehensive mitigation plan."""
    id: str
    risk_assessment_id: str
    mitigations: List[RiskMitigation]
    total_risk_reduction: float
    status: str  # draft, approved, in_progress, completed
    created_by: str
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['mitigations'] = [m.to_dict() for m in self.mitigations]
        return data


class MitigationTracker:
    """Tracks and manages risk mitigations."""

    def __init__(
        self,
        storage_dir: Optional[str] = None,
        scorer: Optional[RiskScorer] = None
    ):
        self.storage_dir = Path(storage_dir) if storage_dir else \
            Path.home() / '.maestro' / 'mitigations'
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.scorer = scorer or RiskScorer()
        self._plans: Dict[str, MitigationPlan] = {}
        self._plan_counter = 0

    def create_plan(
        self,
        assessment_id: str,
        created_by: str,
        mitigations: Optional[List[Dict]] = None
    ) -> MitigationPlan:
        """Create a mitigation plan from assessment."""
        assessment = self.scorer.get_assessment(assessment_id)
        if not assessment:
            raise ValueError(f"Assessment not found: {assessment_id}")

        # Get suggested mitigations from assessment factors
        suggested = []
        for factor in assessment.factors:
            for mitigation in factor.mitigations:
                suggested.append(RiskMitigation(
                    id=f"MIT-{len(suggested):04d}",
                    risk_id=assessment_id,
                    action=mitigation,
                    status='proposed',
                    effectiveness=0.3  # Default estimate
                ))

        self._plan_counter += 1
        plan_id = f"PLAN-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{self._plan_counter:04d}"

        plan = MitigationPlan(
            id=plan_id,
            risk_assessment_id=assessment_id,
            mitigations=suggested,
            total_risk_reduction=sum(m.effectiveness for m in suggested),
            status='draft',
            created_by=created_by
        )

        self._plans[plan_id] = plan
        self._save_plan(plan)

        return plan

    def update_mitigation_status(
        self,
        plan_id: str,
        mitigation_id: str,
        status: str,
        notes: Optional[str] = None
    ) -> Optional[MitigationPlan]:
        """Update status of a mitigation."""
        plan = self._plans.get(plan_id)
        if not plan:
            return None

        for mitigation in plan.mitigations:
            if mitigation.id == mitigation_id:
                mitigation.status = status
                if status == 'completed':
                    mitigation.completed_at = datetime.utcnow().isoformat()
                if notes:
                    mitigation.notes = notes
                break

        self._save_plan(plan)
        return plan

    def get_plan(self, plan_id: str) -> Optional[MitigationPlan]:
        """Get a mitigation plan."""
        return self._plans.get(plan_id)

    def _save_plan(self, plan: MitigationPlan):
        """Save plan to storage."""
        file_path = self.storage_dir / f"{plan.id}.json"
        with open(file_path, 'w') as f:
            json.dump(plan.to_dict(), f, indent=2)


def get_mitigation_tracker(**kwargs) -> MitigationTracker:
    """Get mitigation tracker instance."""
    return MitigationTracker(**kwargs)
