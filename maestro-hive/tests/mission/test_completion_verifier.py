"""Tests for CompletionVerifier."""

import pytest
from datetime import datetime
from unittest.mock import Mock

from maestro_hive.mission.completion_verifier import (
    CompletionVerifier,
    VerificationResult,
    VerificationRule,
    VerificationStatus,
)


class TestVerificationStatus:
    """Tests for VerificationStatus enum."""

    def test_all_statuses_defined(self):
        """Test all expected statuses are defined."""
        statuses = [s.value for s in VerificationStatus]
        assert "pending" in statuses
        assert "passed" in statuses
        assert "failed" in statuses
        assert "skipped" in statuses
        assert "warning" in statuses


class TestVerificationRule:
    """Tests for VerificationRule dataclass."""

    def test_create_rule(self):
        """Test creating a verification rule."""
        rule = VerificationRule(
            name="test_rule",
            rule_type="schema",
            required=True
        )

        assert rule.name == "test_rule"
        assert rule.rule_type == "schema"
        assert rule.required is True
        assert rule.parameters == {}

    def test_create_rule_with_parameters(self):
        """Test creating a rule with parameters."""
        rule = VerificationRule(
            name="custom_rule",
            rule_type="custom",
            parameters={"threshold": 0.9}
        )

        assert rule.parameters["threshold"] == 0.9


class TestVerificationResult:
    """Tests for VerificationResult dataclass."""

    def test_create_result(self):
        """Test creating a verification result."""
        result = VerificationResult(
            success=True,
            status=VerificationStatus.PASSED,
            completion_time=datetime.utcnow(),
            passed_rules=["schema", "completeness"]
        )

        assert result.success is True
        assert result.status == VerificationStatus.PASSED
        assert len(result.passed_rules) == 2


class TestCompletionVerifier:
    """Tests for CompletionVerifier class."""

    @pytest.fixture
    def verifier(self):
        """Create a CompletionVerifier instance."""
        return CompletionVerifier(strict_mode=True)

    @pytest.fixture
    def mock_execution_result(self):
        """Create a mock execution result."""
        result = Mock()
        result.status = "completed"
        result.tasks_completed = 5
        result.tasks_failed = 0
        result.outputs = {"result": "success", "summary": "All done"}
        return result

    def test_initialization(self, verifier):
        """Test verifier initialization."""
        assert verifier.strict_mode is True
        assert verifier._required_outputs == []
        assert verifier._rules == []

    def test_add_required_output(self, verifier):
        """Test adding required output."""
        verifier.add_required_output("result")
        verifier.add_required_output("summary")

        outputs = verifier.get_required_outputs()
        assert "result" in outputs
        assert "summary" in outputs

    def test_add_duplicate_output(self, verifier):
        """Test adding duplicate output doesn't create duplicate."""
        verifier.add_required_output("result")
        verifier.add_required_output("result")

        outputs = verifier.get_required_outputs()
        assert outputs.count("result") == 1

    def test_remove_required_output(self, verifier):
        """Test removing required output."""
        verifier.add_required_output("result")
        verifier.remove_required_output("result")

        outputs = verifier.get_required_outputs()
        assert "result" not in outputs

    def test_add_rule(self, verifier):
        """Test adding verification rule."""
        rule = VerificationRule(name="schema_check", rule_type="schema")
        verifier.add_rule(rule)

        rules = verifier.get_rules()
        assert len(rules) == 1
        assert rules[0].name == "schema_check"

    @pytest.mark.asyncio
    async def test_verify_completion_success(self, verifier, mock_execution_result):
        """Test successful verification."""
        verifier.add_required_output("result")
        verifier.add_required_output("summary")

        result = await verifier.verify_completion(mock_execution_result)

        assert result.success is True
        assert result.status == VerificationStatus.PASSED
        assert result.outputs_verified["result"] is True
        assert result.outputs_verified["summary"] is True

    @pytest.mark.asyncio
    async def test_verify_completion_missing_output(self, verifier, mock_execution_result):
        """Test verification fails with missing output."""
        verifier.add_required_output("result")
        verifier.add_required_output("missing_output")

        result = await verifier.verify_completion(mock_execution_result)

        assert result.success is False
        assert result.status == VerificationStatus.FAILED
        assert result.outputs_verified["missing_output"] is False
        assert len(result.issues) > 0

    @pytest.mark.asyncio
    async def test_verify_completion_with_outputs_dict(self, verifier):
        """Test verification with outputs dictionary."""
        verifier.add_required_output("data")

        result = await verifier.verify_completion(
            outputs={"data": {"key": "value"}}
        )

        assert result.success is True
        assert result.outputs_verified["data"] is True

    @pytest.mark.asyncio
    async def test_verify_schema_rule(self, verifier, mock_execution_result):
        """Test schema verification rule."""
        verifier.add_rule(VerificationRule(
            name="schema_check",
            rule_type="schema",
            parameters={"schema": {"result": str}}
        ))

        result = await verifier.verify_completion(mock_execution_result)

        assert "schema_check" in result.passed_rules

    @pytest.mark.asyncio
    async def test_verify_completeness_rule(self, verifier, mock_execution_result):
        """Test completeness verification rule."""
        verifier.add_rule(VerificationRule(
            name="completeness_check",
            rule_type="completeness"
        ))

        result = await verifier.verify_completion(mock_execution_result)

        assert "completeness_check" in result.passed_rules

    @pytest.mark.asyncio
    async def test_verify_completeness_not_completed(self, verifier):
        """Test completeness rule fails when not completed."""
        mock_result = Mock()
        mock_result.status = "failed"
        mock_result.outputs = {}

        verifier.add_rule(VerificationRule(
            name="completeness_check",
            rule_type="completeness"
        ))

        result = await verifier.verify_completion(mock_result)

        assert "completeness_check" in result.failed_rules

    @pytest.mark.asyncio
    async def test_custom_validator(self, verifier):
        """Test custom validator function."""
        def validate_has_data(outputs):
            return "data" in outputs and outputs["data"] is not None

        verifier.add_custom_validator("has_data", validate_has_data)

        result = await verifier.verify_completion(outputs={"data": "value"})
        assert "has_data" in result.passed_rules

        result2 = await verifier.verify_completion(outputs={})
        assert "has_data" in result2.failed_rules

    @pytest.mark.asyncio
    async def test_non_strict_mode(self):
        """Test non-strict mode allows optional failures."""
        verifier = CompletionVerifier(strict_mode=False)
        verifier.add_rule(VerificationRule(
            name="optional_check",
            rule_type="schema",
            required=False
        ))

        result = await verifier.verify_completion(outputs={})

        # Should not fail for optional rule
        assert result.success is True or "optional_check" not in result.failed_rules

    @pytest.mark.asyncio
    async def test_async_mode(self):
        """Test async mode runs rules concurrently."""
        verifier = CompletionVerifier(strict_mode=True, async_mode=True)
        verifier.add_rule(VerificationRule(name="rule1", rule_type="schema"))
        verifier.add_rule(VerificationRule(name="rule2", rule_type="completeness"))

        mock_result = Mock()
        mock_result.status = "completed"
        mock_result.outputs = {}
        mock_result.tasks_completed = 5
        mock_result.tasks_failed = 0

        result = await verifier.verify_completion(mock_result)

        # Both rules should have been executed
        assert len(result.passed_rules) + len(result.failed_rules) == 2

    @pytest.mark.asyncio
    async def test_verify_with_failed_tasks(self, verifier):
        """Test completeness rule with task failures."""
        mock_result = Mock()
        mock_result.status = "completed"
        mock_result.tasks_completed = 8
        mock_result.tasks_failed = 2
        mock_result.outputs = {}

        verifier.add_rule(VerificationRule(
            name="completeness_check",
            rule_type="completeness",
            parameters={"failure_threshold": 0}
        ))

        result = await verifier.verify_completion(mock_result)

        assert "completeness_check" in result.failed_rules

    def test_clear(self, verifier):
        """Test clearing verifier state."""
        verifier.add_required_output("result")
        verifier.add_rule(VerificationRule(name="test", rule_type="schema"))

        verifier.clear()

        assert verifier.get_required_outputs() == []
        assert verifier.get_rules() == []

    @pytest.mark.asyncio
    async def test_verification_result_metadata(self, verifier, mock_execution_result):
        """Test verification result includes metadata."""
        verifier.add_required_output("result")
        verifier.add_rule(VerificationRule(name="test", rule_type="schema"))

        result = await verifier.verify_completion(mock_execution_result)

        assert "strict_mode" in result.metadata
        assert "total_rules" in result.metadata
        assert "total_required_outputs" in result.metadata
        assert result.metadata["strict_mode"] is True
        assert result.metadata["total_rules"] == 1
        assert result.metadata["total_required_outputs"] == 1
