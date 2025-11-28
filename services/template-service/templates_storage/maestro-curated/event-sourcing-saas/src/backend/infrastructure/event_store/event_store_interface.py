"""Event store interface."""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional
from uuid import UUID
from ...domain.events.base_event import DomainEvent


class IEventStore(ABC):
    """Interface for event store implementations."""

    @abstractmethod
    async def save_events(
        self,
        aggregate_id: UUID,
        events: List[DomainEvent],
        expected_version: int,
        tenant_id: UUID
    ) -> None:
        """Save events to the store."""
        pass

    @abstractmethod
    async def get_events(
        self,
        aggregate_id: UUID,
        tenant_id: UUID,
        from_version: int = 0
    ) -> List[DomainEvent]:
        """Get events for an aggregate."""
        pass

    @abstractmethod
    async def get_all_events(
        self,
        tenant_id: UUID,
        from_position: int = 0,
        limit: int = 100
    ) -> List[DomainEvent]:
        """Get all events for a tenant."""
        pass

    @abstractmethod
    async def get_events_by_type(
        self,
        event_type: str,
        tenant_id: UUID,
        from_time: Optional[datetime] = None
    ) -> List[DomainEvent]:
        """Get events by type."""
        pass