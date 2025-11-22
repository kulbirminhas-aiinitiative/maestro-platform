"""
Unit tests for Circuit Breaker pattern.
"""

import pytest
import asyncio
from src.claude_team_sdk.resilience import (
    CircuitBreaker,
    CircuitState,
    CircuitBreakerOpenError
)


class TestCircuitBreaker:
    """Test circuit breaker functionality."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_closed_state(self):
        """Test circuit breaker starts in CLOSED state."""
        cb = CircuitBreaker(failure_threshold=3)
        assert cb.state == CircuitState.CLOSED
        assert cb.is_closed
        assert not cb.is_open
        assert not cb.is_half_open

    @pytest.mark.asyncio
    async def test_successful_call(self):
        """Test successful function call through circuit breaker."""
        cb = CircuitBreaker()

        async def successful_func():
            return "success"

        result = await cb.call(successful_func)
        assert result == "success"
        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_circuit_opens_after_failures(self):
        """Test circuit opens after threshold failures."""
        cb = CircuitBreaker(failure_threshold=3, name="test_cb")

        async def failing_func():
            raise ValueError("Test error")

        # Fail 3 times
        for i in range(3):
            with pytest.raises(ValueError):
                await cb.call(failing_func)

        # Circuit should be open now
        assert cb.state == CircuitState.OPEN
        assert cb.is_open

    @pytest.mark.asyncio
    async def test_circuit_open_rejects_calls(self):
        """Test open circuit rejects all calls."""
        cb = CircuitBreaker(failure_threshold=2)

        async def failing_func():
            raise ValueError("Test error")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                await cb.call(failing_func)

        assert cb.is_open

        # Next call should fail fast
        with pytest.raises(CircuitBreakerOpenError) as exc_info:
            await cb.call(failing_func)

        assert "is OPEN" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_circuit_half_open_after_timeout(self):
        """Test circuit transitions to HALF_OPEN after timeout."""
        cb = CircuitBreaker(failure_threshold=2, timeout=1)  # 1 second timeout

        async def failing_func():
            raise ValueError("Test error")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                await cb.call(failing_func)

        assert cb.is_open

        # Wait for timeout
        await asyncio.sleep(1.1)

        # Next call should attempt reset (circuit -> HALF_OPEN)
        async def success_func():
            return "success"

        result = await cb.call(success_func)
        assert result == "success"
        # After one success, it should still be checking
        # (needs success_threshold successes to fully close)

    @pytest.mark.asyncio
    async def test_circuit_closes_after_successful_half_open(self):
        """Test circuit closes after successful recovery."""
        cb = CircuitBreaker(
            failure_threshold=2,
            success_threshold=2,
            timeout=1
        )

        async def failing_func():
            raise ValueError("Test error")

        async def success_func():
            return "success"

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                await cb.call(failing_func)

        assert cb.is_open

        # Wait for timeout
        await asyncio.sleep(1.1)

        # Two successful calls should close the circuit
        await cb.call(success_func)
        await cb.call(success_func)

        assert cb.is_closed

    @pytest.mark.asyncio
    async def test_circuit_reopens_on_half_open_failure(self):
        """Test circuit reopens if call fails in HALF_OPEN state."""
        cb = CircuitBreaker(failure_threshold=2, timeout=1)

        async def failing_func():
            raise ValueError("Test error")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                await cb.call(failing_func)

        assert cb.is_open

        # Wait for timeout
        await asyncio.sleep(1.1)

        # Fail in HALF_OPEN state
        with pytest.raises(ValueError):
            await cb.call(failing_func)

        # Should be OPEN again
        assert cb.is_open

    @pytest.mark.asyncio
    async def test_manual_reset(self):
        """Test manual circuit breaker reset."""
        cb = CircuitBreaker(failure_threshold=2)

        async def failing_func():
            raise ValueError("Test error")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                await cb.call(failing_func)

        assert cb.is_open

        # Manual reset
        cb.reset()

        assert cb.is_closed
        assert cb.failure_count == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_with_args(self):
        """Test circuit breaker with function arguments."""
        cb = CircuitBreaker()

        async def func_with_args(a, b, c=None):
            return f"{a}-{b}-{c}"

        result = await cb.call(func_with_args, "x", "y", c="z")
        assert result == "x-y-z"
