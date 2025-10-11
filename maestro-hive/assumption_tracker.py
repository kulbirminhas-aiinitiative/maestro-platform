#!/usr/bin/env python3
"""
Assumption Tracker - Manage Speculative Execution

In parallel workflows, teams work based on incomplete information and make
assumptions to proceed. These assumptions must be explicitly tracked and
validated to prevent building on flawed foundations.

Key Features:
- Track assumptions with context
- Link assumptions to artifacts
- Validate/invalidate assumptions
- Alert affected parties when assumptions change
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from persistence.state_manager import StateManager
from persistence.models import Assumption, AssumptionStatus
from sqlalchemy import select, and_


class AssumptionTracker:
    """
    Tracks and validates assumptions for speculative execution

    When teams work concurrently based on MVD (Minimum Viable Definition),
    they make assumptions to proceed. This tracker ensures those assumptions
    are documented and validated as more information becomes available.
    """

    def __init__(self, state_manager: StateManager):
        self.state = state_manager

    # =========================================================================
    # Assumption Creation and Tracking
    # =========================================================================

    async def track_assumption(
        self,
        team_id: str,
        made_by_agent: str,
        made_by_role: str,
        assumption_text: str,
        assumption_category: str,
        related_artifact_type: str,
        related_artifact_id: str,
        dependent_artifacts: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Track a new assumption

        Args:
            team_id: Team identifier
            made_by_agent: Agent making the assumption
            made_by_role: Role of the agent
            assumption_text: What is being assumed
            assumption_category: Category (data_structure, api_contract, requirement)
            related_artifact_type: What artifact this relates to
            related_artifact_id: ID of related artifact
            dependent_artifacts: List of artifacts depending on this assumption

        Returns:
            Assumption info

        Example:
            await tracker.track_assumption(
                team_id="fraud_team",
                made_by_agent="backend_dev_001",
                made_by_role="Backend Lead",
                assumption_text="Fraud alerts only need id, timestamp, amount, reason fields",
                assumption_category="data_structure",
                related_artifact_type="contract",
                related_artifact_id="FraudAlertsAPI_v0.1",
                dependent_artifacts=[
                    {"type": "task", "id": "implement_kafka_consumer"},
                    {"type": "task", "id": "build_dashboard_ui"}
                ]
            )
        """
        assumption = Assumption(
            id=f"assumption_{uuid.uuid4().hex[:12]}",
            team_id=team_id,
            made_by_agent=made_by_agent,
            made_by_role=made_by_role,
            assumption_text=assumption_text,
            assumption_category=assumption_category,
            related_artifact_type=related_artifact_type,
            related_artifact_id=related_artifact_id,
            status=AssumptionStatus.ACTIVE,
            dependent_artifacts=dependent_artifacts or []
        )

        async with self.state.db.session() as session:
            session.add(assumption)
            await session.commit()
            await session.refresh(assumption)

        # Publish event
        await self.state.redis.publish_event(
            f"team:{team_id}:events:assumption.tracked",
            "assumption.tracked",
            {
                "assumption_id": assumption.id,
                "made_by": made_by_agent,
                "category": assumption_category,
                "text": assumption_text
            }
        )

        print(f"  📌 Assumption tracked: {assumption.id}")
        print(f"     By: {made_by_role} ({made_by_agent})")
        print(f"     Assumes: {assumption_text[:80]}...")

        return assumption.to_dict()

    async def get_assumption(
        self,
        team_id: str,
        assumption_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get assumption by ID"""
        async with self.state.db.session() as session:
            result = await session.execute(
                select(Assumption).where(
                    and_(
                        Assumption.team_id == team_id,
                        Assumption.id == assumption_id
                    )
                )
            )
            assumption = result.scalar_one_or_none()
            return assumption.to_dict() if assumption else None

    async def get_assumptions_by_artifact(
        self,
        team_id: str,
        artifact_type: str,
        artifact_id: str,
        status_filter: Optional[AssumptionStatus] = None
    ) -> List[Dict[str, Any]]:
        """Get all assumptions related to an artifact"""
        async with self.state.db.session() as session:
            query = select(Assumption).where(
                and_(
                    Assumption.team_id == team_id,
                    Assumption.related_artifact_type == artifact_type,
                    Assumption.related_artifact_id == artifact_id
                )
            )

            if status_filter:
                query = query.where(Assumption.status == status_filter)

            result = await session.execute(query)
            assumptions = result.scalars().all()

            return [a.to_dict() for a in assumptions]

    async def get_assumptions_by_agent(
        self,
        team_id: str,
        agent_id: str,
        status_filter: Optional[AssumptionStatus] = None
    ) -> List[Dict[str, Any]]:
        """Get all assumptions made by an agent"""
        async with self.state.db.session() as session:
            query = select(Assumption).where(
                and_(
                    Assumption.team_id == team_id,
                    Assumption.made_by_agent == agent_id
                )
            )

            if status_filter:
                query = query.where(Assumption.status == status_filter)

            result = await session.execute(query)
            assumptions = result.scalars().all()

            return [a.to_dict() for a in assumptions]

    async def get_active_assumptions(
        self,
        team_id: str
    ) -> List[Dict[str, Any]]:
        """Get all active (unvalidated) assumptions"""
        return await self.get_assumptions_by_agent(
            team_id=team_id,
            agent_id="*",  # All agents
            status_filter=AssumptionStatus.ACTIVE
        )

    # =========================================================================
    # Assumption Validation
    # =========================================================================

    async def validate_assumption(
        self,
        assumption_id: str,
        validated_by: str,
        validation_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Mark assumption as validated (confirmed correct)

        Args:
            assumption_id: Assumption to validate
            validated_by: Who validated it
            validation_notes: Optional notes

        Returns:
            Updated assumption
        """
        async with self.state.db.session() as session:
            result = await session.execute(
                select(Assumption).where(Assumption.id == assumption_id)
            )
            assumption = result.scalar_one_or_none()

            if not assumption:
                raise ValueError(f"Assumption {assumption_id} not found")

            assumption.status = AssumptionStatus.VALIDATED
            assumption.validated_at = datetime.utcnow()
            assumption.validated_by = validated_by
            assumption.validation_notes = validation_notes

            await session.commit()
            await session.refresh(assumption)

        # Publish event
        await self.state.redis.publish_event(
            f"team:{assumption.team_id}:events:assumption.validated",
            "assumption.validated",
            {
                "assumption_id": assumption.id,
                "validated_by": validated_by,
                "text": assumption.assumption_text
            }
        )

        print(f"  ✅ Assumption validated: {assumption_id}")
        print(f"     Validated by: {validated_by}")

        return assumption.to_dict()

    async def invalidate_assumption(
        self,
        assumption_id: str,
        invalidated_by: str,
        validation_notes: str
    ) -> Dict[str, Any]:
        """
        Mark assumption as invalidated (proven wrong)

        This is a critical event that may trigger rework and convergence.

        Args:
            assumption_id: Assumption to invalidate
            invalidated_by: Who invalidated it
            validation_notes: Why it's wrong

        Returns:
            Updated assumption + affected artifacts
        """
        async with self.state.db.session() as session:
            result = await session.execute(
                select(Assumption).where(Assumption.id == assumption_id)
            )
            assumption = result.scalar_one_or_none()

            if not assumption:
                raise ValueError(f"Assumption {assumption_id} not found")

            old_status = assumption.status
            assumption.status = AssumptionStatus.INVALIDATED
            assumption.validated_at = datetime.utcnow()
            assumption.validated_by = invalidated_by
            assumption.validation_notes = validation_notes

            await session.commit()
            await session.refresh(assumption)

        # Publish critical event
        await self.state.redis.publish_event(
            f"team:{assumption.team_id}:events:assumption.invalidated",
            "assumption.invalidated",
            {
                "assumption_id": assumption.id,
                "invalidated_by": invalidated_by,
                "text": assumption.assumption_text,
                "dependent_artifacts": assumption.dependent_artifacts,
                "severity": "high"  # This may require rework
            }
        )

        print(f"  ⚠️  Assumption INVALIDATED: {assumption_id}")
        print(f"     By: {invalidated_by}")
        print(f"     Reason: {validation_notes}")
        print(f"     Affected artifacts: {len(assumption.dependent_artifacts)}")

        return assumption.to_dict()

    async def supersede_assumption(
        self,
        assumption_id: str,
        superseded_by: str,
        reason: str
    ) -> Dict[str, Any]:
        """
        Mark assumption as superseded by new information

        Args:
            assumption_id: Assumption being superseded
            superseded_by: Who superseded it
            reason: Why it's being superseded

        Returns:
            Updated assumption
        """
        async with self.state.db.session() as session:
            result = await session.execute(
                select(Assumption).where(Assumption.id == assumption_id)
            )
            assumption = result.scalar_one_or_none()

            if not assumption:
                raise ValueError(f"Assumption {assumption_id} not found")

            assumption.status = AssumptionStatus.SUPERSEDED
            assumption.validated_at = datetime.utcnow()
            assumption.validated_by = superseded_by
            assumption.validation_notes = reason

            await session.commit()
            await session.refresh(assumption)

        print(f"  🔄 Assumption superseded: {assumption_id}")

        return assumption.to_dict()

    # =========================================================================
    # Proactive Validation
    # =========================================================================

    async def check_assumptions_for_artifact(
        self,
        team_id: str,
        artifact_type: str,
        artifact_id: str,
        new_content: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Check if artifact changes invalidate any assumptions

        This should be called whenever an artifact is updated.

        Args:
            team_id: Team identifier
            artifact_type: Type of artifact
            artifact_id: ID of artifact
            new_content: New artifact content

        Returns:
            List of assumptions that may be affected
        """
        # Get all active assumptions related to this artifact
        assumptions = await self.get_assumptions_by_artifact(
            team_id=team_id,
            artifact_type=artifact_type,
            artifact_id=artifact_id,
            status_filter=AssumptionStatus.ACTIVE
        )

        if not assumptions:
            return []

        print(f"\n  🔍 Checking {len(assumptions)} assumptions against artifact update...")

        potentially_affected = []

        for assumption in assumptions:
            # Here you would implement logic to check if the new content
            # contradicts the assumption. For now, we flag them for review.
            potentially_affected.append(assumption)

        if potentially_affected:
            print(f"  ⚠️  {len(potentially_affected)} assumptions need validation")
            for assumption in potentially_affected:
                print(f"     - {assumption['id']}: {assumption['assumption_text'][:60]}...")

        return potentially_affected

    # =========================================================================
    # Reporting
    # =========================================================================

    async def get_assumption_summary(
        self,
        team_id: str
    ) -> Dict[str, Any]:
        """Get summary of assumptions for a team"""
        async with self.state.db.session() as session:
            result = await session.execute(
                select(Assumption).where(Assumption.team_id == team_id)
            )
            all_assumptions = result.scalars().all()

        by_status = {}
        by_category = {}

        for assumption in all_assumptions:
            status = assumption.status.value if isinstance(assumption.status, AssumptionStatus) else assumption.status
            by_status[status] = by_status.get(status, 0) + 1

            category = assumption.assumption_category
            by_category[category] = by_category.get(category, 0) + 1

        return {
            "team_id": team_id,
            "total_assumptions": len(all_assumptions),
            "by_status": by_status,
            "by_category": by_category,
            "active_count": by_status.get("active", 0),
            "invalidated_count": by_status.get("invalidated", 0),
            "validated_count": by_status.get("validated", 0)
        }

    async def print_assumption_summary(self, team_id: str):
        """Print formatted assumption summary"""
        summary = await self.get_assumption_summary(team_id)

        print(f"\n{'=' * 80}")
        print(f"ASSUMPTION TRACKING SUMMARY: {team_id}")
        print(f"{'=' * 80}\n")

        print(f"  Total assumptions tracked: {summary['total_assumptions']}")
        print(f"\n  By Status:")
        for status, count in summary['by_status'].items():
            print(f"    {status}: {count}")

        print(f"\n  By Category:")
        for category, count in summary['by_category'].items():
            print(f"    {category}: {count}")

        if summary['invalidated_count'] > 0:
            print(f"\n  ⚠️  {summary['invalidated_count']} assumptions were invalidated (may require rework)")

        print(f"\n{'=' * 80}\n")


if __name__ == "__main__":
    print("Assumption Tracker - Speculative Execution Management")
    print("=" * 80)
    print("\nEnables teams to work concurrently based on MVD by:")
    print("- Explicitly tracking assumptions")
    print("- Validating assumptions as information evolves")
    print("- Alerting affected parties when assumptions are invalidated")
    print("- Preventing building on flawed foundations")
