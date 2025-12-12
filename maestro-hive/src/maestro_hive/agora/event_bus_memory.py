"""
In-Memory Event Bus Implementation.

This module provides a thread-safe, async-safe in-memory implementation
of the EventBus interface for local development and testing.

Reference: docs/roadmap/AGORA_PHASE2_DETAILED_BACKLOG.md (AGORA-101)
"""

import asyncio
import logging
import time
import uuid
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional, Awaitable
import threading

from .event_bus import EventBus

logger = logging.getLogger(__name__)


class Subscription:
    """Represents an active subscription."""

    __slots__ = ("id", "topic", "callback", "created_at")

    def __init__(
        self,
        subscription_id: str,
        topic: str,
        callback: Callable[[Dict[str, Any]], Awaitable[None]]
    ):
        self.id = subscription_id
        self.topic = topic
        self.callback = callback
        self.created_at = time.monotonic()


class InMemoryEventBus(EventBus):
    """
    Thread-safe, async-safe in-memory Event Bus implementation.

    This implementation uses asyncio for message delivery and provides:
    - Topic-based routing with dictionary of subscription lists
    - Concurrent message delivery to multiple subscribers
    - Thread-safety via asyncio locks
    - Sub-millisecond local message latency

    Use Cases:
    - Local development without external message brokers
    - Unit testing with isolated message passing
    - CI/CD pipeline execution
    - Single-process agent orchestration

    Thread Safety:
        All operations are protected by an asyncio.Lock to ensure
        safe access from multiple coroutines. The implementation is
        designed for use within an asyncio event loop.

    Performance:
        Local message latency is typically < 1ms for simple handlers.
        Messages are delivered concurrently using asyncio.gather().

    Example:
        >>> bus = InMemoryEventBus()
        >>> received = []
        >>> async def handler(msg):
        ...     received.append(msg)
        >>> sub_id = await bus.subscribe("test.topic", handler)
        >>> await bus.publish("test.topic", {"data": "hello"})
        >>> await asyncio.sleep(0.001)  # Allow delivery
        >>> assert received == [{"data": "hello"}]
    """

    def __init__(self):
        """Initialize the in-memory event bus."""
        # Topic -> List of Subscription objects
        self._subscriptions: Dict[str, List[Subscription]] = defaultdict(list)
        # subscription_id -> Subscription for O(1) lookup on unsubscribe
        self._subscription_index: Dict[str, Subscription] = {}
        # Lock for thread-safe modifications
        self._lock = asyncio.Lock()
        # Metrics
        self._messages_published = 0
        self._messages_delivered = 0
        self._closed = False

        logger.debug("InMemoryEventBus initialized")

    async def publish(self, topic: str, message: Dict[str, Any]) -> None:
        """
        Publish a message to a topic.

        Messages are delivered concurrently to all subscribers.
        Delivery failures in one subscriber do not affect others.

        Args:
            topic: The topic to publish to
            message: The message payload

        Raises:
            ValueError: If topic is empty or message is not a dict
            RuntimeError: If the event bus has been closed
        """
        if self._closed:
            raise RuntimeError("Event bus has been closed")

        if not topic or not isinstance(topic, str):
            raise ValueError("Topic must be a non-empty string")

        if not isinstance(message, dict):
            raise ValueError("Message must be a dictionary")

        start_time = time.monotonic()

        async with self._lock:
            subscribers = list(self._subscriptions.get(topic, []))

        if not subscribers:
            logger.debug(f"No subscribers for topic '{topic}', message discarded")
            return

        self._messages_published += 1

        # Deliver to all subscribers concurrently
        delivery_tasks = []
        for subscription in subscribers:
            task = asyncio.create_task(
                self._safe_deliver(subscription, message)
            )
            delivery_tasks.append(task)

        # Wait for all deliveries (with error handling per subscriber)
        await asyncio.gather(*delivery_tasks, return_exceptions=True)

        elapsed_ms = (time.monotonic() - start_time) * 1000
        logger.debug(
            f"Published to '{topic}': {len(subscribers)} subscribers, "
            f"{elapsed_ms:.2f}ms"
        )

    async def _safe_deliver(
        self,
        subscription: Subscription,
        message: Dict[str, Any]
    ) -> None:
        """
        Safely deliver a message to a subscriber.

        Catches and logs any exceptions to prevent one failing subscriber
        from affecting others.
        """
        try:
            await subscription.callback(message)
            self._messages_delivered += 1
        except Exception as e:
            logger.error(
                f"Error delivering to subscriber {subscription.id} "
                f"on topic '{subscription.topic}': {e}"
            )

    async def subscribe(
        self,
        topic: str,
        callback: Callable[[Dict[str, Any]], Awaitable[None]]
    ) -> str:
        """
        Subscribe to a topic with a callback handler.

        Args:
            topic: The topic to subscribe to
            callback: Async function to handle messages

        Returns:
            Unique subscription ID

        Raises:
            ValueError: If topic is empty or callback is not callable
            RuntimeError: If the event bus has been closed
        """
        if self._closed:
            raise RuntimeError("Event bus has been closed")

        if not topic or not isinstance(topic, str):
            raise ValueError("Topic must be a non-empty string")

        if not callable(callback):
            raise ValueError("Callback must be callable")

        subscription_id = f"sub_{uuid.uuid4().hex[:12]}"
        subscription = Subscription(subscription_id, topic, callback)

        async with self._lock:
            self._subscriptions[topic].append(subscription)
            self._subscription_index[subscription_id] = subscription

        logger.debug(f"Subscribed to '{topic}' with ID {subscription_id}")
        return subscription_id

    async def unsubscribe(self, subscription_id: str) -> None:
        """
        Unsubscribe using the subscription ID.

        This is idempotent - unsubscribing a non-existent ID is a no-op.

        Args:
            subscription_id: The ID returned from subscribe()
        """
        async with self._lock:
            subscription = self._subscription_index.pop(subscription_id, None)

            if subscription is None:
                logger.debug(f"Subscription {subscription_id} not found (already removed?)")
                return

            topic_subs = self._subscriptions.get(subscription.topic, [])
            self._subscriptions[subscription.topic] = [
                s for s in topic_subs if s.id != subscription_id
            ]

            # Clean up empty topic lists
            if not self._subscriptions[subscription.topic]:
                del self._subscriptions[subscription.topic]

        logger.debug(f"Unsubscribed {subscription_id} from '{subscription.topic}'")

    async def close(self) -> None:
        """
        Close the event bus and remove all subscriptions.

        After closing, publish and subscribe operations will raise RuntimeError.
        """
        async with self._lock:
            self._closed = True
            self._subscriptions.clear()
            self._subscription_index.clear()

        logger.info(
            f"InMemoryEventBus closed. Stats: "
            f"published={self._messages_published}, "
            f"delivered={self._messages_delivered}"
        )

    @property
    def stats(self) -> Dict[str, Any]:
        """
        Get event bus statistics.

        Returns:
            Dictionary with:
            - topic_count: Number of topics with active subscriptions
            - subscription_count: Total number of active subscriptions
            - messages_published: Total messages published
            - messages_delivered: Total successful deliveries
        """
        return {
            "topic_count": len(self._subscriptions),
            "subscription_count": len(self._subscription_index),
            "messages_published": self._messages_published,
            "messages_delivered": self._messages_delivered,
            "closed": self._closed,
        }

    async def get_subscribers(self, topic: str) -> int:
        """
        Get the number of subscribers for a topic.

        Args:
            topic: The topic to check

        Returns:
            Number of active subscribers
        """
        async with self._lock:
            return len(self._subscriptions.get(topic, []))
