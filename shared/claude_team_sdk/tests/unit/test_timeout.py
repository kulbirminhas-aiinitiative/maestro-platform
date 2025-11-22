"""
Unit tests for Timeout pattern.
"""

import pytest
import asyncio
from src.claude_team_sdk.resilience import with_timeout, TimeoutError


class TestTimeout:
    """Test timeout pattern."""

    @pytest.mark.asyncio
    async def test_function_completes_within_timeout(self):
        """Test function that completes within timeout."""
        async def quick_func():
            await asyncio.sleep(0.1)
            return "success"

        result = await with_timeout(quick_func, seconds=1.0)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_function_exceeds_timeout(self):
        """Test function that exceeds timeout."""
        async def slow_func():
            await asyncio.sleep(2.0)
            return "success"

        with pytest.raises(TimeoutError) as exc_info:
            await with_timeout(slow_func, seconds=0.5, name="slow_operation")

        assert "exceeded" in str(exc_info.value).lower()
        assert "slow_operation" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_timeout_with_zero(self):
        """Test timeout with zero seconds."""
        async def any_func():
            return "success"

        # Zero timeout should fail immediately
        with pytest.raises(TimeoutError):
            await with_timeout(any_func, seconds=0)

    @pytest.mark.asyncio
    async def test_timeout_doesnt_affect_errors(self):
        """Test timeout doesn't mask function errors."""
        async def failing_func():
            raise ValueError("Function error")

        # Should raise ValueError, not TimeoutError
        with pytest.raises(ValueError) as exc_info:
            await with_timeout(failing_func, seconds=1.0)

        assert "Function error" in str(exc_info.value)
