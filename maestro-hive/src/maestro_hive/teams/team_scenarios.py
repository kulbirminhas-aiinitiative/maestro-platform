#!/usr/bin/env python3
"""
Real-World Team Management Scenarios

Implements handlers for 8 common real-world scenarios:
1. Progressive team scaling (2→4 members)
2. Phase-based rotation
3. Performance-based removal
4. Emergency escalation
5. Skill-based dynamic composition
6. Workload-based auto-scaling
7. Cost optimization during idle periods
8. Cross-project resource sharing

Each scenario has a dedicated handler function that demonstrates
how to manage teams dynamically in that situation.
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from dynamic_team_manager import DynamicTeamManager
from team_composition_policies import ProjectType
from persistence.models import MembershipState
import team_organization

SDLCPhase = team_organization.SDLCPhase


class TeamScenarioHandler:
    """
    Handles various real-world team management scenarios

    Each method demonstrates a specific scenario and how to handle it
    using the DynamicTeamManager.
    """

    def __init__(self, team_manager: DynamicTeamManager):
        self.team_manager = team_manager
        self.team_id = team_manager.team_id
        self.state = team_manager.state

    # =========================================================================
    # Scenario 1: Progressive Team Scaling (2→4 members)
    # =========================================================================

    async def scenario_progressive_scaling(
        self,
        initial_personas: List[str] = None
    ) -> Dict[str, Any]:
        """
        Scenario 1: Progressive Team Scaling (2→4+ members)

        Context: Small bug fix turns into a feature requiring more people

        Flow:
        1. Start with 2 members (backend dev + QA)
        2. Discover it's actually a missing feature
        3. Add frontend dev + UI/UX designer
        4. Scale to full team if needed
        """
        print(f"\n{'='*80}")
        print("SCENARIO 1: PROGRESSIVE TEAM SCALING (2→4+ members)")
        print(f"{'='*80}\n")

        print("📖 Context: Bug fix turns into feature development\n")

        # Phase 1: Start with minimal team (2 members)
        print("Phase 1: Starting with minimal bug fix team (2 members)")
        if not initial_personas:
            initial_personas = ["backend_developer", "qa_engineer"]

        for persona in initial_personas:
            await self.team_manager.add_member(
                persona_id=persona,
                reason="Initial bug fix team",
                auto_activate=True
            )

        await self.team_manager.print_team_status()

        # Phase 2: Discovery - need UI changes
        print("\n💡 Discovery: Bug is actually a missing feature requiring UI changes")
        print("   Adding frontend developer and UI/UX designer...\n")

        await self.team_manager.add_member(
            persona_id="frontend_developer",
            reason="Need UI changes for feature",
            auto_activate=True
        )

        await self.team_manager.add_member(
            persona_id="ui_ux_designer",
            reason="Need UX design for new feature",
            auto_activate=True
        )

        await self.team_manager.print_team_status()

        # Phase 3: Determine if further scaling needed
        print("\n📊 Evaluating if more team members needed...")
        health = await self.team_manager.performance_analyzer.analyze_team_health(
            self.team_id
        )

        if health.scaling_recommendation == "scale_up":
            print("   Recommendation: Scale up further\n")
            # Add architect for architecture guidance
            await self.team_manager.add_member(
                persona_id="solution_architect",
                reason="Feature complexity requires architecture guidance",
                auto_activate=True
            )
        else:
            print("   Team size is sufficient for current workload\n")

        final_summary = await self.team_manager.get_team_summary()

        print(f"\n✅ Progressive scaling complete:")
        print(f"   Started with: {len(initial_personas)} members")
        print(f"   Ended with: {final_summary['total_members']} members")
        print(f"   Health score: {final_summary['health_score']}/100\n")

        return final_summary

    # =========================================================================
    # Scenario 2: Phase-Based Rotation
    # =========================================================================

    async def scenario_phase_based_rotation(
        self,
        phases_to_execute: List[SDLCPhase] = None
    ) -> Dict[str, Any]:
        """
        Scenario 2: Phase-Based Team Rotation

        Context: Full SDLC workflow with phase transitions

        Flow:
        1. Requirements: Analyst + UX (active), Architect (standby)
        2. Design: Architect (active), Analyst (standby), Devs (standby)
        3. Implementation: Devs (active), Architect + QA (standby)
        4. Testing: QA (active), Devs (on-call)
        5. Deployment: DevOps + Deployment (active), QA (standby)
        """
        print(f"\n{'='*80}")
        print("SCENARIO 2: PHASE-BASED TEAM ROTATION")
        print(f"{'='*80}\n")

        print("📖 Context: Complete SDLC with phase transitions\n")

        if not phases_to_execute:
            phases_to_execute = [
                SDLCPhase.REQUIREMENTS,
                SDLCPhase.DESIGN,
                SDLCPhase.IMPLEMENTATION,
                SDLCPhase.TESTING,
                SDLCPhase.DEPLOYMENT
            ]

        # Initialize full team first (all on standby or initializing)
        print("Initializing full SDLC team...")
        await self.team_manager.initialize_team_for_project(
            ProjectType.FULL_SDLC,
            use_minimal_team=False
        )

        # Move everyone to standby initially
        all_members = await self.state.get_team_members(self.team_id)
        for member in all_members:
            await self.team_manager.put_on_standby(
                member['agent_id'],
                "Initial state before phase execution"
            )

        phase_summaries = []

        # Execute each phase
        for phase in phases_to_execute:
            print(f"\n{'─'*80}")
            print(f"🚦 PHASE: {phase.value.upper()}")
            print(f"{'─'*80}\n")

            # Scale team for this phase
            actions = await self.team_manager.scale_team_for_phase(phase)

            # Get current state
            summary = await self.team_manager.get_team_summary()
            phase_summaries.append({
                "phase": phase.value,
                "active_members": summary['by_state'].get('active', 0),
                "standby_members": summary['by_state'].get('on_standby', 0),
                "actions": actions
            })

            print(f"Phase {phase.value} team composition:")
            print(f"  Active: {summary['by_state'].get('active', 0)}")
            print(f"  Standby: {summary['by_state'].get('on_standby', 0)}")

        print(f"\n✅ Phase-based rotation complete!")
        print(f"   Executed {len(phases_to_execute)} phases")

        return {
            "phases_executed": len(phases_to_execute),
            "phase_summaries": phase_summaries
        }

    # =========================================================================
    # Scenario 3: Performance-Based Removal
    # =========================================================================

    async def scenario_performance_based_removal(
        self,
        simulate_underperformer: bool = True
    ) -> Dict[str, Any]:
        """
        Scenario 3: Performance-Based Member Removal/Replacement

        Context: Team member consistently underperforming

        Flow:
        1. Monitor performance metrics
        2. Identify underperformers
        3. Take action based on severity:
           - Score 50-60: Improve (monitor)
           - Score 30-50: Move to standby
           - Score <30: Replace
        """
        print(f"\n{'='*80}")
        print("SCENARIO 3: PERFORMANCE-BASED REMOVAL/REPLACEMENT")
        print(f"{'='*80}\n")

        print("📖 Context: Handling underperforming team members\n")

        # Ensure team exists
        members = await self.state.get_team_members(self.team_id)
        if len(members) < 3:
            print("Initializing team first...")
            await self.team_manager.initialize_team_for_project(
                ProjectType.MEDIUM_FEATURE,
                use_minimal_team=True
            )

        # Simulate underperformer if requested
        if simulate_underperformer:
            members = await self.state.get_team_members(
                self.team_id,
                state=MembershipState.ACTIVE
            )
            if members:
                # Artificially lower performance score
                await self.state.update_member_performance(
                    self.team_id,
                    members[0]['agent_id'],
                    performance_score=25,
                    task_completion_rate=30,
                    collaboration_score=20
                )
                print(f"⚠️  Simulated underperformer: {members[0]['agent_id']}")
                print(f"   Performance score: 25/100\n")

        # Evaluate team performance
        evaluation = await self.team_manager.evaluate_team_performance()

        # Handle underperformers with auto-replace
        result = await self.team_manager.handle_underperformers(auto_replace=True)

        print(f"\n✅ Performance management complete:")
        print(f"   Underperformers found: {len(result['underperformers'])}")
        print(f"   Actions taken: {len(result['actions_taken'])}")

        for action in result['actions_taken']:
            print(f"   - {action}")

        return result

    # =========================================================================
    # Scenario 4: Emergency Escalation
    # =========================================================================

    async def scenario_emergency_escalation(
        self,
        emergency_type: str = "security_incident"
    ) -> Dict[str, Any]:
        """
        Scenario 4: Emergency Escalation

        Context: Production security incident during feature development

        Flow:
        1. Team working on feature development (2 devs)
        2. Critical security vulnerability discovered
        3. Immediately add security specialist + deployment specialist
        4. Put feature work on hold
        5. Reassign developers to security patch
        """
        print(f"\n{'='*80}")
        print("SCENARIO 4: EMERGENCY ESCALATION")
        print(f"{'='*80}\n")

        print(f"📖 Context: {emergency_type} during normal development\n")

        # Phase 1: Normal development
        print("Phase 1: Normal feature development (2 developers)")
        current_members = await self.state.get_team_members(self.team_id)

        if len(current_members) == 0:
            await self.team_manager.add_member(
                "backend_developer",
                "Feature development",
                auto_activate=True
            )
            await self.team_manager.add_member(
                "frontend_developer",
                "Feature development",
                auto_activate=True
            )

        # Phase 2: Emergency!
        print("\n🚨 EMERGENCY: Critical security vulnerability discovered!\n")

        # Immediately add emergency response team
        print("Adding emergency response team...")

        emergency_personas = [
            "security_specialist",
            "deployment_specialist",
            "devops_engineer"
        ]

        for persona in emergency_personas:
            # Check if already exists
            existing = await self.state.get_team_members(
                self.team_id,
                persona_id=persona
            )

            if not existing:
                await self.team_manager.add_member(
                    persona_id=persona,
                    reason=f"Emergency response to {emergency_type}",
                    auto_activate=True
                )
            else:
                # Activate if on standby
                if existing[0]['state'] != 'active':
                    await self.team_manager.activate_member(
                        existing[0]['agent_id'],
                        f"Emergency escalation: {emergency_type}"
                    )

        # Put feature work on hold (move to standby)
        print("\nPutting feature development on hold...")

        # Phase 3: Show final state
        await self.team_manager.print_team_status()

        print(f"\n✅ Emergency response complete:")
        print(f"   Emergency team assembled")
        print(f"   Feature work paused")
        print(f"   Focus shifted to {emergency_type}\n")

        summary = await self.team_manager.get_team_summary()
        return summary

    # =========================================================================
    # Scenario 5: Skill-Based Dynamic Composition
    # =========================================================================

    async def scenario_skill_based_composition(
        self,
        project_types_to_demo: List[ProjectType] = None
    ) -> Dict[str, Any]:
        """
        Scenario 5: Skill-Based Dynamic Composition

        Context: Different project types need different team sizes

        Demonstrates:
        - Simple bug: 1-2 people
        - Medium feature: 4-6 people
        - Complex system: 8-11 people
        - Security patch: 3-4 people
        """
        print(f"\n{'='*80}")
        print("SCENARIO 5: SKILL-BASED DYNAMIC COMPOSITION")
        print(f"{'='*80}\n")

        print("📖 Context: Different projects need different team compositions\n")

        if not project_types_to_demo:
            project_types_to_demo = [
                ProjectType.BUG_FIX,
                ProjectType.SIMPLE_FEATURE,
                ProjectType.SECURITY_PATCH
            ]

        results = []

        for proj_type in project_types_to_demo:
            print(f"\n{'─'*80}")
            print(f"Project Type: {proj_type.value.upper()}")
            print(f"{'─'*80}\n")

            # Clear team first
            all_members = await self.state.get_team_members(self.team_id)
            for member in all_members:
                if member['state'] != 'retired':
                    await self.team_manager.retire_member(
                        member['agent_id'],
                        "Clearing team for next project type demo"
                    )

            # Initialize team for this project type
            summary = await self.team_manager.initialize_team_for_project(
                proj_type,
                use_minimal_team=True
            )

            composition = self.team_manager.policy.get_composition_for_project(proj_type)

            print(f"Team composition:")
            print(f"  Members: {summary['members_added']}")
            print(f"  Expected duration: {composition.expected_duration_days} days")
            print(f"  Scaling policy: {composition.scaling_policy}")

            results.append({
                "project_type": proj_type.value,
                "team_size": summary['members_added'],
                "duration_days": composition.expected_duration_days
            })

        print(f"\n✅ Skill-based composition demo complete!")

        return {
            "project_types_demonstrated": len(project_types_to_demo),
            "results": results
        }

    # =========================================================================
    # Scenario 6: Workload-Based Auto-Scaling
    # =========================================================================

    async def scenario_workload_autoscaling(
        self,
        simulate_high_workload: bool = True
    ) -> Dict[str, Any]:
        """
        Scenario 6: Workload-Based Auto-Scaling

        Context: Task queue growing faster than completion

        Triggers:
        - Ready tasks > 10
        - Capacity utilization > 90%

        Actions:
        - Activate standby members
        - Add new members if needed
        """
        print(f"\n{'='*80}")
        print("SCENARIO 6: WORKLOAD-BASED AUTO-SCALING")
        print(f"{'='*80}\n")

        print("📖 Context: Auto-scaling based on workload metrics\n")

        # Ensure team exists
        members = await self.state.get_team_members(self.team_id)
        if len(members) < 3:
            await self.team_manager.initialize_team_for_project(
                ProjectType.MEDIUM_FEATURE,
                use_minimal_team=True
            )

        # Simulate high workload if requested
        if simulate_high_workload:
            print("Simulating high workload (creating tasks)...\n")

            for i in range(15):
                await self.state.create_task(
                    team_id=self.team_id,
                    title=f"Task {i+1}",
                    description=f"Sample task for workload simulation",
                    created_by=self.team_manager.coordinator_id,
                    required_role="developer",
                    priority=5
                )

        # Trigger auto-scaling
        result = await self.team_manager.auto_scale_by_workload()

        print(f"\n✅ Auto-scaling complete:")
        print(f"   Actions taken: {len(result['actions_taken'])}")

        for action in result['actions_taken']:
            print(f"   - {action}")

        return result

    # =========================================================================
    # Scenario 7: Cost Optimization During Idle
    # =========================================================================

    async def scenario_cost_optimization_idle(self) -> Dict[str, Any]:
        """
        Scenario 7: Cost Optimization During Idle Periods

        Context: Waiting for external dependencies

        Actions:
        - Move most members to standby
        - Keep 1 coordinator active to monitor
        - Reactivate when dependency resolved
        """
        print(f"\n{'='*80}")
        print("SCENARIO 7: COST OPTIMIZATION DURING IDLE PERIODS")
        print(f"{'='*80}\n")

        print("📖 Context: Waiting for external dependency (API approval)\n")

        # Ensure team exists
        members = await self.state.get_team_members(self.team_id)
        if len(members) < 3:
            await self.team_manager.initialize_team_for_project(
                ProjectType.MEDIUM_FEATURE,
                use_minimal_team=True
            )

        # Phase 1: Active development
        print("Phase 1: Active development")
        active_before = len(await self.state.get_team_members(
            self.team_id,
            state=MembershipState.ACTIVE
        ))
        print(f"  Active members: {active_before}\n")

        # Phase 2: Waiting period
        print("💤 Waiting for external API approval from partner team...\n")
        print("Moving team to standby (cost optimization)...")

        active_members = await self.state.get_team_members(
            self.team_id,
            state=MembershipState.ACTIVE
        )

        # Keep architect active to monitor, move others to standby
        moved_to_standby = []
        for member in active_members:
            if member['persona_id'] != 'solution_architect':
                await self.team_manager.put_on_standby(
                    member['agent_id'],
                    "Waiting for external dependency"
                )
                moved_to_standby.append(member['agent_id'])

        print(f"\n  Moved to standby: {len(moved_to_standby)} members")
        print(f"  Kept active: 1 member (architect to monitor)\n")

        # Phase 3: Dependency resolved
        print("✅ External dependency resolved! Reactivating team...\n")

        for agent_id in moved_to_standby[:2]:  # Reactivate some members
            await self.team_manager.activate_member(
                agent_id,
                "External dependency resolved, resuming work"
            )

        await self.team_manager.print_team_status()

        print(f"✅ Cost optimization complete:")
        print(f"   Moved to standby: {len(moved_to_standby)}")
        print(f"   Reactivated: 2 members")
        print(f"   Cost savings during idle: ~{len(moved_to_standby)*8} hours\n")

        return {
            "moved_to_standby": len(moved_to_standby),
            "cost_savings_hours": len(moved_to_standby) * 8
        }

    # =========================================================================
    # Scenario 8: Cross-Project Resource Sharing
    # =========================================================================

    async def scenario_cross_project_sharing(self) -> Dict[str, Any]:
        """
        Scenario 8: Cross-Project Resource Sharing

        Context: Multiple projects, limited specialists

        Demonstrates:
        - 1 security specialist shared across 3 projects
        - Queue-based allocation
        - Time-boxed assignments (e.g., 2 hours per project)
        """
        print(f"\n{'='*80}")
        print("SCENARIO 8: CROSS-PROJECT RESOURCE SHARING")
        print(f"{'='*80}\n")

        print("📖 Context: 1 security specialist, 3 projects need security review\n")

        print("Simulating 3 projects:")
        projects = [
            {"id": "project_A", "name": "E-Commerce Platform", "priority": 8},
            {"id": "project_B", "name": "Mobile App", "priority": 10},
            {"id": "project_C", "name": "Internal Tools", "priority": 5}
        ]

        for proj in projects:
            print(f"  - {proj['name']} (priority: {proj['priority']})")

        print("\nAllocation Strategy: Time-boxed rotation")
        print("  - Each project gets 2 hours")
        print("  - Highest priority first")
        print("  - Security specialist rotates between projects\n")

        # Sort by priority
        sorted_projects = sorted(projects, key=lambda p: p['priority'], reverse=True)

        allocations = []
        for i, proj in enumerate(sorted_projects):
            print(f"Slot {i+1}: {proj['name']} (2 hours)")
            allocations.append({
                "project": proj['name'],
                "specialist": "security_specialist",
                "duration_hours": 2,
                "order": i+1
            })

        print(f"\n✅ Resource sharing plan created:")
        print(f"   Projects: 3")
        print(f"   Shared specialist: security_specialist")
        print(f"   Total time: 6 hours (2 hours × 3 projects)")
        print(f"   Strategy: Queue-based, priority-ordered\n")

        return {
            "projects": len(projects),
            "shared_specialist": "security_specialist",
            "allocations": allocations,
            "total_hours": len(projects) * 2
        }


if __name__ == "__main__":
    print("Team Scenario Handlers")
    print("=" * 80)
    print("\nImplements 8 real-world team management scenarios:")
    print("1. Progressive team scaling (2→4 members)")
    print("2. Phase-based rotation")
    print("3. Performance-based removal")
    print("4. Emergency escalation")
    print("5. Skill-based dynamic composition")
    print("6. Workload-based auto-scaling")
    print("7. Cost optimization during idle")
    print("8. Cross-project resource sharing")
    print("\nUse demo_dynamic_teams.py to see all scenarios in action.")
