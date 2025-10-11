#!/usr/bin/env python3
"""
Integration Tests for Smart Team Management

Tests the performance scoring, team health analysis, and auto-scaling features.
"""

import pytest
from performance_metrics import (
    PerformanceMetricsAnalyzer,
    PerformanceThresholds,
    AgentPerformanceScore,
    TeamHealthMetrics
)
from team_composition_policies import (
    TeamCompositionPolicy,
    ProjectType,
    ComplexityLevel
)
from persistence.models import MembershipState
from tests.utils.test_helpers import add_test_member


@pytest.mark.asyncio
class TestPerformanceMetrics:
    """Test performance scoring and analysis"""

    async def test_agent_performance_scoring(self, state_manager, team_id):
        """Test 4-dimensional agent performance scoring"""
        analyzer = PerformanceMetricsAnalyzer(state_manager)

        # Add team member
        await add_test_member(state_manager, team_id, "agent_001", "backend_developer")

        # Update performance metrics
        await state_manager.update_member_performance(
            team_id=team_id,
            agent_id="agent_001",
            performance_score=75,
            task_completion_rate=80,
            average_task_duration_hours=5.0,
            collaboration_score=70
        )

        # Analyze performance
        score = await analyzer.analyze_agent_performance(team_id, "agent_001")

        assert isinstance(score, AgentPerformanceScore)
        assert score.agent_id == "agent_001"
        assert 0 <= score.overall_score <= 100
        assert 0 <= score.task_completion_score <= 100
        assert 0 <= score.speed_score <= 100
        assert 0 <= score.quality_score <= 100
        assert score.collaboration_score == 70

    async def test_underperformer_detection(self, state_manager, team_id):
        """Test underperformer detection logic"""
        analyzer = PerformanceMetricsAnalyzer(state_manager)

        # Add two members: one good performer, one underperformer
        await add_test_member(state_manager, team_id, "good_agent", "backend_developer")
        await add_test_member(state_manager, team_id, "poor_agent", "frontend_developer")

        # Good performer
        await state_manager.update_member_performance(
            team_id=team_id,
            agent_id="good_agent",
            performance_score=90,
            task_completion_rate=95,
            average_task_duration_hours=3.0,
            collaboration_score=85
        )

        # Poor performer
        await state_manager.update_member_performance(
            team_id=team_id,
            agent_id="poor_agent",
            performance_score=40,
            task_completion_rate=45,
            average_task_duration_hours=12.0,
            collaboration_score=30
        )

        # Get underperformers
        underperformers = await analyzer.get_underperformers(team_id)

        assert len(underperformers) == 1
        assert underperformers[0].agent_id == "poor_agent"
        assert underperformers[0].is_underperformer is True
        assert len(underperformers[0].issues) > 0

    async def test_replacement_candidates(self, state_manager, team_id):
        """Test getting replacement candidate recommendations"""
        analyzer = PerformanceMetricsAnalyzer(state_manager)

        # Add severely underperforming agent
        await add_test_member(state_manager, team_id, "bad_agent", "qa_engineer")
        await state_manager.update_member_performance(
            team_id=team_id,
            agent_id="bad_agent",
            performance_score=25,  # Very low
            task_completion_rate=20,
            average_task_duration_hours=20.0,
            collaboration_score=15
        )

        # Get replacement candidates
        candidates = await analyzer.get_replacement_candidates(team_id)

        assert len(candidates) > 0
        agent_id, reason = candidates[0]
        assert agent_id == "bad_agent"
        assert "Low performance" in reason
        assert "score: 25" in reason or "score" in reason.lower()

    async def test_team_health_analysis(self, state_manager, team_id):
        """Test comprehensive team health analysis"""
        analyzer = PerformanceMetricsAnalyzer(state_manager)

        # Add team members with varying performance
        agents = [
            ("agent_001", "backend_developer", 90, 95, 3.0, 85),
            ("agent_002", "frontend_developer", 85, 90, 4.0, 80),
            ("agent_003", "qa_engineer", 45, 50, 10.0, 40)  # Underperformer
        ]

        for agent_id, persona, perf, completion, duration, collab in agents:
            await add_test_member(state_manager, team_id, agent_id, persona)
            await state_manager.update_member_performance(
                team_id=team_id,
                agent_id=agent_id,
                performance_score=perf,
                task_completion_rate=completion,
                average_task_duration_hours=duration,
                collaboration_score=collab
            )

        # Analyze team health
        health = await analyzer.analyze_team_health(team_id)

        assert isinstance(health, TeamHealthMetrics)
        assert health.team_id == team_id
        assert health.active_members == 3
        assert 0 <= health.overall_health_score <= 100
        assert health.underperformers_count == 1
        assert health.top_performers_count >= 0
        assert health.scaling_recommendation in ["scale_up", "scale_down", "maintain"]

    async def test_auto_scaling_recommendations(self, state_manager, team_id):
        """Test auto-scaling recommendations based on workload"""
        analyzer = PerformanceMetricsAnalyzer(
            state_manager,
            thresholds=PerformanceThresholds(
                ready_tasks_threshold=5,  # Lower threshold for testing
                capacity_utilization_high=80
            )
        )

        # Add team members
        for i in range(2):
            await add_test_member(state_manager, team_id, f"agent_{i}", "backend_developer")
            await state_manager.update_member_performance(
                team_id=team_id,
                agent_id=f"agent_{i}",
                performance_score=80
            )

        # Create many ready tasks to trigger scale-up
        for i in range(10):
            await state_manager.create_task(
                team_id=team_id,
                title=f"Task {i}",
                description="Test task",
                status="ready"
            )

        health = await analyzer.analyze_team_health(team_id)

        # Should recommend scaling up due to high task backlog
        assert health.total_ready_tasks >= 5
        assert "scale_up" in health.scaling_recommendation or len(health.recommended_actions) > 0


@pytest.mark.asyncio
class TestTeamCompositionPolicies:
    """Test team composition policies and scaling plans"""

    def test_get_composition_for_project_types(self):
        """Test getting team composition for different project types"""
        policy = TeamCompositionPolicy()

        # Bug fix should have minimal team
        bug_fix = policy.get_composition_for_project(ProjectType.BUG_FIX)
        assert bug_fix.min_team_size == 2
        assert "backend_developer" in bug_fix.required_personas or "qa_engineer" in bug_fix.required_personas

        # Full SDLC should have complete team
        full_sdlc = policy.get_composition_for_project(ProjectType.FULL_SDLC)
        assert full_sdlc.min_team_size == 11
        assert len(full_sdlc.required_personas) >= 10

        # Complex feature
        complex_feat = policy.get_composition_for_project(ProjectType.COMPLEX_FEATURE)
        assert complex_feat.min_team_size >= 7
        assert complex_feat.scaling_policy == "phase_based"

    def test_phase_requirements(self):
        """Test phase-specific team requirements"""
        from team_organization import SDLCPhase

        policy = TeamCompositionPolicy()

        # Requirements phase
        req_phase = policy.get_phase_requirements(SDLCPhase.REQUIREMENTS)
        assert "requirement_analyst" in req_phase.primary_personas
        assert "ui_ux_designer" in req_phase.primary_personas

        # Implementation phase
        impl_phase = policy.get_phase_requirements(SDLCPhase.IMPLEMENTATION)
        assert "backend_developer" in impl_phase.primary_personas
        assert "frontend_developer" in impl_phase.primary_personas
        assert "requirement_analyst" in impl_phase.can_retire_from_previous_phase

        # Deployment phase
        deploy_phase = policy.get_phase_requirements(SDLCPhase.DEPLOYMENT)
        assert "deployment_specialist" in deploy_phase.primary_personas
        assert "devops_engineer" in deploy_phase.primary_personas

    def test_progressive_scaling_plan(self):
        """Test progressive team scaling from 2 to optimal size"""
        policy = TeamCompositionPolicy()

        plan = policy.get_progressive_scaling_plan(
            start_size=2,
            target_project_type=ProjectType.MEDIUM_FEATURE
        )

        assert len(plan) > 0
        assert plan[0]["from_size"] == 2
        assert plan[-1]["to_size"] <= 11  # Max team size

        # Each step should add 1-3 members
        for step in plan:
            delta = step["to_size"] - step["from_size"]
            assert 1 <= delta <= 3
            assert len(step["add_personas"]) == delta

    def test_phase_based_team_scaling(self):
        """Test team scaling recommendations for phase transitions"""
        from team_organization import SDLCPhase

        policy = TeamCompositionPolicy()

        # Current team for requirements phase
        current_personas = {"requirement_analyst", "ui_ux_designer", "solution_architect"}

        # Check what to do when moving to implementation
        scaling = policy.should_scale_team_for_phase(
            SDLCPhase.IMPLEMENTATION,
            current_personas
        )

        # Should recommend adding developers
        assert "backend_developer" in scaling["should_add"] or "frontend_developer" in scaling["should_add"]

        # Should put requirement_analyst on standby or retire
        assert "requirement_analyst" in scaling["should_retire"] or \
               "requirement_analyst" in scaling["should_standby"] or \
               "requirement_analyst" in scaling["should_activate"]

    def test_minimum_viable_teams(self):
        """Test minimum viable team configurations"""
        policy = TeamCompositionPolicy()

        # Bug fix minimum
        bug_fix_team = policy.get_minimum_viable_team(ProjectType.BUG_FIX)
        assert len(bug_fix_team) <= 4
        assert len(bug_fix_team) >= 2

        # Feature minimum
        feature_team = policy.get_minimum_viable_team(ProjectType.SIMPLE_FEATURE)
        assert len(feature_team) >= 5

        # Emergency minimum
        emergency_team = policy.get_minimum_viable_team(ProjectType.EMERGENCY)
        assert len(emergency_team) >= 3
        assert len(emergency_team) <= 5

    def test_optimal_team_composition(self):
        """Test optimal team recommendations"""
        policy = TeamCompositionPolicy()

        optimal = policy.get_optimal_team(ProjectType.MEDIUM_FEATURE)

        assert len(optimal) >= 7
        assert len(optimal) <= 11

        # Should include core roles
        assert any("backend" in p.lower() or "developer" in p.lower() for p in optimal)
        assert any("frontend" in p.lower() or "developer" in p.lower() for p in optimal)


@pytest.mark.asyncio
class TestPerformanceBasedActions:
    """Test performance-based team management actions"""

    async def test_performance_triggers_replacement(self, state_manager, team_id):
        """Test that low performance triggers replacement recommendation"""
        analyzer = PerformanceMetricsAnalyzer(
            state_manager,
            thresholds=PerformanceThresholds(
                min_performance_score=60,
                min_task_completion_rate=50
            )
        )

        # Add poorly performing agent
        await add_test_member(state_manager, team_id, "poor_agent", "backend_developer")
        await state_manager.update_member_performance(
            team_id=team_id,
            agent_id="poor_agent",
            performance_score=30,  # Below threshold
            task_completion_rate=25,  # Below threshold
            collaboration_score=20
        )

        score = await analyzer.analyze_agent_performance(team_id, "poor_agent")

        assert score.is_underperformer is True
        assert score.recommendation in ["replace", "standby"]
        assert score.overall_score < 60

    async def test_workload_triggers_scaling(self, state_manager, team_id):
        """Test high workload triggers scale-up recommendation"""
        analyzer = PerformanceMetricsAnalyzer(
            state_manager,
            thresholds=PerformanceThresholds(ready_tasks_threshold=3)
        )

        # Add small team
        await add_test_member(state_manager, team_id, "agent_001", "backend_developer")
        await state_manager.update_member_performance(
            team_id=team_id,
            agent_id="agent_001",
            performance_score=80
        )

        # Create high task backlog
        for i in range(15):
            await state_manager.create_task(
                team_id=team_id,
                title=f"Task {i}",
                description="Backlog task",
                status="ready"
            )

        health = await analyzer.analyze_team_health(team_id)

        assert health.total_ready_tasks >= 10
        assert health.scaling_recommendation == "scale_up"
        assert any("add" in action.lower() or "scale" in action.lower()
                   for action in health.recommended_actions)
