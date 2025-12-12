"""
Tests for Enforcer Middleware Integration into PersonaExecutor

EPIC: MD-3126 - Integrate Enforcer Middleware into Persona Executor (Control)

Acceptance Criteria:
- AC-1: Attempting to write to a protected file (e.g., policy.yaml) throws GovernanceViolation
- AC-2: Attempting to use a forbidden tool (e.g., sudo) throws GovernanceViolation
- AC-3: Valid actions pass through with <10ms latency
- AC-4: Violations are logged to audit.log
"""

import asyncio
import json
import os
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

import pytest

from maestro_hive.unified_execution import (
    PersonaExecutor,
    GovernanceViolation,
    ExecutionStatus,
    get_execution_config,
)
from maestro_hive.governance.enforcer import (
    Enforcer,
    EnforcerResult,
    AgentContext,
    ViolationType,
)


class TestAC1ProtectedFileViolation:
    """AC-1: Attempting to write to a protected file throws GovernanceViolation."""

    @pytest.fixture
    def temp_audit_log(self):
        """Create a temporary audit log file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            yield f.name
        os.unlink(f.name)

    @pytest.fixture
    def enforcer_with_policy(self):
        """Create an Enforcer with test policy."""
        # Create a temporary policy file
        policy_content = """
file_protection:
  immutable_paths:
    - "*.env"
    - "policy.yaml"
    - "config/governance/*"
  protected_paths:
    - "*.yaml"
    - "src/*"
roles:
  developer_agent:
    forbidden_tools:
      - sudo
      - deploy_prod
      - rm_rf
    allowed_tools:
      - "*"
  architect_agent:
    forbidden_tools:
      - sudo
    allowed_tools:
      - "*"
global_constraints:
  max_recursion_depth: 5
  require_human_approval_for:
    - delete_database
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(policy_content)
            policy_path = f.name

        enforcer = Enforcer(policy_path=policy_path)
        yield enforcer
        os.unlink(policy_path)

    @pytest.mark.asyncio
    async def test_protected_file_write_throws_violation(self, enforcer_with_policy, temp_audit_log):
        """AC-1: Writing to policy.yaml throws GovernanceViolation."""
        executor = PersonaExecutor(
            persona_id="test_dev",
            persona_role="developer_agent",
            enforcer=enforcer_with_policy,
            audit_log_path=temp_audit_log,
        )

        async def write_file(path: str, content: str):
            return f"Written to {path}"

        with pytest.raises(GovernanceViolation) as exc_info:
            await executor.execute(
                write_file,
                "write_file",
                path="config/governance/policy.yaml",
                content="malicious: true"
            )

        assert exc_info.value.violation_type == "immutable_path"
        assert "policy.yaml" in str(exc_info.value) or "immutable" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_env_file_write_blocked(self, enforcer_with_policy, temp_audit_log):
        """AC-1: Writing to .env files throws GovernanceViolation."""
        executor = PersonaExecutor(
            persona_id="test_dev",
            persona_role="developer_agent",
            enforcer=enforcer_with_policy,
            audit_log_path=temp_audit_log,
        )

        async def edit_file(file_path: str, content: str):
            return f"Edited {file_path}"

        with pytest.raises(GovernanceViolation) as exc_info:
            await executor.execute(
                edit_file,
                "edit_file",
                file_path="/app/.env",
                content="SECRET_KEY=hacked"
            )

        assert exc_info.value.violation_type == "immutable_path"


class TestAC2ForbiddenToolViolation:
    """AC-2: Attempting to use a forbidden tool throws GovernanceViolation."""

    @pytest.fixture
    def temp_audit_log(self):
        """Create a temporary audit log file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            yield f.name
        os.unlink(f.name)

    @pytest.fixture
    def enforcer_with_policy(self):
        """Create an Enforcer with test policy."""
        policy_content = """
file_protection:
  immutable_paths:
    - "*.env"
roles:
  developer_agent:
    forbidden_tools:
      - sudo
      - deploy_prod
      - rm_rf
      - delete_database
    allowed_tools:
      - "*"
  architect_agent:
    forbidden_tools:
      - sudo
    allowed_tools:
      - "*"
global_constraints:
  max_recursion_depth: 5
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(policy_content)
            policy_path = f.name

        enforcer = Enforcer(policy_path=policy_path)
        yield enforcer
        os.unlink(policy_path)

    @pytest.mark.asyncio
    async def test_forbidden_tool_sudo_blocked(self, enforcer_with_policy, temp_audit_log):
        """AC-2: Using sudo tool throws GovernanceViolation for developer_agent."""
        executor = PersonaExecutor(
            persona_id="test_dev",
            persona_role="developer_agent",
            enforcer=enforcer_with_policy,
            audit_log_path=temp_audit_log,
        )

        async def sudo(command: str):
            return f"sudo: {command}"

        with pytest.raises(GovernanceViolation) as exc_info:
            await executor.execute(sudo, "sudo", command="rm -rf /")

        assert exc_info.value.violation_type == "forbidden_tool"
        assert exc_info.value.tool_name == "sudo"

    @pytest.mark.asyncio
    async def test_forbidden_tool_deploy_prod_blocked(self, enforcer_with_policy, temp_audit_log):
        """AC-2: Using deploy_prod tool throws GovernanceViolation for developer_agent."""
        executor = PersonaExecutor(
            persona_id="test_dev",
            persona_role="developer_agent",
            enforcer=enforcer_with_policy,
            audit_log_path=temp_audit_log,
        )

        async def deploy_prod(version: str):
            return f"Deployed v{version} to production"

        with pytest.raises(GovernanceViolation) as exc_info:
            await executor.execute(deploy_prod, "deploy_prod", version="1.0.0")

        assert exc_info.value.violation_type == "forbidden_tool"


class TestAC3ValidActionsLatency:
    """AC-3: Valid actions pass through with <10ms latency."""

    @pytest.fixture
    def temp_audit_log(self):
        """Create a temporary audit log file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            yield f.name
        os.unlink(f.name)

    @pytest.fixture
    def permissive_enforcer(self):
        """Create an Enforcer with permissive policy."""
        policy_content = """
file_protection:
  immutable_paths: []
  protected_paths: []
roles:
  developer_agent:
    forbidden_tools: []
    allowed_tools:
      - "*"
global_constraints:
  max_recursion_depth: 10
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(policy_content)
            policy_path = f.name

        enforcer = Enforcer(policy_path=policy_path)
        yield enforcer
        os.unlink(policy_path)

    @pytest.mark.asyncio
    async def test_valid_action_passes_with_low_latency(self, permissive_enforcer, temp_audit_log):
        """AC-3: Valid actions complete with <10ms governance overhead."""
        executor = PersonaExecutor(
            persona_id="test_dev",
            persona_role="developer_agent",
            enforcer=permissive_enforcer,
            audit_log_path=temp_audit_log,
        )

        async def read_file(path: str):
            return f"Content of {path}"

        # Measure total execution time
        start = time.perf_counter()
        result = await executor.execute(read_file, "read_file", path="/app/src/main.py")
        end = time.perf_counter()

        # Validate success
        assert result.success
        assert result.final_output == "Content of /app/src/main.py"

        # Check audit log for latency
        with open(temp_audit_log, 'r') as f:
            audit_entry = json.loads(f.readline())
            assert audit_entry['allowed'] is True
            assert audit_entry['latency_ms'] < 10.0, f"Latency {audit_entry['latency_ms']}ms exceeds 10ms"

    @pytest.mark.asyncio
    async def test_governance_check_under_10ms_average(self, permissive_enforcer, temp_audit_log):
        """AC-3: Multiple governance checks average under 10ms."""
        executor = PersonaExecutor(
            persona_id="test_dev",
            persona_role="developer_agent",
            enforcer=permissive_enforcer,
            audit_log_path=temp_audit_log,
        )

        async def dummy_task():
            return "done"

        latencies = []
        for i in range(10):
            start = time.perf_counter()
            result = await executor.execute(dummy_task, f"task_{i}")
            end = time.perf_counter()
            latencies.append((end - start) * 1000)  # Convert to ms

        # Read audit log to get governance check latencies
        with open(temp_audit_log, 'r') as f:
            for line in f:
                entry = json.loads(line)
                assert entry['latency_ms'] < 10.0, f"Governance check latency {entry['latency_ms']}ms exceeds 10ms"

        avg_latency = sum(latencies) / len(latencies)
        # Allow some margin for task overhead
        assert avg_latency < 50.0, f"Average execution latency {avg_latency}ms is too high"


class TestAC4AuditLogging:
    """AC-4: Violations are logged to audit.log."""

    @pytest.fixture
    def temp_audit_log(self):
        """Create a temporary audit log file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            yield f.name
        os.unlink(f.name)

    @pytest.fixture
    def enforcer_with_policy(self):
        """Create an Enforcer with test policy."""
        policy_content = """
file_protection:
  immutable_paths:
    - "*.env"
    - "policy.yaml"
roles:
  developer_agent:
    forbidden_tools:
      - sudo
      - deploy_prod
    allowed_tools:
      - "*"
global_constraints:
  max_recursion_depth: 5
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(policy_content)
            policy_path = f.name

        enforcer = Enforcer(policy_path=policy_path)
        yield enforcer
        os.unlink(policy_path)

    @pytest.mark.asyncio
    async def test_violation_logged_to_audit(self, enforcer_with_policy, temp_audit_log):
        """AC-4: GovernanceViolation events are logged to audit.log."""
        executor = PersonaExecutor(
            persona_id="test_dev",
            persona_role="developer_agent",
            enforcer=enforcer_with_policy,
            audit_log_path=temp_audit_log,
        )

        async def write_env(file_path: str):
            return "written"

        # Trigger violation
        with pytest.raises(GovernanceViolation):
            await executor.execute(write_env, "write_env", file_path="/app/.env")

        # Verify audit log contains violation
        with open(temp_audit_log, 'r') as f:
            audit_entry = json.loads(f.readline())

        assert audit_entry['persona_id'] == "test_dev"
        assert audit_entry['role'] == "developer_agent"
        assert audit_entry['allowed'] is False
        assert audit_entry['violation_type'] == "immutable_path"
        assert audit_entry['path'] == "/app/.env"
        assert 'timestamp' in audit_entry
        assert 'latency_ms' in audit_entry

    @pytest.mark.asyncio
    async def test_successful_action_logged_to_audit(self, enforcer_with_policy, temp_audit_log):
        """AC-4: Successful actions are also logged for audit trail."""
        executor = PersonaExecutor(
            persona_id="test_dev",
            persona_role="developer_agent",
            enforcer=enforcer_with_policy,
            audit_log_path=temp_audit_log,
        )

        async def read_file(path: str):
            return f"Content of {path}"

        result = await executor.execute(read_file, "read_file", path="/app/src/main.py")
        assert result.success

        # Verify audit log contains success entry
        with open(temp_audit_log, 'r') as f:
            audit_entry = json.loads(f.readline())

        assert audit_entry['persona_id'] == "test_dev"
        assert audit_entry['allowed'] is True
        assert audit_entry['violation_type'] is None

    @pytest.mark.asyncio
    async def test_audit_log_json_format(self, enforcer_with_policy, temp_audit_log):
        """AC-4: Audit log entries are valid JSON with expected fields."""
        executor = PersonaExecutor(
            persona_id="audit_test",
            persona_role="developer_agent",
            enforcer=enforcer_with_policy,
            audit_log_path=temp_audit_log,
        )

        async def some_task():
            return "done"

        await executor.execute(some_task, "some_task")

        with open(temp_audit_log, 'r') as f:
            audit_entry = json.loads(f.readline())

        # Verify required fields
        required_fields = ['timestamp', 'persona_id', 'role', 'tool', 'allowed', 'latency_ms']
        for field in required_fields:
            assert field in audit_entry, f"Missing required field: {field}"


class TestIntegration:
    """Integration tests for enforcer-executor combination."""

    @pytest.fixture
    def temp_audit_log(self):
        """Create a temporary audit log file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            yield f.name
        os.unlink(f.name)

    @pytest.fixture
    def enforcer_with_policy(self):
        """Create an Enforcer with test policy."""
        policy_content = """
file_protection:
  immutable_paths:
    - "*.env"
    - "policy.yaml"
  protected_paths:
    - "*.yaml"
roles:
  developer_agent:
    forbidden_tools:
      - sudo
      - deploy_prod
    allowed_tools:
      - "*"
  architect_agent:
    forbidden_tools: []
    allowed_tools:
      - "*"
global_constraints:
  max_recursion_depth: 5
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(policy_content)
            policy_path = f.name

        enforcer = Enforcer(policy_path=policy_path)
        yield enforcer
        os.unlink(policy_path)

    @pytest.mark.asyncio
    async def test_executor_without_enforcer_skips_governance(self, temp_audit_log):
        """PersonaExecutor without enforcer should skip governance checks."""
        executor = PersonaExecutor(
            persona_id="test_dev",
            persona_role="developer_agent",
            enforcer=None,  # No enforcer
            audit_log_path=temp_audit_log,
        )

        async def write_env(file_path: str):
            return "written"

        # Should succeed without enforcer
        result = await executor.execute(write_env, "write_env", file_path="/app/.env")
        assert result.success
        assert result.final_output == "written"

    @pytest.mark.asyncio
    async def test_architect_can_access_protected_paths(self, enforcer_with_policy, temp_audit_log):
        """Architect role should be able to access protected paths."""
        executor = PersonaExecutor(
            persona_id="test_architect",
            persona_role="architect_agent",
            enforcer=enforcer_with_policy,
            audit_log_path=temp_audit_log,
        )

        async def edit_config(file_path: str, content: str):
            return f"Edited {file_path}"

        # Protected path (yaml) should be accessible by architect
        result = await executor.execute(
            edit_config,
            "edit_config",
            file_path="/app/config/settings.yaml",
            content="updated: true"
        )
        assert result.success

    @pytest.mark.asyncio
    async def test_governance_violation_does_not_retry(self, enforcer_with_policy, temp_audit_log):
        """GovernanceViolation should fail immediately without retry."""
        executor = PersonaExecutor(
            persona_id="test_dev",
            persona_role="developer_agent",
            enforcer=enforcer_with_policy,
            audit_log_path=temp_audit_log,
        )

        call_count = 0

        async def sudo(command: str):
            nonlocal call_count
            call_count += 1
            return f"sudo: {command}"

        with pytest.raises(GovernanceViolation):
            await executor.execute(sudo, "sudo", command="whoami")

        # Should fail on first governance check, never calling the task
        assert call_count == 0, "Task should not be called when governance fails"


class TestEdgeCases:
    """Edge case tests."""

    @pytest.fixture
    def temp_audit_log(self):
        """Create a temporary audit log file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            yield f.name
        os.unlink(f.name)

    @pytest.mark.asyncio
    async def test_action_inference_write(self, temp_audit_log):
        """Test action type inference for write operations."""
        executor = PersonaExecutor(
            persona_id="test",
            persona_role="developer_agent",
            audit_log_path=temp_audit_log,
        )

        assert executor._infer_action_from_tool("write_file") == "write"
        assert executor._infer_action_from_tool("edit_content") == "write"
        assert executor._infer_action_from_tool("create_user") == "write"
        assert executor._infer_action_from_tool("update_config") == "write"

    @pytest.mark.asyncio
    async def test_action_inference_delete(self, temp_audit_log):
        """Test action type inference for delete operations."""
        executor = PersonaExecutor(
            persona_id="test",
            persona_role="developer_agent",
            audit_log_path=temp_audit_log,
        )

        assert executor._infer_action_from_tool("delete_file") == "delete"
        assert executor._infer_action_from_tool("remove_user") == "delete"
        assert executor._infer_action_from_tool("rm_cache") == "delete"

    @pytest.mark.asyncio
    async def test_action_inference_read(self, temp_audit_log):
        """Test action type inference for read operations."""
        executor = PersonaExecutor(
            persona_id="test",
            persona_role="developer_agent",
            audit_log_path=temp_audit_log,
        )

        assert executor._infer_action_from_tool("read_file") == "read"
        assert executor._infer_action_from_tool("get_user") == "read"
        assert executor._infer_action_from_tool("fetch_data") == "read"

    @pytest.mark.asyncio
    async def test_action_inference_default(self, temp_audit_log):
        """Test action type inference defaults to execute."""
        executor = PersonaExecutor(
            persona_id="test",
            persona_role="developer_agent",
            audit_log_path=temp_audit_log,
        )

        assert executor._infer_action_from_tool("run_tests") == "execute"
        assert executor._infer_action_from_tool("deploy") == "execute"
        assert executor._infer_action_from_tool("unknown_tool") == "execute"

    @pytest.mark.asyncio
    async def test_governance_violation_contains_context(self, temp_audit_log):
        """GovernanceViolation exception contains useful context."""
        policy_content = """
file_protection:
  immutable_paths:
    - "*.env"
roles:
  developer_agent:
    forbidden_tools:
      - sudo
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(policy_content)
            policy_path = f.name

        enforcer = Enforcer(policy_path=policy_path)

        executor = PersonaExecutor(
            persona_id="context_test",
            persona_role="developer_agent",
            enforcer=enforcer,
            audit_log_path=temp_audit_log,
        )

        async def sudo():
            return "executed"

        try:
            await executor.execute(sudo, "sudo")
            pytest.fail("Should have raised GovernanceViolation")
        except GovernanceViolation as e:
            assert e.tool_name == "sudo"
            assert e.agent_id == "context_test"
            assert e.violation_type == "forbidden_tool"
            # Test serialization
            d = e.to_dict()
            assert d['tool_name'] == "sudo"
            assert d['agent_id'] == "context_test"

        os.unlink(policy_path)
