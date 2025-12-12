#!/usr/bin/env python3
"""
Team Simulator - Scenario-Based Testing for Team Configurations

MD-3019: Team Simulation & Benchmarking
Implements team simulation capabilities for scenario testing and workflow execution.
"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class SimulationStatus(Enum):
    """Status states for simulations."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScenarioType(Enum):
    """Types of simulation scenarios."""

    SIMPLE_API = "simple_api"
    COMPLEX_ML = "complex_ml"
    MICROSERVICES = "microservices"
    DATA_PIPELINE = "data_pipeline"
    CUSTOM = "custom"


@dataclass
class SimulationScenario:
    """Definition of a simulation scenario."""

    name: str
    description: str
    scenario_type: ScenarioType
    team_size: int
    complexity: str  # simple, medium, complex
    timeout_seconds: int = 300
    requirements: Dict[str, Any] = field(default_factory=dict)
    expected_outputs: List[str] = field(default_factory=list)
    validation_rules: List[Callable] = field(default_factory=list)


@dataclass
class SimulationResult:
    """Result of a simulation run."""

    simulation_id: str
    scenario_name: str
    status: SimulationStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    outputs: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, float] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    checkpoints: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "simulation_id": self.simulation_id,
            "scenario_name": self.scenario_name,
            "status": self.status.value,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds,
            "outputs": self.outputs,
            "metrics": self.metrics,
            "errors": self.errors,
            "checkpoints": self.checkpoints,
        }


class TeamSimulator:
    """
    Team Simulator for scenario-based testing.

    Provides capabilities for:
    - Running predefined simulation scenarios
    - Custom scenario execution
    - Performance tracking and metrics collection
    - Checkpoint management for long-running simulations
    """

    # Predefined scenarios
    PREDEFINED_SCENARIOS = {
        ScenarioType.SIMPLE_API: SimulationScenario(
            name="Simple API Development",
            description="Build a REST API with basic CRUD operations",
            scenario_type=ScenarioType.SIMPLE_API,
            team_size=3,
            complexity="simple",
            timeout_seconds=120,
            requirements={
                "backend": "FastAPI",
                "database": "SQLite",
                "auth": "JWT",
            },
            expected_outputs=["api_spec", "code", "tests"],
        ),
        ScenarioType.COMPLEX_ML: SimulationScenario(
            name="ML Pipeline Development",
            description="Build ML training and prediction pipeline",
            scenario_type=ScenarioType.COMPLEX_ML,
            team_size=5,
            complexity="complex",
            timeout_seconds=600,
            requirements={
                "backend": "FastAPI",
                "ml_framework": "scikit-learn",
                "database": "PostgreSQL",
                "frontend": "React",
            },
            expected_outputs=["api_spec", "model_code", "pipeline", "tests", "docs"],
        ),
        ScenarioType.MICROSERVICES: SimulationScenario(
            name="Microservices Architecture",
            description="Build distributed microservices platform",
            scenario_type=ScenarioType.MICROSERVICES,
            team_size=7,
            complexity="complex",
            timeout_seconds=900,
            requirements={
                "services": ["user", "product", "order", "payment"],
                "gateway": True,
                "messaging": "RabbitMQ",
                "orchestration": "Kubernetes",
            },
            expected_outputs=[
                "architecture",
                "service_code",
                "gateway",
                "configs",
                "tests",
            ],
        ),
        ScenarioType.DATA_PIPELINE: SimulationScenario(
            name="Data Pipeline Development",
            description="Build ETL data processing pipeline",
            scenario_type=ScenarioType.DATA_PIPELINE,
            team_size=4,
            complexity="medium",
            timeout_seconds=300,
            requirements={
                "sources": ["csv", "api", "database"],
                "transformations": ["clean", "aggregate", "enrich"],
                "destinations": ["warehouse", "api"],
            },
            expected_outputs=["pipeline_code", "schemas", "monitoring", "tests"],
        ),
    }

    def __init__(
        self,
        output_dir: str = "./simulation_output",
        checkpoint_dir: str = "./simulation_checkpoints",
    ):
        """
        Initialize Team Simulator.

        Args:
            output_dir: Directory for simulation outputs
            checkpoint_dir: Directory for checkpoint files
        """
        self.output_dir = Path(output_dir)
        self.checkpoint_dir = Path(checkpoint_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        self._active_simulations: Dict[str, SimulationResult] = {}
        self._completed_simulations: List[SimulationResult] = []

    async def run_scenario(
        self,
        scenario: SimulationScenario,
        team_config: Optional[Dict[str, Any]] = None,
        callbacks: Optional[Dict[str, Callable]] = None,
    ) -> SimulationResult:
        """
        Run a simulation scenario.

        Args:
            scenario: The scenario to simulate
            team_config: Optional team configuration overrides
            callbacks: Optional callbacks for events (on_phase_start, on_phase_end, etc.)

        Returns:
            SimulationResult with outputs and metrics
        """
        simulation_id = str(uuid.uuid4())[:8]
        start_time = datetime.now()

        result = SimulationResult(
            simulation_id=simulation_id,
            scenario_name=scenario.name,
            status=SimulationStatus.RUNNING,
            start_time=start_time,
        )

        self._active_simulations[simulation_id] = result
        logger.info(
            f"Starting simulation {simulation_id}: {scenario.name}",
            extra={"simulation_id": simulation_id, "scenario": scenario.name},
        )

        try:
            # Execute simulation phases
            phases = ["requirements", "design", "implementation", "testing", "deployment"]

            for phase_idx, phase in enumerate(phases):
                phase_start = time.time()

                # Callback: phase start
                if callbacks and "on_phase_start" in callbacks:
                    callbacks["on_phase_start"](phase, phase_idx + 1, len(phases))

                # Simulate phase execution
                phase_result = await self._execute_phase(
                    simulation_id, scenario, phase, team_config
                )

                # Record checkpoint
                checkpoint = {
                    "phase": phase,
                    "timestamp": datetime.now().isoformat(),
                    "duration_seconds": time.time() - phase_start,
                    "outputs": phase_result.get("outputs", {}),
                }
                result.checkpoints.append(checkpoint)

                # Update metrics
                result.metrics[f"{phase}_duration"] = time.time() - phase_start
                result.metrics[f"{phase}_quality"] = phase_result.get("quality", 0.85)

                # Callback: phase end
                if callbacks and "on_phase_end" in callbacks:
                    callbacks["on_phase_end"](phase, phase_result)

                # Check timeout
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed > scenario.timeout_seconds:
                    raise TimeoutError(
                        f"Simulation exceeded timeout of {scenario.timeout_seconds}s"
                    )

            # Finalize results
            result.end_time = datetime.now()
            result.duration_seconds = (result.end_time - start_time).total_seconds()
            result.status = SimulationStatus.COMPLETED

            # Calculate overall metrics
            result.metrics["overall_quality"] = sum(
                result.metrics.get(f"{p}_quality", 0) for p in phases
            ) / len(phases)
            result.metrics["total_phases"] = len(phases)

            # Collect outputs
            result.outputs = {
                "scenario": scenario.name,
                "team_size": scenario.team_size,
                "complexity": scenario.complexity,
                "phases_completed": phases,
            }

            logger.info(
                f"Simulation {simulation_id} completed successfully",
                extra={
                    "simulation_id": simulation_id,
                    "duration": result.duration_seconds,
                },
            )

        except TimeoutError as e:
            result.status = SimulationStatus.FAILED
            result.errors.append(str(e))
            result.end_time = datetime.now()
            result.duration_seconds = (result.end_time - start_time).total_seconds()
            logger.error(f"Simulation {simulation_id} timed out: {e}")

        except Exception as e:
            result.status = SimulationStatus.FAILED
            result.errors.append(str(e))
            result.end_time = datetime.now()
            result.duration_seconds = (result.end_time - start_time).total_seconds()
            logger.error(f"Simulation {simulation_id} failed: {e}")

        finally:
            del self._active_simulations[simulation_id]
            self._completed_simulations.append(result)

        return result

    async def _execute_phase(
        self,
        simulation_id: str,
        scenario: SimulationScenario,
        phase: str,
        team_config: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Execute a single simulation phase.

        Args:
            simulation_id: Unique simulation identifier
            scenario: The scenario being simulated
            phase: Phase name (requirements, design, etc.)
            team_config: Team configuration

        Returns:
            Phase execution results
        """
        # Simulate phase work with appropriate delays based on complexity
        complexity_multiplier = {"simple": 0.5, "medium": 1.0, "complex": 1.5}
        base_delay = 0.1  # Base delay in seconds for simulation
        delay = base_delay * complexity_multiplier.get(scenario.complexity, 1.0)

        await asyncio.sleep(delay)

        # Generate simulated outputs based on phase
        outputs = self._generate_phase_outputs(phase, scenario)

        # Calculate simulated quality score
        quality = 0.80 + (0.15 * (scenario.team_size / 7))  # Team size affects quality
        quality = min(0.98, quality)  # Cap at 98%

        return {"outputs": outputs, "quality": quality, "phase": phase}

    def _generate_phase_outputs(
        self, phase: str, scenario: SimulationScenario
    ) -> Dict[str, Any]:
        """Generate simulated outputs for a phase."""
        outputs = {
            "requirements": {
                "functional_requirements": ["FR-001", "FR-002", "FR-003"],
                "non_functional_requirements": ["NFR-001", "NFR-002"],
                "acceptance_criteria": scenario.expected_outputs,
            },
            "design": {
                "architecture_diagram": "arch_v1.png",
                "component_design": scenario.requirements,
                "api_specification": "openapi.yaml",
            },
            "implementation": {
                "modules_created": len(scenario.expected_outputs),
                "lines_of_code": 500 * scenario.team_size,
                "files_created": scenario.team_size * 3,
            },
            "testing": {
                "unit_tests": 20 * scenario.team_size,
                "integration_tests": 5 * scenario.team_size,
                "coverage_percent": 85.0,
            },
            "deployment": {
                "deployment_config": "kubernetes",
                "environments": ["dev", "staging", "prod"],
                "monitoring_enabled": True,
            },
        }
        return outputs.get(phase, {})

    async def run_predefined_scenario(
        self,
        scenario_type: ScenarioType,
        team_config: Optional[Dict[str, Any]] = None,
    ) -> SimulationResult:
        """
        Run a predefined simulation scenario.

        Args:
            scenario_type: Type of predefined scenario
            team_config: Optional team configuration overrides

        Returns:
            SimulationResult
        """
        if scenario_type not in self.PREDEFINED_SCENARIOS:
            raise ValueError(f"Unknown scenario type: {scenario_type}")

        scenario = self.PREDEFINED_SCENARIOS[scenario_type]
        return await self.run_scenario(scenario, team_config)

    async def run_custom_scenario(
        self,
        name: str,
        description: str,
        team_size: int,
        complexity: str,
        requirements: Dict[str, Any],
        timeout_seconds: int = 300,
    ) -> SimulationResult:
        """
        Run a custom simulation scenario.

        Args:
            name: Scenario name
            description: Scenario description
            team_size: Number of team members
            complexity: Complexity level (simple, medium, complex)
            requirements: Custom requirements
            timeout_seconds: Timeout for simulation

        Returns:
            SimulationResult
        """
        scenario = SimulationScenario(
            name=name,
            description=description,
            scenario_type=ScenarioType.CUSTOM,
            team_size=team_size,
            complexity=complexity,
            timeout_seconds=timeout_seconds,
            requirements=requirements,
        )
        return await self.run_scenario(scenario)

    def get_active_simulations(self) -> List[Dict[str, Any]]:
        """Get list of currently active simulations."""
        return [
            {
                "simulation_id": sim_id,
                "scenario_name": result.scenario_name,
                "status": result.status.value,
                "start_time": result.start_time.isoformat(),
                "elapsed_seconds": (datetime.now() - result.start_time).total_seconds(),
            }
            for sim_id, result in self._active_simulations.items()
        ]

    def get_simulation_history(
        self, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get history of completed simulations."""
        return [
            result.to_dict()
            for result in self._completed_simulations[-limit:]
        ]

    def cancel_simulation(self, simulation_id: str) -> bool:
        """
        Cancel an active simulation.

        Args:
            simulation_id: ID of simulation to cancel

        Returns:
            True if cancelled, False if not found
        """
        if simulation_id in self._active_simulations:
            result = self._active_simulations[simulation_id]
            result.status = SimulationStatus.CANCELLED
            result.end_time = datetime.now()
            result.duration_seconds = (
                result.end_time - result.start_time
            ).total_seconds()
            logger.info(f"Simulation {simulation_id} cancelled")
            return True
        return False


# Convenience function for running simulations
async def run_simulation(
    scenario_type: ScenarioType = ScenarioType.SIMPLE_API,
    team_config: Optional[Dict[str, Any]] = None,
) -> SimulationResult:
    """
    Convenience function to run a predefined simulation.

    Args:
        scenario_type: Type of scenario to run
        team_config: Optional team configuration

    Returns:
        SimulationResult
    """
    simulator = TeamSimulator()
    return await simulator.run_predefined_scenario(scenario_type, team_config)


if __name__ == "__main__":
    # Demo run
    async def demo():
        simulator = TeamSimulator()

        print("Running Simple API simulation...")
        result = await simulator.run_predefined_scenario(ScenarioType.SIMPLE_API)

        print(f"\nSimulation ID: {result.simulation_id}")
        print(f"Status: {result.status.value}")
        print(f"Duration: {result.duration_seconds:.2f}s")
        print(f"Overall Quality: {result.metrics.get('overall_quality', 0):.1%}")
        print(f"Phases Completed: {len(result.checkpoints)}")

    asyncio.run(demo())
