"""
Tests for PersonaExecutor (Level 1 Retry)

EPIC: MD-3091 - Unified Execution Foundation
AC-3: Single PersonaExecutor replaces 3 implementations
AC-4: Two-level retry operational (internal 3x)
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from maestro_hive.unified_execution import (
    PersonaExecutor,
    ExecutionConfig,
    Level1Config,
    ExecutionStatus,
    RecoverableError,
    UnrecoverableError,
    TokenBudgetExceeded,
)


class TestPersonaExecutorBasic:
    """Basic functionality tests."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return ExecutionConfig(
            level1=Level1Config(
                max_attempts=3,
                base_delay_seconds=0.1,  # Fast for tests
                max_delay_seconds=0.5,
                enable_self_healing=False,
            ),
            timeout_seconds=5.0,
        )

    @pytest.fixture
    def executor(self, config):
        """Create executor instance."""
        return PersonaExecutor(config=config, persona_id="test_persona")

    @pytest.mark.asyncio
    async def test_successful_execution(self, executor):
        """Test successful task execution on first attempt."""

        async def success_task():
            return "success"

        result = await executor.execute(success_task, "test_task")

        assert result.success
        assert result.final_status == ExecutionStatus.SUCCESS
        assert result.final_output == "success"
        assert result.attempt_count == 1
        assert result.persona_id == "test_persona"

    @pytest.mark.asyncio
    async def test_retry_on_failure_then_success(self, executor):
        """Test retry mechanism with eventual success."""
        call_count = 0

        async def flaky_task():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Transient error")
            return "success"

        result = await executor.execute(flaky_task, "flaky_task")

        assert result.success
        assert result.attempt_count == 2
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_max_retries_exhausted(self, executor):
        """Test UnrecoverableError raised when all retries exhausted."""

        async def always_fail():
            raise ValueError("Persistent error")

        with pytest.raises(UnrecoverableError) as exc_info:
            await executor.execute(always_fail, "failing_task")

        assert "Level 1 retries exhausted" in str(exc_info.value)
        assert exc_info.value.failure_report is not None
        assert exc_info.value.failure_report.failed_persona == "test_persona"

    @pytest.mark.asyncio
    async def test_timeout_handling(self, config):
        """Test timeout handling."""
        config.timeout_seconds = 0.1
        executor = PersonaExecutor(config=config, persona_id="test")

        async def slow_task():
            await asyncio.sleep(1.0)
            return "should_not_reach"

        with pytest.raises(UnrecoverableError):
            await executor.execute(slow_task, "slow_task")


class TestSyntaxValidation:
    """Tests for Python syntax validation."""

    @pytest.fixture
    def executor(self):
        """Create executor with syntax validation enabled."""
        config = ExecutionConfig(
            level1=Level1Config(
                max_attempts=3,
                enable_syntax_validation=True,
                base_delay_seconds=0.01,
            )
        )
        return PersonaExecutor(config=config, persona_id="syntax_test")

    @pytest.mark.asyncio
    async def test_valid_python_code_passes(self, executor):
        """Test that valid Python code passes validation."""

        async def generate_valid_code():
            return '''def hello():
    return "Hello, World!"
'''

        result = await executor.execute(generate_valid_code, "generate_code")
        assert result.success

    @pytest.mark.asyncio
    async def test_invalid_python_syntax_triggers_retry(self, executor):
        """Test that invalid syntax triggers retry."""
        call_count = 0

        async def generate_code():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # Invalid syntax
                return "def broken(\n"
            return "def fixed(): pass"

        result = await executor.execute(generate_code, "generate_code")
        assert result.success
        assert call_count == 2  # First failed, second succeeded


class TestTokenBudget:
    """Tests for token budget enforcement."""

    @pytest.fixture
    def executor(self):
        """Create executor with token budget."""
        config = ExecutionConfig()
        config.tokens.max_tokens_per_persona = 1000
        config.tokens.enforce_budget = True
        return PersonaExecutor(config=config, persona_id="budget_test")

    def test_token_budget_tracking(self, executor):
        """Test token usage tracking."""
        assert executor.get_token_usage() == 0
        executor._tokens_used = 500
        assert executor.get_token_usage() == 500
        executor.reset_token_usage()
        assert executor.get_token_usage() == 0

    def test_token_budget_exceeded(self, executor):
        """Test token budget exceeded exception."""
        executor._tokens_used = 900

        with pytest.raises(TokenBudgetExceeded) as exc_info:
            executor._check_token_budget(200)

        assert exc_info.value.tokens_used == 1100
        assert exc_info.value.budget_limit == 1000


class TestExponentialBackoff:
    """Tests for exponential backoff calculation."""

    def test_backoff_calculation(self):
        """Test exponential backoff delay calculation."""
        config = ExecutionConfig(
            level1=Level1Config(
                base_delay_seconds=1.0,
                max_delay_seconds=10.0,
                backoff_multiplier=2.0,
            )
        )
        executor = PersonaExecutor(config=config)

        assert executor._calculate_delay(1) == 1.0  # 1.0 * 2^0
        assert executor._calculate_delay(2) == 2.0  # 1.0 * 2^1
        assert executor._calculate_delay(3) == 4.0  # 1.0 * 2^2
        assert executor._calculate_delay(4) == 8.0  # 1.0 * 2^3
        assert executor._calculate_delay(5) == 10.0  # Capped at max


class TestErrorClassification:
    """Tests for error classification."""

    @pytest.fixture
    def executor(self):
        return PersonaExecutor(persona_id="classify_test")

    def test_syntax_error_classification(self, executor):
        """Test syntax error classification."""
        error = RecoverableError("Syntax error", error_category="SYNTAX")
        assert executor._classify_error(error) == "SYNTAX"

    def test_timeout_error_classification(self, executor):
        """Test timeout error classification."""
        error = asyncio.TimeoutError("Timed out")
        assert executor._classify_error(error) == "TIMEOUT"

    def test_unknown_error_classification(self, executor):
        """Test unknown error classification."""
        error = RuntimeError("Something went wrong")
        assert executor._classify_error(error) == "UNKNOWN"


class TestExecutionResult:
    """Tests for ExecutionResult serialization."""

    @pytest.mark.asyncio
    async def test_result_to_dict(self):
        """Test ExecutionResult serialization."""
        executor = PersonaExecutor(persona_id="serialize_test")

        async def simple_task():
            return "done"

        result = await executor.execute(simple_task, "test_task")
        result_dict = result.to_dict()

        assert result_dict["task_name"] == "test_task"
        assert result_dict["persona_id"] == "serialize_test"
        assert result_dict["final_status"] == "success"
        assert result_dict["success"] is True
        assert "execution_id" in result_dict
        assert "created_at" in result_dict
