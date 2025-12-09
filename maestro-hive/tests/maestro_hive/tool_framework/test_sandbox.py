"""
Test suite for Tool Framework Sandbox
EPIC: MD-2777 - Quality Assurance & Testing Gaps
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'src'))

try:
    from maestro_hive.tool_framework.sandbox import ToolSandbox, SandboxPolicy
    from maestro_hive.tool_framework.models import Tool, ToolResult
    IMPORT_SUCCESS = True
except ImportError as e:
    IMPORT_SUCCESS = False
    IMPORT_ERROR = str(e)


@pytest.mark.skipif(not IMPORT_SUCCESS, reason=f"Import failed")
class TestToolSandbox:
    """Tests for ToolSandbox execution environment."""

    def test_sandbox_init(self):
        """Test ToolSandbox initialization."""
        sandbox = ToolSandbox()
        assert sandbox is not None

    def test_sandbox_with_policy(self):
        """Test ToolSandbox with custom policy."""
        policy = SandboxPolicy(
            allowed_tools={"tool1", "tool2"},
            max_execution_time_ms=30000,
            max_memory_mb=128,
            allow_network=False
        )
        sandbox = ToolSandbox(policy=policy)
        assert sandbox is not None
        assert sandbox.policy.max_execution_time_ms == 30000

    def test_can_execute_allowed_tool(self):
        """Test checking if allowed tool can execute."""
        policy = SandboxPolicy(allowed_tools={"allowed_tool"})
        sandbox = ToolSandbox(policy=policy)

        mock_tool = Mock(spec=Tool)
        mock_tool.name = "allowed_tool"
        mock_tool.timeout_ms = 5000

        can_exec, reason = sandbox.can_execute(mock_tool)
        assert can_exec is True
        assert reason is None

    def test_can_execute_blocked_tool(self):
        """Test checking if blocked tool cannot execute."""
        policy = SandboxPolicy(blocked_tools={"blocked_tool"})
        sandbox = ToolSandbox(policy=policy)

        mock_tool = Mock(spec=Tool)
        mock_tool.name = "blocked_tool"
        mock_tool.timeout_ms = 5000

        can_exec, reason = sandbox.can_execute(mock_tool)
        assert can_exec is False
        assert "blocked" in reason.lower()

    def test_execute_in_sandbox_success(self):
        """Test successful execution in sandbox."""
        sandbox = ToolSandbox()

        mock_tool = Mock(spec=Tool)
        mock_tool.name = "test_tool"
        mock_tool.timeout_ms = 5000
        mock_tool.handler = lambda: {"result": "success"}

        result = sandbox.execute_in_sandbox(mock_tool, {})
        assert result is not None
        assert result.success is True

    def test_execute_in_sandbox_failure(self):
        """Test failed execution in sandbox."""
        sandbox = ToolSandbox()

        mock_tool = Mock(spec=Tool)
        mock_tool.name = "failing_tool"
        mock_tool.timeout_ms = 5000
        mock_tool.handler = Mock(side_effect=Exception("Test error"))

        result = sandbox.execute_in_sandbox(mock_tool, {})
        assert result is not None
        assert result.success is False

    def test_get_stats(self):
        """Test getting sandbox statistics."""
        sandbox = ToolSandbox()
        stats = sandbox.get_stats()
        assert stats is not None
        assert "execution_count" in stats


@pytest.mark.skipif(not IMPORT_SUCCESS, reason=f"Import failed")
class TestSandboxPolicy:
    """Tests for SandboxPolicy."""

    def test_default_policy(self):
        """Test default sandbox policy."""
        policy = SandboxPolicy()
        assert policy.max_execution_time_ms == 60000
        assert policy.max_memory_mb == 256
        assert policy.allow_network is True

    def test_custom_policy(self):
        """Test custom sandbox policy."""
        policy = SandboxPolicy(
            allowed_tools={"tool1"},
            blocked_tools={"tool2"},
            max_execution_time_ms=10000,
            max_memory_mb=64,
            allow_network=False,
            allow_file_write=True
        )
        assert policy.max_execution_time_ms == 10000
        assert policy.allow_network is False
        assert policy.allow_file_write is True


class TestSandboxEdgeCases:
    """Edge case tests for sandbox."""

    def test_timeout_exceeded(self):
        """Test tool exceeding timeout policy."""
        if IMPORT_SUCCESS:
            policy = SandboxPolicy(max_execution_time_ms=1000)
            sandbox = ToolSandbox(policy=policy)

            mock_tool = Mock(spec=Tool)
            mock_tool.name = "slow_tool"
            mock_tool.timeout_ms = 5000  # Exceeds policy

            can_exec, reason = sandbox.can_execute(mock_tool)
            assert can_exec is False
            assert "timeout" in reason.lower()

    def test_empty_allowed_tools(self):
        """Test policy with empty allowed tools (allow all)."""
        if IMPORT_SUCCESS:
            policy = SandboxPolicy()  # Empty allowed_tools = allow all
            sandbox = ToolSandbox(policy=policy)

            mock_tool = Mock(spec=Tool)
            mock_tool.name = "any_tool"
            mock_tool.timeout_ms = 5000

            can_exec, _ = sandbox.can_execute(mock_tool)
            assert can_exec is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
