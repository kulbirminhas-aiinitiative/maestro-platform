"""Command handler base class and registry."""
from abc import ABC, abstractmethod
from typing import Dict, Type
from .base_command import Command, CommandResult


class CommandHandler(ABC):
    """Base class for command handlers."""

    @abstractmethod
    async def handle(self, command: Command) -> CommandResult:
        """Handle a command."""
        pass


class CommandBus:
    """Command bus for routing commands to handlers."""

    def __init__(self):
        self._handlers: Dict[Type[Command], CommandHandler] = {}

    def register(self, command_type: Type[Command], handler: CommandHandler) -> None:
        """Register a command handler."""
        self._handlers[command_type] = handler

    async def dispatch(self, command: Command) -> CommandResult:
        """Dispatch a command to its handler."""
        command_type = type(command)

        if command_type not in self._handlers:
            return CommandResult(
                success=False,
                message=f"No handler registered for {command_type.__name__}"
            )

        handler = self._handlers[command_type]

        try:
            return await handler.handle(command)
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"Error handling command: {str(e)}",
                errors={"exception": str(e)}
            )