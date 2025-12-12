"""
Tests for SafetyRetryWrapper (Level 2 Retry)

EPIC: MD-3091 - Unified Execution Foundation
AC-4: Two-level retry operational (external 2x with circuit breaker)
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from maestro_hive.unified_execution import (
    SafetyRetryWrapper,
    PersonaExecutor,
    ExecutionConfig,
    Level1Config,
    Level2Config,
    ExecutionStatus,
    UnrecoverableError,
    HelpNeeded,
    CircuitBreakerOpen,
    CircuitBreaker,
    CircuitState,
    FailureReport,
)


class TestCircuitBreaker:
    """Tests for CircuitBreaker pattern."""

    def test_initial_state_closed(self):
        """Test circuit breaker starts closed."""
        cb = CircuitBreaker(threshold=3)
        assert cb.state == CircuitState.CLOSED
        assert cb.consecutive_failures == 0

    def test_opens_after_threshold_failures(self):
        """Test circuit breaker opens after threshold failures."""
        cb = CircuitBreaker(threshold=3)

        cb.record_failure()
        assert cb.state == CircuitState.CLOSED

        cb.record_failure()
        assert cb.state == CircuitState.CLOSED

        cb.record_failure()  # Threshold reached
        assert cb.state == CircuitState.OPEN
        assert cb.is_open()

    def test_success_resets_failures(self):
        """Test success resets consecutive failures."""
        cb = CircuitBreaker(threshold=3)

        cb.record_failure()
        cb.record_failure()
        assert cb.consecutive_failures == 2

        cb.record_success()
        assert cb.consecutive_failures == 0
        assert cb.state == CircuitState.CLOSED

    def test_half_open_after_cooldown(self):
        """Test circuit transitions to half-open after cooldown."""
        cb = CircuitBreaker(threshold=1, cooldown_seconds=0)  # Instant cooldown

        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        # Check if open - should transition to half-open
        assert not cb.is_open()  # Cooldown passed
        assert cb.state == CircuitState.HALF_OPEN

    def test_to_dict_serialization(self):
        """Test circuit breaker serialization."""
        cb = CircuitBreaker(threshold=5, cooldown_seconds=300)
        cb.record_failure()

        cb_dict = cb.to_dict()

        assert cb_dict["state"] == "closed"
        assert cb_dict["consecutive_failures"] == 1
        assert cb_dict["threshold"] == 5
        assert cb_dict["cooldown_seconds"] == 300


class TestSafetyRetryWrapper:
    """Tests for SafetyRetryWrapper Level 2 execution."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return ExecutionConfig(
            level1=Level1Config(
                max_attempts=2,
                base_delay_seconds=0.01,
            ),
            level2=Level2Config(
                max_attempts=2,
                base_delay_seconds=0.01,
                circuit_breaker_threshold=5,
                enable_jira_escalation=False,  # Disable for tests
            ),
            timeout_seconds=5.0,
        )

    @pytest.fixture
    def wrapper(self, config):
        """Create wrapper instance."""
        return SafetyRetryWrapper(config=config)

    @pytest.fixture
    def executor(self, config):
        """Create executor instance."""
        return PersonaExecutor(config=config, persona_id="test_persona")

    @pytest.mark.asyncio
    async def test_successful_execution(self, wrapper, executor):
        """Test successful execution passes through."""

        async def success_task():
            return "success"

        result = await wrapper.execute_safe(
            executor.execute, success_task, task_name="test_task"
        )

        assert result.success
        assert result.final_status == ExecutionStatus.SUCCESS
        assert result.level2_attempts == 1

    @pytest.mark.asyncio
    async def test_level2_retry_on_level1_exhaustion(self, config):
        """Test Level 2 retries when Level 1 is exhausted."""
        # Configure for predictable behavior
        config.level1.max_attempts = 1
        config.level2.max_attempts = 3

        wrapper = SafetyRetryWrapper(config=config)

        # Use a mutable container to track state across executor recreations
        state = {"call_count": 0}

        async def flaky_task():
            state["call_count"] += 1
            if state["call_count"] < 3:  # Fail first 2 calls, succeed on 3rd
                raise ValueError("Fail")
            return "success"

        # Need fresh executor for each L2 attempt to share the task state
        executor = PersonaExecutor(config=config, persona_id="test")
        result = await wrapper.execute_safe(
            executor.execute, flaky_task, task_name="flaky_task"
        )

        assert result.success
        assert result.level2_attempts >= 1

    @pytest.mark.asyncio
    async def test_help_needed_when_all_exhausted(self, config):
        """Test HelpNeeded raised when all retries exhausted."""
        config.level1.max_attempts = 1
        config.level2.max_attempts = 1

        wrapper = SafetyRetryWrapper(config=config)
        executor = PersonaExecutor(config=config, persona_id="test")

        async def always_fail():
            raise ValueError("Persistent error")

        with pytest.raises(HelpNeeded) as exc_info:
            await wrapper.execute_safe(
                executor.execute, always_fail, task_name="failing_task"
            )

        assert "All retry levels exhausted" in str(exc_info.value)
        assert exc_info.value.failure_report is not None

    @pytest.mark.asyncio
    async def test_circuit_breaker_blocks_when_open(self, config):
        """Test circuit breaker blocks execution when open."""
        config.level2.circuit_breaker_threshold = 1  # Open after 1 failure

        wrapper = SafetyRetryWrapper(config=config)

        # Force circuit breaker open
        wrapper.circuit_breaker.record_failure()
        wrapper.circuit_breaker.cooldown_seconds = 3600  # Long cooldown

        async def any_task():
            return "should_not_run"

        with pytest.raises(CircuitBreakerOpen) as exc_info:
            await wrapper.execute_safe(
                AsyncMock(return_value=MagicMock(success=True)),
                any_task,
                task_name="blocked_task",
            )

        assert "Circuit breaker is OPEN" in str(exc_info.value)


class TestLevel2Result:
    """Tests for Level2Result serialization."""

    @pytest.mark.asyncio
    async def test_result_serialization(self):
        """Test Level2Result to_dict."""
        config = ExecutionConfig(
            level1=Level1Config(max_attempts=1, base_delay_seconds=0.01),
            level2=Level2Config(max_attempts=1, base_delay_seconds=0.01),
        )
        wrapper = SafetyRetryWrapper(config=config)
        executor = PersonaExecutor(config=config, persona_id="test")

        async def simple_task():
            return "done"

        result = await wrapper.execute_safe(
            executor.execute, simple_task, task_name="serialize_test"
        )

        result_dict = result.to_dict()

        assert result_dict["task_name"] == "serialize_test"
        assert result_dict["final_status"] == "success"
        assert result_dict["success"] is True
        assert "level1_results" in result_dict
        assert "circuit_breaker_state" in result_dict


class TestExponentialBackoff:
    """Tests for Level 2 exponential backoff."""

    def test_backoff_calculation(self):
        """Test Level 2 exponential backoff."""
        config = ExecutionConfig(
            level2=Level2Config(
                base_delay_seconds=5.0,
                max_delay_seconds=60.0,
                backoff_multiplier=2.0,
            )
        )
        wrapper = SafetyRetryWrapper(config=config)

        assert wrapper._calculate_delay(1) == 5.0  # 5.0 * 2^0
        assert wrapper._calculate_delay(2) == 10.0  # 5.0 * 2^1
        assert wrapper._calculate_delay(3) == 20.0  # 5.0 * 2^2
        assert wrapper._calculate_delay(4) == 40.0  # 5.0 * 2^3
        assert wrapper._calculate_delay(5) == 60.0  # Capped at max
