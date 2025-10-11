#!/usr/bin/env python3
"""
Dynamic Team Manager - Main orchestrator for dynamic team management

Handles:
- Adding/removing team members dynamically
- Performance-based member management
- Auto-scaling based on workload
- Phase-based team transitions
- Member state management (active, standby, retired)
- Performance tracking and replacement
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from datetime import datetime
import uuid

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from persistence.state_manager import StateManager
from persistence.models import MembershipState
import personas
import team_organization
from performance_metrics import PerformanceMetricsAnalyzer, PerformanceThresholds
from team_composition_policies import TeamCompositionPolicy, ProjectType
from role_manager import RoleManager
from onboarding_briefing import OnboardingBriefingGenerator
from knowledge_handoff import KnowledgeHandoffManager

SDLCPersonas = personas.SDLCPersonas
SDLCPhase = team_organization.SDLCPhase


class DynamicTeamManager:
    """
    Main manager for dynamic team operations

    Features:
    - Add/remove members dynamically
    - Performance-based management
    - Auto-scaling (workload-based & phase-based)
    - Member lifecycle management
    - Cost optimization (minimize active members)
    - Role-based assignment (NEW)
    - Onboarding briefings (NEW)
    - Knowledge handoffs (NEW)
    """

    def __init__(
        self,
        team_id: str,
        state_manager: StateManager,
        project_type: Optional[ProjectType] = None,
        project_name: str = "Unnamed Project",
        performance_thresholds: Optional[PerformanceThresholds] = None
    ):
        self.team_id = team_id
        self.state = state_manager
        self.project_type = project_type or ProjectType.MEDIUM_FEATURE
        self.project_name = project_name

        self.personas = SDLCPersonas()
        self.policy = TeamCompositionPolicy()
        self.performance_analyzer = PerformanceMetricsAnalyzer(
            state_manager,
            performance_thresholds
        )

        # NEW: Enhanced features for Elastic Team Model
        self.role_manager = RoleManager(state_manager)
        self.briefing_generator = OnboardingBriefingGenerator(state_manager, project_name)
        self.handoff_manager = KnowledgeHandoffManager(state_manager)

        # Coordinator identity
        self.coordinator_id = f"dynamic_team_manager_{team_id}"
        self.current_phase = SDLCPhase.REQUIREMENTS  # Track current phase

    # =========================================================================
    # Core Member Management
    # =========================================================================

    async def add_member(
        self,
        persona_id: str,
        reason: str,
        initial_state: MembershipState = MembershipState.INITIALIZING,
        auto_activate: bool = True
    ) -> Dict[str, Any]:
        """
        Add a new team member

        Args:
            persona_id: Persona to add (e.g., "backend_developer")
            reason: Why this member is being added
            initial_state: Initial membership state
            auto_activate: Automatically move to ACTIVE after initialization

        Returns:
            Membership info
        """
        # Get persona definition
        persona = self._get_persona_by_id(persona_id)
        if not persona:
            raise ValueError(f"Unknown persona: {persona_id}")

        # Generate agent ID
        agent_id = f"{persona_id}_{self.team_id}"

        # Check if already exists
        existing = await self.state.get_team_members(
            self.team_id,
            persona_id=persona_id
        )

        if existing:
            print(f"  ⚠️  {persona['name']} already in team, updating state...")
            return await self.state.update_member_state(
                self.team_id,
                existing[0]['agent_id'],
                MembershipState.ACTIVE if auto_activate else initial_state,
                reason
            )

        # Add to team membership
        membership = await self.state.add_team_member(
            team_id=self.team_id,
            agent_id=agent_id,
            persona_id=persona_id,
            role_id=persona['role_id'],
            added_by=self.coordinator_id,
            reason=reason,
            initial_state=initial_state
        )

        # Register agent state
        await self.state.update_agent_status(
            team_id=self.team_id,
            agent_id=agent_id,
            role=persona['role_id'],
            status="initialized",
            message=f"Added as {persona['name']}: {reason}"
        )

        # Auto-activate if requested
        if auto_activate and initial_state == MembershipState.INITIALIZING:
            await self.activate_member(agent_id, "Initial activation after adding")

        print(f"  ✓ Added {persona['name']} ({agent_id})")
        return membership

    async def retire_member(
        self,
        agent_id: str,
        reason: str
    ) -> Dict[str, Any]:
        """
        Retire a team member gracefully

        - Updates state to RETIRED
        - Records retirement reason
        - Publishes retirement event
        """
        membership = await self.state.retire_team_member(
            team_id=self.team_id,
            agent_id=agent_id,
            reason=reason
        )

        # Update agent status
        await self.state.update_agent_status(
            team_id=self.team_id,
            agent_id=agent_id,
            role=membership['role_id'],
            status="retired",
            message=f"Retired: {reason}"
        )

        print(f"  ✓ Retired {agent_id}: {reason}")
        return membership

    async def replace_member(
        self,
        agent_id: str,
        reason: str
    ) -> Dict[str, Any]:
        """
        Replace an underperforming member

        - Retires current member
        - Adds new member with same persona
        """
        # Get current member info
        members = await self.state.get_team_members(self.team_id)
        member_to_replace = next((m for m in members if m['agent_id'] == agent_id), None)

        if not member_to_replace:
            raise ValueError(f"Member {agent_id} not found")

        persona_id = member_to_replace['persona_id']

        print(f"  🔄 Replacing {agent_id} ({persona_id})...")

        # Retire old member
        await self.retire_member(agent_id, f"Replaced: {reason}")

        # Add new member with same persona
        new_member = await self.add_member(
            persona_id=persona_id,
            reason=f"Replacement for {agent_id}: {reason}",
            auto_activate=True
        )

        print(f"  ✓ Replacement complete: {new_member['agent_id']}")
        return new_member

    async def activate_member(
        self,
        agent_id: str,
        reason: str = "Activated for active duty"
    ) -> Dict[str, Any]:
        """Move member from INITIALIZING or ON_STANDBY to ACTIVE"""
        return await self.state.update_member_state(
            team_id=self.team_id,
            agent_id=agent_id,
            new_state=MembershipState.ACTIVE,
            reason=reason
        )

    async def put_on_standby(
        self,
        agent_id: str,
        reason: str = "Phase completed, moving to standby"
    ) -> Dict[str, Any]:
        """Move member from ACTIVE to ON_STANDBY"""
        return await self.state.update_member_state(
            team_id=self.team_id,
            agent_id=agent_id,
            new_state=MembershipState.ON_STANDBY,
            reason=reason
        )

    async def suspend_member(
        self,
        agent_id: str,
        reason: str
    ) -> Dict[str, Any]:
        """Suspend member (performance issues)"""
        return await self.state.update_member_state(
            team_id=self.team_id,
            agent_id=agent_id,
            new_state=MembershipState.SUSPENDED,
            reason=reason
        )

    # =========================================================================
    # Team Composition Management
    # =========================================================================

    async def initialize_team_for_project(
        self,
        project_type: ProjectType,
        use_minimal_team: bool = False
    ) -> Dict[str, Any]:
        """
        Initialize team based on project type

        Args:
            project_type: Type of project
            use_minimal_team: If True, start with minimum viable team

        Returns:
            Summary of team initialization
        """
        print(f"\n{'=' * 80}")
        print(f"🚀 INITIALIZING TEAM FOR {project_type.value.upper()}")
        print(f"{'=' * 80}\n")

        # Get team composition
        if use_minimal_team:
            personas_to_add = self.policy.get_minimum_viable_team(project_type)
            print(f"  Using MINIMAL team ({len(personas_to_add)} members)")
        else:
            personas_to_add = self.policy.get_optimal_team(project_type)
            print(f"  Using OPTIMAL team ({len(personas_to_add)} members)")

        # Add members
        added = []
        for persona_id in personas_to_add:
            try:
                membership = await self.add_member(
                    persona_id=persona_id,
                    reason=f"Initial team for {project_type.value}",
                    auto_activate=True
                )
                added.append(membership)
            except Exception as e:
                print(f"  ✗ Failed to add {persona_id}: {e}")

        print(f"\n  ✅ Team initialized: {len(added)} members")
        print(f"{'=' * 80}\n")

        return {
            "team_id": self.team_id,
            "project_type": project_type.value,
            "members_added": len(added),
            "member_ids": [m['agent_id'] for m in added]
        }

    async def scale_team_for_phase(
        self,
        phase: SDLCPhase
    ) -> Dict[str, Any]:
        """
        Scale team based on SDLC phase requirements

        - Adds missing primary personas
        - Activates personas needed for phase
        - Moves non-essential personas to standby
        - Retires personas no longer needed
        """
        print(f"\n{'=' * 80}")
        print(f"🔄 SCALING TEAM FOR {phase.value.upper()} PHASE")
        print(f"{'=' * 80}\n")

        # Get current team
        current_members = await self.state.get_team_members(self.team_id)
        current_personas = {m['persona_id'] for m in current_members}

        # Get phase requirements
        scaling_plan = self.policy.should_scale_team_for_phase(phase, current_personas)

        actions = {
            "added": [],
            "retired": [],
            "activated": [],
            "moved_to_standby": []
        }

        # Add missing personas
        for persona_id in scaling_plan['should_add']:
            membership = await self.add_member(
                persona_id=persona_id,
                reason=f"Required for {phase.value} phase",
                auto_activate=True
            )
            actions['added'].append(membership['agent_id'])

        # Retire personas
        for persona_id in scaling_plan['should_retire']:
            member = next((m for m in current_members if m['persona_id'] == persona_id), None)
            if member and member['state'] not in ['retired', 'reassigned']:
                await self.retire_member(
                    member['agent_id'],
                    f"No longer needed after {phase.value} phase"
                )
                actions['retired'].append(member['agent_id'])

        # Activate personas
        for persona_id in scaling_plan['should_activate']:
            member = next((m for m in current_members if m['persona_id'] == persona_id), None)
            if member and member['state'] != 'active':
                await self.activate_member(
                    member['agent_id'],
                    f"Activated for {phase.value} phase"
                )
                actions['activated'].append(member['agent_id'])

        # Move to standby
        for persona_id in scaling_plan['should_standby']:
            member = next((m for m in current_members if m['persona_id'] == persona_id), None)
            if member and member['state'] == 'active':
                await self.put_on_standby(
                    member['agent_id'],
                    f"Not primary for {phase.value} phase"
                )
                actions['moved_to_standby'].append(member['agent_id'])

        print(f"\n  ✅ Phase scaling complete:")
        print(f"     Added: {len(actions['added'])}")
        print(f"     Retired: {len(actions['retired'])}")
        print(f"     Activated: {len(actions['activated'])}")
        print(f"     Moved to standby: {len(actions['moved_to_standby'])}")
        print(f"{'=' * 80}\n")

        return actions

    # =========================================================================
    # Performance-Based Management
    # =========================================================================

    async def evaluate_team_performance(self) -> Dict[str, Any]:
        """
        Evaluate entire team performance

        Returns:
            - Team health metrics
            - List of underperformers
            - Recommendations
        """
        print(f"\n{'=' * 80}")
        print(f"📊 EVALUATING TEAM PERFORMANCE")
        print(f"{'=' * 80}\n")

        health = await self.performance_analyzer.analyze_team_health(self.team_id)
        underperformers = await self.performance_analyzer.get_underperformers(self.team_id)

        print(f"  Overall health: {health.overall_health_score}/100")
        print(f"  Active members: {health.active_members}")
        print(f"  Underperformers: {health.underperformers_count}")
        print(f"  Scaling recommendation: {health.scaling_recommendation}")

        if health.recommended_actions:
            print(f"\n  Recommended actions:")
            for action in health.recommended_actions:
                print(f"    - {action}")

        if health.issues:
            print(f"\n  ⚠️  Issues:")
            for issue in health.issues:
                print(f"    - {issue}")

        print(f"{'=' * 80}\n")

        return {
            "health": health,
            "underperformers": underperformers
        }

    async def handle_underperformers(
        self,
        auto_replace: bool = False
    ) -> Dict[str, Any]:
        """
        Handle underperforming team members

        If auto_replace=True, automatically replaces members recommended for replacement
        Otherwise, just returns the list
        """
        print(f"\n{'=' * 80}")
        print(f"🔍 HANDLING UNDERPERFORMERS")
        print(f"{'=' * 80}\n")

        underperformers = await self.performance_analyzer.get_underperformers(self.team_id)

        if not underperformers:
            print("  ✅ No underperformers detected!")
            print(f"{'=' * 80}\n")
            return {"underperformers": [], "actions_taken": []}

        actions = []

        for perf in underperformers:
            print(f"\n  ⚠️  {perf.agent_id} ({perf.persona_id})")
            print(f"     Score: {perf.overall_score}/100")
            print(f"     Recommendation: {perf.recommendation}")
            print(f"     Issues: {', '.join(perf.issues)}")

            if auto_replace and perf.recommendation == "replace":
                print(f"     🔄 Auto-replacing...")
                await self.replace_member(
                    perf.agent_id,
                    f"Performance too low ({perf.overall_score}/100)"
                )
                actions.append(f"Replaced {perf.agent_id}")

            elif perf.recommendation == "standby":
                print(f"     ⏸️  Moving to standby...")
                await self.put_on_standby(
                    perf.agent_id,
                    f"Performance issues (score: {perf.overall_score}/100)"
                )
                actions.append(f"Moved {perf.agent_id} to standby")

            elif perf.recommendation == "improve":
                print(f"     ℹ️  Monitoring for improvement...")
                actions.append(f"Monitoring {perf.agent_id}")

        print(f"\n  ✅ Underperformer handling complete")
        print(f"{'=' * 80}\n")

        return {
            "underperformers": [p.agent_id for p in underperformers],
            "actions_taken": actions
        }

    # =========================================================================
    # Auto-Scaling
    # =========================================================================

    async def auto_scale_by_workload(self) -> Dict[str, Any]:
        """
        Auto-scale team based on current workload

        Checks:
        - Number of ready tasks
        - Capacity utilization
        - Team performance

        Actions:
        - Scale up if overloaded
        - Scale down if underutilized
        """
        print(f"\n{'=' * 80}")
        print(f"⚖️  AUTO-SCALING BY WORKLOAD")
        print(f"{'=' * 80}\n")

        health = await self.performance_analyzer.analyze_team_health(self.team_id)

        actions = []

        if health.scaling_recommendation == "scale_up":
            print(f"  📈 Scaling UP recommended")
            print(f"     Ready tasks: {health.total_ready_tasks}")
            print(f"     Capacity: {health.capacity_utilization}%")

            # Get composition for current project
            composition = self.policy.get_composition_for_project(self.project_type)

            # Get current active members
            active_members = await self.state.get_team_members(
                self.team_id,
                state=MembershipState.ACTIVE
            )

            # Try to activate standby members first
            standby_members = await self.state.get_team_members(
                self.team_id,
                state=MembershipState.ON_STANDBY
            )

            if standby_members:
                print(f"\n  ⏩ Activating standby members...")
                for member in standby_members[:2]:  # Activate up to 2
                    await self.activate_member(
                        member['agent_id'],
                        "Activated due to high workload"
                    )
                    actions.append(f"Activated {member['agent_id']}")
            else:
                print(f"\n  ➕ No standby members, would need to hire new members")
                actions.append("Recommendation: Hire additional team members")

        elif health.scaling_recommendation == "scale_down":
            print(f"  📉 Scaling DOWN recommended")
            print(f"     Ready tasks: {health.total_ready_tasks}")
            print(f"     Capacity: {health.capacity_utilization}%")

            # Move some active members to standby
            active_members = await self.state.get_team_members(
                self.team_id,
                state=MembershipState.ACTIVE
            )

            # Don't move critical personas to standby
            critical_personas = ["solution_architect", "security_specialist"]

            candidates_for_standby = [
                m for m in active_members
                if m['persona_id'] not in critical_personas
            ]

            if candidates_for_standby:
                print(f"\n  ⏸️  Moving members to standby...")
                for member in candidates_for_standby[:2]:  # Move up to 2
                    await self.put_on_standby(
                        member['agent_id'],
                        "Low workload, moved to standby"
                    )
                    actions.append(f"Moved {member['agent_id']} to standby")

        else:
            print(f"  ✅ Team size is optimal, no scaling needed")
            actions.append("No scaling needed")

        print(f"\n{'=' * 80}\n")

        return {
            "scaling_recommendation": health.scaling_recommendation,
            "actions_taken": actions
        }

    # =========================================================================
    # Reporting and Status
    # =========================================================================

    async def get_team_summary(self) -> Dict[str, Any]:
        """Get comprehensive team summary"""
        members = await self.state.get_team_members(self.team_id)

        by_state = {}
        for member in members:
            state = member['state']
            by_state[state] = by_state.get(state, 0) + 1

        health = await self.performance_analyzer.analyze_team_health(self.team_id)

        return {
            "team_id": self.team_id,
            "total_members": len(members),
            "by_state": by_state,
            "health_score": health.overall_health_score,
            "capacity_utilization": health.capacity_utilization,
            "underperformers": health.underperformers_count,
            "ready_tasks": health.total_ready_tasks,
            "running_tasks": health.total_running_tasks,
            "scaling_recommendation": health.scaling_recommendation
        }

    async def print_team_status(self):
        """Print formatted team status"""
        summary = await self.get_team_summary()

        print(f"\n{'=' * 80}")
        print(f"👥 TEAM STATUS: {self.team_id}")
        print(f"{'=' * 80}\n")

        print(f"  Total members: {summary['total_members']}")
        print(f"  Health score: {summary['health_score']}/100")
        print(f"\n  By state:")
        for state, count in summary['by_state'].items():
            print(f"    {state}: {count}")

        print(f"\n  Workload:")
        print(f"    Ready tasks: {summary['ready_tasks']}")
        print(f"    Running tasks: {summary['running_tasks']}")
        print(f"    Capacity utilization: {summary['capacity_utilization']}%")

        print(f"\n  Performance:")
        print(f"    Underperformers: {summary['underperformers']}")
        print(f"    Scaling recommendation: {summary['scaling_recommendation']}")

        print(f"\n{'=' * 80}\n")

    # =========================================================================
    # Enhanced Features: Elastic Team Model
    # =========================================================================

    async def add_member_with_briefing(
        self,
        persona_id: str,
        reason: str,
        role_id: Optional[str] = None,
        auto_activate: bool = True
    ) -> Dict[str, Any]:
        """
        Add member with AI-generated onboarding briefing

        This is the enhanced version that provides full context to new members.

        Args:
            persona_id: Persona to add
            reason: Why adding
            role_id: Optional role they're filling
            auto_activate: Auto-activate after initialization

        Returns:
            {
                "membership": membership info,
                "briefing": onboarding briefing,
                "role_assignment": role assignment (if role_id provided)
            }
        """
        print(f"\n  📋 Adding member with onboarding briefing...")

        # Add member (existing functionality)
        membership = await self.add_member(
            persona_id=persona_id,
            reason=reason,
            auto_activate=auto_activate
        )

        # Generate onboarding briefing
        briefing = await self.briefing_generator.generate_briefing(
            team_id=self.team_id,
            agent_id=membership['agent_id'],
            persona_id=persona_id,
            current_phase=self.current_phase,
            role_id=role_id
        )

        # Initialize performance score for new member
        await self.state.update_member_performance(
            self.team_id,
            membership['agent_id'],
            performance_score=100  # Start at 100
        )

        # TODO: Store briefing in membership metadata when metadata support is added

        # Assign to role if provided
        role_assignment = None
        if role_id:
            role_assignment = await self.role_manager.assign_agent_to_role(
                team_id=self.team_id,
                role_id=role_id,
                agent_id=membership['agent_id'],
                assigned_by=self.coordinator_id,
                reason=f"Filling {role_id} role: {reason}"
            )

        # Print briefing summary
        print(f"\n  ✓ Member added with complete onboarding package:")
        print(f"     Agent: {membership['agent_id']}")
        print(f"     Persona: {persona_id}")
        if role_id:
            print(f"     Role: {role_id}")
        print(f"     Briefing includes:")
        print(f"       - {len(briefing.key_decisions)} key decisions")
        print(f"       - {len(briefing.immediate_tasks)} immediate tasks")
        print(f"       - {len(briefing.key_contacts)} key contacts")
        print(f"       - {len(briefing.resources)} resources")

        return {
            "membership": membership,
            "briefing": briefing.to_dict(),
            "role_assignment": role_assignment
        }

    async def retire_member_with_handoff(
        self,
        agent_id: str,
        reason: str,
        require_handoff: bool = True,
        force_skip_handoff: bool = False
    ) -> Dict[str, Any]:
        """
        Retire member with knowledge handoff (Digital Handshake)

        Ensures knowledge is captured before member leaves.

        Args:
            agent_id: Agent to retire
            reason: Reason for retirement
            require_handoff: Require handoff completion
            force_skip_handoff: Force skip handoff (emergency only)

        Returns:
            {
                "membership": retirement info,
                "handoff": handoff info,
                "knowledge_captured": True/False
            }
        """
        print(f"\n  🤝 Retiring member with knowledge handoff...")

        # Get member info
        members = await self.state.get_team_members(self.team_id)
        member = next((m for m in members if m['agent_id'] == agent_id), None)

        if not member:
            raise ValueError(f"Member {agent_id} not found")

        persona_id = member['persona_id']

        # Initiate handoff
        if require_handoff and not force_skip_handoff:
            handoff = await self.handoff_manager.initiate_handoff(
                team_id=self.team_id,
                agent_id=agent_id,
                persona_id=persona_id,
                initiated_by=self.coordinator_id
            )

            # Check if complete
            if not handoff['checklist']['artifacts_verified'] or \
               not handoff['checklist']['documentation_complete'] or \
               not handoff['checklist']['lessons_learned_captured']:

                print(f"\n  ⚠️  Handoff checklist incomplete!")
                print(f"      Please complete checklist before retiring.")
                print(f"      Call complete_handoff() when ready.")

                return {
                    "membership": member,
                    "handoff": handoff,
                    "knowledge_captured": False,
                    "status": "handoff_pending"
                }

            # Complete handoff
            handoff = await self.handoff_manager.complete_handoff(
                handoff_id=handoff['id'],
                completed_by=self.coordinator_id
            )

        elif force_skip_handoff:
            # Skip handoff (not recommended)
            handoff_init = await self.handoff_manager.initiate_handoff(
                team_id=self.team_id,
                agent_id=agent_id,
                persona_id=persona_id,
                initiated_by=self.coordinator_id
            )
            handoff = await self.handoff_manager.skip_handoff(
                handoff_id=handoff_init['id'],
                reason="Forced skip",
                skipped_by=self.coordinator_id
            )
        else:
            handoff = None

        # Retire member (existing functionality)
        membership = await self.retire_member(agent_id, reason)

        # Unassign from roles
        roles = await self.role_manager.get_roles_for_agent(self.team_id, agent_id)
        for role in roles:
            await self.role_manager.unassign_role(
                team_id=self.team_id,
                role_id=role,
                reason=f"Member retired: {reason}"
            )

        print(f"\n  ✓ Member retired with knowledge captured")

        return {
            "membership": membership,
            "handoff": handoff,
            "knowledge_captured": handoff is not None and handoff['status'] == 'completed',
            "status": "retired"
        }

    async def initialize_roles(self) -> List[Dict[str, Any]]:
        """Initialize standard SDLC roles for the team"""
        print(f"\n  🎭 Initializing role-based assignments...")
        roles = await self.role_manager.initialize_standard_roles(
            team_id=self.team_id,
            created_by=self.coordinator_id
        )
        return roles

    async def assign_member_to_role(
        self,
        agent_id: str,
        role_id: str,
        reason: str = "Role assignment"
    ) -> Dict[str, Any]:
        """Assign a team member to a role"""
        return await self.role_manager.assign_agent_to_role(
            team_id=self.team_id,
            role_id=role_id,
            agent_id=agent_id,
            assigned_by=self.coordinator_id,
            reason=reason
        )

    async def reassign_role(
        self,
        role_id: str,
        new_agent_id: str,
        reason: str = "Role reassignment"
    ) -> Dict[str, Any]:
        """Reassign a role to a different agent (seamless handoff)"""
        return await self.role_manager.reassign_role(
            team_id=self.team_id,
            role_id=role_id,
            new_agent_id=new_agent_id,
            assigned_by=self.coordinator_id,
            reason=reason
        )

    async def print_role_summary(self):
        """Print role assignment summary"""
        await self.role_manager.print_role_summary(self.team_id)

    async def complete_pending_handoff(
        self,
        agent_id: str,
        lessons_learned: str,
        open_questions: Optional[List[str]] = None,
        recommendations: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Complete a pending handoff for an agent

        Args:
            agent_id: Agent with pending handoff
            lessons_learned: Lessons learned text
            open_questions: List of open questions
            recommendations: List of recommendations

        Returns:
            Completed handoff info
        """
        # Get pending handoff
        handoff = await self.handoff_manager._get_handoff(self.team_id, agent_id)

        if not handoff:
            raise ValueError(f"No pending handoff for {agent_id}")

        # Update checklist
        await self.handoff_manager.update_handoff_checklist(
            handoff_id=handoff['id'],
            artifacts_verified=True,
            documentation_complete=True,
            lessons_learned=lessons_learned,
            open_questions=open_questions or [],
            recommendations=recommendations or []
        )

        # Complete handoff
        return await self.handoff_manager.complete_handoff(
            handoff_id=handoff['id'],
            completed_by=self.coordinator_id
        )

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _get_persona_by_id(self, persona_id: str) -> Optional[Dict[str, Any]]:
        """Get persona definition by ID"""
        persona_methods = {
            "requirement_analyst": self.personas.requirement_analyst,
            "solution_architect": self.personas.solution_architect,
            "frontend_developer": self.personas.frontend_developer,
            "backend_developer": self.personas.backend_developer,
            "devops_engineer": self.personas.devops_engineer,
            "qa_engineer": self.personas.qa_engineer,
            "security_specialist": self.personas.security_specialist,
            "ui_ux_designer": self.personas.ui_ux_designer,
            "technical_writer": self.personas.technical_writer,
            "deployment_specialist": self.personas.deployment_specialist,
            "deployment_integration_tester": self.personas.deployment_integration_tester
        }

        method = persona_methods.get(persona_id)
        return method() if method else None


if __name__ == "__main__":
    print("Dynamic Team Manager")
    print("=" * 80)
    print("\nMain orchestrator for dynamic team management.")
    print("Use this via sdlc_coordinator or standalone for team management.")
