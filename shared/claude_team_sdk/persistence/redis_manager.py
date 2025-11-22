"""
Redis manager for caching and pub/sub event-driven communication
"""

import asyncio
import json
from typing import Optional, Callable, Dict, Any, List
from datetime import timedelta
import redis.asyncio as redis
from redis.asyncio import Redis
from redis.asyncio.client import PubSub


class RedisManager:
    """
    Manages Redis connections for caching and pub/sub
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        decode_responses: bool = True
    ):
        """
        Initialize Redis manager

        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            password: Redis password (if required)
            decode_responses: Decode responses to strings
        """
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.decode_responses = decode_responses

        self.client: Optional[Redis] = None
        self.pubsub: Optional[PubSub] = None
        self.subscribers: Dict[str, List[Callable]] = {}
        self._listener_task: Optional[asyncio.Task] = None

    async def initialize(self):
        """Initialize Redis client"""
        self.client = await redis.Redis(
            host=self.host,
            port=self.port,
            db=self.db,
            password=self.password,
            decode_responses=self.decode_responses,
            socket_keepalive=True,
            socket_connect_timeout=5,
            retry_on_timeout=True,
        )

        # Test connection
        await self.client.ping()

        # Initialize pub/sub
        self.pubsub = self.client.pubsub()

    async def close(self):
        """Close Redis connections"""
        # Stop listener task
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass

        # Close pub/sub
        if self.pubsub:
            await self.pubsub.close()

        # Close client
        if self.client:
            await self.client.close()

    async def health_check(self) -> bool:
        """Check Redis connectivity"""
        try:
            return await self.client.ping()
        except Exception as e:
            print(f"Redis health check failed: {e}")
            return False

    # =========================================================================
    # Caching Operations
    # =========================================================================

    async def get(self, key: str) -> Optional[str]:
        """Get value from cache"""
        return await self.client.get(key)

    async def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        """Get JSON value from cache"""
        value = await self.get(key)
        return json.loads(value) if value else None

    async def set(
        self,
        key: str,
        value: str,
        expire: Optional[int] = None
    ) -> bool:
        """
        Set value in cache

        Args:
            key: Cache key
            value: Value to store
            expire: Expiration in seconds

        Returns:
            True if successful
        """
        return await self.client.set(key, value, ex=expire)

    async def set_json(
        self,
        key: str,
        value: Dict[str, Any],
        expire: Optional[int] = None
    ) -> bool:
        """Set JSON value in cache"""
        return await self.set(key, json.dumps(value), expire=expire)

    async def delete(self, *keys: str) -> int:
        """Delete keys from cache"""
        return await self.client.delete(*keys)

    async def exists(self, *keys: str) -> int:
        """Check if keys exist"""
        return await self.client.exists(*keys)

    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration on key"""
        return await self.client.expire(key, seconds)

    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment counter"""
        return await self.client.incrby(key, amount)

    # =========================================================================
    # List Operations (for queues)
    # =========================================================================

    async def lpush(self, key: str, *values: str) -> int:
        """Push to left of list"""
        return await self.client.lpush(key, *values)

    async def rpush(self, key: str, *values: str) -> int:
        """Push to right of list"""
        return await self.client.rpush(key, *values)

    async def lpop(self, key: str) -> Optional[str]:
        """Pop from left of list"""
        return await self.client.lpop(key)

    async def rpop(self, key: str) -> Optional[str]:
        """Pop from right of list"""
        return await self.client.rpop(key)

    async def lrange(self, key: str, start: int = 0, end: int = -1) -> List[str]:
        """Get range from list"""
        return await self.client.lrange(key, start, end)

    async def llen(self, key: str) -> int:
        """Get list length"""
        return await self.client.llen(key)

    # =========================================================================
    # Pub/Sub Operations for Event-Driven Communication
    # =========================================================================

    async def publish(self, channel: str, message: str) -> int:
        """
        Publish message to channel

        Args:
            channel: Channel name (e.g., "team:task.completed")
            message: Message to publish (typically JSON)

        Returns:
            Number of subscribers that received the message
        """
        return await self.client.publish(channel, message)

    async def publish_event(
        self,
        channel: str,
        event_type: str,
        data: Dict[str, Any]
    ) -> int:
        """
        Publish structured event

        Args:
            channel: Channel name
            event_type: Event type (e.g., "task.completed", "agent.status")
            data: Event data

        Returns:
            Number of subscribers
        """
        event = {
            "type": event_type,
            "data": data,
            "timestamp": asyncio.get_event_loop().time()
        }
        return await self.publish(channel, json.dumps(event))

    async def subscribe(
        self,
        channel: str,
        callback: Callable[[str, Dict[str, Any]], None]
    ):
        """
        Subscribe to channel with callback

        Args:
            channel: Channel name or pattern (e.g., "team:*")
            callback: Async function to call when message received
                      callback(channel, message_dict)
        """
        if channel not in self.subscribers:
            self.subscribers[channel] = []

        self.subscribers[channel].append(callback)

        # Subscribe to channel
        if "*" in channel or "?" in channel:
            await self.pubsub.psubscribe(channel)
        else:
            await self.pubsub.subscribe(channel)

        # Start listener if not already running
        if not self._listener_task or self._listener_task.done():
            self._listener_task = asyncio.create_task(self._message_listener())

    async def unsubscribe(self, channel: str):
        """Unsubscribe from channel"""
        if channel in self.subscribers:
            del self.subscribers[channel]

        if "*" in channel or "?" in channel:
            await self.pubsub.punsubscribe(channel)
        else:
            await self.pubsub.unsubscribe(channel)

    async def _message_listener(self):
        """Internal message listener loop"""
        try:
            async for message in self.pubsub.listen():
                if message["type"] in ("message", "pmessage"):
                    channel = message["channel"]
                    data = message["data"]

                    # Parse JSON if possible
                    try:
                        parsed_data = json.loads(data)
                    except (json.JSONDecodeError, TypeError):
                        parsed_data = {"raw": data}

                    # Call all subscribers for this channel
                    for pattern, callbacks in self.subscribers.items():
                        if self._channel_matches_pattern(channel, pattern):
                            for callback in callbacks:
                                try:
                                    if asyncio.iscoroutinefunction(callback):
                                        await callback(channel, parsed_data)
                                    else:
                                        callback(channel, parsed_data)
                                except Exception as e:
                                    print(f"Error in subscriber callback: {e}")

        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Error in message listener: {e}")

    def _channel_matches_pattern(self, channel: str, pattern: str) -> bool:
        """Check if channel matches subscription pattern"""
        if pattern == channel:
            return True

        # Simple pattern matching (* = any characters)
        if "*" in pattern:
            import re
            regex = pattern.replace("*", ".*")
            return bool(re.match(f"^{regex}$", channel))

        return False

    # =========================================================================
    # Lock Operations (for distributed coordination)
    # =========================================================================

    async def acquire_lock(
        self,
        lock_name: str,
        timeout: int = 10,
        blocking_timeout: Optional[float] = None
    ) -> bool:
        """
        Acquire distributed lock

        Args:
            lock_name: Name of the lock
            timeout: Lock expiration in seconds
            blocking_timeout: How long to wait for lock (None = don't wait)

        Returns:
            True if lock acquired
        """
        from redis.asyncio import lock
        lock_obj = lock.Lock(
            self.client,
            lock_name,
            timeout=timeout,
            blocking_timeout=blocking_timeout
        )
        return await lock_obj.acquire()

    async def release_lock(self, lock_name: str):
        """Release distributed lock"""
        from redis.asyncio import lock
        lock_obj = lock.Lock(self.client, lock_name)
        await lock_obj.release()


class RedisCacheKey:
    """Helper class for consistent cache key naming"""

    @staticmethod
    def agent_state(team_id: str, agent_id: str) -> str:
        return f"team:{team_id}:agent:{agent_id}:state"

    @staticmethod
    def task_queue(team_id: str, role: Optional[str] = None) -> str:
        if role:
            return f"team:{team_id}:tasks:queue:{role}"
        return f"team:{team_id}:tasks:queue"

    @staticmethod
    def message_cache(team_id: str, limit: int = 100) -> str:
        return f"team:{team_id}:messages:recent:{limit}"

    @staticmethod
    def workflow_status(team_id: str, workflow_id: str) -> str:
        return f"team:{team_id}:workflow:{workflow_id}:status"


class RedisEventChannel:
    """Helper class for consistent event channel naming"""

    @staticmethod
    def task_created(team_id: str) -> str:
        return f"team:{team_id}:events:task.created"

    @staticmethod
    def task_completed(team_id: str) -> str:
        return f"team:{team_id}:events:task.completed"

    @staticmethod
    def task_failed(team_id: str) -> str:
        return f"team:{team_id}:events:task.failed"

    @staticmethod
    def agent_status(team_id: str) -> str:
        return f"team:{team_id}:events:agent.status"

    @staticmethod
    def knowledge_shared(team_id: str) -> str:
        return f"team:{team_id}:events:knowledge.shared"

    @staticmethod
    def decision_proposed(team_id: str) -> str:
        return f"team:{team_id}:events:decision.proposed"

    @staticmethod
    def all_events(team_id: str) -> str:
        """Pattern to subscribe to all events"""
        return f"team:{team_id}:events:*"


# Example usage and testing
if __name__ == "__main__":
    async def test_redis():
        """Test Redis connectivity and pub/sub"""
        redis_manager = RedisManager()
        await redis_manager.initialize()

        print("✓ Redis initialized")

        # Test health check
        healthy = await redis_manager.health_check()
        print(f"✓ Health check: {'OK' if healthy else 'FAILED'}")

        # Test caching
        await redis_manager.set_json("test_key", {"foo": "bar"}, expire=60)
        value = await redis_manager.get_json("test_key")
        print(f"✓ Cache test: {value}")

        # Test pub/sub
        received_messages = []

        async def message_handler(channel: str, message: Dict[str, Any]):
            print(f"✓ Received on {channel}: {message}")
            received_messages.append(message)

        # Subscribe
        await redis_manager.subscribe("test_channel", message_handler)
        await asyncio.sleep(0.1)  # Let subscription register

        # Publish
        await redis_manager.publish_event(
            "test_channel",
            "test.event",
            {"message": "Hello from Redis!"}
        )

        # Wait for message
        await asyncio.sleep(0.5)

        assert len(received_messages) > 0, "No messages received!"
        print(f"✓ Pub/sub test passed: {len(received_messages)} messages")

        await redis_manager.close()
        print("✓ Redis closed")

    asyncio.run(test_redis())
