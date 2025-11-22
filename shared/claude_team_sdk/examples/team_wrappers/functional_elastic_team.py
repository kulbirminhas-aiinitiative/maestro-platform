#!/usr/bin/env python3
"""
Fully Functional Elastic Team - Real Claude API Integration

Advanced team with role-based routing, onboarding, and knowledge handoffs.
Features seamless member substitution and workload-based scaling.

Usage:
    python examples/team_wrappers/functional_elastic_team.py \
        --project "Build microservices platform" \
        --workload high \
        --output ./output/elastic

Features:
    - Real Claude API calls with role-based assignment
    - Onboarding briefings for new members
    - Knowledge handoffs during transitions
    - Workload-based auto-scaling
    - Production-ready deliverables
"""

import asyncio
import argparse
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum
import json
import logging

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Configuration
try:
    from src.claude_team_sdk.config import settings
except ImportError:
    from claude_team_sdk.config import settings

# Claude Code SDK
try:
    from claude_code_sdk import query, ClaudeCodeOptions
    CLAUDE_SDK_AVAILABLE = True
except ImportError:
    CLAUDE_SDK_AVAILABLE = False
    logging.error("❌ claude_code_sdk not available")

logger = logging.getLogger(__name__)


class WorkloadLevel(str, Enum):
    """Workload levels for auto-scaling"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TeamRole(str, Enum):
    """Team roles (abstract from individuals)"""
    TECH_LEAD = "Tech Lead"
    BACKEND_LEAD = "Backend Lead"
    FRONTEND_LEAD = "Frontend Lead"
    QA_LEAD = "QA Lead"


class AgentContext:
    """Context for agent execution"""

    def __init__(self, agent_id: str, role: TeamRole, output_dir: Path):
        self.agent_id = agent_id
        self.role = role
        self.output_dir = output_dir
        self.files_created: List[str] = []
        self.knowledge_items: List[str] = []
        self.start_time = datetime.now()
        self.end_time: Optional[datetime] = None
        self.success = False
        self.error: Optional[str] = None

    def mark_complete(self, success: bool = True, error: Optional[str] = None):
        self.end_time = datetime.now()
        self.success = success
        self.error = error

    def duration(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0

    def add_file(self, file_path: str):
        self.files_created.append(file_path)

    def add_knowledge(self, item: str):
        self.knowledge_items.append(item)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "role": self.role.value,
            "success": self.success,
            "files_created": self.files_created,
            "knowledge_items": self.knowledge_items,
            "duration": self.duration(),
            "error": self.error
        }


class ElasticAgent:
    """Agent with onboarding and knowledge handoff capabilities"""

    def __init__(
        self,
        agent_id: str,
        role: TeamRole,
        output_dir: Path,
        briefing: Optional[Dict[str, Any]] = None
    ):
        self.agent_id = agent_id
        self.role = role
        self.output_dir = output_dir
        self.briefing = briefing or {}
        self.context = AgentContext(agent_id, role, output_dir)

    def _get_role_system_prompt(self) -> str:
        """Get role-specific system prompt"""
        prompts = {
            TeamRole.TECH_LEAD: """You are the Technical Lead.

Responsibilities:
- Define system architecture and technical direction
- Make high-level technical decisions
- Guide development team
- Ensure technical quality and best practices
- Create architectural documentation""",

            TeamRole.BACKEND_LEAD: """You are the Backend Lead.

Responsibilities:
- Design and implement backend services
- Create API specifications
- Implement data layer and business logic
- Ensure performance and scalability
- Create backend documentation""",

            TeamRole.FRONTEND_LEAD: """You are the Frontend Lead.

Responsibilities:
- Design and implement frontend application
- Create user interface components
- Implement client-side logic
- Ensure UX best practices
- Create frontend documentation""",

            TeamRole.QA_LEAD: """You are the QA Lead.

Responsibilities:
- Define testing strategy
- Create test plans and test cases
- Implement automated tests
- Ensure quality standards
- Create testing documentation"""
        }
        return prompts.get(self.role, "You are a team member.")

    async def onboard(self):
        """Process onboarding briefing"""
        if self.briefing:
            logger.info(f"\n[{self.agent_id}] 📚 Onboarding Briefing:")
            logger.info(f"   Role: {self.role.value}")
            logger.info(f"   Context: {self.briefing.get('context', 'N/A')}")
            logger.info(f"   Previous work available: {len(self.briefing.get('previous_files', []))} files")

    async def execute_role_task(self, project: str, available_context: str) -> AgentContext:
        """Execute task for this role"""
        logger.info(f"\n[{self.agent_id}] ⚙️  Executing {self.role.value} tasks...")

        try:
            task_prompts = {
                TeamRole.TECH_LEAD: f"""As Technical Lead, create the technical foundation:

Project: {project}

{available_context}

Create:
1. **ARCHITECTURE.md**: System architecture including:
   - Architecture diagram (mermaid)
   - Component breakdown
   - Technology decisions
   - Integration patterns

2. **TECHNICAL_STANDARDS.md**: Development standards:
   - Coding standards
   - Git workflow
   - Code review process
   - Documentation requirements

3. **TECH_ROADMAP.md**: Development roadmap:
   - Development phases
   - Timeline estimates
   - Resource allocation
   - Risk mitigation""",

                TeamRole.BACKEND_LEAD: f"""As Backend Lead, implement the backend system:

Project: {project}

{available_context}

Review architecture (use Read tool) and create:
1. **Backend source code**: Actual implementation
   - API endpoints
   - Data models
   - Business logic
   - Configuration

2. **API_DOCUMENTATION.md**: API reference:
   - Endpoint documentation
   - Request/response examples
   - Authentication details

3. **BACKEND_SETUP.md**: Setup guide:
   - Installation steps
   - Configuration
   - Running the backend""",

                TeamRole.FRONTEND_LEAD: f"""As Frontend Lead, implement the frontend:

Project: {project}

{available_context}

Review architecture and API docs (use Read tool) and create:
1. **Frontend source code**: Actual implementation
   - UI components
   - State management
   - API integration
   - Routing

2. **UI_COMPONENTS.md**: Component documentation:
   - Component hierarchy
   - Props and state
   - Usage examples

3. **FRONTEND_SETUP.md**: Setup guide:
   - Installation
   - Configuration
   - Running the frontend""",

                TeamRole.QA_LEAD: f"""As QA Lead, create the test suite:

Project: {project}

{available_context}

Review implementation (use Read tool) and create:
1. **Test code**: Actual test implementation
   - Unit tests
   - Integration tests
   - E2E tests

2. **TEST_STRATEGY.md**: Testing strategy:
   - Testing approach
   - Coverage goals
   - Testing tools

3. **TEST_EXECUTION_GUIDE.md**: How to run tests:
   - Test execution steps
   - CI/CD integration
   - Results interpretation"""
            }

            prompt = task_prompts.get(self.role, f"Execute work for {self.role.value}")

            # Onboarding context
            if self.briefing.get('handoff'):
                prompt = f"""HANDOFF FROM PREVIOUS {self.role.value}:
{json.dumps(self.briefing['handoff'], indent=2)}

{prompt}

Continue from where the previous team member left off."""

            options = ClaudeCodeOptions(
                system_prompt=self._get_role_system_prompt(),
                model=settings.claude.model if hasattr(settings, 'claude') else "claude-sonnet-4-20250514",
                cwd=str(self.output_dir),
                permission_mode="auto"
            )

            async for message in query(prompt=prompt, options=options):
                if hasattr(message, 'message_type') and message.message_type == 'tool_use':
                    if hasattr(message, 'name') and message.name in ['Write', 'Edit']:
                        file_path = message.input.get('file_path') if hasattr(message, 'input') else None
                        if file_path:
                            self.context.add_file(file_path)
                            self.context.add_knowledge(f"Created {Path(file_path).name}")
                            logger.info(f"  [{self.agent_id}] 📄 Created: {Path(file_path).name}")

            self.context.mark_complete(success=True)
            logger.info(f"[{self.agent_id}] ✅ Role tasks complete: {len(self.context.files_created)} files")

        except Exception as e:
            logger.exception(f"[{self.agent_id}] ❌ Error executing role tasks")
            self.context.mark_complete(success=False, error=str(e))

        return self.context

    async def create_handoff(self) -> Dict[str, Any]:
        """Create knowledge handoff for successor"""
        logger.info(f"\n[{self.agent_id}] 📝 Creating knowledge handoff...")

        handoff = {
            "from_agent": self.agent_id,
            "role": self.role.value,
            "created_at": datetime.now().isoformat(),
            "knowledge_items": self.context.knowledge_items,
            "files_created": self.context.files_created,
            "status": {
                "work_completed": f"All {self.role.value} tasks completed",
                "pending_items": [],
                "recommendations": "Continue with current architecture approach"
            }
        }

        logger.info(f"[{self.agent_id}] ✅ Knowledge handoff created")
        return handoff


class ElasticTeamWorkflow:
    """Orchestrates elastic team with role-based composition"""

    def __init__(
        self,
        team_id: str,
        project: str,
        workload: WorkloadLevel,
        output_dir: Path
    ):
        self.team_id = team_id
        self.project = project
        self.workload = workload
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.active_agents: Dict[TeamRole, ElasticAgent] = {}
        self.agent_history: List[Dict[str, Any]] = []
        self.handoffs: Dict[TeamRole, Dict[str, Any]] = {}

    async def execute(self) -> Dict[str, Any]:
        """Execute elastic team workflow"""

        logger.info("=" * 80)
        logger.info("🚀 ELASTIC TEAM WORKFLOW - ROLE-BASED EXECUTION")
        logger.info("=" * 80)
        logger.info(f"📝 Project: {self.project}")
        logger.info(f"📊 Workload: {self.workload.value}")
        logger.info(f"📁 Output: {self.output_dir}")
        logger.info("=" * 80)

        start_time = datetime.now()

        # Phase 1: Scale team based on workload
        await self._scale_team()

        # Phase 2: Execute role tasks
        logger.info(f"\n{'=' * 80}")
        logger.info("PHASE 2: EXECUTING ROLE TASKS")
        logger.info(f"{'=' * 80}")

        contexts = []
        for role, agent in self.active_agents.items():
            available_context = self._build_context_for_role(role)
            context = await agent.execute_role_task(self.project, available_context)
            contexts.append(context)

        # Phase 3: Demonstrate role replacement (optional)
        if TeamRole.BACKEND_LEAD in self.active_agents:
            logger.info(f"\n{'=' * 80}")
            logger.info("PHASE 3: DEMONSTRATING ROLE REPLACEMENT")
            logger.info(f"{'=' * 80}")
            await self._replace_role(TeamRole.BACKEND_LEAD)

        # Compile final result
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        all_files = []
        for ctx in contexts:
            all_files.extend(ctx.files_created)

        result = {
            "success": True,
            "team_id": self.team_id,
            "workflow_type": "elastic_role_based",
            "project": self.project,
            "workload": self.workload.value,
            "executed_at": start_time.isoformat(),
            "completed_at": end_time.isoformat(),
            "duration_seconds": duration,
            "active_roles": [r.value for r in self.active_agents.keys()],
            "files_created": all_files,
            "file_count": len(all_files),
            "output_dir": str(self.output_dir),
            "agent_history": self.agent_history,
            "role_contexts": {
                role.value: ctx.to_dict()
                for role, agent in self.active_agents.items()
                for ctx in [agent.context]
            }
        }

        # Save summary
        self._save_summary(result)

        logger.info("\n" + "=" * 80)
        logger.info("✅ ELASTIC TEAM WORKFLOW COMPLETE!")
        logger.info(f"   Duration: {duration:.2f}s")
        logger.info(f"   Active roles: {len(self.active_agents)}")
        logger.info(f"   Files created: {len(all_files)}")
        logger.info(f"   Output: {self.output_dir}")
        logger.info("=" * 80)

        return result

    async def _scale_team(self):
        """Scale team based on workload"""
        logger.info(f"\n{'=' * 80}")
        logger.info(f"PHASE 1: AUTO-SCALING FOR {self.workload.value.upper()} WORKLOAD")
        logger.info(f"{'=' * 80}")

        if self.workload == WorkloadLevel.LOW:
            roles_needed = [TeamRole.TECH_LEAD]
        elif self.workload == WorkloadLevel.MEDIUM:
            roles_needed = [TeamRole.TECH_LEAD, TeamRole.BACKEND_LEAD]
        else:  # HIGH
            roles_needed = [
                TeamRole.TECH_LEAD,
                TeamRole.BACKEND_LEAD,
                TeamRole.FRONTEND_LEAD,
                TeamRole.QA_LEAD
            ]

        for i, role in enumerate(roles_needed):
            await self._assign_role(role, f"{role.value.lower().replace(' ', '_')}_{i+1}")

        logger.info(f"\n✅ Team scaled: {len(self.active_agents)} active roles")

    async def _assign_role(self, role: TeamRole, agent_id: str):
        """Assign an agent to a role with onboarding"""
        logger.info(f"\n➕ Assigning {agent_id} to {role.value}...")

        briefing = {
            "role": role.value,
            "project": self.project,
            "context": f"Taking over as {role.value}",
            "previous_files": list(self._get_all_files())
        }

        # Include handoff if available
        if role in self.handoffs:
            briefing["handoff"] = self.handoffs[role]

        agent = ElasticAgent(agent_id, role, self.output_dir, briefing)
        await agent.onboard()

        self.active_agents[role] = agent

        self.agent_history.append({
            "action": "assigned",
            "role": role.value,
            "agent_id": agent_id,
            "timestamp": datetime.now().isoformat()
        })

        logger.info(f"✅ {agent_id} assigned to {role.value}")

    async def _replace_role(self, role: TeamRole):
        """Replace an agent in a role with knowledge handoff"""
        logger.info(f"\n🔄 Replacing {role.value}...")

        current_agent = self.active_agents.get(role)
        if not current_agent:
            return

        # Create handoff
        handoff = await current_agent.create_handoff()
        self.handoffs[role] = handoff

        self.agent_history.append({
            "action": "retired",
            "role": role.value,
            "agent_id": current_agent.agent_id,
            "timestamp": datetime.now().isoformat()
        })

        # Assign new agent with handoff
        new_agent_id = f"{role.value.lower().replace(' ', '_')}_2"
        await self._assign_role(role, new_agent_id)

    def _build_context_for_role(self, role: TeamRole) -> str:
        """Build context from other roles' work"""
        context_parts = []

        for other_role, agent in self.active_agents.items():
            if other_role != role and agent.context.files_created:
                context_parts.append(f"\n{other_role.value} has created:")
                for file in agent.context.files_created[:5]:
                    context_parts.append(f"  - {file}")

        if context_parts:
            return "Available work from team:\n" + "\n".join(context_parts)
        else:
            return "You are working on this project."

    def _get_all_files(self) -> List[str]:
        """Get all files created by team"""
        all_files = []
        for agent in self.active_agents.values():
            all_files.extend(agent.context.files_created)
        return all_files

    def _save_summary(self, result: Dict[str, Any]):
        """Save execution summary"""
        summary_file = self.output_dir / "workflow_summary.json"
        try:
            with open(summary_file, 'w') as f:
                json.dump(result, f, indent=2, default=str)
            logger.info(f"\n📄 Summary saved: {summary_file}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to save summary: {e}")


async def main():
    """Main entry point"""
    if not CLAUDE_SDK_AVAILABLE:
        print("❌ Error: claude_code_sdk is not available")
        print("Install with: pip install claude-code-sdk")
        return

    parser = argparse.ArgumentParser(
        description="Functional Elastic Team - Role-Based Workflow with Real Claude API"
    )
    parser.add_argument(
        "--project",
        required=True,
        help="Project description"
    )
    parser.add_argument(
        "--workload",
        choices=["low", "medium", "high"],
        default="medium",
        help="Workload level (affects team size)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(settings.output.base_dir if hasattr(settings, 'output') else "./output") / "elastic_team",
        help="Output directory for deliverables"
    )
    parser.add_argument(
        "--team-id",
        default=f"elastic_team_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        help="Team identifier"
    )

    args = parser.parse_args()

    # Create and execute workflow
    workflow = ElasticTeamWorkflow(
        team_id=args.team_id,
        project=args.project,
        workload=WorkloadLevel(args.workload),
        output_dir=args.output
    )

    result = await workflow.execute()

    if result["success"]:
        print(f"\n✅ Workflow completed successfully!")
        print(f"📁 {result['file_count']} files created")
        print(f"👥 {len(result['active_roles'])} roles active")
        print(f"📂 Output: {result['output_dir']}")
    else:
        print(f"\n❌ Workflow failed")
        sys.exit(1)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    asyncio.run(main())
