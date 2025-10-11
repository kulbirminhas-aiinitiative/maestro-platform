#!/usr/bin/env python3
"""
Integration Tests for Parallel Execution Engine

Tests the complete workflow:
- MVD → Parallel work streams → Assumptions → Contracts → Conflicts → Convergence
"""

import pytest
from parallel_workflow_engine import ParallelWorkflowEngine
from assumption_tracker import AssumptionTracker
from contract_manager import ContractManager
from persistence.models import ConflictSeverity, AssumptionStatus, ContractStatus


@pytest.mark.asyncio
class TestParallelWorkflowEngine:
    """Test parallel execution engine workflows"""

    async def test_start_parallel_work_streams(self, state_manager, team_id, sample_mvd):
        """Test starting multiple parallel work streams from MVD"""
        engine = ParallelWorkflowEngine(team_id, state_manager)

        work_streams = [
            {"role": "BA", "agent_id": "ba_001", "stream_type": "analysis", "initial_task": "Define criteria"},
            {"role": "Backend", "agent_id": "be_001", "stream_type": "implementation", "initial_task": "Build API"},
            {"role": "Frontend", "agent_id": "fe_001", "stream_type": "implementation", "initial_task": "Build UI"}
        ]

        result = await engine.start_parallel_work_streams(sample_mvd, work_streams)

        assert result["team_id"] == team_id
        assert result["mvd"]["title"] == sample_mvd["title"]
        assert len(result["streams"]) == 3
        assert all("task_id" in stream for stream in result["streams"])

    async def test_dependency_graph_management(self, state_manager, team_id):
        """Test creating and querying dependency edges"""
        engine = ParallelWorkflowEngine(team_id, state_manager)

        # Create dependency
        dep = await engine.create_dependency(
            source_type="contract",
            source_id="api_v1",
            target_type="task",
            target_id="implement_endpoint",
            dependency_type="requires",
            is_blocking=True
        )

        assert dep["source_id"] == "api_v1"
        assert dep["is_blocking"] is True

        # Query downstream
        downstream = await engine.get_downstream_dependencies("contract", "api_v1")
        assert len(downstream) == 1
        assert downstream[0]["target_id"] == "implement_endpoint"

    async def test_contract_breach_detection(self, state_manager, team_id):
        """Test that contract evolution with breaking changes triggers conflict"""
        engine = ParallelWorkflowEngine(team_id, state_manager)

        old_contract = {
            "id": "contract_001",
            "contract_name": "UserAPI",
            "version": "v1.0",
            "consumers": ["backend_001", "frontend_001"]
        }

        new_contract = {
            "id": "contract_002",
            "contract_name": "UserAPI",
            "version": "v2.0",
            "breaking_changes": True,
            "consumers": ["backend_001", "frontend_001"]
        }

        conflict = await engine.detect_contract_breach(old_contract, new_contract)

        assert conflict is not None
        assert conflict["conflict_type"] == "contract_breach"
        assert conflict["severity"] == ConflictSeverity.HIGH
        assert len(conflict["affected_agents"]) == 2
        assert conflict["estimated_rework_hours"] == 4  # 2 consumers * 2 hours

    async def test_assumption_invalidation_detection(self, state_manager, team_id):
        """Test detecting when artifact changes invalidate assumptions"""
        engine = ParallelWorkflowEngine(team_id, state_manager)

        assumption = {
            "id": "assumption_001",
            "assumption_text": "API returns only id and name fields",
            "related_artifact_type": "contract",
            "related_artifact_id": "api_contract",
            "made_by_agent": "frontend_001",
            "dependent_artifacts": [
                {"type": "task", "id": "build_ui"}
            ]
        }

        new_artifact = {
            "id": "api_contract",
            "type": "contract",
            "content": {"fields": ["id", "name", "email", "phone"]}  # Changed!
        }

        conflict = await engine.detect_assumption_invalidation(assumption, new_artifact)

        assert conflict is not None
        assert conflict["conflict_type"] == "assumption_invalidation"
        assert conflict["severity"] == ConflictSeverity.MEDIUM
        assert "frontend_001" in conflict["affected_agents"]

    async def test_convergence_workflow(self, state_manager, team_id):
        """Test complete convergence workflow: trigger → resolve → complete"""
        engine = ParallelWorkflowEngine(team_id, state_manager)

        # Create some conflicts first
        conflict1 = await engine.create_conflict(
            conflict_type="contract_breach",
            severity=ConflictSeverity.HIGH,
            description="API contract changed",
            artifacts_involved=[{"type": "contract", "id": "api_001"}],
            affected_agents=["backend_001", "frontend_001"],
            estimated_rework_hours=4
        )

        conflict2 = await engine.create_conflict(
            conflict_type="assumption_invalidation",
            severity=ConflictSeverity.MEDIUM,
            description="Data structure assumption invalid",
            artifacts_involved=[{"type": "task", "id": "task_001"}],
            affected_agents=["frontend_001"],
            estimated_rework_hours=2
        )

        # Trigger convergence
        convergence = await engine.trigger_convergence(
            trigger_type="multiple_conflicts",
            trigger_description="Multiple conflicts detected, need team sync",
            conflict_ids=[conflict1["id"], conflict2["id"]],
            participants=["backend_001", "frontend_001", "architect_001"]
        )

        assert convergence["status"] == "in_progress"
        assert len(convergence["conflict_ids"]) == 2
        assert len(convergence["participants"]) == 3

        # Complete convergence
        completed = await engine.complete_convergence(
            convergence_id=convergence["id"],
            decisions_made=[
                {"decision": "Update UI to match new API contract", "agreed_by": ["frontend_001", "backend_001"]}
            ],
            artifacts_updated=[
                {"type": "task", "id": "update_ui_task"}
            ],
            rework_performed=[
                {"agent": "frontend_001", "task": "update_ui", "hours": 3}
            ]
        )

        assert completed["status"] == "completed"
        assert completed["actual_rework_hours"] == 3
        assert len(completed["decisions_made"]) == 1

    async def test_impact_analysis(self, state_manager, team_id):
        """Test impact analysis for artifact changes"""
        engine = ParallelWorkflowEngine(team_id, state_manager)
        assumptions = AssumptionTracker(state_manager)

        # Create artifact with dependency
        await engine.create_dependency(
            source_type="contract",
            source_id="user_api",
            target_type="task",
            target_id="implement_feature",
            dependency_type="requires"
        )

        # Create assumption about this artifact
        await assumptions.track_assumption(
            team_id=team_id,
            made_by_agent="backend_001",
            made_by_role="Backend Lead",
            assumption_text="UserAPI contract stable",
            assumption_category="api_contract",
            related_artifact_type="contract",
            related_artifact_id="user_api"
        )

        # Analyze impact
        impact = await engine.analyze_change_impact(
            artifact_type="contract",
            artifact_id="user_api",
            change_description="Added new required field"
        )

        assert impact["artifact_id"] == "user_api"
        assert impact["downstream_dependencies"] == 1
        assert impact["affected_assumptions"] == 1
        assert "backend_001" in impact["affected_agents"]

    async def test_parallel_execution_metrics(self, state_manager, team_id):
        """Test parallel execution metrics and reporting"""
        engine = ParallelWorkflowEngine(team_id, state_manager)

        # Create some conflicts and convergences
        conflict = await engine.create_conflict(
            conflict_type="test_conflict",
            severity=ConflictSeverity.LOW,
            description="Test conflict",
            artifacts_involved=[],
            affected_agents=["agent_001"],
            estimated_rework_hours=1
        )

        convergence = await engine.trigger_convergence(
            trigger_type="test",
            trigger_description="Test convergence",
            conflict_ids=[conflict["id"]],
            participants=["agent_001"]
        )

        await engine.complete_convergence(
            convergence_id=convergence["id"],
            decisions_made=[],
            artifacts_updated=[],
            rework_performed=[{"hours": 0.5}]
        )

        # Get metrics
        metrics = await engine.get_parallel_execution_metrics()

        assert metrics["team_id"] == team_id
        assert metrics["total_conflicts"] == 1
        assert metrics["resolved_conflicts"] == 1
        assert metrics["total_convergences"] == 1
        assert metrics["completed_convergences"] == 1
        assert metrics["total_estimated_rework_hours"] == 1
        assert metrics["total_actual_rework_hours"] == 0.5
        assert metrics["rework_efficiency"] == 50.0  # 50% of estimated


@pytest.mark.asyncio
class TestAssumptionTracker:
    """Test assumption tracking and validation"""

    async def test_track_and_validate_assumption(self, state_manager, team_id):
        """Test assumption lifecycle: track → validate"""
        tracker = AssumptionTracker(state_manager)

        # Track assumption
        assumption = await tracker.track_assumption(
            team_id=team_id,
            made_by_agent="backend_001",
            made_by_role="Backend Lead",
            assumption_text="Payment API requires only amount and currency",
            assumption_category="api_contract",
            related_artifact_type="contract",
            related_artifact_id="payment_api_v1",
            dependent_artifacts=[{"type": "task", "id": "process_payment"}]
        )

        assert assumption["status"] == AssumptionStatus.ACTIVE
        assert assumption["made_by_agent"] == "backend_001"

        # Validate assumption
        validated = await tracker.validate_assumption(
            assumption_id=assumption["id"],
            validated_by="architect_001",
            validation_notes="Confirmed with product team"
        )

        assert validated["status"] == AssumptionStatus.VALIDATED
        assert validated["validated_by"] == "architect_001"

    async def test_invalidate_assumption(self, state_manager, team_id):
        """Test assumption invalidation triggers alerts"""
        tracker = AssumptionTracker(state_manager)

        assumption = await tracker.track_assumption(
            team_id=team_id,
            made_by_agent="frontend_001",
            made_by_role="Frontend Lead",
            assumption_text="Dashboard loads in under 1 second",
            assumption_category="requirement",
            related_artifact_type="feature",
            related_artifact_id="dashboard_v1",
            dependent_artifacts=[{"type": "task", "id": "optimize_dashboard"}]
        )

        # Invalidate
        invalidated = await tracker.invalidate_assumption(
            assumption_id=assumption["id"],
            invalidated_by="qa_001",
            validation_notes="Performance tests show 3 second load time"
        )

        assert invalidated["status"] == AssumptionStatus.INVALIDATED
        assert len(invalidated["dependent_artifacts"]) == 1

    async def test_assumption_queries(self, state_manager, team_id):
        """Test querying assumptions by various criteria"""
        tracker = AssumptionTracker(state_manager)

        # Create multiple assumptions
        await tracker.track_assumption(
            team_id=team_id,
            made_by_agent="agent_001",
            made_by_role="Developer",
            assumption_text="Assumption 1",
            assumption_category="data_structure",
            related_artifact_type="model",
            related_artifact_id="user_model"
        )

        await tracker.track_assumption(
            team_id=team_id,
            made_by_agent="agent_001",
            made_by_role="Developer",
            assumption_text="Assumption 2",
            assumption_category="api_contract",
            related_artifact_type="model",
            related_artifact_id="user_model"
        )

        # Query by artifact
        by_artifact = await tracker.get_assumptions_by_artifact(
            team_id=team_id,
            artifact_type="model",
            artifact_id="user_model"
        )
        assert len(by_artifact) == 2

        # Query by agent
        by_agent = await tracker.get_assumptions_by_agent(
            team_id=team_id,
            agent_id="agent_001"
        )
        assert len(by_agent) == 2


@pytest.mark.asyncio
class TestContractManager:
    """Test contract versioning and evolution"""

    async def test_contract_creation_and_activation(self, state_manager, team_id):
        """Test contract creation and activation flow"""
        manager = ContractManager(state_manager)

        # Create contract
        contract = await manager.create_contract(
            team_id=team_id,
            contract_name="PaymentAPI",
            version="v1.0",
            contract_type="REST_API",
            specification={
                "endpoints": [
                    {"path": "/payments", "method": "POST", "params": ["amount", "currency"]}
                ]
            },
            owner_role="Tech Lead",
            owner_agent="architect_001",
            consumers=["backend_001", "frontend_001"]
        )

        assert contract["status"] == ContractStatus.DRAFT
        assert contract["contract_name"] == "PaymentAPI"

        # Activate
        activated = await manager.activate_contract(
            contract_id=contract["id"],
            activated_by="architect_001"
        )

        assert activated["status"] == ContractStatus.ACTIVE

    async def test_contract_evolution_with_breaking_changes(self, state_manager, team_id):
        """Test contract evolution triggers proper events"""
        manager = ContractManager(state_manager)

        # Create and activate v1
        v1 = await manager.create_contract(
            team_id=team_id,
            contract_name="UserAPI",
            version="v1.0",
            contract_type="REST_API",
            specification={"fields": ["id", "name"]},
            owner_role="Tech Lead",
            owner_agent="architect_001",
            consumers=["backend_001", "frontend_001"]
        )

        await manager.activate_contract(v1["id"], "architect_001")

        # Evolve to v2 with breaking changes
        v2 = await manager.evolve_contract(
            team_id=team_id,
            contract_name="UserAPI",
            new_version="v2.0",
            new_specification={"fields": ["id", "name", "email"]},  # Added field
            changes_from_previous={"added": ["email"]},
            breaking_changes=True,
            owner_agent="architect_001"
        )

        assert v2["version"] == "v2.0"
        assert v2["breaking_changes"] is True
        assert v2["supersedes_contract_id"] == v1["id"]

        # Activate v2
        await manager.activate_contract(v2["id"], "architect_001")

        # V1 should now be deprecated
        v1_updated = await manager.get_active_contract(team_id, "UserAPI")
        assert v1_updated["version"] == "v2.0"

    async def test_consumer_tracking(self, state_manager, team_id):
        """Test contract consumer registration"""
        manager = ContractManager(state_manager)

        contract = await manager.create_contract(
            team_id=team_id,
            contract_name="NotificationAPI",
            version="v1.0",
            contract_type="gRPC",
            specification={},
            owner_role="Backend Lead",
            owner_agent="backend_001",
            consumers=["service_001"]
        )

        # Register new consumer
        updated = await manager.register_consumer(
            contract_id=contract["id"],
            consumer_id="service_002"
        )

        assert "service_002" in updated["consumers"]
        assert len(updated["consumers"]) == 2
