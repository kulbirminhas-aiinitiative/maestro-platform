"""Unit tests for circuit breaker."""

import pytest
import asyncio
from src.backend.infrastructure.resilience import CircuitBreaker, CircuitBreakerOpenError, CircuitState


@pytest.mark.asyncio
async def test_circuit_breaker_starts_closed():
    """Circuit breaker should start in CLOSED state."""
    breaker = CircuitBreaker(failure_threshold=3)
    assert breaker.get_state() == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_failures():
    """Circuit breaker should open after reaching failure threshold."""
    breaker = CircuitBreaker(failure_threshold=3)

    async def failing_operation():
        raise ValueError("Operation failed")

    # Trigger failures
    for _ in range(3):
        with pytest.raises(ValueError):
            await breaker.call(failing_operation)

    assert breaker.get_state() == CircuitState.OPEN


@pytest.mark.asyncio
async def test_circuit_breaker_blocks_when_open():
    """Circuit breaker should block requests when open."""
    breaker = CircuitBreaker(failure_threshold=2, timeout=1)

    async def failing_operation():
        raise ValueError("Operation failed")

    # Open the circuit
    for _ in range(2):
        with pytest.raises(ValueError):
            await breaker.call(failing_operation)

    # Should block new requests
    with pytest.raises(CircuitBreakerOpenError):
        await breaker.call(failing_operation)


@pytest.mark.asyncio
async def test_circuit_breaker_half_open_after_timeout():
    """Circuit breaker should transition to HALF_OPEN after timeout."""
    breaker = CircuitBreaker(failure_threshold=2, timeout=0.1)

    async def failing_operation():
        raise ValueError("Operation failed")

    # Open the circuit
    for _ in range(2):
        with pytest.raises(ValueError):
            await breaker.call(failing_operation)

    assert breaker.get_state() == CircuitState.OPEN

    # Wait for timeout
    await asyncio.sleep(0.15)

    # Next call should transition to HALF_OPEN
    async def successful_operation():
        return "success"

    result = await breaker.call(successful_operation)
    assert result == "success"


@pytest.mark.asyncio
async def test_circuit_breaker_closes_after_successes():
    """Circuit breaker should close after successful calls in HALF_OPEN."""
    breaker = CircuitBreaker(failure_threshold=2, success_threshold=2, timeout=0.1)

    async def failing_operation():
        raise ValueError("Failed")

    async def successful_operation():
        return "success"

    # Open circuit
    for _ in range(2):
        with pytest.raises(ValueError):
            await breaker.call(failing_operation)

    # Wait for timeout
    await asyncio.sleep(0.15)

    # Succeed twice to close
    await breaker.call(successful_operation)
    await breaker.call(successful_operation)

    assert breaker.get_state() == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_circuit_breaker_resets_failure_count_on_success():
    """Circuit breaker should reset failure count on successful call."""
    breaker = CircuitBreaker(failure_threshold=3)

    async def failing_operation():
        raise ValueError("Failed")

    async def successful_operation():
        return "success"

    # Fail twice
    for _ in range(2):
        with pytest.raises(ValueError):
            await breaker.call(failing_operation)

    assert breaker.failure_count == 2

    # Succeed once
    await breaker.call(successful_operation)

    # Failure count should be reset
    assert breaker.failure_count == 0
    assert breaker.get_state() == CircuitState.CLOSED
