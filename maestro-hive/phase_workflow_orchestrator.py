#!/usr/bin/env python3
"""
Phase Workflow Orchestrator

Orchestrates complete SDLC workflow at the phase level.
Enforces phase boundaries, validates gates, manages progressive quality.

Key Responsibilities:
1. Phase state machine (Requirements → Design → Implementation → Testing → Deployment)
2. Entry/exit gate validation at phase boundaries
3. Progressive quality threshold enforcement
4. Smart persona selection per phase
5. Phase-level retry and rework logic
6. Integration with existing team_execution.py

Usage:
    orchestrator = PhaseWorkflowOrchestrator(
        session_id="ecommerce_v1",
        requirement="Build e-commerce platform",
        output_dir="./output"
    )
    
    result = await orchestrator.execute_workflow(max_iterations=5)
"""

import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from phase_models import (
    SDLCPhase,
    PhaseState,
    PhaseExecution,
    PhaseIssue,
    QualityThresholds,
    WorkflowResult
)
from phase_gate_validator import PhaseGateValidator
from progressive_quality_manager import ProgressiveQualityManager
from team_organization import TeamOrganization
from session_manager import SessionManager, SDLCSession

# Import team_execution for real persona execution
try:
    from team_execution import AutonomousSDLCEngineV3_1_Resumable
    TEAM_EXECUTION_AVAILABLE = True
except ImportError:
    TEAM_EXECUTION_AVAILABLE = False
    logging.warning("⚠️  team_execution not available - will use mock execution")

logger = logging.getLogger(__name__)


class PhaseWorkflowOrchestrator:
    """
    Orchestrates SDLC execution at the phase level
    
    Enforces:
    - Phase boundaries (can't skip phases)
    - Entry gates (prerequisites must be met)
    - Exit gates (quality must meet thresholds)
    - Progressive quality (thresholds increase per iteration)
    
    Benefits:
    - Early failure detection
    - Targeted rework (not full reruns)
    - Quality ratcheting (continuous improvement)
    - Clear workflow visibility
    """
    
    def __init__(
        self,
        session_id: str,
        requirement: str,
        output_dir: Optional[Path] = None,
        enable_phase_gates: bool = True,
        enable_progressive_quality: bool = True,
        maestro_ml_url: str = "http://localhost:8001",
        session_manager: Optional[SessionManager] = None
    ):
        """
        Initialize phase workflow orchestrator
        
        Args:
            session_id: Unique session identifier
            requirement: Project requirement description
            output_dir: Output directory for generated code
            enable_phase_gates: Enable entry/exit gate validation
            enable_progressive_quality: Enable progressive quality thresholds
            maestro_ml_url: URL for ML backend (persona reuse)
            session_manager: Session manager for persistence
        """
        self.session_id = session_id
        self.requirement = requirement
        self.output_dir = output_dir or Path(f"./sdlc_output/{session_id}")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Configuration
        self.enable_phase_gates = enable_phase_gates
        self.enable_progressive_quality = enable_progressive_quality
        self.maestro_ml_url = maestro_ml_url
        
        # Components
        self.phase_gates = PhaseGateValidator()
        self.quality_manager = ProgressiveQualityManager()
        self.session_manager = session_manager or SessionManager()
        self.team_org = TeamOrganization()
        
        # State tracking
        self.current_phase: Optional[SDLCPhase] = None
        self.phase_history: List[PhaseExecution] = []
        self.iteration_count = 0
        self.total_personas_executed = 0
        self.total_personas_reused = 0
        
        # Load or create session
        self.session: Optional[SDLCSession] = None
        self._load_or_create_session()
    
    def _load_or_create_session(self):
        """Load existing session or create new one"""
        existing_session = self.session_manager.load_session(self.session_id)
        
        if existing_session:
            logger.info(f"📂 Resuming session: {self.session_id}")
            self.session = existing_session
            # Restore phase history from session
            self._restore_phase_history()
        else:
            logger.info(f"🆕 Creating new session: {self.session_id}")
            self.session = self.session_manager.create_session(
                requirement=self.requirement,
                output_dir=self.output_dir,
                session_id=self.session_id
            )
    
    def _restore_phase_history(self):
        """Restore phase history from session metadata"""
        if not self.session:
            return
        
        phase_data = self.session.metadata.get("phase_history", [])
        
        if not phase_data:
            logger.debug("No phase history to restore")
            return
        
        try:
            from phase_models import PhaseExecution
            
            for phase_dict in phase_data:
                phase_exec = PhaseExecution.from_dict(phase_dict)
                self.phase_history.append(phase_exec)
            
            logger.info(f"✅ Restored {len(self.phase_history)} phase(s) from session")
            
            # Restore counters
            self.iteration_count = self.session.metadata.get("iteration_count", 0)
            
            # Log restored state
            for phase_exec in self.phase_history:
                logger.info(
                    f"   Phase: {phase_exec.phase.value}, "
                    f"Iteration: {phase_exec.iteration}, "
                    f"State: {phase_exec.state.value}, "
                    f"Quality: {phase_exec.quality_score:.0%}"
                )
        
        except Exception as e:
            logger.error(f"❌ Error restoring phase history: {e}")
            import traceback
            traceback.print_exc()
            # Continue with empty phase history rather than failing
    
    async def execute_workflow(
        self,
        max_iterations: int = 5,
        target_phases: Optional[List[SDLCPhase]] = None
    ) -> WorkflowResult:
        """
        Execute complete SDLC workflow with phase management
        
        Flow:
        1. Start with REQUIREMENTS phase (or resume from last phase)
        2. For each phase:
           a. Validate entry criteria
           b. Select needed personas
           c. Execute personas (via team_execution.py)
           d. Validate exit criteria
           e. Decide: proceed, rework, or fail
        3. Continue until DEPLOYMENT complete or max iterations
        
        Args:
            max_iterations: Maximum iterations allowed
            target_phases: Specific phases to execute (default: all)
        
        Returns:
            WorkflowResult with complete execution details
        """
        
        logger.info("\n" + "="*80)
        logger.info("🚀 PHASE-BASED WORKFLOW ORCHESTRATION")
        logger.info("="*80)
        logger.info(f"Session: {self.session_id}")
        logger.info(f"Requirement: {self.requirement[:100]}...")
        logger.info(f"Max Iterations: {max_iterations}")
        logger.info(f"Phase Gates: {'✅ Enabled' if self.enable_phase_gates else '❌ Disabled'}")
        logger.info(f"Progressive Quality: {'✅ Enabled' if self.enable_progressive_quality else '❌ Disabled'}")
        logger.info("="*80 + "\n")
        
        self.iteration_count = 0
        workflow_start = datetime.now()
        
        # Define phase order
        phase_order = [
            SDLCPhase.REQUIREMENTS,
            SDLCPhase.DESIGN,
            SDLCPhase.IMPLEMENTATION,
            SDLCPhase.TESTING,
            SDLCPhase.DEPLOYMENT
        ]
        
        if target_phases:
            phase_order = [p for p in phase_order if p in target_phases]
        
        try:
            while self.iteration_count < max_iterations:
                self.iteration_count += 1
                
                logger.info(f"\n{'='*80}")
                logger.info(f"🔄 ITERATION {self.iteration_count}/{max_iterations}")
                logger.info(f"{'='*80}\n")
                
                # Determine which phase to execute
                phase = self._determine_next_phase(phase_order)
                
                if phase is None:
                    logger.info("✅ All phases complete!")
                    break
                
                logger.info(f"📍 Executing phase: {phase.value.upper()}")
                
                # Execute phase
                phase_result = await self._execute_phase(phase)
                
                # Record result
                self.phase_history.append(phase_result)
                
                # Update session (will be enhanced when session_manager supports phases)
                self._save_progress()
                
                # Check if phase passed or needs rework
                if phase_result.state == PhaseState.FAILED:
                    logger.error(f"❌ Phase {phase.value} FAILED - Cannot proceed")
                    logger.error(f"   Reason: {phase_result.rework_reason}")
                    break
                
                elif phase_result.state == PhaseState.NEEDS_REWORK:
                    logger.warning(f"⚠️  Phase {phase.value} needs rework")
                    logger.warning(f"   Reason: {phase_result.rework_reason}")
                    # Continue to next iteration for rework
                
                elif phase_result.state == PhaseState.COMPLETED:
                    logger.info(f"✅ Phase {phase.value} COMPLETED")
                    logger.info(f"   Quality: {phase_result.quality_score:.0%}")
                    logger.info(f"   Completeness: {phase_result.completeness:.0%}")
                    # Move to next phase
            
            # Build final result
            workflow_end = datetime.now()
            duration = (workflow_end - workflow_start).total_seconds()
            
            result = self._build_workflow_result(duration)
            
            logger.info("\n" + "="*80)
            logger.info("🎉 WORKFLOW COMPLETE")
            logger.info("="*80)
            logger.info(f"Success: {'✅' if result.success else '❌'}")
            logger.info(f"Total Iterations: {result.total_iterations}")
            logger.info(f"Phases Completed: {len(result.phases_completed)}")
            logger.info(f"Personas Executed: {result.total_personas_executed}")
            logger.info(f"Personas Reused: {result.total_personas_reused}")
            logger.info(f"Final Quality: {result.final_quality_score:.0%}")
            logger.info(f"Final Completeness: {result.final_completeness:.0%}")
            logger.info(f"Duration: {duration:.0f}s")
            logger.info("="*80 + "\n")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Workflow error: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def _determine_next_phase(self, phase_order: List[SDLCPhase]) -> Optional[SDLCPhase]:
        """
        Determine which phase to execute next
        
        Logic:
        1. If a phase failed/needs rework, return that phase
        2. If all phases complete, return None
        3. Otherwise, return first incomplete phase
        """
        
        # Check for phases needing rework
        for phase_exec in reversed(self.phase_history):
            if phase_exec.state == PhaseState.NEEDS_REWORK:
                logger.debug(f"Reworking phase: {phase_exec.phase.value}")
                return phase_exec.phase
        
        # Get completed phases
        completed_phases = set(
            exec.phase for exec in self.phase_history
            if exec.state == PhaseState.COMPLETED
        )
        
        # Find first incomplete phase
        for phase in phase_order:
            if phase not in completed_phases:
                logger.debug(f"Next new phase: {phase.value}")
                return phase
        
        # All phases complete
        return None
    
    async def _execute_phase(
        self,
        phase: SDLCPhase
    ) -> PhaseExecution:
        """
        Execute a single SDLC phase with gates
        
        Steps:
        1. Entry gate validation
        2. Get progressive quality thresholds
        3. Select personas for phase
        4. Execute personas (via team_execution.py)
        5. Exit gate validation
        6. State determination
        """
        
        phase_start = datetime.now()
        iteration = self._get_phase_iteration(phase)
        
        phase_exec = PhaseExecution(
            phase=phase,
            state=PhaseState.IN_PROGRESS,
            iteration=iteration,
            started_at=phase_start,
            personas_executed=[],
            personas_reused=[],
            quality_score=0.0,
            completeness=0.0,
            issues=[]
        )
        
        logger.info(f"\n{'─'*80}")
        logger.info(f"📋 PHASE: {phase.value.upper()} (Iteration {iteration})")
        logger.info(f"{'─'*80}\n")
        
        # STEP 1: Entry Gate Validation
        if self.enable_phase_gates:
            logger.info("🚪 Validating ENTRY gate...")
            entry_gate = await self.phase_gates.validate_entry_criteria(
                phase,
                self.phase_history
            )
            
            phase_exec.entry_gate_result = entry_gate
            
            if not entry_gate.passed:
                logger.error(f"❌ ENTRY gate FAILED")
                for issue in entry_gate.blocking_issues:
                    logger.error(f"   🚫 {issue}")
                
                phase_exec.state = PhaseState.FAILED
                phase_exec.rework_reason = "; ".join(entry_gate.blocking_issues)
                phase_exec.completed_at = datetime.now()
                return phase_exec
            
            logger.info(f"✅ ENTRY gate PASSED ({entry_gate.score:.0%})\n")
        
        # STEP 2: Get Progressive Quality Thresholds
        if self.enable_progressive_quality:
            quality_thresholds = self.quality_manager.get_thresholds_for_iteration(
                phase,
                iteration
            )
        else:
            # Use fixed thresholds
            quality_thresholds = QualityThresholds(
                completeness=0.70,
                quality=0.60,
                test_coverage=0.70
            )
        
        logger.info("")  # Blank line for readability
        
        # STEP 3: Select Personas for Phase
        personas_needed = self._select_personas_for_phase(phase, iteration)
        
        logger.info(f"🤖 Personas selected: {len(personas_needed)}")
        for persona_id in personas_needed:
            logger.info(f"   • {persona_id}")
        logger.info("")
        
        # STEP 4: Execute Personas
        # This is where we would integrate with team_execution.py
        # For now, we'll simulate execution with mock data
        logger.info("⚙️  Executing personas...")
        
        execution_result = await self._execute_personas_for_phase(
            personas_needed,
            phase,
            quality_thresholds
        )
        
        # Update phase execution with results
        phase_exec.personas_executed = execution_result['personas_executed']
        phase_exec.personas_reused = execution_result['personas_reused']
        phase_exec.quality_score = execution_result['quality_score']
        phase_exec.completeness = execution_result['completeness']
        phase_exec.test_coverage = execution_result.get('test_coverage', 0.0)
        
        self.total_personas_executed += len(phase_exec.personas_executed)
        self.total_personas_reused += len(phase_exec.personas_reused)
        
        logger.info(f"✅ Execution complete")
        logger.info(f"   Executed: {len(phase_exec.personas_executed)}")
        logger.info(f"   Reused: {len(phase_exec.personas_reused)}")
        logger.info(f"   Quality: {phase_exec.quality_score:.0%}")
        logger.info(f"   Completeness: {phase_exec.completeness:.0%}\n")
        
        # NEW: Check for quality regression (if iteration > 1)
        if iteration > 1:
            previous_phase_exec = self._get_previous_phase_execution(phase)
            if previous_phase_exec:
                logger.info("🔍 Checking for quality regression...")
                
                current_metrics = {
                    'completeness': phase_exec.completeness,
                    'quality_score': phase_exec.quality_score,
                    'test_coverage': phase_exec.test_coverage
                }
                
                previous_metrics = {
                    'completeness': previous_phase_exec.completeness,
                    'quality_score': previous_phase_exec.quality_score,
                    'test_coverage': previous_phase_exec.test_coverage
                }
                
                regression_check = self.quality_manager.check_quality_regression(
                    phase,
                    current_metrics,
                    previous_metrics,
                    tolerance=0.05
                )
                
                if regression_check['has_regression']:
                    logger.error(f"❌ QUALITY REGRESSION DETECTED!")
                    for regressed_metric in regression_check['regressed_metrics']:
                        logger.error(f"   📉 {regressed_metric}")
                    
                    # Add regression issues to phase execution
                    for regressed_metric in regression_check['regressed_metrics']:
                        phase_exec.issues.append(PhaseIssue(
                            severity="high",
                            category="quality_regression",
                            description=f"Quality regressed: {regressed_metric}",
                            recommendation="Review changes and restore quality"
                        ))
                    
                    # Force phase to NEEDS_REWORK
                    phase_exec.state = PhaseState.NEEDS_REWORK
                    phase_exec.rework_reason = "Quality regression detected: " + ", ".join(
                        regression_check['regressed_metrics']
                    )
                    
                    logger.warning("⚠️  Phase marked for rework due to regression")
                else:
                    logger.info("✅ No quality regression detected")
                    if regression_check['improvements']:
                        for improvement in regression_check['improvements']:
                            logger.info(f"   📈 {improvement}")
        
        # STEP 5: Exit Gate Validation (only if not already marked for rework)
        if self.enable_phase_gates and phase_exec.state != PhaseState.NEEDS_REWORK:
            logger.info("🚪 Validating EXIT gate...")
            exit_gate = await self.phase_gates.validate_exit_criteria(
                phase,
                phase_exec,
                quality_thresholds,
                self.output_dir
            )
            
            phase_exec.exit_gate_result = exit_gate
            
            if not exit_gate.passed:
                if len(exit_gate.blocking_issues) > 0:
                    logger.error(f"❌ EXIT gate FAILED")
                    for issue in exit_gate.blocking_issues:
                        logger.error(f"   🚫 {issue}")
                    
                    if exit_gate.recommendations:
                        logger.info(f"\n💡 Recommendations:")
                        for rec in exit_gate.recommendations:
                            logger.info(f"   • {rec}")
                    
                    phase_exec.state = PhaseState.NEEDS_REWORK
                    phase_exec.rework_reason = "; ".join(exit_gate.blocking_issues)
                else:
                    # Warnings only, allow to proceed
                    logger.warning(f"⚠️  EXIT gate passed with warnings")
                    for warning in exit_gate.warnings:
                        logger.warning(f"   ⚠️  {warning}")
                    phase_exec.state = PhaseState.COMPLETED
            else:
                logger.info(f"✅ EXIT gate PASSED ({exit_gate.score:.0%})")
                phase_exec.state = PhaseState.COMPLETED
        elif phase_exec.state == PhaseState.NEEDS_REWORK:
            # Already marked for rework due to regression, skip exit gate
            logger.info("⏭️  Skipping EXIT gate (already marked for rework)")
        else:
            # No gates, assume complete if not already marked for rework
            if phase_exec.state != PhaseState.NEEDS_REWORK:
                phase_exec.state = PhaseState.COMPLETED
        
        phase_exec.completed_at = datetime.now()
        
        logger.info("")
        logger.info(f"{'─'*80}")
        logger.info(f"📊 Phase {phase.value} result: {phase_exec.state.value.upper()}")
        logger.info(f"{'─'*80}\n")
        
        return phase_exec
    
    def _select_personas_for_phase(
        self,
        phase: SDLCPhase,
        iteration: int
    ) -> List[str]:
        """
        Select personas needed for this phase iteration
        
        Logic (Simple version for Week 2, will enhance in Week 3):
        - Get primary personas from team organization
        - For iteration 1: primary only
        - For iteration 2+: primary + supporting
        """
        
        phase_structure = self.team_org.get_phase_structure()
        phase_info = phase_structure.get(phase, {})
        
        primary = phase_info.get('primary_personas', [])
        supporting = phase_info.get('supporting_personas', [])
        
        if iteration == 1:
            return primary
        else:
            # Add supporting personas for subsequent iterations
            return primary + supporting[:2]  # Limit to 2 support personas
    
    async def _execute_personas_for_phase(
        self,
        personas: List[str],
        phase: SDLCPhase,
        quality_thresholds: QualityThresholds
    ) -> Dict[str, Any]:
        """
        Execute personas for this phase
        
        Integrates with team_execution.py for real persona execution
        """
        
        if not TEAM_EXECUTION_AVAILABLE:
            error_msg = (
                "❌ team_execution.py not available - cannot execute personas. "
                "Install claude_code_sdk and ensure team_execution.py is in path."
            )
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        try:
            # Create execution engine
            engine = AutonomousSDLCEngineV3_1_Resumable(
                selected_personas=personas,
                output_dir=str(self.output_dir),
                session_manager=self.session_manager,
                maestro_ml_url=self.maestro_ml_url,
                enable_persona_reuse=True,
                force_rerun=False
            )
            
            # Execute personas with real Claude SDK
            logger.info(f"🚀 Executing {len(personas)} personas via team_execution.py...")
            
            result = await engine.execute(
                requirement=self.requirement,
                session_id=self.session_id,
                resume_session_id=self.session_id if self.session else None
            )
            
            # Extract metrics from result
            personas_executed = result.get("executed_personas", personas)
            personas_reused = []
            
            # Check reuse stats if available
            if "reuse_stats" in result:
                reuse_stats = result["reuse_stats"]
                # Calculate reused personas based on stats
                total_personas = len(personas)
                reused_count = reuse_stats.get("personas_reused", 0)
                if reused_count > 0:
                    # Simple heuristic: assume first N personas were reused
                    personas_reused = personas[:reused_count]
                    personas_executed = personas[reused_count:]
            
            # Calculate quality metrics from result
            quality_score = self._calculate_quality_from_result(result)
            completeness = self._calculate_completeness_from_result(result)
            test_coverage = self._calculate_test_coverage_from_result(result, phase)
            
            logger.info(f"✅ Execution complete via team_execution.py")
            logger.info(f"   Quality: {quality_score:.0%}")
            logger.info(f"   Completeness: {completeness:.0%}")
            
            return {
                'personas_executed': personas_executed,
                'personas_reused': personas_reused,
                'quality_score': quality_score,
                'completeness': completeness,
                'test_coverage': test_coverage,
                'raw_result': result
            }
            
        except Exception as e:
            logger.error(f"❌ Error executing personas via team_execution: {e}")
            import traceback
            traceback.print_exc()
            # Re-raise instead of falling back to mock
            raise RuntimeError(f"Persona execution failed: {e}") from e
    
    def _mock_execute_personas(
        self,
        personas: List[str],
        phase: SDLCPhase
    ) -> Dict[str, Any]:
        """
        Mock execution for testing when team_execution is not available
        """
        logger.warning("⚠️  MOCK EXECUTION MODE")
        
        # Mock results based on iteration (simulate improvement)
        base_quality = 0.75
        base_completeness = 0.80
        
        # Simulate progressive improvement
        iteration = self._get_phase_iteration(phase)
        quality_boost = min(0.05 * (iteration - 1), 0.15)
        
        return {
            'personas_executed': personas,
            'personas_reused': [],
            'quality_score': min(base_quality + quality_boost, 0.95),
            'completeness': min(base_completeness + quality_boost, 0.98),
            'test_coverage': 0.75 if phase == SDLCPhase.TESTING else 0.0
        }
    
    def _calculate_quality_from_result(self, result: Dict[str, Any]) -> float:
        """Calculate quality score from team_execution result"""
        # Extract quality metrics from persona validation results
        persona_results = result.get('persona_results', [])
        
        if not persona_results:
            return 0.70  # Default
        
        total_quality = 0.0
        count = 0
        
        for persona_result in persona_results:
            validation = persona_result.get('validation', {})
            quality = validation.get('quality_score', 0.0)
            
            if quality > 0:
                total_quality += quality
                count += 1
        
        if count == 0:
            return 0.70  # Default
        
        avg_quality = total_quality / count
        return avg_quality
    
    def _calculate_completeness_from_result(self, result: Dict[str, Any]) -> float:
        """Calculate completeness from team_execution result"""
        persona_results = result.get('persona_results', [])
        
        if not persona_results:
            return 0.75  # Default
        
        total_completeness = 0.0
        count = 0
        
        for persona_result in persona_results:
            validation = persona_result.get('validation', {})
            completeness = validation.get('completeness', 0.0)
            
            if completeness > 0:
                total_completeness += completeness
                count += 1
        
        if count == 0:
            return 0.75  # Default
        
        avg_completeness = total_completeness / count
        return avg_completeness
    
    def _calculate_test_coverage_from_result(
        self,
        result: Dict[str, Any],
        phase: SDLCPhase
    ) -> float:
        """Calculate test coverage from team_execution result"""
        if phase != SDLCPhase.TESTING:
            return 0.0
        
        # Extract test coverage from test persona results
        persona_results = result.get('persona_results', [])
        
        for persona_result in persona_results:
            if 'test' in persona_result.get('persona_id', '').lower():
                validation = persona_result.get('validation', {})
                test_metrics = validation.get('test_metrics', {})
                coverage = test_metrics.get('coverage', 0.0)
                
                if coverage > 0:
                    return coverage
        
        return 0.70  # Default for testing phase
    
    def _get_phase_iteration(self, phase: SDLCPhase) -> int:
        """Get iteration number for a phase (1-based)"""
        count = sum(1 for exec in self.phase_history if exec.phase == phase)
        return count + 1
    
    def _get_previous_phase_execution(self, phase: SDLCPhase) -> Optional[PhaseExecution]:
        """Get the most recent previous execution of this phase"""
        for phase_exec in reversed(self.phase_history):
            if phase_exec.phase == phase:
                return phase_exec
        return None
    
    def _save_progress(self):
        """Save current progress including phase history to session"""
        if not self.session:
            return
        
        try:
            # Serialize phase history to session metadata
            self.session.metadata["phase_history"] = [
                p.to_dict() for p in self.phase_history
            ]
            
            self.session.metadata["current_phase"] = (
                self.current_phase.value if self.current_phase else None
            )
            
            self.session.metadata["iteration_count"] = self.iteration_count
            self.session.metadata["workflow_mode"] = "phase_based"
            
            # Update timestamp
            self.session.last_updated = datetime.now()
            
            # Persist to disk
            self.session_manager.save_session(self.session)
            
            logger.debug(f"💾 Saved phase progress: {len(self.phase_history)} phases")
        
        except Exception as e:
            logger.error(f"❌ Error saving phase progress: {e}")
            import traceback
            traceback.print_exc()
    
    def _build_workflow_result(self, duration: float) -> WorkflowResult:
        """Build final workflow result"""
        
        # Determine completed phases
        completed_phases = [
            exec.phase for exec in self.phase_history
            if exec.state == PhaseState.COMPLETED
        ]
        
        # Calculate final metrics
        if self.phase_history:
            latest = self.phase_history[-1]
            final_quality = latest.quality_score
            final_completeness = latest.completeness
        else:
            final_quality = 0.0
            final_completeness = 0.0
        
        # Determine success
        all_phases = [
            SDLCPhase.REQUIREMENTS,
            SDLCPhase.DESIGN,
            SDLCPhase.IMPLEMENTATION,
            SDLCPhase.TESTING,
            SDLCPhase.DEPLOYMENT
        ]
        success = all(phase in completed_phases for phase in all_phases)
        
        return WorkflowResult(
            success=success,
            session_id=self.session_id,
            total_iterations=self.iteration_count,
            phases_completed=completed_phases,
            phase_history=self.phase_history,
            total_duration_seconds=duration,
            total_personas_executed=self.total_personas_executed,
            total_personas_reused=self.total_personas_reused,
            final_quality_score=final_quality,
            final_completeness=final_completeness
        )


# ============================================================================
# CLI Interface
# ============================================================================

async def main():
    """CLI entry point for phase workflow orchestration"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Phase-Based SDLC Workflow Orchestrator")
    parser.add_argument("--session-id", required=True, help="Session identifier")
    parser.add_argument("--requirement", required=True, help="Project requirement")
    parser.add_argument("--output", help="Output directory")
    parser.add_argument("--max-iterations", type=int, default=5, help="Max iterations")
    parser.add_argument("--disable-gates", action="store_true", help="Disable phase gates")
    parser.add_argument("--disable-progressive", action="store_true", help="Disable progressive quality")
    parser.add_argument("--maestro-ml-url", default="http://localhost:8001", help="ML backend URL")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s'
    )
    
    # Create orchestrator
    orchestrator = PhaseWorkflowOrchestrator(
        session_id=args.session_id,
        requirement=args.requirement,
        output_dir=Path(args.output) if args.output else None,
        enable_phase_gates=not args.disable_gates,
        enable_progressive_quality=not args.disable_progressive,
        maestro_ml_url=args.maestro_ml_url
    )
    
    # Execute workflow
    result = await orchestrator.execute_workflow(max_iterations=args.max_iterations)
    
    # Print summary
    print("\n" + "="*80)
    print("WORKFLOW SUMMARY")
    print("="*80)
    print(f"Session ID: {result.session_id}")
    print(f"Success: {'✅ YES' if result.success else '❌ NO'}")
    print(f"Iterations: {result.total_iterations}")
    print(f"Phases Completed: {len(result.phases_completed)}/{5}")
    print(f"Personas Executed: {result.total_personas_executed}")
    print(f"Personas Reused: {result.total_personas_reused}")
    print(f"Final Quality: {result.final_quality_score:.0%}")
    print(f"Final Completeness: {result.final_completeness:.0%}")
    print(f"Duration: {result.total_duration_seconds:.0f}s")
    print("="*80)
    
    # Exit with appropriate code
    sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    asyncio.run(main())
