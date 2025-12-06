"""
Event Streaming for Execution Tracking

EPIC: MD-2558
AC-3: Real-time streaming of execution progress

Provides real-time event streaming via async generators.
"""

import asyncio
import logging
from collections import defaultdict
from datetime import datetime
from typing import AsyncIterator, Callable, Dict, List, Optional, Set
from uuid import UUID

from .models import ExecutionEvent, EventType

logger = logging.getLogger(__name__)


class StreamPublisher:
    """
    Publisher for real-time execution events (AC-3).

    Supports multiple subscribers per execution and backpressure handling.

    Usage:
        publisher = StreamPublisher(buffer_size=1000)

        # Subscribe to events
        async for event in publisher.subscribe(execution_id):
            print(f"Event: {event.event_type}")

        # Publish events
        await publisher.publish(event)
    """

    def __init__(self, buffer_size: int = 1000):
        """
        Initialize the publisher.

        Args:
            buffer_size: Maximum events to buffer per execution
        """
        self.buffer_size = buffer_size
        self._queues: Dict[UUID, List[asyncio.Queue]] = defaultdict(list)
        self._completed: Set[UUID] = set()
        self._callbacks: Dict[UUID, List[Callable[[ExecutionEvent], None]]] = defaultdict(list)
        self._lock = asyncio.Lock()

        logger.info(f"StreamPublisher initialized with buffer_size={buffer_size}")

    async def publish(self, event: ExecutionEvent) -> None:
        """
        Publish an event to all subscribers.

        Args:
            event: The event to publish
        """
        execution_id = event.execution_id

        async with self._lock:
            queues = self._queues.get(execution_id, [])

            # Publish to all subscriber queues
            for queue in queues:
                if queue.qsize() < self.buffer_size:
                    await queue.put(event)
                else:
                    logger.warning(f"Buffer full for execution {execution_id}, dropping event")

            # Call synchronous callbacks
            callbacks = self._callbacks.get(execution_id, [])
            for callback in callbacks:
                try:
                    callback(event)
                except Exception as e:
                    logger.error(f"Callback error: {e}")

        # Mark completion events
        if event.event_type in (
            EventType.EXECUTION_COMPLETED,
            EventType.EXECUTION_FAILED,
            EventType.EXECUTION_CANCELLED,
        ):
            self._completed.add(execution_id)

    async def subscribe(
        self,
        execution_id: UUID,
        event_types: Optional[List[EventType]] = None,
    ) -> AsyncIterator[ExecutionEvent]:
        """
        Subscribe to events for an execution (AC-3).

        Args:
            execution_id: The execution to subscribe to
            event_types: Optional filter for specific event types

        Yields:
            ExecutionEvents as they occur
        """
        queue: asyncio.Queue = asyncio.Queue(maxsize=self.buffer_size)

        async with self._lock:
            self._queues[execution_id].append(queue)

        try:
            while True:
                # Check if execution is complete
                if execution_id in self._completed and queue.empty():
                    break

                try:
                    # Wait for events with timeout to check completion
                    event = await asyncio.wait_for(queue.get(), timeout=1.0)

                    # Filter by event type if specified
                    if event_types and event.event_type not in event_types:
                        continue

                    yield event

                    # Stop on terminal events
                    if event.event_type in (
                        EventType.EXECUTION_COMPLETED,
                        EventType.EXECUTION_FAILED,
                        EventType.EXECUTION_CANCELLED,
                    ):
                        break

                except asyncio.TimeoutError:
                    # Check completion status periodically
                    continue

        finally:
            # Cleanup
            async with self._lock:
                if execution_id in self._queues:
                    try:
                        self._queues[execution_id].remove(queue)
                    except ValueError:
                        pass
                    if not self._queues[execution_id]:
                        del self._queues[execution_id]

    def add_callback(
        self,
        execution_id: UUID,
        callback: Callable[[ExecutionEvent], None],
    ) -> None:
        """
        Add a synchronous callback for events.

        Args:
            execution_id: The execution to receive callbacks for
            callback: Function to call with each event
        """
        self._callbacks[execution_id].append(callback)

    def remove_callback(
        self,
        execution_id: UUID,
        callback: Callable[[ExecutionEvent], None],
    ) -> None:
        """Remove a callback."""
        if execution_id in self._callbacks:
            try:
                self._callbacks[execution_id].remove(callback)
            except ValueError:
                pass

    async def wait_for_completion(
        self,
        execution_id: UUID,
        timeout: Optional[float] = None,
    ) -> bool:
        """
        Wait for an execution to complete.

        Args:
            execution_id: The execution to wait for
            timeout: Maximum time to wait in seconds

        Returns:
            True if completed, False if timeout
        """
        start = datetime.utcnow()

        while True:
            if execution_id in self._completed:
                return True

            elapsed = (datetime.utcnow() - start).total_seconds()
            if timeout and elapsed > timeout:
                return False

            await asyncio.sleep(0.1)

    def is_complete(self, execution_id: UUID) -> bool:
        """Check if an execution is complete."""
        return execution_id in self._completed

    def subscriber_count(self, execution_id: UUID) -> int:
        """Get the number of subscribers for an execution."""
        return len(self._queues.get(execution_id, []))

    async def cleanup(self, execution_id: UUID) -> None:
        """Clean up resources for a completed execution."""
        async with self._lock:
            if execution_id in self._queues:
                del self._queues[execution_id]
            if execution_id in self._callbacks:
                del self._callbacks[execution_id]
            self._completed.discard(execution_id)
