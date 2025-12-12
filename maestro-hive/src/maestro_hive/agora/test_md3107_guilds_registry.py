"""
Test Suite for MD-3107 - Agora Phase 2: Guilds & Registry

This test suite validates all 4 acceptance criteria:
- AC-1: Define Guild schemas (Coder, Reviewer, Architect, Tester, etc.)
- AC-2: Implement AgentRegistry class with register() and find_agents() methods
- AC-3: Implement GuildRouter to find agents by capability and cost constraints
- AC-4: Agents can check in at startup with their skills and availability

Reference: docs/roadmap/AGORA_PHASE2_DETAILED_BACKLOG.md (AGORA-105)
"""

import pytest
from datetime import datetime, timedelta
from typing import Set

from maestro_hive.agora.guilds import Guild, GuildProfile, GuildType
from maestro_hive.agora.registry import (
    AgentRegistry,
    RegisteredAgent,
    AgentCapabilities,
    AgentStatus,
)
from maestro_hive.agora.router import (
    GuildRouter,
    RoutingRequest,
    RoutingResult,
    RoutingStrategy,
)


# =============================================================================
# AC-1: Guild Schema Tests
# =============================================================================

class TestAC1_GuildSchemas:
    """AC-1: Define Guild schemas (Coder, Reviewer, Architect, Tester, etc.)"""

    def test_guild_type_enum_has_core_guilds(self):
        """Verify all required guild types exist."""
        # Code Production Guilds
        assert GuildType.CODER
        assert GuildType.ARCHITECT
        assert GuildType.FRONTEND_DEVELOPER
        assert GuildType.BACKEND_DEVELOPER

        # QA Guilds
        assert GuildType.REVIEWER
        assert GuildType.TESTER
        assert GuildType.QA_ENGINEER
        assert GuildType.SECURITY_ANALYST

        # Documentation/Design
        assert GuildType.TECHNICAL_WRITER
        assert GuildType.UX_DESIGNER
        assert GuildType.REQUIREMENTS_ANALYST

        # Operations
        assert GuildType.DEVOPS_ENGINEER
        assert GuildType.SRE

        # Coordination
        assert GuildType.PROJECT_MANAGER
        assert GuildType.SCRUM_MASTER

        # Generalist
        assert GuildType.GENERALIST

    def test_guild_initialization(self):
        """Verify Guild.initialize() populates all profiles."""
        Guild._initialized = False  # Reset for test
        Guild._profiles = {}

        Guild.initialize()

        assert Guild._initialized
        assert len(Guild._profiles) >= 17  # At least all GuildType values

    def test_guild_profile_has_required_attributes(self):
        """Verify GuildProfile has all required attributes."""
        Guild.initialize()
        profile = Guild.get_profile(GuildType.CODER)

        assert isinstance(profile.guild_type, GuildType)
        assert isinstance(profile.name, str)
        assert isinstance(profile.description, str)
        assert isinstance(profile.skills, set)
        assert isinstance(profile.cost_per_token_range, tuple)
        assert isinstance(profile.quality_tier, int)
        assert isinstance(profile.can_collaborate_with, list)
        assert isinstance(profile.metadata, dict)
        assert isinstance(profile.created_at, datetime)

    def test_coder_guild_profile(self):
        """Verify CODER guild has expected skills."""
        Guild.initialize()
        coder = Guild.get_profile(GuildType.CODER)

        assert coder.name == "Coder"
        assert "python" in coder.skills
        assert "code_generation" in coder.skills
        assert coder.quality_tier == 4
        assert GuildType.REVIEWER in coder.can_collaborate_with

    def test_architect_guild_profile(self):
        """Verify ARCHITECT guild has expected skills."""
        Guild.initialize()
        architect = Guild.get_profile(GuildType.ARCHITECT)

        assert architect.name == "Solution Architect"
        assert "system_design" in architect.skills
        assert "architecture" in architect.skills
        assert architect.quality_tier == 5

    def test_reviewer_guild_profile(self):
        """Verify REVIEWER guild has expected skills."""
        Guild.initialize()
        reviewer = Guild.get_profile(GuildType.REVIEWER)

        assert reviewer.name == "Code Reviewer"
        assert "code_review" in reviewer.skills
        assert "best_practices" in reviewer.skills
        assert reviewer.quality_tier == 5

    def test_tester_guild_profile(self):
        """Verify TESTER guild has expected skills."""
        Guild.initialize()
        tester = Guild.get_profile(GuildType.TESTER)

        assert tester.name == "Tester"
        assert "unit_testing" in tester.skills
        assert "pytest" in tester.skills

    def test_guild_has_skill_method(self):
        """Verify has_skill works case-insensitively."""
        Guild.initialize()
        coder = Guild.get_profile(GuildType.CODER)

        assert coder.has_skill("python")
        assert coder.has_skill("PYTHON")
        assert coder.has_skill("Python")
        assert not coder.has_skill("rust")

    def test_guild_is_affordable_method(self):
        """Verify is_affordable checks minimum cost."""
        Guild.initialize()
        coder = Guild.get_profile(GuildType.CODER)

        # Coder cost range is (0.001, 0.01)
        assert coder.is_affordable(0.01)
        assert coder.is_affordable(0.001)
        assert not coder.is_affordable(0.0001)

    def test_guild_to_dict_serialization(self):
        """Verify GuildProfile serializes correctly."""
        Guild.initialize()
        profile = Guild.get_profile(GuildType.CODER)
        data = profile.to_dict()

        assert data["guild_type"] == "coder"
        assert data["name"] == "Coder"
        assert "python" in data["skills"]
        assert isinstance(data["cost_per_token_range"], list)

    def test_find_by_skill(self):
        """Verify Guild.find_by_skill finds correct guilds."""
        Guild.initialize()

        python_guilds = Guild.find_by_skill("python")
        assert len(python_guilds) > 0
        assert any(g.guild_type == GuildType.CODER for g in python_guilds)

    def test_find_affordable_guilds(self):
        """Verify Guild.find_affordable finds guilds within budget."""
        Guild.initialize()

        cheap_guilds = Guild.find_affordable(0.002)
        assert len(cheap_guilds) > 0
        # All returned guilds should have min cost <= 0.002
        for g in cheap_guilds:
            assert g.cost_per_token_range[0] <= 0.002


# =============================================================================
# AC-2: AgentRegistry Tests
# =============================================================================

class TestAC2_AgentRegistry:
    """AC-2: Implement AgentRegistry with register() and find_agents() methods"""

    @pytest.fixture
    def registry(self):
        """Create a fresh registry for each test."""
        AgentRegistry.reset_instance()
        return AgentRegistry()

    def test_register_creates_agent(self, registry):
        """Verify register() creates an agent."""
        agent = registry.register(
            name="TestAgent",
            capabilities=AgentCapabilities(
                guilds={GuildType.CODER},
                skills={"python", "testing"},
            ),
        )

        assert agent is not None
        assert agent.name == "TestAgent"
        assert agent.agent_id is not None
        assert GuildType.CODER in agent.capabilities.guilds

    def test_register_with_specific_id(self, registry):
        """Verify register() uses provided agent_id."""
        agent = registry.register(
            name="TestAgent",
            capabilities=AgentCapabilities(),
            agent_id="custom-id-123",
        )

        assert agent.agent_id == "custom-id-123"

    def test_register_updates_existing_agent(self, registry):
        """Verify re-registration updates existing agent."""
        agent1 = registry.register(
            name="TestAgent",
            capabilities=AgentCapabilities(guilds={GuildType.CODER}),
            agent_id="fixed-id",
        )

        agent2 = registry.register(
            name="TestAgent",
            capabilities=AgentCapabilities(guilds={GuildType.ARCHITECT}),
            agent_id="fixed-id",
        )

        assert agent1.agent_id == agent2.agent_id
        assert GuildType.ARCHITECT in agent2.capabilities.guilds

    def test_find_agents_by_guild(self, registry):
        """Verify find_agents() filters by guild."""
        registry.register(
            name="Coder1",
            capabilities=AgentCapabilities(guilds={GuildType.CODER}),
        )
        registry.register(
            name="Reviewer1",
            capabilities=AgentCapabilities(guilds={GuildType.REVIEWER}),
        )

        coders = registry.find_agents(guild=GuildType.CODER)
        assert len(coders) == 1
        assert coders[0].name == "Coder1"

    def test_find_agents_by_skill(self, registry):
        """Verify find_agents() filters by skill."""
        registry.register(
            name="PythonDev",
            capabilities=AgentCapabilities(skills={"python", "django"}),
        )
        registry.register(
            name="JSDev",
            capabilities=AgentCapabilities(skills={"javascript", "react"}),
        )

        python_agents = registry.find_agents(skill="python")
        assert len(python_agents) == 1
        assert python_agents[0].name == "PythonDev"

    def test_find_agents_by_multiple_skills(self, registry):
        """Verify find_agents() filters by multiple skills."""
        registry.register(
            name="FullStack",
            capabilities=AgentCapabilities(skills={"python", "javascript", "docker"}),
        )
        registry.register(
            name="BackendOnly",
            capabilities=AgentCapabilities(skills={"python", "postgresql"}),
        )

        multi_skill = registry.find_agents(skills={"python", "javascript"})
        assert len(multi_skill) == 1
        assert multi_skill[0].name == "FullStack"

    def test_find_agents_by_max_cost(self, registry):
        """Verify find_agents() filters by cost."""
        registry.register(
            name="CheapAgent",
            capabilities=AgentCapabilities(cost_per_token=0.001),
        )
        registry.register(
            name="ExpensiveAgent",
            capabilities=AgentCapabilities(cost_per_token=0.01),
        )

        cheap = registry.find_agents(max_cost=0.005)
        assert len(cheap) == 1
        assert cheap[0].name == "CheapAgent"

    def test_find_agents_available_only(self, registry):
        """Verify find_agents() filters available only by default."""
        agent1 = registry.register(
            name="Available",
            capabilities=AgentCapabilities(),
        )
        agent2 = registry.register(
            name="Busy",
            capabilities=AgentCapabilities(),
        )
        registry.update_status(agent2.agent_id, AgentStatus.BUSY)

        available = registry.find_agents(available_only=True)
        assert len(available) == 1
        assert available[0].name == "Available"

        all_agents = registry.find_agents(available_only=False, min_capacity=0)
        assert len(all_agents) == 2

    def test_find_agents_sorted_by_cost(self, registry):
        """Verify find_agents() returns agents sorted by cost."""
        registry.register(
            name="Medium",
            capabilities=AgentCapabilities(cost_per_token=0.005),
        )
        registry.register(
            name="Cheap",
            capabilities=AgentCapabilities(cost_per_token=0.001),
        )
        registry.register(
            name="Expensive",
            capabilities=AgentCapabilities(cost_per_token=0.01),
        )

        agents = registry.find_agents()
        assert agents[0].name == "Cheap"
        assert agents[1].name == "Medium"
        assert agents[2].name == "Expensive"

    def test_unregister_agent(self, registry):
        """Verify unregister() removes agent."""
        agent = registry.register(name="Test", capabilities=AgentCapabilities())

        assert registry.get_agent(agent.agent_id) is not None

        result = registry.unregister(agent.agent_id)
        assert result is True
        assert registry.get_agent(agent.agent_id) is None

    def test_unregister_nonexistent_returns_false(self, registry):
        """Verify unregister() returns False for unknown agent."""
        result = registry.unregister("nonexistent-id")
        assert result is False


# =============================================================================
# AC-3: GuildRouter Tests
# =============================================================================

class TestAC3_GuildRouter:
    """AC-3: Implement GuildRouter to find agents by capability and cost constraints"""

    @pytest.fixture
    def registry(self):
        """Create a fresh registry."""
        AgentRegistry.reset_instance()
        return AgentRegistry()

    @pytest.fixture
    def router(self, registry):
        """Create a router with the test registry."""
        return GuildRouter(registry)

    def test_route_finds_matching_agent(self, registry, router):
        """Verify route() finds matching agent."""
        registry.register(
            name="TestCoder",
            capabilities=AgentCapabilities(guilds={GuildType.CODER}),
        )

        result = router.route(RoutingRequest(required_guilds={GuildType.CODER}))

        assert result.success
        assert result.agent is not None
        assert result.agent.name == "TestCoder"

    def test_route_fails_when_no_match(self, registry, router):
        """Verify route() returns failure when no match."""
        registry.register(
            name="TestCoder",
            capabilities=AgentCapabilities(guilds={GuildType.CODER}),
        )

        result = router.route(RoutingRequest(required_guilds={GuildType.ARCHITECT}))

        assert not result.success
        assert result.agent is None
        assert "No agents match" in result.reason

    def test_route_respects_cost_constraint(self, registry, router):
        """Verify route() filters by max cost."""
        registry.register(
            name="CheapCoder",
            capabilities=AgentCapabilities(
                guilds={GuildType.CODER},
                cost_per_token=0.001,
            ),
        )
        registry.register(
            name="ExpensiveCoder",
            capabilities=AgentCapabilities(
                guilds={GuildType.CODER},
                cost_per_token=0.02,
            ),
        )

        result = router.route(RoutingRequest(
            required_guilds={GuildType.CODER},
            max_cost_per_token=0.005,
        ))

        assert result.success
        assert result.agent.name == "CheapCoder"

    def test_route_respects_skill_constraint(self, registry, router):
        """Verify route() filters by required skills."""
        registry.register(
            name="PythonCoder",
            capabilities=AgentCapabilities(
                guilds={GuildType.CODER},
                skills={"python"},
            ),
        )
        registry.register(
            name="RustCoder",
            capabilities=AgentCapabilities(
                guilds={GuildType.CODER},
                skills={"rust"},
            ),
        )

        result = router.route(RoutingRequest(
            required_guilds={GuildType.CODER},
            required_skills={"python"},
        ))

        assert result.success
        assert result.agent.name == "PythonCoder"

    def test_route_cheapest_strategy(self, registry, router):
        """Verify CHEAPEST strategy selects lowest cost agent."""
        registry.register(
            name="Cheap",
            capabilities=AgentCapabilities(
                guilds={GuildType.CODER},
                cost_per_token=0.001,
            ),
        )
        registry.register(
            name="Expensive",
            capabilities=AgentCapabilities(
                guilds={GuildType.CODER},
                cost_per_token=0.01,
            ),
        )

        result = router.route(RoutingRequest(
            required_guilds={GuildType.CODER},
            strategy=RoutingStrategy.CHEAPEST,
        ))

        assert result.agent.name == "Cheap"

    def test_route_best_quality_strategy(self, registry, router):
        """Verify BEST_QUALITY strategy selects highest tier agent."""
        registry.register(
            name="LowQuality",
            capabilities=AgentCapabilities(guilds={GuildType.GENERALIST}),
        )
        registry.register(
            name="HighQuality",
            capabilities=AgentCapabilities(guilds={GuildType.ARCHITECT}),
        )

        result = router.route(RoutingRequest(
            strategy=RoutingStrategy.BEST_QUALITY,
        ))

        # ARCHITECT has quality_tier=5, GENERALIST has quality_tier=3
        assert result.agent.name == "HighQuality"

    def test_route_least_loaded_strategy(self, registry, router):
        """Verify LEAST_LOADED strategy selects agent with most capacity."""
        agent1 = registry.register(
            name="Busy",
            capabilities=AgentCapabilities(
                guilds={GuildType.CODER},
                max_concurrent_tasks=2,
            ),
        )
        registry.assign_task(agent1.agent_id)

        registry.register(
            name="Free",
            capabilities=AgentCapabilities(
                guilds={GuildType.CODER},
                max_concurrent_tasks=2,
            ),
        )

        result = router.route(RoutingRequest(
            required_guilds={GuildType.CODER},
            strategy=RoutingStrategy.LEAST_LOADED,
        ))

        assert result.agent.name == "Free"

    def test_route_excludes_specified_agents(self, registry, router):
        """Verify route() excludes specified agents."""
        agent1 = registry.register(
            name="Agent1",
            capabilities=AgentCapabilities(guilds={GuildType.CODER}),
        )
        registry.register(
            name="Agent2",
            capabilities=AgentCapabilities(guilds={GuildType.CODER}),
        )

        result = router.route(RoutingRequest(
            required_guilds={GuildType.CODER},
            exclude_agents={agent1.agent_id},
        ))

        assert result.agent.name == "Agent2"

    def test_find_agents_for_task_maps_task_type(self, registry, router):
        """Verify find_agents_for_task() maps task types to guilds."""
        registry.register(
            name="Coder",
            capabilities=AgentCapabilities(guilds={GuildType.CODER}),
        )
        registry.register(
            name="Reviewer",
            capabilities=AgentCapabilities(guilds={GuildType.REVIEWER}),
        )

        coders = router.find_agents_for_task("code")
        assert len(coders) == 1
        assert coders[0].name == "Coder"

        reviewers = router.find_agents_for_task("review")
        assert len(reviewers) == 1
        assert reviewers[0].name == "Reviewer"

    def test_get_guild_availability(self, registry, router):
        """Verify get_guild_availability() returns stats."""
        registry.register(
            name="Coder1",
            capabilities=AgentCapabilities(guilds={GuildType.CODER}),
        )

        stats = router.get_guild_availability()

        assert "coder" in stats
        assert stats["coder"]["total"] == 1
        assert stats["coder"]["available"] == 1


# =============================================================================
# AC-4: Agent Check-in Tests
# =============================================================================

class TestAC4_AgentCheckin:
    """AC-4: Agents can check in at startup with their skills and availability"""

    @pytest.fixture
    def registry(self):
        """Create a fresh registry."""
        AgentRegistry.reset_instance()
        return AgentRegistry()

    def test_agent_checkin_at_startup(self, registry):
        """Verify agent can register with skills at startup."""
        agent = registry.register(
            name="StartupAgent",
            capabilities=AgentCapabilities(
                guilds={GuildType.CODER, GuildType.TESTER},
                skills={"python", "pytest", "asyncio"},
                languages={"python", "javascript"},
                frameworks={"fastapi", "pytest"},
                max_concurrent_tasks=3,
                cost_per_token=0.005,
            ),
        )

        assert agent.status == AgentStatus.AVAILABLE
        assert agent.capabilities.guilds == {GuildType.CODER, GuildType.TESTER}
        assert "python" in agent.capabilities.skills
        assert agent.capabilities.max_concurrent_tasks == 3

    def test_agent_heartbeat(self, registry):
        """Verify agent can send heartbeat."""
        agent = registry.register(
            name="HeartbeatAgent",
            capabilities=AgentCapabilities(),
        )
        initial_heartbeat = agent.last_heartbeat

        import time
        time.sleep(0.1)

        result = registry.heartbeat(agent.agent_id)

        assert result is True
        assert registry.get_agent(agent.agent_id).last_heartbeat > initial_heartbeat

    def test_agent_heartbeat_with_status(self, registry):
        """Verify heartbeat can update status."""
        agent = registry.register(
            name="HeartbeatAgent",
            capabilities=AgentCapabilities(),
        )

        registry.heartbeat(agent.agent_id, status=AgentStatus.BUSY)

        assert registry.get_agent(agent.agent_id).status == AgentStatus.BUSY

    def test_agent_availability_tracking(self, registry):
        """Verify agent availability is tracked correctly."""
        agent = registry.register(
            name="BusyAgent",
            capabilities=AgentCapabilities(max_concurrent_tasks=2),
        )

        assert agent.is_available
        assert agent.available_capacity == 2

        registry.assign_task(agent.agent_id)
        agent = registry.get_agent(agent.agent_id)
        assert agent.is_available
        assert agent.available_capacity == 1

        registry.assign_task(agent.agent_id)
        agent = registry.get_agent(agent.agent_id)
        assert not agent.is_available  # At capacity
        assert agent.status == AgentStatus.BUSY

    def test_agent_task_completion(self, registry):
        """Verify task completion restores availability."""
        agent = registry.register(
            name="WorkingAgent",
            capabilities=AgentCapabilities(max_concurrent_tasks=1),
        )

        registry.assign_task(agent.agent_id)
        assert registry.get_agent(agent.agent_id).status == AgentStatus.BUSY

        registry.complete_task(agent.agent_id)
        agent = registry.get_agent(agent.agent_id)
        assert agent.status == AgentStatus.AVAILABLE
        assert agent.current_tasks == 0

    def test_stale_agent_cleanup(self, registry):
        """Verify stale agents are marked offline."""
        agent = registry.register(
            name="StaleAgent",
            capabilities=AgentCapabilities(),
        )

        # Manually set old heartbeat
        registry._agents[agent.agent_id].last_heartbeat = datetime.utcnow() - timedelta(minutes=10)
        registry._heartbeat_timeout = timedelta(minutes=5)

        stale_ids = registry.cleanup_stale_agents()

        assert agent.agent_id in stale_ids
        assert registry.get_agent(agent.agent_id).status == AgentStatus.OFFLINE

    def test_agent_capabilities_serialization(self, registry):
        """Verify capabilities can be serialized and deserialized."""
        original = AgentCapabilities(
            guilds={GuildType.CODER, GuildType.TESTER},
            skills={"python", "pytest"},
            languages={"python"},
            frameworks={"fastapi"},
            max_concurrent_tasks=3,
            cost_per_token=0.005,
        )

        data = original.to_dict()
        restored = AgentCapabilities.from_dict(data)

        assert restored.guilds == original.guilds
        assert restored.skills == original.skills
        assert restored.cost_per_token == original.cost_per_token

    def test_registered_agent_serialization(self, registry):
        """Verify registered agent can be serialized."""
        agent = registry.register(
            name="SerializeAgent",
            capabilities=AgentCapabilities(
                guilds={GuildType.CODER},
                skills={"python"},
            ),
        )

        data = agent.to_dict()

        assert data["name"] == "SerializeAgent"
        assert data["agent_id"] == agent.agent_id
        assert "coder" in data["capabilities"]["guilds"]


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests for the full Guild & Registry system."""

    @pytest.fixture
    def setup(self):
        """Set up a full test environment."""
        AgentRegistry.reset_instance()
        registry = AgentRegistry()
        router = GuildRouter(registry)

        # Register a team of agents
        registry.register(
            name="SeniorArchitect",
            capabilities=AgentCapabilities(
                guilds={GuildType.ARCHITECT, GuildType.REVIEWER},
                skills={"system_design", "architecture", "python", "code_review"},
                cost_per_token=0.015,
            ),
        )
        registry.register(
            name="FullStackDev",
            capabilities=AgentCapabilities(
                guilds={GuildType.CODER, GuildType.FRONTEND_DEVELOPER, GuildType.BACKEND_DEVELOPER},
                skills={"python", "typescript", "react", "fastapi"},
                cost_per_token=0.008,
            ),
        )
        registry.register(
            name="QALead",
            capabilities=AgentCapabilities(
                guilds={GuildType.TESTER, GuildType.QA_ENGINEER},
                skills={"pytest", "selenium", "test_automation"},
                cost_per_token=0.006,
            ),
        )
        registry.register(
            name="JuniorDev",
            capabilities=AgentCapabilities(
                guilds={GuildType.CODER},
                skills={"python", "javascript"},
                cost_per_token=0.003,
            ),
        )

        return registry, router

    def test_find_cheapest_coder(self, setup):
        """Find the cheapest available coder."""
        registry, router = setup

        result = router.route(RoutingRequest(
            required_guilds={GuildType.CODER},
            strategy=RoutingStrategy.CHEAPEST,
        ))

        assert result.success
        assert result.agent.name == "JuniorDev"  # Cheapest at 0.003

    def test_find_architect_for_design_task(self, setup):
        """Find an architect for system design."""
        registry, router = setup

        result = router.route(RoutingRequest(
            required_guilds={GuildType.ARCHITECT},
            required_skills={"system_design"},
        ))

        assert result.success
        assert result.agent.name == "SeniorArchitect"

    def test_find_tester_within_budget(self, setup):
        """Find a tester within budget."""
        registry, router = setup

        result = router.route(RoutingRequest(
            required_guilds={GuildType.TESTER},
            max_cost_per_token=0.01,
        ))

        assert result.success
        assert result.agent.name == "QALead"

    def test_assemble_code_review_team(self, setup):
        """Assemble a team for code review."""
        registry, router = setup

        # Find a coder and a reviewer
        coder = router.find_agents_for_task("code", count=1)
        reviewers = registry.find_agents(guild=GuildType.REVIEWER)

        assert len(coder) >= 1
        assert len(reviewers) >= 1
        # SeniorArchitect has REVIEWER guild
        assert any(r.name == "SeniorArchitect" for r in reviewers)

    def test_full_workflow_simulation(self, setup):
        """Simulate a full workflow with multiple agents."""
        registry, router = setup

        # 1. Architect designs the solution
        design_result = router.route(RoutingRequest(
            required_guilds={GuildType.ARCHITECT},
        ))
        assert design_result.success
        architect = design_result.agent
        registry.assign_task(architect.agent_id)

        # 2. Developer implements
        code_result = router.route(RoutingRequest(
            required_guilds={GuildType.CODER},
            required_skills={"python"},
            exclude_agents={architect.agent_id},  # Architect is busy
        ))
        assert code_result.success
        developer = code_result.agent
        registry.assign_task(developer.agent_id)

        # 3. QA tests
        test_result = router.route(RoutingRequest(
            required_guilds={GuildType.TESTER},
        ))
        assert test_result.success
        tester = test_result.agent

        # All three should be different agents
        assert architect.agent_id != developer.agent_id
        assert developer.agent_id != tester.agent_id

    def test_registry_stats(self, setup):
        """Verify registry statistics."""
        registry, router = setup

        stats = registry.get_stats()

        assert stats["total_agents"] == 4
        assert stats["available_count"] == 4
        assert "available" in stats["by_status"]


# =============================================================================
# JIRA Acceptance Scenario Test
# =============================================================================

class TestJiraAcceptanceScenarios:
    """Tests matching JIRA acceptance scenarios."""

    def test_jira_scenario_guild_definitions(self):
        """
        JIRA AC-1: Define Guild schemas (Coder, Reviewer, Architect, Tester, etc.)

        Verify all required guild types are defined with proper schemas.
        """
        Guild.initialize()
        profiles = Guild.get_all_profiles()

        # Verify key guilds exist
        required_guilds = ["CODER", "REVIEWER", "ARCHITECT", "TESTER"]
        for guild_name in required_guilds:
            guild_type = GuildType[guild_name]
            assert guild_type in profiles
            profile = profiles[guild_type]
            assert profile.name
            assert profile.description
            assert len(profile.skills) > 0

    def test_jira_scenario_registry_register_find(self):
        """
        JIRA AC-2: Implement AgentRegistry with register() and find_agents()

        Verify registry has working register() and find_agents() methods.
        """
        AgentRegistry.reset_instance()
        registry = AgentRegistry()

        # Register an agent
        agent = registry.register(
            name="TestCoder",
            capabilities=AgentCapabilities(
                guilds={GuildType.CODER},
                skills={"python"},
            ),
        )
        assert agent.agent_id is not None

        # Find the agent
        found = registry.find_agents(guild=GuildType.CODER)
        assert len(found) == 1
        assert found[0].agent_id == agent.agent_id

    def test_jira_scenario_router_capability_cost(self):
        """
        JIRA AC-3: GuildRouter finds agents by capability and cost constraints

        Verify router can find agents with specific capabilities within budget.
        """
        AgentRegistry.reset_instance()
        registry = AgentRegistry()
        router = GuildRouter(registry)

        # Register agents with different costs
        registry.register(
            name="CheapCoder",
            capabilities=AgentCapabilities(
                guilds={GuildType.CODER},
                skills={"python"},
                cost_per_token=0.001,
            ),
        )
        registry.register(
            name="ExpensiveCoder",
            capabilities=AgentCapabilities(
                guilds={GuildType.CODER},
                skills={"python", "machine_learning"},
                cost_per_token=0.02,
            ),
        )

        # Find within budget
        result = router.route(RoutingRequest(
            required_guilds={GuildType.CODER},
            required_skills={"python"},
            max_cost_per_token=0.005,
        ))

        assert result.success
        assert result.agent.name == "CheapCoder"

    def test_jira_scenario_agent_checkin(self):
        """
        JIRA AC-4: Agents can check in at startup with skills and availability

        Verify agents can register their capabilities and track availability.
        """
        AgentRegistry.reset_instance()
        registry = AgentRegistry()

        # Agent checks in at startup
        agent = registry.register(
            name="StartupAgent",
            capabilities=AgentCapabilities(
                guilds={GuildType.CODER},
                skills={"python", "typescript"},
                max_concurrent_tasks=2,
            ),
        )

        # Verify initial state
        assert agent.status == AgentStatus.AVAILABLE
        assert agent.is_available
        assert agent.available_capacity == 2

        # Agent receives task
        registry.assign_task(agent.agent_id)
        updated = registry.get_agent(agent.agent_id)
        assert updated.current_tasks == 1
        assert updated.available_capacity == 1

        # Agent heartbeat
        result = registry.heartbeat(agent.agent_id)
        assert result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
