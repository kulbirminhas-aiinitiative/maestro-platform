"""
Unit tests for Retry pattern.
"""

import pytest
import asyncio
from src.claude_team_sdk.resilience import retry_with_backoff, RetryError


class TestRetryWithBackoff:
    """Test retry with exponential backoff."""

    @pytest.mark.asyncio
    async def test_successful_first_attempt(self):
        """Test function succeeds on first attempt."""
        call_count = 0

        async def success_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await retry_with_backoff(success_func, max_retries=3)
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_succeeds_on_second_attempt(self):
        """Test function succeeds on second attempt after one failure."""
        call_count = 0

        async def sometimes_fails():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("First attempt fails")
            return "success"

        result = await retry_with_backoff(
            sometimes_fails,
            max_retries=3,
            initial_delay=0.1  # Fast for testing
        )

        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_exhausted(self):
        """Test all retries are exhausted."""
        call_count = 0

        async def always_fails():
            nonlocal call_count
            call_count += 1
            raise ValueError(f"Failure {call_count}")

        with pytest.raises(RetryError) as exc_info:
            await retry_with_backoff(
                always_fails,
                max_retries=3,
                initial_delay=0.1
            )

        assert call_count == 4  # 1 initial + 3 retries
        assert "failed after" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self):
        """Test exponential backoff delay increases."""
        call_times = []

        async def track_time():
            call_times.append(asyncio.get_event_loop().time())
            raise ValueError("Test error")

        try:
            await retry_with_backoff(
                track_time,
                max_retries=2,
                initial_delay=0.1,
                backoff_factor=2.0
            )
        except RetryError:
            pass

        # Should have 3 calls (initial + 2 retries)
        assert len(call_times) == 3

        # Check delays (approximately)
        # First retry: ~0.1s after initial
        # Second retry: ~0.2s after first retry
        if len(call_times) >= 3:
            delay1 = call_times[1] - call_times[0]
            delay2 = call_times[2] - call_times[1]

            assert 0.08 < delay1 < 0.15  # ~0.1s with some tolerance
            assert 0.18 < delay2 < 0.25  # ~0.2s with some tolerance

    @pytest.mark.asyncio
    async def test_max_delay_cap(self):
        """Test max delay caps the backoff."""
        call_times = []

        async def track_time():
            call_times.append(asyncio.get_event_loop().time())
            raise ValueError("Test error")

        try:
            await retry_with_backoff(
                track_time,
                max_retries=3,
                initial_delay=1.0,
                backoff_factor=10.0,  # Would be 10s, 100s without cap
                max_delay=0.5  # Cap at 0.5s
            )
        except RetryError:
            pass

        # All delays should be capped at max_delay
        if len(call_times) >= 3:
            for i in range(1, len(call_times)):
                delay = call_times[i] - call_times[i-1]
                assert delay <= 0.6  # Max 0.5s + tolerance

    @pytest.mark.asyncio
    async def test_retryable_exceptions(self):
        """Test only retryable exceptions are retried."""
        call_count = 0

        async def raises_non_retryable():
            nonlocal call_count
            call_count += 1
            raise RuntimeError("Non-retryable error")

        # RuntimeError is not in retryable_exceptions
        with pytest.raises(RuntimeError):
            await retry_with_backoff(
                raises_non_retryable,
                max_retries=3,
                retryable_exceptions=(ValueError, ConnectionError)
            )

        # Should not retry
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_custom_name_in_logs(self):
        """Test custom name is used in retry logic."""
        async def failing_func():
            raise ValueError("Test")

        # Just verify it doesn't crash with custom name
        try:
            await retry_with_backoff(
                failing_func,
                max_retries=1,
                initial_delay=0.01,
                name="custom_operation"
            )
        except RetryError as e:
            assert "custom_operation" in str(e)
