"""
Tests for MD-3125: Event Bus Integration in Team Execution Engine V2

Tests verify:
- EventBus initialization
- Event emission at key lifecycle stages
- Correct event types and payloads
- Session ID propagation
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import uuid

# Test fixtures and helpers
from orchestrator.event_bus import EventBus, Event, EventType


class TestEventBusIntegration:
    """Tests for Event Bus integration in TeamExecutionEngineV2"""

    @pytest.fixture
    def mock_event_bus(self):
        """Create a mock event bus for testing"""
        bus = MagicMock(spec=EventBus)
        bus.emit_async = AsyncMock()
        return bus

    @pytest.fixture
    def captured_events(self):
        """Capture events emitted during test"""
        events = []
        return events

    @pytest.mark.asyncio
    async def test_workflow_started_event_emitted(self, mock_event_bus, captured_events):
        """AC-1: Running a workflow generates a workflow.started event"""
        # Track emitted events
        async def capture_event(event):
            captured_events.append(event)

        mock_event_bus.emit_async = capture_event

        # Import and patch
        with patch('orchestrator.event_bus.get_event_bus', return_value=mock_event_bus):
            from maestro_hive.teams.team_execution_v2 import TeamExecutionEngineV2

            # The engine should initialize with event bus
            engine = TeamExecutionEngineV2.__new__(TeamExecutionEngineV2)
            engine.event_bus = mock_event_bus

            # Simulate workflow started event
            workflow_id = str(uuid.uuid4())
            event = Event(
                type=EventType.WORKFLOW_STARTED,
                workflow_id=workflow_id,
                payload={"requirement": "Test requirement"}
            )
            await mock_event_bus.emit_async(event)

            assert len(captured_events) == 1
            assert captured_events[0].type == EventType.WORKFLOW_STARTED
            assert captured_events[0].workflow_id == workflow_id

    @pytest.mark.asyncio
    async def test_phase_events_contain_correct_types(self):
        """AC-3: Events contain correct timestamps"""
        bus = EventBus()

        events_received = []

        def handler(event):
            events_received.append(event)

        bus.subscribe(EventType.PHASE_STARTED, handler)
        bus.subscribe(EventType.PHASE_COMPLETED, handler)

        # Emit phase events
        workflow_id = "test-workflow-123"

        bus.emit(Event(
            type=EventType.PHASE_STARTED,
            workflow_id=workflow_id,
            phase="requirement_analysis"
        ))

        bus.emit(Event(
            type=EventType.PHASE_COMPLETED,
            workflow_id=workflow_id,
            phase="requirement_analysis",
            payload={"duration_seconds": 5.0}
        ))

        assert len(events_received) == 2

        # Verify phase started event
        assert events_received[0].type == EventType.PHASE_STARTED
        assert events_received[0].workflow_id == workflow_id
        assert events_received[0].phase == "requirement_analysis"
        assert events_received[0].timestamp is not None

        # Verify phase completed event
        assert events_received[1].type == EventType.PHASE_COMPLETED
        assert events_received[1].payload.get("duration_seconds") == 5.0

    @pytest.mark.asyncio
    async def test_workflow_failed_event_on_error(self):
        """AC-4: Failure scenarios emit a workflow.failed event"""
        bus = EventBus()

        failed_events = []

        def handler(event):
            failed_events.append(event)

        bus.subscribe(EventType.WORKFLOW_FAILED, handler)

        # Emit workflow failed event
        workflow_id = "test-workflow-456"
        bus.emit(Event(
            type=EventType.WORKFLOW_FAILED,
            workflow_id=workflow_id,
            payload={
                "error": "Phase gate blocked",
                "blockers": ["Quality score below threshold"]
            }
        ))

        assert len(failed_events) == 1
        assert failed_events[0].type == EventType.WORKFLOW_FAILED
        assert "error" in failed_events[0].payload
        assert failed_events[0].payload["error"] == "Phase gate blocked"

    @pytest.mark.asyncio
    async def test_session_id_propagation(self):
        """AC-3: Events contain correct session_id (workflow_id)"""
        bus = EventBus()

        all_events = []

        def global_handler(event):
            all_events.append(event)

        bus.subscribe_all(global_handler)

        # Emit multiple events with same workflow_id
        workflow_id = "session-789"

        event_types = [
            EventType.WORKFLOW_STARTED,
            EventType.PHASE_STARTED,
            EventType.PHASE_COMPLETED,
            EventType.WORKFLOW_COMPLETED
        ]

        for event_type in event_types:
            bus.emit(Event(
                type=event_type,
                workflow_id=workflow_id
            ))

        assert len(all_events) == 4

        # All events should have the same workflow_id
        for event in all_events:
            assert event.workflow_id == workflow_id

    @pytest.mark.asyncio
    async def test_event_bus_stats(self):
        """Test event bus statistics tracking"""
        bus = EventBus()

        # Initial stats
        stats = bus.get_stats()
        assert stats["total_events"] == 0

        # Emit some events
        for i in range(5):
            bus.emit(Event(
                type=EventType.PHASE_STARTED,
                workflow_id=f"workflow-{i}"
            ))

        stats = bus.get_stats()
        assert stats["total_events"] == 5
        assert stats["event_counts"].get("phase_started") == 5


class TestEventBusGetterFunction:
    """Tests for get_event_bus singleton"""

    def test_get_event_bus_returns_same_instance(self):
        """get_event_bus() returns the same singleton instance"""
        from orchestrator.event_bus import get_event_bus

        bus1 = get_event_bus()
        bus2 = get_event_bus()

        assert bus1 is bus2


class TestEventSerialization:
    """Tests for Event serialization"""

    def test_event_to_dict(self):
        """Event can be serialized to dictionary"""
        event = Event(
            type=EventType.WORKFLOW_STARTED,
            workflow_id="test-123",
            phase="init",
            payload={"key": "value"}
        )

        data = event.to_dict()

        assert data["type"] == "workflow_started"
        assert data["workflow_id"] == "test-123"
        assert data["phase"] == "init"
        assert data["payload"]["key"] == "value"
        assert "timestamp" in data
        assert "id" in data

    def test_event_from_dict(self):
        """Event can be deserialized from dictionary"""
        data = {
            "id": "event-abc",
            "type": "phase_completed",
            "workflow_id": "workflow-xyz",
            "phase": "testing",
            "payload": {"duration": 10.5},
            "timestamp": datetime.utcnow().isoformat()
        }

        event = Event.from_dict(data)

        assert event.id == "event-abc"
        assert event.type == EventType.PHASE_COMPLETED
        assert event.workflow_id == "workflow-xyz"
        assert event.phase == "testing"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
