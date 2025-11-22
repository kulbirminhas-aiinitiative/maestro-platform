"""
Message broker abstraction with support for multiple messaging systems.
"""

import asyncio
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, Optional, List, Type
from maestro_core_logging import get_logger

from .adapters import (
    KafkaAdapter,
    RedisAdapter,
    RabbitMQAdapter,
    NATSAdapter
)
from .monitoring import MessagingMonitor
from .exceptions import MessagingException


class BrokerType(str, Enum):
    """Supported message broker types."""
    KAFKA = "kafka"
    REDIS = "redis"
    RABBITMQ = "rabbitmq"
    NATS = "nats"
    MEMORY = "memory"  # For testing


class BrokerAdapter(ABC):
    """Abstract base class for broker adapters."""

    @abstractmethod
    async def connect(self) -> None:
        """Connect to the message broker."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the message broker."""
        pass

    @abstractmethod
    async def publish(
        self,
        topic: str,
        message: bytes,
        headers: Optional[Dict[str, str]] = None,
        key: Optional[str] = None
    ) -> None:
        """Publish a message to a topic."""
        pass

    @abstractmethod
    async def subscribe(
        self,
        topic: str,
        group_id: Optional[str] = None,
        auto_offset_reset: str = "latest"
    ) -> Any:
        """Subscribe to a topic and return consumer."""
        pass

    @abstractmethod
    async def create_topic(
        self,
        topic: str,
        partitions: int = 1,
        replication_factor: int = 1
    ) -> None:
        """Create a topic if it doesn't exist."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check broker health."""
        pass


class MessageBroker:
    """
    Enterprise message broker with support for multiple backends.

    Features:
    - Multiple broker support (Kafka, Redis, RabbitMQ, NATS)
    - Connection pooling and failover
    - Message routing and filtering
    - Metrics and monitoring
    - Dead letter queues
    - Message deduplication
    """

    def __init__(
        self,
        broker_type: BrokerType,
        connection_string: str,
        connection_config: Optional[Dict[str, Any]] = None,
        enable_monitoring: bool = True,
        enable_dead_letter_queue: bool = True,
        max_retry_attempts: int = 3,
        retry_backoff_seconds: int = 1
    ):
        """
        Initialize message broker.

        Args:
            broker_type: Type of message broker
            connection_string: Connection string for the broker
            connection_config: Additional connection configuration
            enable_monitoring: Enable metrics and monitoring
            enable_dead_letter_queue: Enable dead letter queue
            max_retry_attempts: Maximum retry attempts for failed messages
            retry_backoff_seconds: Backoff time between retries
        """
        self.broker_type = broker_type
        self.connection_string = connection_string
        self.connection_config = connection_config or {}
        self.enable_monitoring = enable_monitoring
        self.enable_dead_letter_queue = enable_dead_letter_queue
        self.max_retry_attempts = max_retry_attempts
        self.retry_backoff_seconds = retry_backoff_seconds

        self.logger = get_logger(__name__)
        self._adapter: Optional[BrokerAdapter] = None
        self._monitor: Optional[MessagingMonitor] = None
        self._connected = False

        # Initialize adapter
        self._initialize_adapter()

        # Initialize monitoring
        if self.enable_monitoring:
            self._monitor = MessagingMonitor(broker_type=broker_type.value)

    def _initialize_adapter(self) -> None:
        """Initialize the appropriate broker adapter."""
        adapter_map: Dict[BrokerType, Type[BrokerAdapter]] = {
            BrokerType.KAFKA: KafkaAdapter,
            BrokerType.REDIS: RedisAdapter,
            BrokerType.RABBITMQ: RabbitMQAdapter,
            BrokerType.NATS: NATSAdapter,
        }

        if self.broker_type == BrokerType.MEMORY:
            from .adapters.memory import MemoryAdapter
            self._adapter = MemoryAdapter()
        else:
            adapter_class = adapter_map.get(self.broker_type)
            if not adapter_class:
                raise MessagingException(f"Unsupported broker type: {self.broker_type}")

            self._adapter = adapter_class(
                connection_string=self.connection_string,
                **self.connection_config
            )

    async def connect(self) -> None:
        """Connect to the message broker."""
        if self._connected:
            return

        try:
            self.logger.info("Connecting to message broker",
                           broker_type=self.broker_type.value,
                           connection_string=self._mask_connection_string())

            await self._adapter.connect()
            self._connected = True

            self.logger.info("Successfully connected to message broker")

            if self._monitor:
                await self._monitor.record_connection_event("connected")

        except Exception as e:
            self.logger.error("Failed to connect to message broker", error=str(e))
            if self._monitor:
                await self._monitor.record_connection_event("failed")
            raise MessagingException(f"Connection failed: {e}")

    async def disconnect(self) -> None:
        """Disconnect from the message broker."""
        if not self._connected:
            return

        try:
            self.logger.info("Disconnecting from message broker")
            await self._adapter.disconnect()
            self._connected = False

            if self._monitor:
                await self._monitor.record_connection_event("disconnected")

        except Exception as e:
            self.logger.error("Error during disconnect", error=str(e))

    async def publish(
        self,
        topic: str,
        message: bytes,
        headers: Optional[Dict[str, str]] = None,
        key: Optional[str] = None,
        retry: bool = True
    ) -> None:
        """
        Publish a message to a topic.

        Args:
            topic: Topic name
            message: Message content as bytes
            headers: Optional message headers
            key: Optional message key for partitioning
            retry: Whether to retry on failure
        """
        if not self._connected:
            await self.connect()

        attempt = 0
        last_error = None

        while attempt <= self.max_retry_attempts:
            try:
                start_time = asyncio.get_event_loop().time()

                await self._adapter.publish(
                    topic=topic,
                    message=message,
                    headers=headers,
                    key=key
                )

                # Record metrics
                if self._monitor:
                    duration = asyncio.get_event_loop().time() - start_time
                    await self._monitor.record_publish_event(
                        topic=topic,
                        size=len(message),
                        duration=duration,
                        success=True
                    )

                self.logger.debug("Message published successfully",
                                topic=topic,
                                message_size=len(message),
                                attempt=attempt)
                return

            except Exception as e:
                attempt += 1
                last_error = e

                if self._monitor:
                    await self._monitor.record_publish_event(
                        topic=topic,
                        size=len(message),
                        duration=0,
                        success=False,
                        error=str(e)
                    )

                if not retry or attempt > self.max_retry_attempts:
                    break

                self.logger.warning("Publish attempt failed, retrying",
                                  topic=topic,
                                  attempt=attempt,
                                  error=str(e))

                await asyncio.sleep(self.retry_backoff_seconds * attempt)

        # All attempts failed
        self.logger.error("Failed to publish message after all attempts",
                        topic=topic,
                        attempts=attempt,
                        error=str(last_error))

        # Send to dead letter queue if enabled
        if self.enable_dead_letter_queue:
            await self._send_to_dead_letter_queue(
                original_topic=topic,
                message=message,
                headers=headers,
                key=key,
                error=str(last_error)
            )

        raise MessagingException(f"Failed to publish message: {last_error}")

    async def subscribe(
        self,
        topic: str,
        group_id: Optional[str] = None,
        auto_offset_reset: str = "latest"
    ) -> Any:
        """
        Subscribe to a topic.

        Args:
            topic: Topic name
            group_id: Consumer group ID
            auto_offset_reset: Where to start consuming

        Returns:
            Consumer object
        """
        if not self._connected:
            await self.connect()

        try:
            consumer = await self._adapter.subscribe(
                topic=topic,
                group_id=group_id,
                auto_offset_reset=auto_offset_reset
            )

            self.logger.info("Subscribed to topic",
                           topic=topic,
                           group_id=group_id)

            if self._monitor:
                await self._monitor.record_subscription_event(topic, group_id)

            return consumer

        except Exception as e:
            self.logger.error("Failed to subscribe to topic",
                            topic=topic,
                            error=str(e))
            raise MessagingException(f"Subscription failed: {e}")

    async def create_topic(
        self,
        topic: str,
        partitions: int = 1,
        replication_factor: int = 1,
        config: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Create a topic if it doesn't exist.

        Args:
            topic: Topic name
            partitions: Number of partitions
            replication_factor: Replication factor
            config: Additional topic configuration
        """
        if not self._connected:
            await self.connect()

        try:
            await self._adapter.create_topic(
                topic=topic,
                partitions=partitions,
                replication_factor=replication_factor
            )

            self.logger.info("Topic created",
                           topic=topic,
                           partitions=partitions,
                           replication_factor=replication_factor)

        except Exception as e:
            self.logger.error("Failed to create topic",
                            topic=topic,
                            error=str(e))
            raise MessagingException(f"Topic creation failed: {e}")

    async def health_check(self) -> Dict[str, Any]:
        """Check broker health and return status."""
        if not self._connected:
            return {
                "status": "disconnected",
                "broker_type": self.broker_type.value,
                "connected": False
            }

        try:
            broker_healthy = await self._adapter.health_check()

            status = {
                "status": "healthy" if broker_healthy else "unhealthy",
                "broker_type": self.broker_type.value,
                "connected": self._connected,
                "broker_healthy": broker_healthy
            }

            if self._monitor:
                status["metrics"] = await self._monitor.get_metrics()

            return status

        except Exception as e:
            self.logger.error("Health check failed", error=str(e))
            return {
                "status": "error",
                "broker_type": self.broker_type.value,
                "connected": self._connected,
                "error": str(e)
            }

    async def _send_to_dead_letter_queue(
        self,
        original_topic: str,
        message: bytes,
        headers: Optional[Dict[str, str]] = None,
        key: Optional[str] = None,
        error: str = ""
    ) -> None:
        """Send failed message to dead letter queue."""
        dlq_topic = f"{original_topic}.dlq"
        dlq_headers = {
            "original_topic": original_topic,
            "error_reason": error,
            "timestamp": str(asyncio.get_event_loop().time())
        }
        if headers:
            dlq_headers.update(headers)

        try:
            await self._adapter.publish(
                topic=dlq_topic,
                message=message,
                headers=dlq_headers,
                key=key
            )
            self.logger.info("Message sent to dead letter queue",
                           original_topic=original_topic,
                           dlq_topic=dlq_topic)
        except Exception as e:
            self.logger.error("Failed to send message to dead letter queue",
                            error=str(e))

    def _mask_connection_string(self) -> str:
        """Mask sensitive information in connection string."""
        import re
        return re.sub(r'://([^:]+):([^@]+)@', r'://\1:***@', self.connection_string)

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()