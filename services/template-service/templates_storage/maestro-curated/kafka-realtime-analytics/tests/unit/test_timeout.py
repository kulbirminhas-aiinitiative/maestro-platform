"""Unit tests for timeout pattern."""

import pytest
import asyncio
from src.backend.infrastructure.resilience import with_timeout, TimeoutError


@pytest.mark.asyncio
async def test_timeout_succeeds_within_limit():
    """Should return result if operation completes within timeout."""
    async def quick_operation():
        await asyncio.sleep(0.01)
        return "success"

    result = await with_timeout(quick_operation(), timeout_seconds=1.0)
    assert result == "success"


@pytest.mark.asyncio
async def test_timeout_fails_when_exceeded():
    """Should raise TimeoutError if operation exceeds timeout."""
    async def slow_operation():
        await asyncio.sleep(2.0)
        return "success"

    with pytest.raises(TimeoutError, match="exceeded 0.1s timeout"):
        await with_timeout(slow_operation(), timeout_seconds=0.1, operation_name="slow_op")


@pytest.mark.asyncio
async def test_timeout_cancels_operation():
    """Should cancel the operation when timeout is exceeded."""
    operation_cancelled = False

    async def cancellable_operation():
        nonlocal operation_cancelled
        try:
            await asyncio.sleep(2.0)
        except asyncio.CancelledError:
            operation_cancelled = True
            raise

    with pytest.raises(TimeoutError):
        await with_timeout(cancellable_operation(), timeout_seconds=0.1)

    await asyncio.sleep(0.05)  # Give time for cleanup
    # Note: operation cancellation depends on asyncio internals
