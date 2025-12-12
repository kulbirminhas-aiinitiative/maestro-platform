"""
Test Suite for EnforcerMiddleware (MD-3116)

Comprehensive tests for all 5 Acceptance Criteria:
- AC-1: Immutable Protection - Attempting to edit .env returns PermissionError
- AC-2: Role Restriction - A developer_agent attempting deploy_prod is blocked
- AC-3: Budget Check - An agent with $0.00 remaining budget is blocked
- AC-4: Performance - Overhead per call is < 10ms
- AC-5: Fail-Safe - If the policy file is corrupted, ALL actions are blocked

EPIC: MD-3116 - Implement Enforcer Middleware (Synchronous Governance)
"""

import os
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from maestro_hive.governance.enforcer import (
    AgentAction,
    AgentContext,
    BudgetExceededError,
    Enforcer,
    EnforcerMiddleware,
    EnforcerResult,
    PolicyLoadError,
    ViolationType,
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def valid_policy_file():
    """Create a valid policy file for testing."""
    policy_content = {
        "global_constraints": {
            "max_daily_budget_usd": 50.0,
            "max_concurrent_agents": 10,
            "max_recursion_depth": 5,
            "require_human_approval_for": ["deploy_prod", "delete_database"],
        },
        "file_protection": {
            "immutable_paths": [".env", ".env.*", "*.pem", "*.key"],
            "protected_paths": ["src/core/*", "pyproject.toml"],
        },
        "roles": {
            "developer_agent": {
                "max_tokens_per_run": 20000,
                "allowed_tools": ["read_file", "create_file", "edit_file", "run_test"],
                "forbidden_tools": ["deploy_prod", "delete_database", "modify_policy"],
            },
            "architect_agent": {
                "max_tokens_per_run": 100000,
                "allowed_tools": ["*"],
                "forbidden_tools": ["modify_policy"],
            },
        },
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(policy_content, f)
        f.flush()
        yield f.name

    os.unlink(f.name)


@pytest.fixture
def corrupted_policy_file():
    """Create a corrupted (invalid YAML) policy file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("invalid: yaml: content: [[[")
        f.flush()
        yield f.name

    os.unlink(f.name)


@pytest.fixture
def empty_policy_file():
    """Create an empty policy file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("")
        f.flush()
        yield f.name

    os.unlink(f.name)


@pytest.fixture
def enforcer(valid_policy_file):
    """Create an enforcer with valid policy."""
    return Enforcer(policy_path=valid_policy_file)


@pytest.fixture
def developer_agent():
    """Create a developer agent context with default budget."""
    return AgentContext(
        agent_id="dev_001",
        role="developer_agent",
        reputation=50,
        budget_remaining=100.0,
    )


@pytest.fixture
def developer_agent_no_budget():
    """Create a developer agent with zero budget."""
    return AgentContext(
        agent_id="dev_002",
        role="developer_agent",
        reputation=50,
        budget_remaining=0.0,
    )


@pytest.fixture
def architect_agent():
    """Create an architect agent context."""
    return AgentContext(
        agent_id="arch_001",
        role="architect_agent",
        reputation=100,
        budget_remaining=500.0,
    )


# ============================================================================
# AC-1: Immutable Protection Tests
# ============================================================================

class TestAC1ImmutableProtection:
    """
    AC-1: Attempting to edit .env returns PermissionError.

    The Enforcer must block all attempts to modify immutable files
    regardless of agent role or reputation.
    """

    def test_block_env_file_edit(self, enforcer, developer_agent):
        """Attempting to edit .env should be blocked."""
        result = enforcer.check(
            agent=developer_agent,
            tool_name="edit_file",
            target_path="/project/.env",
            action="write",
        )

        assert result.allowed is False
        assert result.violation_type == ViolationType.IMMUTABLE_PATH
        assert ".env" in result.message

    def test_block_env_file_delete(self, enforcer, developer_agent):
        """Attempting to delete .env should be blocked."""
        result = enforcer.check(
            agent=developer_agent,
            tool_name="delete_file",
            target_path=".env",
            action="delete",
        )

        assert result.allowed is False
        # Blocked either by IMMUTABLE_PATH or INSUFFICIENT_ROLE (delete_file not allowed)
        assert result.violation_type in (
            ViolationType.IMMUTABLE_PATH,
            ViolationType.INSUFFICIENT_ROLE,
        )

    def test_block_env_production_file(self, enforcer, developer_agent):
        """Attempting to edit .env.production should be blocked."""
        result = enforcer.check(
            agent=developer_agent,
            tool_name="edit_file",
            target_path="config/.env.production",
            action="write",
        )

        assert result.allowed is False
        assert result.violation_type == ViolationType.IMMUTABLE_PATH

    def test_block_pem_key_files(self, enforcer, developer_agent):
        """Attempting to edit .pem files should be blocked."""
        result = enforcer.check(
            agent=developer_agent,
            tool_name="edit_file",
            target_path="certs/server.pem",
            action="write",
        )

        assert result.allowed is False
        assert result.violation_type == ViolationType.IMMUTABLE_PATH

    def test_architect_cannot_edit_env(self, enforcer, architect_agent):
        """Even architects cannot edit immutable files."""
        result = enforcer.check(
            agent=architect_agent,
            tool_name="edit_file",
            target_path=".env",
            action="write",
        )

        assert result.allowed is False
        assert result.violation_type == ViolationType.IMMUTABLE_PATH

    def test_read_env_file_blocked_by_immutable(self, enforcer, developer_agent):
        """Reading .env is also blocked as it matches immutable pattern."""
        result = enforcer.check(
            agent=developer_agent,
            tool_name="read_file",
            target_path=".env",
            action="read",
        )

        # Current implementation blocks immutable paths for all actions
        # This is more secure - prevents even reading secrets
        assert result.allowed is False
        assert result.violation_type == ViolationType.IMMUTABLE_PATH

    def test_block_env_deletion_convenience_method(self, enforcer, developer_agent):
        """Test the block_env_deletion convenience method."""
        result = enforcer.block_env_deletion(developer_agent, "/config/.env")

        assert result.allowed is False
        assert "403 Forbidden" in result.message


# ============================================================================
# AC-2: Role Restriction Tests
# ============================================================================

class TestAC2RoleRestriction:
    """
    AC-2: A developer_agent attempting deploy_prod is blocked.

    Agents must only be able to use tools allowed for their role.
    """

    def test_developer_blocked_from_deploy_prod(self, enforcer, developer_agent):
        """Developer agent attempting deploy_prod should be blocked."""
        result = enforcer.check(
            agent=developer_agent,
            tool_name="deploy_prod",
            action="execute",
        )

        assert result.allowed is False
        # Could be FORBIDDEN_TOOL or HUMAN_APPROVAL_REQUIRED
        assert result.violation_type in (
            ViolationType.FORBIDDEN_TOOL,
            ViolationType.HUMAN_APPROVAL_REQUIRED,
        )

    def test_developer_blocked_from_delete_database(self, enforcer, developer_agent):
        """Developer agent attempting delete_database should be blocked."""
        result = enforcer.check(
            agent=developer_agent,
            tool_name="delete_database",
            action="execute",
        )

        assert result.allowed is False

    def test_developer_allowed_to_edit_file(self, enforcer, developer_agent):
        """Developer should be allowed to edit regular files."""
        result = enforcer.check(
            agent=developer_agent,
            tool_name="edit_file",
            target_path="src/module.py",
            action="write",
        )

        assert result.allowed is True

    def test_developer_allowed_to_run_tests(self, enforcer, developer_agent):
        """Developer should be allowed to run tests."""
        result = enforcer.check(
            agent=developer_agent,
            tool_name="run_test",
            action="execute",
        )

        assert result.allowed is True

    def test_architect_allowed_more_tools(self, enforcer, architect_agent):
        """Architect should have broader permissions."""
        # Test a tool that developer can't use but architect can
        result = enforcer.check(
            agent=architect_agent,
            tool_name="merge_pr",
            action="execute",
        )

        # Architect has wildcard access
        assert result.allowed is True

    def test_architect_still_blocked_from_modify_policy(self, enforcer, architect_agent):
        """Even architect cannot modify policy."""
        result = enforcer.check(
            agent=architect_agent,
            tool_name="modify_policy",
            action="execute",
        )

        assert result.allowed is False


# ============================================================================
# AC-3: Budget Check Tests
# ============================================================================

class TestAC3BudgetCheck:
    """
    AC-3: An agent with $0.00 remaining budget is blocked.

    Budget enforcement must prevent agents with no budget from executing actions.
    """

    def test_zero_budget_blocked(self, enforcer, developer_agent_no_budget):
        """Agent with $0.00 budget should be blocked from all actions."""
        result = enforcer.check(
            agent=developer_agent_no_budget,
            tool_name="read_file",
            target_path="src/module.py",
            action="read",
        )

        assert result.allowed is False
        assert result.violation_type == ViolationType.BUDGET_EXCEEDED
        assert "$0.00" in result.message

    def test_negative_budget_blocked(self, enforcer):
        """Agent with negative budget should be blocked."""
        agent = AgentContext(
            agent_id="dev_003",
            role="developer_agent",
            budget_remaining=-5.0,
        )

        result = enforcer.check(
            agent=agent,
            tool_name="read_file",
            action="read",
        )

        assert result.allowed is False
        assert result.violation_type == ViolationType.BUDGET_EXCEEDED

    def test_positive_budget_allowed(self, enforcer, developer_agent):
        """Agent with positive budget should be allowed."""
        result = enforcer.check(
            agent=developer_agent,
            tool_name="read_file",
            target_path="src/module.py",
            action="read",
        )

        assert result.allowed is True

    def test_minimal_budget_allowed(self, enforcer):
        """Agent with minimal budget ($0.01) should be allowed."""
        agent = AgentContext(
            agent_id="dev_004",
            role="developer_agent",
            budget_remaining=0.01,
        )

        result = enforcer.check(
            agent=agent,
            tool_name="read_file",
            action="read",
        )

        assert result.allowed is True


# ============================================================================
# AC-4: Performance Tests
# ============================================================================

class TestAC4Performance:
    """
    AC-4: Overhead per call is < 10ms.

    The enforcer must be fast enough to not impact agent performance.
    """

    def test_single_check_under_10ms(self, enforcer, developer_agent):
        """A single enforcement check should complete in < 10ms."""
        start = time.perf_counter()
        result = enforcer.check(
            agent=developer_agent,
            tool_name="read_file",
            target_path="src/module.py",
            action="read",
        )
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 10, f"Check took {elapsed_ms:.2f}ms, expected < 10ms"
        assert result.latency_ms < 10

    def test_denied_check_under_10ms(self, enforcer, developer_agent):
        """Even denied checks should complete in < 10ms."""
        start = time.perf_counter()
        result = enforcer.check(
            agent=developer_agent,
            tool_name="deploy_prod",
            action="execute",
        )
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 10, f"Check took {elapsed_ms:.2f}ms, expected < 10ms"
        assert result.latency_ms < 10

    def test_immutable_check_under_10ms(self, enforcer, developer_agent):
        """Immutable path checks should complete in < 10ms."""
        start = time.perf_counter()
        result = enforcer.check(
            agent=developer_agent,
            tool_name="edit_file",
            target_path=".env",
            action="write",
        )
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 10, f"Check took {elapsed_ms:.2f}ms, expected < 10ms"

    def test_100_checks_average_under_10ms(self, enforcer, developer_agent):
        """Average of 100 checks should be < 10ms."""
        total_time = 0
        for _ in range(100):
            start = time.perf_counter()
            enforcer.check(
                agent=developer_agent,
                tool_name="read_file",
                target_path="src/module.py",
                action="read",
            )
            total_time += time.perf_counter() - start

        avg_ms = (total_time / 100) * 1000
        assert avg_ms < 10, f"Average check took {avg_ms:.2f}ms, expected < 10ms"

    def test_latency_recorded_in_result(self, enforcer, developer_agent):
        """Result should include latency measurement."""
        result = enforcer.check(
            agent=developer_agent,
            tool_name="read_file",
            action="read",
        )

        assert hasattr(result, "latency_ms")
        assert result.latency_ms >= 0
        assert result.latency_ms < 10


# ============================================================================
# AC-5: Fail-Safe Tests
# ============================================================================

class TestAC5FailSafe:
    """
    AC-5: If the policy file is corrupted, ALL actions are blocked.

    The system must fail closed to prevent security bypasses.
    """

    def test_corrupted_policy_enters_fail_safe(self, corrupted_policy_file, developer_agent):
        """Corrupted policy file should put enforcer in fail-safe mode."""
        # Create enforcer with corrupted policy - enters fail-safe mode
        enforcer = Enforcer(policy_path=corrupted_policy_file)

        # Enforcer should be in fail-safe mode
        assert enforcer.is_fail_safe is True

        # All actions should be blocked
        result = enforcer.check(developer_agent, "read_file", "public.txt", "read")
        assert result.allowed is False
        assert "FAIL-SAFE" in result.message

    def test_empty_policy_enters_fail_safe(self, empty_policy_file, developer_agent):
        """Empty policy file should put enforcer in fail-safe mode."""
        enforcer = Enforcer(policy_path=empty_policy_file)
        assert enforcer.is_fail_safe is True

        result = enforcer.check(developer_agent, "read_file", "public.txt", "read")
        assert result.allowed is False

    def test_missing_policy_enters_fail_safe(self, developer_agent):
        """Missing policy file should put enforcer in fail-safe mode."""
        enforcer = Enforcer(policy_path="/nonexistent/policy.yaml")
        assert enforcer.is_fail_safe is True

        result = enforcer.check(developer_agent, "read_file", "public.txt", "read")
        assert result.allowed is False

    def test_fail_safe_flag_set_on_corruption(self, corrupted_policy_file):
        """Fail-safe flag should be set when policy is corrupted."""
        enforcer = Enforcer.__new__(Enforcer)
        enforcer._policy = {}
        enforcer._policy_version = "2.0.0"
        enforcer._policy_corrupted = False
        enforcer._file_locker = None
        enforcer._audit_logger = None
        enforcer._on_violation = []
        enforcer._budget_tracker = {}
        enforcer._lock = None

        try:
            enforcer.load_policy(corrupted_policy_file)
        except PolicyLoadError:
            pass

        # After failed load, policy_corrupted should be True
        assert enforcer._policy_corrupted is True

    def test_fail_safe_blocks_everything(self, valid_policy_file, developer_agent):
        """When in fail-safe mode, all actions are blocked."""
        enforcer = Enforcer(policy_path=valid_policy_file)

        # Manually set fail-safe mode
        enforcer._policy_corrupted = True

        result = enforcer.check(
            agent=developer_agent,
            tool_name="read_file",
            target_path="public.txt",
            action="read",
        )

        assert result.allowed is False
        assert "FAIL-SAFE" in result.message

    def test_is_fail_safe_property(self, valid_policy_file):
        """Test is_fail_safe property."""
        enforcer = Enforcer(policy_path=valid_policy_file)
        assert enforcer.is_fail_safe is False

        enforcer._policy_corrupted = True
        assert enforcer.is_fail_safe is True


# ============================================================================
# EnforcerMiddleware Alias Tests
# ============================================================================

class TestEnforcerMiddlewareAlias:
    """Test that EnforcerMiddleware is an alias for Enforcer."""

    def test_alias_is_enforcer(self):
        """EnforcerMiddleware should be the same as Enforcer."""
        assert EnforcerMiddleware is Enforcer

    def test_can_instantiate_via_alias(self, valid_policy_file):
        """Should be able to create instance via alias."""
        middleware = EnforcerMiddleware(policy_path=valid_policy_file)
        assert isinstance(middleware, Enforcer)


# ============================================================================
# AgentAction Tests
# ============================================================================

class TestAgentAction:
    """Test AgentAction dataclass."""

    def test_create_agent_action(self):
        """Create an AgentAction with all fields."""
        action = AgentAction(
            tool_name="write_file",
            args={"path": "/tmp/output.txt", "content": "Hello"},
            agent_id="dev_001",
        )

        assert action.tool_name == "write_file"
        assert action.args == {"path": "/tmp/output.txt", "content": "Hello"}
        assert action.agent_id == "dev_001"
        assert action.timestamp is not None

    def test_default_agent_id(self):
        """Default agent_id should be 'anonymous'."""
        action = AgentAction(tool_name="read_file")
        assert action.agent_id == "anonymous"


# ============================================================================
# Integration Tests
# ============================================================================

class TestEnforcerIntegration:
    """Integration tests combining multiple ACs."""

    def test_multi_check_scenario(self, enforcer, developer_agent):
        """Test a realistic scenario with multiple checks."""
        # Step 1: Read a config file (allowed)
        r1 = enforcer.check(developer_agent, "read_file", "config/settings.json", "read")
        assert r1.allowed is True

        # Step 2: Try to edit .env (blocked - AC-1)
        r2 = enforcer.check(developer_agent, "edit_file", ".env", "write")
        assert r2.allowed is False

        # Step 3: Edit a regular file (allowed)
        r3 = enforcer.check(developer_agent, "edit_file", "src/app.py", "write")
        assert r3.allowed is True

        # Step 4: Try to deploy (blocked - AC-2)
        r4 = enforcer.check(developer_agent, "deploy_prod", action="execute")
        assert r4.allowed is False

    def test_budget_takes_priority(self, enforcer):
        """Budget check should happen before other checks."""
        agent = AgentContext(
            agent_id="dev_broke",
            role="architect_agent",  # High privilege role
            budget_remaining=0.0,
        )

        # Even as architect with allowed tool, budget blocks first
        result = enforcer.check(agent, "read_file", "public.txt", "read")

        assert result.allowed is False
        assert result.violation_type == ViolationType.BUDGET_EXCEEDED

    def test_all_checks_under_latency_budget(self, enforcer, developer_agent):
        """All check types should complete under 10ms."""
        checks = [
            ("read_file", "src/module.py", "read"),
            ("edit_file", ".env", "write"),
            ("deploy_prod", None, "execute"),
            ("run_test", None, "execute"),
        ]

        for tool, path, action in checks:
            result = enforcer.check(developer_agent, tool, path, action)
            assert result.latency_ms < 10, f"{tool} took {result.latency_ms:.2f}ms"
