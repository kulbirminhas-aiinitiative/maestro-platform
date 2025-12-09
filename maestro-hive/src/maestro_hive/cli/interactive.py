#!/usr/bin/env python3
"""
Interactive CLI: Provides an interactive command-line interface.

This module handles:
- Interactive mode for user sessions
- Command completion and history
- Progress indication during operations
- Help documentation display
"""

import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
import uuid

logger = logging.getLogger(__name__)


class PromptStyle(Enum):
    """Prompt display styles."""
    DEFAULT = "default"
    MINIMAL = "minimal"
    VERBOSE = "verbose"


class ProgressStyle(Enum):
    """Progress indicator styles."""
    SPINNER = "spinner"
    BAR = "bar"
    DOTS = "dots"
    NONE = "none"


@dataclass
class Command:
    """A CLI command definition."""
    name: str
    description: str
    handler: Callable
    aliases: List[str] = field(default_factory=list)
    arguments: List[Dict[str, Any]] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)


@dataclass
class CommandResult:
    """Result of command execution."""
    success: bool
    output: str
    error: Optional[str] = None
    execution_time_ms: float = 0.0


@dataclass
class SessionState:
    """State of an interactive session."""
    session_id: str
    started_at: datetime
    command_history: List[str] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    current_context: Optional[str] = None


class ProgressIndicator:
    """
    Displays progress during operations.

    Implements progress_indication.
    """

    SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self, style: ProgressStyle = ProgressStyle.SPINNER):
        """Initialize progress indicator."""
        self.style = style
        self._frame = 0
        self._total = 0
        self._current = 0
        self._message = ""
        self._running = False

    def start(self, message: str = "", total: int = 0) -> None:
        """Start progress indication."""
        self._message = message
        self._total = total
        self._current = 0
        self._running = True
        self._render()

    def update(self, current: int = None, message: str = None) -> None:
        """Update progress."""
        if current is not None:
            self._current = current
        if message is not None:
            self._message = message
        self._render()

    def increment(self, amount: int = 1) -> None:
        """Increment progress by amount."""
        self._current += amount
        self._render()

    def stop(self, message: str = None) -> None:
        """Stop progress indication."""
        self._running = False
        if message:
            print(f"\r{message}        ")
        else:
            print("\r" + " " * 50 + "\r", end="")

    def _render(self) -> None:
        """Render the progress indicator."""
        if not self._running:
            return

        if self.style == ProgressStyle.SPINNER:
            frame = self.SPINNER_FRAMES[self._frame % len(self.SPINNER_FRAMES)]
            self._frame += 1
            print(f"\r{frame} {self._message}", end="", flush=True)

        elif self.style == ProgressStyle.BAR:
            if self._total > 0:
                pct = self._current / self._total
                filled = int(20 * pct)
                bar = "█" * filled + "░" * (20 - filled)
                print(f"\r[{bar}] {pct*100:.0f}% {self._message}", end="", flush=True)
            else:
                print(f"\r[...] {self._message}", end="", flush=True)

        elif self.style == ProgressStyle.DOTS:
            dots = "." * ((self._frame % 3) + 1)
            self._frame += 1
            print(f"\r{self._message}{dots}   ", end="", flush=True)


class InteractiveCLI:
    """
    Interactive CLI for Maestro.

    Implements:
    - interactive_mode: Interactive command session
    - cli_usability: User-friendly command interface
    - help_documentation: Display command help
    - config_management: Manage configuration settings
    """

    def __init__(self, prompt: str = "maestro> "):
        """Initialize the interactive CLI."""
        self.prompt = prompt
        self.style = PromptStyle.DEFAULT
        self._commands: Dict[str, Command] = {}
        self._session: Optional[SessionState] = None
        self._config: Dict[str, Any] = {}

        # Register built-in commands
        self._register_builtins()

    def _register_builtins(self) -> None:
        """Register built-in commands."""
        self.register_command(Command(
            name="help",
            description="Display help information",
            handler=self._cmd_help,
            aliases=["?", "h"],
            examples=["help", "help run"]
        ))

        self.register_command(Command(
            name="exit",
            description="Exit interactive mode",
            handler=self._cmd_exit,
            aliases=["quit", "q"]
        ))

        self.register_command(Command(
            name="history",
            description="Show command history",
            handler=self._cmd_history
        ))

        self.register_command(Command(
            name="config",
            description="Manage configuration",
            handler=self._cmd_config,
            examples=["config get key", "config set key value"]
        ))

        self.register_command(Command(
            name="clear",
            description="Clear the screen",
            handler=self._cmd_clear
        ))

    def register_command(self, command: Command) -> None:
        """Register a command."""
        self._commands[command.name] = command
        for alias in command.aliases:
            self._commands[alias] = command

    def start_session(self) -> SessionState:
        """
        Start an interactive session.

        Implements interactive_mode.
        """
        self._session = SessionState(
            session_id=str(uuid.uuid4()),
            started_at=datetime.utcnow()
        )

        print("Maestro Interactive CLI")
        print("Type 'help' for available commands, 'exit' to quit")
        print()

        return self._session

    def run(self) -> None:
        """Run the interactive loop."""
        if not self._session:
            self.start_session()

        while True:
            try:
                # Get input
                user_input = input(self.prompt).strip()

                if not user_input:
                    continue

                # Add to history
                self._session.command_history.append(user_input)

                # Parse and execute
                result = self.execute(user_input)

                # Handle exit
                if result and result.output == "__EXIT__":
                    break

                # Display result
                if result:
                    if result.success:
                        if result.output:
                            print(result.output)
                    else:
                        print(f"Error: {result.error}")

            except KeyboardInterrupt:
                print("\nUse 'exit' to quit")
            except EOFError:
                break

        print("Goodbye!")

    def execute(self, input_str: str) -> CommandResult:
        """Execute a command string."""
        import time
        start = time.time()

        # Parse input
        parts = input_str.split()
        if not parts:
            return CommandResult(success=True, output="")

        cmd_name = parts[0].lower()
        args = parts[1:]

        # Find command
        command = self._commands.get(cmd_name)
        if not command:
            return CommandResult(
                success=False,
                output="",
                error=f"Unknown command: {cmd_name}. Type 'help' for available commands."
            )

        # Execute
        try:
            output = command.handler(args)
            return CommandResult(
                success=True,
                output=output or "",
                execution_time_ms=(time.time() - start) * 1000
            )
        except Exception as e:
            logger.error(f"Command error: {e}")
            return CommandResult(
                success=False,
                output="",
                error=str(e),
                execution_time_ms=(time.time() - start) * 1000
            )

    def _cmd_help(self, args: List[str]) -> str:
        """
        Display help information.

        Implements help_documentation.
        """
        if args:
            # Help for specific command
            cmd_name = args[0]
            command = self._commands.get(cmd_name)
            if command:
                lines = [
                    f"Command: {command.name}",
                    f"Description: {command.description}",
                ]
                if command.aliases:
                    lines.append(f"Aliases: {', '.join(command.aliases)}")
                if command.examples:
                    lines.append("Examples:")
                    for ex in command.examples:
                        lines.append(f"  {ex}")
                return "\n".join(lines)
            else:
                return f"Unknown command: {cmd_name}"

        # General help
        lines = ["Available Commands:", ""]

        # Get unique commands (exclude aliases)
        seen = set()
        for cmd in self._commands.values():
            if cmd.name not in seen:
                seen.add(cmd.name)
                aliases = f" ({', '.join(cmd.aliases)})" if cmd.aliases else ""
                lines.append(f"  {cmd.name}{aliases}: {cmd.description}")

        return "\n".join(lines)

    def _cmd_exit(self, args: List[str]) -> str:
        """Exit the CLI."""
        return "__EXIT__"

    def _cmd_history(self, args: List[str]) -> str:
        """Show command history."""
        if not self._session or not self._session.command_history:
            return "No command history"

        lines = []
        for i, cmd in enumerate(self._session.command_history[-20:], 1):
            lines.append(f"{i:3}  {cmd}")
        return "\n".join(lines)

    def _cmd_config(self, args: List[str]) -> str:
        """
        Manage configuration.

        Implements config_management.
        """
        if not args:
            # Show all config
            if not self._config:
                return "No configuration set"
            lines = ["Configuration:"]
            for k, v in self._config.items():
                lines.append(f"  {k} = {v}")
            return "\n".join(lines)

        action = args[0]
        if action == "get" and len(args) >= 2:
            key = args[1]
            value = self._config.get(key)
            return f"{key} = {value}" if value is not None else f"Key not found: {key}"

        elif action == "set" and len(args) >= 3:
            key = args[1]
            value = " ".join(args[2:])
            self._config[key] = value
            return f"Set {key} = {value}"

        elif action == "delete" and len(args) >= 2:
            key = args[1]
            if key in self._config:
                del self._config[key]
                return f"Deleted: {key}"
            return f"Key not found: {key}"

        return "Usage: config [get|set|delete] <key> [value]"

    def _cmd_clear(self, args: List[str]) -> str:
        """Clear the screen."""
        print("\033[2J\033[H", end="")
        return ""

    def get_completions(self, text: str) -> List[str]:
        """Get command completions for text."""
        if not text:
            return list(self._commands.keys())
        return [c for c in self._commands.keys() if c.startswith(text.lower())]

    def set_variable(self, name: str, value: Any) -> None:
        """Set a session variable."""
        if self._session:
            self._session.variables[name] = value

    def get_variable(self, name: str) -> Optional[Any]:
        """Get a session variable."""
        if self._session:
            return self._session.variables.get(name)
        return None


# Factory function
def create_interactive_cli(prompt: str = "maestro> ") -> InteractiveCLI:
    """Create a new InteractiveCLI instance."""
    return InteractiveCLI(prompt=prompt)


# Convenience functions
def create_progress(style: ProgressStyle = ProgressStyle.SPINNER) -> ProgressIndicator:
    """Create a progress indicator."""
    return ProgressIndicator(style=style)
