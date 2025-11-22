"""
MAESTRO Core Messaging Library

Enterprise-grade event streaming and messaging with support for multiple brokers.
Follows patterns used by companies like LinkedIn (Kafka), Netflix, and Airbnb.

Usage:
    from maestro_core_messaging import MessageBroker, EventPublisher, EventConsumer

    # Initialize message broker
    broker = MessageBroker(
        broker_type="kafka",
        connection_string="localhost:9092"
    )

    # Publish events
    publisher = EventPublisher(broker)
    await publisher.publish(
        topic="user.events",
        event={
            "event_type": "user_created",
            "user_id": 123,
            "timestamp": "2023-01-01T00:00:00Z"
        }
    )

    # Consume events
    consumer = EventConsumer(broker)

    @consumer.subscribe("user.events")
    async def handle_user_event(event):
        print(f"Received: {event}")

    await consumer.start()
"""

from .broker import MessageBroker, BrokerType
from .publisher import EventPublisher, EventPublisherConfig
from .consumer import EventConsumer, EventConsumerConfig, MessageHandler
from .event import Event, EventMetadata
from .serializers import (
    EventSerializer,
    JSONSerializer,
    AvroSerializer,
    ProtobufSerializer
)
from .adapters import (
    KafkaAdapter,
    RedisAdapter,
    RabbitMQAdapter,
    NATSAdapter
)
from .patterns import (
    EventSourcing,
    CQRS,
    Saga,
    OutboxPattern
)
from .monitoring import MessagingMonitor
from .exceptions import (
    MessagingException,
    PublishException,
    ConsumeException,
    SerializationException
)

__version__ = "1.0.0"
__all__ = [
    # Core classes
    "MessageBroker",
    "BrokerType",
    "EventPublisher",
    "EventPublisherConfig",
    "EventConsumer",
    "EventConsumerConfig",
    "MessageHandler",

    # Event models
    "Event",
    "EventMetadata",

    # Serialization
    "EventSerializer",
    "JSONSerializer",
    "AvroSerializer",
    "ProtobufSerializer",

    # Broker adapters
    "KafkaAdapter",
    "RedisAdapter",
    "RabbitMQAdapter",
    "NATSAdapter",

    # Messaging patterns
    "EventSourcing",
    "CQRS",
    "Saga",
    "OutboxPattern",

    # Monitoring
    "MessagingMonitor",

    # Exceptions
    "MessagingException",
    "PublishException",
    "ConsumeException",
    "SerializationException",
]