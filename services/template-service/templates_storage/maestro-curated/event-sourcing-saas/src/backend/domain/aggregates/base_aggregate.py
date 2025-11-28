"""Base aggregate root for event sourcing."""
from typing import List, Type
from uuid import UUID
from abc import ABC, abstractmethod
from ..events.base_event import DomainEvent


class AggregateRoot(ABC):
    """Base class for aggregate roots in event sourcing."""

    def __init__(self, aggregate_id: UUID, tenant_id: UUID):
        self.aggregate_id = aggregate_id
        self.tenant_id = tenant_id
        self.version = 0
        self._uncommitted_events: List[DomainEvent] = []

    def apply_event(self, event: DomainEvent, is_new: bool = True) -> None:
        """Apply an event to the aggregate."""
        self._apply(event)
        if is_new:
            self._uncommitted_events.append(event)
            self.version += 1

    @abstractmethod
    def _apply(self, event: DomainEvent) -> None:
        """Apply event to update aggregate state. Must be implemented by subclasses."""
        pass

    def get_uncommitted_events(self) -> List[DomainEvent]:
        """Get list of uncommitted events."""
        return self._uncommitted_events.copy()

    def mark_events_as_committed(self) -> None:
        """Clear uncommitted events after persistence."""
        self._uncommitted_events.clear()

    def load_from_history(self, events: List[DomainEvent]) -> None:
        """Reconstruct aggregate from event history."""
        for event in events:
            self._apply(event)
            self.version = event.version

    @property
    def aggregate_type(self) -> str:
        """Return the aggregate type name."""
        return self.__class__.__name__