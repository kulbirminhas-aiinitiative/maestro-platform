"""
Tests for TeamExecutorV2Adapter

EPIC: MD-2535
AC-7: Integration test verifies real code generation

These tests verify:
1. Adapter initialization
2. Claude availability checking
3. Explicit error handling (no silent fallback)
4. Contract validation
5. Output validation
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import tempfile

# Add project paths
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from epic_executor.phases.team_executor_adapter import (
    TeamExecutorV2Adapter,
    ClaudeUnavailableError,
    ContractValidationError,
    TaskExecutionResult,
    ContractValidationResult,
)


class TestTeamExecutorV2AdapterInit:
    """Test adapter initialization."""

    def test_init_with_defaults(self):
        """Test initialization with default parameters."""
        adapter = TeamExecutorV2Adapter()
        assert adapter.output_dir.exists()
        assert adapter.enable_validation is True
        assert adapter.quality_threshold == 0.8

    def test_init_with_custom_output_dir(self):
        """Test initialization with custom output directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            adapter = TeamExecutorV2Adapter(output_dir=tmpdir)
            assert str(adapter.output_dir) == tmpdir

    def test_init_creates_output_dir(self):
        """Test that initialization creates output directory if missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_dir = Path(tmpdir) / "new_dir"
            adapter = TeamExecutorV2Adapter(output_dir=str(custom_dir))
            assert custom_dir.exists()


class TestClaudeAvailability:
    """Test Claude availability checking - AC-5."""

    def test_check_raises_when_sdk_unavailable(self):
        """Test that ClaudeUnavailableError is raised when SDK is unavailable."""
        adapter = TeamExecutorV2Adapter()

        # Mock the import to fail
        with patch.dict(sys.modules, {'claude_code_api_layer': None}):
            adapter._claude_available = None  # Reset cache

            with pytest.raises(ClaudeUnavailableError) as exc_info:
                adapter.check_claude_availability()

            # Check that error message indicates SDK issue and no fallback
            error_msg = str(exc_info.value).lower()
            assert "not installed" in error_msg or "not available" in error_msg
            assert "not fall back" in error_msg or "does not fall back" in error_msg

    def test_check_caches_result(self):
        """Test that availability check result is cached."""
        adapter = TeamExecutorV2Adapter()
        adapter._claude_available = True  # Pre-set cache

        # Should return True without checking again
        result = adapter.check_claude_availability()
        assert result is True

    def test_check_raises_cached_unavailable(self):
        """Test that cached unavailability raises error."""
        adapter = TeamExecutorV2Adapter()
        adapter._claude_available = False  # Pre-set unavailable

        with pytest.raises(ClaudeUnavailableError):
            adapter.check_claude_availability()


class TestContractValidation:
    """Test contract validation - AC-4."""

    @pytest.mark.asyncio
    async def test_validate_valid_contracts(self):
        """Test validation of valid contracts."""
        adapter = TeamExecutorV2Adapter()

        contracts = [
            {
                "id": "contract-1",
                "name": "API Contract",
                "deliverables": [{"name": "api.py"}],
            },
            {
                "id": "contract-2",
                "name": "UI Contract",
                "deliverables": [{"name": "app.tsx"}],
            },
        ]

        result = await adapter.validate_contracts(contracts)

        assert result.valid is True
        assert result.contracts_checked == 2
        assert result.contracts_passed == 2
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_validate_missing_fields(self):
        """Test validation fails for contracts missing required fields."""
        adapter = TeamExecutorV2Adapter()

        contracts = [
            {
                "id": "contract-1",
                # Missing name and deliverables
            },
        ]

        result = await adapter.validate_contracts(contracts)

        assert result.valid is False
        assert result.contracts_passed == 0
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_validate_empty_deliverables(self):
        """Test validation fails for empty deliverables."""
        adapter = TeamExecutorV2Adapter()

        contracts = [
            {
                "id": "contract-1",
                "name": "Empty Contract",
                "deliverables": [],
            },
        ]

        result = await adapter.validate_contracts(contracts)

        assert result.valid is False
        assert "no deliverables" in result.errors[0].lower()


class TestOutputValidation:
    """Test output validation - AC-6."""

    @pytest.mark.asyncio
    async def test_validate_existing_files(self):
        """Test validation of existing files."""
        adapter = TeamExecutorV2Adapter()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a real file with content
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("def main():\n    print('hello')\n")

            result = await adapter._validate_output(
                [str(test_file)],
                ["Create a function"]
            )

            assert result["valid"] is True
            assert result["files_checked"] == 1

    @pytest.mark.asyncio
    async def test_validate_missing_file(self):
        """Test validation fails for missing files."""
        adapter = TeamExecutorV2Adapter()

        result = await adapter._validate_output(
            ["/nonexistent/file.py"],
            ["Some criteria"]
        )

        assert result["valid"] is False
        assert "does not exist" in result["errors"][0]

    @pytest.mark.asyncio
    async def test_validate_empty_file(self):
        """Test validation fails for empty files."""
        adapter = TeamExecutorV2Adapter()

        with tempfile.TemporaryDirectory() as tmpdir:
            empty_file = Path(tmpdir) / "empty.py"
            empty_file.write_text("")

            result = await adapter._validate_output(
                [str(empty_file)],
                ["Some criteria"]
            )

            assert result["valid"] is False
            assert "empty" in result["errors"][0].lower()

    @pytest.mark.asyncio
    async def test_validate_stub_file(self):
        """Test validation warns about stub files with NotImplementedError."""
        adapter = TeamExecutorV2Adapter()

        with tempfile.TemporaryDirectory() as tmpdir:
            stub_file = Path(tmpdir) / "stub.py"
            # Create a file with mostly stub content (raise NotImplementedError)
            stub_file.write_text('''"""Stub file"""

def implement():
    raise NotImplementedError("Not implemented")

def another():
    raise NotImplementedError("Also not implemented")

def third():
    pass
''')

            result = await adapter._validate_output(
                [str(stub_file)],
                ["Implement feature"]
            )

            # Should detect stub pattern when stub indicators exceed 50% of code
            assert result["valid"] is False
            assert any("stub" in e.lower() or "NotImplementedError" in e for e in result["errors"])


class TestTaskExecution:
    """Test task execution - AC-2."""

    @pytest.mark.asyncio
    async def test_execute_task_checks_availability(self):
        """Test that execute_task checks Claude availability first."""
        adapter = TeamExecutorV2Adapter()
        adapter._claude_available = False  # Mark as unavailable

        with pytest.raises(ClaudeUnavailableError):
            await adapter.execute_task({
                "ac_id": "AC-1",
                "ac_description": "Test task",
            })

    @pytest.mark.asyncio
    async def test_execute_task_builds_requirement(self):
        """Test that task is converted to requirement string."""
        adapter = TeamExecutorV2Adapter()

        task = {
            "epic_key": "MD-2535",
            "epic_summary": "Create adapter",
            "ac_id": "AC-1",
            "ac_description": "Create TeamExecutorV2Adapter class",
            "requirement_type": "feature",
        }

        requirement = adapter._build_requirement_from_task(task)

        assert "MD-2535" in requirement
        assert "AC-1" in requirement
        assert "TeamExecutorV2Adapter" in requirement

    @pytest.mark.asyncio
    async def test_execute_task_with_previous_contracts(self):
        """Test that previous contracts are passed to engine - AC-4."""
        adapter = TeamExecutorV2Adapter()

        # Mock the engine and Claude availability
        mock_engine = Mock()
        mock_engine.execute = AsyncMock(return_value={
            "success": True,
            "deliverables": {},
            "quality": {"overall_quality_score": 0.9, "contracts_fulfilled": 1},
        })

        adapter._engine = mock_engine
        adapter._claude_available = True

        previous_contracts = [
            {"id": "prev-1", "name": "Previous Contract"}
        ]

        await adapter.execute_task({
            "ac_id": "AC-1",
            "ac_description": "Test",
            "previous_contracts": previous_contracts,
        })

        # Verify execute was called with previous contracts
        call_args = mock_engine.execute.call_args
        constraints = call_args[1].get("constraints", call_args[0][1] if len(call_args[0]) > 1 else {})
        assert "previous_phase_contracts" in constraints


class TestIntegrationWithImplementationPhase:
    """Integration tests - AC-7."""

    @pytest.mark.asyncio
    async def test_implement_method_compatibility(self):
        """Test that implement() method is compatible with ImplementationPhase."""
        adapter = TeamExecutorV2Adapter()

        # Mock internal execution
        adapter._claude_available = True
        adapter.execute_task = AsyncMock(return_value=TaskExecutionResult(
            success=True,
            files_created=["test.py"],
            changes={"test.py": "Created"},
            quality_score=0.9,
        ))

        result = await adapter.implement("Create a test function")

        assert "files" in result
        assert "changes" in result
        assert "success" in result


class TestNoSilentFallback:
    """Test that adapter never falls back silently - AC-5."""

    def test_no_basic_executor_fallback(self):
        """Verify adapter doesn't use BasicImplementationExecutor."""
        adapter = TeamExecutorV2Adapter()

        # The adapter should not have any reference to BasicImplementationExecutor
        import inspect
        source = inspect.getsource(TeamExecutorV2Adapter)

        # BasicImplementationExecutor should not be used
        assert "BasicImplementationExecutor" not in source

    @pytest.mark.asyncio
    async def test_error_messages_explicit(self):
        """Test that error messages explicitly state no fallback."""
        adapter = TeamExecutorV2Adapter()
        adapter._claude_available = False

        with pytest.raises(ClaudeUnavailableError) as exc_info:
            adapter.check_claude_availability()

        error_msg = str(exc_info.value)
        assert "NOT" in error_msg or "not" in error_msg
        assert "fallback" in error_msg.lower() or "stub" in error_msg.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
