#!/usr/bin/env python3
"""
Tests for ShiftLeftValidator (MD-3093: Shift-Left Validation Integration)

Tests cover all 4 acceptance criteria:
- AC-1: BDV contract checks run after each persona group
- AC-2: ACC architectural checks run incrementally
- AC-3: Critical violations stop execution immediately
- AC-4: Validator feedback reaches personas for correction
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from maestro_hive.teams.shift_left_validator import (
    ShiftLeftValidator,
    CriticalViolation,
    GroupValidationResult,
    ValidationFeedback,
    ValidationViolation,
    ViolationSeverity,
    SHIFT_LEFT_CONFIG
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def validator():
    """Create a ShiftLeftValidator instance."""
    return ShiftLeftValidator()


@pytest.fixture
def sample_contracts():
    """Sample contracts for testing."""
    return [
        {
            "id": "contract_001",
            "name": "Backend API Contract",
            "provider_persona_id": "backend_developer",
            "consumer_persona_ids": ["frontend_developer"],
            "acceptance_criteria": [
                "API endpoints respond correctly",
                "Error handling implemented"
            ],
            "deliverables": [
                {"name": "api_impl", "artifacts": ["backend/src/*.py"]}
            ]
        }
    ]


@pytest.fixture
def sample_group_result():
    """Sample group execution result."""
    return {
        "backend_developer": MagicMock(
            success=True,
            files_created=["backend/src/api.py"],
            quality_score=0.85,
            contract_fulfilled=True
        )
    }


@pytest.fixture
def temp_output_dir(tmp_path):
    """Temporary output directory."""
    output = tmp_path / "generated_project"
    output.mkdir()
    return output


# =============================================================================
# TEST: CONFIGURATION
# =============================================================================

class TestConfiguration:
    """Test validator configuration."""

    def test_default_config_loaded(self, validator):
        """Test that default configuration is loaded."""
        assert validator.config["enable_per_group_bdv"] == True
        assert validator.config["enable_per_group_acc"] == True
        assert validator.config["early_stop_on_critical"] == True
        assert validator.config["max_correction_retries"] == 2

    def test_custom_config_override(self):
        """Test custom configuration override."""
        custom = {"enable_per_group_bdv": False, "max_correction_retries": 5}
        validator = ShiftLeftValidator(config=custom)

        assert validator.config["enable_per_group_bdv"] == False
        assert validator.config["max_correction_retries"] == 5
        # Defaults should still be present
        assert validator.config["enable_per_group_acc"] == True


# =============================================================================
# TEST: AC-1 - BDV Contract Checks Per Group
# =============================================================================

class TestAC1BDVPerGroup:
    """AC-1: BDV contract checks run after each persona group."""

    @pytest.mark.asyncio
    async def test_bdv_validation_called_per_group(
        self, validator, sample_contracts, sample_group_result, temp_output_dir
    ):
        """Test that BDV validation is called for each group."""
        mock_bdv_service = MagicMock()
        mock_bdv_result = MagicMock(
            contracts_fulfilled=1,
            total_contracts=1,
            scenarios_passed=5,
            total_scenarios=5
        )
        mock_bdv_service.validate_contracts.return_value = mock_bdv_result

        with patch.object(validator, '_get_bdv_service', return_value=mock_bdv_service):
            result = await validator.validate_group(
                group_id="group_0",
                group_result=sample_group_result,
                contracts=sample_contracts,
                output_dir=temp_output_dir,
                execution_id="test_exec_001"
            )

            # BDV service should be called
            mock_bdv_service.validate_contracts.assert_called_once()
            # Result should have BDV score
            assert result.bdv_score > 0

    @pytest.mark.asyncio
    async def test_bdv_creates_violations_on_failure(
        self, validator, sample_contracts, sample_group_result, temp_output_dir
    ):
        """Test that BDV creates violations when contracts fail."""
        mock_bdv_service = MagicMock()
        mock_bdv_result = MagicMock(
            contracts_fulfilled=0,
            total_contracts=1,
            scenarios_passed=2,
            total_scenarios=5,
            failed_scenarios=[{"name": "API responds", "id": "scenario_1"}]
        )
        mock_bdv_service.validate_contracts.return_value = mock_bdv_result

        with patch.object(validator, '_get_bdv_service', return_value=mock_bdv_service):
            result = await validator.validate_group(
                group_id="group_0",
                group_result=sample_group_result,
                contracts=sample_contracts,
                output_dir=temp_output_dir,
                execution_id="test_exec_002"
            )

            # Should have violations
            assert len(result.violations) > 0
            bdv_violations = [v for v in result.violations if v.category == "bdv"]
            assert len(bdv_violations) > 0

    @pytest.mark.asyncio
    async def test_bdv_service_unavailable_graceful_fallback(
        self, validator, sample_contracts, sample_group_result, temp_output_dir
    ):
        """Test graceful fallback when BDV service unavailable."""
        with patch.object(validator, '_get_bdv_service', return_value=None):
            result = await validator.validate_group(
                group_id="group_0",
                group_result=sample_group_result,
                contracts=sample_contracts,
                output_dir=temp_output_dir,
                execution_id="test_exec_003"
            )

            # Should still return a result with default score
            assert result.bdv_score == 1.0
            assert result.passed  # No failures without service


# =============================================================================
# TEST: AC-2 - ACC Incremental Checks
# =============================================================================

class TestAC2ACCIncremental:
    """AC-2: ACC architectural checks run incrementally."""

    @pytest.mark.asyncio
    async def test_acc_validation_called_per_group(
        self, validator, sample_contracts, sample_group_result, temp_output_dir
    ):
        """Test that ACC validation is called for each group."""
        mock_acc_service = MagicMock()
        mock_acc_result = MagicMock(
            is_compliant=True,
            conformance_score=0.95,
            violations=MagicMock(total=0, blocking=0),
            cycles_detected=[]
        )
        mock_acc_service.validate_architecture.return_value = mock_acc_result

        with patch.object(validator, '_get_bdv_service', return_value=None):
            with patch.object(validator, '_get_acc_service', return_value=mock_acc_service):
                result = await validator.validate_group(
                    group_id="group_0",
                    group_result=sample_group_result,
                    contracts=sample_contracts,
                    output_dir=temp_output_dir,
                    execution_id="test_exec_004"
                )

                # ACC service should be called
                mock_acc_service.validate_architecture.assert_called_once()
                assert result.acc_score == 0.95

    @pytest.mark.asyncio
    async def test_acc_tracks_cumulative_state(
        self, validator, sample_contracts, sample_group_result, temp_output_dir
    ):
        """Test that ACC tracks cumulative state across groups."""
        mock_acc_service = MagicMock()
        mock_acc_result = MagicMock(
            is_compliant=True,
            conformance_score=0.90,
            violations=MagicMock(total=1, blocking=0),
            cycles_detected=[]
        )
        mock_acc_service.validate_architecture.return_value = mock_acc_result

        with patch.object(validator, '_get_bdv_service', return_value=None):
            with patch.object(validator, '_get_acc_service', return_value=mock_acc_service):
                # Validate first group
                await validator.validate_group(
                    group_id="group_0",
                    group_result=sample_group_result,
                    contracts=sample_contracts,
                    output_dir=temp_output_dir,
                    execution_id="test_exec_005"
                )

                # Check cumulative state is tracked
                assert "group_0" in validator._cumulative_state
                assert validator._cumulative_state["group_0"]["conformance_score"] == 0.90

    @pytest.mark.asyncio
    async def test_acc_detects_dependency_cycles(
        self, validator, sample_contracts, sample_group_result, temp_output_dir
    ):
        """Test that ACC detects and reports dependency cycles."""
        mock_acc_service = MagicMock()
        mock_acc_result = MagicMock(
            is_compliant=False,
            conformance_score=0.60,
            violations=MagicMock(total=2, blocking=0),
            cycles_detected=["A -> B -> C -> A"]
        )
        mock_acc_service.validate_architecture.return_value = mock_acc_result

        with patch.object(validator, '_get_bdv_service', return_value=None):
            with patch.object(validator, '_get_acc_service', return_value=mock_acc_service):
                result = await validator.validate_group(
                    group_id="group_0",
                    group_result=sample_group_result,
                    contracts=sample_contracts,
                    output_dir=temp_output_dir,
                    execution_id="test_exec_006"
                )

                # Should have cycle violations
                cycle_violations = [v for v in result.violations if "cycle" in v.message.lower()]
                assert len(cycle_violations) > 0


# =============================================================================
# TEST: AC-3 - Critical Violations Stop Execution
# =============================================================================

class TestAC3EarlyStop:
    """AC-3: Critical violations stop execution immediately."""

    @pytest.mark.asyncio
    async def test_blocking_violations_raise_critical_exception(
        self, validator, sample_contracts, sample_group_result, temp_output_dir
    ):
        """Test that blocking violations raise CriticalViolation."""
        mock_acc_service = MagicMock()
        mock_acc_result = MagicMock(
            is_compliant=False,
            conformance_score=0.20,
            violations=MagicMock(total=5, blocking=3),
            cycles_detected=[]
        )
        mock_acc_service.validate_architecture.return_value = mock_acc_result

        with patch.object(validator, '_get_bdv_service', return_value=None):
            with patch.object(validator, '_get_acc_service', return_value=mock_acc_service):
                with pytest.raises(CriticalViolation) as exc_info:
                    await validator.validate_group(
                        group_id="group_0",
                        group_result=sample_group_result,
                        contracts=sample_contracts,
                        output_dir=temp_output_dir,
                        execution_id="test_exec_007"
                    )

                assert exc_info.value.group_id == "group_0"
                assert len(exc_info.value.violations) > 0

    @pytest.mark.asyncio
    async def test_score_below_threshold_triggers_early_stop(
        self, validator, sample_contracts, sample_group_result, temp_output_dir
    ):
        """Test that scores below threshold trigger early stop."""
        # Set low threshold
        validator.config["critical_violation_threshold"] = 0.5

        mock_bdv_service = MagicMock()
        mock_bdv_result = MagicMock(
            contracts_fulfilled=0,
            total_contracts=2,
            scenarios_passed=0,
            total_scenarios=10
        )
        mock_bdv_service.validate_contracts.return_value = mock_bdv_result

        mock_acc_service = MagicMock()
        mock_acc_result = MagicMock(
            is_compliant=False,
            conformance_score=0.20,
            violations=MagicMock(total=3, blocking=0),
            cycles_detected=[]
        )
        mock_acc_service.validate_architecture.return_value = mock_acc_result

        with patch.object(validator, '_get_bdv_service', return_value=mock_bdv_service):
            with patch.object(validator, '_get_acc_service', return_value=mock_acc_service):
                with pytest.raises(CriticalViolation) as exc_info:
                    await validator.validate_group(
                        group_id="group_0",
                        group_result=sample_group_result,
                        contracts=sample_contracts,
                        output_dir=temp_output_dir,
                        execution_id="test_exec_008"
                    )

                assert "threshold" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_early_stop_disabled_continues_execution(
        self, validator, sample_contracts, sample_group_result, temp_output_dir
    ):
        """Test that disabling early stop allows continuation without exception."""
        validator.config["early_stop_on_critical"] = False

        mock_acc_service = MagicMock()
        mock_acc_result = MagicMock(
            is_compliant=False,
            conformance_score=0.20,
            violations=MagicMock(total=5, blocking=3),
            cycles_detected=[]
        )
        mock_acc_service.validate_architecture.return_value = mock_acc_result

        with patch.object(validator, '_get_bdv_service', return_value=None):
            with patch.object(validator, '_get_acc_service', return_value=mock_acc_service):
                # Should NOT raise exception when early_stop_on_critical=False
                result = await validator.validate_group(
                    group_id="group_0",
                    group_result=sample_group_result,
                    contracts=sample_contracts,
                    output_dir=temp_output_dir,
                    execution_id="test_exec_009"
                )

                # Result should indicate issues but not stop execution
                assert not result.passed  # Failed validation
                # When early_stop is disabled, should_stop is set but no exception raised
                # Violations are still recorded
                assert len(result.violations) > 0
                blocking_violations = [v for v in result.violations if v.severity == ViolationSeverity.BLOCKING]
                assert len(blocking_violations) > 0


# =============================================================================
# TEST: AC-4 - Feedback for Correction
# =============================================================================

class TestAC4FeedbackCorrection:
    """AC-4: Validator feedback reaches personas for correction."""

    @pytest.mark.asyncio
    async def test_feedback_generated_on_violations(
        self, validator, sample_contracts, sample_group_result, temp_output_dir
    ):
        """Test that feedback is generated when violations occur."""
        validator.config["early_stop_on_critical"] = False

        mock_bdv_service = MagicMock()
        mock_bdv_result = MagicMock(
            contracts_fulfilled=0,
            total_contracts=1,
            scenarios_passed=3,
            total_scenarios=5,
            failed_scenarios=[]
        )
        mock_bdv_service.validate_contracts.return_value = mock_bdv_result

        with patch.object(validator, '_get_bdv_service', return_value=mock_bdv_service):
            with patch.object(validator, '_get_acc_service', return_value=None):
                result = await validator.validate_group(
                    group_id="group_0",
                    group_result=sample_group_result,
                    contracts=sample_contracts,
                    output_dir=temp_output_dir,
                    execution_id="test_exec_010"
                )

                # Should have feedback
                assert result.feedback is not None
                assert isinstance(result.feedback, ValidationFeedback)

    def test_feedback_contains_actionable_suggestions(self, validator):
        """Test that feedback contains actionable suggestions."""
        violations = [
            ValidationViolation(
                id="v1",
                severity=ViolationSeverity.HIGH,
                category="bdv",
                message="Contract not fulfilled",
                suggestion="Check deliverables"
            )
        ]

        feedback = validator._generate_feedback(
            group_id="group_0",
            violations=violations,
            group_result={"backend_developer": MagicMock()}
        )

        assert len(feedback.suggestions) > 0
        assert feedback.persona_id == "backend_developer"

    def test_feedback_to_prompt_context_format(self, validator):
        """Test that feedback can be converted to prompt context."""
        violations = [
            ValidationViolation(
                id="v1",
                severity=ViolationSeverity.HIGH,
                category="bdv",
                message="API validation failed",
                suggestion="Add input validation"
            )
        ]

        feedback = validator._generate_feedback(
            group_id="group_0",
            violations=violations,
            group_result={"backend_developer": MagicMock()}
        )

        prompt_context = feedback.to_prompt_context()

        assert "VALIDATION FEEDBACK" in prompt_context
        assert "HIGH" in prompt_context
        assert "API validation failed" in prompt_context
        assert "Add input validation" in prompt_context

    def test_feedback_priority_based_on_severity(self, validator):
        """Test that feedback priority reflects violation severity."""
        # Blocking violation
        blocking_violations = [
            ValidationViolation(
                id="v1",
                severity=ViolationSeverity.BLOCKING,
                category="acc",
                message="Security violation"
            )
        ]

        feedback_blocking = validator._generate_feedback(
            group_id="group_0",
            violations=blocking_violations,
            group_result={}
        )
        assert feedback_blocking.priority == ViolationSeverity.BLOCKING

        # High violation
        high_violations = [
            ValidationViolation(
                id="v2",
                severity=ViolationSeverity.HIGH,
                category="bdv",
                message="Contract issue"
            )
        ]

        feedback_high = validator._generate_feedback(
            group_id="group_1",
            violations=high_violations,
            group_result={}
        )
        assert feedback_high.priority == ViolationSeverity.HIGH


# =============================================================================
# TEST: VALIDATION HISTORY
# =============================================================================

class TestValidationHistory:
    """Test validation history tracking."""

    @pytest.mark.asyncio
    async def test_validation_history_accumulated(
        self, validator, sample_contracts, sample_group_result, temp_output_dir
    ):
        """Test that validation history accumulates across groups."""
        with patch.object(validator, '_get_bdv_service', return_value=None):
            with patch.object(validator, '_get_acc_service', return_value=None):
                # Validate multiple groups
                await validator.validate_group(
                    group_id="group_0",
                    group_result=sample_group_result,
                    contracts=sample_contracts,
                    output_dir=temp_output_dir,
                    execution_id="test_exec_011"
                )

                await validator.validate_group(
                    group_id="group_1",
                    group_result=sample_group_result,
                    contracts=sample_contracts,
                    output_dir=temp_output_dir,
                    execution_id="test_exec_011"
                )

                history = validator.get_validation_history()
                assert len(history) == 2

    def test_cumulative_score_calculation(self, validator):
        """Test cumulative score calculation."""
        # Manually add history
        validator._validation_history = [
            GroupValidationResult(
                group_id="g1", passed=True, bdv_score=0.8, acc_score=0.9,
                violations=[]
            ),
            GroupValidationResult(
                group_id="g2", passed=True, bdv_score=0.7, acc_score=0.8,
                violations=[]
            )
        ]

        cumulative = validator.get_cumulative_score()
        # (0.85 + 0.75) / 2 = 0.80
        assert 0.79 <= cumulative <= 0.81

    def test_reset_clears_state(self, validator):
        """Test that reset clears all state."""
        validator._validation_history = [MagicMock()]
        validator._cumulative_state = {"group_0": {"score": 0.8}}

        validator.reset()

        assert len(validator._validation_history) == 0
        assert len(validator._cumulative_state) == 0


# =============================================================================
# TEST: CRITICAL VIOLATION EXCEPTION
# =============================================================================

class TestCriticalViolationException:
    """Test CriticalViolation exception."""

    def test_exception_contains_violations(self):
        """Test that exception contains violations."""
        violations = [
            ValidationViolation(
                id="v1",
                severity=ViolationSeverity.BLOCKING,
                category="acc",
                message="Critical issue"
            )
        ]

        exc = CriticalViolation(
            message="Critical failure",
            violations=violations,
            group_id="group_0"
        )

        assert len(exc.violations) == 1
        assert exc.group_id == "group_0"

    def test_get_blocking_violations(self):
        """Test filtering blocking violations."""
        violations = [
            ValidationViolation(id="v1", severity=ViolationSeverity.BLOCKING, category="acc", message="Block1"),
            ValidationViolation(id="v2", severity=ViolationSeverity.HIGH, category="bdv", message="High1"),
            ValidationViolation(id="v3", severity=ViolationSeverity.BLOCKING, category="acc", message="Block2"),
        ]

        exc = CriticalViolation(
            message="Test",
            violations=violations,
            group_id="group_0"
        )

        blocking = exc.get_blocking_violations()
        assert len(blocking) == 2
        assert all(v.severity == ViolationSeverity.BLOCKING for v in blocking)


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
