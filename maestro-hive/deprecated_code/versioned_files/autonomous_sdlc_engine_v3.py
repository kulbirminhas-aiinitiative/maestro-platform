#!/usr/bin/env python3
"""
Autonomous SDLC Engine V3 - Fully Dynamic Persona-Driven Execution

Key Innovation: No hardcoded workflow phases
- Takes any list of personas (1 or more)
- Dynamically determines what work to do based on personas provided
- Each persona executes their specialized work autonomously
- Flexible: 1 persona = 1 phase, all personas = full SDLC

Examples:
  - [requirement_analyst] → Only requirements documents
  - [ui_ux_designer] → Only wireframes and mockups
  - [requirement_analyst, backend_developer] → Requirements + Backend code
  - All 11 personas → Full SDLC cycle
"""

import asyncio
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
import json
import logging

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from personas import SDLCPersonas
from team_organization import get_deliverables_for_persona
from config import CLAUDE_CONFIG, OUTPUT_CONFIG

# Claude Agent SDK
try:
    from claude_agent_sdk import query, ClaudeAgentOptions
    CLAUDE_SDK_AVAILABLE = True
except ImportError:
    CLAUDE_SDK_AVAILABLE = False
    logging.error("❌ claude_agent_sdk not available")

logger = logging.getLogger(__name__)


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

    def mark_complete(self, success: bool = True, error: str = None):
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
            "persona_id": self.persona_id,
            "success": self.success,
            "files_created": self.files_created,
            "deliverables": self.deliverables,
            "duration": self.duration(),
            "error": self.error
        }


class ProjectContext:
    """Shared context across all persona executions"""

    def __init__(self, requirement: str, output_dir: Path):
        self.requirement = requirement
        self.output_dir = output_dir
        self.files_registry: Dict[str, Dict[str, Any]] = {}
        self.persona_outputs: Dict[str, PersonaExecutionContext] = {}
        self.execution_order: List[str] = []

    def register_file(self, file_path: str, created_by: str, file_type: str):
        """Register a file created by a persona"""
        self.files_registry[file_path] = {
            "created_by": created_by,
            "file_type": file_type,
            "created_at": datetime.now().isoformat()
        }

    def get_files_by_persona(self, persona_id: str) -> List[str]:
        """Get all files created by a specific persona"""
        return [
            path for path, info in self.files_registry.items()
            if info["created_by"] == persona_id
        ]

    def get_all_files(self) -> List[str]:
        """Get all files created"""
        return list(self.files_registry.keys())

    def get_available_context(self, for_persona: str) -> str:
        """Build context from previous personas' work"""
        context_parts = [f"Original Requirement:\n{self.requirement}\n"]

        # Add outputs from personas that have already executed
        for persona_id in self.execution_order:
            if persona_id == for_persona:
                break

            if persona_id in self.persona_outputs:
                output = self.persona_outputs[persona_id]
                if output.success and output.files_created:
                    context_parts.append(f"\n{persona_id} created:")
                    for file in output.files_created[:5]:  # Limit to avoid huge context
                        context_parts.append(f"  - {file}")

        return "\n".join(context_parts)


class AutonomousSDLCEngineV3:
    """
    Fully Dynamic Persona-Driven SDLC Engine

    No hardcoded phases - executes only the personas you provide
    """

    def __init__(self, selected_personas: List[str], output_dir: str = None):
        """
        Initialize V3 engine with selected personas

        Args:
            selected_personas: List of persona IDs to execute (e.g., ['requirement_analyst'])
            output_dir: Output directory for generated files
        """
        if not CLAUDE_SDK_AVAILABLE:
            raise RuntimeError("claude_agent_sdk is required for V3 engine")

        self.selected_personas = selected_personas
        self.output_dir = Path(output_dir or OUTPUT_CONFIG["default_output_dir"])
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Load persona configurations
        self.all_personas = SDLCPersonas.get_all_personas()
        self.persona_configs = {
            pid: self.all_personas[pid]
            for pid in selected_personas
            if pid in self.all_personas
        }

        if not self.persona_configs:
            raise ValueError(f"No valid personas found in: {selected_personas}")

        # Determine execution order based on persona dependencies
        self.execution_order = self._determine_execution_order()

        logger.info(f"🚀 SDLC V3 Engine initialized with {len(self.persona_configs)} personas")
        logger.info(f"📋 Execution order: {' → '.join(self.execution_order)}")

    def _determine_execution_order(self) -> List[str]:
        """
        Determine optimal execution order based on persona types and dependencies

        Uses heuristic ordering:
        1. Analysis personas (requirement_analyst, etc.)
        2. Architecture personas (solution_architect, etc.)
        3. Security review (security_specialist)
        4. Development personas (backend, frontend, database)
        5. Design personas (ui_ux_designer)
        6. Testing personas (unit_tester, integration_tester)
        7. Deployment personas (devops_engineer)
        8. Documentation personas (technical_writer)
        """

        # Define persona priority tiers
        priority_tiers = {
            # Tier 1: Requirements and analysis
            "requirement_analyst": 1,

            # Tier 2: Architecture and design planning
            "solution_architect": 2,

            # Tier 3: Security review
            "security_specialist": 3,

            # Tier 4: Core development (can run in parallel in real impl)
            "backend_developer": 4,
            "database_specialist": 4,
            "frontend_developer": 5,  # After backend so it can use APIs

            # Tier 5: UX/UI design (can inform frontend)
            "ui_ux_designer": 5,

            # Tier 6: Testing
            "unit_tester": 6,
            "integration_tester": 7,

            # Tier 7: Deployment
            "devops_engineer": 8,

            # Tier 8: Documentation
            "technical_writer": 9
        }

        # Sort selected personas by priority
        ordered = sorted(
            self.selected_personas,
            key=lambda p: priority_tiers.get(p, 999)  # Unknown personas go last
        )

        return ordered

    async def execute(self, requirement: str) -> Dict[str, Any]:
        """
        Execute the SDLC workflow with selected personas

        Args:
            requirement: The user requirement to implement

        Returns:
            Execution result with files, deliverables, and metrics
        """

        logger.info("="*80)
        logger.info("🚀 AUTONOMOUS SDLC ENGINE V3 - DYNAMIC PERSONA EXECUTION")
        logger.info("="*80)
        logger.info(f"📝 Requirement: {requirement[:100]}...")
        logger.info(f"👥 Personas: {', '.join(self.selected_personas)}")
        logger.info(f"📁 Output: {self.output_dir}")
        logger.info("="*80)

        start_time = datetime.now()

        # Initialize project context
        project_context = ProjectContext(requirement, self.output_dir)
        project_context.execution_order = self.execution_order

        # Execute each persona in order
        for i, persona_id in enumerate(self.execution_order, 1):
            logger.info(f"\n{'='*80}")
            logger.info(f"🤖 [{i}/{len(self.execution_order)}] Executing: {persona_id}")
            logger.info(f"{'='*80}")

            persona_context = await self._execute_persona(
                persona_id,
                requirement,
                project_context
            )

            project_context.persona_outputs[persona_id] = persona_context

            if persona_context.success:
                logger.info(f"✅ {persona_id} completed: {len(persona_context.files_created)} files")
            else:
                logger.error(f"❌ {persona_id} failed: {persona_context.error}")

        # Build final result
        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds()

        all_files = project_context.get_all_files()
        successful_personas = [
            pid for pid, ctx in project_context.persona_outputs.items()
            if ctx.success
        ]

        result = {
            "success": len(successful_personas) > 0,
            "requirement": requirement,
            "selected_personas": self.selected_personas,
            "execution_order": self.execution_order,
            "successful_personas": successful_personas,
            "failed_personas": [
                pid for pid in self.execution_order
                if pid not in successful_personas
            ],
            "files": all_files,
            "file_count": len(all_files),
            "project_dir": str(self.output_dir),
            "total_duration": total_duration,
            "persona_details": {
                pid: ctx.to_dict()
                for pid, ctx in project_context.persona_outputs.items()
            }
        }

        # Save execution summary
        self._save_execution_summary(result)

        logger.info("\n" + "="*80)
        logger.info("📊 EXECUTION SUMMARY")
        logger.info("="*80)
        logger.info(f"✅ Success: {result['success']}")
        logger.info(f"👥 Personas executed: {len(successful_personas)}/{len(self.execution_order)}")
        logger.info(f"📁 Files created: {result['file_count']}")
        logger.info(f"⏱️  Total duration: {total_duration:.2f}s")
        logger.info(f"📂 Output: {result['project_dir']}")
        logger.info("="*80)

        return result

    async def _execute_persona(
        self,
        persona_id: str,
        requirement: str,
        project_context: ProjectContext
    ) -> PersonaExecutionContext:
        """Execute a single persona's work"""

        persona_context = PersonaExecutionContext(
            persona_id,
            requirement,
            self.output_dir
        )

        try:
            # Get persona configuration
            persona_config = self.persona_configs[persona_id]

            # Get expected deliverables for this persona
            expected_deliverables = get_deliverables_for_persona(persona_id)

            # Build context-aware prompt
            available_context = project_context.get_available_context(persona_id)
            prompt = self._build_persona_prompt(
                persona_config,
                requirement,
                expected_deliverables,
                available_context
            )

            # Configure Claude with persona's system prompt
            options = ClaudeAgentOptions(
                system_prompt=persona_config["system_prompt"],
                model=CLAUDE_CONFIG["model"],
                cwd=str(self.output_dir),
                permission_mode=CLAUDE_CONFIG["permission_mode"]
            )

            logger.info(f"🤖 {persona_id} is working...")
            logger.info(f"📦 Expected deliverables: {', '.join(expected_deliverables[:5])}")

            # Execute with Claude Agent SDK
            async for message in query(prompt=prompt, options=options):
                # Track tool usage - check message_type attribute
                if hasattr(message, 'message_type') and message.message_type == 'tool_use':
                    if hasattr(message, 'name') and message.name == 'Write':
                        file_path = message.input.get('file_path') if hasattr(message, 'input') else None
                        if file_path:
                            persona_context.add_file(file_path)
                            project_context.register_file(
                                file_path,
                                persona_id,
                                "created"
                            )
                            logger.debug(f"  📄 Created: {file_path}")

                    elif hasattr(message, 'name') and message.name == 'Edit':
                        file_path = message.input.get('file_path') if hasattr(message, 'input') else None
                        if file_path:
                            logger.debug(f"  ✏️  Edited: {file_path}")

            persona_context.mark_complete(success=True)

        except Exception as e:
            logger.exception(f"❌ Error executing {persona_id}")
            persona_context.mark_complete(success=False, error=str(e))

        return persona_context

    def _build_persona_prompt(
        self,
        persona_config: Dict[str, Any],
        requirement: str,
        expected_deliverables: List[str],
        available_context: str
    ) -> str:
        """Build a dynamic prompt for the persona"""

        persona_name = persona_config["name"]
        expertise = persona_config.get("expertise", [])

        prompt = f"""You are the {persona_name} for this project.

{available_context}

Your task is to analyze the requirement and create the deliverables for your role.

Your expertise areas:
{chr(10).join(f"- {exp}" for exp in expertise[:5])}

Expected deliverables for your role:
{chr(10).join(f"- {d}" for d in expected_deliverables)}

Using the Claude Code tools (Write, Edit, Read, Bash, WebSearch):
1. Analyze the requirement and any available context from previous work
2. Create all necessary deliverables for your role
3. Ensure your output is production-ready and follows best practices
4. Create files in appropriate directories (use mkdir if needed)

Work autonomously - you decide what to create and how to structure it.
Focus on your specialized domain only.

Output directory: {self.output_dir}
"""

        return prompt

    def _save_execution_summary(self, result: Dict[str, Any]):
        """Save execution summary to output directory"""

        summary_file = self.output_dir / "execution_summary_v3.json"

        try:
            with open(summary_file, 'w') as f:
                json.dump(result, f, indent=2, default=str)
            logger.info(f"📄 Execution summary saved: {summary_file}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to save execution summary: {e}")


async def main():
    """Main entry point for testing"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python autonomous_sdlc_engine_v3.py <persona1> [persona2 ...] --requirement 'Your requirement'")
        print("\nExamples:")
        print("  # Single persona - requirements only")
        print("  python autonomous_sdlc_engine_v3.py requirement_analyst --requirement 'Create a blog platform'")
        print("\n  # Two personas - requirements + backend")
        print("  python autonomous_sdlc_engine_v3.py requirement_analyst backend_developer --requirement 'Create a blog'")
        print("\n  # Full team")
        print("  python autonomous_sdlc_engine_v3.py requirement_analyst solution_architect backend_developer --requirement 'Create a blog'")
        return

    # Parse arguments
    personas = []
    requirement = None

    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == '--requirement':
            requirement = sys.argv[i + 1] if i + 1 < len(sys.argv) else None
            break
        else:
            personas.append(sys.argv[i])
        i += 1

    if not personas:
        print("❌ Error: No personas specified")
        return

    if not requirement:
        requirement = "Create a modern web application"

    print(f"🚀 Running V3 with personas: {', '.join(personas)}")
    print(f"📝 Requirement: {requirement}")

    # Create and execute engine
    engine = AutonomousSDLCEngineV3(
        selected_personas=personas,
        output_dir="./generated_v3_project"
    )

    result = await engine.execute(requirement)

    if result["success"]:
        print(f"\n✅ Execution completed successfully!")
        print(f"📁 {result['file_count']} files created")
        print(f"📂 Project: {result['project_dir']}")
    else:
        print(f"\n❌ Execution failed")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    asyncio.run(main())
