"""
Unit tests for Bulkhead pattern.
"""

import pytest
import asyncio
from src.claude_team_sdk.resilience import Bulkhead, BulkheadFullError


class TestBulkhead:
    """Test bulkhead isolation pattern."""

    @pytest.mark.asyncio
    async def test_bulkhead_allows_within_limit(self):
        """Test bulkhead allows operations within limit."""
        bulkhead = Bulkhead(max_concurrent=3)

        async def simple_func(value):
            await asyncio.sleep(0.1)
            return value

        # Run 3 concurrent operations (at limit)
        results = await asyncio.gather(
            bulkhead.call(simple_func, 1),
            bulkhead.call(simple_func, 2),
            bulkhead.call(simple_func, 3),
        )

        assert results == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_bulkhead_queues_excess(self):
        """Test bulkhead queues operations beyond limit."""
        bulkhead = Bulkhead(max_concurrent=2)
        execution_order = []

        async def track_execution(value):
            execution_order.append(f"start-{value}")
            await asyncio.sleep(0.1)
            execution_order.append(f"end-{value}")
            return value

        # Start 4 operations, but only 2 can run concurrently
        results = await asyncio.gather(
            bulkhead.call(track_execution, 1),
            bulkhead.call(track_execution, 2),
            bulkhead.call(track_execution, 3),
            bulkhead.call(track_execution, 4),
        )

        assert results == [1, 2, 3, 4]

        # First 2 should start, then complete before others start
        assert execution_order[0] in ["start-1", "start-2"]
        assert execution_order[1] in ["start-1", "start-2"]

    @pytest.mark.asyncio
    async def test_bulkhead_tracking(self):
        """Test bulkhead tracks active operations."""
        bulkhead = Bulkhead(max_concurrent=2)

        async def hold_slot():
            # Check count while holding slot
            return bulkhead.active_count

        # No operations running
        assert bulkhead.active_count == 0
        assert bulkhead.available_slots == 2
        assert not bulkhead.is_full

        # Start 2 concurrent operations
        counts = await asyncio.gather(
            bulkhead.call(hold_slot),
            bulkhead.call(hold_slot),
        )

        # Each should see 1 active (itself)
        assert 1 in counts

        # After completion, count should be 0
        assert bulkhead.active_count == 0

    @pytest.mark.asyncio
    async def test_bulkhead_with_timeout(self):
        """Test bulkhead with wait timeout."""
        bulkhead = Bulkhead(max_concurrent=1, wait_timeout=0.2)

        async def hold_slot():
            await asyncio.sleep(1.0)  # Hold for 1 second
            return "done"

        # Start first operation (will hold slot)
        task1 = asyncio.create_task(bulkhead.call(hold_slot))

        # Wait a bit to ensure first operation has the slot
        await asyncio.sleep(0.05)

        # Try to get slot with short timeout - should fail
        with pytest.raises(BulkheadFullError) as exc_info:
            await bulkhead.call(hold_slot)

        assert "is full" in str(exc_info.value).lower()

        # Cancel first task to clean up
        task1.cancel()
        try:
            await task1
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_bulkhead_error_handling(self):
        """Test bulkhead releases slot on error."""
        bulkhead = Bulkhead(max_concurrent=1)

        async def failing_func():
            raise ValueError("Test error")

        # Error should still release the slot
        with pytest.raises(ValueError):
            await bulkhead.call(failing_func)

        # Slot should be available again
        assert bulkhead.active_count == 0
        assert not bulkhead.is_full
