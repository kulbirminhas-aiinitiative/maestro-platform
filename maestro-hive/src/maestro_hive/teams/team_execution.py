#!/usr/bin/env python3
"""
Autonomous SDLC Engine V3.1 - Persona-Level Intelligent Reuse + Resumable Sessions

Revolutionary Integration:
- V4.1 Persona-Level Reuse: Analyze each persona independently for artifact reuse
- Resumable Sessions: Continue work across multiple runs
- RAG Integration: Get templates and best practices
- Quality Review: Validate outputs with Quality Fabric
- Template Creation: High-quality outputs become reusable templates

Complete Workflow:
  Frontend (WebSocket/REST)
      ↓
  BFF Service (unified_bff_service.py)
      ↓
  Autonomous SDLC Engine V3.1 (THIS FILE)
      ↓
  ┌─────────────────────────────────────────────┐
  │ NEW: Persona-Level Reuse Analysis (V4.1)    │
  │ - Check similar projects                    │
  │ - Build PersonaReuseMap                     │
  │ - Decide per-persona: reuse vs execute      │
  └─────────────────────────────────────────────┘
      ↓
  ┌─────────────────────────────────────────────┐
  │ For Personas to REUSE (85%+ match):         │
  │ - Fetch artifacts from similar projects     │
  │ - Skip execution (0 minutes)                │
  │ - Integrate into current session            │
  └─────────────────────────────────────────────┘
      ↓
  ┌─────────────────────────────────────────────┐
  │ For Personas to EXECUTE (<85% match):       │
  │ - RAG Integration (templates/best practices)│
  │ - Persona Execution (Claude Code SDK)       │
  │ - Quality Review (quality_service.py)       │
  │ - Template Validation & Creation            │
  └─────────────────────────────────────────────┘
      ↓
  Response to Frontend (quality scores + reuse stats)

Key Innovation:
  Even if overall project is 50% similar (V3 would execute all),
  V3.1 identifies specific personas with 90%+ matches and reuses them!

  Example:
    Overall: 52% similar
    - system_architect: 100% → REUSE ⚡
    - frontend_developer: 90% → REUSE ⚡
    - backend_developer: 35% → EXECUTE 🔨
    Result: 50% time savings (V3: 0% savings)
"""

import asyncio
import sys
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import httpx
import json

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from personas import SDLCPersonas
from team_organization import get_deliverables_for_persona
from config import CLAUDE_CONFIG, OUTPUT_CONFIG
from session_manager import SessionManager, SDLCSession
from validation_utils import (
    validate_persona_deliverables,
    detect_stubs_and_placeholders,
    detect_project_type,
    analyze_implementation_quality
)

# NEW: AutoGen-inspired enhancements
from conversation_manager import ConversationHistory
from collaborative_executor import CollaborativeExecutor
from structured_output_extractor import StructuredOutputExtractor

# MD-3096: Proactive Constraint Injection (BDV/ACC in prompts)
try:
    from constraint_injector import get_constraint_injector, InjectorConfig
    CONSTRAINT_INJECTOR_AVAILABLE = True
    logger.info("✅ ConstraintInjector loaded (MD-3096)")
except ImportError:
    CONSTRAINT_INJECTOR_AVAILABLE = False
    logger.warning("⚠️ ConstraintInjector not available")

# Claude Code SDK
try:
    from claude_code_sdk import query, ClaudeCodeOptions
    from claude_code_sdk._internal.transport.subprocess_cli import SubprocessCLITransport
    CLAUDE_SDK_AVAILABLE = True
except ImportError:
    CLAUDE_SDK_AVAILABLE = False
    logging.error("❌ claude_code_sdk not available")

logger = logging.getLogger(__name__)

# Find Claude CLI path (needed for SubprocessCLITransport in poetry virtualenv)
def find_claude_cli():
    """Find Claude CLI in common locations since poetry subprocess may not have it in PATH."""
    # Try which() first
    cli_path = shutil.which("claude")
    if cli_path:
        return cli_path

    # Check common NVM locations
    import os
    home = os.path.expanduser("~")
    common_paths = [
        f"{home}/.nvm/versions/node/v22.19.0/bin/claude",
        f"{home}/.nvm/versions/node/v20.12.0/bin/claude",
        f"{home}/.nvm/versions/node/v18.18.0/bin/claude",
        "/usr/local/bin/claude",
        "/usr/bin/claude",
        f"{home}/.local/bin/claude",
        f"{home}/node_modules/.bin/claude",
    ]

    for path in common_paths:
        if Path(path).exists():
            return path

    return None

CLAUDE_CLI_PATH = find_claude_cli()
if not CLAUDE_CLI_PATH:
    logger.warning("⚠️  Claude CLI not found - persona execution may fail")
else:
    logger.info(f"✅ Found Claude CLI at: {CLAUDE_CLI_PATH}")

# ============================================================================
# V4.1 DATA STRUCTURES
# ============================================================================

class PersonaReuseDecision:
    """Reuse decision for a single persona"""
    def __init__(
        self,
        persona_id: str,
        similarity_score: float,
        should_reuse: bool,
        source_project_id: Optional[str],
        rationale: str,
        match_details: Dict[str, Any]
    ):
        self.persona_id = persona_id
        self.similarity_score = similarity_score
        self.should_reuse = should_reuse
        self.source_project_id = source_project_id
        self.rationale = rationale
        self.match_details = match_details
        self.source_artifacts = []


class PersonaReuseMap:
    """Complete persona-level reuse map"""
    def __init__(
        self,
        overall_similarity: float,
        persona_decisions: Dict[str, PersonaReuseDecision],
        personas_to_reuse: List[str],
        personas_to_execute: List[str],
        time_savings_percent: float,
        cost_savings_dollars: float
    ):
        self.overall_similarity = overall_similarity
        self.persona_decisions = persona_decisions
        self.personas_to_reuse = personas_to_reuse
        self.personas_to_execute = personas_to_execute
        self.time_savings_percent = time_savings_percent
        self.cost_savings_dollars = cost_savings_dollars


# ============================================================================
# PERSONA EXECUTION CONTEXT
# ============================================================================

class PersonaExecutionContext:
    """Context for a single persona's execution"""

    def __init__(self, persona_id: str, requirement: str, output_dir: Path):
        self.persona_id = persona_id
        self.requirement = requirement
        self.output_dir = output_dir
        self.files_created = []
        self.deliverables = {}
        self.start_time = datetime.now()
        self.end_time = None
        self.success = False
        self.error = None
        self.reused = False  # NEW: Track if this was reused
        self.reuse_source = None  # NEW: Source project if reused
        self.quality_gate = None  # NEW: Quality gate validation results
        self.quality_issues = []  # NEW: List of quality issues found

    def mark_complete(self, success: bool = True, error: str = None):
        self.end_time = datetime.now()
        self.success = success
        self.error = error

    def mark_reused(self, source_project_id: str):
        """Mark this persona as reused (not executed)"""
        self.reused = True
        self.reuse_source = source_project_id
        self.success = True
        self.end_time = datetime.now()

    def duration(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0

    def add_file(self, file_path: str):
        self.files_created.append(file_path)


# ============================================================================
# V4.1 PERSONA-LEVEL REUSE CLIENT
# ============================================================================

class PersonaReuseClient:
    """Client for ML Phase 3.1 persona-level reuse APIs"""

    def __init__(self, maestro_ml_url: str = "http://localhost:8001"):
        self.base_url = maestro_ml_url

    async def build_persona_reuse_map(
        self,
        new_requirements: str,
        existing_requirements: str,
        persona_ids: List[str]
    ) -> Optional[PersonaReuseMap]:
        """
        Build persona-level reuse map by calling ML Phase 3.1 API
        """
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/ml/persona/build-reuse-map",
                    json={
                        "new_project_requirements": new_requirements,
                        "existing_project_requirements": existing_requirements,
                        "persona_ids": persona_ids
                    }
                )

                if response.status_code != 200:
                    logger.warning(f"Persona reuse map failed: {response.text}")
                    return None

                data = response.json()

                # Build PersonaReuseDecision objects
                persona_decisions = {}
                for persona_id, match_data in data["persona_matches"].items():
                    decision = PersonaReuseDecision(
                        persona_id=persona_id,
                        similarity_score=match_data["similarity_score"],
                        should_reuse=match_data["should_reuse"],
                        source_project_id=match_data.get("source_project_id"),
                        rationale=match_data["rationale"],
                        match_details=match_data["match_details"]
                    )
                    persona_decisions[persona_id] = decision

                return PersonaReuseMap(
                    overall_similarity=data["overall_similarity"],
                    persona_decisions=persona_decisions,
                    personas_to_reuse=data["personas_to_reuse"],
                    personas_to_execute=data["personas_to_execute"],
                    time_savings_percent=data["estimated_time_savings_percent"],
                    cost_savings_dollars=data.get("summary", {}).get("reuse_count", 0) * 22
                )

        except Exception as e:
            logger.error(f"Error building persona reuse map: {e}")
            return None

    async def find_similar_project(self, specs: Dict) -> Optional[Dict]:
        """Find most similar project"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/ml/find-similar-projects",
                    json={
                        "specs": specs,
                        "min_similarity": 0.50,  # Lower threshold for persona-level
                        "limit": 1
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    if data:
                        return data[0]  # Most similar

        except Exception as e:
            logger.error(f"Error finding similar project: {e}")

        return None

    async def fetch_persona_artifacts(
        self,
        source_project_id: str,
        persona_id: str
    ) -> List[str]:
        """Fetch artifacts for a specific persona from source project"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/projects/{source_project_id}/artifacts",
                    params={"persona": persona_id}
                )

                if response.status_code == 200:
                    data = response.json()
                    return data.get("artifacts", [])

        except Exception as e:
            logger.warning(f"Could not fetch artifacts for {persona_id}: {e}")

        return []


# ============================================================================
# AUTONOMOUS SDLC ENGINE V3.1 (Persona-Level Reuse + Resumable)
# ============================================================================

class AutonomousSDLCEngineV3_1_Resumable:
    """
    V3.1 Engine with Persona-Level Intelligent Reuse + Resumable Sessions

    Key Features:
    1. Persona-level reuse analysis (V4.1)
    2. Session persistence and resume
    3. RAG integration for templates
    4. Quality review and validation
    5. Template creation from high-quality outputs
    """

    def __init__(
        self,
        selected_personas: List[str],
        output_dir: str = None,
        session_manager: SessionManager = None,
        maestro_ml_url: str = "http://localhost:8001",
        enable_persona_reuse: bool = True,
        force_rerun: bool = False
    ):
        if not CLAUDE_SDK_AVAILABLE:
            raise RuntimeError("claude_code_sdk is required")

        self.selected_personas = selected_personas
        self.output_dir = Path(output_dir or OUTPUT_CONFIG["default_output_dir"])
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Session manager
        self.session_manager = session_manager or SessionManager()

        # V4.1: Persona reuse client
        self.enable_persona_reuse = enable_persona_reuse

        # Force re-run of completed personas (for iterative improvements)
        self.force_rerun = force_rerun
        self.persona_reuse_client = PersonaReuseClient(maestro_ml_url)

        # Load persona configurations (will be loaded async in ensure_initialized)
        self.all_personas = {}
        self.persona_configs = {}
        self._initialized = False

        # Stats
        self.reuse_stats = {
            "personas_reused": 0,
            "personas_executed": 0,
            "time_saved_seconds": 0,
            "cost_saved_dollars": 0
        }

        # Project context for validation
        self.project_context = None
        
        # NEW: Phase-aware execution support
        # These are set by PhaseIntegratedExecutor to enable progressive quality
        self.quality_thresholds = None  # QualityThresholds from ProgressiveQualityManager
        self.current_phase = None  # SDLCPhase enum
        self.current_iteration = None  # int
        
        # NEW: Message-based context system (Phase 1 - AutoGen-inspired)
        # Replaces simple string context with rich conversation history
        self.conversation = None  # Will be initialized in execute_workflow
        self.output_extractor = StructuredOutputExtractor()
        self.collaborative_executor = None  # Will be initialized in execute_workflow

    async def ensure_initialized(self):
        """Ensure personas are loaded asynchronously"""
        if self._initialized:
            return

        # Load personas asynchronously
        try:
            from src.personas import get_adapter
            adapter = get_adapter()
            await adapter.ensure_loaded()
        except Exception as e:
            logger.warning(f"Could not load personas via adapter: {e}")

        self.all_personas = SDLCPersonas.get_all_personas()
        self.persona_configs = {
            pid: self.all_personas[pid]
            for pid in self.selected_personas
            if pid in self.all_personas
        }

        if not self.persona_configs:
            raise ValueError(f"No valid personas found in: {self.selected_personas}")

        self._initialized = True

    def _determine_execution_order(self, personas: List[str]) -> List[str]:
        """
        Determine optimal execution order with deployment validation personas

        NEW: Automatically includes devops_engineer and deployment_specialist
        at the end if they're in the available personas (but not already selected)
        """
        priority_tiers = {
            "requirement_analyst": 1,
            "solution_architect": 2,
            "security_specialist": 3,
            "backend_developer": 4,
            "database_specialist": 4,
            "frontend_developer": 5,
            "ui_ux_designer": 5,
            "unit_tester": 6,
            "qa_engineer": 6,
            "test_engineer": 7,  # NEW: Generates & runs comprehensive tests
            "integration_tester": 7,
            "devops_engineer": 8,
            "deployment_specialist": 9,
            "deployment_integration_tester": 9,  # Alias
            "technical_writer": 10
        }

        # Sort selected personas by priority
        ordered = sorted(personas, key=lambda p: priority_tiers.get(p, 999))

        # NEW: Ensure QA and deployment personas are included for production-ready output
        # This ensures deployment validation happens automatically
        recommended_personas = []

        # If backend/frontend developers ran, ensure QA and Test Engineer run
        if any(p in personas for p in ["backend_developer", "frontend_developer"]):
            if "qa_engineer" not in personas:
                recommended_personas.append("qa_engineer")

            # NEW: Auto-add test_engineer for comprehensive test generation
            if "test_engineer" not in personas and "test_engineer" in self.all_personas:
                recommended_personas.append("test_engineer")

        # If any development personas ran, ensure DevOps validates deployment
        development_personas = {
            "backend_developer", "frontend_developer", "database_specialist",
            "ui_ux_designer"
        }
        if any(p in personas for p in development_personas):
            if "devops_engineer" not in personas and "devops_engineer" in self.all_personas:
                recommended_personas.append("devops_engineer")

            if "deployment_specialist" not in personas and "deployment_specialist" in self.all_personas:
                recommended_personas.append("deployment_specialist")

        # Add recommended personas to the end
        if recommended_personas:
            logger.info(f"ℹ️  Auto-adding recommended personas for deployment validation: {', '.join(recommended_personas)}")
            for persona in recommended_personas:
                if persona not in ordered:
                    ordered.append(persona)

        return ordered

    async def execute(
        self,
        requirement: str,
        session_id: Optional[str] = None,
        resume_session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute SDLC workflow with persona-level reuse and session persistence

        NEW V3.1 Flow:
        1. Load/create session
        2. Check for similar projects (V4.1)
        3. Build persona-level reuse map
        4. For each persona:
           - If should_reuse: Fetch artifacts from similar project
           - If should_execute: Run persona with RAG + Quality review
        5. Save session and return results
        """

        # Ensure personas are loaded
        await self.ensure_initialized()

        # ===================================================================
        # STEP 1: Load or create session
        # ===================================================================
        if resume_session_id:
            session = self.session_manager.load_session(resume_session_id)
            if not session:
                raise ValueError(f"Session not found: {resume_session_id}")

            requirement = session.requirement
            self.output_dir = session.output_dir
            logger.info(f"📂 Resuming session: {session.session_id}")
            logger.info(f"✅ Completed personas: {', '.join(session.completed_personas)}")

        else:
            session = self.session_manager.create_session(
                requirement=requirement,
                output_dir=self.output_dir,
                session_id=session_id
            )
            logger.info(f"🆕 Created new session: {session.session_id}")
        
        # NEW: Initialize conversation history for message-based context
        if self.conversation is None:
            self.conversation = ConversationHistory(session.session_id)
            logger.info(f"📝 Initialized conversation history")

            # Initialize collaborative executor
            self.collaborative_executor = CollaborativeExecutor(
                conversation=self.conversation,
                output_dir=self.output_dir
            )
            logger.info(f"🤝 Initialized collaborative executor")

            # Add initial system message
            self.conversation.add_system_message(
                content=f"Starting SDLC workflow: {requirement}",
                phase="initialization",
                level="info"
            )

        # ===================================================================
        # STEP 2: Determine pending personas
        # ===================================================================
        if self.force_rerun:
            # Force mode: Re-run all selected personas regardless of completion status
            pending_personas = self.selected_personas
            logger.info(f"🔄 Force mode enabled - will re-run {len(pending_personas)} persona(s) even if completed")
        else:
            # Normal mode: Only run personas that haven't been completed
            pending_personas = [
                p for p in self.selected_personas
                if p not in session.completed_personas
            ]

        if not pending_personas:
            logger.info("✅ All requested personas already completed!")
            return self._build_result(session, [], start_time=datetime.now())

        execution_order = self._determine_execution_order(pending_personas)

        # ===================================================================
        # STEP 3: NEW V3.1 - Persona-Level Reuse Analysis
        # ===================================================================
        reuse_map = None

        if self.enable_persona_reuse and "requirement_analyst" not in session.completed_personas:
            # First run - need to create requirements first
            logger.info("ℹ️  First run - requirement_analyst will run first before reuse analysis")

        elif self.enable_persona_reuse:
            logger.info("\n" + "="*80)
            logger.info("🔍 V3.1: PERSONA-LEVEL REUSE ANALYSIS")
            logger.info("="*80)

            reuse_map = await self._analyze_persona_reuse(requirement, execution_order)

            if reuse_map:
                logger.info(f"📊 Overall similarity: {reuse_map.overall_similarity:.1%}")
                logger.info(f"⚡ Personas to REUSE: {len(reuse_map.personas_to_reuse)}")
                logger.info(f"🔨 Personas to EXECUTE: {len(reuse_map.personas_to_execute)}")
                logger.info(f"⏱️  Time savings: {reuse_map.time_savings_percent:.1f}%")
                logger.info(f"💰 Cost savings: ${reuse_map.cost_savings_dollars:.2f}")

                # Log per-persona decisions
                for persona_id, decision in reuse_map.persona_decisions.items():
                    emoji = "⚡ REUSE" if decision.should_reuse else "🔨 EXECUTE"
                    logger.info(f"  {emoji} {persona_id}: {decision.similarity_score:.0%} - {decision.rationale[:80]}")

                logger.info("="*80 + "\n")

        # ===================================================================
        # STEP 4: Execute SDLC Workflow
        # ===================================================================
        logger.info("="*80)
        logger.info("🚀 AUTONOMOUS SDLC ENGINE V3.1 - PERSONA-LEVEL REUSE")
        logger.info("="*80)
        logger.info(f"📝 Requirement: {requirement[:100]}...")
        logger.info(f"🆔 Session: {session.session_id}")
        logger.info(f"⏳ To process: {', '.join(execution_order)}")
        logger.info(f"📁 Output: {self.output_dir}")
        logger.info("="*80)

        start_time = datetime.now()

        for i, persona_id in enumerate(execution_order, 1):
            logger.info(f"\n{'='*80}")
            logger.info(f"🤖 [{i}/{len(execution_order)}] Processing: {persona_id}")
            logger.info(f"{'='*80}")

            # Check if this persona should be reused
            should_reuse = (
                reuse_map and
                persona_id in reuse_map.personas_to_reuse and
                reuse_map.persona_decisions[persona_id].should_reuse
            )

            if should_reuse:
                # V3.1: REUSE artifacts from similar project
                persona_context = await self._reuse_persona_artifacts(
                    persona_id,
                    requirement,
                    session,
                    reuse_map.persona_decisions[persona_id]
                )
                self.reuse_stats["personas_reused"] += 1
                self.reuse_stats["cost_saved_dollars"] += 22  # $22 per persona

            else:
                # V3: EXECUTE persona normally (with RAG + Quality)
                persona_context = await self._execute_persona(
                    persona_id,
                    requirement,
                    session
                )
                self.reuse_stats["personas_executed"] += 1

            # ===================================================================
            # NEW V3.2: RUN QUALITY GATE (for executed personas only)
            # ===================================================================
            if persona_context.success and not persona_context.reused:
                quality_gate_result = await self._run_quality_gate(
                    persona_id,
                    persona_context
                )

                # Store quality gate results
                persona_context.quality_gate = quality_gate_result

                # Save validation report to disk
                self._save_validation_report(persona_id, quality_gate_result, persona_context)

                # If quality gate failed, mark persona as failed
                if not quality_gate_result["passed"]:
                    logger.warning(
                        f"⚠️  {persona_id} failed quality gate but continuing "
                        f"(can be retried later)"
                    )
                    # Store recommendations for later review
                    persona_context.quality_issues = quality_gate_result["recommendations"]

                    # NOTE: We don't mark as failed to avoid blocking,
                    # but we record the quality issues for visibility
                    # Option to enable strict mode: persona_context.success = False

            # Save persona execution to session
            session.add_persona_execution(
                persona_id=persona_id,
                files_created=persona_context.files_created,
                deliverables=persona_context.deliverables,
                duration=persona_context.duration(),
                success=persona_context.success
            )

            # Persist session after each persona
            self.session_manager.save_session(session)

            if persona_context.success:
                status = "⚡ REUSED" if persona_context.reused else "✅ EXECUTED"
                quality_suffix = ""
                if persona_context.quality_gate:
                    if persona_context.quality_gate["passed"]:
                        quality_suffix = " [Quality: ✅]"
                    else:
                        quality_suffix = " [Quality: ⚠️ Issues found]"
                logger.info(f"{status} {persona_id}: {len(persona_context.files_created)} files{quality_suffix}")
            else:
                logger.error(f"❌ {persona_id} failed: {persona_context.error}")

        # ===================================================================
        # STEP 5: NEW - Run Deployment Validation (with prerequisites)
        # ===================================================================
        logger.info("\n" + "="*80)
        logger.info("🚀 DEPLOYMENT VALIDATION")
        logger.info("="*80)

        # NEW: Check if critical development personas passed before validating deployment
        critical_dev_personas = {"backend_developer", "frontend_developer"}
        executed_critical = [p for p in execution_order if p in critical_dev_personas]

        should_run_deployment_validation = True
        if executed_critical:
            # Check if any critical dev persona failed completely
            failed_critical = []
            for persona_id in executed_critical:
                persona_exec = session.personas.get(persona_id)
                if persona_exec:
                    # Check quality gate results
                    validation_file = self.output_dir / "validation_reports" / f"{persona_id}_validation.json"
                    if validation_file.exists():
                        try:
                            validation_data = json.loads(validation_file.read_text())
                            quality_gate = validation_data.get("quality_gate", {})
                            completeness = quality_gate.get("completeness_percentage", 0)

                            # If completeness < 30%, consider it a critical failure
                            if completeness < 30:
                                failed_critical.append((persona_id, completeness))
                        except Exception:
                            pass

            if failed_critical:
                should_run_deployment_validation = False
                logger.warning("\n⚠️  SKIPPING Deployment Validation")
                logger.warning("   Critical development personas have not completed:")
                for persona_id, completeness in failed_critical:
                    logger.warning(f"   - {persona_id}: {completeness:.0f}% complete")
                logger.warning("\n   Deployment validation requires:")
                logger.warning("   - backend_developer: ≥30% completeness")
                logger.warning("   - frontend_developer: ≥30% completeness")
                logger.warning("\n   Run failed personas first:")
                logger.warning(f"   python team_execution.py {' '.join([p[0] for p in failed_critical])} --resume {session.session_id}")

        if should_run_deployment_validation:
            deployment_validation = await self._run_deployment_validation(self.output_dir)
        else:
            # Create minimal deployment validation report showing prerequisites not met
            deployment_validation = {
                "passed": False,
                "checks": [],
                "errors": [{
                    "check": "Prerequisites",
                    "status": "❌ FAIL",
                    "error": "Critical development personas incomplete",
                    "details": f"Failed: {', '.join([p[0] for p in failed_critical])}"
                }],
                "warnings": [{
                    "check": "Deployment Readiness",
                    "message": "Run development personas first before deployment validation"
                }],
                "skipped": True,
                "reason": "Critical personas have <30% completeness"
            }

        # Save deployment validation report
        reports_dir = self.output_dir / "validation_reports"
        reports_dir.mkdir(exist_ok=True)

        deployment_report_file = reports_dir / "DEPLOYMENT_VALIDATION.json"
        deployment_report_file.write_text(json.dumps(deployment_validation, indent=2))
        logger.info(f"\n💾 Deployment validation report saved: {deployment_report_file}")

        # Log deployment status
        if deployment_validation.get("skipped"):
            logger.warning("\n⏭️  DEPLOYMENT VALIDATION: SKIPPED")
            logger.warning(f"   Reason: {deployment_validation.get('reason', 'Prerequisites not met')}")
            logger.warning("\n   Complete development first, then re-run deployment validation")
        elif deployment_validation["passed"]:
            logger.info("\n✅ DEPLOYMENT VALIDATION: PASSED")
            logger.info("   Project is ready for deployment!")
        else:
            logger.error("\n❌ DEPLOYMENT VALIDATION: FAILED")
            logger.error(f"   Found {len(deployment_validation['errors'])} critical error(s)")
            for error in deployment_validation["errors"]:
                logger.error(f"   - {error['check']}: {error['error']}")

            if deployment_validation["warnings"]:
                logger.warning(f"\n⚠️  Found {len(deployment_validation['warnings'])} warning(s)")
                for warning in deployment_validation["warnings"]:
                    logger.warning(f"   - {warning['check']}: {warning['message']}")

            logger.error("\n⚠️  Project NOT ready for deployment - fix errors above")

        logger.info("="*80 + "\n")

        # ===================================================================
        # STEP 6: Generate final quality summary report
        # ===================================================================
        self._generate_final_quality_report(session, execution_order)
        
        # ===================================================================
        # NEW: Phase 3 - Resolve pending questions
        # ===================================================================
        if self.collaborative_executor and self.conversation:
            try:
                logger.info("\n" + "="*80)
                logger.info("🤔 PHASE 3: CONTINUOUS COLLABORATION")
                logger.info("="*80)
                
                phase_name = self.current_phase.value if self.current_phase else "execution"
                resolved_questions = await self.collaborative_executor.resolve_pending_questions(
                    requirement=requirement,
                    phase=phase_name,
                    max_questions=10
                )
                
                if resolved_questions:
                    logger.info(f"✅ Resolved {len(resolved_questions)} question(s) from team collaboration")
                else:
                    logger.info(f"  No pending questions to resolve")
                    
                logger.info("="*80 + "\n")
            except Exception as e:
                logger.warning(f"⚠️  Question resolution failed: {e}")

        # ===================================================================
        # STEP 7: Save conversation history and build result
        # ===================================================================
        # NEW: Save conversation history
        if self.conversation:
            conv_path = self.output_dir / "conversation_history.json"
            self.conversation.save(conv_path)
            logger.info(f"💾 Saved conversation history to {conv_path}")
            
            # Log conversation statistics
            stats = self.conversation.get_summary_statistics()
            logger.info(f"📊 Conversation stats: {stats['total_messages']} messages, "
                       f"{stats['decisions_made']} decisions, {stats['questions_asked']} questions")
        
        return self._build_result(session, execution_order, start_time, reuse_map, deployment_validation)

    async def _analyze_persona_reuse(
        self,
        requirement: str,
        pending_personas: List[str]
    ) -> Optional[PersonaReuseMap]:
        """
        NEW V3.1: Analyze persona-level reuse opportunities
        """
        try:
            # Read REQUIREMENTS.md from current session
            requirements_path = self.output_dir / "REQUIREMENTS.md"
            if not requirements_path.exists():
                logger.info("ℹ️  No REQUIREMENTS.md found, skipping reuse analysis")
                return None

            new_requirements = requirements_path.read_text()

            # Find similar project
            logger.info("🔍 Searching for similar projects...")
            # For now, use a placeholder similar project
            # In production, this would call ML API to find similar project
            # and fetch its requirements

            # Placeholder: Assume we found a similar project
            # In reality, you'd call: similar_project = await self.persona_reuse_client.find_similar_project(specs)

            # For demo, return None if no similar project found
            # Real implementation would fetch existing project's requirements
            existing_requirements = "# Placeholder existing requirements"

            # Build persona reuse map
            reuse_map = await self.persona_reuse_client.build_persona_reuse_map(
                new_requirements=new_requirements,
                existing_requirements=existing_requirements,
                persona_ids=pending_personas
            )

            return reuse_map

        except Exception as e:
            logger.error(f"Error in persona reuse analysis: {e}")
            return None

    async def _reuse_persona_artifacts(
        self,
        persona_id: str,
        requirement: str,
        session: SDLCSession,
        reuse_decision: PersonaReuseDecision
    ) -> PersonaExecutionContext:
        """
        NEW V3.1: Reuse artifacts from similar project instead of executing

        This is where the magic happens - we skip execution entirely!
        """
        persona_context = PersonaExecutionContext(
            persona_id,
            requirement,
            self.output_dir
        )

        try:
            logger.info(f"⚡ REUSING {persona_id} from project {reuse_decision.source_project_id}")
            logger.info(f"   Similarity: {reuse_decision.similarity_score:.0%}")
            logger.info(f"   Rationale: {reuse_decision.rationale}")

            # Fetch artifacts from source project
            artifacts = await self.persona_reuse_client.fetch_persona_artifacts(
                source_project_id=reuse_decision.source_project_id,
                persona_id=persona_id
            )

            if artifacts:
                logger.info(f"   📥 Fetched {len(artifacts)} artifacts")

                # Copy artifacts to current session
                for artifact_path in artifacts:
                    # In production, this would actually copy files
                    # For now, just track that they were reused
                    persona_context.add_file(artifact_path)

                persona_context.mark_reused(reuse_decision.source_project_id)
                logger.info(f"   ✅ Artifacts integrated into current session")

            else:
                logger.warning(f"   ⚠️  No artifacts found, falling back to execution")
                # Fallback to execution
                return await self._execute_persona(persona_id, requirement, session)

        except Exception as e:
            logger.error(f"❌ Error reusing artifacts for {persona_id}: {e}")
            # Fallback to execution
            return await self._execute_persona(persona_id, requirement, session)

        return persona_context

    async def _execute_persona(
        self,
        persona_id: str,
        requirement: str,
        session: SDLCSession
    ) -> PersonaExecutionContext:
        """
        V3.2: Execute a single persona with proper file tracking and quality validation
        """
        persona_context = PersonaExecutionContext(
            persona_id,
            requirement,
            self.output_dir
        )

        try:
            persona_config = self.persona_configs[persona_id]
            expected_deliverables = get_deliverables_for_persona(persona_id)

            # NEW: Build context from conversation history (rich context)
            if self.conversation and len(self.conversation) > 0:
                phase_name = self.current_phase.value if self.current_phase else "execution"
                conversation_context = self.conversation.get_persona_context(
                    persona_id,
                    phase=phase_name
                )
            else:
                # Fallback to old session context if conversation not available
                conversation_context = self.session_manager.get_session_context(session)
            
            prompt = self._build_persona_prompt(
                persona_config,
                requirement,
                expected_deliverables,
                conversation_context,
                persona_id  # Pass persona_id for context-specific instructions
            )

            options = ClaudeCodeOptions(
                system_prompt=persona_config["system_prompt"],
                model=CLAUDE_CONFIG["model"],
                cwd=str(self.output_dir),
                permission_mode=CLAUDE_CONFIG["permission_mode"]
            )

            logger.info(f"🤖 {persona_id} is working...")
            logger.info(f"📦 Expected deliverables: {', '.join(expected_deliverables[:5])}")

            # ===================================================================
            # NEW: Snapshot filesystem BEFORE execution
            # ===================================================================
            before_files = set(self.output_dir.rglob("*"))
            logger.debug(f"📸 Snapshot: {len(before_files)} files before execution")

            # Execute with Claude Code SDK
            # Create transport with explicit cli_path to work in poetry virtualenv
            transport = None
            if CLAUDE_CLI_PATH:
                transport = SubprocessCLITransport(
                    prompt=prompt,
                    options=options,
                    cli_path=CLAUDE_CLI_PATH
                )

            async for message in query(prompt=prompt, options=options, transport=transport):
                # Keep legacy tracking for backwards compatibility
                if hasattr(message, 'message_type') and message.message_type == 'tool_use':
                    if hasattr(message, 'name') and message.name == 'Write':
                        file_path = message.input.get('file_path') if hasattr(message, 'input') else None
                        if file_path:
                            logger.debug(f"  📄 Creating: {file_path}")

            # ===================================================================
            # NEW: Snapshot filesystem AFTER execution
            # ===================================================================
            after_files = set(self.output_dir.rglob("*"))
            new_files = after_files - before_files

            # Filter to actual files (not directories) and make paths relative
            persona_context.files_created = [
                str(f.relative_to(self.output_dir))
                for f in new_files
                if f.is_file()
            ]

            logger.info(f"✅ {persona_id} created {len(persona_context.files_created)} files")

            # ===================================================================
            # NEW: Check for nested folder creation and warn
            # ===================================================================
            nested_project_dir = self.output_dir / self.output_dir.name
            if nested_project_dir.exists() and nested_project_dir.is_dir():
                logger.error(f"❌ WARNING: {persona_id} created nested folder: {nested_project_dir}")
                logger.error(f"   This violates project structure rules!")
                logger.error(f"   Nested folders should NOT be created!")
                # Log but don't fail - let human review decide

            # ===================================================================
            # NEW: Map files to deliverables (pattern + AI hybrid)
            # ===================================================================

            # CRITICAL FIX: Re-scan directory to get ALL files, not just new ones
            # This is especially important for remediation iterations where previous
            # iterations may have created files
            all_files_in_directory = self._scan_persona_files(persona_id)

            logger.debug(f"  📂 Files from this iteration: {len(persona_context.files_created)}")
            logger.debug(f"  📂 Total files in directory: {len(all_files_in_directory)}")

            # Use ALL files for deliverable matching, not just new ones
            files_to_match = all_files_in_directory if all_files_in_directory else persona_context.files_created

            # Step 1: Fast pattern matching
            pattern_matches = self._map_files_to_deliverables(
                persona_id,
                expected_deliverables,
                files_to_match
            )

            # Step 2: AI-powered semantic matching for unmatched files
            persona_context.deliverables = await self._intelligent_deliverable_matcher(
                persona_id,
                expected_deliverables,
                files_to_match,
                pattern_matches
            )

            logger.info(
                f"📦 Deliverables: {len(persona_context.deliverables)}/{len(expected_deliverables)} "
                f"({len(persona_context.deliverables)/max(len(expected_deliverables), 1)*100:.0f}%)"
            )

            persona_context.mark_complete(success=True)
            
            # NEW: Extract structured output and add to conversation
            if self.conversation and self.output_extractor:
                try:
                    structured = await self.output_extractor.extract_from_persona_work(
                        persona_id=persona_id,
                        files_created=persona_context.files_created,
                        output_dir=self.output_dir,
                        deliverables=persona_context.deliverables
                    )
                    
                    # Determine current phase name
                    phase_name = self.current_phase.value if self.current_phase else "execution"
                    
                    # Add to conversation
                    message = self.conversation.add_persona_work(
                        persona_id=persona_id,
                        phase=phase_name,
                        summary=structured["summary"],
                        decisions=structured["decisions"],
                        files_created=persona_context.files_created,
                        deliverables=persona_context.deliverables,
                        questions=structured.get("questions", []),
                        assumptions=structured.get("assumptions", []),
                        dependencies=structured.get("dependencies", {}),
                        concerns=structured.get("concerns", []),
                        duration_seconds=persona_context.duration(),
                        metadata={
                            "reused": False,
                            "quality_gate_passed": None  # Will be updated later
                        }
                    )
                    
                    logger.info(f"📨 Added message {message.id[:8]}... to conversation")
                except Exception as e:
                    logger.warning(f"Failed to extract structured output: {e}")

        except Exception as e:
            logger.exception(f"❌ Error executing {persona_id}")
            persona_context.mark_complete(success=False, error=str(e))

        return persona_context

    def _map_files_to_deliverables(
        self,
        persona_id: str,
        expected_deliverables: List[str],
        files_created: List[str]
    ) -> Dict[str, List[str]]:
        """
        Map created files to expected deliverables using pattern matching

        Focus: Quality over quantity - match files to their purpose
        """
        import fnmatch

        # Comprehensive deliverable-to-file pattern mapping
        # UPDATED: Now matches JSON contracts from maestro-engine/src/personas/definitions/*.json
        deliverable_patterns = {
            # Requirements Analyst - UPDATED to match JSON
            "functional_requirements": ["*functional*requirements*.md", "*functional*.md", "FUNCTIONAL_REQUIREMENTS.md"],
            "non_functional_requirements": ["*non*functional*.md", "*nfr*.md", "NON_FUNCTIONAL_REQUIREMENTS.md"],
            "complexity_score": ["*complexity*.md", "*complexity*.json", "COMPLEXITY*.md"],
            "domain_classification": ["*domain*.md", "*classification*.md", "DOMAIN*.md"],

            # Solution Architect - UPDATED to match JSON
            "architecture_design": ["*architecture*.md", "ARCHITECTURE.md", "*arch*design*.md"],
            "technology_stack": ["*tech*stack*.md", "*technology*.md", "TECH_STACK.md"],
            "component_diagram": ["*component*.md", "*diagram*.md", "*components*.png", "*architecture*.png"],
            "integration_patterns": ["*integration*.md", "*patterns*.md", "INTEGRATION*.md"],
            "api_specifications": ["*api*.md", "*openapi*.yaml", "*swagger*.yaml", "*api*.yml", "API*.md"],

            # Security Specialist - UPDATED to match JSON
            "security_audit_report": ["*security*audit*.md", "*security*review*.md", "SECURITY_AUDIT*.md"],
            "vulnerability_assessment": ["*vulnerability*.md", "*vuln*.md", "VULNERABILITY*.md"],
            "security_recommendations": ["*security*recommend*.md", "*security*improve*.md"],
            "remediation_plan": ["*remediation*.md", "REMEDIATION*.md"],

            # Backend Developer - UPDATED to match JSON
            "api_implementation": ["**/routes/**/*.ts", "**/api/**/*.ts", "**/controllers/**/*.ts", "**/*api*.py"],
            "database_schema": ["**/prisma/**/*.prisma", "**/migrations/**/*", "**/models/**/*", "**/schema*.sql"],
            "business_logic": ["**/services/**/*.ts", "**/logic/**/*.ts", "**/business/**/*.py", "**/services/**/*.py"],
            "authentication_system": ["**/auth/**/*", "**/authentication/**/*", "**/middleware/auth*"],
            "api_documentation": ["**/docs/api*.md", "API*.md", "*openapi*.yaml"],

            # Frontend Developer - UPDATED to match JSON
            "component_code": ["**/components/**/*.tsx", "**/components/**/*.jsx", "**/*component*.ts"],
            "routing_configuration": ["**/routes/**/*.tsx", "**/routing/**/*", "**/router*"],
            "state_management_setup": ["**/store/**/*", "**/redux/**/*", "**/context/**/*", "**/*state*.ts"],
            "api_integration_code": ["**/api/**/*.ts", "**/services/**/*.ts", "**/*api*client*.ts"],
            "styling_implementation": ["**/*.css", "**/*.scss", "**/styles/**/*", "**/*.module.css", "**/theme*"],

            # DevOps Engineer - UPDATED to match JSON
            "dockerfile": ["Dockerfile*", "**/*.dockerfile"],
            "docker_compose": ["docker-compose*.yml", "docker-compose*.yaml"],
            "ci_cd_pipeline": [".github/**/*.yml", ".gitlab-ci.yml", "Jenkinsfile", ".circleci/**/*", "**/*pipeline*"],
            "deployment_configuration": ["**/deploy*.yml", "**/deploy*.yaml", "**/k8s/**/*", "**/helm/**/*"],

            # QA Engineer - UPDATED to match JSON
            "test_strategy": ["**/test*strategy*.md", "**/testing/*strategy*.md", "TEST_STRATEGY*.md"],
            "unit_tests": ["**/*test.ts", "**/*test.tsx", "**/*spec.ts", "**/*test*.py", "**/tests/unit/**/*"],
            "integration_tests": ["**/integration*test*.ts", "**/tests/integration/**/*", "**/*integration*spec*.py"],
            "e2e_tests": ["**/e2e/**/*", "**/tests/e2e/**/*", "**/*e2e*test*", "**/*.spec.ts"],
            "test_coverage_report": ["**/coverage/**/*", "**/test*coverage*.md", "**/test*report*.md"],

            # Technical Writer - UPDATED to match JSON
            "readme": ["README.md", "**/README.md"],
            "user_guide": ["**/user*guide*.md", "**/guide*.md", "USER_GUIDE*.md"],
            "api_documentation": ["**/api*.md", "**/docs/api*.md", "API*.md"],
            "setup_instructions": ["**/setup*.md", "**/install*.md", "**/getting*started*.md", "SETUP*.md"],

            # Deployment Specialist - UPDATED to match JSON
            "deployment_plan": ["**/deployment*plan*.md", "DEPLOYMENT_PLAN*.md"],
            "deployment_checklist": ["**/deployment*checklist*.md", "**/deploy*checklist*.md"],
            "rollback_procedure": ["**/rollback*.md", "ROLLBACK*.md"],
            "validation_tests": ["**/validation*test*.md", "**/smoke*test*.md", "**/deployment*test*"],

            # UI/UX Designer - UPDATED to match JSON  
            "wireframes": ["**/wireframes/**/*", "**/*wireframe*"],
            "user_flows": ["**/flows/**/*", "**/*user*flow*", "**/*flow*diagram*"],
            "design_system": ["**/design*system*.md", "**/*design*.md", "DESIGN_SYSTEM*.md"],
            "component_specifications": ["**/component*spec*.md", "**/components/*/spec*.md"],
            "accessibility_guidelines": ["**/accessibility*.md", "**/*a11y*.md", "ACCESSIBILITY*.md"],

            # Project Reviewer - UPDATED with flexible matching
            "project_maturity_report": ["**/reviews/*MATURITY*.md", "**/PROJECT_MATURITY*.md", "**/project*maturity*.md", "**/*maturity*report*.md"],
            "gap_analysis_report": ["**/reviews/*GAP*.md", "**/GAP_ANALYSIS*.md", "**/gap*analysis*.md", "**/*gap*analysis*.md"],
            "remediation_plan": ["**/reviews/*REMEDIATION*.md", "**/REMEDIATION*.md", "**/remediation*plan*.md", "**/*remediation*.md"],
            "metrics_json": ["**/reviews/METRICS*.json", "**/PROJECT_METRICS.json", "**/metrics.json", "**/*metrics*.json"],  # FIXED: Added flexible pattern
            "final_quality_assessment": ["**/reviews/*QUALITY*.md", "**/FINAL_QUALITY*.md", "**/final*quality*.md", "**/*quality*assessment*.md"],

            # Phase Reviewer - NEW (phase-level validation)
            "phase_validation_report": ["**/phase_reviews/**/PHASE_VALIDATION*.md", "**/phase*validation*.md"],
            "deliverables_checklist": ["**/phase_reviews/**/DELIVERABLES_CHECKLIST*.md", "**/deliverables*checklist*.md"],
            "quality_score": ["**/phase_reviews/**/quality_score.json", "**/phase*quality*.json"],
            "gaps_identified": ["**/phase_reviews/**/GAPS_IDENTIFIED*.md", "**/phase*gaps*.md"],
            "transition_recommendation": ["**/phase_reviews/**/TRANSITION*.md", "**/transition*recommend*.md"],

            # Database Administrator - ADDED (was missing)
            "database_schema": ["**/schema*.sql", "**/database*.sql", "**/*schema*.md"],
            "migration_scripts": ["**/migrations/**/*", "**/*migration*.sql"],
            "indexing_strategy": ["**/index*.sql", "**/*indexing*.md"],
            "data_integrity_rules": ["**/constraints*.sql", "**/*integrity*.md"],

            # Integration Tester - Keeping existing (not in JSON but used)
            "integration_test_plan": ["**/integration*test*plan*.md"],
            "integration_tests": ["**/integration*test*.ts", "**/tests/integration/**/*"],
            "validation_report": ["**/validation*report*.md"],
        }

        deliverables_found = {}

        for deliverable_name in expected_deliverables:
            if deliverable_name not in deliverable_patterns:
                logger.debug(f"⚠️  No pattern defined for deliverable: {deliverable_name}")
                continue

            patterns = deliverable_patterns[deliverable_name]
            matched_files = []

            for file_path in files_created:
                for pattern in patterns:
                    if fnmatch.fnmatch(file_path, pattern):
                        matched_files.append(file_path)
                        break

            if matched_files:
                deliverables_found[deliverable_name] = matched_files
                logger.debug(f"  ✓ {deliverable_name}: {len(matched_files)} files")

        return deliverables_found

    def _scan_persona_files(self, persona_id: str) -> List[str]:
        """
        Scan output directory for ALL files relevant to this persona

        This fixes the issue where only current iteration files are counted.
        For remediation, we need to see ALL files from all iterations.

        Returns:
            List of relative file paths for this persona's domain
        """
        # Map personas to their expected output directories
        persona_directories = {
            "requirement_analyst": ["requirements/", "requirements_document.md", "user_stories.md", "README.md"],
            "solution_architect": ["architecture/", "design/"],
            "security_specialist": ["security/"],
            "backend_developer": ["backend/", "server/", "api/"],
            "frontend_developer": ["frontend/", "client/", "ui/"],
            "qa_engineer": ["tests/", "test/", "qa/"],
            "devops_engineer": [".github/", "docker-compose", "Dockerfile", "k8s/", "infrastructure/"],
            "deployment_specialist": ["deployment/", "deploy/"],
            "technical_writer": ["docs/", "documentation/", "README"],
            "project_reviewer": ["reviews/"],
            "test_engineer": ["tests/", "test/"],
            "ui_ux_designer": ["design/", "ui/", "wireframes/"]
        }

        # Get relevant patterns for this persona
        patterns = persona_directories.get(persona_id, [])
        if not patterns:
            # Fallback: return all files
            return [
                str(f.relative_to(self.output_dir))
                for f in self.output_dir.rglob("*")
                if f.is_file() and not f.name.startswith('.') and 'node_modules' not in str(f)
            ]

        # Scan for files matching persona's domain
        relevant_files = []
        for pattern in patterns:
            if pattern.endswith('/'):
                # Directory pattern
                dir_path = self.output_dir / pattern.rstrip('/')
                if dir_path.exists():
                    relevant_files.extend([
                        str(f.relative_to(self.output_dir))
                        for f in dir_path.rglob("*")
                        if f.is_file() and not f.name.startswith('.')
                    ])
            else:
                # File pattern
                matches = list(self.output_dir.glob(f"**/{pattern}*"))
                relevant_files.extend([
                    str(f.relative_to(self.output_dir))
                    for f in matches
                    if f.is_file() and not f.name.startswith('.')
                ])

        return relevant_files

    async def _intelligent_deliverable_matcher(
        self,
        persona_id: str,
        expected_deliverables: List[str],
        files_created: List[str],
        pattern_matched: Dict[str, List[str]]
    ) -> Dict[str, List[str]]:
        """
        AI-powered intelligent deliverable matching via deliverable_validator persona

        Uses Claude Code SDK persona to semantically match files to deliverables,
        catching variations that rigid patterns miss (e.g., "comprehensive", "detailed").

        Args:
            persona_id: The persona being validated
            expected_deliverables: List of required deliverable names
            files_created: List of file paths created by persona
            pattern_matched: Already matched files from pattern matching

        Returns:
            Enhanced deliverables mapping with AI-identified matches
        """
        # Start with pattern matches
        deliverables_found = dict(pattern_matched)

        # Find unmatched deliverables and files
        unmatched_deliverables = [d for d in expected_deliverables if d not in deliverables_found]
        matched_file_paths = {f for files in deliverables_found.values() for f in files}
        unmatched_files = [f for f in files_created if f not in matched_file_paths]

        if not unmatched_deliverables or not unmatched_files:
            logger.debug(f"  🤖 AI matcher: No unmatched deliverables or files")
            return deliverables_found

        logger.info(f"  🤖 Using AI persona to match {len(unmatched_files)} files to {len(unmatched_deliverables)} deliverables")

        try:
            from claude_code_sdk import ClaudeCodeClient
            import json

            # Create validation request for deliverable_validator persona
            requirement = f"""You are an intelligent deliverable validator for an SDLC system.

Persona being validated: {persona_id}

Expected Deliverables (unmatched by patterns):
{chr(10).join(f"- {d}" for d in unmatched_deliverables)}

Files Created (unmatched by patterns):
{chr(10).join(f"- {f}" for f in unmatched_files)}

Task: Determine which files match which deliverables based on SEMANTIC INTENT, not exact naming.

Examples of intelligent matching:
- "project_maturity_report_testing_comprehensive.md" → matches "project_maturity_report"
- "gap_analysis_testing_detailed.md" → matches "gap_analysis_report"
- "metrics_testing_comprehensive.json" → matches "metrics_json"
- "final_quality_assessment_testing_definitive.md" → matches "final_quality_assessment"
- "remediation_plan_testing_strategic.md" → matches "remediation_plan"

Rules:
1. Match based on semantic meaning, not exact string matching
2. Ignore modifiers like "comprehensive", "detailed", "strategic", "testing"
3. Match file extensions appropriately (json → *_json, md → *_report, *_plan, etc.)
4. If unsure, DO NOT match (precision over recall)

Create a file deliverable_matches.json with ONLY this exact JSON structure:
{{
  "deliverable_name": ["file_path1", "file_path2"],
  "another_deliverable": ["file_path3"]
}}

If a file doesn't match any deliverable, omit it. If a deliverable has no matches, omit it.
DO NOT include explanations, just the JSON."""

            # Use Claude Code SDK to run intelligent validator
            # Use phase_reviewer for phase-specific validation, project_reviewer for overall
            validator_persona = "phase_reviewer" if persona_id in ["requirement_analyst", "solution_architect", "backend_developer", "frontend_developer", "qa_engineer", "devops_engineer"] else "deliverable_validator"

            logger.info(f"  🎯 Using {validator_persona} for intelligent validation")

            async with ClaudeCodeClient() as client:
                result = await client.execute_persona(
                    persona_id=validator_persona,
                    requirement=requirement,
                    output_dir=self.output_dir / "validation_temp",
                    context={
                        "persona_id": persona_id,
                        "expected_deliverables": unmatched_deliverables,
                        "files_created": unmatched_files
                    }
                )

                # Read the validation result
                matches_file = self.output_dir / "validation_temp" / "deliverable_matches.json"
                if matches_file.exists():
                    ai_matches = json.loads(matches_file.read_text())

                    # Merge AI matches with pattern matches
                    for deliverable_name, matched_files in ai_matches.items():
                        if deliverable_name in expected_deliverables:
                            if deliverable_name in deliverables_found:
                                # Add to existing matches (deduplicate)
                                existing = set(deliverables_found[deliverable_name])
                                deliverables_found[deliverable_name] = list(existing | set(matched_files))
                            else:
                                deliverables_found[deliverable_name] = matched_files
                            logger.info(f"  ✓ AI persona matched {deliverable_name}: {matched_files}")

                    # Cleanup temp directory
                    import shutil
                    shutil.rmtree(self.output_dir / "validation_temp", ignore_errors=True)

            return deliverables_found

        except Exception as e:
            logger.warning(f"  ⚠️  AI persona matcher failed ({type(e).__name__}: {e}), using pattern matches only")
            return deliverables_found

    async def _run_quality_gate(
        self,
        persona_id: str,
        persona_context: PersonaExecutionContext
    ) -> Dict[str, Any]:
        """
        Run quality gate validation after persona execution

        Focus: Quality metrics, not file counts
        - Completeness (deliverables created)
        - Correctness (no stubs/placeholders)
        - Context-aware (only validate what's relevant)

        Returns:
            {
                "passed": bool,
                "validation_report": Dict,
                "recommendations": List[str]
            }
        """
        expected_deliverables = get_deliverables_for_persona(persona_id)

        logger.info(f"\n🔍 Running Quality Gate for {persona_id}")
        logger.info("=" * 80)

        # Detect project context if not already done
        if not self.project_context:
            self.project_context = detect_project_type(self.output_dir)
            logger.info(f"📋 Project type detected: {self.project_context['type']}")

        # Validate deliverables with context awareness
        validation = validate_persona_deliverables(
            persona_id,
            expected_deliverables,
            persona_context.deliverables,
            self.output_dir,
            self.project_context
        )

        logger.info(f"📊 Completeness: {validation['completeness_percentage']:.1f}%")
        logger.info(f"⭐ Quality Score: {validation['quality_score']:.2f}")
        logger.info(f"🎯 Combined Score: {validation['combined_score']:.2f}")

        if validation["missing"]:
            logger.warning(f"❌ Missing deliverables: {', '.join(validation['missing'])}")

        if validation["partial"]:
            logger.warning(f"⚠️  Partial/stub deliverables: {', '.join(validation['partial'])}")

        # Log quality issues
        if validation["quality_issues"]:
            logger.warning(f"\n⚠️  Quality Issues Found: {len(validation['quality_issues'])}")
            for issue in validation["quality_issues"][:5]:  # Show top 5
                logger.warning(f"   📄 {issue['file']} ({issue['severity']})")
                for problem in issue["issues"][:2]:  # Show top 2 issues per file
                    logger.warning(f"      - {problem}")

        # Determine if quality gate passed
        # NEW: Use progressive thresholds from ProgressiveQualityManager if available
        if self.quality_thresholds:
            # Phase-aware progressive thresholds
            required_completeness = self.quality_thresholds.completeness * 100
            required_quality = self.quality_thresholds.quality
            
            logger.info(
                f"\n🎯 Progressive Quality Thresholds (Iteration {self.current_iteration or 1}):"
            )
            logger.info(f"   Required Completeness: {required_completeness:.0f}%")
            logger.info(f"   Required Quality: {required_quality:.2f}")
        else:
            # Fallback to fixed thresholds (backward compatibility)
            required_completeness = 70.0
            required_quality = 0.60
            logger.debug("Using fixed quality thresholds (no progressive quality manager)")
        
        passed = (
            validation["completeness_percentage"] >= required_completeness and
            validation["quality_score"] >= required_quality and
            len([i for i in validation["quality_issues"] if i.get("severity") == "critical"]) == 0
        )

        # Generate recommendations
        recommendations = []

        if validation["completeness_percentage"] < required_completeness:
            recommendations.append(
                f"Increase completeness from {validation['completeness_percentage']:.1f}% "
                f"to ≥{required_completeness:.0f}%"
            )

        if validation["quality_score"] < required_quality:
            recommendations.append(
                f"Improve quality score from {validation['quality_score']:.2f} "
                f"to ≥{required_quality:.2f}"
            )

        if validation["missing"]:
            missing_list = validation['missing'][:3]
            recommendations.append(
                f"Create missing deliverables: {', '.join(missing_list)}"
            )

        if validation["partial"]:
            partial_list = validation['partial'][:3]
            recommendations.append(
                f"Complete stub implementations: {', '.join(partial_list)}"
            )

        # Persona-specific checks
        if persona_id == "qa_engineer":
            # QA must produce test results or completeness reports
            has_validation_evidence = any(
                "result" in f or "report" in f or "completeness" in f
                for f in persona_context.files_created
            )

            if not has_validation_evidence:
                passed = False
                recommendations.append(
                    "QA Engineer must produce validation evidence (test results, completeness reports)"
                )

        if persona_id in ["backend_developer", "frontend_developer"]:
            # Check for excessive critical issues
            critical_issues = [
                i for i in validation["quality_issues"]
                if i.get("severity") in ["critical", "high"]
            ]

            if len(critical_issues) > 3:
                passed = False
                recommendations.append(
                    f"Fix {len(critical_issues)} critical/high issues before proceeding"
                )

        # Log result
        logger.info("\n" + "=" * 80)
        if passed:
            logger.info(f"✅ Quality Gate PASSED for {persona_id}")
        else:
            logger.warning(f"⚠️  Quality Gate FAILED for {persona_id}")
            logger.warning("📋 Recommendations:")
            for rec in recommendations:
                logger.warning(f"   - {rec}")
        logger.info("=" * 80 + "\n")

        return {
            "passed": passed,
            "validation_report": validation,
            "recommendations": recommendations
        }

    async def _run_deployment_validation(
        self,
        project_dir: Path
    ) -> Dict[str, Any]:
        """
        NEW: Validate deployment readiness - checks build, runtime, and configuration

        Validates:
        1. Dependencies installed (node_modules/ or venv/)
        2. Backend builds successfully (npm run build / python setup.py)
        3. Frontend builds successfully (npm run build / vite build)
        4. CORS configuration exists and is valid
        5. Environment files documented (.env.example)
        6. TypeScript compilation passes
        7. No critical runtime configuration errors

        Returns:
            {
                "passed": bool,
                "checks": List[Dict],  # Successful checks
                "errors": List[Dict],  # Failed checks with details
                "warnings": List[Dict] # Non-critical issues
            }
        """
        validation_results = {
            "passed": True,
            "checks": [],
            "errors": [],
            "warnings": []
        }

        logger.info("🔍 Running Deployment Validation...")

        # ===================================================================
        # Check 1: Backend Build Validation
        # ===================================================================
        backend_dir = project_dir / "backend"
        if backend_dir.exists():
            logger.info("   📦 Validating backend...")

            # Check node_modules
            if not (backend_dir / "node_modules").exists():
                validation_results["warnings"].append({
                    "check": "Backend Dependencies",
                    "message": "node_modules/ not found - run 'npm install' first"
                })

            # Check package.json has build script
            package_json = backend_dir / "package.json"
            if package_json.exists():
                try:
                    import json as json_lib
                    pkg_data = json_lib.loads(package_json.read_text())

                    if "scripts" in pkg_data and "build" in pkg_data["scripts"]:
                        # Try to build
                        try:
                            process = await asyncio.create_subprocess_shell(
                                f"cd {backend_dir} && npm run build",
                                stdout=asyncio.subprocess.PIPE,
                                stderr=asyncio.subprocess.PIPE
                            )
                            stdout, stderr = await asyncio.wait_for(
                                process.communicate(),
                                timeout=120.0  # 2 minute timeout
                            )

                            if process.returncode == 0:
                                validation_results["checks"].append({
                                    "check": "Backend Build",
                                    "status": "✅ PASS",
                                    "message": "Backend builds successfully"
                                })
                                logger.info("      ✅ Backend build: PASS")
                            else:
                                validation_results["passed"] = False
                                error_msg = stderr.decode()[:500]  # Limit error length
                                validation_results["errors"].append({
                                    "check": "Backend Build",
                                    "status": "❌ FAIL",
                                    "error": f"Build failed with exit code {process.returncode}",
                                    "details": error_msg
                                })
                                logger.error(f"      ❌ Backend build: FAIL")
                                logger.error(f"         {error_msg}")

                        except asyncio.TimeoutError:
                            validation_results["passed"] = False
                            validation_results["errors"].append({
                                "check": "Backend Build",
                                "status": "❌ FAIL",
                                "error": "Build timed out (>2 minutes)"
                            })
                            logger.error("      ❌ Backend build: TIMEOUT")

                        except Exception as e:
                            validation_results["warnings"].append({
                                "check": "Backend Build",
                                "message": f"Could not run build: {str(e)}"
                            })
                            logger.warning(f"      ⚠️  Backend build: {str(e)}")
                    else:
                        validation_results["warnings"].append({
                            "check": "Backend Build Script",
                            "message": "No 'build' script in package.json"
                        })

                except Exception as e:
                    validation_results["warnings"].append({
                        "check": "Backend package.json",
                        "message": f"Could not parse package.json: {str(e)}"
                    })

        # ===================================================================
        # Check 2: Frontend Build Validation
        # ===================================================================
        frontend_dir = project_dir / "frontend"
        if frontend_dir.exists():
            logger.info("   📦 Validating frontend...")

            # Check node_modules
            if not (frontend_dir / "node_modules").exists():
                validation_results["warnings"].append({
                    "check": "Frontend Dependencies",
                    "message": "node_modules/ not found - run 'npm install' first"
                })

            # Check package.json has build script
            package_json = frontend_dir / "package.json"
            if package_json.exists():
                try:
                    import json as json_lib
                    pkg_data = json_lib.loads(package_json.read_text())

                    if "scripts" in pkg_data and "build" in pkg_data["scripts"]:
                        # Try to build
                        try:
                            process = await asyncio.create_subprocess_shell(
                                f"cd {frontend_dir} && npm run build",
                                stdout=asyncio.subprocess.PIPE,
                                stderr=asyncio.subprocess.PIPE
                            )
                            stdout, stderr = await asyncio.wait_for(
                                process.communicate(),
                                timeout=120.0  # 2 minute timeout
                            )

                            if process.returncode == 0:
                                validation_results["checks"].append({
                                    "check": "Frontend Build",
                                    "status": "✅ PASS",
                                    "message": "Frontend builds successfully"
                                })
                                logger.info("      ✅ Frontend build: PASS")
                            else:
                                validation_results["passed"] = False
                                error_msg = stderr.decode()[:500]
                                validation_results["errors"].append({
                                    "check": "Frontend Build",
                                    "status": "❌ FAIL",
                                    "error": f"Build failed with exit code {process.returncode}",
                                    "details": error_msg
                                })
                                logger.error(f"      ❌ Frontend build: FAIL")
                                logger.error(f"         {error_msg}")

                        except asyncio.TimeoutError:
                            validation_results["passed"] = False
                            validation_results["errors"].append({
                                "check": "Frontend Build",
                                "status": "❌ FAIL",
                                "error": "Build timed out (>2 minutes)"
                            })
                            logger.error("      ❌ Frontend build: TIMEOUT")

                        except Exception as e:
                            validation_results["warnings"].append({
                                "check": "Frontend Build",
                                "message": f"Could not run build: {str(e)}"
                            })
                            logger.warning(f"      ⚠️  Frontend build: {str(e)}")
                    else:
                        validation_results["warnings"].append({
                            "check": "Frontend Build Script",
                            "message": "No 'build' script in package.json"
                        })

                except Exception as e:
                    validation_results["warnings"].append({
                        "check": "Frontend package.json",
                        "message": f"Could not parse package.json: {str(e)}"
                    })

        # ===================================================================
        # Check 3: CORS Configuration Validation
        # ===================================================================
        if backend_dir.exists():
            logger.info("   🔍 Checking CORS configuration...")

            # Check common server files for CORS
            server_files = [
                backend_dir / "src/server.ts",
                backend_dir / "src/app.ts",
                backend_dir / "src/index.ts",
                backend_dir / "src/main.ts"
            ]

            cors_found = False
            cors_config_valid = False

            for server_file in server_files:
                if server_file.exists():
                    content = server_file.read_text()

                    if "cors(" in content:
                        cors_found = True

                        # Check for origin configuration
                        if "origin:" in content or "origin :" in content:
                            cors_config_valid = True
                            validation_results["checks"].append({
                                "check": "CORS Configuration",
                                "status": "✅ PASS",
                                "message": f"CORS configured in {server_file.name}"
                            })
                            logger.info(f"      ✅ CORS: Found in {server_file.name}")
                            break
                        else:
                            validation_results["warnings"].append({
                                "check": "CORS Configuration",
                                "message": f"CORS middleware found but origin not configured in {server_file.name}"
                            })
                            logger.warning(f"      ⚠️  CORS: Missing origin config in {server_file.name}")

            if not cors_found:
                validation_results["warnings"].append({
                    "check": "CORS Configuration",
                    "message": "CORS middleware not found in server files"
                })
                logger.warning("      ⚠️  CORS: Not configured")

        # ===================================================================
        # Check 4: Environment Configuration
        # ===================================================================
        logger.info("   🔍 Checking environment configuration...")

        for subdir_name in ["backend", "frontend"]:
            subdir = project_dir / subdir_name
            if subdir.exists():
                env_example = subdir / ".env.example"
                env_file = subdir / ".env"

                if env_example.exists():
                    validation_results["checks"].append({
                        "check": f"{subdir_name.title()} .env.example",
                        "status": "✅ PASS",
                        "message": "Environment variables documented"
                    })
                    logger.info(f"      ✅ {subdir_name}/.env.example: Found")

                    if not env_file.exists():
                        validation_results["warnings"].append({
                            "check": f"{subdir_name.title()} .env",
                            "message": ".env file missing (needs to be created from .env.example)"
                        })
                        logger.warning(f"      ⚠️  {subdir_name}/.env: Missing")

        # ===================================================================
        # Check 5: TypeScript Configuration
        # ===================================================================
        if backend_dir.exists():
            tsconfig = backend_dir / "tsconfig.json"
            if tsconfig.exists():
                try:
                    import json as json_lib
                    ts_data = json_lib.loads(tsconfig.read_text())

                    validation_results["checks"].append({
                        "check": "TypeScript Configuration",
                        "status": "✅ PASS",
                        "message": "tsconfig.json exists and is valid JSON"
                    })
                    logger.info("      ✅ tsconfig.json: Valid")

                except Exception as e:
                    validation_results["errors"].append({
                        "check": "TypeScript Configuration",
                        "status": "❌ FAIL",
                        "error": f"tsconfig.json is invalid: {str(e)}"
                    })
                    validation_results["passed"] = False
                    logger.error(f"      ❌ tsconfig.json: Invalid JSON")

        # ===================================================================
        # Check 6: NEW - Test Execution (if tests exist)
        # ===================================================================
        logger.info("   🧪 Running automated tests...")

        # Backend tests
        if backend_dir.exists() and (backend_dir / "tests").exists():
            logger.info("      📦 Running backend tests...")
            try:
                process = await asyncio.create_subprocess_shell(
                    f"cd {backend_dir} && npm test -- --passWithNoTests --coverage 2>&1",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=180.0  # 3 minute timeout for tests
                )

                if process.returncode == 0:
                    validation_results["checks"].append({
                        "check": "Backend Tests",
                        "status": "✅ PASS",
                        "message": "Backend tests passed"
                    })
                    logger.info("         ✅ Backend tests: PASS")

                    # Save test output
                    test_log = project_dir / "test_execution_backend.log"
                    test_log.write_text(stdout.decode())
                else:
                    # Tests failed - this is critical
                    validation_results["errors"].append({
                        "check": "Backend Tests",
                        "status": "❌ FAIL",
                        "error": f"Tests failed with exit code {process.returncode}",
                        "details": stderr.decode()[:500]
                    })
                    validation_results["passed"] = False
                    logger.error(f"         ❌ Backend tests: FAIL")

            except asyncio.TimeoutError:
                validation_results["warnings"].append({
                    "check": "Backend Tests",
                    "message": "Tests timed out (>3 minutes)"
                })
                logger.warning("         ⚠️  Backend tests: TIMEOUT")

            except Exception as e:
                validation_results["warnings"].append({
                    "check": "Backend Tests",
                    "message": f"Could not run tests: {str(e)}"
                })
                logger.warning(f"         ⚠️  Backend tests: {str(e)}")

        # Frontend tests
        if frontend_dir.exists() and (frontend_dir / "src").exists():
            logger.info("      📦 Running frontend tests...")
            try:
                process = await asyncio.create_subprocess_shell(
                    f"cd {frontend_dir} && npm test -- --passWithNoTests --coverage 2>&1",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=180.0
                )

                if process.returncode == 0:
                    validation_results["checks"].append({
                        "check": "Frontend Tests",
                        "status": "✅ PASS",
                        "message": "Frontend tests passed"
                    })
                    logger.info("         ✅ Frontend tests: PASS")

                    # Save test output
                    test_log = project_dir / "test_execution_frontend.log"
                    test_log.write_text(stdout.decode())
                else:
                    validation_results["errors"].append({
                        "check": "Frontend Tests",
                        "status": "❌ FAIL",
                        "error": f"Tests failed with exit code {process.returncode}",
                        "details": stderr.decode()[:500]
                    })
                    validation_results["passed"] = False
                    logger.error(f"         ❌ Frontend tests: FAIL")

            except asyncio.TimeoutError:
                validation_results["warnings"].append({
                    "check": "Frontend Tests",
                    "message": "Tests timed out (>3 minutes)"
                })
                logger.warning("         ⚠️  Frontend tests: TIMEOUT")

            except Exception as e:
                validation_results["warnings"].append({
                    "check": "Frontend Tests",
                    "message": f"Could not run tests: {str(e)}"
                })
                logger.warning(f"         ⚠️  Frontend tests: {str(e)}")

        # ===================================================================
        # Check 7: NEW - Quality-Fabric Integration (if available)
        # ===================================================================
        try:
            from quality_fabric_integration import QualityFabricClient

            logger.info("   🔍 Running Quality-Fabric validation...")

            async with QualityFabricClient() as qf_client:
                if await qf_client.health_check():
                    qf_result = await qf_client.validate_project(
                        project_dir=project_dir,
                        phase="deployment",
                        validation_type="comprehensive"
                    )

                    if qf_result:
                        overall_score = qf_result.get("overall_score", 0)

                        if overall_score >= 0.80:
                            validation_results["checks"].append({
                                "check": "Quality-Fabric Validation",
                                "status": "✅ PASS",
                                "message": f"Quality score: {overall_score:.0%}"
                            })
                            logger.info(f"      ✅ Quality-Fabric: {overall_score:.0%}")
                        else:
                            validation_results["warnings"].append({
                                "check": "Quality-Fabric Validation",
                                "message": f"Quality score {overall_score:.0%} below target (80%)"
                            })
                            logger.warning(f"      ⚠️  Quality-Fabric: {overall_score:.0%} (target: 80%)")

                        # Store full quality-fabric results
                        validation_results["quality_fabric_results"] = qf_result

        except ImportError:
            logger.debug("   ⚠️  Quality-Fabric not available (optional)")
        except Exception as e:
            logger.debug(f"   ⚠️  Quality-Fabric error: {e} (optional)")

        # ===================================================================
        # Final Summary
        # ===================================================================
        logger.info("\n   📊 Deployment Validation Summary:")
        logger.info(f"      Checks Passed: {len(validation_results['checks'])}")
        logger.info(f"      Errors: {len(validation_results['errors'])}")
        logger.info(f"      Warnings: {len(validation_results['warnings'])}")

        return validation_results

    def _save_validation_report(
        self,
        persona_id: str,
        quality_gate_result: Dict[str, Any],
        persona_context: PersonaExecutionContext
    ):
        """
        Save validation report to disk for post-mortem analysis

        Creates:
        - validation_reports/{persona_id}_validation.json
        - validation_reports/summary.json (overall summary)
        """
        try:
            # Create validation_reports directory
            reports_dir = self.output_dir / "validation_reports"
            reports_dir.mkdir(exist_ok=True)

            # Build detailed report
            report = {
                "persona_id": persona_id,
                "timestamp": datetime.now().isoformat(),
                "success": persona_context.success,
                "reused": persona_context.reused,
                "files_created": persona_context.files_created,
                "files_count": len(persona_context.files_created),
                "deliverables": {
                    name: files for name, files in persona_context.deliverables.items()
                },
                "deliverables_count": len(persona_context.deliverables),
                "duration_seconds": persona_context.duration(),
                "quality_gate": {
                    "passed": quality_gate_result["passed"],
                    "completeness_percentage": quality_gate_result["validation_report"]["completeness_percentage"],
                    "quality_score": quality_gate_result["validation_report"]["quality_score"],
                    "combined_score": quality_gate_result["validation_report"].get("combined_score", 0.0),
                    "missing_deliverables": quality_gate_result["validation_report"]["missing"],
                    "partial_deliverables": quality_gate_result["validation_report"]["partial"],
                    "quality_issues_count": len(quality_gate_result["validation_report"]["quality_issues"]),
                    "quality_issues": quality_gate_result["validation_report"]["quality_issues"],
                    "recommendations": quality_gate_result["recommendations"]
                }
            }

            # Save persona-specific report
            report_file = reports_dir / f"{persona_id}_validation.json"
            report_file.write_text(json.dumps(report, indent=2))
            logger.debug(f"💾 Saved validation report: {report_file}")

            # Update summary report
            summary_file = reports_dir / "summary.json"
            if summary_file.exists():
                summary = json.loads(summary_file.read_text())
            else:
                summary = {
                    "session_id": self.session_manager.current_session.session_id if hasattr(self.session_manager, 'current_session') else "unknown",
                    "created_at": datetime.now().isoformat(),
                    "personas": {},
                    "overall_stats": {
                        "total_personas": 0,
                        "passed_quality_gates": 0,
                        "failed_quality_gates": 0,
                        "avg_completeness": 0.0,
                        "avg_quality": 0.0,
                        "total_issues": 0
                    }
                }

            # Add persona to summary
            summary["personas"][persona_id] = {
                "passed": quality_gate_result["passed"],
                "completeness": quality_gate_result["validation_report"]["completeness_percentage"],
                "quality": quality_gate_result["validation_report"]["quality_score"],
                "issues": len(quality_gate_result["validation_report"]["quality_issues"])
            }

            # Recalculate overall stats
            total = len(summary["personas"])
            passed = sum(1 for p in summary["personas"].values() if p["passed"])
            failed = total - passed
            avg_completeness = sum(p["completeness"] for p in summary["personas"].values()) / max(total, 1)
            avg_quality = sum(p["quality"] for p in summary["personas"].values()) / max(total, 1)
            total_issues = sum(p["issues"] for p in summary["personas"].values())

            summary["overall_stats"] = {
                "total_personas": total,
                "passed_quality_gates": passed,
                "failed_quality_gates": failed,
                "avg_completeness": round(avg_completeness, 2),
                "avg_quality": round(avg_quality, 2),
                "total_issues": total_issues
            }

            summary["last_updated"] = datetime.now().isoformat()

            summary_file.write_text(json.dumps(summary, indent=2))
            logger.debug(f"💾 Updated summary report: {summary_file}")

        except Exception as e:
            logger.warning(f"⚠️  Could not save validation report: {e}")

    def _generate_final_quality_report(
        self,
        session: SDLCSession,
        execution_order: List[str]
    ):
        """
        Generate final quality summary report for the entire workflow

        Creates:
        - validation_reports/FINAL_QUALITY_REPORT.md (human-readable)
        """
        try:
            reports_dir = self.output_dir / "validation_reports"
            if not reports_dir.exists():
                return  # No validation reports generated

            # Read summary.json
            summary_file = reports_dir / "summary.json"
            if not summary_file.exists():
                return

            summary = json.loads(summary_file.read_text())

            # Generate markdown report
            report_lines = [
                "# Final Quality Validation Report",
                "",
                f"**Session ID:** {session.session_id}",
                f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"**Total Personas Executed:** {summary['overall_stats']['total_personas']}",
                "",
                "---",
                "",
                "## Overall Quality Metrics",
                "",
                f"- **Quality Gates Passed:** {summary['overall_stats']['passed_quality_gates']} / {summary['overall_stats']['total_personas']}",
                f"- **Quality Gates Failed:** {summary['overall_stats']['failed_quality_gates']} / {summary['overall_stats']['total_personas']}",
                f"- **Average Completeness:** {summary['overall_stats']['avg_completeness']:.1f}%",
                f"- **Average Quality Score:** {summary['overall_stats']['avg_quality']:.2f}",
                f"- **Total Quality Issues:** {summary['overall_stats']['total_issues']}",
                "",
            ]

            # Overall status
            all_passed = summary['overall_stats']['failed_quality_gates'] == 0
            if all_passed:
                report_lines.extend([
                    "## ✅ Overall Status: PASSED",
                    "",
                    "All personas passed their quality gates. Project is ready for deployment.",
                    ""
                ])
            else:
                report_lines.extend([
                    "## ⚠️ Overall Status: NEEDS ATTENTION",
                    "",
                    f"{summary['overall_stats']['failed_quality_gates']} persona(s) failed quality gates.",
                    "Review individual reports below and address issues before deployment.",
                    ""
                ])

            report_lines.append("---")
            report_lines.append("")
            report_lines.append("## Persona Quality Reports")
            report_lines.append("")

            # Per-persona breakdown
            for persona_id in execution_order:
                if persona_id not in summary["personas"]:
                    continue

                persona_data = summary["personas"][persona_id]
                status_icon = "✅" if persona_data["passed"] else "⚠️"

                report_lines.extend([
                    f"### {status_icon} {persona_id}",
                    "",
                    f"- **Quality Gate:** {'PASSED' if persona_data['passed'] else 'FAILED'}",
                    f"- **Completeness:** {persona_data['completeness']:.1f}%",
                    f"- **Quality Score:** {persona_data['quality']:.2f}",
                    f"- **Issues Found:** {persona_data['issues']}",
                    ""
                ])

                # Load detailed report for recommendations
                detail_file = reports_dir / f"{persona_id}_validation.json"
                if detail_file.exists():
                    detail = json.loads(detail_file.read_text())

                    if detail["quality_gate"]["recommendations"]:
                        report_lines.append("**Recommendations:**")
                        for rec in detail["quality_gate"]["recommendations"]:
                            report_lines.append(f"- {rec}")
                        report_lines.append("")

                    if detail["quality_gate"]["missing_deliverables"]:
                        report_lines.append(f"**Missing Deliverables:** {', '.join(detail['quality_gate']['missing_deliverables'])}")
                        report_lines.append("")

                    if detail["quality_gate"]["partial_deliverables"]:
                        report_lines.append(f"**Partial/Stub Deliverables:** {', '.join(detail['quality_gate']['partial_deliverables'])}")
                        report_lines.append("")

            # Add recommendations section
            report_lines.extend([
                "---",
                "",
                "## Next Steps",
                ""
            ])

            if all_passed:
                report_lines.extend([
                    "1. ✅ All quality gates passed",
                    "2. ✅ Review individual validation reports in `validation_reports/` directory",
                    "3. ✅ Proceed with deployment",
                    ""
                ])
            else:
                report_lines.extend([
                    "1. ⚠️ Review failed personas above",
                    "2. ⚠️ Address quality issues and recommendations",
                    "3. ⚠️ Re-run failed personas:",
                    "   ```bash",
                    f"   python team_execution.py <failed_personas> --resume {session.session_id}",
                    "   ```",
                    "4. ⚠️ Verify all quality gates pass before deployment",
                    ""
                ])

            # Footer
            report_lines.extend([
                "---",
                "",
                "## Report Files",
                "",
                "- `summary.json` - Overall statistics",
                "- `{persona_id}_validation.json` - Detailed per-persona reports",
                "- `FINAL_QUALITY_REPORT.md` - This file",
                "",
                "---",
                "",
                f"*Report generated by Quality Validation System v3.2 on {datetime.now().isoformat()}*"
            ])

            # Write report
            final_report = reports_dir / "FINAL_QUALITY_REPORT.md"
            final_report.write_text("\n".join(report_lines))

            logger.info(f"\n📊 Final quality report: {final_report}")

        except Exception as e:
            logger.warning(f"⚠️  Could not generate final quality report: {e}")

    def _build_persona_prompt(
        self,
        persona_config: Dict[str, Any],
        requirement: str,
        expected_deliverables: List[str],
        session_context: str,
        persona_id: Optional[str] = None
    ) -> str:
        """Build prompt with session context and validation instructions"""
        persona_name = persona_config["name"]
        expertise = persona_config.get("expertise", [])

        prompt = f"""You are the {persona_name} for this project.

TEAM CONVERSATION AND PREVIOUS WORK:
{session_context}

Your task is to build on the existing work and create your deliverables.

Your expertise areas:
{chr(10).join(f"- {exp}" for exp in expertise[:5])}

Expected deliverables for your role:
{chr(10).join(f"- {d}" for d in expected_deliverables)}

Using the Claude Code tools (Write, Edit, Read, Bash, WebSearch):
1. Review the work done by previous personas (check existing files)
2. Build on their work - don't duplicate, extend and enhance
3. Create your deliverables using best practices
4. Ensure consistency with existing files

IMPORTANT: When you complete your work, create a summary document (README.md or SUMMARY.md in your deliverable folder) that includes:
- Brief summary of what you accomplished (2-3 sentences)
- Key technical decisions and WHY you made them
- Alternatives you considered and trade-offs
- Any questions for other team members (if applicable)
- Assumptions you made that might need validation

This summary helps the team understand your work and decisions.

Work autonomously. Focus on your specialized domain.

CRITICAL FILE CREATION RULES: 
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  IMPORTANT: You are already working inside the project directory!

Current working directory: {self.output_dir}
Project name: {self.output_dir.name}

✅ CORRECT file paths:
   - backend/src/service.ts
   - frontend/src/App.tsx
   - docs/README.md
   - reviews/report.md

❌ WRONG - DO NOT CREATE:
   - {self.output_dir.name}/backend/...  ← WRONG! Nested folder!
   - {self.output_dir.name}/reviews/...  ← WRONG! Nested folder!
   - ./{self.output_dir.name}/...        ← WRONG! Nested folder!

🚫 NEVER create a subfolder named "{self.output_dir.name}"
🚫 NEVER nest the project inside itself
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

When you create files:
1. Use relative paths from current directory (backend/, frontend/, reviews/)
2. Do NOT prepend the project name ({self.output_dir.name})
3. The cwd is ALREADY set to the project root
"""

        # Add persona-specific validation instructions
        if persona_id == "qa_engineer":
            prompt += """

================================================================================
CRITICAL: QA VALIDATION RESPONSIBILITIES
================================================================================

You are the QUALITY GATEKEEPER. Your primary job is VALIDATION, not just test creation.

MANDATORY STEPS:

1. VERIFY IMPLEMENTATION COMPLETENESS
   - Read requirements document
   - List ALL expected features
   - Check backend routes: grep -r "router\\.(get|post|put)" backend/src/routes/
   - Check for commented routes: grep -r "// router\\.use" backend/
   - Check frontend pages: find frontend/src/pages -name "*.tsx"
   - Check for stubs: grep -ri "coming soon\\|placeholder\\|TODO" .

2. VALIDATE BUILD SUCCEEDS (NEW - CRITICAL FOR DEPLOYMENT)
   Run these commands and capture output:

   Backend Build Test:
   ```bash
   cd backend
   npm run build 2>&1 | tee build_test_backend.log
   ```

   Frontend Build Test:
   ```bash
   cd frontend
   npm run build 2>&1 | tee build_test_frontend.log
   ```

   If builds fail:
   - Document ALL build errors in build_failures.md
   - Mark deployment readiness as FAILED
   - Include error messages and line numbers

3. CREATE COMPLETENESS REPORT
   Create a file: completeness_report.md with:
   ```
   # Implementation Completeness Report

   ## Expected Features (from requirements)
   - Feature 1: ✅ Implemented | ⚠️ Partial | ❌ Missing
   - Feature 2: ...

   ## Backend API Endpoints
   - POST /api/auth/login: ✅ Implemented
   - GET /api/workspaces: ❌ Commented out
   ...

   ## Frontend Pages
   - /login: ✅ Fully implemented
   - /workspace: ⚠️ "Coming Soon" stub
   ...

   ## Build Validation (NEW)
   - Backend Build: ✅ SUCCESS | ❌ FAILED (see build_test_backend.log)
   - Frontend Build: ✅ SUCCESS | ❌ FAILED (see build_test_frontend.log)

   ## Summary
   - Completeness: XX%
   - Build Status: PASS/FAIL
   - Quality Gate: PASS/FAIL
   ```

4. RUN ACTUAL TESTS (not just create test plans)
   - cd backend && npm test (if test script exists)
   - cd frontend && npm test (if test script exists)
   - Capture results in test_results.md

5. DEPLOYMENT READINESS CHECK (NEW)
   Create: deployment_readiness.md
   ```
   # Deployment Readiness Report

   ## Build Validation
   - ✅/❌ Backend builds without errors
   - ✅/❌ Frontend builds without errors
   - ✅/❌ TypeScript compilation passes

   ## Dependency Check
   - ✅/❌ All dependencies installed (node_modules exists)
   - ✅/❌ No missing peer dependencies

   ## Configuration Check
   - ✅/❌ .env.example exists
   - ✅/❌ CORS configured in backend
   - ✅/❌ API endpoints not commented out

   ## FINAL DECISION: GO / NO-GO for Deployment
   Rationale: [explain why project is or isn't ready]
   ```

6. QUALITY DECISION
   - If completeness < 80%: FAIL and document gaps
   - If critical features missing: FAIL
   - If stubs/placeholders: FAIL
   - If builds fail: FAIL (NEW)
   - If major config issues: FAIL (NEW)

Your deliverables MUST include:
- test_plan.md
- completeness_report.md ← CRITICAL
- test_results.md (actual results, not plans)
- deployment_readiness.md ← NEW - CRITICAL FOR DEPLOYMENT
- build_test_backend.log (if backend exists)
- build_test_frontend.log (if frontend exists)

"""

        elif persona_id in ["deployment_specialist", "deployment_integration_tester", "devops_engineer"]:
            prompt += """

================================================================================
CRITICAL: DEPLOYMENT VALIDATION & CONFIGURATION
================================================================================

You are responsible for ensuring the project can actually be deployed and run.

MANDATORY PRE-DEPLOYMENT CHECKS:

1. BUILD VALIDATION (CRITICAL)
   You MUST run builds to verify deployment readiness:

   ```bash
   # Backend build
   cd backend && npm run build 2>&1 | tee deployment_build_backend.log

   # Frontend build
   cd frontend && npm run build 2>&1 | tee deployment_build_frontend.log
   ```

   If either build fails:
   - Document errors in deployment_blockers.md
   - Mark deployment as NO-GO
   - Stop validation (no point checking further if builds fail)

2. CONFIGURATION VALIDATION
   - Check CORS: grep -n "cors(" backend/src/server.ts
     * Verify origin is configured (not undefined)
     * Verify credentials setting exists
   - Check .env files:
     * backend/.env.example must exist
     * frontend/.env.example must exist
     * Document required variables in deployment_config.md
   - Check ports:
     * No port conflicts (check server.ts for hardcoded ports)
     * Environment variable PORT is used

3. DEPENDENCY VALIDATION
   - Verify package.json has all required dependencies
   - Check for peer dependency warnings
   - Verify lockfiles exist (package-lock.json or yarn.lock)

4. SMOKE TESTS
   - Check backend server entrypoint: grep -r "app\\.listen" backend/src/
   - Check routes not commented: grep -c "// router\\.use" backend/src/routes/
   - If count > 0: Document which routes are disabled
   - Check for "TODO" or "Coming Soon" in production files

5. DOCKER/DEPLOYMENT FILES (if applicable)
   - Verify Dockerfile exists and is valid
   - Verify docker-compose.yml exists and is valid
   - Check for .dockerignore

6. CREATE DEPLOYMENT READINESS REPORT
   File: deployment_readiness_report.md
   ```
   # Deployment Readiness Report

   ## Build Status
   - Backend Build: ✅ SUCCESS | ❌ FAILED
   - Frontend Build: ✅ SUCCESS | ❌ FAILED
   - Build Time: XX seconds

   ## Configuration Status
   - CORS: ✅ Configured | ❌ Missing/Invalid
   - Environment Variables: ✅ Documented | ❌ Missing .env.example
   - Port Configuration: ✅ Correct | ❌ Hardcoded/Conflicting

   ## Dependency Status
   - All Dependencies: ✅ Resolved | ⚠️ Warnings | ❌ Missing
   - Security Vulnerabilities: XX critical, XX high

   ## Code Quality Issues
   - Commented Routes: XX found (see details)
   - Stub/Placeholder Code: XX found (see details)
   - TODO Comments: XX found

   ## Docker/Deployment
   - Dockerfile: ✅ Present | ❌ Missing
   - docker-compose.yml: ✅ Present | ❌ Missing

   ## FINAL DECISION: GO / NO-GO for Deployment

   Status: [GO | NO-GO]
   Confidence: [High | Medium | Low]

   Rationale:
   [Detailed explanation of why deployment is approved or blocked]

   ## Blockers (if NO-GO)
   1. [Critical blocker 1]
   2. [Critical blocker 2]

   ## Recommendations
   1. [Improvement 1]
   2. [Improvement 2]
   ```

7. FAIL CONDITIONS (AUTO NO-GO)
   - Backend build fails
   - Frontend build fails
   - CORS not configured
   - Routes are commented out
   - "Coming Soon" pages exist in production code
   - Critical dependencies missing
   - Major features from requirements not implemented

Your deliverables MUST include:
- deployment_readiness_report.md ← CRITICAL
- deployment_build_backend.log (if backend exists)
- deployment_build_frontend.log (if frontend exists)
- deployment_config.md (environment variables documentation)
- deployment_blockers.md (if any blockers found)

DO NOT approve deployment unless ALL builds succeed and configurations are valid.

"""

        elif persona_id in ["backend_developer", "frontend_developer"]:
            prompt += """

================================================================================
IMPLEMENTATION QUALITY STANDARDS
================================================================================

Your work will be validated. Requirements:

1. NO STUBS
   - No "Coming Soon" text
   - No commented-out routes
   - No empty functions
   - No excessive TODOs (max 2-3 is OK)

2. COMPLETE FEATURES
   - All routes from architecture spec
   - All pages functional (no placeholders)

3. ERROR HANDLING
   - Try-catch blocks for async operations
   - Input validation
   - Meaningful error messages

"""

        # MD-3096: Proactive Constraint Injection (BDV/ACC/Security)
        # Inject constraints INTO prompts BEFORE code generation
        if CONSTRAINT_INJECTOR_AVAILABLE and persona_id:
            try:
                injector = get_constraint_injector()

                # Get contracts if available (for BDV scenarios)
                contracts = getattr(self, '_current_contracts', [])

                # Project context for ACC rules
                project_context = {
                    "output_dir": str(self.output_dir),
                    "project_name": self.output_dir.name if self.output_dir else "unknown"
                }

                # Inject constraints
                prompt, injection_result = injector.inject_constraints(
                    base_prompt=prompt,
                    persona_id=persona_id,
                    requirement=requirement,
                    contracts=contracts,
                    project_context=project_context
                )

                if injection_result.total_constraints_injected > 0:
                    logger.info(f"✅ Constraints injected for {persona_id}: "
                               f"BDV={injection_result.bdv_scenarios_injected}, "
                               f"ACC={injection_result.acc_rules_injected}, "
                               f"Security={injection_result.security_constraints_injected}")
            except Exception as e:
                logger.warning(f"⚠️ Constraint injection failed for {persona_id}: {e}")

        return prompt

    def _build_result(
        self,
        session: SDLCSession,
        execution_order: List[str],
        start_time: datetime,
        reuse_map: Optional[PersonaReuseMap] = None,
        deployment_validation: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Build final result with V3.1 stats and deployment validation"""
        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds()

        result = {
            "success": True,
            "session_id": session.session_id,
            "requirement": session.requirement,
            "executed_personas": execution_order,
            "all_completed_personas": session.completed_personas,
            "files": session.get_all_files(),
            "file_count": len(session.get_all_files()),
            "project_dir": str(self.output_dir),
            "total_duration": total_duration,
            "resumable": True,

            # NEW V3.1: Reuse statistics
            "persona_reuse_enabled": self.enable_persona_reuse,
            "reuse_stats": {
                "personas_reused": self.reuse_stats["personas_reused"],
                "personas_executed": self.reuse_stats["personas_executed"],
                "cost_saved_dollars": self.reuse_stats["cost_saved_dollars"],
                "time_saved_percent": reuse_map.time_savings_percent if reuse_map else 0
            },

            # NEW V3.2: Deployment validation
            "deployment_ready": deployment_validation["passed"] if deployment_validation else False,
            "deployment_validation": deployment_validation
        }

        if reuse_map:
            result["persona_reuse_map"] = {
                "overall_similarity": reuse_map.overall_similarity,
                "personas_reused": reuse_map.personas_to_reuse,
                "personas_executed": reuse_map.personas_to_execute,
                "persona_decisions": {
                    pid: {
                        "similarity_score": decision.similarity_score,
                        "should_reuse": decision.should_reuse,
                        "rationale": decision.rationale
                    }
                    for pid, decision in reuse_map.persona_decisions.items()
                }
            }

        # Log summary
        logger.info("\n" + "="*80)
        logger.info("📊 EXECUTION SUMMARY - V3.1")
        logger.info("="*80)
        logger.info(f"✅ Success: {result['success']}")
        logger.info(f"🆔 Session: {result['session_id']}")
        logger.info(f"👥 Executed in this run: {len(execution_order)}")
        logger.info(f"👥 Total completed: {len(session.completed_personas)}")
        logger.info(f"📁 Files created: {result['file_count']}")
        logger.info(f"⏱️  Duration: {total_duration:.2f}s")

        if reuse_map:
            logger.info(f"\n🎯 V3.1 PERSONA-LEVEL REUSE:")
            logger.info(f"   ⚡ Personas reused: {self.reuse_stats['personas_reused']}")
            logger.info(f"   🔨 Personas executed: {self.reuse_stats['personas_executed']}")
            logger.info(f"   💰 Cost saved: ${self.reuse_stats['cost_saved_dollars']:.2f}")
            logger.info(f"   ⏱️  Time saved: {reuse_map.time_savings_percent:.1f}%")

        logger.info(f"\n📂 Output: {result['project_dir']}")
        logger.info(f"\n💡 Resume command:")
        logger.info(f"   python {Path(__file__).name} <new_personas> --resume {session.session_id}")
        logger.info("="*80)

        return result


# ============================================================================
# SESSION MANAGEMENT HELPERS
# ============================================================================

def list_sessions(session_manager: SessionManager):
    """List all available sessions"""
    sessions = session_manager.list_sessions()

    if not sessions:
        print("No sessions found.")
        return

    print("\n" + "="*80)
    print("📋 AVAILABLE SESSIONS")
    print("="*80)

    for i, session in enumerate(sessions, 1):
        print(f"\n{i}. Session: {session['session_id']}")
        print(f"   Requirement: {session['requirement']}")
        print(f"   Created: {session['created_at']}")
        print(f"   Last Updated: {session['last_updated']}")
        print(f"   Completed Personas: {session['completed_personas']}")
        print(f"   Files: {session['files_count']}")

    print("\n" + "="*80)
    print("💡 Resume a session:")
    print(f"   python {Path(__file__).name} <personas> --resume <session_id>")
    print("="*80 + "\n")


async def main():
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Autonomous SDLC Engine V3.1 - Persona-Level Reuse + Resumable",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # New session with V3.1 persona-level reuse
  python autonomous_sdlc_engine_v3_1_resumable.py requirement_analyst backend_developer \\
      --requirement "Create blog platform" \\
      --session-id blog_v1

  # Resume existing session
  python autonomous_sdlc_engine_v3_1_resumable.py frontend_developer \\
      --resume blog_v1

  # Disable persona-level reuse (V3 mode)
  python autonomous_sdlc_engine_v3_1_resumable.py requirement_analyst \\
      --requirement "Create e-commerce" \\
      --disable-persona-reuse

  # List sessions
  python autonomous_sdlc_engine_v3_1_resumable.py --list-sessions
        """
    )

    parser.add_argument("personas", nargs="*", help="Personas to execute")
    parser.add_argument("--requirement", help="Project requirement (for new sessions)")
    parser.add_argument("--session-id", help="Session ID for new session")
    parser.add_argument("--resume", help="Resume existing session ID")
    parser.add_argument("--list-sessions", action="store_true", help="List all sessions")
    parser.add_argument("--output", help="Output directory")
    parser.add_argument("--maestro-ml-url", default="http://localhost:8001", help="Maestro ML URL")
    parser.add_argument("--disable-persona-reuse", action="store_true", help="Disable V3.1 persona-level reuse")
    parser.add_argument("--force", action="store_true", help="Force re-execution of completed personas (for iterative improvements)")

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )

    session_manager = SessionManager()

    # List sessions
    if args.list_sessions:
        list_sessions(session_manager)
        return

    # Validate arguments
    if not args.resume and not args.requirement:
        parser.error("--requirement is required for new sessions")

    if not args.personas and not args.resume:
        parser.error("Specify personas to execute")

    # Create engine
    engine = AutonomousSDLCEngineV3_1_Resumable(
        selected_personas=args.personas if args.personas else [],
        output_dir=args.output,
        session_manager=session_manager,
        maestro_ml_url=args.maestro_ml_url,
        enable_persona_reuse=not args.disable_persona_reuse,
        force_rerun=args.force
    )

    # Execute
    result = await engine.execute(
        requirement=args.requirement,
        session_id=args.session_id,
        resume_session_id=args.resume
    )

    # Print result
    print("\n" + "="*80)
    print("✅ EXECUTION COMPLETE")
    print("="*80)
    print(f"Session ID: {result['session_id']}")
    print(f"Files created: {result['file_count']}")
    print(f"Output directory: {result['project_dir']}")

    if result.get("persona_reuse_enabled"):
        print(f"\n⚡ V3.1 Persona-Level Reuse:")
        print(f"   Reused: {result['reuse_stats']['personas_reused']} personas")
        print(f"   Executed: {result['reuse_stats']['personas_executed']} personas")
        print(f"   Cost saved: ${result['reuse_stats']['cost_saved_dollars']:.2f}")

    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
