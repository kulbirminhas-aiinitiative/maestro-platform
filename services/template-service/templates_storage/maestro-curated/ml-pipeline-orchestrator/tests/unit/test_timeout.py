"""Unit tests for timeout pattern."""

import pytest
import asyncio
from src.infrastructure.resilience import with_timeout, TimeoutError


@pytest.mark.asyncio
async def test_timeout_succeeds_within_limit():
    """Timeout should succeed if operation completes in time"""
    async def fast_operation():
        await asyncio.sleep(0.01)
        return "success"

    result = await with_timeout(fast_operation(), timeout_seconds=1.0)
    assert result == "success"


@pytest.mark.asyncio
async def test_timeout_fails_when_exceeded():
    """Timeout should raise TimeoutError when exceeded"""
    async def slow_operation():
        await asyncio.sleep(1.0)
        return "success"

    with pytest.raises(TimeoutError) as exc_info:
        await with_timeout(slow_operation(), timeout_seconds=0.1)

    assert "exceeded 0.1s timeout" in str(exc_info.value)


@pytest.mark.asyncio
async def test_timeout_with_custom_operation_name():
    """Timeout should include operation name in error"""
    async def slow_operation():
        await asyncio.sleep(1.0)
        return "success"

    with pytest.raises(TimeoutError) as exc_info:
        await with_timeout(
            slow_operation(),
            timeout_seconds=0.1,
            operation_name="custom_operation"
        )

    assert "custom_operation" in str(exc_info.value)
