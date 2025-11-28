"""Unit tests for fallback pattern."""

import pytest
from src.backend.infrastructure.resilience import with_fallback, FallbackValue


@pytest.mark.asyncio
async def test_fallback_uses_primary_on_success():
    """Should use primary function when it succeeds."""
    async def primary():
        return "primary"

    async def fallback():
        return "fallback"

    result = await with_fallback(primary, fallback)
    assert result == "primary"


@pytest.mark.asyncio
async def test_fallback_uses_fallback_on_failure():
    """Should use fallback function when primary fails."""
    async def primary():
        raise ValueError("Primary failed")

    async def fallback():
        return "fallback"

    result = await with_fallback(primary, fallback)
    assert result == "fallback"


@pytest.mark.asyncio
async def test_fallback_raises_when_both_fail():
    """Should raise fallback exception when both fail."""
    async def primary():
        raise ValueError("Primary failed")

    async def fallback():
        raise RuntimeError("Fallback failed")

    with pytest.raises(RuntimeError, match="Fallback failed"):
        await with_fallback(primary, fallback)


@pytest.mark.asyncio
async def test_fallback_value_none():
    """Should provide None as fallback value."""
    async def failing_operation():
        raise ValueError("Failed")

    result = await with_fallback(failing_operation, FallbackValue.none)
    assert result is None


@pytest.mark.asyncio
async def test_fallback_value_empty_list():
    """Should provide empty list as fallback value."""
    async def failing_operation():
        raise ValueError("Failed")

    result = await with_fallback(failing_operation, FallbackValue.empty_list)
    assert result == []


@pytest.mark.asyncio
async def test_fallback_value_constant():
    """Should provide constant value as fallback."""
    async def failing_operation():
        raise ValueError("Failed")

    result = await with_fallback(failing_operation, FallbackValue.constant({"default": True}))
    assert result == {"default": True}
