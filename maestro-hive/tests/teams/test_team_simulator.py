#!/usr/bin/env python3
"""
Tests for Team Simulator

MD-3019: Team Simulation & Benchmarking
"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from maestro_hive.teams.team_simulator import (
    TeamSimulator,
    SimulationResult,
    SimulationScenario,
    SimulationStatus,
    ScenarioType,
    run_simulation,
)


class TestSimulationScenario:
    """Tests for SimulationScenario dataclass."""

    def test_scenario_creation(self):
        """Test creating a simulation scenario."""
        scenario = SimulationScenario(
            name="Test Scenario",
            description="A test scenario",
            scenario_type=ScenarioType.SIMPLE_API,
            team_size=3,
            complexity="simple",
            timeout_seconds=120,
        )

        assert scenario.name == "Test Scenario"
        assert scenario.team_size == 3
        assert scenario.complexity == "simple"
        assert scenario.timeout_seconds == 120

    def test_scenario_with_requirements(self):
        """Test scenario with custom requirements."""
        scenario = SimulationScenario(
            name="Custom Scenario",
            description="A custom scenario",
            scenario_type=ScenarioType.CUSTOM,
            team_size=5,
            complexity="medium",
            requirements={"backend": "FastAPI", "database": "PostgreSQL"},
            expected_outputs=["api", "tests", "docs"],
        )

        assert scenario.requirements["backend"] == "FastAPI"
        assert "api" in scenario.expected_outputs


class TestSimulationResult:
    """Tests for SimulationResult dataclass."""

    def test_result_to_dict(self):
        """Test converting result to dictionary."""
        result = SimulationResult(
            simulation_id="test123",
            scenario_name="Test Scenario",
            status=SimulationStatus.COMPLETED,
            start_time=datetime(2024, 1, 1, 10, 0, 0),
            end_time=datetime(2024, 1, 1, 10, 5, 0),
            duration_seconds=300.0,
            metrics={"overall_quality": 0.85},
        )

        data = result.to_dict()

        assert data["simulation_id"] == "test123"
        assert data["status"] == "completed"
        assert data["duration_seconds"] == 300.0
        assert data["metrics"]["overall_quality"] == 0.85


class TestTeamSimulator:
    """Tests for TeamSimulator class."""

    @pytest.fixture
    def simulator(self, tmp_path):
        """Create a TeamSimulator instance."""
        return TeamSimulator(
            output_dir=str(tmp_path / "output"),
            checkpoint_dir=str(tmp_path / "checkpoints"),
        )

    def test_simulator_initialization(self, simulator):
        """Test simulator initializes correctly."""
        assert simulator.output_dir.exists()
        assert simulator.checkpoint_dir.exists()
        assert len(simulator._active_simulations) == 0
        assert len(simulator._completed_simulations) == 0

    def test_predefined_scenarios_exist(self, simulator):
        """Test predefined scenarios are available."""
        assert ScenarioType.SIMPLE_API in simulator.PREDEFINED_SCENARIOS
        assert ScenarioType.COMPLEX_ML in simulator.PREDEFINED_SCENARIOS
        assert ScenarioType.MICROSERVICES in simulator.PREDEFINED_SCENARIOS
        assert ScenarioType.DATA_PIPELINE in simulator.PREDEFINED_SCENARIOS

    @pytest.mark.asyncio
    async def test_run_simple_api_scenario(self, simulator):
        """Test running the simple API scenario."""
        scenario = simulator.PREDEFINED_SCENARIOS[ScenarioType.SIMPLE_API]
        result = await simulator.run_scenario(scenario)

        assert result.status == SimulationStatus.COMPLETED
        assert result.simulation_id is not None
        assert result.duration_seconds > 0
        assert result.metrics["overall_quality"] > 0
        assert len(result.checkpoints) == 5  # 5 phases

    @pytest.mark.asyncio
    async def test_run_predefined_scenario(self, simulator):
        """Test running a predefined scenario by type."""
        result = await simulator.run_predefined_scenario(ScenarioType.SIMPLE_API)

        assert result.status == SimulationStatus.COMPLETED
        assert result.scenario_name == "Simple API Development"

    @pytest.mark.asyncio
    async def test_run_custom_scenario(self, simulator):
        """Test running a custom scenario."""
        result = await simulator.run_custom_scenario(
            name="Custom Test",
            description="A custom test scenario",
            team_size=4,
            complexity="medium",
            requirements={"backend": "Flask"},
            timeout_seconds=120,
        )

        assert result.status == SimulationStatus.COMPLETED
        assert result.scenario_name == "Custom Test"
        assert len(result.checkpoints) == 5

    @pytest.mark.asyncio
    async def test_simulation_with_callbacks(self, simulator):
        """Test simulation with phase callbacks."""
        phases_started = []
        phases_ended = []

        callbacks = {
            "on_phase_start": lambda phase, idx, total: phases_started.append(phase),
            "on_phase_end": lambda phase, result: phases_ended.append(phase),
        }

        scenario = simulator.PREDEFINED_SCENARIOS[ScenarioType.SIMPLE_API]
        result = await simulator.run_scenario(scenario, callbacks=callbacks)

        assert len(phases_started) == 5
        assert len(phases_ended) == 5
        assert "requirements" in phases_started
        assert "deployment" in phases_ended

    @pytest.mark.asyncio
    async def test_simulation_timeout(self, simulator):
        """Test simulation timeout handling."""
        scenario = SimulationScenario(
            name="Timeout Test",
            description="Test timeout",
            scenario_type=ScenarioType.CUSTOM,
            team_size=3,
            complexity="complex",
            timeout_seconds=0,  # Immediate timeout
        )

        result = await simulator.run_scenario(scenario)

        assert result.status == SimulationStatus.FAILED
        assert len(result.errors) > 0
        assert "timeout" in result.errors[0].lower()

    def test_get_active_simulations(self, simulator):
        """Test getting active simulations."""
        active = simulator.get_active_simulations()
        assert isinstance(active, list)
        assert len(active) == 0  # No active simulations initially

    @pytest.mark.asyncio
    async def test_get_simulation_history(self, simulator):
        """Test getting simulation history."""
        # Run a simulation first
        await simulator.run_predefined_scenario(ScenarioType.SIMPLE_API)

        history = simulator.get_simulation_history()

        assert len(history) == 1
        assert history[0]["scenario_name"] == "Simple API Development"

    @pytest.mark.asyncio
    async def test_simulation_quality_metrics(self, simulator):
        """Test that quality metrics are calculated."""
        result = await simulator.run_predefined_scenario(ScenarioType.SIMPLE_API)

        # Check phase-level quality metrics
        assert "requirements_quality" in result.metrics
        assert "design_quality" in result.metrics
        assert "implementation_quality" in result.metrics
        assert "testing_quality" in result.metrics
        assert "deployment_quality" in result.metrics

        # Check overall quality
        assert "overall_quality" in result.metrics
        assert 0 <= result.metrics["overall_quality"] <= 1

    @pytest.mark.asyncio
    async def test_multiple_simulations(self, simulator):
        """Test running multiple simulations."""
        results = []
        for _ in range(3):
            result = await simulator.run_predefined_scenario(ScenarioType.SIMPLE_API)
            results.append(result)

        assert len(results) == 3
        # Each should have unique ID
        ids = [r.simulation_id for r in results]
        assert len(set(ids)) == 3

        # History should have all 3
        history = simulator.get_simulation_history()
        assert len(history) == 3


class TestScenarioType:
    """Tests for ScenarioType enum."""

    def test_scenario_types(self):
        """Test all scenario types exist."""
        assert ScenarioType.SIMPLE_API.value == "simple_api"
        assert ScenarioType.COMPLEX_ML.value == "complex_ml"
        assert ScenarioType.MICROSERVICES.value == "microservices"
        assert ScenarioType.DATA_PIPELINE.value == "data_pipeline"
        assert ScenarioType.CUSTOM.value == "custom"


class TestSimulationStatus:
    """Tests for SimulationStatus enum."""

    def test_status_values(self):
        """Test all status values exist."""
        assert SimulationStatus.PENDING.value == "pending"
        assert SimulationStatus.RUNNING.value == "running"
        assert SimulationStatus.COMPLETED.value == "completed"
        assert SimulationStatus.FAILED.value == "failed"
        assert SimulationStatus.CANCELLED.value == "cancelled"


class TestConvenienceFunction:
    """Tests for run_simulation convenience function."""

    @pytest.mark.asyncio
    async def test_run_simulation_default(self):
        """Test run_simulation with defaults."""
        result = await run_simulation()

        assert result.status == SimulationStatus.COMPLETED
        assert result.scenario_name == "Simple API Development"

    @pytest.mark.asyncio
    async def test_run_simulation_with_type(self):
        """Test run_simulation with specific type."""
        result = await run_simulation(ScenarioType.DATA_PIPELINE)

        assert result.status == SimulationStatus.COMPLETED
        assert result.scenario_name == "Data Pipeline Development"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
