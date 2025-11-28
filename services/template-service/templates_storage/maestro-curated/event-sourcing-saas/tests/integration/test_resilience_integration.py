"""Integration tests for resilience patterns."""

import pytest
import asyncio
from src.backend.infrastructure.resilience import (
    CircuitBreaker,
    CircuitBreakerOpenError,
    retry_with_backoff,
    with_timeout,
    TimeoutError,
    with_fallback
)


@pytest.mark.asyncio
async def test_circuit_breaker_with_retry():
    """Circuit breaker and retry should work together."""
    breaker = CircuitBreaker(failure_threshold=2, timeout=0.1)
    call_count = 0

    async def flaky_operation():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ValueError("Temporary failure")
        return "success"

    async def operation_with_breaker():
        return await breaker.call(flaky_operation)

    result = await retry_with_backoff(
        operation_with_breaker,
        max_retries=5,
        initial_delay=0.01
    )

    assert result == "success"
    assert call_count == 3


@pytest.mark.asyncio
async def test_timeout_with_fallback():
    """Timeout and fallback should work together."""
    async def slow_primary():
        await asyncio.sleep(1.0)
        return "primary"

    async def fast_fallback():
        return "fallback"

    async def primary_with_timeout():
        return await with_timeout(slow_primary(), timeout_seconds=0.1)

    result = await with_fallback(primary_with_timeout, fast_fallback)
    assert result == "fallback"


@pytest.mark.asyncio
async def test_all_patterns_combined():
    """All resilience patterns should work together."""
    breaker = CircuitBreaker(failure_threshold=3, timeout=0.1)
    call_count = 0

    async def unreliable_operation():
        nonlocal call_count
        call_count += 1

        # Fail first 2 times
        if call_count <= 2:
            raise ValueError("Temporary failure")

        # Succeed on 3rd attempt
        await asyncio.sleep(0.01)
        return f"success on attempt {call_count}"

    async def primary_with_all_patterns():
        async def operation_with_timeout():
            return await with_timeout(
                breaker.call(unreliable_operation),
                timeout_seconds=1.0
            )

        return await retry_with_backoff(
            operation_with_timeout,
            max_retries=5,
            initial_delay=0.01
        )

    async def fallback_operation():
        return "fallback result"

    result = await with_fallback(primary_with_all_patterns, fallback_operation)
    assert result == "success on attempt 3"
