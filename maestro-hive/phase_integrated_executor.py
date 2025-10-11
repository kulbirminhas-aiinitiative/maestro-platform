#!/usr/bin/env python3
"""
Phase-Integrated SDLC Executor

Integrates phase workflow orchestration with team execution engine.
This is the missing link that connects:
- PhaseWorkflowOrchestrator (phase management)
- AutonomousSDLCEngineV3_1_Resumable (persona execution)
- PhaseGateValidator (quality gates)
- ProgressiveQualityManager (quality thresholds)

This fixes the Sunday.com issue by:
1. Enforcing phase boundaries
2. Detecting completion properly
3. Catching failures early
4. Progressive quality enforcement
5. Adaptive persona selection
"""

import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

sys.path.insert(0, str(Path(__file__).parent))

from phase_models import (
    SDLCPhase,
    PhaseState,
    PhaseExecution,
    PhaseIssue,
    QualityThresholds,
    PhaseGateResult
)
from phase_workflow_orchestrator import PhaseWorkflowOrchestrator
from phase_gate_validator import PhaseGateValidator
from progressive_quality_manager import ProgressiveQualityManager
from team_organization import TeamOrganization
from session_manager import SessionManager

# Import team execution engine
try:
    from team_execution import AutonomousSDLCEngineV3_1_Resumable
    TEAM_EXECUTION_AVAILABLE = True
except ImportError:
    TEAM_EXECUTION_AVAILABLE = False
    logging.warning("⚠️  team_execution not available")

logger = logging.getLogger(__name__)


class PhaseIntegratedExecutor:
    """
    Integrated phase-based SDLC executor
    
    Bridges phase workflow orchestration with actual persona execution,
    enforcing quality gates and progressive thresholds at every step.
    
    Key Innovation:
    - Phase-by-phase execution with validation
    - Early failure detection (fail at Design, not Deployment)
    - Progressive quality (60% → 70% → 80% → 95%)
    - Adaptive persona selection (only run what's needed)
    """
    
    def __init__(
        self,
        session_id: str,
        requirement: str,
        output_dir: Optional[Path] = None,
        enable_phase_gates: bool = True,
        enable_progressive_quality: bool = True,
        enable_persona_reuse: bool = True,
        maestro_ml_url: str = "http://localhost:8001"
    ):
        """
        Initialize phase-integrated executor
        
        Args:
            session_id: Unique session identifier
            requirement: Project requirement description
            output_dir: Output directory for generated code
            enable_phase_gates: Enable phase gate validation
            enable_progressive_quality: Enable progressive quality thresholds
            enable_persona_reuse: Enable V4.1 persona-level reuse
            maestro_ml_url: URL for ML backend (persona reuse)
        """
        self.session_id = session_id
        self.requirement = requirement
        self.output_dir = output_dir or Path(f"./sdlc_output/{session_id}")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Configuration
        self.enable_phase_gates = enable_phase_gates
        self.enable_progressive_quality = enable_progressive_quality
        self.enable_persona_reuse = enable_persona_reuse
        self.maestro_ml_url = maestro_ml_url
        
        # Components
        self.phase_gates = PhaseGateValidator()
        self.quality_manager = ProgressiveQualityManager()
        self.team_org = TeamOrganization()
        self.session_manager = SessionManager()
        
        # Team execution engine
        if not TEAM_EXECUTION_AVAILABLE:
            raise RuntimeError(
                "team_execution module required. "
                "Install with: pip install claude_code_sdk"
            )
        
        # Initialize team executor (will be created per-phase)
        self.team_executor = None
        
        # State
        self.current_phase: Optional[SDLCPhase] = None
        self.phase_history: List[PhaseExecution] = []
        self.iteration_count = 0
        
        logger.info(f"🚀 Phase-Integrated Executor initialized")
        logger.info(f"   Session: {session_id}")
        logger.info(f"   Output: {self.output_dir}")
        logger.info(f"   Phase Gates: {'✅ Enabled' if enable_phase_gates else '❌ Disabled'}")
        logger.info(f"   Progressive Quality: {'✅ Enabled' if enable_progressive_quality else '❌ Disabled'}")
        logger.info(f"   Persona Reuse: {'✅ Enabled' if enable_persona_reuse else '❌ Disabled'}")
    
    async def execute_workflow(
        self,
        max_iterations: int = 5,
        target_phases: Optional[List[SDLCPhase]] = None
    ) -> Dict[str, Any]:
        """
        Execute complete phase-based SDLC workflow
        
        Flow:
        1. Start with REQUIREMENTS phase
        2. For each phase:
           a. Validate entry criteria (can we start?)
           b. Select personas needed for phase
           c. Get progressive quality thresholds
           d. Execute personas via team_execution
           e. Validate deliverables and quality
           f. Validate exit criteria (can we proceed?)
           g. Decide: next phase, rework, or fail
        3. Continue until DEPLOYMENT complete or max iterations
        
        Args:
            max_iterations: Maximum iterations allowed
            target_phases: Phases to execute (default: all)
        
        Returns:
            Workflow result with status, metrics, and recommendations
        """
        
        if not target_phases:
            target_phases = [
                SDLCPhase.REQUIREMENTS,
                SDLCPhase.DESIGN,
                SDLCPhase.IMPLEMENTATION,
                SDLCPhase.TESTING,
                SDLCPhase.DEPLOYMENT
            ]
        
        start_time = datetime.now()
        
        logger.info("\n" + "="*80)
        logger.info("🚀 PHASE-INTEGRATED SDLC WORKFLOW")
        logger.info("="*80)
        logger.info(f"📝 Requirement: {self.requirement[:80]}...")
        logger.info(f"🆔 Session: {self.session_id}")
        logger.info(f"📁 Output: {self.output_dir}")
        logger.info(f"🎯 Target Phases: {[p.value for p in target_phases]}")
        logger.info(f"🔄 Max Iterations: {max_iterations}")
        logger.info("="*80 + "\n")
        
        # Main workflow loop
        for iteration in range(1, max_iterations + 1):
            self.iteration_count = iteration
            
            logger.info(f"\n{'='*80}")
            logger.info(f"🔄 ITERATION {iteration}/{max_iterations}")
            logger.info(f"{'='*80}\n")
            
            # Execute each phase in sequence
            for phase in target_phases:
                self.current_phase = phase
                
                logger.info(f"\n{'-'*80}")
                logger.info(f"📍 PHASE: {phase.value}")
                logger.info(f"{'-'*80}\n")
                
                # Execute phase with full validation
                phase_execution = await self.execute_phase(
                    phase=phase,
                    iteration=iteration
                )
                
                # Record phase execution
                self.phase_history.append(phase_execution)
                
                # Check phase result
                if phase_execution.state == PhaseState.BLOCKED:
                    logger.error(f"\n🚫 BLOCKED: Cannot start {phase.value}")
                    logger.error("Entry gate validation failed")
                    return self._build_failure_result(
                        phase, iteration, "Entry gate blocked", phase_execution
                    )
                
                elif phase_execution.state == PhaseState.FAILED:
                    logger.error(f"\n❌ FAILED: {phase.value} execution failed")
                    return self._build_failure_result(
                        phase, iteration, "Execution failed", phase_execution
                    )
                
                elif phase_execution.state == PhaseState.REQUIRES_REWORK:
                    logger.warning(f"\n⚠️  REWORK NEEDED: {phase.value}")
                    logger.warning(f"Exit gate validation failed")
                    
                    # Log issues
                    if phase_execution.issues:
                        logger.warning("Issues found:")
                        for issue in phase_execution.issues:
                            logger.warning(f"  - {issue.description}")
                    
                    # Check if we should retry or fail
                    if iteration >= max_iterations:
                        logger.error(f"\n❌ Max iterations reached")
                        return self._build_failure_result(
                            phase, iteration, "Max iterations exceeded", phase_execution
                        )
                    
                    # Break from phase loop to retry in next iteration
                    logger.info(f"\n🔄 Will retry {phase.value} in iteration {iteration + 1}")
                    break
                
                elif phase_execution.state == PhaseState.COMPLETED:
                    logger.info(f"\n✅ COMPLETED: {phase.value}")
                    logger.info(f"   Completeness: {phase_execution.completeness:.0%}")
                    logger.info(f"   Quality: {phase_execution.quality_score:.2f}")
                    logger.info(f"   Personas: {', '.join(phase_execution.personas_executed)}")
                    
                    # Continue to next phase
                    continue
                
                else:
                    logger.warning(f"\n⚠️  Unknown state: {phase_execution.state}")
                    return self._build_failure_result(
                        phase, iteration, "Unknown state", phase_execution
                    )
            
            # Check if all phases completed successfully
            if all(
                any(
                    pe.phase == phase and pe.state == PhaseState.COMPLETED
                    for pe in self.phase_history
                )
                for phase in target_phases
            ):
                logger.info(f"\n{'='*80}")
                logger.info("✅ ✅ ✅ WORKFLOW COMPLETE ✅ ✅ ✅")
                logger.info(f"{'='*80}\n")
                
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                
                return self._build_success_result(duration)
        
        # Max iterations reached without full completion
        logger.warning(f"\n{'='*80}")
        logger.warning("⚠️  WORKFLOW INCOMPLETE")
        logger.warning(f"Reached max iterations ({max_iterations})")
        logger.warning(f"{'='*80}\n")
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        return self._build_partial_result(duration)
    
    async def execute_phase(
        self,
        phase: SDLCPhase,
        iteration: int
    ) -> PhaseExecution:
        """
        Execute single phase with full validation pipeline
        
        Steps:
        1. Validate entry gate (prerequisites)
        2. Select personas for phase
        3. Get progressive quality thresholds
        4. Execute personas via team_execution
        5. Validate deliverables
        6. Validate exit gate (quality)
        7. Return phase execution result
        
        Args:
            phase: Phase to execute
            iteration: Current iteration number
        
        Returns:
            PhaseExecution with results and validation status
        """
        
        phase_execution = PhaseExecution(
            phase=phase,
            iteration=iteration,
            start_time=datetime.now()
        )
        
        # ====================================================================
        # STEP 1: Entry Gate Validation
        # ====================================================================
        logger.info(f"🚪 Step 1: Validating ENTRY gate for {phase.value}...")
        
        entry_result = await self.phase_gates.validate_entry_criteria(
            phase, self.phase_history
        )
        
        phase_execution.entry_gate = entry_result
        
        if not entry_result.passed:
            logger.error(f"❌ Entry gate FAILED for {phase.value}")
            phase_execution.state = PhaseState.BLOCKED
            phase_execution.end_time = datetime.now()
            
            # Convert blocking issues to PhaseIssue objects
            for issue_desc in entry_result.blocking_issues:
                phase_execution.add_issue(PhaseIssue(
                    severity="critical",
                    category="entry_gate",
                    description=issue_desc,
                    phase=phase
                ))
            
            return phase_execution
        
        logger.info(f"✅ Entry gate PASSED ({entry_result.score:.0%})")
        
        # ====================================================================
        # STEP 2: Adaptive Persona Selection
        # ====================================================================
        logger.info(f"\n👥 Step 2: Selecting personas for {phase.value}...")
        
        # Get personas for this phase
        # For now, use simple phase-persona mapping
        # TODO: Implement AdaptivePersonaSelector
        personas = self._select_personas_for_phase(phase, iteration)
        
        logger.info(f"Selected {len(personas)} persona(s): {', '.join(personas)}")
        phase_execution.personas_executed = personas
        
        # ====================================================================
        # STEP 3: Get Progressive Quality Thresholds
        # ====================================================================
        logger.info(f"\n📊 Step 3: Getting quality thresholds...")
        
        thresholds = self.quality_manager.get_thresholds_for_iteration(
            phase, iteration
        )
        
        logger.info(
            f"Thresholds for iteration {iteration}: "
            f"completeness={thresholds.completeness:.0%}, "
            f"quality={thresholds.quality:.2f}, "
            f"test_coverage={thresholds.test_coverage:.0%}"
        )
        
        # ====================================================================
        # STEP 4: Execute Personas
        # ====================================================================
        logger.info(f"\n🔨 Step 4: Executing personas...")
        
        try:
            execution_results = await self._execute_personas_for_phase(
                phase=phase,
                personas=personas,
                thresholds=thresholds,
                iteration=iteration
            )
            
            phase_execution.completeness = execution_results.get("completeness", 0.0)
            phase_execution.quality_score = execution_results.get("quality_score", 0.0)
            phase_execution.personas_executed = personas
            
            logger.info(f"✅ Persona execution complete")
            logger.info(f"   Completeness: {phase_execution.completeness:.0%}")
            logger.info(f"   Quality: {phase_execution.quality_score:.2f}")
        
        except Exception as e:
            logger.exception(f"❌ Error executing personas: {e}")
            phase_execution.state = PhaseState.FAILED
            phase_execution.end_time = datetime.now()
            phase_execution.add_issue(PhaseIssue(
                severity="critical",
                category="execution",
                description=f"Execution error: {str(e)}",
                phase=phase
            ))
            return phase_execution
        
        # ====================================================================
        # STEP 5: Validate Deliverables
        # ====================================================================
        logger.info(f"\n📦 Step 5: Validating deliverables...")
        
        deliverable_validation = await self._validate_phase_deliverables(
            phase, execution_results
        )
        
        # ====================================================================
        # STEP 6: Exit Gate Validation
        # ====================================================================
        logger.info(f"\n🚪 Step 6: Validating EXIT gate for {phase.value}...")
        
        exit_result = await self.phase_gates.validate_exit_criteria(
            phase, 
            self.phase_history,
            execution_results.get("session", None),
            thresholds
        )
        
        phase_execution.exit_gate = exit_result
        
        if exit_result.passed:
            logger.info(f"✅ Exit gate PASSED ({exit_result.score:.0%})")
            phase_execution.state = PhaseState.COMPLETED
        else:
            logger.warning(f"⚠️  Exit gate FAILED ({exit_result.score:.0%})")
            phase_execution.state = PhaseState.REQUIRES_REWORK
            
            # Convert exit gate issues to PhaseIssue objects
            for issue_desc in exit_result.blocking_issues:
                phase_execution.add_issue(PhaseIssue(
                    severity="high",
                    category="exit_gate",
                    description=issue_desc,
                    phase=phase
                ))
            
            # Log recommendations
            if exit_result.recommendations:
                logger.info("\n📋 Recommendations:")
                for rec in exit_result.recommendations:
                    logger.info(f"   - {rec}")
        
        phase_execution.end_time = datetime.now()
        
        return phase_execution
    
    async def _execute_personas_for_phase(
        self,
        phase: SDLCPhase,
        personas: List[str],
        thresholds: QualityThresholds,
        iteration: int
    ) -> Dict[str, Any]:
        """
        Execute personas for a specific phase using team_execution engine
        
        Args:
            phase: Current phase
            personas: List of persona IDs to execute
            thresholds: Progressive quality thresholds
            iteration: Current iteration number
        
        Returns:
            Execution results including completeness, quality, and session data
        """
        
        # Create team executor for this phase
        team_executor = AutonomousSDLCEngineV3_1_Resumable(
            selected_personas=personas,
            output_dir=str(self.output_dir),
            session_manager=self.session_manager,
            maestro_ml_url=self.maestro_ml_url,
            enable_persona_reuse=self.enable_persona_reuse,
            force_rerun=False  # Let phase system handle retries
        )
        
        # Store thresholds in executor for quality gate validation
        # This connects progressive quality manager with team execution
        team_executor.quality_thresholds = thresholds
        team_executor.current_phase = phase
        team_executor.current_iteration = iteration
        
        # Execute personas
        result = await team_executor.execute(
            requirement=self.requirement,
            session_id=self.session_id,
            resume_session_id=self.session_id if iteration > 1 else None
        )
        
        # Extract metrics from result
        session = self.session_manager.load_session(self.session_id)
        
        # Calculate completeness and quality from session
        completeness = self._calculate_phase_completeness(phase, session)
        quality_score = self._calculate_phase_quality(phase, session)
        
        return {
            "completeness": completeness,
            "quality_score": quality_score,
            "session": session,
            "result": result
        }
    
    def _select_personas_for_phase(
        self,
        phase: SDLCPhase,
        iteration: int
    ) -> List[str]:
        """
        Select personas needed for phase
        
        Simple implementation - maps phases to personas.
        Future enhancement: Adaptive selection based on previous issues.
        
        Args:
            phase: Current phase
            iteration: Current iteration
        
        Returns:
            List of persona IDs
        """
        
        # Base persona mapping per phase
        phase_personas = {
            SDLCPhase.REQUIREMENTS: [
                "requirement_analyst"
            ],
            SDLCPhase.DESIGN: [
                "solution_architect",
                "security_specialist"
            ],
            SDLCPhase.IMPLEMENTATION: [
                "backend_developer",
                "frontend_developer"
            ],
            SDLCPhase.TESTING: [
                "qa_engineer",
                "integration_tester"
            ],
            SDLCPhase.DEPLOYMENT: [
                "devops_engineer",
                "deployment_specialist"
            ]
        }
        
        personas = phase_personas.get(phase, [])
        
        # Iteration 1: Run all base personas
        # Iteration 2+: Could be optimized to only run failed personas
        # For now, run all to ensure quality
        
        logger.debug(f"Phase {phase.value} personas: {personas}")
        
        return personas
    
    async def _validate_phase_deliverables(
        self,
        phase: SDLCPhase,
        execution_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate deliverables for phase
        
        Args:
            phase: Current phase
            execution_results: Results from persona execution
        
        Returns:
            Validation results
        """
        
        # For now, return basic validation
        # Future: Implement comprehensive deliverable checking
        
        return {
            "valid": True,
            "missing_deliverables": [],
            "issues": []
        }
    
    def _calculate_phase_completeness(
        self,
        phase: SDLCPhase,
        session: Any
    ) -> float:
        """
        Calculate completeness for phase based on deliverables
        
        Args:
            phase: Current phase
            session: SDLC session with results
        
        Returns:
            Completeness score (0.0 to 1.0)
        """
        
        # Read validation reports if available
        validation_dir = self.output_dir / "validation_reports"
        
        if validation_dir.exists():
            summary_file = validation_dir / "summary.json"
            
            if summary_file.exists():
                import json
                summary = json.loads(summary_file.read_text())
                
                # Average completeness across personas
                completeness_scores = [
                    p["completeness"] / 100.0
                    for p in summary.get("personas", {}).values()
                ]
                
                if completeness_scores:
                    return sum(completeness_scores) / len(completeness_scores)
        
        # Fallback: Estimate based on completed personas
        if session and session.completed_personas:
            # Rough estimate: 70% base if personas ran
            return 0.70
        
        return 0.0
    
    def _calculate_phase_quality(
        self,
        phase: SDLCPhase,
        session: Any
    ) -> float:
        """
        Calculate quality score for phase
        
        Args:
            phase: Current phase
            session: SDLC session with results
        
        Returns:
            Quality score (0.0 to 1.0)
        """
        
        # Read validation reports if available
        validation_dir = self.output_dir / "validation_reports"
        
        if validation_dir.exists():
            summary_file = validation_dir / "summary.json"
            
            if summary_file.exists():
                import json
                summary = json.loads(summary_file.read_text())
                
                # Average quality across personas
                quality_scores = [
                    p["quality"]
                    for p in summary.get("personas", {}).values()
                ]
                
                if quality_scores:
                    return sum(quality_scores) / len(quality_scores)
        
        # Fallback: Estimate based on success
        if session and session.completed_personas:
            return 0.65
        
        return 0.0
    
    def _build_success_result(self, duration: float) -> Dict[str, Any]:
        """Build successful workflow result"""
        
        return {
            "success": True,
            "status": "completed",
            "session_id": self.session_id,
            "requirement": self.requirement,
            "total_iterations": self.iteration_count,
            "total_duration_seconds": duration,
            "phases_completed": [
                pe.phase.value
                for pe in self.phase_history
                if pe.state == PhaseState.COMPLETED
            ],
            "phase_history": [
                {
                    "phase": pe.phase.value,
                    "iteration": pe.iteration,
                    "state": pe.state.value,
                    "completeness": pe.completeness,
                    "quality_score": pe.quality_score,
                    "personas": pe.personas_executed
                }
                for pe in self.phase_history
            ],
            "output_dir": str(self.output_dir),
            "recommendations": []
        }
    
    def _build_failure_result(
        self,
        phase: SDLCPhase,
        iteration: int,
        reason: str,
        phase_execution: PhaseExecution
    ) -> Dict[str, Any]:
        """Build failure result"""
        
        recommendations = []
        
        if phase_execution.issues:
            recommendations.append(f"Fix {len(phase_execution.issues)} issues in {phase.value} phase")
            for issue in phase_execution.issues[:3]:  # Top 3
                recommendations.append(f"- {issue.description}")
        
        return {
            "success": False,
            "status": "failed",
            "session_id": self.session_id,
            "requirement": self.requirement,
            "failed_at_phase": phase.value,
            "failed_at_iteration": iteration,
            "failure_reason": reason,
            "recommendations": recommendations,
            "phase_history": [
                {
                    "phase": pe.phase.value,
                    "iteration": pe.iteration,
                    "state": pe.state.value,
                    "completeness": pe.completeness,
                    "quality_score": pe.quality_score
                }
                for pe in self.phase_history
            ],
            "output_dir": str(self.output_dir)
        }
    
    def _build_partial_result(self, duration: float) -> Dict[str, Any]:
        """Build partial completion result"""
        
        completed_phases = [
            pe.phase.value
            for pe in self.phase_history
            if pe.state == PhaseState.COMPLETED
        ]
        
        return {
            "success": False,
            "status": "partial",
            "session_id": self.session_id,
            "requirement": self.requirement,
            "total_iterations": self.iteration_count,
            "total_duration_seconds": duration,
            "phases_completed": completed_phases,
            "phase_history": [
                {
                    "phase": pe.phase.value,
                    "iteration": pe.iteration,
                    "state": pe.state.value,
                    "completeness": pe.completeness,
                    "quality_score": pe.quality_score
                }
                for pe in self.phase_history
            ],
            "output_dir": str(self.output_dir),
            "recommendations": [
                "Consider increasing max_iterations to allow more refinement"
            ]
        }


# ============================================================================
# CLI for Testing
# ============================================================================

async def main():
    """CLI entry point for testing"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Phase-Integrated SDLC Executor",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument("--session", required=True, help="Session ID")
    parser.add_argument("--requirement", required=True, help="Project requirement")
    parser.add_argument("--output", help="Output directory")
    parser.add_argument("--max-iterations", type=int, default=5, help="Max iterations")
    parser.add_argument("--disable-phase-gates", action="store_true", help="Disable phase gates")
    parser.add_argument("--disable-progressive-quality", action="store_true", help="Disable progressive quality")
    parser.add_argument("--disable-persona-reuse", action="store_true", help="Disable persona reuse")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )
    
    # Create executor
    executor = PhaseIntegratedExecutor(
        session_id=args.session,
        requirement=args.requirement,
        output_dir=Path(args.output) if args.output else None,
        enable_phase_gates=not args.disable_phase_gates,
        enable_progressive_quality=not args.disable_progressive_quality,
        enable_persona_reuse=not args.disable_persona_reuse
    )
    
    # Execute workflow
    result = await executor.execute_workflow(max_iterations=args.max_iterations)
    
    # Print summary
    print("\n" + "="*80)
    print("WORKFLOW RESULT")
    print("="*80)
    print(f"Success: {result['success']}")
    print(f"Status: {result['status']}")
    print(f"Iterations: {result.get('total_iterations', 0)}")
    
    if result['success']:
        print(f"Phases Completed: {', '.join(result['phases_completed'])}")
    else:
        print(f"Failed At: {result.get('failed_at_phase', 'N/A')}")
        print("\nRecommendations:")
        for rec in result.get('recommendations', []):
            print(f"  - {rec}")
    
    print(f"\nOutput: {result['output_dir']}")
    print("="*80)
    
    return 0 if result['success'] else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
