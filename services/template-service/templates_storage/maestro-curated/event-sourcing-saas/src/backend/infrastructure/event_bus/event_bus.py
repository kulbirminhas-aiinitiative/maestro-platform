"""Event bus for publishing and subscribing to domain events."""
import asyncio
from typing import Callable, Dict, List
from ...domain.events.base_event import DomainEvent


EventHandler = Callable[[DomainEvent], None]


class EventBus:
    """Event bus for domain event distribution."""

    def __init__(self):
        self._subscribers: Dict[str, List[EventHandler]] = {}

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Subscribe to an event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    async def publish(self, event: DomainEvent) -> None:
        """Publish an event to all subscribers."""
        event_type = event.event_type

        if event_type in self._subscribers:
            tasks = [
                self._handle_event(handler, event)
                for handler in self._subscribers[event_type]
            ]
            await asyncio.gather(*tasks, return_exceptions=True)

    async def publish_many(self, events: List[DomainEvent]) -> None:
        """Publish multiple events."""
        for event in events:
            await self.publish(event)

    async def _handle_event(self, handler: EventHandler, event: DomainEvent) -> None:
        """Handle event with error catching."""
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(event)
            else:
                handler(event)
        except Exception as e:
            # Log error but don't fail the publish
            print(f"Error in event handler: {e}")