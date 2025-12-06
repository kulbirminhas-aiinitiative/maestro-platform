"""
Tests for MaestroCommand CLI handler

EPIC: MD-2502 - CLI Slash Command Interface
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from maestro_hive.maestro.cli.command import MaestroCommand


class TestArgumentParsing:
    """Test CLI argument parsing."""

    def test_parse_epic_key(self):
        """Should parse EPIC key argument."""
        cmd = MaestroCommand()
        args = cmd.parse_args(["MD-2493"])

        assert args.input == "MD-2493"
        assert args.resume is None
        assert args.status is False
        assert args.dry_run is False

    def test_parse_adhoc_requirement(self):
        """Should parse ad-hoc requirement argument."""
        cmd = MaestroCommand()
        args = cmd.parse_args(["Build a REST API"])

        assert args.input == "Build a REST API"

    def test_parse_resume_flag(self):
        """Should parse --resume flag with session ID."""
        cmd = MaestroCommand()
        args = cmd.parse_args(["--resume", "abc-123"])

        assert args.resume == "abc-123"

    def test_parse_status_flag(self):
        """Should parse --status flag."""
        cmd = MaestroCommand()
        args = cmd.parse_args(["--status"])

        assert args.status is True

    def test_parse_dry_run_flag(self):
        """Should parse --dry-run flag."""
        cmd = MaestroCommand()
        args = cmd.parse_args(["--dry-run", "MD-2493"])

        assert args.dry_run is True
        assert args.input == "MD-2493"

    def test_parse_no_learning_flag(self):
        """Should parse --no-learning flag."""
        cmd = MaestroCommand()
        args = cmd.parse_args(["--no-learning", "MD-2493"])

        assert args.no_learning is True

    def test_parse_stub_mode_flag(self):
        """Should parse --stub-mode flag."""
        cmd = MaestroCommand()
        args = cmd.parse_args(["--stub-mode", "MD-2493"])

        assert args.stub_mode is True

    def test_parse_output_dir(self):
        """Should parse --output-dir option."""
        cmd = MaestroCommand()
        args = cmd.parse_args(["--output-dir", "/custom/path", "MD-2493"])

        assert args.output_dir == "/custom/path"

    def test_parse_verbose_flag(self):
        """Should parse -v/--verbose flag."""
        cmd = MaestroCommand()

        args = cmd.parse_args(["-v", "MD-2493"])
        assert args.verbose is True

        args = cmd.parse_args(["--verbose", "MD-2493"])
        assert args.verbose is True


class TestStatusCommand:
    """Test --status command."""

    def test_status_when_idle(self):
        """Should return idle status when no execution is running."""
        cmd = MaestroCommand()
        result = cmd._show_status()

        assert result["status"] == "idle"
        assert "message" in result


class TestDryRun:
    """Test --dry-run command."""

    @pytest.mark.asyncio
    async def test_dry_run_epic(self):
        """Dry run should show execution plan for EPIC."""
        cmd = MaestroCommand()
        result = await cmd.execute(["--dry-run", "MD-2493"])

        assert result["status"] == "dry_run"
        assert result["input_value"] == "MD-2493"
        assert result["detected_mode"] == "epic"
        assert "execution_plan" in result
        assert len(result["execution_plan"]) == 10

    @pytest.mark.asyncio
    async def test_dry_run_adhoc(self):
        """Dry run should show execution plan for ad-hoc requirement."""
        cmd = MaestroCommand()
        result = await cmd.execute(["--dry-run", "Build a feature"])

        assert result["status"] == "dry_run"
        assert result["detected_mode"] == "adhoc"


class TestNoInputHandling:
    """Test handling of missing input."""

    @pytest.mark.asyncio
    async def test_no_input_shows_help(self):
        """Should return error when no input provided."""
        cmd = MaestroCommand()
        result = await cmd.execute([])

        assert result["status"] == "error"
        assert "No input provided" in result["error"]


class TestCommandIntegration:
    """Integration tests for command execution."""

    @pytest.mark.asyncio
    async def test_execute_with_flags(self):
        """Should respect all flags during execution."""
        cmd = MaestroCommand()

        with patch.object(cmd, 'orchestrator') as mock_orch:
            mock_orch.execute = AsyncMock(return_value={"status": "completed"})
            mock_orch._detect_mode = MagicMock(return_value="epic")
            mock_orch.enable_learning = False
            mock_orch.enable_real_execution = False

            result = await cmd.execute(["--dry-run", "--no-learning", "--stub-mode", "MD-2493"])

            # Dry run should return plan without actual execution
            assert result["status"] == "dry_run"
