"""PostgreSQL-based event store implementation."""
import json
from datetime import datetime
from typing import List, Optional
from uuid import UUID
import asyncpg
from asyncpg.pool import Pool
from ...domain.events.base_event import DomainEvent
from .event_store_interface import IEventStore


class PostgreSQLEventStore(IEventStore):
    """Event store implementation using PostgreSQL."""

    def __init__(self, pool: Pool):
        self.pool = pool

    async def save_events(
        self,
        aggregate_id: UUID,
        events: List[DomainEvent],
        expected_version: int,
        tenant_id: UUID
    ) -> None:
        """Save events to the event store with optimistic concurrency control."""
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # Check version for optimistic concurrency
                current_version = await conn.fetchval(
                    """
                    SELECT COALESCE(MAX(version), 0)
                    FROM events
                    WHERE aggregate_id = $1 AND tenant_id = $2
                    """,
                    aggregate_id,
                    tenant_id
                )

                if current_version != expected_version:
                    raise ConcurrencyException(
                        f"Expected version {expected_version} but found {current_version}"
                    )

                # Insert events
                for event in events:
                    await conn.execute(
                        """
                        INSERT INTO events (
                            event_id, event_type, aggregate_id, aggregate_type,
                            tenant_id, occurred_at, version, user_id, data, metadata
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                        """,
                        event.event_id,
                        event.event_type,
                        event.aggregate_id,
                        event.aggregate_type,
                        event.tenant_id,
                        event.occurred_at,
                        event.version,
                        event.user_id,
                        json.dumps(event.dict()),
                        json.dumps(event.metadata)
                    )

    async def get_events(
        self,
        aggregate_id: UUID,
        tenant_id: UUID,
        from_version: int = 0
    ) -> List[DomainEvent]:
        """Retrieve events for an aggregate."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT data
                FROM events
                WHERE aggregate_id = $1 AND tenant_id = $2 AND version > $3
                ORDER BY version ASC
                """,
                aggregate_id,
                tenant_id,
                from_version
            )

            return [self._deserialize_event(row['data']) for row in rows]

    async def get_all_events(
        self,
        tenant_id: UUID,
        from_position: int = 0,
        limit: int = 100
    ) -> List[DomainEvent]:
        """Retrieve all events for a tenant from a position."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT data
                FROM events
                WHERE tenant_id = $1 AND position > $2
                ORDER BY position ASC
                LIMIT $3
                """,
                tenant_id,
                from_position,
                limit
            )

            return [self._deserialize_event(row['data']) for row in rows]

    async def get_events_by_type(
        self,
        event_type: str,
        tenant_id: UUID,
        from_time: Optional[datetime] = None
    ) -> List[DomainEvent]:
        """Retrieve events of a specific type."""
        async with self.pool.acquire() as conn:
            if from_time:
                rows = await conn.fetch(
                    """
                    SELECT data
                    FROM events
                    WHERE event_type = $1 AND tenant_id = $2 AND occurred_at >= $3
                    ORDER BY occurred_at ASC
                    """,
                    event_type,
                    tenant_id,
                    from_time
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT data
                    FROM events
                    WHERE event_type = $1 AND tenant_id = $2
                    ORDER BY occurred_at ASC
                    """,
                    event_type,
                    tenant_id
                )

            return [self._deserialize_event(row['data']) for row in rows]

    def _deserialize_event(self, data: str) -> DomainEvent:
        """Deserialize event from JSON."""
        event_dict = json.loads(data) if isinstance(data, str) else data
        return DomainEvent(**event_dict)


class ConcurrencyException(Exception):
    """Exception raised when optimistic concurrency check fails."""
    pass