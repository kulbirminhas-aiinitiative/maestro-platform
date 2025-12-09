"""
Maestro CLI - Main Entry Point
==============================

Implements the unified /maestro command that replaces epic-execute
and team_execution_v2 as a single entry point.

Usage:
    /maestro MD-2486         # Process EPIC from JIRA
    /maestro "Build API..."  # Ad-hoc requirement
    /maestro --resume <id>   # Continue previous session

Implements: AC-1 (Single command replaces epic-execute and team_execution_v2)
"""

import argparse
import sys
from dataclasses import dataclass
from enum import Enum
from typing import Optional

try:
    from .command_router import CommandRouter, CommandType
    from .epic_handler import EpicHandler
    from .requirement_handler import RequirementHandler
    from .session_manager import SessionManager, Session
    from .progress_reporter import ProgressReporter
except ImportError:
    from command_router import CommandRouter, CommandType
    from epic_handler import EpicHandler
    from requirement_handler import RequirementHandler
    from session_manager import SessionManager, Session
    from progress_reporter import ProgressReporter


class ExecutionStatus(Enum):
    """Status of command execution."""
    SUCCESS = "success"
    FAILED = "failed"
    IN_PROGRESS = "in_progress"
    RESUMED = "resumed"


@dataclass
class ExecutionResult:
    """Result of a maestro command execution."""
    status: ExecutionStatus
    session_id: str
    message: str
    score: Optional[float] = None
    artifacts: Optional[dict] = None
    error: Optional[str] = None


class MaestroCLI:
    """
    Main CLI class for the /maestro command.

    Provides a unified interface for:
    - Processing JIRA EPICs
    - Handling ad-hoc requirements
    - Resuming previous sessions
    - Reporting progress
    """

    def __init__(
        self,
        session_manager: Optional[SessionManager] = None,
        progress_reporter: Optional[ProgressReporter] = None,
    ):
        """
        Initialize the Maestro CLI.

        Args:
            session_manager: Optional session manager instance
            progress_reporter: Optional progress reporter instance
        """
        self.router = CommandRouter()
        self.session_manager = session_manager or SessionManager()
        self.progress_reporter = progress_reporter or ProgressReporter()
        self.epic_handler = EpicHandler()
        self.requirement_handler = RequirementHandler()

    def execute(self, input_str: str) -> ExecutionResult:
        """
        Execute a maestro command.

        This is the main entry point that replaces both epic-execute
        and team_execution_v2.

        Args:
            input_str: The input string (EPIC ID or requirement text)

        Returns:
            ExecutionResult with status, session_id, and any artifacts
        """
        # Create new session
        session = self.session_manager.create_session()
        self.progress_reporter.start(total_steps=10)

        try:
            # Route the command
            self.progress_reporter.update(1, "Analyzing input...")
            command_type = self.router.detect_type(input_str)
            handler = self.router.route(input_str)

            # Execute based on type
            self.progress_reporter.update(2, f"Processing as {command_type.value}...")

            if command_type == CommandType.EPIC_ID:
                result = self.epic_handler.process(input_str, session)
            elif command_type == CommandType.REQUIREMENT:
                result = self.requirement_handler.process(input_str, session)
            else:
                raise ValueError(f"Unknown command type: {command_type}")

            # Save checkpoint
            self.progress_reporter.update(9, "Saving session...")
            self.session_manager.save_checkpoint(session)

            # Complete
            self.progress_reporter.update(10, "Complete!")

            execution_result = ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                session_id=session.session_id,
                message=f"Successfully processed {command_type.value}",
                score=result.score if hasattr(result, 'score') else None,
                artifacts=result.artifacts if hasattr(result, 'artifacts') else None,
            )

            self.progress_reporter.complete(execution_result)
            return execution_result

        except Exception as e:
            self.session_manager.save_checkpoint(session)
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                session_id=session.session_id,
                message="Execution failed",
                error=str(e),
            )

    def resume(self, session_id: str) -> ExecutionResult:
        """
        Resume a previous session.

        Implements AC-3: Resume capability for long-running executions.

        Args:
            session_id: The session ID to resume

        Returns:
            ExecutionResult with resumed session status
        """
        try:
            session = self.session_manager.load_session(session_id)
            self.progress_reporter.start(total_steps=10)
            self.progress_reporter.update(
                session.current_step,
                f"Resuming from step {session.current_step}..."
            )

            # Continue execution from checkpoint
            if session.command_type == CommandType.EPIC_ID:
                result = self.epic_handler.resume(session)
            else:
                result = self.requirement_handler.resume(session)

            self.session_manager.save_checkpoint(session)

            execution_result = ExecutionResult(
                status=ExecutionStatus.RESUMED,
                session_id=session.session_id,
                message=f"Resumed session from step {session.current_step}",
                score=result.score if hasattr(result, 'score') else None,
                artifacts=result.artifacts if hasattr(result, 'artifacts') else None,
            )

            self.progress_reporter.complete(execution_result)
            return execution_result

        except FileNotFoundError:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                session_id=session_id,
                message="Session not found",
                error=f"Session {session_id} does not exist",
            )

    def get_status(self, session_id: str) -> dict:
        """
        Get status of a session.

        Args:
            session_id: The session ID to check

        Returns:
            Status dictionary with session details
        """
        try:
            session = self.session_manager.load_session(session_id)
            return {
                "session_id": session.session_id,
                "status": session.status.value,
                "current_step": session.current_step,
                "total_steps": session.total_steps,
                "started_at": session.started_at.isoformat(),
                "last_updated": session.last_updated.isoformat(),
            }
        except FileNotFoundError:
            return {
                "session_id": session_id,
                "status": "not_found",
                "error": f"Session {session_id} does not exist",
            }

    def health_check(self) -> dict:
        """
        Perform health check.

        Returns:
            Health status dictionary
        """
        return {
            "status": "healthy",
            "version": "1.0.0",
            "components": {
                "router": "ok",
                "epic_handler": "ok",
                "requirement_handler": "ok",
                "session_manager": "ok",
                "progress_reporter": "ok",
            }
        }


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="maestro",
        description="Unified Maestro CLI - Single entry point for EPIC and requirement processing",
    )

    parser.add_argument(
        "input",
        nargs="?",
        help="EPIC ID (e.g., MD-2486) or requirement text in quotes",
    )

    parser.add_argument(
        "--resume",
        metavar="SESSION_ID",
        help="Resume a previous session",
    )

    parser.add_argument(
        "--status",
        metavar="SESSION_ID",
        help="Check status of a session",
    )

    parser.add_argument(
        "--health",
        action="store_true",
        help="Perform health check",
    )

    parser.add_argument(
        "--list-sessions",
        action="store_true",
        help="List all sessions",
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output",
    )

    return parser


def main(args: Optional[list] = None) -> int:
    """
    Main entry point for the maestro CLI.

    Args:
        args: Command line arguments (uses sys.argv if None)

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    parser = create_parser()
    parsed = parser.parse_args(args)

    cli = MaestroCLI()

    # Health check
    if parsed.health:
        import json
        print(json.dumps(cli.health_check(), indent=2))
        return 0

    # List sessions
    if parsed.list_sessions:
        sessions = cli.session_manager.list_sessions()
        for session in sessions:
            print(f"{session.session_id}: {session.status.value} (step {session.current_step}/{session.total_steps})")
        return 0

    # Check status
    if parsed.status:
        import json
        status = cli.get_status(parsed.status)
        print(json.dumps(status, indent=2))
        return 0

    # Resume session
    if parsed.resume:
        result = cli.resume(parsed.resume)
        if result.status == ExecutionStatus.FAILED:
            print(f"Error: {result.error}", file=sys.stderr)
            return 1
        print(f"Session {result.session_id}: {result.message}")
        return 0

    # Execute new command
    if parsed.input:
        result = cli.execute(parsed.input)
        if result.status == ExecutionStatus.FAILED:
            print(f"Error: {result.error}", file=sys.stderr)
            return 1
        print(f"Session {result.session_id}: {result.message}")
        if result.score is not None:
            print(f"Score: {result.score}")
        return 0

    # No input provided
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
