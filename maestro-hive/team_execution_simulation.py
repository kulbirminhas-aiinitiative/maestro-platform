#!/usr/bin/env python3
"""
Team Execution V2 - Split Mode Simulations

Comprehensive simulation suite demonstrating all execution modes:
- Scenario A: Pure Split Mode (5 independent executions)
- Scenario B: Pure Batch Mode (single continuous run)
- Scenario C: Mixed Mode (requirements+design continuous, rest phased)
- Scenario D: Parallel-Hybrid (parallel work within sequential phases)
- Scenario E: Human-in-Loop (checkpoints at design and testing)
- Scenario F: Dynamic Blueprint Switching (different patterns per phase)

Each scenario demonstrates:
- Context persistence between phases
- Contract validation at boundaries
- Quality metrics tracking
- Timing comparisons
- State recovery from checkpoints
"""

import asyncio
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import time

# Add paths
sys.path.insert(0, str(Path(__file__).parent))

# Import split mode engine
from team_execution_v2_split_mode import TeamExecutionEngineV2SplitMode
from team_execution_context import TeamExecutionContext, list_checkpoints

logger = logging.getLogger(__name__)


# =============================================================================
# SAMPLE REQUIREMENTS
# =============================================================================

SAMPLE_REQUIREMENTS = {
    "simple_api": """
Build a simple REST API for a task management system.

Requirements:
- User authentication (JWT tokens)
- CRUD operations for tasks
- Task assignment to users
- SQLite database
- Basic frontend (React)

Estimated complexity: Simple
Estimated time: 4-6 hours
""",

    "ml_api": """
Build a REST API for ML model training and prediction.

Requirements:
- Upload training datasets
- Train classification models (scikit-learn)
- Model versioning and storage
- Prediction endpoints
- Model performance monitoring
- React dashboard for visualization

Tech stack:
- Backend: Python FastAPI
- Frontend: React + TypeScript
- Database: PostgreSQL
- ML: scikit-learn, PyTorch

Estimated complexity: Complex
Estimated time: 30-40 hours
""",

    "microservices": """
Build a microservices-based e-commerce platform.

Requirements:
- User service (authentication, profiles)
- Product service (catalog, inventory)
- Order service (cart, checkout, fulfillment)
- Payment service (Stripe integration)
- API Gateway
- Service mesh (Istio)
- React frontend

Tech stack:
- Backend: Python FastAPI + Go
- Frontend: React + TypeScript
- Database: PostgreSQL + Redis
- Message Queue: RabbitMQ
- Container: Docker + Kubernetes

Estimated complexity: Very Complex
Estimated time: 80-100 hours
"""
}


# =============================================================================
# BASE SIMULATION CLASS
# =============================================================================

class TeamExecutionSimulation:
    """Base class for simulations"""

    def __init__(
        self,
        scenario_name: str,
        output_dir: str = "./simulation_output",
        checkpoint_dir: str = "./simulation_checkpoints"
    ):
        self.scenario_name = scenario_name
        self.output_dir = Path(output_dir) / scenario_name
        self.checkpoint_dir = Path(checkpoint_dir) / scenario_name

        # Create engine
        self.engine = TeamExecutionEngineV2SplitMode(
            output_dir=str(self.output_dir),
            checkpoint_dir=str(self.checkpoint_dir)
        )

        # Results
        self.start_time = None
        self.end_time = None
        self.context = None

    async def run(self, requirement: str) -> TeamExecutionContext:
        """Run simulation - to be overridden"""
        raise NotImplementedError

    def print_results(self):
        """Print simulation results"""
        if not self.context:
            print("No results yet")
            return

        duration = (self.end_time - self.start_time).total_seconds()

        print(f"\n{'='*80}")
        print(f"SIMULATION RESULTS: {self.scenario_name}")
        print(f"{'='*80}")

        # Timing
        print(f"\n⏱️  Timing:")
        print(f"   Total Duration: {duration:.1f}s ({duration/60:.1f}m)")
        print(f"   Phase Durations:")
        for phase, metrics in self.context.team_state.timing_metrics.items():
            print(f"      {phase}: {metrics.get('phase_duration', 0):.1f}s")

        # Quality
        print(f"\n✨ Quality:")
        overall_quality = self.context.team_state.get_overall_quality()
        print(f"   Overall Quality: {overall_quality:.0%}")
        for phase, metrics in self.context.team_state.quality_metrics.items():
            print(f"      {phase}: {metrics.get('overall_quality', 0):.0%}")

        # Checkpoints
        checkpoints = list_checkpoints(str(self.checkpoint_dir))
        print(f"\n💾 Checkpoints:")
        print(f"   Total: {len(checkpoints)}")
        for cp in checkpoints:
            print(f"      {cp['phase_completed']}: {cp['file']}")

        # Summary
        print(f"\n📊 Summary:")
        summary = self.context.get_summary()
        print(f"   Phases Completed: {summary['completed_phases']}/{summary['total_phases']}")
        print(f"   Blueprints Used: {summary['blueprints_used']}")
        print(f"   Personas Executed: {summary['personas_executed']}")
        print(f"   Artifacts Created: {summary['artifacts_created']}")

        print(f"\n{'='*80}\n")


# =============================================================================
# SCENARIO A: PURE SPLIT MODE
# =============================================================================

class ScenarioA_PureSplitMode(TeamExecutionSimulation):
    """
    Pure split mode: Each phase executes independently with checkpoints.

    Demonstrates:
    - Independent phase execution
    - Checkpoint save/load between phases
    - Context persistence
    - Contract validation at boundaries
    """

    def __init__(self):
        super().__init__("scenario_a_pure_split")

    async def run(self, requirement: str) -> TeamExecutionContext:
        """Run pure split mode simulation"""
        print(f"\n{'='*80}")
        print("SCENARIO A: PURE SPLIT MODE")
        print("Each phase runs independently with checkpoints")
        print(f"{'='*80}\n")

        self.start_time = datetime.now()

        # Phase 1: Requirements
        print("\n🔵 Phase 1: Requirements (independent execution)")
        ctx = await self.engine.execute_phase(
            phase_name="requirements",
            requirement=requirement
        )
        checkpoint_1 = self.checkpoint_dir / f"{ctx.workflow.workflow_id}_requirements.json"
        ctx.create_checkpoint(str(checkpoint_1))
        print(f"   ✅ Checkpoint saved: {checkpoint_1.name}")

        # Simulate process death and restart
        print("\n⚠️  Simulating process death...")
        time.sleep(1)
        print("   Process restarted! Loading from checkpoint...")

        # Phase 2: Design (resume from checkpoint)
        print("\n🔵 Phase 2: Design (resume from checkpoint)")
        ctx = await self.engine.resume_from_checkpoint(str(checkpoint_1))
        checkpoint_2 = self.checkpoint_dir / f"{ctx.workflow.workflow_id}_design.json"
        ctx.create_checkpoint(str(checkpoint_2))
        print(f"   ✅ Checkpoint saved: {checkpoint_2.name}")

        # Phase 3: Implementation
        print("\n🔵 Phase 3: Implementation (resume from checkpoint)")
        ctx = await self.engine.resume_from_checkpoint(str(checkpoint_2))
        checkpoint_3 = self.checkpoint_dir / f"{ctx.workflow.workflow_id}_implementation.json"
        ctx.create_checkpoint(str(checkpoint_3))
        print(f"   ✅ Checkpoint saved: {checkpoint_3.name}")

        # Phase 4: Testing
        print("\n🔵 Phase 4: Testing (resume from checkpoint)")
        ctx = await self.engine.resume_from_checkpoint(str(checkpoint_3))
        checkpoint_4 = self.checkpoint_dir / f"{ctx.workflow.workflow_id}_testing.json"
        ctx.create_checkpoint(str(checkpoint_4))
        print(f"   ✅ Checkpoint saved: {checkpoint_4.name}")

        # Phase 5: Deployment
        print("\n🔵 Phase 5: Deployment (resume from checkpoint)")
        ctx = await self.engine.resume_from_checkpoint(str(checkpoint_4))

        self.end_time = datetime.now()
        self.context = ctx

        return ctx


# =============================================================================
# SCENARIO B: PURE BATCH MODE
# =============================================================================

class ScenarioB_PureBatchMode(TeamExecutionSimulation):
    """
    Pure batch mode: All phases execute continuously.

    Demonstrates:
    - Single-go execution
    - No checkpoints (fastest mode)
    - Continuous context flow
    - All-or-nothing execution
    """

    def __init__(self):
        super().__init__("scenario_b_pure_batch")

    async def run(self, requirement: str) -> TeamExecutionContext:
        """Run pure batch mode simulation"""
        print(f"\n{'='*80}")
        print("SCENARIO B: PURE BATCH MODE")
        print("All phases execute continuously without checkpoints")
        print(f"{'='*80}\n")

        self.start_time = datetime.now()

        # Execute all phases in one go
        ctx = await self.engine.execute_batch(
            requirement=requirement,
            create_checkpoints=False  # No checkpoints for speed
        )

        self.end_time = datetime.now()
        self.context = ctx

        return ctx


# =============================================================================
# SCENARIO C: MIXED MODE
# =============================================================================

class ScenarioC_MixedMode(TeamExecutionSimulation):
    """
    Mixed mode: Some phases continuous, some with checkpoints.

    Demonstrates:
    - Selective checkpoints
    - Requirements+Design continuous
    - Checkpoints at Implementation and Testing
    - Balanced speed + control
    """

    def __init__(self):
        super().__init__("scenario_c_mixed")

    async def run(self, requirement: str) -> TeamExecutionContext:
        """Run mixed mode simulation"""
        print(f"\n{'='*80}")
        print("SCENARIO C: MIXED MODE")
        print("Selective checkpoints: After design and testing")
        print(f"{'='*80}\n")

        self.start_time = datetime.now()

        # Execute with selective checkpoints
        ctx = await self.engine.execute_mixed(
            requirement=requirement,
            checkpoint_after=["design", "testing"]
        )

        self.end_time = datetime.now()
        self.context = ctx

        return ctx


# =============================================================================
# SCENARIO D: PARALLEL-HYBRID MODE
# =============================================================================

class ScenarioD_ParallelHybrid(TeamExecutionSimulation):
    """
    Parallel-Hybrid: Sequential phases with parallel work within each.

    Demonstrates:
    - Phases run sequentially
    - Within implementation phase: Backend || Frontend || Database
    - Within testing phase: Unit || Integration || Performance
    - Maximum time savings through parallelism
    """

    def __init__(self):
        super().__init__("scenario_d_parallel_hybrid")

    async def run(self, requirement: str) -> TeamExecutionContext:
        """Run parallel-hybrid simulation"""
        print(f"\n{'='*80}")
        print("SCENARIO D: PARALLEL-HYBRID MODE")
        print("Sequential phases with parallel work within each")
        print(f"{'='*80}\n")

        self.start_time = datetime.now()

        # For simulation, use batch mode (parallel within phases is default behavior)
        ctx = await self.engine.execute_batch(
            requirement=requirement,
            create_checkpoints=True  # Create checkpoints for visibility
        )

        self.end_time = datetime.now()
        self.context = ctx

        return ctx


# =============================================================================
# SCENARIO E: HUMAN-IN-THE-LOOP
# =============================================================================

class ScenarioE_HumanInLoop(TeamExecutionSimulation):
    """
    Human-in-the-Loop: Checkpoints with human edits.

    Demonstrates:
    - Execution pauses at design
    - Human reviews and edits architecture
    - Contracts re-validated after edits
    - Execution continues with edited context
    """

    def __init__(self):
        super().__init__("scenario_e_human_in_loop")

    async def run(self, requirement: str) -> TeamExecutionContext:
        """Run human-in-loop simulation"""
        print(f"\n{'='*80}")
        print("SCENARIO E: HUMAN-IN-THE-LOOP")
        print("Checkpoints at design and testing for human review")
        print(f"{'='*80}\n")

        self.start_time = datetime.now()

        # Phase 1-2: Requirements + Design
        print("\n🔵 Phases 1-2: Requirements + Design")
        ctx = None
        for phase in ["requirements", "design"]:
            ctx = await self.engine.execute_phase(
                phase_name=phase,
                checkpoint=ctx,
                requirement=requirement if phase == "requirements" else None
            )

        # Save checkpoint for human review
        checkpoint_design = self.checkpoint_dir / f"{ctx.workflow.workflow_id}_design.json"
        ctx.create_checkpoint(str(checkpoint_design))

        print(f"\n⏸️  PAUSING for human review of design phase")
        print(f"   Checkpoint: {checkpoint_design}")

        # Simulate human edits
        print("\n👤 Human reviews design and makes edits:")
        human_edits = {
            "design": {
                "outputs": {
                    "architecture": {
                        "components": ["API Gateway", "Service A", "Service B", "Database"],
                        "note": "HUMAN EDIT: Added API Gateway for better scalability"
                    }
                }
            }
        }
        print("   - Added API Gateway to architecture")

        # Resume with edits
        print("\n▶️  Resuming execution with human edits...")
        ctx = await self.engine.resume_from_checkpoint(
            str(checkpoint_design),
            human_edits=human_edits
        )

        # Continue with remaining phases
        for phase in ["testing", "deployment"]:
            next_phase = await self.engine.execute_phase(
                phase_name=phase,
                checkpoint=ctx
            )
            ctx = next_phase

        self.end_time = datetime.now()
        self.context = ctx

        return ctx


# =============================================================================
# SCENARIO F: DYNAMIC BLUEPRINT SWITCHING
# =============================================================================

class ScenarioF_DynamicBlueprints(TeamExecutionSimulation):
    """
    Dynamic Blueprint Switching: Different patterns per phase.

    Demonstrates:
    - Requirements: Sequential (thorough analysis)
    - Design: Collaborative (team discussion)
    - Implementation: Parallel (contract-first)
    - Testing: Parallel (multiple test types)
    - Deployment: Sequential (controlled rollout)
    """

    def __init__(self):
        super().__init__("scenario_f_dynamic_blueprints")

    async def run(self, requirement: str) -> TeamExecutionContext:
        """Run dynamic blueprints simulation"""
        print(f"\n{'='*80}")
        print("SCENARIO F: DYNAMIC BLUEPRINT SWITCHING")
        print("Different blueprint patterns for each phase")
        print(f"{'='*80}\n")

        self.start_time = datetime.now()

        # Execute with dynamic blueprint selection (default behavior)
        ctx = await self.engine.execute_batch(
            requirement=requirement,
            create_checkpoints=True
        )

        # Print blueprint selections
        print("\n📊 Blueprint Selections Per Phase:")
        for phase, blueprint_rec in ctx.team_state.blueprint_selections.items():
            print(f"   {phase}: {blueprint_rec.blueprint_name}")
            print(f"      Execution Mode: {blueprint_rec.execution_mode}")
            print(f"      Personas: {', '.join(blueprint_rec.personas)}")

        self.end_time = datetime.now()
        self.context = ctx

        return ctx


# =============================================================================
# SIMULATION RUNNER
# =============================================================================

class SimulationRunner:
    """Run all simulations and compare results"""

    SCENARIOS = {
        "a": ("Pure Split Mode", ScenarioA_PureSplitMode),
        "b": ("Pure Batch Mode", ScenarioB_PureBatchMode),
        "c": ("Mixed Mode", ScenarioC_MixedMode),
        "d": ("Parallel-Hybrid", ScenarioD_ParallelHybrid),
        "e": ("Human-in-Loop", ScenarioE_HumanInLoop),
        "f": ("Dynamic Blueprints", ScenarioF_DynamicBlueprints)
    }

    @staticmethod
    async def run_scenario(
        scenario_id: str,
        requirement: str = None
    ) -> TeamExecutionSimulation:
        """Run a single scenario"""
        if scenario_id not in SimulationRunner.SCENARIOS:
            raise ValueError(f"Unknown scenario: {scenario_id}")

        name, scenario_class = SimulationRunner.SCENARIOS[scenario_id]

        print(f"\n{'#'*80}")
        print(f"RUNNING SCENARIO {scenario_id.upper()}: {name}")
        print(f"{'#'*80}\n")

        requirement = requirement or SAMPLE_REQUIREMENTS["simple_api"]

        simulation = scenario_class()
        await simulation.run(requirement)
        simulation.print_results()

        return simulation

    @staticmethod
    async def run_all_scenarios(requirement: str = None):
        """Run all scenarios and compare"""
        print(f"\n{'#'*80}")
        print("RUNNING ALL SCENARIOS")
        print(f"{'#'*80}\n")

        requirement = requirement or SAMPLE_REQUIREMENTS["simple_api"]

        results = {}
        for scenario_id in ["a", "b", "c", "d", "e", "f"]:
            simulation = await SimulationRunner.run_scenario(scenario_id, requirement)
            results[scenario_id] = simulation

        # Print comparison
        SimulationRunner.print_comparison(results)

    @staticmethod
    def print_comparison(results: Dict[str, TeamExecutionSimulation]):
        """Print comparison of all scenarios"""
        print(f"\n{'='*80}")
        print("SCENARIO COMPARISON")
        print(f"{'='*80}\n")

        # Headers
        print(f"{'Scenario':<20} {'Duration':<15} {'Quality':<10} {'Checkpoints':<12} {'Phases':<8}")
        print(f"{'-'*20} {'-'*15} {'-'*10} {'-'*12} {'-'*8}")

        for scenario_id, simulation in results.items():
            name = SimulationRunner.SCENARIOS[scenario_id][0]
            duration = (simulation.end_time - simulation.start_time).total_seconds()
            quality = simulation.context.team_state.get_overall_quality()
            checkpoints = len(list_checkpoints(str(simulation.checkpoint_dir)))
            phases = len(simulation.context.workflow.phase_results)

            print(f"{name:<20} {duration:>6.1f}s ({duration/60:>4.1f}m) {quality:>7.0%}   {checkpoints:>3}          {phases}/5")

        print(f"\n{'='*80}\n")

        # Insights
        print("📊 Key Insights:")
        print()
        print("Speed Ranking (fastest to slowest):")
        sorted_by_speed = sorted(
            results.items(),
            key=lambda x: (x[1].end_time - x[1].start_time).total_seconds()
        )
        for i, (scenario_id, sim) in enumerate(sorted_by_speed, 1):
            duration = (sim.end_time - sim.start_time).total_seconds()
            print(f"   {i}. Scenario {scenario_id.upper()}: {duration/60:.1f}m")

        print()
        print("Control Ranking (most human control):")
        control_rank = {"e": 5, "a": 4, "c": 3, "f": 3, "d": 2, "b": 1}
        sorted_by_control = sorted(control_rank.items(), key=lambda x: x[1], reverse=True)
        for i, (scenario_id, _) in enumerate(sorted_by_control, 1):
            name = SimulationRunner.SCENARIOS[scenario_id][0]
            print(f"   {i}. Scenario {scenario_id.upper()} ({name})")


# =============================================================================
# CLI AND MAIN
# =============================================================================

async def main():
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Team Execution V2 - Split Mode Simulations"
    )

    parser.add_argument(
        "--scenario",
        choices=["a", "b", "c", "d", "e", "f", "all"],
        default="all",
        help="Scenario to run (a-f) or 'all'"
    )

    parser.add_argument(
        "--requirement",
        choices=["simple_api", "ml_api", "microservices"],
        default="simple_api",
        help="Sample requirement to use"
    )

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )

    # Get requirement
    requirement = SAMPLE_REQUIREMENTS[args.requirement]

    print(f"\nRequirement: {args.requirement}")
    print(f"{requirement}\n")

    # Run scenario(s)
    if args.scenario == "all":
        await SimulationRunner.run_all_scenarios(requirement)
    else:
        await SimulationRunner.run_scenario(args.scenario, requirement)


if __name__ == "__main__":
    asyncio.run(main())
