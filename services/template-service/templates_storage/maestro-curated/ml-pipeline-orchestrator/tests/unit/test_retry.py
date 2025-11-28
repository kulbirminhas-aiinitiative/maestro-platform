"""Unit tests for retry with exponential backoff."""

import pytest
import asyncio
from src.infrastructure.resilience import (
    retry_with_backoff,
    RetryExhaustedError
)


@pytest.mark.asyncio
async def test_retry_succeeds_first_attempt():
    """Retry should succeed on first attempt"""
    call_count = 0

    async def succeeding_operation():
        nonlocal call_count
        call_count += 1
        return "success"

    result = await retry_with_backoff(succeeding_operation, max_retries=3)
    assert result == "success"
    assert call_count == 1


@pytest.mark.asyncio
async def test_retry_succeeds_after_failures():
    """Retry should succeed after transient failures"""
    call_count = 0

    async def eventually_succeeding_operation():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ValueError("Transient failure")
        return "success"

    result = await retry_with_backoff(
        eventually_succeeding_operation,
        max_retries=5,
        initial_delay=0.01
    )

    assert result == "success"
    assert call_count == 3


@pytest.mark.asyncio
async def test_retry_fails_after_max_retries():
    """Retry should fail after max retries exhausted"""
    call_count = 0

    async def always_failing_operation():
        nonlocal call_count
        call_count += 1
        raise ValueError("Permanent failure")

    with pytest.raises(RetryExhaustedError):
        await retry_with_backoff(
            always_failing_operation,
            max_retries=3,
            initial_delay=0.01
        )

    assert call_count == 4  # Initial + 3 retries


@pytest.mark.asyncio
async def test_retry_respects_retryable_exceptions():
    """Retry should only retry specified exceptions"""
    call_count = 0

    async def operation_with_non_retryable_error():
        nonlocal call_count
        call_count += 1
        raise TypeError("Non-retryable error")

    with pytest.raises(TypeError):
        await retry_with_backoff(
            operation_with_non_retryable_error,
            max_retries=3,
            retryable_exceptions=(ValueError,)
        )

    assert call_count == 1  # Should not retry


@pytest.mark.asyncio
async def test_retry_exponential_backoff():
    """Retry should use exponential backoff"""
    call_count = 0
    call_times = []

    async def failing_operation():
        nonlocal call_count
        call_count += 1
        call_times.append(asyncio.get_event_loop().time())
        raise ValueError("Failed")

    with pytest.raises(RetryExhaustedError):
        await retry_with_backoff(
            failing_operation,
            max_retries=2,
            initial_delay=0.1,
            backoff_factor=2.0
        )

    # Verify delays are increasing
    assert call_count == 3
    assert len(call_times) == 3

    # Check approximate delays (allowing for timing variance)
    delay1 = call_times[1] - call_times[0]
    delay2 = call_times[2] - call_times[1]
    assert 0.08 < delay1 < 0.15  # ~0.1s
    assert 0.18 < delay2 < 0.25  # ~0.2s
