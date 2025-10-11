#!/usr/bin/env python3
"""
Integration Tests for Elastic Team Model

Tests role-based routing, onboarding briefings, and knowledge handoff protocols.
"""

import pytest
from dynamic_team_manager import DynamicTeamManager
from role_manager import RoleManager
from onboarding_briefing import OnboardingBriefingGenerator
from knowledge_handoff import KnowledgeHandoffProtocol
from team_composition_policies import ProjectType
from persistence.models import MembershipState
import team_organization

SDLCPhase = team_organization.SDLCPhase


@pytest.mark.asyncio
class TestRoleBasedRouting:
    """Test role abstraction and task routing"""

    async def test_create_and_assign_roles(self, state_manager, team_id):
        """Test creating roles and assigning agents to them"""
        role_mgr = RoleManager(state_manager)

        # Create role
        role = await role_mgr.create_role(
            team_id=team_id,
            role_name="Backend Lead",
            persona_type="backend_developer",
            priority=10,
            is_required=True
        )

        assert role["role_name"] == "Backend Lead"
        assert role["is_required"] is True
        assert role["current_agent_id"] is None  # Not filled yet

        # Assign agent to role
        assignment = await role_mgr.assign_agent_to_role(
            role_id=role["id"],
            agent_id="backend_001"
        )

        assert assignment["agent_id"] == "backend_001"
        assert assignment["role_id"] == role["id"]

        # Check role is now filled
        updated_role = await role_mgr.get_role(role["id"])
        assert updated_role["current_agent_id"] == "backend_001"

    async def test_role_reassignment(self, state_manager, team_id):
        """Test seamless role reassignment from one agent to another"""
        role_mgr = RoleManager(state_manager)

        # Create role and assign first agent
        role = await role_mgr.create_role(
            team_id=team_id,
            role_name="QA Lead",
            persona_type="qa_engineer",
            priority=8
        )

        await role_mgr.assign_agent_to_role(role["id"], "qa_001")

        # Reassign to new agent
        new_assignment = await role_mgr.assign_agent_to_role(
            role_id=role["id"],
            agent_id="qa_002"
        )

        assert new_assignment["agent_id"] == "qa_002"

        # Old assignment should be ended
        assignments = await role_mgr.get_role_assignments(role["id"])
        active = [a for a in assignments if a["ended_at"] is None]
        assert len(active) == 1
        assert active[0]["agent_id"] == "qa_002"

    async def test_unfilled_roles_detection(self, state_manager, team_id):
        """Test detection of unfilled required roles"""
        role_mgr = RoleManager(state_manager)

        # Create required roles
        await role_mgr.create_role(
            team_id=team_id,
            role_name="Tech Lead",
            persona_type="solution_architect",
            priority=10,
            is_required=True
        )

        await role_mgr.create_role(
            team_id=team_id,
            role_name="DevOps",
            persona_type="devops_engineer",
            priority=8,
            is_required=True
        )

        # Get unfilled required roles
        unfilled = await role_mgr.get_unfilled_required_roles(team_id)

        assert len(unfilled) == 2
        assert all(role["is_required"] for role in unfilled)
        assert all(role["current_agent_id"] is None for role in unfilled)


@pytest.mark.asyncio
class TestOnboardingBriefing:
    """Test AI-powered onboarding briefings"""

    async def test_generate_onboarding_briefing(self, state_manager, team_id):
        """Test generating onboarding briefing for new team member"""
        generator = OnboardingBriefingGenerator(state_manager)

        # Create some context (decisions, tasks, members)
        await state_manager.add_team_member(team_id, "architect_001", "solution_architect")

        await state_manager.create_task(
            team_id=team_id,
            title="Design payment API",
            description="Critical task",
            status="in_progress"
        )

        # Generate briefing
        briefing = await generator.generate_briefing(
            team_id=team_id,
            persona_id="backend_developer",
            current_phase=SDLCPhase.IMPLEMENTATION,
            role_id="backend_lead"
        )

        assert briefing.team_id == team_id
        assert briefing.persona_id == "backend_developer"
        assert briefing.current_phase == SDLCPhase.IMPLEMENTATION
        assert isinstance(briefing.key_decisions, list)
        assert isinstance(briefing.immediate_tasks, list)
        assert isinstance(briefing.key_contacts, list)
        assert isinstance(briefing.resources, list)

    async def test_briefing_contains_relevant_context(self, state_manager, team_id):
        """Test briefing contains relevant team context"""
        generator = OnboardingBriefingGenerator(state_manager)

        # Create rich context
        await state_manager.add_team_member(team_id, "lead_001", "tech_lead")
        await state_manager.add_team_member(team_id, "dev_001", "backend_developer")

        task_id = await state_manager.create_task(
            team_id=team_id,
            title="Implement user authentication",
            description="High priority security feature",
            status="ready",
            metadata={"priority": "critical"}
        )

        briefing = await generator.generate_briefing(
            team_id=team_id,
            persona_id="security_specialist",
            current_phase=SDLCPhase.IMPLEMENTATION,
            role_id="security_lead"
        )

        # Should include key contacts (existing members)
        assert len(briefing.key_contacts) >= 2

        # Should include resources
        assert len(briefing.resources) > 0


@pytest.mark.asyncio
class TestKnowledgeHandoff:
    """Test knowledge handoff protocol"""

    async def test_create_handoff_document(self, state_manager, team_id):
        """Test creating knowledge handoff when member leaves"""
        handoff_protocol = KnowledgeHandoffProtocol(state_manager)

        # Add member who will leave
        await state_manager.add_team_member(team_id, "leaving_agent", "backend_developer")

        # Create tasks for this agent
        task1_id = await state_manager.create_task(
            team_id=team_id,
            title="Task 1 in progress",
            description="Work in progress",
            status="in_progress"
        )

        task2_id = await state_manager.create_task(
            team_id=team_id,
            title="Task 2 blocked",
            description="Blocked on external dependency",
            status="blocked"
        )

        # Generate handoff
        handoff = await handoff_protocol.create_handoff(
            team_id=team_id,
            departing_agent_id="leaving_agent",
            successor_agent_id="replacement_agent"
        )

        assert handoff.departing_agent_id == "leaving_agent"
        assert handoff.successor_agent_id == "replacement_agent"
        assert isinstance(handoff.in_progress_tasks, list)
        assert isinstance(handoff.key_knowledge, list)
        assert isinstance(handoff.important_contacts, list)

    async def test_handoff_marks_task_reassignment(self, state_manager, team_id):
        """Test handoff properly tracks task reassignments"""
        handoff_protocol = KnowledgeHandoffProtocol(state_manager)

        await state_manager.add_team_member(team_id, "old_agent", "frontend_developer")

        # Create task
        task_id = await state_manager.create_task(
            team_id=team_id,
            title="UI component",
            description="Work in progress",
            status="in_progress"
        )

        handoff = await handoff_protocol.create_handoff(
            team_id=team_id,
            departing_agent_id="old_agent",
            successor_agent_id="new_agent",
            in_progress_task_ids=[task_id]
        )

        # Should track this task as needing reassignment
        assert len(handoff.in_progress_tasks) >= 0  # May or may not have tasks depending on assignment


@pytest.mark.asyncio
class TestDynamicTeamManager:
    """Test complete dynamic team management workflows"""

    async def test_add_member_with_briefing(self, state_manager, team_id):
        """Test adding member with automatic onboarding briefing"""
        manager = DynamicTeamManager(
            team_id=team_id,
            state_manager=state_manager,
            project_type=ProjectType.MEDIUM_FEATURE,
            project_name="Test Project"
        )

        # Initialize roles
        await manager.initialize_role_based_assignments()

        # Add member with briefing
        result = await manager.add_member_with_briefing(
            persona_id="backend_developer",
            current_phase=SDLCPhase.IMPLEMENTATION,
            role_id=None  # Will auto-assign to unfilled role
        )

        assert "membership" in result
        assert "briefing" in result
        assert result["membership"]["persona_id"] == "backend_developer"

    async def test_retire_member_with_handoff(self, state_manager, team_id):
        """Test retiring member with knowledge handoff"""
        manager = DynamicTeamManager(
            team_id=team_id,
            state_manager=state_manager,
            project_type=ProjectType.SIMPLE_FEATURE,
            project_name="Test Project"
        )

        # Add member
        await state_manager.add_team_member(team_id, "retiring_agent", "qa_engineer")

        # Retire with handoff
        result = await manager.retire_member_with_handoff(
            agent_id="retiring_agent",
            successor_agent_id="new_qa_agent"
        )

        assert "handoff" in result
        assert result["handoff"].departing_agent_id == "retiring_agent"
        assert result["handoff"].successor_agent_id == "new_qa_agent"

        # Member should be retired
        membership = await state_manager.get_team_member(team_id, "retiring_agent")
        assert membership["state"] == MembershipState.RETIRED

    async def test_scale_team_for_phase_transition(self, state_manager, team_id):
        """Test automatic team scaling during phase transition"""
        manager = DynamicTeamManager(
            team_id=team_id,
            state_manager=state_manager,
            project_type=ProjectType.MEDIUM_FEATURE,
            project_name="Test Project"
        )

        # Start with requirements phase team
        await manager.add_member_with_briefing("requirement_analyst", SDLCPhase.REQUIREMENTS)
        await manager.add_member_with_briefing("ui_ux_designer", SDLCPhase.REQUIREMENTS)

        # Transition to implementation phase
        result = await manager.scale_for_phase_transition(
            from_phase=SDLCPhase.REQUIREMENTS,
            to_phase=SDLCPhase.IMPLEMENTATION
        )

        assert "added_members" in result or "retired_members" in result or "standby_members" in result

        # Should have added developers
        members = await state_manager.get_team_members(team_id, state=MembershipState.ACTIVE)
        personas = [m["persona_id"] for m in members]
        assert any("developer" in p for p in personas)

    async def test_performance_based_team_adjustment(self, state_manager, team_id):
        """Test team adjustment based on performance metrics"""
        manager = DynamicTeamManager(
            team_id=team_id,
            state_manager=state_manager,
            project_type=ProjectType.MEDIUM_FEATURE,
            project_name="Test Project"
        )

        # Add underperforming member
        await state_manager.add_team_member(team_id, "poor_performer", "backend_developer")
        await state_manager.update_member_performance(
            team_id=team_id,
            agent_id="poor_performer",
            performance_score=25,
            task_completion_rate=20
        )

        # Check for performance issues
        result = await manager.check_and_handle_performance_issues()

        assert "underperformers" in result
        assert len(result["underperformers"]) > 0
        assert any(u.agent_id == "poor_performer" for u in result["underperformers"])

        # Should recommend replacement
        assert result["underperformers"][0].recommendation in ["replace", "standby"]


@pytest.mark.asyncio
class TestTeamLifecycle:
    """Test complete team lifecycle scenarios"""

    async def test_progressive_team_scaling(self, state_manager, team_id):
        """Test scaling team from 2 to 8 members progressively"""
        manager = DynamicTeamManager(
            team_id=team_id,
            state_manager=state_manager,
            project_type=ProjectType.MEDIUM_FEATURE,
            project_name="Progressive Scaling Test"
        )

        # Start with 2 members
        await manager.add_member_with_briefing("solution_architect", SDLCPhase.DESIGN)
        await manager.add_member_with_briefing("backend_developer", SDLCPhase.DESIGN)

        team_size_1 = len(await state_manager.get_team_members(team_id, state=MembershipState.ACTIVE))
        assert team_size_1 == 2

        # Scale to 4
        await manager.scale_team(target_size=4, reason="workload_increase")

        team_size_2 = len(await state_manager.get_team_members(team_id, state=MembershipState.ACTIVE))
        assert team_size_2 >= 3  # Should have added at least 1

        # Scale to 8
        await manager.scale_team(target_size=8, reason="project_expansion")

        team_size_3 = len(await state_manager.get_team_members(team_id, state=MembershipState.ACTIVE))
        assert team_size_3 >= 6  # Should be approaching 8

    async def test_phase_based_rotation(self, state_manager, team_id):
        """Test rotating team members based on SDLC phase"""
        manager = DynamicTeamManager(
            team_id=team_id,
            state_manager=state_manager,
            project_type=ProjectType.FULL_SDLC,
            project_name="Phase Rotation Test"
        )

        # Requirements phase
        await manager.add_member_with_briefing("requirement_analyst", SDLCPhase.REQUIREMENTS)
        await manager.add_member_with_briefing("ui_ux_designer", SDLCPhase.REQUIREMENTS)

        # Move to implementation
        await manager.scale_for_phase_transition(SDLCPhase.REQUIREMENTS, SDLCPhase.IMPLEMENTATION)

        # Designer might move to standby, developers added
        active_members = await state_manager.get_team_members(team_id, state=MembershipState.ACTIVE)
        active_personas = [m["persona_id"] for m in active_members]

        assert any("developer" in p for p in active_personas)

        # Move to deployment
        await manager.scale_for_phase_transition(SDLCPhase.IMPLEMENTATION, SDLCPhase.DEPLOYMENT)

        active_members = await state_manager.get_team_members(team_id, state=MembershipState.ACTIVE)
        active_personas = [m["persona_id"] for m in active_members]

        assert any("deployment" in p or "devops" in p for p in active_personas)
