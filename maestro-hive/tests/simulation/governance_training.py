"""
Governance Validation & Training Simulation (MD-3124)

Runs 4 simulation scenarios to validate the governance layer:
1. Rogue Agent - Attempts malicious actions -> BLOCKED
2. Good Citizen - Normal operations -> ALLOWED
3. Greedy Agent - Resource exhaustion -> THROTTLED
4. Clumsy Agent - Concurrent editing -> ERROR

EPIC: MD-3124 - Run Governance Validation & Training Simulation
"""

import json
import os
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest
import yaml

from maestro_hive.governance.enforcer import (
    AgentContext,
    Enforcer,
    EnforcerResult,
    ViolationType,
)
from maestro_hive.governance.reputation import (
    ReputationEngine,
    ReputationEvent,
    ReputationScore,
)


# ============================================================================
# Audit Log for Training
# ============================================================================

@dataclass
class AuditEntry:
    """Single entry in the audit log."""
    timestamp: str
    agent_id: str
    action: str
    target: str
    result: str  # ALLOWED or DENIED
    violation_type: Optional[str] = None
    reputation_delta: int = 0
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "agent_id": self.agent_id,
            "action": self.action,
            "target": self.target,
            "result": self.result,
            "violation_type": self.violation_type,
            "reputation_delta": self.reputation_delta,
            "message": self.message,
        }


class AuditLogger:
    """Simple audit logger for training simulation."""

    def __init__(self, log_path: Optional[str] = None):
        self.entries: List[AuditEntry] = []
        self.log_path = log_path

    def log(
        self,
        agent_id: str,
        action: str,
        target: str,
        result: EnforcerResult,
    ) -> None:
        """Log an enforcement result."""
        entry = AuditEntry(
            timestamp=datetime.utcnow().isoformat(),
            agent_id=agent_id,
            action=action,
            target=target,
            result="ALLOWED" if result.allowed else "DENIED",
            violation_type=result.violation_type.value if result.violation_type else None,
            message=result.message,
        )
        self.entries.append(entry)

        # Write to file if path specified
        if self.log_path:
            with open(self.log_path, "a") as f:
                f.write(json.dumps(entry.to_dict()) + "\n")

    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics."""
        allowed = sum(1 for e in self.entries if e.result == "ALLOWED")
        denied = sum(1 for e in self.entries if e.result == "DENIED")
        return {
            "total_entries": len(self.entries),
            "allowed": allowed,
            "denied": denied,
            "denial_rate": denied / max(len(self.entries), 1),
        }


# ============================================================================
# File Locker for Concurrency Testing
# ============================================================================

class SimpleFileLocker:
    """Simple file locker for testing concurrency control."""

    def __init__(self):
        self._locks: Dict[str, str] = {}  # path -> agent_id

    def acquire_lock(self, path: str, agent_id: str) -> bool:
        """Try to acquire a lock."""
        if path in self._locks and self._locks[path] != agent_id:
            return False
        self._locks[path] = agent_id
        return True

    def release_lock(self, path: str, agent_id: str) -> bool:
        """Release a lock."""
        if path in self._locks and self._locks[path] == agent_id:
            del self._locks[path]
            return True
        return False

    def get_lock_holder(self, path: str) -> Optional[str]:
        """Get current lock holder."""
        return self._locks.get(path)


# ============================================================================
# Training Report Generator
# ============================================================================

@dataclass
class TrainingReport:
    """Training simulation report."""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    scenarios_run: int = 0
    scenarios_passed: int = 0
    scenarios_failed: int = 0
    audit_summary: Dict[str, Any] = field(default_factory=dict)
    reputation_changes: List[Dict[str, Any]] = field(default_factory=list)
    lessons_learned: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "scenarios_run": self.scenarios_run,
            "scenarios_passed": self.scenarios_passed,
            "scenarios_failed": self.scenarios_failed,
            "pass_rate": self.scenarios_passed / max(self.scenarios_run, 1),
            "audit_summary": self.audit_summary,
            "reputation_changes": self.reputation_changes,
            "lessons_learned": self.lessons_learned,
        }

    def add_lesson(self, lesson: str) -> None:
        self.lessons_learned.append(lesson)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def valid_policy_file():
    """Create a valid policy file for training simulation."""
    policy_content = {
        "global_constraints": {
            "max_daily_budget_usd": 50.0,
            "max_concurrent_agents": 10,
            "max_recursion_depth": 5,
            "require_human_approval_for": ["deploy_prod", "delete_database"],
        },
        "file_protection": {
            "immutable_paths": [".env", ".env.*", "*.pem", "*.key", "**/secrets/**"],
            "protected_paths": ["src/core/*", "pyproject.toml", "docker-compose*.yml"],
        },
        "roles": {
            "developer_agent": {
                "max_tokens_per_run": 20000,
                "allowed_tools": ["read_file", "create_file", "edit_file", "run_test"],
                "forbidden_tools": ["deploy_prod", "delete_database", "modify_policy", "drop_table"],
            },
            "senior_developer_agent": {
                "max_tokens_per_run": 50000,
                "allowed_tools": ["read_file", "create_file", "edit_file", "run_test", "merge_pr"],
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
def audit_log_path():
    """Create temporary audit log file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
        yield f.name
    if os.path.exists(f.name):
        os.unlink(f.name)


@pytest.fixture
def enforcer(valid_policy_file):
    """Create enforcer with valid policy."""
    return Enforcer(policy_path=valid_policy_file)


@pytest.fixture
def reputation_engine():
    """Create reputation engine for training."""
    return ReputationEngine(
        initial_score=50,
        min_score=10,
        max_daily_gain=100,
        max_daily_loss=-50,
    )


@pytest.fixture
def audit_logger(audit_log_path):
    """Create audit logger."""
    return AuditLogger(log_path=audit_log_path)


@pytest.fixture
def file_locker():
    """Create file locker for concurrency testing."""
    return SimpleFileLocker()


@pytest.fixture
def training_report():
    """Create training report."""
    return TrainingReport()


# ============================================================================
# Scenario 1: The "Rogue" Agent
# ============================================================================

class TestScenario1RogueAgent:
    """
    Scenario 1: The "Rogue" Agent

    Intent: "Delete the entire database."
    Expected Result: BLOCKED by Enforcer. Reputation DECREASED.
    """

    def test_rogue_agent_delete_database_blocked(
        self,
        enforcer,
        reputation_engine,
        audit_logger,
        training_report,
    ):
        """Rogue agent attempting to delete database should be blocked."""
        # Create rogue agent
        rogue = AgentContext(
            agent_id="rogue_001",
            role="developer_agent",
            reputation=50,
            budget_remaining=100.0,
        )

        # Attempt 1: Delete database
        result = enforcer.check(
            agent=rogue,
            tool_name="delete_database",
            target_path="prod_database",
            action="execute",
        )

        # Log the action
        audit_logger.log(rogue.agent_id, "delete_database", "prod_database", result)

        # Verify blocked
        assert result.allowed is False
        assert result.violation_type in (
            ViolationType.FORBIDDEN_TOOL,
            ViolationType.HUMAN_APPROVAL_REQUIRED,
        )

        # Decrease reputation for attempted violation
        change = reputation_engine.record_event(
            rogue.agent_id,
            ReputationEvent.POLICY_VIOLATION,
            {"attempted_action": "delete_database"},
        )

        # Verify reputation decreased
        assert change.delta < 0
        score = reputation_engine.get_score(rogue.agent_id)
        assert score.score < 50  # Started at 50

        # Update training report
        training_report.scenarios_run += 1
        training_report.scenarios_passed += 1
        training_report.reputation_changes.append(change.to_dict())
        training_report.add_lesson(
            "Rogue agent 'delete_database' was blocked by Enforcer (FORBIDDEN_TOOL)"
        )

    def test_rogue_agent_drop_table_blocked(
        self,
        enforcer,
        reputation_engine,
        audit_logger,
    ):
        """Rogue agent attempting to drop table should be blocked."""
        rogue = AgentContext(
            agent_id="rogue_002",
            role="developer_agent",
            reputation=50,
            budget_remaining=100.0,
        )

        result = enforcer.check(
            agent=rogue,
            tool_name="drop_table",
            target_path="users_table",
            action="execute",
        )

        audit_logger.log(rogue.agent_id, "drop_table", "users_table", result)

        assert result.allowed is False

    def test_rogue_agent_modify_env_blocked(
        self,
        enforcer,
        reputation_engine,
        audit_logger,
    ):
        """Rogue agent attempting to modify .env should be blocked."""
        rogue = AgentContext(
            agent_id="rogue_003",
            role="developer_agent",
            reputation=50,
            budget_remaining=100.0,
        )

        result = enforcer.check(
            agent=rogue,
            tool_name="edit_file",
            target_path=".env",
            action="write",
        )

        audit_logger.log(rogue.agent_id, "edit_file", ".env", result)

        assert result.allowed is False
        assert result.violation_type == ViolationType.IMMUTABLE_PATH

    def test_rogue_agent_access_secrets_blocked(
        self,
        enforcer,
        audit_logger,
    ):
        """Rogue agent attempting to access secrets directory should be blocked."""
        rogue = AgentContext(
            agent_id="rogue_004",
            role="developer_agent",
            reputation=50,
            budget_remaining=100.0,
        )

        result = enforcer.check(
            agent=rogue,
            tool_name="read_file",
            target_path="/app/secrets/api_keys.json",
            action="read",
        )

        audit_logger.log(rogue.agent_id, "read_file", "/app/secrets/api_keys.json", result)

        assert result.allowed is False
        assert result.violation_type == ViolationType.IMMUTABLE_PATH


# ============================================================================
# Scenario 2: The "Good" Citizen
# ============================================================================

class TestScenario2GoodCitizen:
    """
    Scenario 2: The "Good" Citizen

    Intent: "Create a new feature file feature.py."
    Expected Result: ALLOWED. Reputation INCREASED.
    """

    def test_good_citizen_create_file_allowed(
        self,
        enforcer,
        reputation_engine,
        audit_logger,
        training_report,
    ):
        """Good citizen creating a new feature file should be allowed."""
        # Create good citizen agent
        citizen = AgentContext(
            agent_id="citizen_001",
            role="developer_agent",
            reputation=50,
            budget_remaining=100.0,
        )

        # Attempt: Create a new feature file
        result = enforcer.check(
            agent=citizen,
            tool_name="create_file",
            target_path="src/features/new_feature.py",
            action="write",
        )

        # Log the action
        audit_logger.log(citizen.agent_id, "create_file", "src/features/new_feature.py", result)

        # Verify allowed
        assert result.allowed is True

        # Increase reputation for good behavior (simulating PR merged)
        change = reputation_engine.record_event(
            citizen.agent_id,
            ReputationEvent.PR_MERGED,
            {"pr_id": "PR-123", "lines_changed": 100},
        )

        # Verify reputation increased
        assert change.delta > 0
        score = reputation_engine.get_score(citizen.agent_id)
        assert score.score > 50  # Started at 50

        # Update training report
        training_report.scenarios_run += 1
        training_report.scenarios_passed += 1
        training_report.reputation_changes.append(change.to_dict())
        training_report.add_lesson(
            "Good citizen 'create_file' was allowed. Reputation increased on PR merge."
        )

    def test_good_citizen_run_tests_allowed(
        self,
        enforcer,
        reputation_engine,
        audit_logger,
    ):
        """Good citizen running tests should be allowed."""
        citizen = AgentContext(
            agent_id="citizen_002",
            role="developer_agent",
            reputation=50,
            budget_remaining=100.0,
        )

        result = enforcer.check(
            agent=citizen,
            tool_name="run_test",
            target_path="tests/",
            action="execute",
        )

        audit_logger.log(citizen.agent_id, "run_test", "tests/", result)

        assert result.allowed is True

        # Record test passed
        change = reputation_engine.record_event(
            citizen.agent_id,
            ReputationEvent.TEST_PASSED,
        )
        assert change.delta >= 0

    def test_good_citizen_edit_code_allowed(
        self,
        enforcer,
        audit_logger,
    ):
        """Good citizen editing code should be allowed."""
        citizen = AgentContext(
            agent_id="citizen_003",
            role="developer_agent",
            reputation=60,
            budget_remaining=100.0,
        )

        result = enforcer.check(
            agent=citizen,
            tool_name="edit_file",
            target_path="src/utils/helpers.py",
            action="write",
        )

        audit_logger.log(citizen.agent_id, "edit_file", "src/utils/helpers.py", result)

        assert result.allowed is True

    def test_good_citizen_read_file_allowed(
        self,
        enforcer,
        audit_logger,
    ):
        """Good citizen reading code files should be allowed."""
        citizen = AgentContext(
            agent_id="citizen_004",
            role="developer_agent",
            reputation=50,
            budget_remaining=100.0,
        )

        result = enforcer.check(
            agent=citizen,
            tool_name="read_file",
            target_path="src/app.py",
            action="read",
        )

        audit_logger.log(citizen.agent_id, "read_file", "src/app.py", result)

        # read_file is an allowed tool for developers
        assert result.allowed is True


# ============================================================================
# Scenario 3: The "Greedy" Agent
# ============================================================================

class TestScenario3GreedyAgent:
    """
    Scenario 3: The "Greedy" Agent

    Intent: "Run a loop that consumes 100% CPU/Budget."
    Expected Result: THROTTLED or KILLED by Resource Monitor.
    """

    def test_greedy_agent_zero_budget_blocked(
        self,
        enforcer,
        reputation_engine,
        audit_logger,
        training_report,
    ):
        """Greedy agent with zero budget should be blocked."""
        # Create greedy agent with depleted budget
        greedy = AgentContext(
            agent_id="greedy_001",
            role="developer_agent",
            reputation=50,
            budget_remaining=0.0,  # No budget left
        )

        # Attempt any action
        result = enforcer.check(
            agent=greedy,
            tool_name="run_test",
            target_path="tests/",
            action="execute",
        )

        # Log the action
        audit_logger.log(greedy.agent_id, "run_test", "tests/", result)

        # Verify blocked due to budget
        assert result.allowed is False
        assert result.violation_type == ViolationType.BUDGET_EXCEEDED

        # Update training report
        training_report.scenarios_run += 1
        training_report.scenarios_passed += 1
        training_report.add_lesson(
            "Greedy agent with $0.00 budget was blocked (BUDGET_EXCEEDED)"
        )

    def test_greedy_agent_negative_budget_blocked(
        self,
        enforcer,
        audit_logger,
    ):
        """Greedy agent with negative budget should be blocked."""
        greedy = AgentContext(
            agent_id="greedy_002",
            role="developer_agent",
            reputation=50,
            budget_remaining=-10.0,  # Somehow negative
        )

        result = enforcer.check(
            agent=greedy,
            tool_name="read_file",
            target_path="src/app.py",
            action="read",
        )

        audit_logger.log(greedy.agent_id, "read_file", "src/app.py", result)

        assert result.allowed is False
        assert result.violation_type == ViolationType.BUDGET_EXCEEDED

    def test_greedy_agent_hits_daily_gain_limit(
        self,
        reputation_engine,
    ):
        """Greedy agent hitting daily gain limit should be rate limited."""
        greedy_id = "greedy_003"

        # Set high daily gain to force limit
        engine = reputation_engine
        engine._max_daily_gain = 50  # Low limit for testing

        # Record many events to hit limit
        total_gain = 0
        for i in range(20):
            # Use different event types to avoid cooldown
            change = engine.record_event(
                greedy_id,
                ReputationEvent.PR_MERGED,
                {"pr_id": f"PR-{i}", "lines_changed": 100},
            )
            total_gain += change.delta
            time.sleep(0.01)  # Small delay

        # Should have been rate limited
        score = engine.get_score(greedy_id)
        # Total gain should be capped by daily limit
        assert score.daily_gain <= engine._max_daily_gain

    def test_greedy_agent_recursion_limit(
        self,
        enforcer,
        audit_logger,
    ):
        """Greedy agent exceeding recursion depth should be blocked."""
        greedy = AgentContext(
            agent_id="greedy_004",
            role="developer_agent",
            reputation=50,
            budget_remaining=100.0,
            recursion_depth=10,  # Exceeds max of 5
        )

        result = enforcer.check(
            agent=greedy,
            tool_name="read_file",
            target_path="src/app.py",
            action="read",
        )

        audit_logger.log(greedy.agent_id, "read_file", "src/app.py", result)

        assert result.allowed is False
        assert result.violation_type == ViolationType.RECURSION_LIMIT


# ============================================================================
# Scenario 4: The "Clumsy" Agent
# ============================================================================

class TestScenario4ClumsyAgent:
    """
    Scenario 4: The "Clumsy" Agent

    Intent: "Edit a file locked by another agent."
    Expected Result: WAIT or ERROR (Concurrency Check).
    """

    def test_clumsy_agent_file_locked_error(
        self,
        enforcer,
        file_locker,
        audit_logger,
        training_report,
    ):
        """Clumsy agent editing locked file should get error."""
        # Inject file locker into enforcer
        enforcer.set_file_locker(file_locker)

        # First agent acquires lock
        senior = AgentContext(
            agent_id="senior_001",
            role="senior_developer_agent",
            reputation=100,
            budget_remaining=100.0,
        )
        file_locker.acquire_lock("src/shared_module.py", senior.agent_id)

        # Clumsy agent tries to edit same file
        clumsy = AgentContext(
            agent_id="clumsy_001",
            role="developer_agent",
            reputation=50,
            budget_remaining=100.0,
        )

        result = enforcer.check(
            agent=clumsy,
            tool_name="edit_file",
            target_path="src/shared_module.py",
            action="write",
        )

        # Log the action
        audit_logger.log(clumsy.agent_id, "edit_file", "src/shared_module.py", result)

        # Verify blocked due to file lock
        assert result.allowed is False
        assert result.violation_type == ViolationType.FILE_LOCKED
        assert "senior_001" in result.message

        # Update training report
        training_report.scenarios_run += 1
        training_report.scenarios_passed += 1
        training_report.add_lesson(
            "Clumsy agent blocked from editing locked file (FILE_LOCKED by senior_001)"
        )

    def test_clumsy_agent_can_read_locked_file(
        self,
        enforcer,
        file_locker,
        audit_logger,
    ):
        """Clumsy agent should be able to read a locked file (read is allowed)."""
        enforcer.set_file_locker(file_locker)

        # First agent acquires lock
        file_locker.acquire_lock("src/shared_module.py", "senior_001")

        # Clumsy agent tries to read same file
        clumsy = AgentContext(
            agent_id="clumsy_002",
            role="developer_agent",
            reputation=50,
            budget_remaining=100.0,
        )

        result = enforcer.check(
            agent=clumsy,
            tool_name="read_file",
            target_path="src/shared_module.py",
            action="read",
        )

        audit_logger.log(clumsy.agent_id, "read_file", "src/shared_module.py", result)

        # Reading is allowed even when file is locked
        assert result.allowed is True

    def test_clumsy_agent_can_edit_after_unlock(
        self,
        enforcer,
        file_locker,
        audit_logger,
    ):
        """Clumsy agent should be able to edit after lock is released."""
        enforcer.set_file_locker(file_locker)

        # Acquire and release lock
        file_locker.acquire_lock("src/shared_module.py", "senior_001")
        file_locker.release_lock("src/shared_module.py", "senior_001")

        # Now clumsy agent can edit
        clumsy = AgentContext(
            agent_id="clumsy_003",
            role="developer_agent",
            reputation=50,
            budget_remaining=100.0,
        )

        result = enforcer.check(
            agent=clumsy,
            tool_name="edit_file",
            target_path="src/shared_module.py",
            action="write",
        )

        audit_logger.log(clumsy.agent_id, "edit_file", "src/shared_module.py", result)

        assert result.allowed is True

    def test_clumsy_agent_can_edit_own_locked_file(
        self,
        enforcer,
        file_locker,
        audit_logger,
    ):
        """Agent should be able to edit a file they locked."""
        enforcer.set_file_locker(file_locker)

        # Clumsy agent acquires lock
        clumsy = AgentContext(
            agent_id="clumsy_004",
            role="developer_agent",
            reputation=50,
            budget_remaining=100.0,
        )
        file_locker.acquire_lock("src/my_module.py", clumsy.agent_id)

        result = enforcer.check(
            agent=clumsy,
            tool_name="edit_file",
            target_path="src/my_module.py",
            action="write",
        )

        audit_logger.log(clumsy.agent_id, "edit_file", "src/my_module.py", result)

        # Should be allowed since they hold the lock
        assert result.allowed is True


# ============================================================================
# Training Report Generation
# ============================================================================

class TestTrainingReportGeneration:
    """Test training report generation after all scenarios."""

    def test_generate_full_training_report(
        self,
        enforcer,
        reputation_engine,
        audit_logger,
        file_locker,
    ):
        """Run all scenarios and generate comprehensive training report."""
        enforcer.set_file_locker(file_locker)
        report = TrainingReport()

        # --- Scenario 1: Rogue Agent ---
        rogue = AgentContext(
            agent_id="rogue_training",
            role="developer_agent",
            reputation=50,
            budget_remaining=100.0,
        )
        result = enforcer.check(rogue, "delete_database", "prod_db", "execute")
        audit_logger.log(rogue.agent_id, "delete_database", "prod_db", result)

        if not result.allowed:
            change = reputation_engine.record_event(
                rogue.agent_id, ReputationEvent.POLICY_VIOLATION
            )
            report.reputation_changes.append(change.to_dict())
            report.scenarios_passed += 1
        report.scenarios_run += 1

        # --- Scenario 2: Good Citizen ---
        citizen = AgentContext(
            agent_id="citizen_training",
            role="developer_agent",
            reputation=50,
            budget_remaining=100.0,
        )
        result = enforcer.check(citizen, "create_file", "src/feature.py", "write")
        audit_logger.log(citizen.agent_id, "create_file", "src/feature.py", result)

        if result.allowed:
            change = reputation_engine.record_event(
                citizen.agent_id,
                ReputationEvent.PR_MERGED,
                {"lines_changed": 100},
            )
            report.reputation_changes.append(change.to_dict())
            report.scenarios_passed += 1
        report.scenarios_run += 1

        # --- Scenario 3: Greedy Agent ---
        greedy = AgentContext(
            agent_id="greedy_training",
            role="developer_agent",
            reputation=50,
            budget_remaining=0.0,
        )
        result = enforcer.check(greedy, "run_test", "tests/", "execute")
        audit_logger.log(greedy.agent_id, "run_test", "tests/", result)

        if not result.allowed and result.violation_type == ViolationType.BUDGET_EXCEEDED:
            report.scenarios_passed += 1
        report.scenarios_run += 1

        # --- Scenario 4: Clumsy Agent ---
        file_locker.acquire_lock("src/shared.py", "other_agent")
        clumsy = AgentContext(
            agent_id="clumsy_training",
            role="developer_agent",
            reputation=50,
            budget_remaining=100.0,
        )
        result = enforcer.check(clumsy, "edit_file", "src/shared.py", "write")
        audit_logger.log(clumsy.agent_id, "edit_file", "src/shared.py", result)

        if not result.allowed and result.violation_type == ViolationType.FILE_LOCKED:
            report.scenarios_passed += 1
        report.scenarios_run += 1

        # --- Generate Report ---
        report.audit_summary = audit_logger.get_summary()
        report.add_lesson("Enforcer correctly blocks forbidden tools (delete_database)")
        report.add_lesson("Good citizens are allowed to create files and earn reputation")
        report.add_lesson("Budget enforcement prevents resource exhaustion")
        report.add_lesson("File locking prevents concurrent edit conflicts")

        # Verify all scenarios passed
        assert report.scenarios_run == 4
        assert report.scenarios_passed == 4
        assert report.audit_summary["total_entries"] == 4
        assert len(report.lessons_learned) == 4

        # Print report for verification
        report_dict = report.to_dict()
        print("\n" + "=" * 60)
        print("TRAINING REPORT")
        print("=" * 60)
        print(json.dumps(report_dict, indent=2))


# ============================================================================
# Audit Log Verification
# ============================================================================

class TestAuditLogVerification:
    """Verify audit.log shows clear ALLOWED and DENIED entries."""

    def test_audit_log_contains_allowed_entries(
        self,
        enforcer,
        audit_logger,
    ):
        """Audit log should contain ALLOWED entries for valid actions."""
        agent = AgentContext(
            agent_id="audit_test_001",
            role="developer_agent",
            reputation=50,
            budget_remaining=100.0,
        )

        result = enforcer.check(agent, "read_file", "src/app.py", "read")
        audit_logger.log(agent.agent_id, "read_file", "src/app.py", result)

        # Verify log entry
        assert len(audit_logger.entries) == 1
        entry = audit_logger.entries[0]
        assert entry.result == "ALLOWED"
        assert entry.agent_id == "audit_test_001"
        assert entry.action == "read_file"

    def test_audit_log_contains_denied_entries(
        self,
        enforcer,
        audit_logger,
    ):
        """Audit log should contain DENIED entries for blocked actions."""
        agent = AgentContext(
            agent_id="audit_test_002",
            role="developer_agent",
            reputation=50,
            budget_remaining=100.0,
        )

        result = enforcer.check(agent, "deploy_prod", None, "execute")
        audit_logger.log(agent.agent_id, "deploy_prod", "", result)

        # Verify log entry
        assert len(audit_logger.entries) == 1
        entry = audit_logger.entries[0]
        assert entry.result == "DENIED"
        assert entry.violation_type is not None

    def test_audit_log_file_written(
        self,
        enforcer,
        audit_log_path,
    ):
        """Audit log should be written to file."""
        logger = AuditLogger(log_path=audit_log_path)

        agent = AgentContext(
            agent_id="audit_test_003",
            role="developer_agent",
            reputation=50,
            budget_remaining=100.0,
        )

        result = enforcer.check(agent, "edit_file", "src/module.py", "write")
        logger.log(agent.agent_id, "edit_file", "src/module.py", result)

        # Verify file contains entry
        with open(audit_log_path, "r") as f:
            content = f.read()
            assert "audit_test_003" in content
            assert "ALLOWED" in content


# ============================================================================
# Reputation Database Verification
# ============================================================================

class TestReputationDatabaseVerification:
    """Verify reputation.db shows updated scores after the run."""

    def test_reputation_updated_after_violation(
        self,
        reputation_engine,
    ):
        """Reputation should decrease after policy violation."""
        agent_id = "rep_test_001"

        # Get initial score
        initial = reputation_engine.get_score(agent_id)
        initial_score = initial.score

        # Record violation
        reputation_engine.record_event(agent_id, ReputationEvent.POLICY_VIOLATION)

        # Verify score decreased
        updated = reputation_engine.get_score(agent_id)
        assert updated.score < initial_score
        assert updated.total_events == 1

    def test_reputation_updated_after_success(
        self,
        reputation_engine,
    ):
        """Reputation should increase after successful actions."""
        agent_id = "rep_test_002"

        initial = reputation_engine.get_score(agent_id)
        initial_score = initial.score

        # Record success
        reputation_engine.record_event(
            agent_id,
            ReputationEvent.PR_MERGED,
            {"lines_changed": 100},
        )

        updated = reputation_engine.get_score(agent_id)
        assert updated.score > initial_score

    def test_reputation_history_tracked(
        self,
        reputation_engine,
    ):
        """Reputation history should track all changes."""
        agent_id = "rep_test_003"

        # Multiple events
        reputation_engine.record_event(agent_id, ReputationEvent.TEST_PASSED)
        reputation_engine.record_event(agent_id, ReputationEvent.BUG_FIXED)
        reputation_engine.record_event(agent_id, ReputationEvent.BUILD_BROKEN)

        history = reputation_engine.get_history(agent_id=agent_id)
        assert len(history) >= 3
