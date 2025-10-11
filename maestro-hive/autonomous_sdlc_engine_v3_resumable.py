#!/usr/bin/env python3
"""
Autonomous SDLC Engine V3.1 - Resumable Sessions

Key Features:
- Fully dynamic persona-driven execution (from V3)
- Session persistence and resume capability
- Incremental workflow execution across multiple days/runs
- Automatic context propagation from previous personas

Usage Examples:

# Day 1: Run requirements analysis only
python autonomous_sdlc_engine_v3_resumable.py requirement_analyst \\
    --requirement "Create a blog platform" \\
    --session-id blog_project_v1

# Day 2: Resume and add UX design (uses same session)
python autonomous_sdlc_engine_v3_resumable.py ui_ux_designer \\
    --resume blog_project_v1

# Day 3: Resume and add backend development
python autonomous_sdlc_engine_v3_resumable.py backend_developer \\
    --resume blog_project_v1

# Or run multiple personas at once on existing session
python autonomous_sdlc_engine_v3_resumable.py frontend_developer devops_engineer \\
    --resume blog_project_v1

# OR: Run ALL remaining personas (except already completed)
python autonomous_sdlc_engine_v3_resumable.py \\
    --resume blog_project_v1 \\
    --all-remaining

# List all sessions
python autonomous_sdlc_engine_v3_resumable.py --list-sessions
"""

import asyncio
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from personas import SDLCPersonas
from team_organization import get_deliverables_for_persona
from config import CLAUDE_CONFIG, OUTPUT_CONFIG
from session_manager import SessionManager, SDLCSession

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


class AutonomousSDLCEngineV3Resumable:
    """
    Resumable SDLC Engine with Session Management

    Enables incremental execution: Run personas across multiple sessions
    """

    def __init__(
        self,
        selected_personas: List[str],
        output_dir: str = None,
        session_manager: SessionManager = None
    ):
        if not CLAUDE_SDK_AVAILABLE:
            raise RuntimeError("claude_agent_sdk is required")

        self.selected_personas = selected_personas
        self.output_dir = Path(output_dir or OUTPUT_CONFIG["default_output_dir"])
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Session manager
        self.session_manager = session_manager or SessionManager()

        # Load persona configurations
        self.all_personas = SDLCPersonas.get_all_personas()
        self.persona_configs = {
            pid: self.all_personas[pid]
            for pid in selected_personas
            if pid in self.all_personas
        }

        if not self.persona_configs:
            raise ValueError(f"No valid personas found in: {selected_personas}")

    def _determine_execution_order(self, personas: List[str]) -> List[str]:
        """Determine optimal execution order"""
        priority_tiers = {
            "requirement_analyst": 1,
            "solution_architect": 2,
            "security_specialist": 3,
            "backend_developer": 4,
            "database_specialist": 4,
            "frontend_developer": 5,
            "ui_ux_designer": 5,
            "unit_tester": 6,
            "integration_tester": 7,
            "devops_engineer": 8,
            "technical_writer": 9
        }

        return sorted(personas, key=lambda p: priority_tiers.get(p, 999))

    async def execute(
        self,
        requirement: str,
        session_id: Optional[str] = None,
        resume_session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute SDLC workflow with session persistence

        Args:
            requirement: User requirement (required for new sessions)
            session_id: Session ID for new session
            resume_session_id: Session ID to resume existing session

        Returns:
            Execution result with session info
        """

        # Load or create session
        if resume_session_id:
            session = self.session_manager.load_session(resume_session_id)
            if not session:
                raise ValueError(f"Session not found: {resume_session_id}")

            # Use session's requirement and output dir
            requirement = session.requirement
            self.output_dir = session.output_dir
            logger.info(f"📂 Resuming session: {session.session_id}")
            logger.info(f"📋 Original requirement: {requirement[:100]}...")
            logger.info(f"✅ Completed personas: {', '.join(session.completed_personas)}")

        else:
            # Create new session
            session = self.session_manager.create_session(
                requirement=requirement,
                output_dir=self.output_dir,
                session_id=session_id
            )
            logger.info(f"🆕 Created new session: {session.session_id}")

        # Determine which personas to execute
        pending_personas = [
            p for p in self.selected_personas
            if p not in session.completed_personas
        ]

        if not pending_personas:
            logger.info("✅ All requested personas already completed!")
            return {
                "success": True,
                "session_id": session.session_id,
                "message": "All personas already completed",
                "completed_personas": session.completed_personas,
                "files": session.get_all_files(),
                "project_dir": str(self.output_dir)
            }

        execution_order = self._determine_execution_order(pending_personas)

        logger.info("="*80)
        logger.info("🚀 AUTONOMOUS SDLC ENGINE V3.1 - RESUMABLE SESSIONS")
        logger.info("="*80)
        logger.info(f"📝 Requirement: {requirement[:100]}...")
        logger.info(f"🆔 Session: {session.session_id}")
        logger.info(f"✅ Already completed: {', '.join(session.completed_personas) or 'None'}")
        logger.info(f"⏳ To execute: {', '.join(execution_order)}")
        logger.info(f"📁 Output: {self.output_dir}")
        logger.info("="*80)

        start_time = datetime.now()

        # Execute each pending persona
        for i, persona_id in enumerate(execution_order, 1):
            logger.info(f"\n{'='*80}")
            logger.info(f"🤖 [{i}/{len(execution_order)}] Executing: {persona_id}")
            logger.info(f"{'='*80}")

            persona_context = await self._execute_persona(
                persona_id,
                requirement,
                session
            )

            # Save persona execution to session
            session.add_persona_execution(
                persona_id=persona_id,
                files_created=persona_context.files_created,
                deliverables=persona_context.deliverables,
                duration=persona_context.duration(),
                success=persona_context.success
            )

            # Persist session after each persona (for resume capability)
            self.session_manager.save_session(session)

            if persona_context.success:
                logger.info(f"✅ {persona_id} completed: {len(persona_context.files_created)} files")
            else:
                logger.error(f"❌ {persona_id} failed: {persona_context.error}")

        # Build final result
        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds()

        result = {
            "success": True,
            "session_id": session.session_id,
            "requirement": requirement,
            "executed_personas": execution_order,
            "all_completed_personas": session.completed_personas,
            "files": session.get_all_files(),
            "file_count": len(session.get_all_files()),
            "project_dir": str(self.output_dir),
            "total_duration": total_duration,
            "resumable": True
        }

        logger.info("\n" + "="*80)
        logger.info("📊 EXECUTION SUMMARY")
        logger.info("="*80)
        logger.info(f"✅ Success: {result['success']}")
        logger.info(f"🆔 Session: {result['session_id']}")
        logger.info(f"👥 Executed in this run: {len(execution_order)}")
        logger.info(f"👥 Total completed: {len(session.completed_personas)}")
        logger.info(f"📁 Files created: {result['file_count']}")
        logger.info(f"⏱️  Duration: {total_duration:.2f}s")
        logger.info(f"📂 Output: {result['project_dir']}")
        logger.info(f"\n💡 Resume command:")
        logger.info(f"   python {Path(__file__).name} <new_personas> --resume {session.session_id}")
        logger.info("="*80)

        return result

    async def _execute_persona(
        self,
        persona_id: str,
        requirement: str,
        session: SDLCSession
    ) -> PersonaExecutionContext:
        """Execute a single persona with session context"""

        persona_context = PersonaExecutionContext(
            persona_id,
            requirement,
            self.output_dir
        )

        try:
            persona_config = self.persona_configs[persona_id]
            expected_deliverables = get_deliverables_for_persona(persona_id)

            # Build context from session history
            session_context = self.session_manager.get_session_context(session)
            prompt = self._build_persona_prompt(
                persona_config,
                requirement,
                expected_deliverables,
                session_context
            )

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
                if hasattr(message, 'message_type') and message.message_type == 'tool_use':
                    if hasattr(message, 'name') and message.name == 'Write':
                        file_path = message.input.get('file_path') if hasattr(message, 'input') else None
                        if file_path:
                            persona_context.add_file(file_path)
                            logger.debug(f"  📄 Created: {file_path}")

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
        session_context: str
    ) -> str:
        """Build prompt with session context"""

        persona_name = persona_config["name"]
        expertise = persona_config.get("expertise", [])

        prompt = f"""You are the {persona_name} for this project.

SESSION CONTEXT (work already done):
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

Work autonomously. Focus on your specialized domain.

Output directory: {self.output_dir}
"""

        return prompt


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
    """Main entry point"""
    import sys
    import argparse

    parser = argparse.ArgumentParser(
        description="Autonomous SDLC Engine V3.1 - Resumable Sessions",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('personas', nargs='*', help='Personas to execute')
    parser.add_argument('--requirement', help='Project requirement (for new sessions)')
    parser.add_argument('--session-id', help='Session ID for new session')
    parser.add_argument('--resume', help='Resume existing session by ID')
    parser.add_argument('--all-remaining', action='store_true', help='Execute all remaining personas (not yet completed)')
    parser.add_argument('--list-sessions', action='store_true', help='List all sessions')
    parser.add_argument('--output-dir', help='Output directory')

    args = parser.parse_args()

    session_manager = SessionManager()

    # List sessions
    if args.list_sessions:
        list_sessions(session_manager)
        return

    # Handle --all-remaining flag
    if args.all_remaining:
        if not args.resume:
            print("❌ Error: --all-remaining requires --resume")
            return

        # Load session to determine remaining personas
        session = session_manager.load_session(args.resume)
        if not session:
            print(f"❌ Error: Session not found: {args.resume}")
            return

        # Get all available personas
        all_available_personas = list(SDLCPersonas.get_all_personas().keys())

        # Filter out completed personas
        remaining_personas = [
            p for p in all_available_personas
            if p not in session.completed_personas
        ]

        if not remaining_personas:
            print(f"✅ All personas already completed in session {args.resume}!")
            return

        print(f"🔄 Resuming session: {args.resume}")
        print(f"📋 Remaining personas to execute ({len(remaining_personas)}):")
        print(f"   {', '.join(remaining_personas)}")

        args.personas = remaining_personas

    # Validate arguments
    if not args.personas and not args.all_remaining:
        parser.print_help()
        return

    # Resume existing session
    if args.resume:
        if not args.all_remaining:
            print(f"🔄 Resuming session: {args.resume}")

        engine = AutonomousSDLCEngineV3Resumable(
            selected_personas=args.personas,
            output_dir=args.output_dir,
            session_manager=session_manager
        )
        result = await engine.execute(
            requirement="",  # Will be loaded from session
            resume_session_id=args.resume
        )

    # Create new session
    else:
        if not args.requirement:
            print("❌ Error: --requirement is required for new sessions")
            return

        engine = AutonomousSDLCEngineV3Resumable(
            selected_personas=args.personas,
            output_dir=args.output_dir or "./generated_v3_project",
            session_manager=session_manager
        )
        result = await engine.execute(
            requirement=args.requirement,
            session_id=args.session_id
        )

    if result["success"]:
        print(f"\n✅ Execution completed!")
        print(f"🆔 Session: {result['session_id']}")
        print(f"📁 {result['file_count']} files")
        print(f"📂 Project: {result['project_dir']}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    asyncio.run(main())
