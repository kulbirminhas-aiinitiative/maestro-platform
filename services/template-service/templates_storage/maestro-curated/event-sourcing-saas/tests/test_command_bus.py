"""Tests for command bus."""
import pytest
from uuid import uuid4
from src.backend.application.commands.base_command import Command, CommandResult
from src.backend.application.commands.command_handler import CommandHandler, CommandBus


class TestCommand(Command):
    """Test command."""
    value: str


class TestCommandHandler(CommandHandler):
    """Test command handler."""

    async def handle(self, command: TestCommand) -> CommandResult:
        """Handle test command."""
        return CommandResult(
            success=True,
            message=f"Handled: {command.value}"
        )


@pytest.fixture
def command_bus():
    """Create command bus."""
    bus = CommandBus()
    bus.register(TestCommand, TestCommandHandler())
    return bus


@pytest.mark.asyncio
async def test_command_dispatch(command_bus):
    """Test command dispatch."""
    command = TestCommand(
        command_id=uuid4(),
        tenant_id=uuid4(),
        value="test"
    )

    result = await command_bus.dispatch(command)

    assert result.success is True
    assert "Handled: test" in result.message


@pytest.mark.asyncio
async def test_unregistered_command(command_bus):
    """Test dispatch of unregistered command."""

    class UnregisteredCommand(Command):
        pass

    command = UnregisteredCommand(
        command_id=uuid4(),
        tenant_id=uuid4()
    )

    result = await command_bus.dispatch(command)

    assert result.success is False
    assert "No handler registered" in result.message