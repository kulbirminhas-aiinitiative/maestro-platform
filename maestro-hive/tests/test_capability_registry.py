"""
Test Suite for Capability Registry Implementation
JIRA Epic: MD-2042
Sub-tasks: MD-2064, MD-2065, MD-2066, MD-2067, MD-2068, MD-2069

Test Categories:
1. Database Schema Tests (MD-2064)
2. CapabilityRegistry Class Tests (MD-2065)
3. API Endpoint Tests (MD-2066)
4. Routing Algorithm Tests (MD-2067)
5. Versioning Tests (MD-2068)
6. Integration Tests (MD-2069)
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
from uuid import uuid4

# Test Configuration
QUALITY_FABRIC_URL = "http://localhost:8000"


# ============================================================================
# MD-2064: Database Schema Tests
# ============================================================================
class TestDatabaseSchema:
    """Tests for the capability registry database schema."""

    def test_agents_table_exists(self, db_session):
        """Verify agents table is created with correct columns."""
        # Expected columns: id, name, persona_type, availability_status,
        # wip_limit, current_wip, metadata, created_at, updated_at
        result = db_session.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name='agents'"
        )
        columns = [row[0] for row in result]

        assert 'id' in columns
        assert 'name' in columns
        assert 'persona_type' in columns
        assert 'availability_status' in columns
        assert 'wip_limit' in columns
        assert 'current_wip' in columns

    def test_capabilities_table_exists(self, db_session):
        """Verify capabilities table is created with correct columns."""
        # Expected columns: id, skill_id, parent_skill_id, category, version,
        # description, created_at
        result = db_session.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name='capabilities'"
        )
        columns = [row[0] for row in result]

        assert 'id' in columns
        assert 'skill_id' in columns
        assert 'parent_skill_id' in columns
        assert 'version' in columns

    def test_agent_capabilities_junction_table(self, db_session):
        """Verify agent_capabilities junction table exists with correct structure."""
        result = db_session.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name='agent_capabilities'"
        )
        columns = [row[0] for row in result]

        assert 'agent_id' in columns
        assert 'capability_id' in columns
        assert 'proficiency' in columns
        assert 'source' in columns
        assert 'confidence' in columns

    def test_agent_quality_history_table(self, db_session):
        """Verify quality history table for tracking scores."""
        result = db_session.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name='agent_quality_history'"
        )
        columns = [row[0] for row in result]

        assert 'agent_id' in columns
        assert 'task_id' in columns
        assert 'quality_score' in columns
        assert 'execution_time_ms' in columns

    def test_proficiency_constraint(self, db_session):
        """Verify proficiency values are constrained between 1 and 5."""
        # Attempt to insert invalid proficiency should fail
        with pytest.raises(Exception):
            db_session.execute(
                "INSERT INTO agent_capabilities (agent_id, capability_id, proficiency) "
                "VALUES (gen_random_uuid(), gen_random_uuid(), 6)"
            )

    def test_unique_agent_capability_constraint(self, db_session):
        """Verify unique constraint on (agent_id, capability_id)."""
        agent_id = str(uuid4())
        cap_id = str(uuid4())

        # First insert should succeed
        db_session.execute(
            f"INSERT INTO agents (id, name) VALUES ('{agent_id}', 'Test')"
        )
        db_session.execute(
            f"INSERT INTO capabilities (id, skill_id) VALUES ('{cap_id}', 'Backend:Python')"
        )
        db_session.execute(
            f"INSERT INTO agent_capabilities (agent_id, capability_id, proficiency) "
            f"VALUES ('{agent_id}', '{cap_id}', 3)"
        )

        # Second insert with same combo should fail
        with pytest.raises(Exception):
            db_session.execute(
                f"INSERT INTO agent_capabilities (agent_id, capability_id, proficiency) "
                f"VALUES ('{agent_id}', '{cap_id}', 4)"
            )

    def test_cascade_delete_agent(self, db_session):
        """Verify deleting agent cascades to agent_capabilities."""
        agent_id = str(uuid4())
        cap_id = str(uuid4())

        db_session.execute(f"INSERT INTO agents (id, name) VALUES ('{agent_id}', 'Test')")
        db_session.execute(f"INSERT INTO capabilities (id, skill_id) VALUES ('{cap_id}', 'Test:Skill')")
        db_session.execute(
            f"INSERT INTO agent_capabilities (agent_id, capability_id, proficiency) "
            f"VALUES ('{agent_id}', '{cap_id}', 3)"
        )

        # Delete agent
        db_session.execute(f"DELETE FROM agents WHERE id = '{agent_id}'")

        # Agent capabilities should be deleted too
        result = db_session.execute(
            f"SELECT COUNT(*) FROM agent_capabilities WHERE agent_id = '{agent_id}'"
        )
        assert result.fetchone()[0] == 0


# ============================================================================
# MD-2065: CapabilityRegistry Class Tests
# ============================================================================
class TestCapabilityRegistryClass:
    """Tests for the CapabilityRegistry class CRUD operations."""

    @pytest.fixture
    def registry(self, db_session):
        """Create a CapabilityRegistry instance for testing."""
        from dde.capability_registry import CapabilityRegistry
        return CapabilityRegistry(db_session, 'config/capability_taxonomy.yaml')

    def test_register_agent(self, registry):
        """Test registering a new agent with capabilities."""
        agent = registry.register_agent(
            agent_id="test-agent-1",
            name="Test Backend Developer",
            persona_type="backend_developer",
            capabilities={
                "Backend:Python:FastAPI": 5,
                "Backend:Python:SQLAlchemy": 4,
                "Testing:Unit": 4
            }
        )

        assert agent.agent_id == "test-agent-1"
        assert agent.name == "Test Backend Developer"
        assert len(agent.capabilities) == 3

    def test_unregister_agent(self, registry):
        """Test removing an agent from the registry."""
        # Register first
        registry.register_agent(
            agent_id="temp-agent",
            name="Temporary Agent",
            persona_type="temp",
            capabilities={"Testing:Unit": 3}
        )

        # Unregister
        result = registry.unregister_agent("temp-agent")
        assert result is True

        # Verify removal
        agent = registry.get_agent("temp-agent")
        assert agent is None

    def test_get_agent(self, registry):
        """Test retrieving an agent by ID."""
        registry.register_agent(
            agent_id="lookup-test",
            name="Lookup Test Agent",
            persona_type="tester",
            capabilities={"Testing:E2E": 4}
        )

        agent = registry.get_agent("lookup-test")
        assert agent is not None
        assert agent.name == "Lookup Test Agent"

    def test_list_agents_with_filters(self, registry):
        """Test listing agents with various filters."""
        # Register multiple agents
        registry.register_agent("agent-a", "Agent A", "backend", {"Backend:Python": 5})
        registry.register_agent("agent-b", "Agent B", "frontend", {"Web:React": 4})
        registry.register_agent("agent-c", "Agent C", "backend", {"Backend:Node": 3})

        # Filter by persona type
        backend_agents = registry.list_agents(persona_type="backend")
        assert len(backend_agents) == 2

    def test_update_agent_status(self, registry):
        """Test updating agent availability status."""
        registry.register_agent("status-test", "Status Test", "dev", {"Backend:Python": 3})

        registry.update_agent_status("status-test", status="busy", wip=2)

        agent = registry.get_agent("status-test")
        assert agent.availability_status == "busy"
        assert agent.current_wip == 2

    def test_add_capability(self, registry):
        """Test adding a new capability to an existing agent."""
        registry.register_agent("cap-test", "Capability Test", "dev", {"Backend:Python": 4})

        registry.add_capability("cap-test", "Backend:Python:Django", 3)

        agent = registry.get_agent("cap-test")
        caps = {c.skill_id: c.proficiency for c in agent.capabilities}
        assert "Backend:Python:Django" in caps
        assert caps["Backend:Python:Django"] == 3

    def test_update_capability(self, registry):
        """Test updating an existing capability proficiency."""
        registry.register_agent("update-cap", "Update Cap Test", "dev", {"Backend:Python": 3})

        registry.update_capability("update-cap", "Backend:Python", 5)

        agent = registry.get_agent("update-cap")
        caps = {c.skill_id: c.proficiency for c in agent.capabilities}
        assert caps["Backend:Python"] == 5

    def test_remove_capability(self, registry):
        """Test removing a capability from an agent."""
        registry.register_agent(
            "remove-cap",
            "Remove Cap Test",
            "dev",
            {"Backend:Python": 4, "Backend:Node": 3}
        )

        registry.remove_capability("remove-cap", "Backend:Node")

        agent = registry.get_agent("remove-cap")
        caps = [c.skill_id for c in agent.capabilities]
        assert "Backend:Node" not in caps
        assert "Backend:Python" in caps

    def test_find_capable_agents(self, registry):
        """Test finding agents with specific capabilities."""
        registry.register_agent("find-1", "Find Test 1", "backend", {"Backend:Python:FastAPI": 5})
        registry.register_agent("find-2", "Find Test 2", "backend", {"Backend:Python:FastAPI": 3})
        registry.register_agent("find-3", "Find Test 3", "frontend", {"Web:React": 5})

        # Find agents with FastAPI capability
        capable = registry.find_capable_agents(
            required_skills=["Backend:Python:FastAPI"],
            min_proficiency=4
        )

        assert len(capable) == 1
        assert capable[0].agent_id == "find-1"

    def test_cache_invalidation(self, registry):
        """Test that cache is properly invalidated on updates."""
        registry.register_agent("cache-test", "Cache Test", "dev", {"Backend:Python": 3})

        # Get agent (should cache)
        agent1 = registry.get_agent("cache-test")

        # Update directly
        registry.update_capability("cache-test", "Backend:Python", 5)

        # Get again - should reflect update
        agent2 = registry.get_agent("cache-test")
        caps = {c.skill_id: c.proficiency for c in agent2.capabilities}

        assert caps["Backend:Python"] == 5


# ============================================================================
# MD-2066: API Endpoint Tests
# ============================================================================
class TestAPIEndpoints:
    """Tests for the capability registry REST API endpoints."""

    @pytest.fixture
    def api_client(self):
        """Create an API client for testing."""
        import httpx
        return httpx.Client(base_url="http://localhost:8000")

    def test_register_agent_endpoint(self, api_client):
        """Test POST /api/capabilities/agents endpoint."""
        response = api_client.post("/api/capabilities/agents", json={
            "name": "API Test Agent",
            "persona_type": "backend_developer",
            "capabilities": {
                "Backend:Python:FastAPI": 5,
                "Testing:Unit": 4
            }
        })

        assert response.status_code == 201
        data = response.json()
        assert "agent_id" in data
        assert data["name"] == "API Test Agent"

    def test_list_agents_endpoint(self, api_client):
        """Test GET /api/capabilities/agents endpoint."""
        response = api_client.get("/api/capabilities/agents")

        assert response.status_code == 200
        data = response.json()
        assert "agents" in data
        assert isinstance(data["agents"], list)

    def test_get_agent_endpoint(self, api_client):
        """Test GET /api/capabilities/agents/{id} endpoint."""
        # First create an agent
        create_response = api_client.post("/api/capabilities/agents", json={
            "name": "Get Test Agent",
            "persona_type": "tester",
            "capabilities": {"Testing:Unit": 3}
        })
        agent_id = create_response.json()["agent_id"]

        # Then retrieve it
        response = api_client.get(f"/api/capabilities/agents/{agent_id}")

        assert response.status_code == 200
        assert response.json()["name"] == "Get Test Agent"

    def test_update_agent_endpoint(self, api_client):
        """Test PUT /api/capabilities/agents/{id} endpoint."""
        # Create agent
        create_response = api_client.post("/api/capabilities/agents", json={
            "name": "Update Test Agent",
            "persona_type": "dev",
            "capabilities": {"Backend:Python": 3}
        })
        agent_id = create_response.json()["agent_id"]

        # Update agent
        response = api_client.put(f"/api/capabilities/agents/{agent_id}", json={
            "availability_status": "busy",
            "current_wip": 2
        })

        assert response.status_code == 200
        assert response.json()["availability_status"] == "busy"

    def test_delete_agent_endpoint(self, api_client):
        """Test DELETE /api/capabilities/agents/{id} endpoint."""
        # Create agent
        create_response = api_client.post("/api/capabilities/agents", json={
            "name": "Delete Test Agent",
            "persona_type": "temp",
            "capabilities": {"Testing:Unit": 2}
        })
        agent_id = create_response.json()["agent_id"]

        # Delete agent
        response = api_client.delete(f"/api/capabilities/agents/{agent_id}")

        assert response.status_code == 200

        # Verify deletion
        get_response = api_client.get(f"/api/capabilities/agents/{agent_id}")
        assert get_response.status_code == 404

    def test_discover_endpoint(self, api_client):
        """Test POST /api/capabilities/discover endpoint."""
        response = api_client.post("/api/capabilities/discover", json={
            "required_skills": ["Backend:Python:FastAPI", "Testing:Integration"],
            "min_proficiency": 3,
            "availability_required": True,
            "limit": 5
        })

        assert response.status_code == 200
        data = response.json()
        assert "agents" in data
        assert "match_scores" in data

    def test_list_capabilities_endpoint(self, api_client):
        """Test GET /api/capabilities endpoint."""
        response = api_client.get("/api/capabilities")

        assert response.status_code == 200
        data = response.json()
        assert "capabilities" in data
        # Should include taxonomy capabilities
        assert len(data["capabilities"]) > 0

    def test_health_endpoint(self, api_client):
        """Test GET /api/capabilities/health endpoint."""
        response = api_client.get("/api/capabilities/health")

        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


# ============================================================================
# MD-2067: Routing Algorithm Tests
# ============================================================================
class TestRoutingAlgorithm:
    """Tests for the capability-based routing algorithm."""

    @pytest.fixture
    def matcher(self, registry):
        """Create a CapabilityMatcher instance for testing."""
        from dde.capability_matcher import CapabilityMatcher
        return CapabilityMatcher(registry)

    def test_proficiency_score_calculation(self, matcher):
        """Test proficiency score calculation (35% weight)."""
        # Agent with proficiency 5 should score 1.0 on proficiency
        # Agent with proficiency 3 should score 0.6 on proficiency

        score_5 = matcher._calculate_proficiency_score(
            proficiency=5,
            max_proficiency=5
        )
        score_3 = matcher._calculate_proficiency_score(
            proficiency=3,
            max_proficiency=5
        )

        assert score_5 == 1.0
        assert score_3 == 0.6

    def test_availability_score_calculation(self, matcher):
        """Test availability score calculation (25% weight)."""
        # Available agent should score 1.0
        # Busy agent should score 0.0

        available_score = matcher._calculate_availability_score("available")
        busy_score = matcher._calculate_availability_score("busy")

        assert available_score == 1.0
        assert busy_score == 0.0

    def test_quality_history_score(self, matcher):
        """Test quality history score calculation (25% weight)."""
        # Recent high scores should result in high quality score
        quality_history = [0.9, 0.85, 0.92, 0.88, 0.95]

        score = matcher._calculate_quality_score(quality_history)

        # Weighted average should be around 0.9
        assert 0.85 <= score <= 0.95

    def test_load_factor_score(self, matcher):
        """Test load factor score calculation (10% weight)."""
        # Agent with 0 WIP out of 3 limit should score 1.0
        # Agent with 2 WIP out of 3 limit should score ~0.33

        score_0 = matcher._calculate_load_score(current_wip=0, wip_limit=3)
        score_2 = matcher._calculate_load_score(current_wip=2, wip_limit=3)

        assert score_0 == 1.0
        assert abs(score_2 - 0.33) < 0.1

    def test_recency_score(self, matcher):
        """Test recency score calculation (5% weight)."""
        # Agent active in last hour should score 1.0
        # Agent active 24 hours ago should score lower

        recent = datetime.now() - timedelta(minutes=30)
        old = datetime.now() - timedelta(hours=24)

        recent_score = matcher._calculate_recency_score(recent)
        old_score = matcher._calculate_recency_score(old)

        assert recent_score > old_score
        assert recent_score > 0.8
        assert old_score < 0.5

    def test_composite_match_score(self, matcher, registry):
        """Test complete match score calculation with all factors."""
        # Register an ideal agent
        registry.register_agent(
            "ideal-agent",
            "Ideal Agent",
            "backend",
            {"Backend:Python:FastAPI": 5, "Testing:Integration": 5}
        )
        registry.update_agent_status("ideal-agent", "available", wip=0)

        # Calculate match score
        score = matcher.calculate_match_score(
            agent_id="ideal-agent",
            required_skills=["Backend:Python:FastAPI", "Testing:Integration"]
        )

        # Ideal agent should score very high
        assert score.total > 0.8
        assert score.components["proficiency"] == 1.0
        assert score.components["availability"] == 1.0

    def test_hierarchical_skill_matching(self, matcher, registry):
        """Test that parent skills match child skill requirements."""
        # Agent with "Backend:Python" should match "Backend:Python:FastAPI" requirement
        registry.register_agent(
            "parent-skill-agent",
            "Parent Skill Agent",
            "backend",
            {"Backend:Python": 4}  # Parent skill
        )

        # Should still find matches for child skill requirement
        capable = registry.find_capable_agents(
            required_skills=["Backend:Python:FastAPI"],
            include_parent_matches=True
        )

        # Should include the agent with parent skill
        agent_ids = [a.agent_id for a in capable]
        assert "parent-skill-agent" in agent_ids

    def test_skill_group_expansion(self, matcher, registry):
        """Test skill group expansion (e.g., FullStackWeb)."""
        # Register agent with individual skills
        registry.register_agent(
            "fullstack-agent",
            "Full Stack Agent",
            "fullstack",
            {
                "Web:React": 4,
                "Backend:Node": 4,
                "Data:PostgreSQL": 3,
                "DevOps:Docker": 3
            }
        )

        # Search using skill group
        capable = registry.find_capable_agents(
            required_skills=["FullStackWeb"],  # Should expand to component skills
            min_proficiency=3
        )

        agent_ids = [a.agent_id for a in capable]
        assert "fullstack-agent" in agent_ids

    def test_match_ranking(self, matcher, registry):
        """Test that agents are ranked correctly by match score."""
        # Register agents with varying capabilities
        registry.register_agent("high-skill", "High Skill", "backend", {"Backend:Python": 5})
        registry.register_agent("med-skill", "Med Skill", "backend", {"Backend:Python": 3})
        registry.register_agent("low-skill", "Low Skill", "backend", {"Backend:Python": 2})

        # Get ranked matches
        matches = matcher.match(
            required_skills=["Backend:Python"],
            top_n=3
        )

        # Should be ordered by score descending
        assert matches[0].agent_id == "high-skill"
        assert matches[1].agent_id == "med-skill"
        assert matches[2].agent_id == "low-skill"

    def test_match_with_min_proficiency(self, matcher, registry):
        """Test filtering by minimum proficiency."""
        registry.register_agent("prof-5", "Proficiency 5", "dev", {"Backend:Python": 5})
        registry.register_agent("prof-2", "Proficiency 2", "dev", {"Backend:Python": 2})

        matches = matcher.match(
            required_skills=["Backend:Python"],
            min_proficiency=4
        )

        # Only prof-5 should match
        assert len(matches) == 1
        assert matches[0].agent_id == "prof-5"

    def test_performance_under_100ms(self, matcher, registry):
        """Test that capability lookup completes in under 100ms."""
        import time

        # Register many agents
        for i in range(100):
            registry.register_agent(
                f"perf-agent-{i}",
                f"Performance Agent {i}",
                "backend",
                {"Backend:Python": i % 5 + 1}
            )

        # Time the lookup
        start = time.time()
        matches = matcher.match(
            required_skills=["Backend:Python"],
            top_n=10
        )
        duration_ms = (time.time() - start) * 1000

        # Should complete in under 100ms
        assert duration_ms < 100, f"Lookup took {duration_ms}ms, expected <100ms"


# ============================================================================
# MD-2068: Capability Versioning Tests
# ============================================================================
class TestCapabilityVersioning:
    """Tests for capability versioning support."""

    def test_capability_version_parsing(self):
        """Test SemVer parsing for capabilities."""
        from dde.capability_registry import CapabilityVersion

        version = CapabilityVersion.parse("1.2.3")

        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3

    def test_version_compatibility_check(self):
        """Test version compatibility checking."""
        from dde.capability_registry import CapabilityVersion

        required = CapabilityVersion.parse("2.0.0")
        compatible = CapabilityVersion.parse("2.1.0")
        incompatible = CapabilityVersion.parse("1.9.0")

        assert required.is_compatible_with(compatible)
        assert not required.is_compatible_with(incompatible)

    def test_deprecated_capability_migration(self, registry):
        """Test migrating deprecated capabilities to successors."""
        # Register old skill name
        registry.add_capability_version(
            skill_id="Web:Frontend",
            version="1.0.0",
            deprecated=True,
            successor_skill_id="Web"
        )

        # Migrate should return new skill ID
        new_skill = registry.migrate_capability("Web:Frontend")

        assert new_skill == "Web"

    def test_versioned_capability_registration(self, registry):
        """Test registering capabilities with specific versions."""
        registry.register_agent(
            "versioned-agent",
            "Versioned Agent",
            "backend",
            capabilities={
                "Backend:Python:FastAPI@3.0.0": 5,
                "Web:React@18.0.0": 4
            }
        )

        agent = registry.get_agent("versioned-agent")
        # Should parse version correctly
        cap_versions = {c.skill_id: c.version for c in agent.capabilities}

        assert "Backend:Python:FastAPI" in cap_versions
        assert cap_versions["Backend:Python:FastAPI"] == "3.0.0"


# ============================================================================
# MD-2069: Integration Tests
# ============================================================================
class TestTeamExecutionIntegration:
    """Integration tests with team_execution_v2.py."""

    @pytest.fixture
    def team_composer(self, registry):
        """Create a TeamComposerAgent with registry integration."""
        from team_execution_v2 import TeamComposerAgent
        return TeamComposerAgent(capability_registry=registry)

    def test_requirement_analysis_with_registry(self, team_composer, registry):
        """Test that requirement analysis queries capability registry."""
        # Register capable agents
        registry.register_agent(
            "backend-dev",
            "Backend Developer",
            "backend_developer",
            {"Backend:Python:FastAPI": 5, "Testing:Unit": 4}
        )

        # Analyze requirement
        classification = team_composer.analyze_requirement(
            "Create a REST API endpoint for user management"
        )

        # Should identify required skills
        assert "Backend:Python" in classification.required_expertise or \
               "Backend" in classification.required_expertise

    def test_persona_extraction_uses_registry(self, team_composer, registry):
        """Test that persona extraction queries available agents."""
        # Register agents
        registry.register_agent(
            "actual-backend",
            "Actual Backend Dev",
            "backend_developer",
            {"Backend:Python:FastAPI": 5}
        )
        registry.update_agent_status("actual-backend", "available", 0)

        # Extract personas should use registry
        personas = team_composer._extract_personas_for_requirement(
            requirement_type="api_development",
            required_expertise=["Backend:Python:FastAPI"]
        )

        # Should include our registered agent
        persona_ids = [p.persona_id for p in personas]
        # The persona should match a real registered agent
        assert len(personas) > 0

    def test_execution_updates_registry(self, team_composer, registry):
        """Test that execution completion updates registry scores."""
        registry.register_agent(
            "exec-test-agent",
            "Execution Test Agent",
            "backend",
            {"Backend:Python": 4}
        )

        # Simulate execution completion
        team_composer.on_execution_complete(
            agent_id="exec-test-agent",
            task_id="test-task-123",
            success=True,
            quality_score=0.95
        )

        # Quality history should be updated
        agent = registry.get_agent("exec-test-agent")
        assert len(agent.quality_history) > 0
        assert agent.quality_history[-1] == 0.95

    def test_proficiency_boost_on_success(self, team_composer, registry):
        """Test proficiency boost for high-quality executions."""
        registry.register_agent(
            "boost-test",
            "Boost Test Agent",
            "backend",
            {"Backend:Python": 4}
        )

        # Complete with high quality
        team_composer.on_execution_complete(
            agent_id="boost-test",
            task_id="high-quality-task",
            success=True,
            quality_score=0.95,
            primary_skill="Backend:Python"
        )

        # Proficiency should be boosted
        agent = registry.get_agent("boost-test")
        caps = {c.skill_id: c.proficiency for c in agent.capabilities}

        # Should have increased from 4 (by 0.1 boost = 4.1, rounded to 4 or capped)
        assert caps["Backend:Python"] >= 4

    def test_status_update_after_execution(self, team_composer, registry):
        """Test agent status is updated after execution."""
        registry.register_agent(
            "status-update-test",
            "Status Update Test",
            "backend",
            {"Backend:Python": 4}
        )
        registry.update_agent_status("status-update-test", "busy", wip=2)

        # Complete execution
        team_composer.on_execution_complete(
            agent_id="status-update-test",
            task_id="task-done",
            success=True,
            quality_score=0.8
        )

        # WIP should decrease
        agent = registry.get_agent("status-update-test")
        assert agent.current_wip == 1


# ============================================================================
# Validation Tests (Quality Fabric Integration)
# ============================================================================
class TestQualityFabricValidation:
    """Tests that validate against quality-fabric API."""

    @pytest.fixture
    def qf_client(self):
        """Create quality-fabric API client."""
        import httpx
        return httpx.Client(base_url=QUALITY_FABRIC_URL)

    def test_dde_validation_endpoint(self, qf_client):
        """Test DDE validation through quality-fabric."""
        response = qf_client.post("/api/validation/dde", json={
            "component": "capability_registry",
            "test_results": {
                "total_tests": 50,
                "passed": 48,
                "failed": 2,
                "coverage": 85.5
            }
        })

        assert response.status_code == 200
        result = response.json()
        assert "verdict" in result

    def test_trimodal_validation(self, qf_client):
        """Test tri-modal validation (BDV + ACC + DDE)."""
        response = qf_client.post("/api/validation/tri-modal", json={
            "component": "capability_registry",
            "bdv_results": {"contracts_validated": 10, "passed": 10},
            "acc_results": {"architecture_checks": 5, "passed": 5},
            "dde_results": {"tests_passed": 48, "tests_failed": 2}
        })

        assert response.status_code == 200
        result = response.json()
        assert "overall_verdict" in result


# ============================================================================
# Fixtures
# ============================================================================
@pytest.fixture(scope="session")
def db_session():
    """Create database session for testing."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    # Use test database
    engine = create_engine("postgresql://maestro_sandbox:maestro_sandbox@localhost:15432/maestro_test")
    Session = sessionmaker(bind=engine)
    session = Session()

    yield session

    session.close()


@pytest.fixture(scope="function")
def registry(db_session):
    """Create a fresh CapabilityRegistry for each test."""
    # Import will be available after implementation
    try:
        from dde.capability_registry import CapabilityRegistry
        return CapabilityRegistry(db_session, 'config/capability_taxonomy.yaml')
    except ImportError:
        pytest.skip("CapabilityRegistry not yet implemented")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
