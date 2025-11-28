"""Projection manager for read model updates."""
import asyncio
from typing import Dict, List, Type
from abc import ABC, abstractmethod
from ...domain.events.base_event import DomainEvent


class Projection(ABC):
    """Base class for projections."""

    @abstractmethod
    async def project(self, event: DomainEvent) -> None:
        """Project an event to update read model."""
        pass

    @abstractmethod
    def handles(self) -> List[str]:
        """Return list of event types this projection handles."""
        pass


class ProjectionManager:
    """Manages projections and event routing."""

    def __init__(self):
        self._projections: Dict[str, List[Projection]] = {}

    def register(self, projection: Projection) -> None:
        """Register a projection."""
        for event_type in projection.handles():
            if event_type not in self._projections:
                self._projections[event_type] = []
            self._projections[event_type].append(projection)

    async def handle_event(self, event: DomainEvent) -> None:
        """Route event to appropriate projections."""
        event_type = event.event_type

        if event_type in self._projections:
            tasks = [
                projection.project(event)
                for projection in self._projections[event_type]
            ]
            await asyncio.gather(*tasks)

    async def handle_events(self, events: List[DomainEvent]) -> None:
        """Handle multiple events."""
        for event in events:
            await self.handle_event(event)