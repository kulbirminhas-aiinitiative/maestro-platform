"""
CLI Slash Command Interface Library
===================================

Unified /maestro command entry point for the Maestro platform.

Modules:
    - maestro_cli: Main CLI entry point
    - command_router: Command routing logic
    - epic_handler: JIRA EPIC processing
    - requirement_handler: Free-form requirement handling
    - session_manager: Session persistence and resume
    - progress_reporter: Progress reporting and status updates
"""

try:
    from .maestro_cli import MaestroCLI, main
    from .command_router import CommandRouter, CommandType
    from .epic_handler import EpicHandler, EpicResult
    from .requirement_handler import RequirementHandler, RequirementResult
    from .session_manager import SessionManager, Session, SessionStatus
    from .progress_reporter import ProgressReporter, ProgressEvent
except ImportError:
    from maestro_cli import MaestroCLI, main
    from command_router import CommandRouter, CommandType
    from epic_handler import EpicHandler, EpicResult
    from requirement_handler import RequirementHandler, RequirementResult
    from session_manager import SessionManager, Session, SessionStatus
    from progress_reporter import ProgressReporter, ProgressEvent

__all__ = [
    # Main CLI
    "MaestroCLI",
    "main",
    # Command routing
    "CommandRouter",
    "CommandType",
    # Handlers
    "EpicHandler",
    "EpicResult",
    "RequirementHandler",
    "RequirementResult",
    # Session management
    "SessionManager",
    "Session",
    "SessionStatus",
    # Progress reporting
    "ProgressReporter",
    "ProgressEvent",
]

__version__ = "1.0.0"
