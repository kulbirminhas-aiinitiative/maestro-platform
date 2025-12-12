"""
Tests for Mission Handoff Coordinator.
EPIC: MD-3024 - Mission to Execution Handoff
"""

import pytest
import asyncio
from datetime import datetime

from maestro_hive.mission import (
    HandoffCoordinator,
    HandoffState,
    HandoffConfig,
    MissionContext,
    MissionConstraints,
    Artifact,
    ValidationSeverity,
)


class TestHandoffCoordinator:
    """Test suite for HandoffCoordinator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.coordinator = HandoffCoordinator()
        self.valid_context = MissionContext(
            mission_id="test-mission-001",
            mission_name="Test Mission",
            objectives=["Objective 1", "Objective 2"],
            team_composition={"lead": "architect", "members": ["dev1", "dev2"]},
            constraints=MissionConstraints(
                max_duration_hours=4.0,
                max_cost_dollars=50.0,
            ),
            artifacts=[],
            metadata={"priority": "high"},
        )

    @pytest.mark.asyncio
    async def test_coordinate_handoff_success(self):
        """Test successful handoff coordination."""
        result = await self.coordinator.coordinate_handoff(
            mission_id="test-001",
            context=self.valid_context,
        )

        assert result.status == HandoffState.COMPLETED
        assert result.mission_id == "test-001"
        assert result.handoff_id is not None
        assert result.execution_id is not None
        assert result.error is None
        assert result.duration_seconds > 0

    @pytest.mark.asyncio
    async def test_coordinate_handoff_with_config(self):
        """Test handoff with custom configuration."""
        config = HandoffConfig(
            timeout_seconds=60,
            max_retries=5,
            enable_validation=True,
        )

        result = await self.coordinator.coordinate_handoff(
            mission_id="test-002",
            context=self.valid_context,
            config=config,
        )

        assert result.status == HandoffState.COMPLETED

    @pytest.mark.asyncio
    async def test_coordinate_handoff_validation_disabled(self):
        """Test handoff with validation disabled."""
        config = HandoffConfig(enable_validation=False)

        # Create context with missing required field
        context = MissionContext(
            mission_id="test-003",
            mission_name="",  # Empty name would normally fail validation
            objectives=[],
            team_composition={},
            constraints=MissionConstraints(),
        )

        result = await self.coordinator.coordinate_handoff(
            mission_id="test-003",
            context=context,
            config=config,
        )

        # Should succeed because validation is disabled
        assert result.status == HandoffState.COMPLETED

    @pytest.mark.asyncio
    async def test_validate_readiness_valid_context(self):
        """Test validation with valid context."""
        result = await self.coordinator.validate_readiness(self.valid_context)

        assert result.is_valid is True
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_validate_readiness_missing_mission_id(self):
        """Test validation with missing mission ID."""
        context = MissionContext(
            mission_id="",
            mission_name="Test",
            objectives=["obj1"],
            team_composition={},
            constraints=MissionConstraints(),
        )

        result = await self.coordinator.validate_readiness(context)

        assert result.is_valid is False
        assert any(i.code == "MISSING_MISSION_ID" for i in result.errors)

    @pytest.mark.asyncio
    async def test_validate_readiness_missing_name(self):
        """Test validation with missing mission name."""
        context = MissionContext(
            mission_id="test",
            mission_name="",
            objectives=["obj1"],
            team_composition={},
            constraints=MissionConstraints(),
        )

        result = await self.coordinator.validate_readiness(context)

        assert result.is_valid is False
        assert any(i.code == "MISSING_MISSION_NAME" for i in result.errors)

    @pytest.mark.asyncio
    async def test_validate_readiness_no_objectives(self):
        """Test validation with no objectives."""
        context = MissionContext(
            mission_id="test",
            mission_name="Test",
            objectives=[],
            team_composition={},
            constraints=MissionConstraints(),
        )

        result = await self.coordinator.validate_readiness(context)

        assert result.is_valid is False
        assert any(i.code == "NO_OBJECTIVES" for i in result.errors)

    @pytest.mark.asyncio
    async def test_validate_readiness_invalid_duration(self):
        """Test validation with invalid duration."""
        context = MissionContext(
            mission_id="test",
            mission_name="Test",
            objectives=["obj1"],
            team_composition={},
            constraints=MissionConstraints(max_duration_hours=-1),
        )

        result = await self.coordinator.validate_readiness(context)

        assert result.is_valid is False
        assert any(i.code == "INVALID_DURATION" for i in result.errors)

    @pytest.mark.asyncio
    async def test_validate_readiness_warnings(self):
        """Test validation warnings."""
        context = MissionContext(
            mission_id="test",
            mission_name="Test",
            objectives=["obj1"],
            team_composition={},  # Empty team triggers warning
            constraints=MissionConstraints(max_duration_hours=48),  # Long duration
        )

        result = await self.coordinator.validate_readiness(context)

        assert result.is_valid is True  # Warnings don't fail validation
        assert len(result.warnings) >= 2

    @pytest.mark.asyncio
    async def test_get_status_existing(self):
        """Test getting status for existing handoff."""
        # First create a handoff
        result = await self.coordinator.coordinate_handoff(
            mission_id="test-status",
            context=self.valid_context,
        )

        # Get its status
        status = await self.coordinator.get_status(result.handoff_id)

        assert status is not None
        assert status.handoff_id == result.handoff_id
        assert status.state == HandoffState.COMPLETED

    @pytest.mark.asyncio
    async def test_get_status_nonexistent(self):
        """Test getting status for non-existent handoff."""
        status = await self.coordinator.get_status("nonexistent-id")
        assert status is None

    @pytest.mark.asyncio
    async def test_cancel_pending_handoff(self):
        """Test cancelling not possible after completion."""
        result = await self.coordinator.coordinate_handoff(
            mission_id="test-cancel",
            context=self.valid_context,
        )

        # Can't cancel completed handoff
        cancelled = await self.coordinator.cancel(result.handoff_id)
        assert cancelled is False

    @pytest.mark.asyncio
    async def test_cancel_nonexistent(self):
        """Test cancelling non-existent handoff."""
        cancelled = await self.coordinator.cancel("nonexistent-id")
        assert cancelled is False

    @pytest.mark.asyncio
    async def test_list_active(self):
        """Test listing active handoffs."""
        # After completion, no active handoffs
        await self.coordinator.coordinate_handoff(
            mission_id="test-active",
            context=self.valid_context,
        )

        active = await self.coordinator.list_active()
        assert len(active) == 0  # Completed handoffs are not active

    def test_get_metrics(self):
        """Test getting coordinator metrics."""
        metrics = self.coordinator.get_metrics()

        assert "total_handoffs" in metrics
        assert "by_state" in metrics

    @pytest.mark.asyncio
    async def test_multiple_handoffs(self):
        """Test handling multiple concurrent handoffs."""
        results = await asyncio.gather(
            self.coordinator.coordinate_handoff("m1", self.valid_context),
            self.coordinator.coordinate_handoff("m2", self.valid_context),
            self.coordinator.coordinate_handoff("m3", self.valid_context),
        )

        assert len(results) == 3
        assert all(r.status == HandoffState.COMPLETED for r in results)
        assert len(set(r.handoff_id for r in results)) == 3  # All unique IDs


class TestMissionContext:
    """Test suite for MissionContext."""

    def test_context_creation(self):
        """Test creating a mission context."""
        context = MissionContext(
            mission_id="test",
            mission_name="Test Mission",
            objectives=["obj1"],
            team_composition={"lead": "arch"},
            constraints=MissionConstraints(),
        )

        assert context.mission_id == "test"
        assert context.version == "1.0"
        assert isinstance(context.created_at, datetime)

    def test_context_to_dict(self):
        """Test serializing context to dictionary."""
        context = MissionContext(
            mission_id="test",
            mission_name="Test",
            objectives=["obj1"],
            team_composition={},
            constraints=MissionConstraints(max_duration_hours=5),
        )

        data = context.to_dict()

        assert data["mission_id"] == "test"
        assert data["mission_name"] == "Test"
        assert data["constraints"]["max_duration_hours"] == 5

    def test_context_from_dict(self):
        """Test deserializing context from dictionary."""
        data = {
            "mission_id": "test",
            "mission_name": "Test",
            "objectives": ["obj1", "obj2"],
            "team_composition": {"lead": "arch"},
            "constraints": {
                "max_duration_hours": 8,
                "max_cost_dollars": 100,
            },
            "metadata": {"key": "value"},
            "version": "1.0",
        }

        context = MissionContext.from_dict(data)

        assert context.mission_id == "test"
        assert len(context.objectives) == 2
        assert context.constraints.max_duration_hours == 8

    def test_context_round_trip(self):
        """Test serialization round-trip."""
        original = MissionContext(
            mission_id="test",
            mission_name="Test",
            objectives=["obj1"],
            team_composition={"team": "data"},
            constraints=MissionConstraints(max_personas=5),
            metadata={"extra": "info"},
        )

        data = original.to_dict()
        restored = MissionContext.from_dict(data)

        assert restored.mission_id == original.mission_id
        assert restored.mission_name == original.mission_name
        assert restored.objectives == original.objectives
        assert restored.constraints.max_personas == original.constraints.max_personas


class TestArtifact:
    """Test suite for Artifact."""

    def test_artifact_creation(self):
        """Test creating an artifact."""
        artifact = Artifact(
            id="art-001",
            name="design_doc",
            type="document",
            path="/path/to/doc.md",
        )

        assert artifact.id == "art-001"
        assert artifact.name == "design_doc"
        assert isinstance(artifact.created_at, datetime)
