"""
Command Router
==============

Routes incoming commands to appropriate handlers based on input type.

Implements: AC-2 (Support EPIC ID or free-form requirement)
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Protocol, Any


class CommandType(Enum):
    """Type of command being processed."""
    EPIC_ID = "epic_id"
    REQUIREMENT = "requirement"
    RESUME = "resume"
    UNKNOWN = "unknown"


class Handler(Protocol):
    """Protocol for command handlers."""

    def process(self, input_str: str, session: Any) -> Any:
        """Process the input and return result."""
        ...

    def resume(self, session: Any) -> Any:
        """Resume processing from a checkpoint."""
        ...


@dataclass
class RouteResult:
    """Result of routing a command."""
    command_type: CommandType
    handler_name: str
    input_normalized: str


class CommandRouter:
    """
    Routes commands to appropriate handlers.

    Detects whether input is:
    - A JIRA EPIC ID (e.g., MD-2486, PROJ-123)
    - A free-form requirement text
    - A resume command

    Supports AC-2: Support EPIC ID or free-form requirement
    """

    # Pattern for JIRA issue keys (project key can be single letter)
    EPIC_ID_PATTERN = re.compile(r'^[A-Z][A-Z0-9]*-\d+$')

    # Pattern for resume command
    RESUME_PATTERN = re.compile(r'^--resume\s+(\S+)$')

    def __init__(self):
        """Initialize the command router."""
        self._handlers: dict[CommandType, str] = {
            CommandType.EPIC_ID: "EpicHandler",
            CommandType.REQUIREMENT: "RequirementHandler",
        }

    def detect_type(self, input_str: str) -> CommandType:
        """
        Detect the type of command from input string.

        Args:
            input_str: The raw input string

        Returns:
            CommandType indicating the detected type

        Examples:
            >>> router = CommandRouter()
            >>> router.detect_type("MD-2486")
            CommandType.EPIC_ID
            >>> router.detect_type("Build a REST API")
            CommandType.REQUIREMENT
        """
        if not input_str or not input_str.strip():
            return CommandType.UNKNOWN

        normalized = input_str.strip()

        # Check for EPIC ID pattern
        if self.EPIC_ID_PATTERN.match(normalized.upper()):
            return CommandType.EPIC_ID

        # Check for resume pattern
        if self.RESUME_PATTERN.match(normalized):
            return CommandType.RESUME

        # Default to requirement (free-form text)
        return CommandType.REQUIREMENT

    def route(self, input_str: str) -> RouteResult:
        """
        Route input to appropriate handler.

        Args:
            input_str: The raw input string

        Returns:
            RouteResult with command type and handler name
        """
        command_type = self.detect_type(input_str)
        normalized = self._normalize_input(input_str, command_type)

        handler_name = self._handlers.get(command_type, "UnknownHandler")

        return RouteResult(
            command_type=command_type,
            handler_name=handler_name,
            input_normalized=normalized,
        )

    def _normalize_input(self, input_str: str, command_type: CommandType) -> str:
        """
        Normalize input based on command type.

        Args:
            input_str: Raw input string
            command_type: Detected command type

        Returns:
            Normalized input string
        """
        if command_type == CommandType.EPIC_ID:
            # Uppercase EPIC IDs
            return input_str.strip().upper()
        elif command_type == CommandType.REQUIREMENT:
            # Strip quotes from requirements
            stripped = input_str.strip()
            if stripped.startswith('"') and stripped.endswith('"'):
                return stripped[1:-1]
            if stripped.startswith("'") and stripped.endswith("'"):
                return stripped[1:-1]
            return stripped
        else:
            return input_str.strip()

    def is_epic_id(self, input_str: str) -> bool:
        """
        Check if input is a valid EPIC ID.

        Args:
            input_str: String to check

        Returns:
            True if input matches EPIC ID pattern
        """
        return bool(self.EPIC_ID_PATTERN.match(input_str.strip().upper()))

    def is_requirement(self, input_str: str) -> bool:
        """
        Check if input should be treated as a requirement.

        Args:
            input_str: String to check

        Returns:
            True if input is free-form text (not an EPIC ID)
        """
        return self.detect_type(input_str) == CommandType.REQUIREMENT

    def extract_resume_session_id(self, input_str: str) -> str | None:
        """
        Extract session ID from resume command.

        Args:
            input_str: Resume command string

        Returns:
            Session ID or None if not a resume command
        """
        match = self.RESUME_PATTERN.match(input_str.strip())
        if match:
            return match.group(1)
        return None

    def validate_epic_id(self, epic_id: str) -> tuple[bool, str]:
        """
        Validate an EPIC ID format.

        Args:
            epic_id: The EPIC ID to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not epic_id:
            return False, "EPIC ID cannot be empty"

        normalized = epic_id.strip().upper()

        if not self.EPIC_ID_PATTERN.match(normalized):
            return False, f"Invalid EPIC ID format: {epic_id}. Expected format: PROJECT-NUMBER (e.g., MD-2486)"

        return True, ""

    def get_supported_types(self) -> list[CommandType]:
        """
        Get list of supported command types.

        Returns:
            List of supported CommandType values
        """
        return [CommandType.EPIC_ID, CommandType.REQUIREMENT, CommandType.RESUME]
