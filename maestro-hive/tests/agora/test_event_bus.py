"""
Tests for the Event Bus implementations.

These tests verify:
- EventBus abstract interface contract
- InMemoryEventBus functionality
- Topic isolation
- Subscriber isolation
- Performance (latency < 1ms)
- Thread safety
"""

import asyncio
import pytest
import time
from typing import List, Dict, Any

from maestro_hive.agora import EventBus, InMemoryEventBus


class TestEventBusInterface:
    """Tests for EventBus abstract interface."""

    def test_cannot_instantiate_abstract_class(self):
        """EventBus is abstract and cannot be instantiated directly."""
        with pytest.raises(TypeError):
            EventBus()

    def test_interface_methods_exist(self):
        """Verify all required methods are defined."""
        assert hasattr(EventBus, "publish")
        assert hasattr(EventBus, "subscribe")
        assert hasattr(EventBus, "unsubscribe")
        assert hasattr(EventBus, "close")


class TestInMemoryEventBus:
    """Tests for InMemoryEventBus implementation."""

    @pytest.fixture
    def bus(self):
        """Create a fresh event bus for each test."""
        return InMemoryEventBus()

    @pytest.mark.asyncio
    async def test_publish_to_subscriber(self, bus):
        """Publisher sends message, subscriber receives it."""
        received: List[Dict[str, Any]] = []

        async def handler(msg):
            received.append(msg)

        await bus.subscribe("topic-a", handler)
        await bus.publish("topic-a", {"data": "hello"})

        # Allow async delivery
        await asyncio.sleep(0.01)

        assert len(received) == 1
        assert received[0]["data"] == "hello"

    @pytest.mark.asyncio
    async def test_topic_isolation(self, bus):
        """Subscriber on topic-b does NOT receive messages from topic-a."""
        received_a: List[Dict] = []
        received_b: List[Dict] = []

        async def handler_a(msg):
            received_a.append(msg)

        async def handler_b(msg):
            received_b.append(msg)

        await bus.subscribe("topic-a", handler_a)
        await bus.subscribe("topic-b", handler_b)

        await bus.publish("topic-a", {"for": "topic-a"})
        await asyncio.sleep(0.01)

        assert len(received_a) == 1
        assert len(received_b) == 0
        assert received_a[0]["for"] == "topic-a"

    @pytest.mark.asyncio
    async def test_multiple_subscribers_same_topic(self, bus):
        """Multiple subscribers on same topic all receive message."""
        received_1: List[Dict] = []
        received_2: List[Dict] = []
        received_3: List[Dict] = []

        async def handler_1(msg):
            received_1.append(msg)

        async def handler_2(msg):
            received_2.append(msg)

        async def handler_3(msg):
            received_3.append(msg)

        await bus.subscribe("shared-topic", handler_1)
        await bus.subscribe("shared-topic", handler_2)
        await bus.subscribe("shared-topic", handler_3)

        await bus.publish("shared-topic", {"broadcast": True})
        await asyncio.sleep(0.01)

        assert len(received_1) == 1
        assert len(received_2) == 1
        assert len(received_3) == 1

    @pytest.mark.asyncio
    async def test_unsubscribe(self, bus):
        """After unsubscribe, no more messages received."""
        received: List[Dict] = []

        async def handler(msg):
            received.append(msg)

        sub_id = await bus.subscribe("topic", handler)
        await bus.publish("topic", {"msg": 1})
        await asyncio.sleep(0.01)

        assert len(received) == 1

        await bus.unsubscribe(sub_id)
        await bus.publish("topic", {"msg": 2})
        await asyncio.sleep(0.01)

        # Should still be 1, no new messages
        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_unsubscribe_idempotent(self, bus):
        """Unsubscribing twice is safe (no error)."""
        async def handler(msg):
            pass

        sub_id = await bus.subscribe("topic", handler)
        await bus.unsubscribe(sub_id)
        await bus.unsubscribe(sub_id)  # Should not raise

    @pytest.mark.asyncio
    async def test_publish_no_subscribers(self, bus):
        """Publishing to topic with no subscribers does not error."""
        # Should not raise
        await bus.publish("empty-topic", {"data": "ignored"})

    @pytest.mark.asyncio
    async def test_latency_under_1ms(self, bus):
        """Message delivery latency should be < 1ms for local messages."""
        delivery_times: List[float] = []

        async def handler(msg):
            delivery_time = time.monotonic() - msg["sent_at"]
            delivery_times.append(delivery_time)

        await bus.subscribe("perf-topic", handler)

        # Send 100 messages and measure
        for _ in range(100):
            await bus.publish("perf-topic", {"sent_at": time.monotonic()})

        await asyncio.sleep(0.1)  # Allow all deliveries

        assert len(delivery_times) == 100

        avg_latency_ms = (sum(delivery_times) / len(delivery_times)) * 1000
        max_latency_ms = max(delivery_times) * 1000

        # Average should be well under 1ms
        assert avg_latency_ms < 1.0, f"Average latency {avg_latency_ms:.2f}ms exceeds 1ms"
        # Even worst case should be reasonable
        assert max_latency_ms < 10.0, f"Max latency {max_latency_ms:.2f}ms too high"

    @pytest.mark.asyncio
    async def test_handler_exception_doesnt_break_others(self, bus):
        """Exception in one handler doesn't prevent delivery to others."""
        received_good: List[Dict] = []

        async def bad_handler(msg):
            raise ValueError("I always fail!")

        async def good_handler(msg):
            received_good.append(msg)

        await bus.subscribe("topic", bad_handler)
        await bus.subscribe("topic", good_handler)

        await bus.publish("topic", {"test": True})
        await asyncio.sleep(0.01)

        # Good handler should still receive despite bad handler failing
        assert len(received_good) == 1

    @pytest.mark.asyncio
    async def test_close_prevents_operations(self, bus):
        """After close(), publish and subscribe raise errors."""
        await bus.close()

        with pytest.raises(RuntimeError):
            await bus.publish("topic", {})

        with pytest.raises(RuntimeError):
            await bus.subscribe("topic", lambda x: None)

    @pytest.mark.asyncio
    async def test_stats(self, bus):
        """Stats tracking works correctly."""
        async def handler(msg):
            pass

        initial_stats = bus.stats
        assert initial_stats["topic_count"] == 0
        assert initial_stats["subscription_count"] == 0
        assert initial_stats["messages_published"] == 0

        await bus.subscribe("topic-1", handler)
        await bus.subscribe("topic-2", handler)

        assert bus.stats["topic_count"] == 2
        assert bus.stats["subscription_count"] == 2

        await bus.publish("topic-1", {"test": True})
        await asyncio.sleep(0.01)

        assert bus.stats["messages_published"] == 1
        assert bus.stats["messages_delivered"] == 1

    @pytest.mark.asyncio
    async def test_get_subscribers_count(self, bus):
        """get_subscribers returns correct count."""
        async def handler(msg):
            pass

        assert await bus.get_subscribers("empty") == 0

        await bus.subscribe("topic", handler)
        assert await bus.get_subscribers("topic") == 1

        await bus.subscribe("topic", handler)
        assert await bus.get_subscribers("topic") == 2

    @pytest.mark.asyncio
    async def test_publish_invalid_topic_raises(self, bus):
        """Publishing with invalid topic raises ValueError."""
        with pytest.raises(ValueError):
            await bus.publish("", {"data": "test"})

        with pytest.raises(ValueError):
            await bus.publish(None, {"data": "test"})

    @pytest.mark.asyncio
    async def test_publish_invalid_message_raises(self, bus):
        """Publishing non-dict message raises ValueError."""
        with pytest.raises(ValueError):
            await bus.publish("topic", "not a dict")

        with pytest.raises(ValueError):
            await bus.publish("topic", ["list", "not", "dict"])

    @pytest.mark.asyncio
    async def test_subscribe_invalid_topic_raises(self, bus):
        """Subscribing with invalid topic raises ValueError."""
        async def handler(msg):
            pass

        with pytest.raises(ValueError):
            await bus.subscribe("", handler)

    @pytest.mark.asyncio
    async def test_subscribe_invalid_callback_raises(self, bus):
        """Subscribing with non-callable raises ValueError."""
        with pytest.raises(ValueError):
            await bus.subscribe("topic", "not callable")

    @pytest.mark.asyncio
    async def test_subscription_id_is_unique(self, bus):
        """Each subscription gets a unique ID."""
        async def handler(msg):
            pass

        ids = set()
        for _ in range(100):
            sub_id = await bus.subscribe("topic", handler)
            assert sub_id not in ids
            ids.add(sub_id)

        assert len(ids) == 100


class TestConcurrency:
    """Tests for concurrent operations."""

    @pytest.mark.asyncio
    async def test_concurrent_publishes(self):
        """Multiple concurrent publishes are handled safely."""
        bus = InMemoryEventBus()
        received: List[Dict] = []
        lock = asyncio.Lock()

        async def handler(msg):
            async with lock:
                received.append(msg)

        await bus.subscribe("concurrent", handler)

        # Publish 100 messages concurrently
        tasks = [
            bus.publish("concurrent", {"id": i})
            for i in range(100)
        ]
        await asyncio.gather(*tasks)
        await asyncio.sleep(0.1)

        assert len(received) == 100

    @pytest.mark.asyncio
    async def test_concurrent_subscribe_unsubscribe(self):
        """Concurrent subscribe/unsubscribe operations are safe."""
        bus = InMemoryEventBus()

        async def handler(msg):
            pass

        async def subscribe_task():
            sub_id = await bus.subscribe("topic", handler)
            await asyncio.sleep(0.001)
            await bus.unsubscribe(sub_id)

        # Run 50 concurrent subscribe/unsubscribe cycles
        tasks = [subscribe_task() for _ in range(50)]
        await asyncio.gather(*tasks)

        # Should end with 0 subscriptions
        assert await bus.get_subscribers("topic") == 0
