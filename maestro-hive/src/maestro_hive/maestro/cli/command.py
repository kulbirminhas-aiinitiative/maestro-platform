"""
Maestro CLI Command Handler

EPIC: MD-2502 - CLI Slash Command Interface (Sub-EPIC of MD-2493)

Handles /maestro slash command execution for Claude Code.

Usage:
    /maestro MD-2486         - Process EPIC from JIRA
    /maestro "Build API..."  - Ad-hoc requirement
    /maestro --resume <id>   - Continue previous session
    /maestro --status        - Show current execution status
"""

import asyncio
import argparse
import logging
import sys
from typing import Any, Dict, List, Optional

from ..orchestrator import UnifiedMaestroOrchestrator, ExecutionMode

logger = logging.getLogger(__name__)


class MaestroCommand:
    """
    Handler for the /maestro slash command.

    This class provides the entry point for the unified Maestro CLI,
    parsing arguments and delegating to UnifiedMaestroOrchestrator.
    """

    def __init__(self):
        """Initialize the command handler."""
        self.orchestrator: Optional[UnifiedMaestroOrchestrator] = None
        self._parser = self._create_parser()

    def _create_parser(self) -> argparse.ArgumentParser:
        """Create the argument parser for /maestro command."""
        parser = argparse.ArgumentParser(
            prog="/maestro",
            description="Unified Maestro CLI - SDLC Execution with Learning Loop",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
    /maestro MD-2486             Process JIRA EPIC MD-2486
    /maestro "Build API..."      Execute ad-hoc requirement
    /maestro --resume abc123     Resume previous session
    /maestro --status            Show current execution status
    /maestro --dry-run MD-2486   Preview execution plan
            """,
        )

        parser.add_argument(
            "input",
            nargs="?",
            help="EPIC key (e.g., MD-2486) or ad-hoc requirement text",
        )

        parser.add_argument(
            "--resume",
            metavar="SESSION_ID",
            help="Resume a previous execution session",
        )

        parser.add_argument(
            "--status",
            action="store_true",
            help="Show current execution status",
        )

        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview execution plan without running",
        )

        parser.add_argument(
            "--no-learning",
            action="store_true",
            help="Disable RAG-based learning loop",
        )

        parser.add_argument(
            "--stub-mode",
            action="store_true",
            help="Generate stubs instead of real code (for testing)",
        )

        parser.add_argument(
            "--output-dir",
            default="/tmp/maestro",
            help="Directory for generated artifacts",
        )

        parser.add_argument(
            "--verbose",
            "-v",
            action="store_true",
            help="Enable verbose logging",
        )

        return parser

    def parse_args(self, args: Optional[List[str]] = None) -> argparse.Namespace:
        """Parse command-line arguments."""
        return self._parser.parse_args(args)

    async def execute(self, args: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Execute the /maestro command.

        Args:
            args: Command-line arguments (uses sys.argv if None)

        Returns:
            Execution result dictionary
        """
        parsed = self.parse_args(args)

        # Configure logging
        if parsed.verbose:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)

        # Handle --status
        if parsed.status:
            return self._show_status()

        # Handle --resume
        if parsed.resume:
            return await self._resume_session(parsed.resume)

        # Require input for execution
        if not parsed.input:
            print(self._parser.format_help())
            return {"status": "error", "error": "No input provided"}

        # Initialize orchestrator
        self.orchestrator = UnifiedMaestroOrchestrator(
            output_dir=parsed.output_dir,
            enable_learning=not parsed.no_learning,
            enable_real_execution=not parsed.stub_mode,
        )

        # Handle --dry-run
        if parsed.dry_run:
            return self._dry_run(parsed.input)

        # Execute
        logger.info(f"Starting Maestro execution: {parsed.input}")
        result = await self.orchestrator.execute(parsed.input)

        return result

    def _show_status(self) -> Dict[str, Any]:
        """Show current execution status."""
        if not self.orchestrator or not self.orchestrator._current_state:
            return {"status": "idle", "message": "No active execution"}

        state = self.orchestrator._current_state
        return {
            "status": "running",
            "execution_id": state.execution_id,
            "current_phase": state.current_phase.name,
            "started_at": state.started_at.isoformat(),
        }

    async def _resume_session(self, session_id: str) -> Dict[str, Any]:
        """Resume a previous execution session."""
        if not self.orchestrator:
            self.orchestrator = UnifiedMaestroOrchestrator()

        return await self.orchestrator.resume(session_id)

    def _dry_run(self, input_value: str) -> Dict[str, Any]:
        """Preview execution plan without running."""
        mode = self.orchestrator._detect_mode(input_value)

        return {
            "status": "dry_run",
            "input_value": input_value,
            "detected_mode": mode.value,
            "execution_plan": [
                {"phase": 0, "name": "RAG_RETRIEVAL", "description": "Query similar past executions"},
                {"phase": 1, "name": "UNDERSTANDING", "description": "Parse EPIC, extract ACs"},
                {"phase": 2, "name": "DESIGN", "description": "11 Personas parallel design"},
                {"phase": 3, "name": "IMPLEMENTATION", "description": "Generate real code"},
                {"phase": 4, "name": "TESTING", "description": "Run actual tests"},
                {"phase": 5, "name": "TODO_AUDIT", "description": "TODO/FIXME verification"},
                {"phase": 6, "name": "BUILD", "description": "Build verification"},
                {"phase": 7, "name": "EVIDENCE", "description": "Semantic evidence matching"},
                {"phase": 8, "name": "COMPLIANCE", "description": "Self-check scoring"},
                {"phase": 9, "name": "UPDATE", "description": "Update EPIC & store learning"},
            ],
            "learning_enabled": self.orchestrator.enable_learning,
            "real_execution_enabled": self.orchestrator.enable_real_execution,
        }


def main():
    """Entry point for the /maestro command."""
    command = MaestroCommand()
    result = asyncio.run(command.execute())
    print(result)
    return 0 if result.get("status") != "error" else 1


if __name__ == "__main__":
    sys.exit(main())
