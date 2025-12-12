"""
Event Bus Interface - Abstract base class for Pub/Sub messaging.

This module defines the contract for event bus implementations in the Agora.
The event bus is the "Town Square" where agents broadcast intents and
discover work opportunities without tight coupling.

Reference: docs/roadmap/AGORA_PHASE2_DETAILED_BACKLOG.md (AGORA-100)
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional, Awaitable
import logging

logger = logging.getLogger(__name__)


class EventBus(ABC):
    """
    Abstract base class for Event Bus implementations.

    The Event Bus provides a Pub/Sub mechanism for agent communication.
    Agents can:
    - publish() messages to topics (broadcast intent)
    - subscribe() to topics with callbacks (listen for work)
    - unsubscribe() when no longer interested

    This decouples agents from each other - a publisher doesn't need to
    know who (or how many) subscribers exist. This enables:
    - Dynamic team formation (Swarming)
    - Service discovery
    - Load balancing through natural competition

    Example:
        >>> bus = InMemoryEventBus()
        >>> async def handler(msg): print(f"Received: {msg}")
        >>> sub_id = await bus.subscribe("tasks.python", handler)
        >>> await bus.publish("tasks.python", {"task": "optimize algo"})
        >>> await bus.unsubscribe(sub_id)
    """

    @abstractmethod
    async def publish(self, topic: str, message: Dict[str, Any]) -> None:
        """
        Publish a message to a topic.

        All subscribers listening to this topic will receive the message
        asynchronously. The order of delivery to multiple subscribers
        is not guaranteed.

        Args:
            topic: The topic/channel name (e.g., "tasks.python", "bids.ui")
            message: The message payload as a dictionary

        Raises:
            ValueError: If topic is empty or message is not a dict

        Note:
            Publishing to a topic with no subscribers is valid - the message
            is simply discarded (fire-and-forget semantics).
        """
        pass

    @abstractmethod
    async def subscribe(
        self,
        topic: str,
        callback: Callable[[Dict[str, Any]], Awaitable[None]]
    ) -> str:
        """
        Subscribe to a topic with a callback handler.

        The callback will be invoked for every message published to the topic
        after this subscription is created. Callbacks are invoked asynchronously.

        Args:
            topic: The topic/channel name to subscribe to
            callback: Async function to handle messages. Signature:
                     async def handler(message: Dict[str, Any]) -> None

        Returns:
            subscription_id: A unique identifier for this subscription.
                            Use this ID to unsubscribe later.

        Raises:
            ValueError: If topic is empty or callback is not callable

        Example:
            >>> async def my_handler(msg):
            ...     if msg.get("budget", 0) > 100:
            ...         await submit_bid(msg)
            >>> sub_id = await bus.subscribe("tasks.frontend", my_handler)
        """
        pass

    @abstractmethod
    async def unsubscribe(self, subscription_id: str) -> None:
        """
        Unsubscribe from a topic using the subscription ID.

        After unsubscribing, the callback will no longer receive messages.
        It is safe to unsubscribe from a subscription that has already
        been removed (idempotent operation).

        Args:
            subscription_id: The ID returned from subscribe()

        Note:
            Unsubscribing while a message is being processed will not
            interrupt that processing - only future messages are affected.
        """
        pass

    async def close(self) -> None:
        """
        Close the event bus and release resources.

        Implementations should:
        - Cancel all pending deliveries
        - Remove all subscriptions
        - Release any network connections or threads

        This is a no-op in the base class but implementations should override.
        """
        pass
