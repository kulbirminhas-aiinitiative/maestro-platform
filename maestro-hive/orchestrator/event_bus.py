"""
Event Bus for Integration Events (MD-2125)

Provides pub/sub messaging for workflow orchestration events.
Supports:
- Event types: workflow_started, phase_completed, task_created, doc_generated
- Webhook delivery to external systems
- Event persistence for replay
"""

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (
    Any, Callable, Dict, List, Optional, Set, Union
)
from threading import Lock
from queue import Queue
import httpx

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Event types emitted by the orchestrator"""
    # Workflow lifecycle
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"
    WORKFLOW_PAUSED = "workflow_paused"
    WORKFLOW_RESUMED = "workflow_resumed"

    # Phase lifecycle
    PHASE_STARTED = "phase_started"
    PHASE_COMPLETED = "phase_completed"
    PHASE_FAILED = "phase_failed"

    # Task management
    TASK_CREATED = "task_created"
    TASK_UPDATED = "task_updated"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"

    # Documentation
    DOC_GENERATED = "doc_generated"
    DOC_PUBLISHED = "doc_published"

    # Governance
    GOVERNANCE_CHECK_STARTED = "governance_check_started"
    GOVERNANCE_CHECK_PASSED = "governance_check_passed"
    GOVERNANCE_CHECK_FAILED = "governance_check_failed"

    # Checkpoints
    CHECKPOINT_CREATED = "checkpoint_created"
    CHECKPOINT_RESTORED = "checkpoint_restored"

    # Health
    HEALTH_CHECK = "health_check"
    ERROR_OCCURRED = "error_occurred"


@dataclass
class Event:
    """
    An event emitted by the orchestrator.

    Attributes:
        id: Unique event identifier
        type: Event type
        workflow_id: Associated workflow ID
        phase: Current phase (optional)
        payload: Event-specific data
        timestamp: Event timestamp
        correlation_id: For tracking related events
        metadata: Additional metadata
    """
    type: EventType
    workflow_id: str
    payload: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    phase: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'id': self.id,
            'type': self.type.value,
            'workflow_id': self.workflow_id,
            'phase': self.phase,
            'payload': self.payload,
            'timestamp': self.timestamp.isoformat(),
            'correlation_id': self.correlation_id,
            'metadata': self.metadata
        }

    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        """Create from dictionary"""
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            type=EventType(data['type']),
            workflow_id=data['workflow_id'],
            phase=data.get('phase'),
            payload=data.get('payload', {}),
            timestamp=datetime.fromisoformat(data['timestamp']) if data.get('timestamp') else datetime.utcnow(),
            correlation_id=data.get('correlation_id'),
            metadata=data.get('metadata', {})
        )


# Type alias for event handlers
EventHandler = Callable[[Event], None]
AsyncEventHandler = Callable[[Event], Any]


@dataclass
class WebhookConfig:
    """Configuration for webhook delivery"""
    url: str
    headers: Dict[str, str] = field(default_factory=dict)
    event_types: List[EventType] = field(default_factory=list)  # Empty = all events
    retry_count: int = 3
    timeout_seconds: float = 30.0
    enabled: bool = True


class EventBus:
    """
    Central event bus for workflow orchestration.

    Features:
    - Pub/sub event handling
    - Webhook delivery
    - Event persistence
    - Async support
    """

    def __init__(
        self,
        persist_events: bool = True,
        max_history: int = 10000
    ):
        """
        Initialize the event bus.

        Args:
            persist_events: Whether to persist events for replay
            max_history: Maximum events to keep in memory
        """
        self._handlers: Dict[EventType, List[EventHandler]] = {}
        self._async_handlers: Dict[EventType, List[AsyncEventHandler]] = {}
        self._global_handlers: List[EventHandler] = []
        self._webhooks: List[WebhookConfig] = []
        self._event_history: List[Event] = []
        self._persist_events = persist_events
        self._max_history = max_history
        self._lock = Lock()
        self._event_queue: Queue = Queue()
        self._paused = False

        logger.info("EventBus initialized")

    def subscribe(
        self,
        event_type: EventType,
        handler: EventHandler
    ) -> None:
        """
        Subscribe to a specific event type.

        Args:
            event_type: Event type to subscribe to
            handler: Handler function to call
        """
        with self._lock:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            self._handlers[event_type].append(handler)
            logger.debug(f"Handler subscribed to {event_type.value}")

    def subscribe_async(
        self,
        event_type: EventType,
        handler: AsyncEventHandler
    ) -> None:
        """Subscribe async handler to event type"""
        with self._lock:
            if event_type not in self._async_handlers:
                self._async_handlers[event_type] = []
            self._async_handlers[event_type].append(handler)

    def subscribe_all(self, handler: EventHandler) -> None:
        """Subscribe to all events"""
        with self._lock:
            self._global_handlers.append(handler)
            logger.debug("Global handler subscribed")

    def unsubscribe(
        self,
        event_type: EventType,
        handler: EventHandler
    ) -> bool:
        """
        Unsubscribe from an event type.

        Returns:
            True if handler was found and removed
        """
        with self._lock:
            if event_type in self._handlers:
                try:
                    self._handlers[event_type].remove(handler)
                    return True
                except ValueError:
                    pass
        return False

    def add_webhook(self, config: WebhookConfig) -> None:
        """Add a webhook for event delivery"""
        with self._lock:
            self._webhooks.append(config)
            logger.info(f"Webhook added: {config.url}")

    def remove_webhook(self, url: str) -> bool:
        """Remove a webhook by URL"""
        with self._lock:
            for i, webhook in enumerate(self._webhooks):
                if webhook.url == url:
                    self._webhooks.pop(i)
                    return True
        return False

    def emit(self, event: Event) -> None:
        """
        Emit an event synchronously.

        Args:
            event: Event to emit
        """
        if self._paused:
            self._event_queue.put(event)
            return

        self._process_event(event)

    def _process_event(self, event: Event) -> None:
        """Process an event internally"""
        # Persist event
        if self._persist_events:
            self._persist(event)

        # Call type-specific handlers
        handlers = self._handlers.get(event.type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Handler error for {event.type.value}: {e}")

        # Call global handlers
        for handler in self._global_handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Global handler error: {e}")

        # Deliver to webhooks
        self._deliver_webhooks(event)

        logger.debug(f"Event emitted: {event.type.value} ({event.id})")

    async def emit_async(self, event: Event) -> None:
        """Emit an event asynchronously"""
        if self._paused:
            self._event_queue.put(event)
            return

        # Persist event
        if self._persist_events:
            self._persist(event)

        # Call sync handlers
        handlers = self._handlers.get(event.type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Handler error: {e}")

        # Call async handlers
        async_handlers = self._async_handlers.get(event.type, [])
        if async_handlers:
            await asyncio.gather(
                *[h(event) for h in async_handlers],
                return_exceptions=True
            )

        # Deliver webhooks async
        await self._deliver_webhooks_async(event)

    def _persist(self, event: Event) -> None:
        """Persist event to history"""
        with self._lock:
            self._event_history.append(event)
            # Trim history if needed
            if len(self._event_history) > self._max_history:
                self._event_history = self._event_history[-self._max_history:]

    def _deliver_webhooks(self, event: Event) -> None:
        """Deliver event to webhooks synchronously"""
        for webhook in self._webhooks:
            if not webhook.enabled:
                continue

            # Check event type filter
            if webhook.event_types and event.type not in webhook.event_types:
                continue

            try:
                with httpx.Client(timeout=webhook.timeout_seconds) as client:
                    response = client.post(
                        webhook.url,
                        json=event.to_dict(),
                        headers={
                            'Content-Type': 'application/json',
                            **webhook.headers
                        }
                    )
                    response.raise_for_status()
                    logger.debug(f"Webhook delivered to {webhook.url}")
            except Exception as e:
                logger.error(f"Webhook delivery failed to {webhook.url}: {e}")

    async def _deliver_webhooks_async(self, event: Event) -> None:
        """Deliver event to webhooks asynchronously"""
        async with httpx.AsyncClient() as client:
            for webhook in self._webhooks:
                if not webhook.enabled:
                    continue

                if webhook.event_types and event.type not in webhook.event_types:
                    continue

                try:
                    response = await client.post(
                        webhook.url,
                        json=event.to_dict(),
                        headers={
                            'Content-Type': 'application/json',
                            **webhook.headers
                        },
                        timeout=webhook.timeout_seconds
                    )
                    response.raise_for_status()
                except Exception as e:
                    logger.error(f"Async webhook failed: {e}")

    def get_history(
        self,
        workflow_id: Optional[str] = None,
        event_type: Optional[EventType] = None,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Event]:
        """
        Get event history with optional filtering.

        Args:
            workflow_id: Filter by workflow ID
            event_type: Filter by event type
            since: Filter by timestamp
            limit: Maximum events to return

        Returns:
            List of matching events
        """
        with self._lock:
            events = self._event_history.copy()

        # Apply filters
        if workflow_id:
            events = [e for e in events if e.workflow_id == workflow_id]
        if event_type:
            events = [e for e in events if e.type == event_type]
        if since:
            events = [e for e in events if e.timestamp >= since]

        # Return most recent first, limited
        return events[-limit:][::-1]

    def replay(
        self,
        workflow_id: str,
        handlers: Optional[Dict[EventType, EventHandler]] = None
    ) -> int:
        """
        Replay events for a workflow.

        Args:
            workflow_id: Workflow to replay events for
            handlers: Optional custom handlers for replay

        Returns:
            Number of events replayed
        """
        events = self.get_history(workflow_id=workflow_id, limit=10000)
        events.reverse()  # Chronological order

        count = 0
        for event in events:
            if handlers:
                handler = handlers.get(event.type)
                if handler:
                    handler(event)
            else:
                self._process_event(event)
            count += 1

        logger.info(f"Replayed {count} events for workflow {workflow_id}")
        return count

    def pause(self) -> None:
        """Pause event processing (queue events)"""
        self._paused = True
        logger.info("EventBus paused")

    def resume(self) -> int:
        """
        Resume event processing and process queued events.

        Returns:
            Number of queued events processed
        """
        self._paused = False
        count = 0

        while not self._event_queue.empty():
            event = self._event_queue.get_nowait()
            self._process_event(event)
            count += 1

        logger.info(f"EventBus resumed, processed {count} queued events")
        return count

    def clear_history(self) -> int:
        """
        Clear event history.

        Returns:
            Number of events cleared
        """
        with self._lock:
            count = len(self._event_history)
            self._event_history.clear()
        return count

    def get_stats(self) -> Dict[str, Any]:
        """Get event bus statistics"""
        with self._lock:
            event_counts = {}
            for event in self._event_history:
                event_type = event.type.value
                event_counts[event_type] = event_counts.get(event_type, 0) + 1

            return {
                'total_events': len(self._event_history),
                'handler_count': sum(len(h) for h in self._handlers.values()),
                'global_handler_count': len(self._global_handlers),
                'webhook_count': len(self._webhooks),
                'is_paused': self._paused,
                'queued_events': self._event_queue.qsize(),
                'event_counts': event_counts
            }


# Singleton event bus instance
_default_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get the default event bus instance"""
    global _default_bus
    if _default_bus is None:
        _default_bus = EventBus()
    return _default_bus


def emit_event(
    event_type: EventType,
    workflow_id: str,
    payload: Optional[Dict[str, Any]] = None,
    phase: Optional[str] = None,
    **kwargs
) -> Event:
    """
    Convenience function to emit an event.

    Args:
        event_type: Type of event
        workflow_id: Workflow ID
        payload: Event payload
        phase: Current phase
        **kwargs: Additional event attributes

    Returns:
        The emitted event
    """
    event = Event(
        type=event_type,
        workflow_id=workflow_id,
        payload=payload or {},
        phase=phase,
        **kwargs
    )
    get_event_bus().emit(event)
    return event
