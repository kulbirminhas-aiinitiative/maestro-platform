#!/usr/bin/env python3
"""
Team Execution Engine V2 - Split Mode

Enables phase-by-phase execution of SDLC workflows with:
- Independent phase execution (can run in separate processes)
- Full state persistence via checkpoints
- Contract validation at phase boundaries
- Human-in-the-loop support
- Blueprint selection per phase
- Batch mode compatibility

Usage:
    # Phase-by-phase execution
    engine = TeamExecutionEngineV2SplitMode()
    ctx = await engine.execute_phase("requirements", requirement="Build API")
    ctx.create_checkpoint("checkpoint_req.json")
    # ... human reviews ...
    ctx = await engine.resume_from_checkpoint("checkpoint_req.json")

    # Batch execution (all phases)
    ctx = await engine.execute_batch(requirement="Build API")

    # Mixed execution
    ctx = await engine.execute_mixed(
        requirement="Build API",
        checkpoint_after=["design", "testing"]
    )
"""

import asyncio
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass
from collections import defaultdict

# Add paths
sys.path.insert(0, str(Path(__file__).parent))

# Import context model
from team_execution_context import (
    TeamExecutionContext,
    CheckpointMetadata,
    CheckpointType,
    validate_checkpoint_file
)

# Import workflow components
conductor_path = Path("/home/ec2-user/projects/conductor")
sys.path.insert(0, str(conductor_path))

from examples.sdlc_workflow_context import PhaseResult, PhaseStatus

# Import team execution engine
from team_execution_v2 import (
    TeamExecutionEngineV2,
    TeamComposerAgent,
    ContractDesignerAgent,
    RequirementClassification,
    BlueprintRecommendation
)

# Import contract validation
try:
    from contracts.integration.contract_manager import ContractManager
    from contracts.integration.exceptions import ValidationException
    CONTRACT_VALIDATION_AVAILABLE = True
except ImportError:
    CONTRACT_VALIDATION_AVAILABLE = False
    ContractManager = None
    ValidationException = Exception

logger = logging.getLogger(__name__)


# =============================================================================
# PHASE CIRCUIT BREAKER
# =============================================================================

class PhaseCircuitBreaker:
    """
    Circuit breaker for phase boundary validation.

    Prevents cascading failures by opening circuit after too many failures.
    """

    def __init__(self, max_failures: int = 3, timeout_seconds: int = 300):
        """
        Initialize circuit breaker.

        Args:
            max_failures: Max failures before opening circuit
            timeout_seconds: Timeout before trying half-open state
        """
        self.max_failures = max_failures
        self.timeout = timeout_seconds
        self.failures = defaultdict(int)
        self.last_failure = {}
        self.state = {}  # "closed", "open", "half-open"

    def is_open(self, boundary: str) -> bool:
        """Check if circuit is open for a boundary"""
        if self.state.get(boundary) != "open":
            return False

        # Check if timeout elapsed -> try half-open
        import time
        if time.time() - self.last_failure.get(boundary, 0) > self.timeout:
            self.state[boundary] = "half-open"
            logger.info(f"Circuit breaker {boundary}: HALF-OPEN (trying again)")
            return False

        return True

    def record_failure(self, boundary: str):
        """Record a validation failure"""
        import time
        self.failures[boundary] += 1
        self.last_failure[boundary] = time.time()

        if self.failures[boundary] >= self.max_failures:
            self.state[boundary] = "open"
            logger.error(f"🔴 Circuit breaker OPEN for {boundary} ({self.failures[boundary]} failures)")

    def record_success(self, boundary: str):
        """Record a validation success"""
        self.failures[boundary] = 0
        self.state[boundary] = "closed"
        logger.info(f"🟢 Circuit breaker CLOSED for {boundary}")


# =============================================================================
# SPLIT MODE EXECUTION ENGINE
# =============================================================================

class TeamExecutionEngineV2SplitMode:
    """
    Split mode execution engine for team_execution_v2.

    Orchestrates phase-by-phase SDLC execution with full state persistence.
    """

    # Standard SDLC phases
    SDLC_PHASES = ["requirements", "design", "implementation", "testing", "deployment"]

    # Phase-specific blueprint recommendations
    PHASE_BLUEPRINT_HINTS = {
        "requirements": {
            "preferred_execution": "sequential",
            "preferred_scaling": "static",
            "rationale": "Requirements analysis benefits from thorough sequential analysis"
        },
        "design": {
            "preferred_execution": "collaborative",
            "preferred_scaling": "static",
            "rationale": "Design decisions need team discussion and consensus"
        },
        "implementation": {
            "preferred_execution": "parallel",
            "preferred_scaling": "elastic",
            "rationale": "Implementation has clear contracts enabling parallelism"
        },
        "testing": {
            "preferred_execution": "parallel",
            "preferred_scaling": "elastic",
            "rationale": "Different test types can run in parallel"
        },
        "deployment": {
            "preferred_execution": "sequential",
            "preferred_scaling": "static",
            "rationale": "Deployment requires careful sequential steps"
        }
    }

    # Quality thresholds per phase
    PHASE_QUALITY_THRESHOLDS = {
        "requirements": 0.75,
        "design": 0.80,
        "implementation": 0.70,
        "testing": 0.85,
        "deployment": 0.90
    }

    def __init__(
        self,
        output_dir: Optional[str] = None,
        checkpoint_dir: Optional[str] = None,
        quality_threshold: float = 0.70,
        enable_contracts: bool = True
    ):
        """
        Initialize split mode execution engine.

        Args:
            output_dir: Directory for generated output
            checkpoint_dir: Directory for checkpoint files
            quality_threshold: Minimum quality score (0-1)
            enable_contracts: Whether to enable contract validation
        """
        self.output_dir = Path(output_dir or "./generated_project")
        self.checkpoint_dir = Path(checkpoint_dir or "./checkpoints")
        self.quality_threshold = quality_threshold

        # Create directories
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        # Create underlying execution engine
        self.engine = TeamExecutionEngineV2(output_dir=self.output_dir)

        # AI agents
        self.team_composer = TeamComposerAgent()
        self.contract_designer = ContractDesignerAgent()

        # Contract validation
        self.enable_contracts = enable_contracts
        self.contract_manager = None
        self.circuit_breaker = PhaseCircuitBreaker()

        if enable_contracts and CONTRACT_VALIDATION_AVAILABLE:
            try:
                self.contract_manager = ContractManager()
                logger.info("✅ Contract validation enabled")
            except Exception as e:
                logger.warning(f"Contract manager init failed: {e}")
                self.enable_contracts = False

        logger.info("="*80)
        logger.info("✅ Team Execution Engine V2 - Split Mode initialized")
        logger.info(f"   Output directory: {self.output_dir}")
        logger.info(f"   Checkpoint directory: {self.checkpoint_dir}")
        logger.info(f"   Quality threshold: {self.quality_threshold:.0%}")
        logger.info(f"   Contract validation: {self.enable_contracts}")
        logger.info("="*80)

    # ========================================================================
    # PROGRESS CALLBACK HELPERS
    # ========================================================================

    async def _emit_progress_event(
        self,
        callback: Optional[callable],
        event: Dict[str, Any]
    ):
        """
        Safely emit progress event to callback.

        Args:
            callback: Progress callback function
            event: Event data to emit
        """
        if callback is None:
            return

        try:
            # Add timestamp if not present
            if "timestamp" not in event:
                event["timestamp"] = datetime.now().isoformat()

            # Call the callback
            if asyncio.iscoroutinefunction(callback):
                await callback(event)
            else:
                callback(event)
        except Exception as e:
            logger.warning(f"Progress callback error: {e}")

    # ========================================================================
    # PHASE EXECUTION
    # ========================================================================

    async def execute_phase(
        self,
        phase_name: str,
        checkpoint: Optional[TeamExecutionContext] = None,
        requirement: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> TeamExecutionContext:
        """
        Execute a single SDLC phase.

        Args:
            phase_name: Name of phase to execute (requirements, design, etc.)
            checkpoint: Previous checkpoint context (if resuming)
            requirement: Initial requirement (required for first phase)
            progress_callback: Optional async callback for progress events
                              Signature: async def callback(event: Dict[str, Any]) -> None

        Returns:
            TeamExecutionContext with this phase completed

        Raises:
            ValueError: If starting non-first phase without checkpoint
            ValueError: If first phase without requirement
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"🎬 EXECUTING PHASE: {phase_name.upper()}")
        logger.info(f"{'='*80}")

        start_time = datetime.now()

        # Step 1: Initialize or load context
        if checkpoint is None:
            if phase_name != self.SDLC_PHASES[0]:
                raise ValueError(
                    f"Cannot start at '{phase_name}' without checkpoint. "
                    f"Either start at '{self.SDLC_PHASES[0]}' or provide checkpoint."
                )
            if requirement is None:
                raise ValueError("requirement is required for first phase")

            # Create new context
            workflow_id = f"workflow-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            context = TeamExecutionContext.create_new(
                requirement=requirement,
                workflow_id=workflow_id,
                execution_mode="phased"
            )
            logger.info(f"📝 Created new workflow: {workflow_id}")
        else:
            context = checkpoint
            logger.info(f"📂 Loaded workflow: {context.workflow.workflow_id}")
            logger.info(f"   Previous phase: {context.workflow.current_phase}")

        # Emit phase_started event
        await self._emit_progress_event(progress_callback, {
            "type": "phase_started",
            "workflow_id": context.workflow.workflow_id,
            "phase": phase_name,
            "execution_mode": context.workflow.execution_mode,
            "phases_completed": len(context.workflow.phase_results)
        })

        # Step 2: Extract phase-specific requirement
        phase_requirement = self._extract_phase_requirement(
            phase_name=phase_name,
            context=context,
            original_requirement=requirement
        )

        logger.info(f"\n📋 Phase requirement:")
        logger.info(f"   {phase_requirement[:200]}...")

        # Step 3: Validate phase boundary (if not first phase)
        if phase_name != self.SDLC_PHASES[0]:
            previous_phase = self._get_previous_phase(phase_name)
            if previous_phase:
                logger.info(f"\n🔍 Validating phase boundary: {previous_phase} → {phase_name}")
                await self._validate_phase_boundary(
                    phase_from=previous_phase,
                    phase_to=phase_name,
                    context=context
                )

        # Step 4: Select blueprint for this phase
        logger.info(f"\n🎯 Selecting blueprint for {phase_name} phase...")
        blueprint_rec = await self._select_blueprint_for_phase(
            phase_name=phase_name,
            context=context,
            phase_requirement=phase_requirement
        )
        context.add_blueprint_selection(phase_name, blueprint_rec)

        logger.info(f"   ✅ Selected: {blueprint_rec.blueprint_name}")
        logger.info(f"      Execution mode: {blueprint_rec.execution_mode}")
        logger.info(f"      Personas: {', '.join(blueprint_rec.personas)}")

        # Emit blueprint_selected event
        await self._emit_progress_event(progress_callback, {
            "type": "blueprint_selected",
            "workflow_id": context.workflow.workflow_id,
            "phase": phase_name,
            "blueprint": blueprint_rec.blueprint_name,
            "execution_mode": blueprint_rec.execution_mode,
            "personas": blueprint_rec.personas
        })

        # Step 5: Execute team for this phase
        logger.info(f"\n🎬 Executing {phase_name} team...")

        # ✅ FIXED: Build rich context with previous outputs
        all_previous_outputs = context.workflow.get_all_previous_outputs(phase_name)
        artifact_paths = self._collect_artifact_paths(context, phase_name)

        # ✅ FIXED: Collect all contracts from previous phases
        previous_contracts = self._collect_previous_contracts(context, phase_name)

        rich_context = {
            "phase": phase_name,
            "quality_threshold": self.PHASE_QUALITY_THRESHOLDS.get(
                phase_name,
                self.quality_threshold
            ),
            # ✅ NEW: Add previous phase outputs
            "previous_phase_outputs": all_previous_outputs,
            # ✅ NEW: Add artifact path mappings
            "artifact_paths": artifact_paths,
            # ✅ NEW: Add previous phase contracts
            "previous_phase_contracts": previous_contracts,
            # ✅ NEW: Add workflow metadata
            "workflow_id": context.workflow.workflow_id,
            "output_dir": str(self.output_dir)
        }

        execution_result = await self.engine.execute(
            requirement=phase_requirement,
            constraints=rich_context  # ✅ FIXED: Pass rich context with contracts
        )

        # Step 6: Extract phase outputs
        phase_outputs = self._extract_phase_outputs(
            phase_name=phase_name,
            execution_result=execution_result
        )

        # Step 7: Collect quality metrics
        quality_metrics = {
            "overall_quality": execution_result["quality"]["overall_quality_score"],
            "contract_fulfillment": (
                execution_result["quality"]["contracts_fulfilled"] /
                execution_result["quality"]["contracts_total"]
                if execution_result["quality"]["contracts_total"] > 0 else 0.0
            ),
            "completeness": execution_result["quality"]["overall_quality_score"]
        }

        # Emit artifacts_created event
        artifacts_list = list(execution_result.get("deliverables", {}).keys())
        if artifacts_list:
            await self._emit_progress_event(progress_callback, {
                "type": "artifacts_created",
                "workflow_id": context.workflow.workflow_id,
                "phase": phase_name,
                "artifacts": artifacts_list,
                "artifact_count": len(artifacts_list)
            })

        # Emit quality_check event
        await self._emit_progress_event(progress_callback, {
            "type": "quality_check",
            "workflow_id": context.workflow.workflow_id,
            "phase": phase_name,
            "quality_score": quality_metrics["overall_quality"],
            "contract_fulfillment": quality_metrics["contract_fulfillment"],
            "threshold": self.PHASE_QUALITY_THRESHOLDS.get(phase_name, self.quality_threshold),
            "passed": quality_metrics["overall_quality"] >= self.PHASE_QUALITY_THRESHOLDS.get(phase_name, self.quality_threshold)
        })

        timing_metrics = {
            "phase_duration": execution_result["duration_seconds"],
            "ai_analysis_time": execution_result.get("classification", {}).get("duration", 0.0),
            "blueprint_selection_time": 0.0,
            "contract_design_time": 0.0,
            "persona_execution_time": execution_result["execution"]["total_duration"]
        }

        # Step 8: Create PhaseResult
        phase_result = PhaseResult(
            phase_name=phase_name,
            status=PhaseStatus.COMPLETED if execution_result["success"] else PhaseStatus.FAILED,
            outputs=phase_outputs,
            context_received=context.workflow.get_all_previous_outputs(phase_name),
            context_passed={f"{phase_name}_output": phase_outputs},
            contracts_validated=[],  # Will be filled by boundary validation
            artifacts_created=list(execution_result.get("deliverables", {}).keys()),
            duration_seconds=execution_result["duration_seconds"],
            started_at=start_time,
            completed_at=datetime.now()
        )

        # Step 9: Add results to context
        context.workflow.add_phase_result(phase_name, phase_result)
        context.add_quality_metrics(phase_name, quality_metrics)
        context.add_timing_metrics(phase_name, timing_metrics)

        # Update checkpoint metadata
        context.checkpoint_metadata.phase_completed = phase_name
        context.checkpoint_metadata.awaiting_phase = self._get_next_phase(phase_name)
        context.checkpoint_metadata.quality_score = quality_metrics["overall_quality"]
        context.checkpoint_metadata.quality_gate_passed = (
            quality_metrics["overall_quality"] >= self.PHASE_QUALITY_THRESHOLDS.get(phase_name, self.quality_threshold)
        )

        logger.info(f"\n{'='*80}")
        logger.info(f"✅ PHASE {phase_name.upper()} COMPLETED")
        logger.info(f"{'='*80}")
        logger.info(f"Quality: {quality_metrics['overall_quality']:.0%}")
        logger.info(f"Duration: {phase_result.duration_seconds:.1f}s")
        logger.info(f"Artifacts: {len(phase_result.artifacts_created)}")
        logger.info(f"Quality Gate: {'✅ PASSED' if context.checkpoint_metadata.quality_gate_passed else '❌ FAILED'}")
        logger.info(f"{'='*80}")

        # Emit phase_completed event
        await self._emit_progress_event(progress_callback, {
            "type": "phase_completed",
            "workflow_id": context.workflow.workflow_id,
            "phase": phase_name,
            "quality_score": quality_metrics["overall_quality"],
            "quality_gate_passed": context.checkpoint_metadata.quality_gate_passed,
            "artifacts": phase_result.artifacts_created,
            "duration_seconds": phase_result.duration_seconds,
            "next_phase": self._get_next_phase(phase_name)
        })

        return context

    # ========================================================================
    # BATCH EXECUTION
    # ========================================================================

    async def execute_batch(
        self,
        requirement: str,
        create_checkpoints: bool = False,
        progress_callback: Optional[callable] = None
    ) -> TeamExecutionContext:
        """
        Execute all SDLC phases continuously (batch mode).

        Args:
            requirement: Project requirement
            create_checkpoints: Whether to create checkpoints after each phase
            progress_callback: Optional async callback for progress events

        Returns:
            TeamExecutionContext with all phases completed
        """
        logger.info(f"\n{'='*80}")
        logger.info("🚀 BATCH EXECUTION: All SDLC Phases Continuously")
        logger.info(f"{'='*80}")
        logger.info(f"Requirement: {requirement[:100]}...")
        logger.info(f"Create checkpoints: {create_checkpoints}")
        logger.info(f"{'='*80}")

        context = None

        # Emit workflow_started event (will be emitted after first phase creates context)

        for i, phase_name in enumerate(self.SDLC_PHASES):
            logger.info(f"\n📍 Phase {i+1}/{len(self.SDLC_PHASES)}: {phase_name}")

            # Execute phase
            context = await self.execute_phase(
                phase_name=phase_name,
                checkpoint=context,
                requirement=requirement if phase_name == self.SDLC_PHASES[0] else None,
                progress_callback=progress_callback
            )

            # Create checkpoint if requested
            if create_checkpoints:
                checkpoint_path = (
                    self.checkpoint_dir /
                    f"{context.workflow.workflow_id}_{phase_name}.json"
                )
                context.create_checkpoint(str(checkpoint_path))
                logger.info(f"💾 Checkpoint saved: {checkpoint_path}")

                # Emit checkpoint_created event
                await self._emit_progress_event(progress_callback, {
                    "type": "checkpoint_created",
                    "workflow_id": context.workflow.workflow_id,
                    "phase": phase_name,
                    "checkpoint_path": str(checkpoint_path),
                    "checkpoint_type": "phase_complete"
                })

        # Mark workflow complete
        context.workflow.completed_at = datetime.now()
        context.checkpoint_metadata.checkpoint_type = CheckpointType.BATCH_COMPLETE

        logger.info(f"\n{'='*80}")
        logger.info("✅ BATCH EXECUTION COMPLETE")
        logger.info(f"{'='*80}")

        # Print summary
        context.print_summary()

        # Emit workflow_completed event
        await self._emit_progress_event(progress_callback, {
            "type": "workflow_completed",
            "workflow_id": context.workflow.workflow_id,
            "total_phases": len(self.SDLC_PHASES),
            "completed_phases": len(context.workflow.phase_results),
            "total_duration": sum(
                phase.duration_seconds
                for phase in context.workflow.phase_results.values()
            )
        })

        return context

    # ========================================================================
    # CHECKPOINT RESUME
    # ========================================================================

    async def resume_from_checkpoint(
        self,
        checkpoint_path: str,
        human_edits: Optional[Dict[str, Any]] = None
    ) -> TeamExecutionContext:
        """
        Resume execution from a checkpoint file.

        Args:
            checkpoint_path: Path to checkpoint JSON file
            human_edits: Optional edits to apply before resuming
                        Format: {phase_name: {"outputs": {...}}}

        Returns:
            TeamExecutionContext ready for next phase
        """
        logger.info(f"\n{'='*80}")
        logger.info("🔄 RESUMING FROM CHECKPOINT")
        logger.info(f"{'='*80}")
        logger.info(f"Checkpoint: {checkpoint_path}")

        # Validate checkpoint
        validation = validate_checkpoint_file(checkpoint_path)
        if not validation["valid"]:
            logger.error("❌ Invalid checkpoint:")
            for issue in validation["issues"]:
                logger.error(f"   - {issue}")
            raise ValueError(f"Invalid checkpoint: {checkpoint_path}")

        logger.info(f"✅ Checkpoint validation passed")

        # Load checkpoint
        context = TeamExecutionContext.load_from_checkpoint(checkpoint_path)
        logger.info(f"✅ Loaded workflow: {context.workflow.workflow_id}")
        logger.info(f"   Last phase: {context.workflow.current_phase}")
        logger.info(f"   Phases completed: {len(context.workflow.phase_results)}")

        # Apply human edits
        if human_edits:
            logger.info(f"\n📝 Applying human edits...")
            context.workflow.apply_human_edits(human_edits)
            context.checkpoint_metadata.human_edits_applied = True
            logger.info(f"✅ Human edits applied")

            # Re-validate contracts after edits
            if self.enable_contracts and self.contract_manager:
                logger.info(f"\n🔍 Re-validating contracts after edits...")
                await self._revalidate_contracts(context)

        # Get next phase
        next_phase = self._get_next_phase(context.workflow.current_phase)
        if not next_phase:
            logger.warning("⚠️  No more phases to execute")
            logger.info("   Workflow is complete!")
            return context

        logger.info(f"\n▶️  Resuming with phase: {next_phase}")

        # Execute next phase
        context = await self.execute_phase(
            phase_name=next_phase,
            checkpoint=context
        )

        return context

    # ========================================================================
    # MIXED EXECUTION
    # ========================================================================

    async def execute_mixed(
        self,
        requirement: str,
        checkpoint_after: List[str],
        progress_callback: Optional[callable] = None
    ) -> TeamExecutionContext:
        """
        Execute workflow with selective checkpoints.

        Args:
            requirement: Project requirement
            checkpoint_after: List of phases after which to create checkpoints
            progress_callback: Optional async callback for progress events

        Returns:
            TeamExecutionContext (may be partially complete if checkpointed)
        """
        logger.info(f"\n{'='*80}")
        logger.info("🔀 MIXED EXECUTION: Selective Checkpoints")
        logger.info(f"{'='*80}")
        logger.info(f"Requirement: {requirement[:100]}...")
        logger.info(f"Checkpoints after: {', '.join(checkpoint_after)}")
        logger.info(f"{'='*80}")

        context = None

        for i, phase_name in enumerate(self.SDLC_PHASES):
            logger.info(f"\n📍 Phase {i+1}/{len(self.SDLC_PHASES)}: {phase_name}")

            # Check if this is a checkpoint phase
            is_checkpoint_phase = phase_name in checkpoint_after

            if is_checkpoint_phase:
                logger.info("   🔍 [CHECKPOINT PHASE - Will save after execution]")

            # Execute phase
            context = await self.execute_phase(
                phase_name=phase_name,
                checkpoint=context,
                requirement=requirement if phase_name == self.SDLC_PHASES[0] else None,
                progress_callback=progress_callback
            )

            # Create checkpoint if this is a checkpoint phase
            if is_checkpoint_phase:
                next_phase = self._get_next_phase(phase_name)
                if next_phase:  # Only checkpoint if there are more phases
                    checkpoint_path = (
                        self.checkpoint_dir /
                        f"{context.workflow.workflow_id}_{phase_name}.json"
                    )
                    context.workflow.awaiting_human_review = True
                    context.checkpoint_metadata.awaiting_human_review = True
                    context.create_checkpoint(str(checkpoint_path))

                    logger.info(f"\n💾 Checkpoint saved: {checkpoint_path}")
                    logger.info("⏸️  Workflow paused for human review")
                    logger.info(f"   To resume: await engine.resume_from_checkpoint('{checkpoint_path}')")

                    # Emit checkpoint_created event
                    await self._emit_progress_event(progress_callback, {
                        "type": "checkpoint_created",
                        "workflow_id": context.workflow.workflow_id,
                        "phase": phase_name,
                        "checkpoint_path": str(checkpoint_path),
                        "checkpoint_type": "human_review",
                        "awaiting_human_review": True,
                        "next_phase": next_phase
                    })

                    return context

        # Mark workflow complete
        context.workflow.completed_at = datetime.now()

        logger.info(f"\n{'='*80}")
        logger.info("✅ MIXED EXECUTION COMPLETE")
        logger.info(f"{'='*80}")

        context.print_summary()

        # Emit workflow_completed event
        await self._emit_progress_event(progress_callback, {
            "type": "workflow_completed",
            "workflow_id": context.workflow.workflow_id,
            "total_phases": len(self.SDLC_PHASES),
            "completed_phases": len(context.workflow.phase_results),
            "total_duration": sum(
                phase.duration_seconds
                for phase in context.workflow.phase_results.values()
            )
        })

        return context

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def _extract_phase_requirement(
        self,
        phase_name: str,
        context: TeamExecutionContext,
        original_requirement: Optional[str] = None
    ) -> str:
        """
        Extract phase-specific requirement from context.

        ✅ FIXED: Now includes FULL context from all previous phases
        ✅ FIXED: Includes artifacts, deliverables, and instructions

        Args:
            phase_name: Current phase
            context: Workflow context
            original_requirement: Original requirement (for first phase)

        Returns:
            Phase-specific requirement string with complete context
        """
        # For first phase, use original requirement
        if phase_name == self.SDLC_PHASES[0]:
            base_requirement = original_requirement or context.workflow.metadata.get("initial_requirement", "")
            return f"""# {phase_name.upper()} PHASE

## Project Requirement
{base_requirement}

## Phase Objective
Analyze and document project requirements."""

        # ✅ FIXED: Get FULL context from ALL previous phases
        previous_outputs = context.workflow.get_all_previous_outputs(phase_name)

        # Build comprehensive requirement
        requirement_parts = [
            f"# {phase_name.upper()} PHASE\n",
            f"## Original Project Requirement",
            original_requirement or context.workflow.metadata.get("initial_requirement", ""),
            f"\n## Execution Context",
            f"- Current Phase: {phase_name}",
            f"- Previous Phases Completed: {', '.join(context.workflow.phase_order)}",
            f"- Execution Mode: {context.workflow.execution_mode}",
        ]

        # ✅ FIXED: Include FULL outputs from ALL previous phases
        if previous_outputs:
            requirement_parts.append(f"\n## 📦 Complete Context from Previous Phases\n")
            requirement_parts.append("You are building upon work completed by previous team members. ")
            requirement_parts.append("Review their deliverables carefully before proceeding.\n")

            for prev_phase_name, prev_output in previous_outputs.items():
                requirement_parts.append(f"\n### {prev_phase_name.upper()} Phase Deliverables:\n")

                # ✅ FIXED: Include FULL output (no truncation!)
                if isinstance(prev_output, dict):
                    # Pretty print with full detail
                    requirement_parts.append("```json")
                    requirement_parts.append(json.dumps(prev_output, indent=2))  # ✅ FULL, not [:500]
                    requirement_parts.append("```\n")
                else:
                    requirement_parts.append(str(prev_output))
                    requirement_parts.append("\n")

                # ✅ NEW: Include artifacts created
                phase_result = context.workflow.get_phase_result(prev_phase_name)
                if phase_result and phase_result.artifacts_created:
                    requirement_parts.append(f"\n**Artifacts Created:**\n")
                    for artifact in phase_result.artifacts_created:
                        requirement_parts.append(f"- {artifact}\n")

                # ✅ NEW: Include instructions passed forward
                if phase_result and phase_result.context_passed:
                    requirement_parts.append(f"\n**Instructions for Next Phase:**\n")
                    for key, value in phase_result.context_passed.items():
                        requirement_parts.append(f"- **{key}**: {value}\n")

        # ✅ NEW: Include all available artifacts
        if context.workflow.shared_artifacts:
            requirement_parts.append(f"\n## 📄 All Available Artifacts\n")
            requirement_parts.append("The following artifacts have been created and are available for your use:\n\n")

            for artifact in context.workflow.shared_artifacts:
                requirement_parts.append(
                    f"- `{artifact['name']}` (created by {artifact['created_by_phase']} phase"
                )
                if artifact.get('created_at'):
                    requirement_parts.append(f" at {artifact['created_at']}")
                requirement_parts.append(")\n")

        # ✅ NEW: Add phase-specific instructions
        requirement_parts.append(f"\n## 🎯 Your Objective for {phase_name.upper()} Phase\n")

        phase_objectives = {
            "requirements": "Analyze and document detailed requirements based on the project description.",
            "design": "Design the system architecture, APIs, database schema, and component structure based on requirements.",
            "implementation": "Implement the system according to the design specifications. Use the API specs, database schemas, and architecture from the design phase.",
            "testing": "Create comprehensive tests for the implemented system. Test against the specifications from design phase.",
            "deployment": "Deploy the tested system. Use configurations and infrastructure designs from previous phases."
        }

        requirement_parts.append(phase_objectives.get(phase_name, f"Complete the {phase_name} phase deliverables."))
        requirement_parts.append("\n")

        return "\n".join(requirement_parts)

    async def _select_blueprint_for_phase(
        self,
        phase_name: str,
        context: TeamExecutionContext,
        phase_requirement: str
    ) -> BlueprintRecommendation:
        """Select appropriate blueprint for a phase"""
        # Use team composer to analyze phase requirement
        if context.team_state.classification is None:
            # First time - analyze full requirement
            original_req = context.workflow.metadata.get("initial_requirement", "")
            classification = await self.team_composer.analyze_requirement(original_req)
            context.team_state.classification = classification
        else:
            classification = context.team_state.classification

        # Get blueprint recommendation with phase hints
        constraints = {
            "phase": phase_name,
            **self.PHASE_BLUEPRINT_HINTS.get(phase_name, {})
        }

        blueprint_rec = await self.team_composer.recommend_blueprint(
            classification,
            constraints
        )

        return blueprint_rec

    def _extract_phase_outputs(
        self,
        phase_name: str,
        execution_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extract phase outputs with FULL artifact tracking.

        ✅ FIXED: Now includes artifact_paths, artifacts_content, and summary
        """
        # Collect all artifact paths
        artifact_paths = []
        for persona_id, persona_result in execution_result.get("deliverables", {}).items():
            artifact_paths.extend(persona_result.get("files_created", []))

        # Read key artifacts (requirements docs, API specs, etc.)
        artifacts_content = {}
        key_files = self._identify_key_files(artifact_paths)
        for file_path in key_files:
            try:
                with open(file_path, 'r') as f:
                    artifacts_content[file_path] = f.read()
            except Exception as e:
                logger.warning(f"Could not read artifact {file_path}: {e}")

        # Create comprehensive summary
        summary = self._create_phase_summary(phase_name, execution_result, artifacts_content)

        return {
            "phase": phase_name,
            "artifact_paths": artifact_paths,  # ✅ NEW
            "artifacts_content": artifacts_content,  # ✅ NEW
            "summary": summary,  # ✅ NEW
            "deliverables": execution_result.get("deliverables", {}),
            "quality": execution_result.get("quality", {}),
            "execution_summary": {
                "personas": execution_result.get("team", {}).get("personas", []),
                "blueprint": execution_result.get("blueprint", {}).get("name"),
                "duration": execution_result.get("duration_seconds", 0.0)
            }
        }

    def _identify_key_files(self, artifact_paths: List[str]) -> List[str]:
        """Identify key files that should be passed to next phase."""
        key_patterns = [
            "requirements",
            "user_stories",
            "architecture",
            "api_spec",
            "design",
            "contract",
            "README",
            "schema",
            "model"
        ]

        key_files = []
        for path in artifact_paths:
            path_lower = path.lower()
            if any(pattern in path_lower for pattern in key_patterns):
                key_files.append(path)

        return key_files

    def _create_phase_summary(
        self,
        phase_name: str,
        execution_result: Dict[str, Any],
        artifacts_content: Dict[str, str]
    ) -> str:
        """Create AI-generated summary of phase outputs."""
        summary_parts = [
            f"Phase: {phase_name}",
            f"Status: {execution_result.get('success', False)}",
            f"Artifacts: {len(artifacts_content)} key files",
        ]

        # Add brief excerpts from key files
        for file_path, content in artifacts_content.items():
            file_name = Path(file_path).name
            excerpt = content[:500] if len(content) > 500 else content
            summary_parts.append(f"\n{file_name}:\n{excerpt}\n")

        return "\n".join(summary_parts)

    async def _validate_phase_boundary(
        self,
        phase_from: str,
        phase_to: str,
        context: TeamExecutionContext
    ):
        """Validate phase boundary using ContractManager"""
        if not self.enable_contracts or not self.contract_manager:
            logger.info("   ⏭️  Skipping contract validation (disabled)")
            return

        boundary_id = f"{phase_from}-{phase_to}"

        # Check circuit breaker
        if self.circuit_breaker.is_open(boundary_id):
            logger.error(f"   🔴 Circuit breaker OPEN for {boundary_id}")
            raise ValidationException(f"Circuit breaker open for {boundary_id}")

        try:
            # Get previous phase result
            prev_result = context.workflow.get_phase_result(phase_from)
            if not prev_result:
                logger.warning(f"   ⚠️  No result from {phase_from}, skipping validation")
                return

            # Create contract message
            message = {
                "id": f"phase-transition-{boundary_id}",
                "ts": datetime.utcnow().isoformat(),
                "sender": f"phase-{phase_from}",
                "receiver": f"phase-{phase_to}",
                "performative": "inform",
                "content": prev_result.outputs,
                "metadata": {
                    "quality_score": context.team_state.quality_metrics.get(phase_from, {}).get("overall_quality", 0.0),
                    "artifacts": prev_result.artifacts_created
                }
            }

            # Validate
            result = self.contract_manager.process_incoming_message(
                message=message,
                sender_id=f"phase-{phase_from}",
                require_signature=False
            )

            self.circuit_breaker.record_success(boundary_id)

            # Record validation
            context.workflow.add_contract_validation(
                phase=phase_to,
                contract_id=boundary_id,
                validation_result={"passed": True, "intent": str(result.get("intent"))}
            )

            logger.info(f"   ✅ Contract validation passed")

        except ValidationException as e:
            self.circuit_breaker.record_failure(boundary_id)
            logger.error(f"   ❌ Contract validation failed: {e}")
            raise

    async def _revalidate_contracts(self, context: TeamExecutionContext):
        """Re-validate all contracts after human edits"""
        for i, phase_name in enumerate(context.workflow.phase_order):
            if i == 0:
                continue  # Skip first phase

            previous_phase = context.workflow.phase_order[i-1]
            await self._validate_phase_boundary(
                phase_from=previous_phase,
                phase_to=phase_name,
                context=context
            )

    def _get_next_phase(self, current_phase: str) -> Optional[str]:
        """Get next phase after current_phase"""
        try:
            index = self.SDLC_PHASES.index(current_phase)
            if index < len(self.SDLC_PHASES) - 1:
                return self.SDLC_PHASES[index + 1]
        except ValueError:
            pass
        return None

    def _get_previous_phase(self, current_phase: str) -> Optional[str]:
        """Get previous phase before current_phase"""
        try:
            index = self.SDLC_PHASES.index(current_phase)
            if index > 0:
                return self.SDLC_PHASES[index - 1]
        except ValueError:
            pass
        return None

    def _collect_artifact_paths(
        self,
        context: TeamExecutionContext,
        current_phase: str
    ) -> Dict[str, List[str]]:
        """
        Collect all artifact paths from previous phases.

        Args:
            context: Workflow context
            current_phase: Current phase (artifacts before this are collected)

        Returns:
            Dict mapping phase_name -> list of artifact paths
        """
        artifact_map = {}

        for phase_name in context.workflow.phase_order:
            if phase_name == current_phase:
                break  # Don't include current phase

            phase_result = context.workflow.get_phase_result(phase_name)
            if phase_result:
                artifact_map[phase_name] = phase_result.artifacts_created

        return artifact_map

    def _collect_previous_contracts(
        self,
        context: TeamExecutionContext,
        current_phase: str
    ) -> List[Any]:
        """
        Collect all contracts from previous phases for contract lifecycle.

        ✅ NEW: Accumulates contracts to establish dependencies between phases

        Args:
            context: Workflow context
            current_phase: Current phase (contracts before this are collected)

        Returns:
            List of ContractSpecification objects from previous phases
        """
        from team_execution_v2 import ContractSpecification

        all_contracts = []

        # Get contracts from each previous phase's outputs
        for phase_name in context.workflow.phase_order:
            if phase_name == current_phase:
                break  # Don't include current phase

            phase_result = context.workflow.get_phase_result(phase_name)
            if phase_result and phase_result.outputs:
                # Extract contracts from phase outputs if they exist
                # Contracts are stored in the execution_result under "contracts"
                if isinstance(phase_result.outputs, dict) and "contracts" in phase_result.outputs:
                    phase_contracts_data = phase_result.outputs["contracts"]

                    # Convert dict format back to ContractSpecification objects
                    for contract_data in phase_contracts_data:
                        try:
                            contract = ContractSpecification(
                                id=contract_data.get("id", ""),
                                name=contract_data.get("name", ""),
                                version=contract_data.get("version", "v1.0"),
                                contract_type=contract_data.get("type", "Deliverable"),
                                deliverables=contract_data.get("deliverables", []),
                                dependencies=contract_data.get("dependencies", []),
                                provider_persona_id=contract_data.get("provider", ""),
                                consumer_persona_ids=contract_data.get("consumers", []),
                                acceptance_criteria=contract_data.get("acceptance_criteria", []),
                                interface_spec=contract_data.get("interface_spec"),
                                mock_available=contract_data.get("mock_available", False),
                                mock_endpoint=contract_data.get("mock_endpoint"),
                                estimated_effort_hours=contract_data.get("estimated_effort_hours", 0.0)
                            )
                            all_contracts.append(contract)
                        except Exception as e:
                            logger.warning(f"Could not reconstruct contract from {phase_name}: {e}")

        if all_contracts:
            logger.info(f"   🔗 Collected {len(all_contracts)} contract(s) from previous phases")

        return all_contracts


# =============================================================================
# CLI ENTRY POINT
# =============================================================================

async def main():
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Team Execution Engine V2 - Split Mode",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Mode selection
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("--batch", action="store_true", help="Batch mode (all phases)")
    mode_group.add_argument("--phase", help="Execute single phase")
    mode_group.add_argument("--resume", help="Resume from checkpoint file")
    mode_group.add_argument("--mixed", action="store_true", help="Mixed mode with selective checkpoints")

    # Common arguments
    parser.add_argument("--requirement", help="Project requirement")
    parser.add_argument("--output", help="Output directory", default="./generated_project")
    parser.add_argument("--checkpoint-dir", help="Checkpoint directory", default="./checkpoints")
    parser.add_argument("--checkpoint-after", nargs="+", help="Phases to checkpoint after (for mixed mode)")
    parser.add_argument("--create-checkpoints", action="store_true", help="Create checkpoints in batch mode")
    parser.add_argument("--quality-threshold", type=float, default=0.70, help="Quality threshold")

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )

    # Create engine
    engine = TeamExecutionEngineV2SplitMode(
        output_dir=args.output,
        checkpoint_dir=args.checkpoint_dir,
        quality_threshold=args.quality_threshold
    )

    # Execute based on mode
    if args.batch:
        if not args.requirement:
            parser.error("--requirement is required for batch mode")

        context = await engine.execute_batch(
            requirement=args.requirement,
            create_checkpoints=args.create_checkpoints
        )

    elif args.phase:
        if not args.requirement:
            parser.error("--requirement is required for phase execution")

        context = await engine.execute_phase(
            phase_name=args.phase,
            requirement=args.requirement
        )

        # Save checkpoint
        checkpoint_path = Path(args.checkpoint_dir) / f"{context.workflow.workflow_id}_{args.phase}.json"
        context.create_checkpoint(str(checkpoint_path))
        print(f"\n💾 Checkpoint saved: {checkpoint_path}")

    elif args.resume:
        context = await engine.resume_from_checkpoint(
            checkpoint_path=args.resume
        )

    elif args.mixed:
        if not args.requirement:
            parser.error("--requirement is required for mixed mode")
        if not args.checkpoint_after:
            parser.error("--checkpoint-after is required for mixed mode")

        context = await engine.execute_mixed(
            requirement=args.requirement,
            checkpoint_after=args.checkpoint_after
        )

    print("\n" + "="*80)
    print("EXECUTION COMPLETE")
    print("="*80)
    context.print_summary()


if __name__ == "__main__":
    asyncio.run(main())
