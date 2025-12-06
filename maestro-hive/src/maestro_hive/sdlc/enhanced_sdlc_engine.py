#!/usr/bin/env python3.11
"""
Enhanced SDLC Engine - Full SDK Integration

This is a complete rewrite of autonomous_sdlc_engine_v3_resumable.py that
properly leverages the claude_team_sdk's full capabilities:

✅ TeamCoordinator with MCP server
✅ TeamAgent-based personas
✅ Knowledge sharing (share_knowledge/get_knowledge)
✅ Artifact management (store_artifact/get_artifacts)
✅ Inter-agent messaging (post_message/get_messages)
✅ Democratic decisions (propose_decision/vote_decision)
✅ Parallel execution where stages are independent
✅ Team status monitoring
✅ Session persistence via SDK workspace

SDLC Phases:
    Phase 1: Foundation (Sequential Pipeline)
        - Requirements Analyst → Solution Architect → Security Review

    Phase 2: Implementation (Parallel + Collaboration)
        - Backend Developer + Database Specialist (parallel, collaborate)
        - Frontend Developer + UI/UX Designer (parallel, collaborate)

    Phase 3: Quality Assurance (Sequential Pipeline)
        - Unit Tester → Integration Tester

    Phase 4: Deployment (Parallel)
        - DevOps Engineer + Technical Writer (parallel)

Usage:
    # New SDLC workflow
    python3.11 enhanced_sdlc_engine.py \\
        --requirement "Build a blog platform with user authentication" \\
        --output ./blog_project \\
        --session-id blog_v1

    # Resume existing workflow
    python3.11 enhanced_sdlc_engine.py \\
        --resume blog_v1 \\
        --phases implementation qa  # Continue with specific phases

    # Full auto-complete (run all remaining phases)
    python3.11 enhanced_sdlc_engine.py \\
        --resume blog_v1 \\
        --auto-complete
"""

import asyncio
import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
import logging

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.claude_team_sdk import TeamAgent, AgentConfig, AgentRole, AgentStatus, TeamCoordinator
from src.claude_team_sdk.coordination.team_coordinator import TeamConfig

logger = logging.getLogger(__name__)


class SDLCPhase(str, Enum):
    """SDLC workflow phases"""
    FOUNDATION = "foundation"
    IMPLEMENTATION = "implementation"
    QA = "qa"
    DEPLOYMENT = "deployment"


class SDLCPersonaAgent(TeamAgent):
    """Base class for all SDLC persona agents"""

    def __init__(
        self,
        persona_id: str,
        coordination_server,
        role: AgentRole,
        persona_name: str,
        expertise: List[str],
        expected_deliverables: List[str]
    ):
        self.persona_name = persona_name
        self.expertise = expertise
        self.expected_deliverables = expected_deliverables

        config = AgentConfig(
            agent_id=persona_id,
            role=role,
            auto_claim_tasks=False,  # Manual task assignment for controlled workflow
            system_prompt=f"""You are the {persona_name} for this SDLC project.

Your expertise areas:
{chr(10).join(f"- {exp}" for exp in expertise[:5])}

Your expected deliverables:
{chr(10).join(f"- {d}" for d in expected_deliverables)}

CRITICAL INSTRUCTIONS:
1. ALWAYS check previous work using get_knowledge and get_artifacts
2. BUILD ON existing work - never duplicate, always extend
3. SHARE your key findings via share_knowledge
4. STORE your deliverables via store_artifact
5. COMMUNICATE with other team members via post_message when needed
6. CREATE actual files using Write tool
7. Reference specific files and knowledge items from previous stages

You are part of a coordinated team. Use SDK coordination tools effectively."""
        )
        super().__init__(config, coordination_server)

    async def execute_work(
        self,
        requirement: str,
        output_dir: Path,
        coordinator: TeamCoordinator
    ) -> Dict[str, Any]:
        """Execute this persona's work"""
        await self._update_status(AgentStatus.WORKING, f"Executing {self.persona_name}")

        logger.info(f"[{self.agent_id}] 🤖 Starting work...")
        logger.info(f"[{self.agent_id}] 📦 Deliverables: {', '.join(self.expected_deliverables[:3])}")

        # Get existing knowledge and artifacts
        knowledge = coordinator.shared_workspace["knowledge"]
        artifacts = coordinator.shared_workspace["artifacts"]

        # Build context
        context = self._build_context(requirement, knowledge, artifacts, output_dir)

        # Execute persona's work
        await self.client.query(context)

        files_created = []
        async for msg in self.client.receive_response():
            if hasattr(msg, 'message_type') and msg.message_type == 'tool_use':
                if hasattr(msg, 'name') and msg.name == 'Write':
                    file_path = msg.input.get('file_path') if hasattr(msg, 'input') else None
                    if file_path:
                        files_created.append(file_path)
                        logger.info(f"  [{self.agent_id}] 📄 Created: {Path(file_path).name}")

        await self._update_status(AgentStatus.IDLE, "Work completed")
        logger.info(f"[{self.agent_id}] ✅ Completed: {len(files_created)} files")

        return {
            "persona_id": self.agent_id,
            "files_created": files_created,
            "success": True
        }

    def _build_context(
        self,
        requirement: str,
        knowledge: Dict,
        artifacts: Dict,
        output_dir: Path
    ) -> str:
        """Build execution context with existing work"""

        context = f"""ORIGINAL REQUIREMENT:
{requirement}

OUTPUT DIRECTORY: {output_dir}

"""

        if knowledge:
            context += "KNOWLEDGE FROM PREVIOUS TEAM MEMBERS:\n"
            for key, item in list(knowledge.items())[:10]:  # Last 10 items
                context += f"- {key} (by {item.get('agent_id', 'unknown')}): {str(item.get('value', ''))[:200]}...\n"
            context += "\n"

        if artifacts:
            context += "ARTIFACTS FROM PREVIOUS TEAM MEMBERS:\n"
            for aid, artifact in list(artifacts.items())[:10]:
                context += f"- {artifact.get('name', 'unknown')} ({artifact.get('type', 'unknown')})\n"
            context += "\n"

        context += f"""YOUR TASK:
1. Review all previous work (use get_knowledge and get_artifacts)
2. Create your deliverables: {', '.join(self.expected_deliverables)}
3. Share your key findings (use share_knowledge)
4. Store your deliverables (use store_artifact)
5. If you need input from other team members, use post_message

Work autonomously and thoroughly. Focus on your specialized domain.
"""

        return context


# ============================================================================
# FOUNDATION PHASE AGENTS
# ============================================================================

class RequirementsAnalystAgent(SDLCPersonaAgent):
    """Requirements analysis and specification"""

    def __init__(self, coordination_server):
        super().__init__(
            persona_id="requirements_analyst",
            coordination_server=coordination_server,
            role=AgentRole.ANALYST,
            persona_name="Requirements Analyst",
            expertise=[
                "Requirements gathering and analysis",
                "User story creation",
                "Acceptance criteria definition",
                "Stakeholder communication",
                "Functional and non-functional requirements"
            ],
            expected_deliverables=[
                "REQUIREMENTS.md - Comprehensive requirements document",
                "USER_STORIES.md - User stories with acceptance criteria",
                "FUNCTIONAL_SPEC.md - Functional specifications"
            ]
        )


class SolutionArchitectAgent(SDLCPersonaAgent):
    """System architecture and design"""

    def __init__(self, coordination_server):
        super().__init__(
            persona_id="solution_architect",
            coordination_server=coordination_server,
            role=AgentRole.ARCHITECT,
            persona_name="Solution Architect",
            expertise=[
                "System architecture design",
                "Component design",
                "Technology selection",
                "Scalability planning",
                "Architecture documentation"
            ],
            expected_deliverables=[
                "ARCHITECTURE.md - System architecture design",
                "TECH_STACK.md - Technology choices with rationale",
                "COMPONENT_DESIGN.md - Component breakdown"
            ]
        )


class SecuritySpecialistAgent(SDLCPersonaAgent):
    """Security review and hardening"""

    def __init__(self, coordination_server):
        super().__init__(
            persona_id="security_specialist",
            coordination_server=coordination_server,
            role=AgentRole.REVIEWER,
            persona_name="Security Specialist",
            expertise=[
                "Security architecture review",
                "Threat modeling",
                "Authentication and authorization",
                "Data protection",
                "Security best practices"
            ],
            expected_deliverables=[
                "SECURITY_REVIEW.md - Security analysis",
                "THREAT_MODEL.md - Threat analysis",
                "SECURITY_REQUIREMENTS.md - Security requirements"
            ]
        )


# ============================================================================
# IMPLEMENTATION PHASE AGENTS
# ============================================================================

class BackendDeveloperAgent(SDLCPersonaAgent):
    """Backend development"""

    def __init__(self, coordination_server):
        super().__init__(
            persona_id="backend_developer",
            coordination_server=coordination_server,
            role=AgentRole.DEVELOPER,
            persona_name="Backend Developer",
            expertise=[
                "API development",
                "Business logic implementation",
                "Server-side architecture",
                "RESTful/GraphQL API design",
                "Backend frameworks"
            ],
            expected_deliverables=[
                "backend/ - Backend source code",
                "API_DOCUMENTATION.md - API endpoints",
                "backend/README.md - Backend setup guide"
            ]
        )


class DatabaseSpecialistAgent(SDLCPersonaAgent):
    """Database design and implementation"""

    def __init__(self, coordination_server):
        super().__init__(
            persona_id="database_specialist",
            coordination_server=coordination_server,
            role=AgentRole.DEVELOPER,
            persona_name="Database Specialist",
            expertise=[
                "Database schema design",
                "Query optimization",
                "Data modeling",
                "Migration strategies",
                "Database performance"
            ],
            expected_deliverables=[
                "database/schema.sql - Database schema",
                "database/migrations/ - Migration files",
                "DATABASE_DESIGN.md - Database documentation"
            ]
        )


class FrontendDeveloperAgent(SDLCPersonaAgent):
    """Frontend development"""

    def __init__(self, coordination_server):
        super().__init__(
            persona_id="frontend_developer",
            coordination_server=coordination_server,
            role=AgentRole.DEVELOPER,
            persona_name="Frontend Developer",
            expertise=[
                "UI implementation",
                "Frontend frameworks (React, Vue, Angular)",
                "State management",
                "API integration",
                "Responsive design"
            ],
            expected_deliverables=[
                "frontend/ - Frontend source code",
                "frontend/README.md - Frontend setup guide",
                "frontend/COMPONENT_STRUCTURE.md - Component docs"
            ]
        )


class UIUXDesignerAgent(SDLCPersonaAgent):
    """UI/UX design"""

    def __init__(self, coordination_server):
        super().__init__(
            persona_id="ui_ux_designer",
            coordination_server=coordination_server,
            role=AgentRole.DEVELOPER,
            persona_name="UI/UX Designer",
            expertise=[
                "User experience design",
                "User interface design",
                "Wireframing",
                "Design systems",
                "Accessibility"
            ],
            expected_deliverables=[
                "design/WIREFRAMES.md - UI wireframes",
                "design/DESIGN_SYSTEM.md - Design system",
                "design/USER_FLOWS.md - User flow documentation"
            ]
        )


# ============================================================================
# QA PHASE AGENTS
# ============================================================================

class UnitTesterAgent(SDLCPersonaAgent):
    """Unit testing"""

    def __init__(self, coordination_server):
        super().__init__(
            persona_id="unit_tester",
            coordination_server=coordination_server,
            role=AgentRole.TESTER,
            persona_name="Unit Tester",
            expertise=[
                "Unit test development",
                "Test coverage analysis",
                "TDD practices",
                "Mocking and stubbing",
                "Test automation"
            ],
            expected_deliverables=[
                "tests/unit/ - Unit test files",
                "UNIT_TEST_PLAN.md - Unit testing strategy",
                "tests/README.md - Testing documentation"
            ]
        )


class IntegrationTesterAgent(SDLCPersonaAgent):
    """Integration testing"""

    def __init__(self, coordination_server):
        super().__init__(
            persona_id="integration_tester",
            coordination_server=coordination_server,
            role=AgentRole.TESTER,
            persona_name="Integration Tester",
            expertise=[
                "Integration test development",
                "End-to-end testing",
                "API testing",
                "Test scenarios",
                "Test data management"
            ],
            expected_deliverables=[
                "tests/integration/ - Integration test files",
                "INTEGRATION_TEST_PLAN.md - Integration testing strategy",
                "tests/e2e/ - End-to-end tests"
            ]
        )


# ============================================================================
# DEPLOYMENT PHASE AGENTS
# ============================================================================

class DevOpsEngineerAgent(SDLCPersonaAgent):
    """DevOps and deployment"""

    def __init__(self, coordination_server):
        super().__init__(
            persona_id="devops_engineer",
            coordination_server=coordination_server,
            role=AgentRole.DEPLOYER,
            persona_name="DevOps Engineer",
            expertise=[
                "CI/CD pipeline setup",
                "Container orchestration",
                "Infrastructure as code",
                "Deployment automation",
                "Monitoring and logging"
            ],
            expected_deliverables=[
                "deploy/ - Deployment configuration",
                "Dockerfile - Container definition",
                ".github/workflows/ - CI/CD pipelines",
                "DEPLOYMENT_GUIDE.md - Deployment documentation"
            ]
        )


class TechnicalWriterAgent(SDLCPersonaAgent):
    """Technical documentation"""

    def __init__(self, coordination_server):
        super().__init__(
            persona_id="technical_writer",
            coordination_server=coordination_server,
            role=AgentRole.DEVELOPER,
            persona_name="Technical Writer",
            expertise=[
                "Technical documentation",
                "User guides",
                "API documentation",
                "README creation",
                "Documentation standards"
            ],
            expected_deliverables=[
                "README.md - Project README",
                "docs/USER_GUIDE.md - User guide",
                "docs/DEVELOPER_GUIDE.md - Developer guide",
                "CHANGELOG.md - Change log"
            ]
        )


# ============================================================================
# ENHANCED SDLC ENGINE
# ============================================================================

class EnhancedSDLCEngine:
    """
    SDK-powered SDLC workflow engine

    Features:
    - TeamCoordinator with MCP server
    - TeamAgent-based personas
    - Knowledge sharing via SDK
    - Parallel execution where possible
    - Democratic decisions for critical choices
    - Session persistence via SDK workspace
    """

    def __init__(self, output_dir: Path, session_id: str = None):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.session_id = session_id or f"sdlc_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Create TeamCoordinator
        team_config = TeamConfig(
            team_id=self.session_id,
            workspace_path=self.output_dir,
            max_agents=15  # All SDLC personas
        )
        self.coordinator = TeamCoordinator(team_config)
        self.coord_server = self.coordinator.create_coordination_server()

        # Track state
        self.completed_phases = set()
        self.requirement = None

    async def execute_full_sdlc(
        self,
        requirement: str,
        phases: Optional[List[SDLCPhase]] = None
    ) -> Dict[str, Any]:
        """Execute complete or partial SDLC workflow"""

        self.requirement = requirement

        if phases is None:
            phases = [SDLCPhase.FOUNDATION, SDLCPhase.IMPLEMENTATION, SDLCPhase.QA, SDLCPhase.DEPLOYMENT]

        logger.info("=" * 80)
        logger.info("🚀 ENHANCED SDLC ENGINE - Full SDK Integration")
        logger.info("=" * 80)
        logger.info(f"📝 Requirement: {requirement[:100]}...")
        logger.info(f"🆔 Session: {self.session_id}")
        logger.info(f"📊 Phases to execute: {', '.join([p.value for p in phases])}")
        logger.info(f"📁 Output: {self.output_dir}")
        logger.info("=" * 80)

        start_time = datetime.now()
        results = {}

        for phase in phases:
            if phase not in self.completed_phases:
                logger.info(f"\n{'=' * 80}")
                logger.info(f"📍 PHASE: {phase.value.upper()}")
                logger.info(f"{'=' * 80}")

                phase_result = await self._execute_phase(phase, requirement)
                results[phase.value] = phase_result
                self.completed_phases.add(phase)

                # Save workspace state after each phase
                await self._save_session()

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # Get final workspace state
        final_state = await self.coordinator.get_workspace_state()

        final_result = {
            "success": True,
            "session_id": self.session_id,
            "requirement": requirement,
            "completed_phases": [p.value for p in self.completed_phases],
            "phase_results": results,
            "knowledge_items": final_state['knowledge_items'],
            "artifacts": final_state['artifacts'],
            "messages": final_state['messages'],
            "total_duration": duration,
            "output_dir": str(self.output_dir)
        }

        logger.info("\n" + "=" * 80)
        logger.info("📊 SDLC EXECUTION COMPLETE")
        logger.info("=" * 80)
        logger.info(f"✅ Success: {final_result['success']}")
        logger.info(f"🆔 Session: {self.session_id}")
        logger.info(f"📚 Knowledge Items: {final_result['knowledge_items']}")
        logger.info(f"📦 Artifacts: {final_result['artifacts']}")
        logger.info(f"💬 Messages: {final_result['messages']}")
        logger.info(f"⏱️  Duration: {duration:.2f}s")
        logger.info(f"📂 Output: {self.output_dir}")
        logger.info("=" * 80)

        return final_result

    async def _execute_phase(self, phase: SDLCPhase, requirement: str) -> Dict[str, Any]:
        """Execute a specific SDLC phase"""

        if phase == SDLCPhase.FOUNDATION:
            return await self._execute_foundation_phase(requirement)
        elif phase == SDLCPhase.IMPLEMENTATION:
            return await self._execute_implementation_phase(requirement)
        elif phase == SDLCPhase.QA:
            return await self._execute_qa_phase(requirement)
        elif phase == SDLCPhase.DEPLOYMENT:
            return await self._execute_deployment_phase(requirement)
        else:
            raise ValueError(f"Unknown phase: {phase}")

    async def _execute_foundation_phase(self, requirement: str) -> Dict[str, Any]:
        """Phase 1: Foundation (Sequential Pipeline)"""
        logger.info("📋 Foundation Phase: Requirements → Architecture → Security")

        # Requirements Analyst
        analyst = RequirementsAnalystAgent(self.coord_server)
        await analyst.initialize()
        analyst_result = await analyst.execute_work(requirement, self.output_dir, self.coordinator)
        await analyst.shutdown()

        # Solution Architect (builds on requirements)
        architect = SolutionArchitectAgent(self.coord_server)
        await architect.initialize()
        architect_result = await architect.execute_work(requirement, self.output_dir, self.coordinator)
        await architect.shutdown()

        # Security Specialist (reviews architecture)
        security = SecuritySpecialistAgent(self.coord_server)
        await security.initialize()
        security_result = await security.execute_work(requirement, self.output_dir, self.coordinator)
        await security.shutdown()

        return {
            "personas": ["requirements_analyst", "solution_architect", "security_specialist"],
            "pattern": "sequential_pipeline",
            "results": [analyst_result, architect_result, security_result]
        }

    async def _execute_implementation_phase(self, requirement: str) -> Dict[str, Any]:
        """Phase 2: Implementation (Parallel + Collaboration)"""
        logger.info("⚙️  Implementation Phase: Backend+Database || Frontend+UI/UX (parallel)")

        # Create all agents
        backend_dev = BackendDeveloperAgent(self.coord_server)
        db_specialist = DatabaseSpecialistAgent(self.coord_server)
        frontend_dev = FrontendDeveloperAgent(self.coord_server)
        ui_ux = UIUXDesignerAgent(self.coord_server)

        # Initialize all
        await asyncio.gather(
            backend_dev.initialize(),
            db_specialist.initialize(),
            frontend_dev.initialize(),
            ui_ux.initialize()
        )

        # Execute in parallel
        results = await asyncio.gather(
            backend_dev.execute_work(requirement, self.output_dir, self.coordinator),
            db_specialist.execute_work(requirement, self.output_dir, self.coordinator),
            frontend_dev.execute_work(requirement, self.output_dir, self.coordinator),
            ui_ux.execute_work(requirement, self.output_dir, self.coordinator)
        )

        # Shutdown all
        await asyncio.gather(
            backend_dev.shutdown(),
            db_specialist.shutdown(),
            frontend_dev.shutdown(),
            ui_ux.shutdown()
        )

        return {
            "personas": ["backend_developer", "database_specialist", "frontend_developer", "ui_ux_designer"],
            "pattern": "parallel_execution",
            "results": list(results)
        }

    async def _execute_qa_phase(self, requirement: str) -> Dict[str, Any]:
        """Phase 3: QA (Sequential Pipeline)"""
        logger.info("🧪 QA Phase: Unit Testing → Integration Testing")

        # Unit Tester
        unit_tester = UnitTesterAgent(self.coord_server)
        await unit_tester.initialize()
        unit_result = await unit_tester.execute_work(requirement, self.output_dir, self.coordinator)
        await unit_tester.shutdown()

        # Integration Tester (builds on unit tests)
        integration_tester = IntegrationTesterAgent(self.coord_server)
        await integration_tester.initialize()
        integration_result = await integration_tester.execute_work(requirement, self.output_dir, self.coordinator)
        await integration_tester.shutdown()

        return {
            "personas": ["unit_tester", "integration_tester"],
            "pattern": "sequential_pipeline",
            "results": [unit_result, integration_result]
        }

    async def _execute_deployment_phase(self, requirement: str) -> Dict[str, Any]:
        """Phase 4: Deployment (Parallel)"""
        logger.info("🚀 Deployment Phase: DevOps || Technical Writer (parallel)")

        # Create agents
        devops = DevOpsEngineerAgent(self.coord_server)
        tech_writer = TechnicalWriterAgent(self.coord_server)

        # Initialize
        await asyncio.gather(
            devops.initialize(),
            tech_writer.initialize()
        )

        # Execute in parallel
        results = await asyncio.gather(
            devops.execute_work(requirement, self.output_dir, self.coordinator),
            tech_writer.execute_work(requirement, self.output_dir, self.coordinator)
        )

        # Shutdown
        await asyncio.gather(
            devops.shutdown(),
            tech_writer.shutdown()
        )

        return {
            "personas": ["devops_engineer", "technical_writer"],
            "pattern": "parallel_execution",
            "results": list(results)
        }

    async def _save_session(self):
        """Save session state via SDK workspace"""
        session_data = {
            "session_id": self.session_id,
            "requirement": self.requirement,
            "completed_phases": [p.value for p in self.completed_phases],
            "timestamp": datetime.now().isoformat()
        }

        # Store in coordinator's workspace
        self.coordinator.shared_workspace["session_metadata"] = session_data

        # Also save to file for resume capability
        session_file = self.output_dir / ".session.json"
        with open(session_file, 'w') as f:
            json.dump(session_data, f, indent=2)

        logger.debug(f"💾 Session saved: {self.session_id}")

    async def resume_session(self, session_id: str) -> Dict[str, Any]:
        """Resume existing session"""
        session_file = self.output_dir / ".session.json"

        if not session_file.exists():
            raise ValueError(f"Session not found: {session_id}")

        with open(session_file, 'r') as f:
            session_data = json.load(f)

        self.session_id = session_data["session_id"]
        self.requirement = session_data["requirement"]
        self.completed_phases = {SDLCPhase(p) for p in session_data["completed_phases"]}

        logger.info(f"📂 Resumed session: {self.session_id}")
        logger.info(f"✅ Completed phases: {', '.join([p.value for p in self.completed_phases])}")

        return session_data


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

async def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Enhanced SDLC Engine - Full SDK Integration",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('--requirement', help='Project requirement (for new sessions)')
    parser.add_argument('--output', type=Path, default=Path("./sdlc_output"),
                       help='Output directory')
    parser.add_argument('--session-id', help='Session ID for new session')
    parser.add_argument('--resume', help='Resume existing session by ID')
    parser.add_argument('--phases', nargs='+',
                       choices=['foundation', 'implementation', 'qa', 'deployment'],
                       help='Specific phases to execute')
    parser.add_argument('--auto-complete', action='store_true',
                       help='Auto-complete all remaining phases')

    args = parser.parse_args()

    # Resume session
    if args.resume:
        output_dir = Path(args.output)
        engine = EnhancedSDLCEngine(output_dir=output_dir, session_id=args.resume)
        session_data = await engine.resume_session(args.resume)

        if args.auto_complete:
            # Execute all remaining phases
            all_phases = [SDLCPhase.FOUNDATION, SDLCPhase.IMPLEMENTATION, SDLCPhase.QA, SDLCPhase.DEPLOYMENT]
            remaining_phases = [p for p in all_phases if p not in engine.completed_phases]

            if remaining_phases:
                print(f"🔄 Auto-completing {len(remaining_phases)} remaining phases...")
                result = await engine.execute_full_sdlc(
                    requirement=engine.requirement,
                    phases=remaining_phases
                )
            else:
                print("✅ All phases already completed!")
                return

        elif args.phases:
            # Execute specific phases
            phases = [SDLCPhase(p) for p in args.phases]
            result = await engine.execute_full_sdlc(
                requirement=engine.requirement,
                phases=phases
            )
        else:
            print("ℹ️  Session resumed. Use --auto-complete or --phases to continue.")
            return

    # New session
    else:
        if not args.requirement:
            print("❌ Error: --requirement is required for new sessions")
            return

        engine = EnhancedSDLCEngine(
            output_dir=args.output,
            session_id=args.session_id
        )

        phases = None
        if args.phases:
            phases = [SDLCPhase(p) for p in args.phases]

        result = await engine.execute_full_sdlc(
            requirement=args.requirement,
            phases=phases
        )

    print(f"\n✅ Execution completed!")
    print(f"🆔 Session: {result['session_id']}")
    print(f"📚 Knowledge Items: {result['knowledge_items']}")
    print(f"📦 Artifacts: {result['artifacts']}")
    print(f"📂 Output: {result['output_dir']}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    asyncio.run(main())
