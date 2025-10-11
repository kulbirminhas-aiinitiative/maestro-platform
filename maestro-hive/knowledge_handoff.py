#!/usr/bin/env python3
"""
Knowledge Handoff Protocol and Manager

Implements the "Digital Handshake" - ensures knowledge is captured
before team members retire/leave.

Prevents knowledge loss by:
- Verifying artifacts are documented
- Capturing lessons learned
- Recording open questions and recommendations
- Ensuring knowledge is in the system, not just in someone's head
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import uuid

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from persistence.state_manager import StateManager
from persistence.models import KnowledgeHandoff, TaskStatus
from sqlalchemy import select, and_


@dataclass
class HandoffChecklist:
    """
    Checklist for knowledge handoff

    All items must be completed before member can retire.
    """
    # Required items
    artifacts_verified: bool = False
    documentation_complete: bool = False
    lessons_learned_captured: bool = False

    # Content
    lessons_learned: Optional[str] = None
    open_questions: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    key_decisions: List[str] = field(default_factory=list)
    artifacts_list: List[str] = field(default_factory=list)

    # Metadata
    completed_tasks_count: int = 0
    failed_tasks_count: int = 0
    knowledge_items_shared: int = 0

    def is_complete(self) -> bool:
        """Check if all required items are complete"""
        return (
            self.artifacts_verified and
            self.documentation_complete and
            self.lessons_learned_captured
        )

    def get_completion_percentage(self) -> int:
        """Get completion percentage"""
        total = 3
        completed = sum([
            self.artifacts_verified,
            self.documentation_complete,
            self.lessons_learned_captured
        ])
        return int((completed / total) * 100)


class KnowledgeHandoffManager:
    """
    Manages knowledge handoff when team members retire

    Ensures knowledge is captured before members leave.
    """

    def __init__(self, state_manager: StateManager):
        self.state = state_manager

    # =========================================================================
    # Handoff Initiation
    # =========================================================================

    async def initiate_handoff(
        self,
        team_id: str,
        agent_id: str,
        persona_id: str,
        initiated_by: str = "system"
    ) -> Dict[str, Any]:
        """
        Initiate knowledge handoff for a retiring member

        Starts the handoff process, creates checklist, and gathers initial data.

        Args:
            team_id: Team identifier
            agent_id: Agent who is retiring
            persona_id: Persona type
            initiated_by: Who initiated the handoff

        Returns:
            Handoff info with initial checklist
        """
        print(f"\n  🤝 Initiating knowledge handoff for {agent_id}...")

        # Check if handoff already exists
        existing = await self._get_handoff(team_id, agent_id)
        if existing and existing['status'] != 'completed':
            print(f"  ⚠️  Handoff already in progress")
            return existing

        # Create handoff record
        handoff_id = str(uuid.uuid4())
        handoff = KnowledgeHandoff(
            id=handoff_id,
            team_id=team_id,
            agent_id=agent_id,
            persona_id=persona_id,
            status="initiated",
            initiated_by=initiated_by
        )

        async with self.state.db.session() as session:
            session.add(handoff)
            await session.commit()
            await session.refresh(handoff)

        # Generate initial checklist
        checklist = await self._generate_initial_checklist(team_id, agent_id)

        # Update handoff with checklist data
        await self._update_handoff_checklist(handoff_id, checklist)

        print(f"  ✓ Handoff initiated (ID: {handoff_id[:8]})")
        print(f"     Tasks completed: {checklist.completed_tasks_count}")
        print(f"     Knowledge items: {checklist.knowledge_items_shared}")
        print(f"     Artifacts: {len(checklist.artifacts_list)}")

        result = await self._get_handoff_by_id(handoff_id)
        return result

    async def _generate_initial_checklist(
        self,
        team_id: str,
        agent_id: str
    ) -> HandoffChecklist:
        """
        Generate initial checklist by analyzing member's contributions

        Examines:
        - Tasks completed
        - Artifacts created
        - Knowledge shared
        - Decisions participated in
        """
        from persistence.models import Task, Artifact, Decision

        checklist = HandoffChecklist()

        async with self.state.db.session() as session:
            # Get completed tasks
            task_result = await session.execute(
                select(Task).where(
                    and_(
                        Task.team_id == team_id,
                        Task.assigned_to == agent_id,
                        Task.status == TaskStatus.SUCCESS
                    )
                )
            )
            completed_tasks = task_result.scalars().all()
            checklist.completed_tasks_count = len(completed_tasks)

            # Get failed tasks
            failed_result = await session.execute(
                select(Task).where(
                    and_(
                        Task.team_id == team_id,
                        Task.assigned_to == agent_id,
                        Task.status == TaskStatus.FAILED
                    )
                )
            )
            failed_tasks = failed_result.scalars().all()
            checklist.failed_tasks_count = len(failed_tasks)

            # Get artifacts
            artifact_result = await session.execute(
                select(Artifact).where(
                    and_(
                        Artifact.team_id == team_id,
                        Artifact.created_by == agent_id
                    )
                )
            )
            artifacts = artifact_result.scalars().all()
            checklist.artifacts_list = [
                f"{a.name} ({a.artifact_type})" for a in artifacts
            ]

            # Get decisions
            decision_result = await session.execute(
                select(Decision).where(
                    and_(
                        Decision.team_id == team_id,
                        Decision.proposed_by == agent_id
                    )
                )
            )
            decisions = decision_result.scalars().all()
            checklist.key_decisions = [
                d.id for d in decisions
            ]

        # Get knowledge items
        knowledge = await self.state.get_knowledge(team_id)
        agent_knowledge = [k for k in knowledge if k.get('from') == agent_id]
        checklist.knowledge_items_shared = len(agent_knowledge)

        # Auto-verify artifacts if they exist
        if len(checklist.artifacts_list) > 0:
            checklist.artifacts_verified = True

        return checklist

    # =========================================================================
    # Checklist Completion
    # =========================================================================

    async def update_handoff_checklist(
        self,
        handoff_id: str,
        artifacts_verified: Optional[bool] = None,
        documentation_complete: Optional[bool] = None,
        lessons_learned: Optional[str] = None,
        open_questions: Optional[List[str]] = None,
        recommendations: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Update handoff checklist items

        Args:
            handoff_id: Handoff identifier
            artifacts_verified: Whether artifacts are verified
            documentation_complete: Whether documentation is complete
            lessons_learned: Lessons learned text
            open_questions: List of open questions
            recommendations: List of recommendations

        Returns:
            Updated handoff info
        """
        async with self.state.db.session() as session:
            result = await session.execute(
                select(KnowledgeHandoff).where(
                    KnowledgeHandoff.id == handoff_id
                )
            )
            handoff = result.scalar_one_or_none()

            if not handoff:
                raise ValueError(f"Handoff {handoff_id} not found")

            # Update checklist items
            if artifacts_verified is not None:
                handoff.artifacts_verified = artifacts_verified

            if documentation_complete is not None:
                handoff.documentation_complete = documentation_complete

            if lessons_learned is not None:
                handoff.lessons_learned = lessons_learned
                handoff.lessons_learned_captured = True

            if open_questions is not None:
                handoff.open_questions = open_questions

            if recommendations is not None:
                handoff.recommendations = recommendations

            # Update status
            if handoff.is_complete() and handoff.status != "completed":
                handoff.status = "in_progress"

            await session.commit()
            await session.refresh(handoff)

        return handoff.to_dict()

    async def _update_handoff_checklist(
        self,
        handoff_id: str,
        checklist: HandoffChecklist
    ) -> Dict[str, Any]:
        """Internal method to update handoff with full checklist"""
        return await self.update_handoff_checklist(
            handoff_id=handoff_id,
            artifacts_verified=checklist.artifacts_verified,
            documentation_complete=checklist.documentation_complete,
            lessons_learned=checklist.lessons_learned,
            open_questions=checklist.open_questions,
            recommendations=checklist.recommendations
        )

    # =========================================================================
    # Handoff Completion
    # =========================================================================

    async def complete_handoff(
        self,
        handoff_id: str,
        completed_by: str,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Complete knowledge handoff

        Verifies all checklist items are complete and marks handoff as complete.
        Stores knowledge in the system knowledge base.

        Args:
            handoff_id: Handoff identifier
            completed_by: Who completed the handoff
            force: Force completion even if checklist incomplete (not recommended)

        Returns:
            Completed handoff info
        """
        async with self.state.db.session() as session:
            result = await session.execute(
                select(KnowledgeHandoff).where(
                    KnowledgeHandoff.id == handoff_id
                )
            )
            handoff = result.scalar_one_or_none()

            if not handoff:
                raise ValueError(f"Handoff {handoff_id} not found")

            # Check if complete
            if not handoff.is_complete() and not force:
                raise ValueError(
                    f"Handoff not complete. Missing: "
                    f"{'artifacts ' if not handoff.artifacts_verified else ''}"
                    f"{'documentation ' if not handoff.documentation_complete else ''}"
                    f"{'lessons learned ' if not handoff.lessons_learned_captured else ''}"
                )

            # Mark complete
            handoff.status = "completed"
            handoff.completed_at = datetime.utcnow()
            handoff.completed_by = completed_by

            await session.commit()
            await session.refresh(handoff)

        # Store lessons learned in knowledge base
        if handoff.lessons_learned:
            await self.state.share_knowledge(
                team_id=handoff.team_id,
                key=f"lessons_learned_{handoff.agent_id}",
                value=handoff.lessons_learned,
                source_agent=handoff.agent_id,
                category="lessons_learned",
                tags=["handoff", "retirement", handoff.persona_id]
            )

        # Store recommendations
        if handoff.recommendations:
            await self.state.share_knowledge(
                team_id=handoff.team_id,
                key=f"recommendations_{handoff.agent_id}",
                value="\n".join(handoff.recommendations),
                source_agent=handoff.agent_id,
                category="recommendations",
                tags=["handoff", "retirement", handoff.persona_id]
            )

        # Store open questions
        if handoff.open_questions:
            await self.state.share_knowledge(
                team_id=handoff.team_id,
                key=f"open_questions_{handoff.agent_id}",
                value="\n".join(handoff.open_questions),
                source_agent=handoff.agent_id,
                category="open_questions",
                tags=["handoff", "retirement", handoff.persona_id]
            )

        print(f"\n  ✅ Knowledge handoff completed for {handoff.agent_id}")
        print(f"     Status: All knowledge captured and stored")

        return handoff.to_dict()

    async def skip_handoff(
        self,
        handoff_id: str,
        reason: str,
        skipped_by: str
    ) -> Dict[str, Any]:
        """
        Skip handoff (not recommended, but available for emergencies)

        Args:
            handoff_id: Handoff identifier
            reason: Reason for skipping
            skipped_by: Who authorized the skip

        Returns:
            Skipped handoff info
        """
        async with self.state.db.session() as session:
            result = await session.execute(
                select(KnowledgeHandoff).where(
                    KnowledgeHandoff.id == handoff_id
                )
            )
            handoff = result.scalar_one_or_none()

            if not handoff:
                raise ValueError(f"Handoff {handoff_id} not found")

            handoff.status = "skipped"
            handoff.completed_at = datetime.utcnow()
            handoff.completed_by = skipped_by
            handoff.extra_metadata = handoff.extra_metadata or {}
            handoff.extra_metadata['skip_reason'] = reason

            await session.commit()
            await session.refresh(handoff)

        print(f"  ⚠️  Handoff skipped for {handoff.agent_id}: {reason}")

        return handoff.to_dict()

    # =========================================================================
    # Query Methods
    # =========================================================================

    async def _get_handoff(
        self,
        team_id: str,
        agent_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get most recent handoff for an agent"""
        async with self.state.db.session() as session:
            from sqlalchemy import desc

            result = await session.execute(
                select(KnowledgeHandoff).where(
                    and_(
                        KnowledgeHandoff.team_id == team_id,
                        KnowledgeHandoff.agent_id == agent_id
                    )
                ).order_by(desc(KnowledgeHandoff.initiated_at)).limit(1)
            )
            handoff = result.scalar_one_or_none()

            return handoff.to_dict() if handoff else None

    async def _get_handoff_by_id(self, handoff_id: str) -> Dict[str, Any]:
        """Get handoff by ID"""
        async with self.state.db.session() as session:
            result = await session.execute(
                select(KnowledgeHandoff).where(
                    KnowledgeHandoff.id == handoff_id
                )
            )
            handoff = result.scalar_one_or_none()

            if not handoff:
                raise ValueError(f"Handoff {handoff_id} not found")

            return handoff.to_dict()

    async def get_pending_handoffs(
        self,
        team_id: str
    ) -> List[Dict[str, Any]]:
        """Get all pending handoffs for a team"""
        async with self.state.db.session() as session:
            result = await session.execute(
                select(KnowledgeHandoff).where(
                    and_(
                        KnowledgeHandoff.team_id == team_id,
                        KnowledgeHandoff.status.in_(["initiated", "in_progress"])
                    )
                )
            )
            handoffs = result.scalars().all()

            return [h.to_dict() for h in handoffs]

    # =========================================================================
    # Reporting
    # =========================================================================

    def print_handoff_status(self, handoff: Dict[str, Any]):
        """Print formatted handoff status"""
        print(f"\n{'=' * 80}")
        print(f"KNOWLEDGE HANDOFF STATUS")
        print(f"{'=' * 80}\n")

        print(f"  Agent: {handoff['agent_id']}")
        print(f"  Persona: {handoff['persona_id']}")
        print(f"  Status: {handoff['status'].upper()}")
        print(f"  Initiated: {handoff['initiated_at']}")

        checklist = handoff['checklist']
        completed = sum([
            checklist['artifacts_verified'],
            checklist['documentation_complete'],
            checklist['lessons_learned_captured']
        ])
        total = 3
        percentage = int((completed / total) * 100)

        print(f"\n  Completion: {percentage}% ({completed}/{total} items)")

        print(f"\n  Checklist:")
        print(f"    {'✓' if checklist['artifacts_verified'] else '✗'} Artifacts verified")
        print(f"    {'✓' if checklist['documentation_complete'] else '✗'} Documentation complete")
        print(f"    {'✓' if checklist['lessons_learned_captured'] else '✗'} Lessons learned captured")

        if handoff['lessons_learned']:
            print(f"\n  Lessons Learned:")
            print(f"    {handoff['lessons_learned'][:200]}...")

        if handoff['recommendations']:
            print(f"\n  Recommendations ({len(handoff['recommendations'])}):")
            for rec in handoff['recommendations'][:3]:
                print(f"    - {rec}")

        if handoff['open_questions']:
            print(f"\n  Open Questions ({len(handoff['open_questions'])}):")
            for q in handoff['open_questions'][:3]:
                print(f"    - {q}")

        print(f"\n{'=' * 80}\n")

    async def print_team_handoffs(self, team_id: str):
        """Print all handoffs for a team"""
        pending = await self.get_pending_handoffs(team_id)

        print(f"\n{'=' * 80}")
        print(f"TEAM HANDOFFS: {team_id}")
        print(f"{'=' * 80}\n")

        if not pending:
            print("  No pending handoffs")
        else:
            print(f"  Pending handoffs: {len(pending)}\n")
            for handoff in pending:
                completion = (
                    sum([
                        handoff['checklist']['artifacts_verified'],
                        handoff['checklist']['documentation_complete'],
                        handoff['checklist']['lessons_learned_captured']
                    ]) / 3 * 100
                )
                print(f"    {handoff['agent_id']}: {completion:.0f}% complete ({handoff['status']})")

        print(f"\n{'=' * 80}\n")


if __name__ == "__main__":
    print("Knowledge Handoff Manager")
    print("=" * 80)
    print("\nImplements the 'Digital Handshake' protocol to ensure knowledge is captured")
    print("before team members retire.")
    print("\nChecklist items:")
    print("  1. Artifacts verified (all work documented)")
    print("  2. Documentation complete")
    print("  3. Lessons learned captured")
    print("\nAdditional captured:")
    print("  - Open questions")
    print("  - Recommendations for successors")
    print("  - Key decisions participated in")
