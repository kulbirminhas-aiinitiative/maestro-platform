"""Unit tests for retry with exponential backoff."""

import pytest
import asyncio
from src.backend.infrastructure.resilience import retry_with_backoff


@pytest.mark.asyncio
async def test_retry_succeeds_on_first_attempt():
    """Should return result on first successful attempt."""
    call_count = 0

    async def successful_operation():
        nonlocal call_count
        call_count += 1
        return "success"

    result = await retry_with_backoff(successful_operation, max_retries=3)
    assert result == "success"
    assert call_count == 1


@pytest.mark.asyncio
async def test_retry_succeeds_after_failures():
    """Should retry and eventually succeed."""
    call_count = 0

    async def eventually_succeeds():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ValueError("Not yet")
        return "success"

    result = await retry_with_backoff(eventually_succeeds, max_retries=3, initial_delay=0.01)
    assert result == "success"
    assert call_count == 3


@pytest.mark.asyncio
async def test_retry_fails_after_max_retries():
    """Should raise last exception after exhausting retries."""
    call_count = 0

    async def always_fails():
        nonlocal call_count
        call_count += 1
        raise ValueError(f"Attempt {call_count} failed")

    with pytest.raises(ValueError, match="Attempt 4 failed"):
        await retry_with_backoff(always_fails, max_retries=3, initial_delay=0.01)

    assert call_count == 4  # Initial + 3 retries


@pytest.mark.asyncio
async def test_retry_respects_retryable_exceptions():
    """Should only retry on specified exceptions."""
    call_count = 0

    async def raises_different_exception():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise ValueError("Retryable")
        raise TypeError("Not retryable")

    with pytest.raises(TypeError):
        await retry_with_backoff(
            raises_different_exception,
            max_retries=3,
            initial_delay=0.01,
            retryable_exceptions=(ValueError,)
        )

    assert call_count == 2  # Retried once for ValueError, then failed on TypeError


@pytest.mark.asyncio
async def test_retry_exponential_backoff():
    """Should increase delay exponentially between retries."""
    import time

    call_times = []

    async def failing_operation():
        call_times.append(time.time())
        raise ValueError("Failed")

    with pytest.raises(ValueError):
        await retry_with_backoff(
            failing_operation,
            max_retries=3,
            initial_delay=0.1,
            backoff_factor=2.0
        )

    # Check delays are increasing (approximately 0.1s, 0.2s, 0.4s)
    assert len(call_times) == 4
    delay1 = call_times[1] - call_times[0]
    delay2 = call_times[2] - call_times[1]

    assert 0.08 < delay1 < 0.15  # ~0.1s
    assert 0.15 < delay2 < 0.25  # ~0.2s
