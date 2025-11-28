"""Unit tests for circuit breaker pattern."""

import pytest
import asyncio
from src.infrastructure.resilience import (
    CircuitBreaker,
    CircuitBreakerOpenError,
    CircuitState
)


@pytest.mark.asyncio
async def test_circuit_breaker_starts_closed():
    """Circuit breaker should start in CLOSED state"""
    breaker = CircuitBreaker(failure_threshold=3)
    assert breaker.get_state() == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_failures():
    """Circuit breaker should open after failure threshold"""
    breaker = CircuitBreaker(failure_threshold=3, timeout=0.1)
    call_count = 0

    async def failing_operation():
        nonlocal call_count
        call_count += 1
        raise ValueError("Operation failed")

    # Trigger failures to open circuit
    for _ in range(3):
        with pytest.raises(ValueError):
            await breaker.call(failing_operation)

    # Circuit should now be open
    assert breaker.get_state() == CircuitState.OPEN


@pytest.mark.asyncio
async def test_circuit_breaker_blocks_calls_when_open():
    """Circuit breaker should block calls when OPEN"""
    breaker = CircuitBreaker(failure_threshold=2, timeout=10)

    async def failing_operation():
        raise ValueError("Failed")

    # Open the circuit
    for _ in range(2):
        with pytest.raises(ValueError):
            await breaker.call(failing_operation)

    # Next call should be blocked
    with pytest.raises(CircuitBreakerOpenError):
        await breaker.call(failing_operation)


@pytest.mark.asyncio
async def test_circuit_breaker_half_open_after_timeout():
    """Circuit breaker should enter HALF_OPEN after timeout"""
    breaker = CircuitBreaker(failure_threshold=2, timeout=0.1)

    async def failing_operation():
        raise ValueError("Failed")

    # Open the circuit
    for _ in range(2):
        with pytest.raises(ValueError):
            await breaker.call(failing_operation)

    assert breaker.get_state() == CircuitState.OPEN

    # Wait for timeout
    await asyncio.sleep(0.15)

    # Next call should attempt in HALF_OPEN
    async def succeeding_operation():
        return "success"

    result = await breaker.call(succeeding_operation)
    assert result == "success"


@pytest.mark.asyncio
async def test_circuit_breaker_closes_after_successes():
    """Circuit breaker should close after success threshold in HALF_OPEN"""
    breaker = CircuitBreaker(
        failure_threshold=2,
        success_threshold=2,
        timeout=0.1
    )

    async def failing_operation():
        raise ValueError("Failed")

    async def succeeding_operation():
        return "success"

    # Open the circuit
    for _ in range(2):
        with pytest.raises(ValueError):
            await breaker.call(failing_operation)

    # Wait for timeout
    await asyncio.sleep(0.15)

    # Succeed twice to close circuit
    await breaker.call(succeeding_operation)
    await breaker.call(succeeding_operation)

    assert breaker.get_state() == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_circuit_breaker_resets_failure_count_on_success():
    """Circuit breaker should reset failure count on success"""
    breaker = CircuitBreaker(failure_threshold=3)
    call_count = 0

    async def sometimes_failing_operation():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ValueError("Failed")
        return "success"

    # Fail twice
    for _ in range(2):
        with pytest.raises(ValueError):
            await breaker.call(sometimes_failing_operation)

    # Succeed once (should reset failure count)
    result = await breaker.call(sometimes_failing_operation)
    assert result == "success"
    assert breaker.get_state() == CircuitState.CLOSED
