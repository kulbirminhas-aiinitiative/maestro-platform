"""Tests for event store."""
import pytest
from uuid import uuid4
from datetime import datetime
from src.backend.domain.events.base_event import DomainEvent
from src.backend.infrastructure.event_store.postgresql_event_store import (
    PostgreSQLEventStore,
    ConcurrencyException
)


@pytest.fixture
async def event_store(db_pool):
    """Create event store instance."""
    return PostgreSQLEventStore(db_pool)


@pytest.fixture
def sample_event():
    """Create sample event."""
    tenant_id = uuid4()
    aggregate_id = uuid4()

    return DomainEvent(
        event_type="TestEvent",
        aggregate_id=aggregate_id,
        aggregate_type="TestAggregate",
        tenant_id=tenant_id,
        version=1,
        user_id=uuid4()
    )


@pytest.mark.asyncio
async def test_save_and_retrieve_events(event_store, sample_event):
    """Test saving and retrieving events."""
    # Save event
    await event_store.save_events(
        aggregate_id=sample_event.aggregate_id,
        events=[sample_event],
        expected_version=0,
        tenant_id=sample_event.tenant_id
    )

    # Retrieve events
    events = await event_store.get_events(
        aggregate_id=sample_event.aggregate_id,
        tenant_id=sample_event.tenant_id
    )

    assert len(events) == 1
    assert events[0].event_id == sample_event.event_id
    assert events[0].event_type == sample_event.event_type


@pytest.mark.asyncio
async def test_concurrency_check(event_store, sample_event):
    """Test optimistic concurrency control."""
    # Save first event
    await event_store.save_events(
        aggregate_id=sample_event.aggregate_id,
        events=[sample_event],
        expected_version=0,
        tenant_id=sample_event.tenant_id
    )

    # Try to save with wrong version
    with pytest.raises(ConcurrencyException):
        await event_store.save_events(
            aggregate_id=sample_event.aggregate_id,
            events=[sample_event],
            expected_version=0,  # Should be 1
            tenant_id=sample_event.tenant_id
        )


@pytest.mark.asyncio
async def test_get_events_by_type(event_store, sample_event):
    """Test retrieving events by type."""
    await event_store.save_events(
        aggregate_id=sample_event.aggregate_id,
        events=[sample_event],
        expected_version=0,
        tenant_id=sample_event.tenant_id
    )

    events = await event_store.get_events_by_type(
        event_type="TestEvent",
        tenant_id=sample_event.tenant_id
    )

    assert len(events) >= 1
    assert all(e.event_type == "TestEvent" for e in events)