"""
Event Bus - Redis-based pub/sub for decision events.

Provides the communication layer between maestro-hive (execution)
and maestro-backend (integration/learning).
"""
from abc import ABC, abstractmethod
from typing import Callable, List, Optional
import json
import logging

from .decision_events import DecisionEvent


logger = logging.getLogger(__name__)


class EventBusInterface(ABC):
    """Abstract interface for event bus implementations."""
    
    @abstractmethod
    async def publish(self, channel: str, event: DecisionEvent) -> bool:
        """Publish a decision event to a channel."""
        pass
    
    @abstractmethod
    async def subscribe(
        self, 
        channel: str, 
        handler: Callable[[DecisionEvent], None]
    ) -> None:
        """Subscribe to events on a channel."""
        pass
    
    @abstractmethod
    async def unsubscribe(self, channel: str) -> None:
        """Unsubscribe from a channel."""
        pass


class RedisEventBus(EventBusInterface):
    """
    Redis-based event bus implementation.
    
    Uses Redis pub/sub for real-time event distribution.
    """
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        channel_prefix: str = "maestro:visibility:",
    ):
        self._redis_url = redis_url
        self._channel_prefix = channel_prefix
        self._redis = None  # Lazy initialization
        self._subscriptions: dict = {}
        
    async def _get_redis(self):
        """Get or create Redis connection."""
        if self._redis is None:
            try:
                import redis.asyncio as aioredis
                self._redis = await aioredis.from_url(self._redis_url)
            except ImportError:
                logger.warning("redis.asyncio not available, using mock")
                self._redis = MockRedis()
        return self._redis
    
    async def publish(self, channel: str, event: DecisionEvent) -> bool:
        """Publish a decision event to Redis channel."""
        try:
            redis = await self._get_redis()
            full_channel = f"{self._channel_prefix}{channel}"
            
            # Serialize event
            payload = json.dumps({
                "epic_id": event.epic_id,
                "decision_id": str(event.decision_id),
                "persona": event.persona,
                "decision_type": event.decision_type,
                "description": event.description,
                "rationale": event.rationale,
                "artifacts": event.artifacts,
                "timestamp": event.timestamp.isoformat(),
                "verbosity_level": event.verbosity_level.value,
                "metadata": event.metadata,
            })
            
            await redis.publish(full_channel, payload)
            logger.debug(f"Published event to {full_channel}: {event.decision_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
            return False
    
    async def subscribe(
        self,
        channel: str,
        handler: Callable[[DecisionEvent], None]
    ) -> None:
        """Subscribe to events on a channel."""
        redis = await self._get_redis()
        full_channel = f"{self._channel_prefix}{channel}"
        
        pubsub = redis.pubsub()
        await pubsub.subscribe(full_channel)
        
        self._subscriptions[channel] = pubsub
        logger.info(f"Subscribed to {full_channel}")
    
    async def unsubscribe(self, channel: str) -> None:
        """Unsubscribe from a channel."""
        if channel in self._subscriptions:
            pubsub = self._subscriptions[channel]
            await pubsub.unsubscribe()
            del self._subscriptions[channel]
            logger.info(f"Unsubscribed from {channel}")


class MockRedis:
    """Mock Redis for testing without Redis server."""
    
    async def publish(self, channel: str, message: str) -> int:
        logger.debug(f"MockRedis publish: {channel}")
        return 1
    
    def pubsub(self):
        return MockPubSub()


class MockPubSub:
    """Mock PubSub for testing."""
    
    async def subscribe(self, channel: str) -> None:
        pass
    
    async def unsubscribe(self) -> None:
        pass
