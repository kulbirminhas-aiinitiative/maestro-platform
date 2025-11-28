"""Unit tests for fallback pattern."""

import pytest
from src.infrastructure.resilience import with_fallback


@pytest.mark.asyncio
async def test_fallback_uses_primary_when_successful():
    """Fallback should use primary operation when it succeeds"""
    async def primary():
        return "primary_result"

    async def fallback():
        return "fallback_result"

    result = await with_fallback(primary, fallback)
    assert result == "primary_result"


@pytest.mark.asyncio
async def test_fallback_uses_fallback_when_primary_fails():
    """Fallback should use fallback operation when primary fails"""
    async def primary():
        raise ValueError("Primary failed")

    async def fallback():
        return "fallback_result"

    result = await with_fallback(primary, fallback)
    assert result == "fallback_result"


@pytest.mark.asyncio
async def test_fallback_fails_when_both_fail():
    """Fallback should raise exception when both operations fail"""
    async def primary():
        raise ValueError("Primary failed")

    async def fallback():
        raise RuntimeError("Fallback also failed")

    with pytest.raises(RuntimeError):
        await with_fallback(primary, fallback)


@pytest.mark.asyncio
async def test_fallback_with_arguments():
    """Fallback should pass arguments to both operations"""
    async def primary(x, y):
        if x < 0:
            raise ValueError("Negative value")
        return x + y

    async def fallback(x, y):
        return abs(x) + y

    # Primary succeeds
    result1 = await with_fallback(primary, fallback, x=5, y=3)
    assert result1 == 8

    # Primary fails, fallback succeeds
    result2 = await with_fallback(primary, fallback, x=-5, y=3)
    assert result2 == 8


@pytest.mark.asyncio
async def test_fallback_with_custom_operation_name():
    """Fallback should use custom operation name for logging"""
    call_log = []

    async def primary():
        call_log.append("primary")
        raise ValueError("Failed")

    async def fallback():
        call_log.append("fallback")
        return "fallback_result"

    result = await with_fallback(
        primary,
        fallback,
        operation_name="my_operation"
    )

    assert result == "fallback_result"
    assert call_log == ["primary", "fallback"]


@pytest.mark.asyncio
async def test_fallback_preserves_primary_result():
    """Fallback should not invoke fallback if primary succeeds"""
    fallback_called = False

    async def primary():
        return "primary_success"

    async def fallback():
        nonlocal fallback_called
        fallback_called = True
        return "fallback_result"

    result = await with_fallback(primary, fallback)
    assert result == "primary_success"
    assert not fallback_called
