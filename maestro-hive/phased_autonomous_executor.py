#!/usr/bin/env python3
"""
Phased Autonomous SDLC Executor with Progressive Quality Management

This system addresses the critical requirements:
1. Phase-based execution with clear phase boundaries
2. Entry and exit gates for each phase to detect failures early
3. Progressive quality thresholds that increase with each iteration
4. Intelligent phase rework with minimal persona re-execution
5. Dynamic team composition based on phase and iteration

Key Innovations:
- Early failure detection via phase gates (prevent divergence)
- Progressive quality: Iteration N+1 has higher standards than Iteration N
- Smart rework: Only re-execute personas that failed, not entire phase
- Adaptive teams: Phase/iteration-specific persona selection
- Resumable: Can pause/resume at any phase

Workflow:
┌─────────────────────────────────────────────────────┐
│ Phase 1: Requirements                               │
│ Entry Gate → Execute Personas → Exit Gate          │
│ ✓ Pass: → Phase 2   ✗ Fail: → Rework              │
└─────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────┐
│ Phase 2: Design                                     │
│ Entry Gate → Execute Personas → Exit Gate          │
│ Quality Threshold: Iteration 1 = 60%, Iter 2 = 75% │
└─────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────┐
│ Phase 3: Implementation                             │
│ Entry Gate → Execute Personas → Exit Gate          │
│ Quality Threshold: Progressive + Previous Best     │
└─────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────┐
│ Phase 4: Testing & QA                               │
│ Entry Gate → Execute Personas → Exit Gate          │
│ Higher thresholds: Must improve on previous        │
└─────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────┐
│ Phase 5: Deployment                                 │
│ Entry Gate → Execute Personas → Exit Gate          │
│ ✓ Pass: → Production Ready                         │
└─────────────────────────────────────────────────────┘

Usage:
    # Start fresh
    python phased_autonomous_executor.py \\
        --requirement "Create task management system" \\
        --session task_mgmt_v1 \\
        --max-phase-iterations 3

    # Resume from checkpoint
    python phased_autonomous_executor.py \\
        --resume task_mgmt_v1

    # Validate and remediate existing project
    python phased_autonomous_executor.py \\
        --validate sunday_com/sunday_com \\
        --remediate
"""

import asyncio
import sys
import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field, asdict
import logging
from enum import Enum

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

# Import existing components
from phase_models import SDLCPhase, PhaseState, PhaseExecution, PhaseGateResult, PhaseIssue, QualityThresholds
from phase_gate_validator import PhaseGateValidator
from progressive_quality_manager import ProgressiveQualityManager
from session_manager import SessionManager, SDLCSession
from team_organization import TeamOrganization
from validation_utils import (
    validate_persona_deliverables,
    detect_project_type,
    analyze_implementation_quality
)

logger = logging.getLogger(__name__)


# ============================================================================
# CONSTANTS
# ============================================================================

# Quality and improvement thresholds
MIN_QUALITY_IMPROVEMENT = 0.05  # Minimum 5% improvement required between iterations
REMEDIATION_THRESHOLD = 0.80  # Quality score below this triggers remediation
VALIDATION_PASS_THRESHOLD = 0.80  # Minimum score to pass validation


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class PhaseCheckpoint:
    """Checkpoint data for resumable execution"""
    session_id: str
    current_phase: SDLCPhase
    phase_iteration: int
    global_iteration: int
    completed_phases: List[SDLCPhase]
    phase_executions: List[Dict[str, Any]]  # Serialized PhaseExecution objects
    best_quality_scores: Dict[str, float]  # phase -> best score achieved
    failed_personas: Dict[str, List[str]] = field(default_factory=dict)  # phase -> list of failed personas
    created_at: str = ""
    last_updated: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization"""
        return {
            **asdict(self),
            "current_phase": self.current_phase.value if self.current_phase else None,
            "completed_phases": [p.value for p in self.completed_phases],
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PhaseCheckpoint":
        """Load from dict"""
        return cls(
            session_id=data["session_id"],
            current_phase=SDLCPhase(data["current_phase"]) if data["current_phase"] else None,
            phase_iteration=data["phase_iteration"],
            global_iteration=data["global_iteration"],
            completed_phases=[SDLCPhase(p) for p in data["completed_phases"]],
            phase_executions=data["phase_executions"],
            best_quality_scores=data["best_quality_scores"],
            failed_personas=data.get("failed_personas", {}),
            created_at=data.get("created_at", ""),
            last_updated=data.get("last_updated", "")
        )


@dataclass
class PhasePersonaMapping:
    """Define which personas execute in each phase"""
    phase: SDLCPhase
    required_personas: List[str]  # Must execute
    optional_personas: List[str] = field(default_factory=list)  # Execute on rework/iteration > 1
    rework_personas: List[str] = field(default_factory=list)  # Only execute during rework


# Default phase-to-persona mapping
DEFAULT_PHASE_MAPPINGS = [
    PhasePersonaMapping(
        phase=SDLCPhase.REQUIREMENTS,
        required_personas=["requirement_analyst"],
        optional_personas=[],
        rework_personas=["requirement_analyst"]  # Re-analyze requirements on rework
    ),
    PhasePersonaMapping(
        phase=SDLCPhase.DESIGN,
        required_personas=["solution_architect", "database_specialist"],
        optional_personas=["security_specialist"],  # Add on iteration 2+
        rework_personas=["solution_architect"]  # Re-architect on rework
    ),
    PhasePersonaMapping(
        phase=SDLCPhase.IMPLEMENTATION,
        required_personas=["backend_developer", "frontend_developer"],
        optional_personas=["database_specialist"],  # Re-run if DB issues
        rework_personas=[]  # Identify failed personas dynamically
    ),
    PhasePersonaMapping(
        phase=SDLCPhase.TESTING,
        required_personas=["qa_engineer", "unit_tester"],
        optional_personas=["integration_tester"],
        rework_personas=["qa_engineer"]  # Re-validate on rework
    ),
    PhasePersonaMapping(
        phase=SDLCPhase.DEPLOYMENT,
        required_personas=["devops_engineer", "deployment_integration_tester"],
        optional_personas=["project_reviewer"],
        rework_personas=["deployment_integration_tester"]
    )
]


# ============================================================================
# PHASED AUTONOMOUS EXECUTOR
# ============================================================================

class PhasedAutonomousExecutor:
    """
    Autonomous executor with phase-based workflow and progressive quality
    
    Key Features:
    1. Phased execution with entry/exit gates
    2. Progressive quality thresholds (increase per iteration)
    3. Early failure detection (gate validation)
    4. Smart rework (minimal persona re-execution)
    5. Dynamic team composition
    """
    
    def __init__(
        self,
        session_id: str,
        requirement: str,
        output_dir: Optional[Path] = None,
        max_phase_iterations: int = 3,
        max_global_iterations: int = 10,
        phase_mappings: Optional[List[PhasePersonaMapping]] = None,
        enable_progressive_quality: bool = True
    ):
        self.session_id = session_id
        self.requirement = requirement
        self.output_dir = output_dir or Path(f"./sdlc_output/{session_id}")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_phase_iterations = max_phase_iterations
        self.max_global_iterations = max_global_iterations
        self.phase_mappings = phase_mappings or DEFAULT_PHASE_MAPPINGS
        self.enable_progressive_quality = enable_progressive_quality
        
        # Components
        self.session_manager = SessionManager()
        self.gate_validator = PhaseGateValidator()
        self.quality_manager = ProgressiveQualityManager() if enable_progressive_quality else None
        
        # Checkpoint management
        self.checkpoint_file = Path(f"sdlc_sessions/checkpoints/{session_id}_checkpoint.json")
        self.checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Execution state
        self.checkpoint: Optional[PhaseCheckpoint] = None
        self.phase_executions: List[PhaseExecution] = []
        self.best_quality_scores: Dict[str, float] = {}  # phase -> best score
        
    # ========================================================================
    # CHECKPOINT MANAGEMENT
    # ========================================================================
    
    def save_checkpoint(self):
        """Save current execution state"""
        if not self.checkpoint:
            return
        
        try:
            self.checkpoint.last_updated = datetime.now().isoformat()
            self.checkpoint.phase_executions = [
                exec.to_dict() for exec in self.phase_executions
            ]
            self.checkpoint.best_quality_scores = self.best_quality_scores
            
            # Ensure directory exists
            self.checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write to temporary file first, then rename (atomic operation)
            temp_file = self.checkpoint_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(self.checkpoint.to_dict(), f, indent=2)
            
            # Atomic rename
            temp_file.replace(self.checkpoint_file)
            
            logger.info(f"💾 Checkpoint saved: {self.checkpoint_file}")
            
        except Exception as e:
            logger.error(f"❌ Failed to save checkpoint: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Don't fail the entire execution if checkpoint save fails
            # but log it prominently
    
    def load_checkpoint(self) -> bool:
        """Load execution state from checkpoint"""
        if not self.checkpoint_file.exists():
            logger.info(f"📂 No checkpoint found at {self.checkpoint_file}")
            return False
        
        try:
            with open(self.checkpoint_file) as f:
                data = json.load(f)
            
            self.checkpoint = PhaseCheckpoint.from_dict(data)
            self.best_quality_scores = self.checkpoint.best_quality_scores
            
            logger.info(f"📂 Loaded checkpoint: {self.checkpoint.current_phase}")
            logger.info(f"   Iteration: {self.checkpoint.global_iteration}")
            logger.info(f"   Completed phases: {[p.value for p in self.checkpoint.completed_phases]}")
            
            return True
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Checkpoint file is corrupted (invalid JSON): {e}")
            logger.warning("   Starting fresh execution instead")
            return False
            
        except KeyError as e:
            logger.error(f"❌ Checkpoint file is missing required field: {e}")
            logger.warning("   Starting fresh execution instead")
            return False
            
        except Exception as e:
            logger.error(f"❌ Failed to load checkpoint: {e}")
            import traceback
            logger.error(traceback.format_exc())
            logger.warning("   Starting fresh execution instead")
            return False
    
    def create_checkpoint(self, current_phase: SDLCPhase, phase_iteration: int, global_iteration: int):
        """Create new checkpoint"""
        self.checkpoint = PhaseCheckpoint(
            session_id=self.session_id,
            current_phase=current_phase,
            phase_iteration=phase_iteration,
            global_iteration=global_iteration,
            completed_phases=[],
            phase_executions=[],
            best_quality_scores={},
            failed_personas={},
            created_at=datetime.now().isoformat(),
            last_updated=datetime.now().isoformat()
        )
        self.save_checkpoint()
    
    # ========================================================================
    # PHASE EXECUTION
    # ========================================================================
    
    async def execute_autonomous(self) -> Dict[str, Any]:
        """
        Main autonomous execution loop
        
        Returns:
            Final execution results
        """
        logger.info("="*80)
        logger.info("🚀 PHASED AUTONOMOUS SDLC EXECUTOR")
        logger.info("="*80)
        logger.info(f"📝 Session: {self.session_id}")
        logger.info(f"🎯 Requirement: {self.requirement[:80]}...")
        logger.info(f"📁 Output: {self.output_dir}")
        logger.info(f"🔄 Max phase iterations: {self.max_phase_iterations}")
        logger.info(f"🔄 Max global iterations: {self.max_global_iterations}")
        logger.info(f"📈 Progressive quality: {'Enabled' if self.enable_progressive_quality else 'Disabled'}")
        logger.info("="*80)
        
        # Try to load checkpoint
        if not self.load_checkpoint():
            # Start fresh
            self.create_checkpoint(
                current_phase=SDLCPhase.REQUIREMENTS,
                phase_iteration=1,
                global_iteration=1
            )
        
        global_iteration = self.checkpoint.global_iteration
        
        # Execute phases in order
        for global_iteration in range(self.checkpoint.global_iteration, self.max_global_iterations + 1):
            logger.info(f"\n{'='*80}")
            logger.info(f"🔄 GLOBAL ITERATION {global_iteration}/{self.max_global_iterations}")
            logger.info(f"{'='*80}\n")
            
            self.checkpoint.global_iteration = global_iteration
            
            # Get phases to execute
            if self.checkpoint.completed_phases:
                # Resume from current phase
                start_phase_idx = list(SDLCPhase).index(self.checkpoint.current_phase)
            else:
                start_phase_idx = 0
            
            phases_to_execute = list(SDLCPhase)[start_phase_idx:]
            
            all_phases_passed = True
            
            for phase in phases_to_execute:
                logger.info(f"\n{'='*80}")
                logger.info(f"📍 PHASE: {phase.value.upper()}")
                logger.info(f"   Iteration: {self.checkpoint.phase_iteration}")
                logger.info(f"{'='*80}\n")
                
                # Execute phase with retry logic
                phase_result = await self.execute_phase_with_retry(
                    phase=phase,
                    iteration=self.checkpoint.phase_iteration,
                    global_iteration=global_iteration
                )
                
                if phase_result.state == PhaseState.COMPLETED:
                    logger.info(f"✅ Phase {phase.value} COMPLETED")
                    
                    # Mark phase as completed
                    if phase not in self.checkpoint.completed_phases:
                        self.checkpoint.completed_phases.append(phase)
                    
                    # Move to next phase
                    next_phase_idx = list(SDLCPhase).index(phase) + 1
                    if next_phase_idx < len(SDLCPhase):
                        self.checkpoint.current_phase = list(SDLCPhase)[next_phase_idx]
                        self.checkpoint.phase_iteration = 1  # Reset for new phase
                    
                    self.save_checkpoint()
                    
                elif phase_result.state == PhaseState.NEEDS_REWORK:
                    logger.warning(f"⚠️  Phase {phase.value} NEEDS_REWORK")
                    all_phases_passed = False
                    
                    # Stay on this phase, increment iteration
                    self.checkpoint.phase_iteration += 1
                    self.save_checkpoint()
                    break  # Exit phase loop to start next global iteration
                    
                elif phase_result.state == PhaseState.FAILED:
                    logger.error(f"❌ Phase {phase.value} FAILED")
                    return self._build_failure_result(phase, phase_result)
            
            # Check if all phases completed successfully
            if all_phases_passed and len(self.checkpoint.completed_phases) == len(SDLCPhase):
                logger.info("\n" + "="*80)
                logger.info("✅ ✅ ✅ ALL PHASES COMPLETED SUCCESSFULLY! ✅ ✅ ✅")
                logger.info("="*80)
                return self._build_success_result()
            
            # Continue to next global iteration if we need rework
            if not all_phases_passed:
                logger.info(f"\n🔄 Continuing to global iteration {global_iteration + 1} for rework...")
        
        # Max iterations reached
        logger.warning(f"\n⚠️  Reached max global iterations ({self.max_global_iterations})")
        return self._build_timeout_result()
    
    async def execute_phase_with_retry(
        self,
        phase: SDLCPhase,
        iteration: int,
        global_iteration: int
    ) -> PhaseExecution:
        """
        Execute a single phase with retry logic
        
        Workflow:
        1. Run entry gate (check dependencies)
        2. Select personas to execute
        3. Execute personas
        4. Run exit gate (validate outputs)
        5. If failed: identify issues and retry up to max_phase_iterations
        
        Returns:
            PhaseExecution with final state
        """
        phase_exec = PhaseExecution(
            phase=phase,
            state=PhaseState.NOT_STARTED,
            iteration=iteration,
            started_at=datetime.now()
        )
        
        for retry in range(1, self.max_phase_iterations + 1):
            logger.info(f"\n{'─'*80}")
            logger.info(f"🔄 Phase {phase.value} - Attempt {retry}/{self.max_phase_iterations}")
            logger.info(f"{'─'*80}\n")
            
            # Step 1: Entry Gate
            entry_result = await self.run_entry_gate(phase, iteration, global_iteration)
            phase_exec.entry_gate_result = entry_result
            
            if not entry_result.passed:
                logger.error(f"❌ Entry gate FAILED for {phase.value}")
                logger.error(f"   Issues: {entry_result.blocking_issues}")
                phase_exec.state = PhaseState.BLOCKED
                phase_exec.completed_at = datetime.now()
                return phase_exec
            
            logger.info(f"✅ Entry gate PASSED (score: {entry_result.score:.2f})")
            
            # Step 2: Select personas
            personas_to_execute = self.select_personas_for_phase(
                phase, iteration, retry, entry_result
            )
            
            logger.info(f"👥 Personas to execute: {', '.join(personas_to_execute)}")
            
            # Step 3: Execute personas
            phase_exec.state = PhaseState.IN_PROGRESS
            persona_results = await self.execute_personas(
                personas_to_execute,
                phase,
                iteration,
                global_iteration
            )
            
            phase_exec.personas_executed.extend(persona_results["executed"])
            phase_exec.personas_reused.extend(persona_results["reused"])
            
            # Step 4: Exit Gate
            exit_result = await self.run_exit_gate(phase, iteration, global_iteration, phase_exec)
            phase_exec.exit_gate_result = exit_result
            phase_exec.quality_score = exit_result.score
            
            if exit_result.passed:
                logger.info(f"✅ Exit gate PASSED (score: {exit_result.score:.2f})")
                phase_exec.state = PhaseState.COMPLETED
                phase_exec.completed_at = datetime.now()
                
                # Update best quality score
                phase_key = phase.value
                if phase_key not in self.best_quality_scores or exit_result.score > self.best_quality_scores[phase_key]:
                    self.best_quality_scores[phase_key] = exit_result.score
                    logger.info(f"🏆 New best quality score for {phase.value}: {exit_result.score:.2f}")
                
                # NEW: Run phase_reviewer to create phase validation report
                logger.info(f"\n📋 Running phase_reviewer for {phase.value}...")
                try:
                    await self.execute_personas(
                        personas=["phase_reviewer"],
                        phase=phase,
                        iteration=iteration,
                        global_iteration=global_iteration
                    )
                    logger.info(f"✅ Phase review completed for {phase.value}")
                except Exception as e:
                    logger.warning(f"⚠️  Phase review failed (non-blocking): {e}")
                
                # Clear failed personas for this phase (if any)
                if self.checkpoint and phase_key in self.checkpoint.failed_personas:
                    del self.checkpoint.failed_personas[phase_key]
                
                return phase_exec
            
            # Exit gate failed
            logger.warning(f"⚠️  Exit gate FAILED (score: {exit_result.score:.2f}, required: {exit_result.required_threshold:.2f})")
            logger.warning(f"   Failed criteria: {exit_result.criteria_failed}")
            
            # Extract issues for rework
            phase_exec.issues = self._extract_issues_from_gate_result(exit_result)
            
            # Identify failed personas for smarter retry
            failed_personas = self._identify_failed_personas(exit_result, phase)
            if self.checkpoint:
                self.checkpoint.failed_personas[phase.value] = failed_personas
                logger.info(f"   Tracking failed personas for retry: {', '.join(failed_personas)}")
            
            if retry < self.max_phase_iterations:
                logger.info(f"\n🔄 Preparing rework iteration {retry + 1}...")
                # Continue to next retry
            else:
                logger.error(f"❌ Max iterations reached for phase {phase.value}")
                phase_exec.state = PhaseState.FAILED
                phase_exec.completed_at = datetime.now()
                return phase_exec
        
        # Should not reach here
        phase_exec.state = PhaseState.NEEDS_REWORK
        phase_exec.completed_at = datetime.now()
        return phase_exec
    
    # ========================================================================
    # GATE VALIDATION
    # ========================================================================
    
    async def run_entry_gate(
        self,
        phase: SDLCPhase,
        iteration: int,
        global_iteration: int
    ) -> PhaseGateResult:
        """
        Validate phase entry criteria
        
        Checks:
        - Previous phase dependencies met
        - Required artifacts exist
        - Quality threshold from previous phase
        """
        logger.info(f"🚪 Running entry gate for {phase.value}...")
        
        result = await self.gate_validator.validate_entry_gate(
            phase=phase,
            project_dir=self.output_dir,
            previous_phases=self.checkpoint.completed_phases if self.checkpoint else []
        )
        
        return result
    
    async def run_exit_gate(
        self,
        phase: SDLCPhase,
        iteration: int,
        global_iteration: int,
        phase_exec: PhaseExecution
    ) -> PhaseGateResult:
        """
        Validate phase exit criteria
        
        Checks:
        - All deliverables created
        - Quality score meets threshold (progressive)
        - No critical issues
        """
        logger.info(f"🚪 Running exit gate for {phase.value}...")
        
        # Get progressive quality threshold
        if self.quality_manager:
            thresholds = self.quality_manager.get_thresholds_for_iteration(
                phase=phase,
                iteration=iteration
            )
            required_quality = thresholds.quality
            required_completeness = thresholds.completeness
        else:
            required_quality = 0.70
            required_completeness = 0.80
        
        # Get best previous score for this phase (must improve)
        phase_key = phase.value
        best_previous_score = self.best_quality_scores.get(phase_key, 0.0)
        
        # On iteration > 1, require improvement
        if iteration > 1:
            required_quality = max(required_quality, best_previous_score + MIN_QUALITY_IMPROVEMENT)
            logger.info(
                f"   📈 Progressive quality: Iteration {iteration} requires ≥{required_quality:.2f} "
                f"(previous best: {best_previous_score:.2f})"
            )
        
        result = await self.gate_validator.validate_exit_criteria(
            phase=phase,
            phase_exec=phase_exec,
            quality_thresholds=QualityThresholds(
                completeness=required_completeness,
                quality=required_quality
            ),
            output_dir=self.output_dir
        )
        
        return result
    
    # ========================================================================
    # PERSONA EXECUTION
    # ========================================================================
    
    def select_personas_for_phase(
        self,
        phase: SDLCPhase,
        iteration: int,
        retry: int,
        entry_result: PhaseGateResult
    ) -> List[str]:
        """
        Select personas to execute for this phase
        
        Logic:
        - Iteration 1, Retry 1: Required personas only
        - Iteration 1, Retry > 1: Required + failed personas from previous retry
        - Iteration > 1: Required + optional personas
        """
        mapping = next((m for m in self.phase_mappings if m.phase == phase), None)
        if not mapping:
            logger.warning(f"No persona mapping found for {phase}, using defaults")
            return []
        
        personas = set(mapping.required_personas)
        
        # Add optional personas on iteration > 1
        if iteration > 1:
            personas.update(mapping.optional_personas)
        
        # Add rework personas and failed personas on retry > 1
        if retry > 1:
            personas.update(mapping.rework_personas)
            
            # Add failed personas from previous retry
            phase_key = phase.value
            if self.checkpoint and phase_key in self.checkpoint.failed_personas:
                failed = self.checkpoint.failed_personas[phase_key]
                logger.info(f"   Adding failed personas from previous retry: {', '.join(failed)}")
                personas.update(failed)
        
        return list(personas)
    
    async def execute_personas(
        self,
        personas: List[str],
        phase: SDLCPhase,
        iteration: int,
        global_iteration: int
    ) -> Dict[str, Any]:
        """
        Execute selected personas using AutonomousSDLCEngineV3_1_Resumable
        
        Returns:
            {
                "executed": List[str],  # Personas that ran
                "reused": List[str],    # Personas that were reused
                "success": bool
            }
        """
        logger.info(f"🤖 Executing {len(personas)} personas for {phase.value}...")
        
        try:
            # Import the working execution engine
            from team_execution import AutonomousSDLCEngineV3_1_Resumable
            
            # Create engine instance for this remediation
            engine = AutonomousSDLCEngineV3_1_Resumable(
                selected_personas=personas,
                output_dir=str(self.output_dir),
                session_manager=self.session_manager,
                enable_persona_reuse=True,  # Enable reuse for cost savings
                force_rerun=True  # Force re-execution even if already done
            )
            
            # Set phase and iteration context for progressive quality
            engine.current_phase = phase
            engine.current_iteration = iteration
            
            # Execute the personas
            logger.info(f"   Personas to execute: {', '.join(personas)}")
            
            # Check if session exists by attempting to load it
            existing_session = self.session_manager.load_session(self.session_id)
            
            if existing_session:
                logger.info(f"   Resuming existing session: {self.session_id}")
                result = await engine.execute(
                    requirement=self.requirement,
                    resume_session_id=self.session_id
                )
            else:
                logger.info(f"   Creating new session: {self.session_id}")
                # Create new session with requirement
                result = await engine.execute(
                    requirement=self.requirement,
                    session_id=self.session_id
                )
            
            # Extract execution results
            executed_personas = []
            reused_personas = []

            if result and "reuse_stats" in result:
                reuse_stats = result["reuse_stats"]
                executed_personas = [p for p in personas if p not in reused_personas]

                logger.info(f"   ✅ Executed: {reuse_stats.get('personas_executed', len(personas))} personas")
                logger.info(f"   ⚡ Reused: {reuse_stats.get('personas_reused', 0)} personas")
            else:
                executed_personas = personas

            # NEW: Capture deployment validation results
            deployment_ready = result.get("deployment_ready", False) if result else False
            deployment_validation = result.get("deployment_validation") if result else None

            if deployment_validation:
                logger.info(f"\n   🚀 Deployment Validation:")
                logger.info(f"      Status: {'✅ READY' if deployment_ready else '❌ NOT READY'}")
                logger.info(f"      Checks Passed: {len(deployment_validation.get('checks', []))}")
                logger.info(f"      Errors: {len(deployment_validation.get('errors', []))}")
                logger.info(f"      Warnings: {len(deployment_validation.get('warnings', []))}")

            return {
                "executed": executed_personas,
                "reused": reused_personas,
                "success": True,
                # NEW: Include deployment validation in return
                "deployment_ready": deployment_ready,
                "deployment_validation": deployment_validation
            }
            
        except Exception as e:
            logger.error(f"❌ Persona execution failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            return {
                "executed": [],
                "reused": [],
                "success": False,
                "error": str(e)
            }
    
    # ========================================================================
    # VALIDATION & REMEDIATION
    # ========================================================================
    
    async def validate_and_remediate(self, project_dir: Path) -> Dict[str, Any]:
        """
        Validate existing project and trigger remediation if needed
        
        Usage for sunday_com:
            executor.validate_and_remediate(Path("sunday_com/sunday_com"))
        
        Returns:
            Remediation results
        """
        logger.info("="*80)
        logger.info("🔍 VALIDATION & REMEDIATION")
        logger.info("="*80)
        logger.info(f"📁 Project: {project_dir}")
        logger.info("="*80)
        
        # Validate path first
        try:
            self._validate_project_path(project_dir)
        except (ValueError, PermissionError) as e:
            logger.error(f"❌ Invalid project path: {e}")
            return {
                "status": "error",
                "error": str(e),
                "remediation_needed": False
            }
        
        # Try to detect requirement from project
        if not self.requirement or self.requirement == "Validation and remediation":
            # Try to load requirement from project
            requirement_file = project_dir / "REQUIREMENTS.md"
            readme_file = project_dir / "README.md"
            
            if requirement_file.exists():
                with open(requirement_file) as f:
                    self.requirement = f.read()[:500]  # First 500 chars
                logger.info(f"📝 Loaded requirement from {requirement_file}")
            elif readme_file.exists():
                with open(readme_file) as f:
                    content = f.read()
                    # Extract first paragraph or first 500 chars
                    self.requirement = content[:500]
                logger.info(f"📝 Loaded requirement from {readme_file}")
            else:
                self.requirement = f"Validate and remediate project: {project_dir.name}"
                logger.info(f"📝 Using generated requirement")
        
        # Step 1: Run comprehensive validation
        validation_results = await self._run_comprehensive_validation(project_dir)
        
        logger.info(f"\n📊 Validation Results:")
        logger.info(f"   Overall Score: {validation_results['overall_score']:.2f}")
        logger.info(f"   Issues Found: {len(validation_results['issues'])}")
        logger.info(f"   Critical Issues: {validation_results['critical_issues']}")
        
        # Step 2: Check if remediation needed
        if validation_results['overall_score'] < REMEDIATION_THRESHOLD:
            logger.warning(f"\n⚠️  Project quality below threshold ({REMEDIATION_THRESHOLD:.0%}). Starting remediation...")
            
            # Identify phases and personas to remediate
            remediation_plan = self._build_remediation_plan(validation_results)
            
            logger.info(f"\n📋 Remediation Plan:")
            for phase, personas in remediation_plan.items():
                logger.info(f"   {phase}: {', '.join(personas)}")
            
            # Execute remediation
            remediation_results = await self._execute_remediation(
                project_dir,
                remediation_plan,
                validation_results
            )
            
            return remediation_results
        else:
            logger.info("\n✅ Project quality acceptable. No remediation needed.")
            return {
                "status": "success",
                "remediation_needed": False,
                "validation_results": validation_results
            }
    
    async def _run_comprehensive_validation(self, project_dir: Path) -> Dict[str, Any]:
        """Run comprehensive validation across all phases"""
        validation_results = {
            "overall_score": 0.0,
            "phase_scores": {},
            "issues": [],
            "critical_issues": 0,
            "warnings": []
        }
        
        # Detect project type
        project_context = detect_project_type(project_dir)
        
        # Validate each phase
        total_score = 0.0
        phase_count = 0
        
        for phase in SDLCPhase:
            phase_validation = await self._validate_phase_artifacts(
                phase, project_dir, project_context
            )
            
            validation_results["phase_scores"][phase.value] = phase_validation["score"]
            validation_results["issues"].extend(phase_validation["issues"])
            validation_results["critical_issues"] += phase_validation["critical_count"]
            
            total_score += phase_validation["score"]
            phase_count += 1
        
        validation_results["overall_score"] = total_score / max(phase_count, 1)
        
        return validation_results
    
    async def _validate_phase_artifacts(
        self,
        phase: SDLCPhase,
        project_dir: Path,
        project_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate artifacts for a specific phase
        
        Uses REAL validation data from persona validation reports if available,
        otherwise calculates from project structure.
        
        Handles nested project directories (e.g., project/project/)
        """
        
        completeness_score = 0.0
        quality_score = 0.0
        
        # Handle nested project directories - check if project has nested folder with same name
        actual_project_dir = project_dir
        nested_dir = project_dir / project_dir.name
        if nested_dir.exists() and nested_dir.is_dir():
            # Check which one has more content by comparing DIRECT children only (not recursive)
            # This avoids double-counting when outer includes nested
            outer_direct_files = len(list(project_dir.glob("*.py"))) + len(list(project_dir.glob("*.js"))) + \
                                len(list(project_dir.glob("*.md"))) + len(list(project_dir.glob("*.json")))
            inner_direct_files = len(list(nested_dir.glob("*.py"))) + len(list(nested_dir.glob("*.js"))) + \
                                len(list(nested_dir.glob("*.md"))) + len(list(nested_dir.glob("*.json")))
            
            # Also check for presence of typical project structure indicators in nested dir
            has_src = (nested_dir / "src").exists() or (nested_dir / "backend").exists() or (nested_dir / "frontend").exists()
            has_package = (nested_dir / "package.json").exists() or (nested_dir / "pyproject.toml").exists() or \
                         (nested_dir / "requirements.txt").exists() or (nested_dir / "pom.xml").exists()
            
            # Use nested if it has more direct files OR has project structure indicators
            if inner_direct_files > outer_direct_files or (has_src and has_package):
                logger.info(f"Detected nested project structure, using inner directory: {nested_dir}")
                actual_project_dir = nested_dir
        
        # FIRST: Try to load REAL validation data from validation reports
        # Check both outer and actual project directory
        validation_dirs = [
            project_dir / "validation_reports",
            actual_project_dir / "validation_reports"
        ]
        
        for validation_dir in validation_dirs:
            if validation_dir.exists():
                validation_files = list(validation_dir.glob("*_validation.json"))
                
                if validation_files:
                    logger.debug(f"Found {len(validation_files)} validation reports in {validation_dir}")
                    
                    # Aggregate quality scores from all validation reports
                    all_completeness = []
                    all_quality = []
                    
                    for val_file in validation_files:
                        try:
                            with open(val_file) as f:
                                val_data = json.load(f)
                                
                            quality_gate = val_data.get('quality_gate', {})
                            if quality_gate:
                                comp = quality_gate.get('completeness_percentage', 0) / 100.0
                                qual = quality_gate.get('quality_score', 0)
                                
                                all_completeness.append(comp)
                                all_quality.append(qual)
                                
                                logger.debug(f"  {val_file.name}: comp={comp:.2f}, qual={qual:.2f}")
                        except Exception as e:
                            logger.debug(f"  Could not read {val_file.name}: {e}")
                    
                    # Use average of all validation reports
                    if all_completeness:
                        completeness_score = sum(all_completeness) / len(all_completeness)
                    if all_quality:
                        quality_score = sum(all_quality) / len(all_quality)
                        
                    if completeness_score > 0 or quality_score > 0:
                        logger.info(f"Phase {phase.value}: Using REAL validation data from {validation_dir.name} - comp={completeness_score:.2f}, qual={quality_score:.2f}")
                        break  # Found valid data, stop searching
        
        # FALLBACK: Calculate from file structure if no validation reports
        if completeness_score == 0.0 and quality_score == 0.0:
            logger.debug(f"No validation reports found, calculating from project structure at {actual_project_dir}")
            
            try:
                # Get all relevant files from actual project directory
                code_files = list(actual_project_dir.glob("**/*.py")) + list(actual_project_dir.glob("**/*.js")) + \
                            list(actual_project_dir.glob("**/*.ts")) + list(actual_project_dir.glob("**/*.java"))
                
                # Filter out node_modules, venv, etc
                code_files = [f for f in code_files if not any(
                    exclude in str(f) for exclude in ['node_modules', 'venv', '.venv', '__pycache__', 'dist', 'build']
                )]
                
                doc_files = list(actual_project_dir.glob("**/*.md"))
                test_files = [f for f in code_files if 'test' in f.name.lower() or 'spec' in f.name.lower()]
                
                # Calculate base completeness from file existence
                if len(code_files) > 0:
                    completeness_score = 0.2  # Has some code
                    
                    if len(code_files) > 5:
                        completeness_score = 0.3  # Has multiple files
                        
                    if len(code_files) > 10:
                        completeness_score = 0.4  # Substantial codebase
                        
                    if len(doc_files) > 2:
                        completeness_score += 0.1  # Has documentation
                        
                    if len(test_files) > 0:
                        completeness_score += 0.1  # Has tests
                
                # Analyze quality from actual file content
                quality_scores = []
                sample_files = code_files[:min(10, len(code_files))]  # Sample up to 10 files
                
                for file_path in sample_files:
                    try:
                        file_quality = analyze_implementation_quality(file_path)
                        quality_scores.append(file_quality.get('quality_score', 0.0))
                    except Exception:
                        pass
                
                if quality_scores:
                    quality_score = sum(quality_scores) / len(quality_scores)
                elif len(code_files) > 0:
                    # Has code but couldn't analyze - assume minimal quality
                    quality_score = 0.1
                    
                # Boost scores based on phase-specific artifacts
                phase_boost = self._calculate_phase_artifact_boost(phase, actual_project_dir, project_context)
                completeness_score = min(completeness_score + phase_boost, 1.0)
                
                logger.debug(f"Phase {phase.value}: Calculated from structure - {len(code_files)} code files, {len(doc_files)} docs, {len(test_files)} tests")
                
            except Exception as e:
                logger.warning(f"Could not analyze project quality: {e}")
                # Fallback: check if directory has content at all
                if any(actual_project_dir.iterdir()):
                    completeness_score = 0.1
                    quality_score = 0.1
        
        # Create a phase execution with calculated scores
        mock_phase_exec = PhaseExecution(
            phase=phase,
            iteration=1,
            state=PhaseState.IN_PROGRESS,
            started_at=datetime.now(),
            personas_executed=[]
        )
        
        # Set quality scores (now from REAL validation data when available)
        mock_phase_exec.completeness = completeness_score
        mock_phase_exec.quality_score = quality_score
        
        logger.debug(f"Phase {phase.value} FINAL: completeness={completeness_score:.2f}, quality={quality_score:.2f}")
        
        # Use phase gate validator
        result = await self.gate_validator.validate_exit_criteria(
            phase=phase,
            phase_exec=mock_phase_exec,
            quality_thresholds=QualityThresholds(
                completeness=0.80,
                quality=0.70
            ),
            output_dir=actual_project_dir  # Use actual project directory
        )
        
        return {
            "score": result.score,
            "issues": result.criteria_failed,
            "critical_count": len(result.blocking_issues)
        }
    
    def _calculate_phase_artifact_boost(
        self,
        phase: SDLCPhase,
        project_dir: Path,
        project_context: Dict[str, Any]
    ) -> float:
        """Calculate boost to completeness based on phase-specific artifacts"""
        boost = 0.0
        
        if phase == SDLCPhase.REQUIREMENTS:
            # Check for requirements documentation
            if (project_dir / "REQUIREMENTS.md").exists():
                boost += 0.2
            if (project_dir / "README.md").exists():
                boost += 0.1
                
        elif phase == SDLCPhase.DESIGN:
            # Check for design documentation
            if (project_dir / "ARCHITECTURE.md").exists() or (project_dir / "architecture.md").exists():
                boost += 0.2
            if (project_dir / "API.md").exists() or (project_dir / "api").exists():
                boost += 0.1
                
        elif phase == SDLCPhase.IMPLEMENTATION:
            # Check for code files
            code_files = list(project_dir.glob("**/*.py")) + list(project_dir.glob("**/*.js"))
            if len(code_files) > 5:
                boost += 0.2
            elif len(code_files) > 0:
                boost += 0.1
                
        elif phase == SDLCPhase.TESTING:
            # Check for test files
            test_files = list(project_dir.glob("**/test_*.py")) + list(project_dir.glob("**/*_test.py"))
            test_files += list(project_dir.glob("**/*.test.js")) + list(project_dir.glob("**/tests/**/*.py"))
            if len(test_files) > 3:
                boost += 0.2
            elif len(test_files) > 0:
                boost += 0.1
                
        elif phase == SDLCPhase.DEPLOYMENT:
            # Check for deployment files
            if (project_dir / "Dockerfile").exists() or (project_dir / "docker-compose.yml").exists():
                boost += 0.1
            if (project_dir / "deployment").exists() or (project_dir / ".github").exists():
                boost += 0.1
        
        return boost
    
    def _build_remediation_plan(
        self,
        validation_results: Dict[str, Any]
    ) -> Dict[str, List[str]]:
        """
        Build remediation plan based on validation issues
        
        Uses enhanced heuristics to map issues to phases and personas.
        Logs unclassified issues for visibility.
        """
        remediation_plan = {}
        unclassified_issues = []
        
        # Define classification rules
        classification_rules = [
            # (keywords, phase, personas)
            (['requirement', 'story', 'specification', 'user need'], 
             SDLCPhase.REQUIREMENTS, ['requirement_analyst']),
            
            (['design', 'architecture', 'system design', 'component'], 
             SDLCPhase.DESIGN, ['solution_architect']),
            
            (['database', 'schema', 'table', 'query', 'migration'], 
             SDLCPhase.DESIGN, ['database_specialist']),
            
            (['security', 'authentication', 'authorization', 'encryption'], 
             SDLCPhase.DESIGN, ['security_specialist']),
            
            (['backend', 'api', 'server', 'endpoint', 'service'], 
             SDLCPhase.IMPLEMENTATION, ['backend_developer']),
            
            (['frontend', 'ui', 'interface', 'component', 'view'], 
             SDLCPhase.IMPLEMENTATION, ['frontend_developer']),
            
            (['test', 'qa', 'quality', 'coverage', 'validation'], 
             SDLCPhase.TESTING, ['qa_engineer']),
            
            (['unit test', 'unit testing'], 
             SDLCPhase.TESTING, ['unit_tester']),
            
            (['integration test', 'integration testing'], 
             SDLCPhase.TESTING, ['integration_tester']),
            
            (['deploy', 'deployment', 'infrastructure', 'devops'], 
             SDLCPhase.DEPLOYMENT, ['devops_engineer']),
            
            (['smoke test', 'deployment validation'], 
             SDLCPhase.DEPLOYMENT, ['deployment_integration_tester']),
        ]
        
        # Analyze issues by phase
        for issue in validation_results["issues"]:
            issue_lower = issue.lower()
            classified = False
            
            # Try each classification rule
            for keywords, phase, personas in classification_rules:
                if any(keyword in issue_lower for keyword in keywords):
                    phase_key = phase.value
                    if phase_key not in remediation_plan:
                        remediation_plan[phase_key] = set()
                    remediation_plan[phase_key].update(personas)
                    classified = True
                    break
            
            if not classified:
                unclassified_issues.append(issue)
        
        # Log unclassified issues
        if unclassified_issues:
            logger.warning(f"\n⚠️  {len(unclassified_issues)} issues could not be classified:")
            for issue in unclassified_issues[:5]:  # Show first 5
                logger.warning(f"   - {issue}")
            if len(unclassified_issues) > 5:
                logger.warning(f"   ... and {len(unclassified_issues) - 5} more")
        
        # Convert sets to lists
        return {k: list(v) for k, v in remediation_plan.items()}
    
    async def _execute_remediation(
        self,
        project_dir: Path,
        remediation_plan: Dict[str, List[str]],
        validation_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute remediation by re-running failed personas in correct phase order
        
        Retries up to max_phase_iterations times if validation still fails
        """
        logger.info("\n🔧 Starting remediation...")
        
        # Set output directory to the project being remediated
        self.output_dir = project_dir
        
        # Use canonical phase order from TeamOrganization (single source of truth)
        phase_order = TeamOrganization.get_phase_order()
        
        logger.debug(f"Executing remediation in phase order: {[p.value for p in phase_order]}")
        
        initial_score = validation_results['overall_score']
        best_score = initial_score
        final_validation = validation_results
        
        # Retry remediation up to max_phase_iterations times
        for remediation_iteration in range(1, self.max_phase_iterations + 1):
            logger.info(f"\n{'='*80}")
            logger.info(f"🔧 REMEDIATION ITERATION {remediation_iteration}/{self.max_phase_iterations}")
            logger.info(f"{'='*80}\n")
            
            # Execute each phase's remediation IN ORDER
            for phase in phase_order:
                phase_key = phase.value
                if phase_key in remediation_plan:
                    personas = remediation_plan[phase_key]
                    
                    logger.info(f"\n🔧 Remediating {phase.value}: {', '.join(personas)}")
                    
                    await self.execute_personas(
                        personas=personas,
                        phase=phase,
                        iteration=remediation_iteration,
                        global_iteration=remediation_iteration
                    )
            
            # Re-validate after this remediation iteration
            logger.info(f"\n🔍 Re-validating after remediation iteration {remediation_iteration}...")
            final_validation = await self._run_comprehensive_validation(project_dir)
            
            current_score = final_validation['overall_score']
            improvement = current_score - initial_score
            iteration_improvement = current_score - best_score
            
            logger.info(f"\n📊 Validation Results (Iteration {remediation_iteration}):")
            logger.info(f"   Initial Score: {initial_score:.2f}")
            logger.info(f"   Current Score: {current_score:.2f} (best: {best_score:.2f})")
            logger.info(f"   Total Improvement: {improvement:+.2f} ({improvement:.1%})")
            logger.info(f"   Iteration Improvement: {iteration_improvement:+.2f}")
            
            # Update best score
            if current_score > best_score:
                best_score = current_score
                logger.info(f"   🏆 New best score!")
            
            # Check if we've passed the threshold
            if current_score >= VALIDATION_PASS_THRESHOLD:
                logger.info(f"\n✅ Remediation successful! Score {current_score:.2f} meets threshold {VALIDATION_PASS_THRESHOLD:.2f}")
                return {
                    "status": "success",
                    "remediation_executed": True,
                    "iterations_used": remediation_iteration,
                    "initial_score": initial_score,
                    "final_score": current_score,
                    "improvement": improvement,
                    "phases_remediated": list(remediation_plan.keys()),
                    "final_validation": final_validation
                }
            
            # Check if we made sufficient improvement to continue
            if remediation_iteration > 1 and iteration_improvement < MIN_QUALITY_IMPROVEMENT:
                logger.warning(f"\n⚠️  Insufficient improvement in iteration {remediation_iteration} ({iteration_improvement:+.2f})")
                if remediation_iteration < self.max_phase_iterations:
                    logger.info(f"   Continuing to next remediation iteration...")
            
            # If this is not the last iteration, continue
            if remediation_iteration < self.max_phase_iterations:
                logger.info(f"\n🔄 Score {current_score:.2f} still below threshold {VALIDATION_PASS_THRESHOLD:.2f}")
                logger.info(f"   Proceeding to remediation iteration {remediation_iteration + 1}...")
        
        # Max iterations reached without passing threshold
        final_score = final_validation['overall_score']
        improvement = final_score - initial_score
        
        logger.warning(f"\n⚠️  Remediation completed {self.max_phase_iterations} iterations")
        logger.warning(f"   Final score {final_score:.2f} still below threshold {VALIDATION_PASS_THRESHOLD:.2f}")
        
        if improvement > 0:
            logger.info(f"   However, quality improved by {improvement:+.2f} ({improvement:.1%})")
            status = "partial_success"
        else:
            logger.warning(f"   Quality did not improve (change: {improvement:+.2f})")
            status = "failed"
        
        return {
            "status": status,
            "remediation_executed": True,
            "iterations_used": self.max_phase_iterations,
            "initial_score": initial_score,
            "final_score": final_score,
            "improvement": improvement,
            "phases_remediated": list(remediation_plan.keys()),
            "final_validation": final_validation,
            "message": f"Completed {self.max_phase_iterations} remediation iterations, score: {final_score:.2f}"
        }
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _validate_project_path(self, path: Path) -> None:
        """
        Validate project path is safe and accessible
        
        Args:
            path: Path to validate
            
        Raises:
            ValueError: If path is invalid
            PermissionError: If path is not accessible
        """
        # Check existence
        if not path.exists():
            raise ValueError(f"Path does not exist: {path}")
        
        # Check it's a directory
        if not path.is_dir():
            raise ValueError(f"Path is not a directory: {path}")
        
        # Check read permission
        if not os.access(path, os.R_OK):
            raise PermissionError(f"Path is not readable: {path}")
        
        # Check write permission (needed for remediation)
        if not os.access(path, os.W_OK):
            raise PermissionError(f"Path is not writable: {path}")
        
        # Resolve to absolute path to prevent traversal
        resolved = path.resolve()
        logger.debug(f"Validated project path: {resolved}")
    
    def _identify_failed_personas(self, exit_result: PhaseGateResult, phase: SDLCPhase) -> List[str]:
        """
        Identify which personas likely failed based on exit gate results
        
        Uses heuristics to map failed criteria to personas:
        - Requirements failures -> requirement_analyst
        - Architecture/design failures -> solution_architect
        - Backend/API failures -> backend_developer
        - Frontend/UI failures -> frontend_developer
        - Test failures -> qa_engineer, unit_tester
        - Deployment failures -> devops_engineer
        
        Args:
            exit_result: Exit gate validation result
            phase: Current phase
            
        Returns:
            List of persona names that likely caused failures
        """
        failed_personas = set()
        
        # Get mapping for this phase
        mapping = next((m for m in self.phase_mappings if m.phase == phase), None)
        if not mapping:
            return []
        
        # Analyze failed criteria and blocking issues
        all_issues = exit_result.criteria_failed + exit_result.blocking_issues
        
        for issue in all_issues:
            issue_lower = issue.lower()
            
            # Requirements phase
            if phase == SDLCPhase.REQUIREMENTS:
                if any(term in issue_lower for term in ['requirement', 'story', 'specification']):
                    failed_personas.add('requirement_analyst')
            
            # Design phase
            elif phase == SDLCPhase.DESIGN:
                if any(term in issue_lower for term in ['architecture', 'design', 'system']):
                    failed_personas.add('solution_architect')
                elif any(term in issue_lower for term in ['database', 'schema', 'table']):
                    failed_personas.add('database_specialist')
                elif any(term in issue_lower for term in ['security', 'authentication', 'authorization']):
                    failed_personas.add('security_specialist')
            
            # Implementation phase
            elif phase == SDLCPhase.IMPLEMENTATION:
                if any(term in issue_lower for term in ['backend', 'api', 'server', 'endpoint']):
                    failed_personas.add('backend_developer')
                elif any(term in issue_lower for term in ['frontend', 'ui', 'interface', 'component']):
                    failed_personas.add('frontend_developer')
                elif any(term in issue_lower for term in ['database', 'query', 'migration']):
                    failed_personas.add('database_specialist')
            
            # Testing phase
            elif phase == SDLCPhase.TESTING:
                if any(term in issue_lower for term in ['test', 'coverage', 'quality']):
                    failed_personas.add('qa_engineer')
                    if 'unit' in issue_lower:
                        failed_personas.add('unit_tester')
                    elif 'integration' in issue_lower:
                        failed_personas.add('integration_tester')
            
            # Deployment phase
            elif phase == SDLCPhase.DEPLOYMENT:
                if any(term in issue_lower for term in ['deploy', 'infrastructure', 'configuration']):
                    failed_personas.add('devops_engineer')
                elif any(term in issue_lower for term in ['integration', 'smoke', 'validation']):
                    failed_personas.add('deployment_integration_tester')
        
        # If no specific personas identified, return all required personas
        if not failed_personas:
            logger.warning(f"   Could not identify specific failed personas, will re-run all required personas")
            return mapping.required_personas
        
        # Filter to only include personas that were executed in this phase
        result = [p for p in failed_personas if p in mapping.required_personas + mapping.optional_personas]
        
        logger.info(f"   Identified failed personas: {', '.join(result)}")
        return result
    
    def _extract_issues_from_gate_result(self, gate_result: PhaseGateResult) -> List[PhaseIssue]:
        """Convert gate result to phase issues"""
        issues = []
        
        for issue_desc in gate_result.blocking_issues:
            issues.append(PhaseIssue(
                severity="critical",
                category="completeness",
                description=issue_desc,
                recommendation=None
            ))
        
        for criteria in gate_result.criteria_failed:
            issues.append(PhaseIssue(
                severity="high",
                category="quality",
                description=f"Failed criteria: {criteria}",
                recommendation=None
            ))
        
        return issues
    
    def _build_success_result(self) -> Dict[str, Any]:
        """Build success result"""
        return {
            "status": "success",
            "session_id": self.session_id,
            "completed_phases": [p.value for p in self.checkpoint.completed_phases],
            "total_iterations": self.checkpoint.global_iteration,
            "best_quality_scores": self.best_quality_scores,
            "output_dir": str(self.output_dir),
            "checkpoint_file": str(self.checkpoint_file)
        }
    
    def _build_failure_result(self, phase: SDLCPhase, phase_exec: PhaseExecution) -> Dict[str, Any]:
        """Build failure result"""
        return {
            "status": "failed",
            "session_id": self.session_id,
            "failed_phase": phase.value,
            "reason": phase_exec.rework_reason or "Phase execution failed",
            "issues": [asdict(issue) for issue in phase_exec.issues],
            "output_dir": str(self.output_dir)
        }
    
    def _build_timeout_result(self) -> Dict[str, Any]:
        """Build timeout result"""
        return {
            "status": "timeout",
            "session_id": self.session_id,
            "completed_phases": [p.value for p in self.checkpoint.completed_phases],
            "current_phase": self.checkpoint.current_phase.value if self.checkpoint.current_phase else None,
            "iterations_used": self.checkpoint.global_iteration,
            "message": "Reached maximum iterations without full completion",
            "output_dir": str(self.output_dir)
        }


# ============================================================================
# CLI
# ============================================================================

async def main():
    """CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Phased Autonomous SDLC Executor with Progressive Quality",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start fresh execution
  python phased_autonomous_executor.py \\
      --requirement "Create task management system with real-time collaboration" \\
      --session task_mgmt_v1 \\
      --max-phase-iterations 3

  # Resume from checkpoint
  python phased_autonomous_executor.py \\
      --resume task_mgmt_v1

  # Validate and remediate existing project (sunday_com)
  python phased_autonomous_executor.py \\
      --validate sunday_com/sunday_com \\
      --session sunday_remediation \\
      --remediate
        """
    )
    
    parser.add_argument("--requirement", help="Project requirement (for new sessions)")
    parser.add_argument("--session", help="Session ID")
    parser.add_argument("--resume", help="Resume from checkpoint (session ID)")
    parser.add_argument("--validate", help="Validate existing project directory")
    parser.add_argument("--remediate", action="store_true", help="Remediate after validation")
    parser.add_argument("--output", help="Output directory")
    parser.add_argument("--max-phase-iterations", type=int, default=3, help="Max iterations per phase")
    parser.add_argument("--max-global-iterations", type=int, default=10, help="Max global iterations")
    parser.add_argument("--disable-progressive-quality", action="store_true", help="Disable progressive quality thresholds")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(f"phased_autonomous_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        ]
    )
    
    # Validation mode
    if args.validate:
        if not args.session:
            parser.error("--session required for validation")
        
        executor = PhasedAutonomousExecutor(
            session_id=args.session,
            requirement="Validation and remediation",
            output_dir=Path(args.output) if args.output else None,
            max_phase_iterations=args.max_phase_iterations,
            max_global_iterations=args.max_global_iterations,
            enable_progressive_quality=not args.disable_progressive_quality
        )
        
        result = await executor.validate_and_remediate(Path(args.validate))
        
        print("\n" + "="*80)
        print("📊 VALIDATION & REMEDIATION RESULTS")
        print("="*80)
        print(json.dumps(result, indent=2))
        print("="*80)
        
        return
    
    # Resume mode
    if args.resume:
        session_id = args.resume
        requirement = "Resumed session"
    else:
        if not args.requirement or not args.session:
            parser.error("--requirement and --session required for new execution")
        session_id = args.session
        requirement = args.requirement
    
    # Create executor
    executor = PhasedAutonomousExecutor(
        session_id=session_id,
        requirement=requirement,
        output_dir=Path(args.output) if args.output else None,
        max_phase_iterations=args.max_phase_iterations,
        max_global_iterations=args.max_global_iterations,
        enable_progressive_quality=not args.disable_progressive_quality
    )
    
    # Execute
    result = await executor.execute_autonomous()
    
    # Print result
    print("\n" + "="*80)
    print("📊 EXECUTION RESULTS")
    print("="*80)
    print(json.dumps(result, indent=2, default=str))
    print("="*80)
    
    # Exit code
    sys.exit(0 if result["status"] == "success" else 1)


if __name__ == "__main__":
    asyncio.run(main())
