#!/usr/bin/env python3
"""
Fully Functional Dynamic Team - Real Claude API Integration

Phase-based team with just-in-time member addition/retirement.
Agents are added only when needed for their phase and retired after completion.

Usage:
    python examples/team_wrappers/functional_dynamic_team.py \
        --project "Build a REST API for user management" \
        --phases design implement test \
        --output ./output/dynamic

Features:
    - Real Claude API calls for each phase
    - Just-in-time agent lifecycle management
    - Actual code and documentation generation
    - Cost-optimized (minimal active agents)
    - Phase-based workflow
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


class ProjectPhase(str, Enum):
    """Project phases for dynamic team composition"""
    DESIGN = "design"
    IMPLEMENT = "implement"
    TEST = "test"
    DEPLOY = "deploy"


class AgentContext:
    """Context for agent execution"""

    def __init__(self, agent_id: str, role: str, phase: str, output_dir: Path):
        self.agent_id = agent_id
        self.role = role
        self.phase = phase
        self.output_dir = output_dir
        self.files_created: List[str] = []
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

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "role": self.role,
            "phase": self.phase,
            "success": self.success,
            "files_created": self.files_created,
            "duration": self.duration(),
            "error": self.error
        }


class ArchitectAgent:
    """Architect - Design phase agent"""

    def __init__(self, agent_id: str, output_dir: Path):
        self.agent_id = agent_id
        self.output_dir = output_dir

    async def design(self, project: str, phase_context: str) -> AgentContext:
        """Create architectural design"""
        context = AgentContext(self.agent_id, "architect", "design", self.output_dir)

        logger.info(f"[{self.agent_id}] 🏗️  Designing architecture...")

        try:
            system_prompt = """You are a Solution Architect.

Your responsibilities:
- Design system architecture
- Create technical specifications
- Define component structure
- Specify technologies and patterns
- Create architecture diagrams (as markdown/mermaid)

Create production-ready architectural documentation."""

            prompt = f"""Design the architecture for this project:

Project: {project}

{phase_context}

Create the following deliverables:

1. **architecture_overview.md**: System architecture including:
   - High-level architecture diagram (mermaid)
   - Component breakdown
   - Technology stack decisions
   - Design patterns to use

2. **api_specification.md**: API design including:
   - Endpoint definitions
   - Request/response schemas
   - Authentication approach
   - Error handling strategy

3. **data_model.md**: Data models including:
   - Entity definitions
   - Relationships
   - Database schema (if applicable)

4. **technical_decisions.md**: ADRs (Architecture Decision Records):
   - Key technical decisions
   - Rationale for each decision
   - Trade-offs considered

Use the Write tool to create these files. Use mermaid diagrams where applicable."""

            options = ClaudeCodeOptions(
                system_prompt=system_prompt,
                model=settings.claude.model if hasattr(settings, 'claude') else "claude-sonnet-4-20250514",
                cwd=str(self.output_dir),
                permission_mode="auto"
            )

            async for message in query(prompt=prompt, options=options):
                if hasattr(message, 'message_type') and message.message_type == 'tool_use':
                    if hasattr(message, 'name') and message.name == 'Write':
                        file_path = message.input.get('file_path') if hasattr(message, 'input') else None
                        if file_path:
                            context.add_file(file_path)
                            logger.info(f"  [{self.agent_id}] 📄 Created: {Path(file_path).name}")

            context.mark_complete(success=True)
            logger.info(f"[{self.agent_id}] ✅ Design complete: {len(context.files_created)} files")

        except Exception as e:
            logger.exception(f"[{self.agent_id}] ❌ Error during design")
            context.mark_complete(success=False, error=str(e))

        return context


class DeveloperAgent:
    """Developer - Implementation phase agent"""

    def __init__(self, agent_id: str, output_dir: Path):
        self.agent_id = agent_id
        self.output_dir = output_dir

    async def implement(self, project: str, component: str, phase_context: str) -> AgentContext:
        """Implement a component"""
        context = AgentContext(self.agent_id, "developer", "implement", self.output_dir)

        logger.info(f"[{self.agent_id}] 💻 Implementing: {component}...")

        try:
            system_prompt = """You are a Software Developer.

Your responsibilities:
- Implement features based on architecture
- Write clean, production-ready code
- Follow best practices and design patterns
- Create necessary configurations
- Document your code

Create working, production-ready implementations."""

            prompt = f"""Implement this component based on the architectural design:

Project: {project}
Component: {component}

{phase_context}

Review the architecture files (use Read tool) and implement:

1. **Source code files**: Create the actual implementation
   - Main application code
   - Configuration files
   - Helper/utility modules
   - Follow the architecture specified

2. **requirements.txt** or **package.json**: Dependencies needed

3. **README.md** for this component: Setup and usage instructions

4. **IMPLEMENTATION_NOTES.md**: Implementation details:
   - Design patterns used
   - Key implementation decisions
   - Known limitations
   - Future improvements

Use Read tool to review the architecture, then use Write tool to implement.
Create working, production-ready code."""

            options = ClaudeCodeOptions(
                system_prompt=system_prompt,
                model=settings.claude.model if hasattr(settings, 'claude') else "claude-sonnet-4-20250514",
                cwd=str(self.output_dir),
                permission_mode="auto"
            )

            async for message in query(prompt=prompt, options=options):
                if hasattr(message, 'message_type') and message.message_type == 'tool_use':
                    if hasattr(message, 'name') and message.name in ['Write', 'Edit']:
                        file_path = message.input.get('file_path') if hasattr(message, 'input') else None
                        if file_path:
                            context.add_file(file_path)
                            logger.info(f"  [{self.agent_id}] 📄 Created: {Path(file_path).name}")

            context.mark_complete(success=True)
            logger.info(f"[{self.agent_id}] ✅ Implementation complete: {len(context.files_created)} files")

        except Exception as e:
            logger.exception(f"[{self.agent_id}] ❌ Error during implementation")
            context.mark_complete(success=False, error=str(e))

        return context


class TesterAgent:
    """Tester - Testing phase agent"""

    def __init__(self, agent_id: str, output_dir: Path):
        self.agent_id = agent_id
        self.output_dir = output_dir

    async def test(self, project: str, phase_context: str) -> AgentContext:
        """Create test suite"""
        context = AgentContext(self.agent_id, "tester", "test", self.output_dir)

        logger.info(f"[{self.agent_id}] 🧪 Creating test suite...")

        try:
            system_prompt = """You are a QA/Testing Engineer.

Your responsibilities:
- Create comprehensive test plans
- Write automated tests
- Define test scenarios
- Create test documentation
- Specify testing strategies

Create production-ready test suites."""

            prompt = f"""Create a comprehensive test suite for this project:

Project: {project}

{phase_context}

Review the implementation files (use Read tool) and create:

1. **test_plan.md**: Test strategy including:
   - Testing approach (unit, integration, e2e)
   - Test scenarios
   - Coverage goals
   - Testing tools/frameworks

2. **Test files**: Actual test code
   - Unit tests
   - Integration tests
   - Test fixtures/mocks

3. **test_scenarios.md**: Detailed test scenarios:
   - Happy path scenarios
   - Edge cases
   - Error conditions
   - Expected results

4. **TEST_RESULTS.md**: Template for test results:
   - Test execution checklist
   - Results template
   - Bug report template

Use Read tool to review implementation, then Write tool to create tests.
Create working, executable test code."""

            options = ClaudeCodeOptions(
                system_prompt=system_prompt,
                model=settings.claude.model if hasattr(settings, 'claude') else "claude-sonnet-4-20250514",
                cwd=str(self.output_dir),
                permission_mode="auto"
            )

            async for message in query(prompt=prompt, options=options):
                if hasattr(message, 'message_type') and message.message_type == 'tool_use':
                    if hasattr(message, 'name') and message.name == 'Write':
                        file_path = message.input.get('file_path') if hasattr(message, 'input') else None
                        if file_path:
                            context.add_file(file_path)
                            logger.info(f"  [{self.agent_id}] 📄 Created: {Path(file_path).name}")

            context.mark_complete(success=True)
            logger.info(f"[{self.agent_id}] ✅ Testing complete: {len(context.files_created)} files")

        except Exception as e:
            logger.exception(f"[{self.agent_id}] ❌ Error during testing")
            context.mark_complete(success=False, error=str(e))

        return context


class DynamicTeamWorkflow:
    """Orchestrates dynamic team with phase-based lifecycle"""

    def __init__(self, team_id: str, project: str, phases: List[ProjectPhase], output_dir: Path):
        self.team_id = team_id
        self.project = project
        self.phases = phases
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.phase_results: Dict[str, List[AgentContext]] = {}
        self.all_files: List[str] = []

    async def execute(self) -> Dict[str, Any]:
        """Execute dynamic team workflow with phase-based agent lifecycle"""

        logger.info("=" * 80)
        logger.info("🚀 DYNAMIC TEAM WORKFLOW - PHASE-BASED EXECUTION")
        logger.info("=" * 80)
        logger.info(f"📝 Project: {self.project}")
        logger.info(f"📋 Phases: {[p.value for p in self.phases]}")
        logger.info(f"📁 Output: {self.output_dir}")
        logger.info("=" * 80)

        start_time = datetime.now()

        # Execute each phase
        for phase in self.phases:
            await self._execute_phase(phase)

        # Compile final result
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        result = {
            "success": True,
            "team_id": self.team_id,
            "workflow_type": "dynamic_phase_based",
            "project": self.project,
            "executed_at": start_time.isoformat(),
            "completed_at": end_time.isoformat(),
            "duration_seconds": duration,
            "phases_executed": [p.value for p in self.phases],
            "files_created": self.all_files,
            "file_count": len(self.all_files),
            "output_dir": str(self.output_dir),
            "phase_results": {
                phase: [ctx.to_dict() for ctx in results]
                for phase, results in self.phase_results.items()
            }
        }

        # Save summary
        self._save_summary(result)

        logger.info("\n" + "=" * 80)
        logger.info("✅ DYNAMIC TEAM WORKFLOW COMPLETE!")
        logger.info(f"   Duration: {duration:.2f}s")
        logger.info(f"   Phases executed: {len(self.phases)}")
        logger.info(f"   Files created: {len(self.all_files)}")
        logger.info(f"   Output: {self.output_dir}")
        logger.info("=" * 80)

        return result

    async def _execute_phase(self, phase: ProjectPhase):
        """Execute a single phase with appropriate agents"""
        logger.info(f"\n{'=' * 80}")
        logger.info(f"📋 PHASE: {phase.value.upper()}")
        logger.info(f"{'=' * 80}")

        phase_context = self._build_phase_context()

        if phase == ProjectPhase.DESIGN:
            # Add architect for design
            logger.info("➕ Adding architect agent...")
            architect = ArchitectAgent("architect_1", self.output_dir)

            result = await architect.design(self.project, phase_context)
            self.phase_results[phase.value] = [result]
            self.all_files.extend(result.files_created)

            logger.info("➖ Design phase complete - architect work done")

        elif phase == ProjectPhase.IMPLEMENT:
            # Add developers for implementation
            components = ["core_api", "data_layer", "business_logic"]
            logger.info(f"➕ Adding {len(components)} developer agents...")

            tasks = []
            for i, component in enumerate(components):
                dev = DeveloperAgent(f"developer_{i+1}", self.output_dir)
                tasks.append(dev.implement(self.project, component, phase_context))

            results = await asyncio.gather(*tasks)
            self.phase_results[phase.value] = results

            for result in results:
                self.all_files.extend(result.files_created)

            logger.info("➖ Implementation phase complete - developers work done")

        elif phase == ProjectPhase.TEST:
            # Add tester for testing
            logger.info("➕ Adding tester agent...")
            tester = TesterAgent("tester_1", self.output_dir)

            result = await tester.test(self.project, phase_context)
            self.phase_results[phase.value] = [result]
            self.all_files.extend(result.files_created)

            logger.info("➖ Testing phase complete - tester work done")

    def _build_phase_context(self) -> str:
        """Build context from previous phases"""
        context_parts = []

        for phase, results in self.phase_results.items():
            if results:
                context_parts.append(f"\n{phase.upper()} phase completed:")
                all_phase_files = []
                for result in results:
                    all_phase_files.extend(result.files_created)
                for file in all_phase_files[:10]:  # Limit to avoid huge context
                    context_parts.append(f"  - {file}")

        if context_parts:
            return "Previous work:\n" + "\n".join(context_parts)
        else:
            return "This is the first phase."

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
        description="Functional Dynamic Team - Phase-Based Workflow with Real Claude API"
    )
    parser.add_argument(
        "--project",
        required=True,
        help="Project description"
    )
    parser.add_argument(
        "--phases",
        nargs="+",
        choices=["design", "implement", "test", "deploy"],
        default=["design", "implement", "test"],
        help="Project phases to execute"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(settings.output.base_dir if hasattr(settings, 'output') else "./output") / "dynamic_team",
        help="Output directory for deliverables"
    )
    parser.add_argument(
        "--team-id",
        default=f"dynamic_team_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        help="Team identifier"
    )

    args = parser.parse_args()

    # Convert phases to enum
    phases = [ProjectPhase(p) for p in args.phases]

    # Create and execute workflow
    workflow = DynamicTeamWorkflow(
        team_id=args.team_id,
        project=args.project,
        phases=phases,
        output_dir=args.output
    )

    result = await workflow.execute()

    if result["success"]:
        print(f"\n✅ Workflow completed successfully!")
        print(f"📁 {result['file_count']} files created")
        print(f"📋 {len(result['phases_executed'])} phases executed")
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
