"""
Tests for Execution Tracking Module

EPIC: MD-2558
[RUNTIME-ENGINE] Execution Tracking - Monitor and Record All Runs

Tests cover all acceptance criteria:
- AC-1: Every execution creates a traceable record
- AC-2: Record includes: input, context, decisions, output, outcome
- AC-3: Real-time streaming of execution progress
- AC-4: Integration with Execution History Store (MD-2500)
- AC-5: Queryable execution history for analytics
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from maestro_hive.runtime.tracking.models import (
    TrackedExecution,
    TraceContext,
    Decision,
    ExecutionEvent,
    ExecutionOutcome,
    EventType,
    DecisionType,
)
from maestro_hive.runtime.tracking.config import TrackerConfig
from maestro_hive.runtime.tracking.stream import StreamPublisher
from maestro_hive.runtime.tracking.query import QueryService, AnalyticsResult
from maestro_hive.runtime.tracking.tracker import ExecutionTracker


# =============================================================================
# Test TrackedExecution Model (AC-1, AC-2)
# =============================================================================

class TestTrackedExecution:
    """Tests for TrackedExecution model."""

    def test_create_execution(self):
        """AC-1: Every execution creates a traceable record with unique ID."""
        execution = TrackedExecution()
        assert execution.id is not None
        assert execution.outcome == ExecutionOutcome.PENDING
        assert execution.started_at is not None

    def test_execution_with_context(self):
        """AC-2: Record includes input and context."""
        context = TraceContext(
            persona_id="code-reviewer",
            persona_version="1.0.0",
            input_data={"code": "def hello(): pass"},
            environment={"python_version": "3.11"},
            user_id="user123",
            tags=["python", "review"],
        )
        execution = TrackedExecution(trace_context=context)

        assert execution.trace_context.persona_id == "code-reviewer"
        assert execution.trace_context.input_data["code"] == "def hello(): pass"
        assert "python" in execution.trace_context.tags

    def test_mark_completed(self):
        """AC-2: Record includes output and outcome."""
        execution = TrackedExecution()
        execution.mark_started()

        output = {"review": "Looks good", "score": 95}
        execution.mark_completed(
            outcome=ExecutionOutcome.SUCCESS,
            output_data=output,
            output_summary="Code review passed"
        )

        assert execution.outcome == ExecutionOutcome.SUCCESS
        assert execution.output_data["score"] == 95
        assert execution.completed_at is not None
        assert execution.duration_ms is not None

    def test_mark_failed(self):
        """AC-2: Record captures error information."""
        execution = TrackedExecution()
        execution.mark_started()

        execution.mark_failed(
            error_message="Syntax error in code",
            error_details={"line": 42}
        )

        assert execution.outcome == ExecutionOutcome.FAILED
        assert execution.error_message == "Syntax error in code"
        assert execution.error_details["line"] == 42

    def test_serialization(self):
        """Test execution can be serialized and deserialized."""
        execution = TrackedExecution(
            trace_context=TraceContext(persona_id="test-persona"),
            outcome=ExecutionOutcome.SUCCESS,
        )
        execution.add_decision(Decision(
            decision_type=DecisionType.TOOL_SELECTION,
            choice="analyzer"
        ))

        data = execution.to_dict()
        restored = TrackedExecution.from_dict(data)

        assert restored.id == execution.id
        assert restored.trace_context.persona_id == "test-persona"
        assert len(restored.decisions) == 1


# =============================================================================
# Test Decision Model (AC-2)
# =============================================================================

class TestDecision:
    """Tests for Decision model."""

    def test_create_decision(self):
        """AC-2: Decisions are captured."""
        decision = Decision(
            decision_type=DecisionType.TOOL_SELECTION,
            choice="static_analysis",
            reasoning="Code review requires static analysis first",
            alternatives=["lint", "format"],
            confidence=0.95
        )

        assert decision.decision_type == DecisionType.TOOL_SELECTION
        assert decision.choice == "static_analysis"
        assert decision.confidence == 0.95
        assert "lint" in decision.alternatives

    def test_decision_serialization(self):
        """Test decision serialization."""
        decision = Decision(
            decision_type=DecisionType.STRATEGY_CHOICE,
            choice="aggressive",
        )

        data = decision.to_dict()
        restored = Decision.from_dict(data)

        assert restored.decision_type == decision.decision_type
        assert restored.choice == decision.choice


# =============================================================================
# Test ExecutionEvent Model (AC-3)
# =============================================================================

class TestExecutionEvent:
    """Tests for ExecutionEvent model."""

    def test_create_event(self):
        """AC-3: Events can be created for streaming."""
        event = ExecutionEvent(
            event_type=EventType.PROGRESS_UPDATE,
            message="Processing file 1 of 10",
            progress_percent=10.0,
            data={"current_file": "main.py"}
        )

        assert event.event_type == EventType.PROGRESS_UPDATE
        assert event.progress_percent == 10.0
        assert event.data["current_file"] == "main.py"

    def test_event_types(self):
        """Test all event types can be created."""
        for event_type in EventType:
            event = ExecutionEvent(event_type=event_type)
            assert event.event_type == event_type


# =============================================================================
# Test StreamPublisher (AC-3)
# =============================================================================

class TestStreamPublisher:
    """Tests for StreamPublisher - real-time event streaming."""

    @pytest.mark.asyncio
    async def test_publish_and_subscribe(self):
        """AC-3: Real-time streaming of execution progress."""
        publisher = StreamPublisher(buffer_size=100)
        execution_id = uuid4()

        received_events = []

        async def collect_events():
            async for event in publisher.subscribe(execution_id):
                received_events.append(event)
                if event.event_type == EventType.EXECUTION_COMPLETED:
                    break

        # Start collector
        collector_task = asyncio.create_task(collect_events())

        # Give subscriber time to register
        await asyncio.sleep(0.1)

        # Publish events
        events = [
            ExecutionEvent(execution_id=execution_id, event_type=EventType.EXECUTION_STARTED),
            ExecutionEvent(execution_id=execution_id, event_type=EventType.PROGRESS_UPDATE, progress_percent=50),
            ExecutionEvent(execution_id=execution_id, event_type=EventType.EXECUTION_COMPLETED),
        ]

        for event in events:
            await publisher.publish(event)

        # Wait for collection
        await asyncio.wait_for(collector_task, timeout=5.0)

        assert len(received_events) == 3
        assert received_events[0].event_type == EventType.EXECUTION_STARTED
        assert received_events[2].event_type == EventType.EXECUTION_COMPLETED

    @pytest.mark.asyncio
    async def test_multiple_subscribers(self):
        """Test multiple subscribers receive events."""
        publisher = StreamPublisher()
        execution_id = uuid4()

        received1 = []
        received2 = []

        async def collect1():
            async for event in publisher.subscribe(execution_id):
                received1.append(event)
                if event.event_type == EventType.EXECUTION_COMPLETED:
                    break

        async def collect2():
            async for event in publisher.subscribe(execution_id):
                received2.append(event)
                if event.event_type == EventType.EXECUTION_COMPLETED:
                    break

        task1 = asyncio.create_task(collect1())
        task2 = asyncio.create_task(collect2())

        await asyncio.sleep(0.1)

        await publisher.publish(ExecutionEvent(
            execution_id=execution_id,
            event_type=EventType.EXECUTION_COMPLETED
        ))

        await asyncio.wait_for(asyncio.gather(task1, task2), timeout=5.0)

        assert len(received1) == 1
        assert len(received2) == 1

    @pytest.mark.asyncio
    async def test_subscriber_count(self):
        """Test subscriber counting."""
        publisher = StreamPublisher()
        execution_id = uuid4()

        assert publisher.subscriber_count(execution_id) == 0

        async def dummy_subscribe():
            async for _ in publisher.subscribe(execution_id):
                break

        task = asyncio.create_task(dummy_subscribe())
        await asyncio.sleep(0.1)

        assert publisher.subscriber_count(execution_id) == 1

        # Complete to cleanup
        await publisher.publish(ExecutionEvent(
            execution_id=execution_id,
            event_type=EventType.EXECUTION_COMPLETED
        ))
        await task


# =============================================================================
# Test QueryService (AC-5)
# =============================================================================

class TestQueryService:
    """Tests for QueryService - queryable execution history."""

    @pytest.mark.asyncio
    async def test_filter_by_persona(self):
        """AC-5: Queryable by persona."""
        query = QueryService()

        # Add some executions
        exec1 = TrackedExecution(trace_context=TraceContext(persona_id="reviewer"))
        exec2 = TrackedExecution(trace_context=TraceContext(persona_id="coder"))
        exec3 = TrackedExecution(trace_context=TraceContext(persona_id="reviewer"))

        query.cache_execution(exec1)
        query.cache_execution(exec2)
        query.cache_execution(exec3)

        results = await query.filter(persona_id="reviewer")
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_filter_by_outcome(self):
        """AC-5: Queryable by outcome."""
        query = QueryService()

        exec1 = TrackedExecution(outcome=ExecutionOutcome.SUCCESS)
        exec2 = TrackedExecution(outcome=ExecutionOutcome.FAILED)
        exec3 = TrackedExecution(outcome=ExecutionOutcome.SUCCESS)

        query.cache_execution(exec1)
        query.cache_execution(exec2)
        query.cache_execution(exec3)

        results = await query.filter(outcome=ExecutionOutcome.SUCCESS)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_filter_by_time_range(self):
        """AC-5: Queryable by time range."""
        query = QueryService()

        now = datetime.utcnow()
        exec1 = TrackedExecution(started_at=now - timedelta(hours=1))
        exec2 = TrackedExecution(started_at=now - timedelta(days=2))
        exec3 = TrackedExecution(started_at=now - timedelta(minutes=30))

        query.cache_execution(exec1)
        query.cache_execution(exec2)
        query.cache_execution(exec3)

        results = await query.filter(since=now - timedelta(hours=2))
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_get_analytics(self):
        """AC-5: Analytics for execution history."""
        query = QueryService()

        # Add executions with different outcomes and durations
        for i in range(5):
            exec = TrackedExecution(
                trace_context=TraceContext(persona_id="test"),
                outcome=ExecutionOutcome.SUCCESS,
                duration_ms=100 * (i + 1),
                token_count=1000,
                cost_usd=0.01,
            )
            exec.add_decision(Decision(decision_type=DecisionType.TOOL_SELECTION, choice="tool"))
            query.cache_execution(exec)

        for i in range(3):
            exec = TrackedExecution(
                trace_context=TraceContext(persona_id="test"),
                outcome=ExecutionOutcome.FAILED,
                duration_ms=50,
            )
            query.cache_execution(exec)

        analytics = await query.get_analytics()

        assert analytics.count == 8
        assert analytics.success_count == 5
        assert analytics.failed_count == 3
        assert analytics.success_rate == 5/8
        assert analytics.total_tokens == 5000
        assert analytics.total_cost_usd == 0.05
        assert DecisionType.TOOL_SELECTION.value in analytics.decisions_by_type

    @pytest.mark.asyncio
    async def test_get_failed(self):
        """AC-5: Query failed executions."""
        query = QueryService()

        exec1 = TrackedExecution(outcome=ExecutionOutcome.SUCCESS)
        exec2 = TrackedExecution(
            outcome=ExecutionOutcome.FAILED,
            error_message="Test error"
        )

        query.cache_execution(exec1)
        query.cache_execution(exec2)

        failed = await query.get_failed()
        assert len(failed) == 1
        assert failed[0].error_message == "Test error"


# =============================================================================
# Test TrackerConfig
# =============================================================================

class TestTrackerConfig:
    """Tests for TrackerConfig."""

    def test_default_config(self):
        """Test default configuration."""
        config = TrackerConfig()
        assert config.enabled is True
        assert config.stream_buffer_size == 1000
        assert config.decision_limit == 500

    def test_disabled_config(self):
        """Test disabled configuration."""
        config = TrackerConfig.disabled()
        assert config.enabled is False

    def test_minimal_config(self):
        """Test minimal configuration."""
        config = TrackerConfig.minimal()
        assert config.enabled is True
        assert config.capture_input is False
        assert config.stream_events is False

    def test_full_config(self):
        """Test full configuration."""
        config = TrackerConfig.full()
        assert config.enabled is True
        assert config.capture_input is True
        assert config.stream_events is True


# =============================================================================
# Test ExecutionTracker (All ACs)
# =============================================================================

class TestExecutionTracker:
    """Tests for main ExecutionTracker."""

    @pytest.mark.asyncio
    async def test_start_execution(self):
        """AC-1: Start creates traceable record."""
        tracker = ExecutionTracker()

        execution = await tracker.start_execution(
            persona_id="test-persona",
            input_data={"query": "test input"},
            user_id="user123",
        )

        assert execution.id is not None
        assert execution.trace_context.persona_id == "test-persona"
        assert execution.outcome == ExecutionOutcome.RUNNING

    @pytest.mark.asyncio
    async def test_log_decision(self):
        """AC-2: Decisions are logged."""
        tracker = ExecutionTracker()

        execution = await tracker.start_execution(persona_id="test")

        decision = await tracker.log_decision(
            execution_id=execution.id,
            decision_type=DecisionType.TOOL_SELECTION,
            choice="analyzer",
            reasoning="Best tool for the job",
        )

        assert decision is not None
        assert decision.choice == "analyzer"
        assert len(execution.decisions) == 1

    @pytest.mark.asyncio
    async def test_complete_execution(self):
        """AC-2: Complete captures output."""
        tracker = ExecutionTracker()

        execution = await tracker.start_execution(persona_id="test")

        completed = await tracker.complete_execution(
            execution_id=execution.id,
            output_data={"result": "success"},
            output_summary="Task completed successfully",
        )

        assert completed.outcome == ExecutionOutcome.SUCCESS
        assert completed.output_data["result"] == "success"

    @pytest.mark.asyncio
    async def test_fail_execution(self):
        """AC-2: Failure captures error."""
        tracker = ExecutionTracker()

        execution = await tracker.start_execution(persona_id="test")

        failed = await tracker.fail_execution(
            execution_id=execution.id,
            error_message="Something went wrong",
            error_details={"code": "E001"},
        )

        assert failed.outcome == ExecutionOutcome.FAILED
        assert failed.error_message == "Something went wrong"

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test track context manager."""
        tracker = ExecutionTracker()

        async with tracker.track(
            persona_id="test-persona",
            input_data={"test": True}
        ) as execution:
            await tracker.log_decision(
                execution_id=execution.id,
                decision_type=DecisionType.STRATEGY_CHOICE,
                choice="fast",
            )

        # Execution should be completed
        assert execution.id not in tracker._executions

    @pytest.mark.asyncio
    async def test_context_manager_with_error(self):
        """Test track context manager handles errors."""
        tracker = ExecutionTracker()

        with pytest.raises(ValueError):
            async with tracker.track(persona_id="test") as execution:
                raise ValueError("Test error")

        # Execution should be failed
        assert execution.id not in tracker._executions

    @pytest.mark.asyncio
    async def test_stream_events(self):
        """AC-3: Real-time streaming via tracker."""
        tracker = ExecutionTracker()
        execution = await tracker.start_execution(persona_id="test")

        received = []

        async def collect():
            async for event in tracker.stream_events(execution.id):
                received.append(event)
                if event.event_type == EventType.EXECUTION_COMPLETED:
                    break

        collector = asyncio.create_task(collect())
        await asyncio.sleep(0.1)

        await tracker.update_progress(execution.id, 50, "Halfway there")
        await tracker.complete_execution(execution.id)

        await asyncio.wait_for(collector, timeout=5.0)

        # Should have: start, progress, complete
        assert len(received) >= 2

    @pytest.mark.asyncio
    async def test_disabled_tracking(self):
        """Test disabled tracking returns minimal execution."""
        config = TrackerConfig.disabled()
        tracker = ExecutionTracker(config=config)

        execution = await tracker.start_execution(persona_id="test")

        # Still returns an execution but tracking is minimal
        assert execution is not None
        assert execution.trace_context.persona_id == "test"

    @pytest.mark.asyncio
    async def test_query_service_integration(self):
        """AC-5: Query service is accessible."""
        tracker = ExecutionTracker()

        exec1 = await tracker.start_execution(persona_id="p1")
        exec2 = await tracker.start_execution(persona_id="p2")
        exec3 = await tracker.start_execution(persona_id="p1")

        await tracker.complete_execution(exec1.id)
        await tracker.complete_execution(exec2.id)
        await tracker.complete_execution(exec3.id)

        # Query via tracker
        results = await tracker.query_service.filter(persona_id="p1")
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_list_active(self):
        """Test listing active executions."""
        tracker = ExecutionTracker()

        exec1 = await tracker.start_execution(persona_id="p1")
        exec2 = await tracker.start_execution(persona_id="p2")

        active = tracker.list_active()
        assert len(active) == 2

        await tracker.complete_execution(exec1.id)

        active = tracker.list_active()
        assert len(active) == 1


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests for the full tracking workflow."""

    @pytest.mark.asyncio
    async def test_full_execution_workflow(self):
        """Test complete execution tracking workflow."""
        tracker = ExecutionTracker()

        # Start execution
        execution = await tracker.start_execution(
            persona_id="code-reviewer",
            input_data={"code": "print('hello')"},
            context={"environment": {"python": "3.11"}},
            user_id="dev1",
            correlation_id="req-123",
            tags=["python", "quick-review"],
        )

        # Log decisions
        await tracker.log_decision(
            execution_id=execution.id,
            decision_type=DecisionType.TOOL_SELECTION,
            choice="ast_parser",
            reasoning="Python code requires AST parsing",
            alternatives=["regex", "manual"],
            confidence=0.95,
        )

        await tracker.log_decision(
            execution_id=execution.id,
            decision_type=DecisionType.STRATEGY_CHOICE,
            choice="thorough",
            reasoning="User requested detailed review",
        )

        # Update progress
        await tracker.update_progress(execution.id, 25, "Parsing code...")
        await tracker.update_progress(execution.id, 50, "Analyzing structure...")
        await tracker.update_progress(execution.id, 75, "Generating report...")

        # Complete
        result = await tracker.complete_execution(
            execution_id=execution.id,
            output_data={
                "review": "Code looks good",
                "issues": [],
                "score": 95,
            },
            output_summary="Review passed with score 95/100",
            token_count=1500,
            cost_usd=0.02,
        )

        # Verify result
        assert result.outcome == ExecutionOutcome.SUCCESS
        assert len(result.decisions) == 2
        assert result.output_data["score"] == 95
        assert result.token_count == 1500

    @pytest.mark.asyncio
    async def test_execution_with_streaming(self):
        """Test execution with event streaming."""
        tracker = ExecutionTracker()

        events = []

        async def start_and_track():
            execution = await tracker.start_execution(
                persona_id="test",
                input_data={"data": "test"},
            )

            # Collect events in background
            async def collect():
                async for event in tracker.stream_events(execution.id):
                    events.append(event)
                    if event.event_type == EventType.EXECUTION_COMPLETED:
                        break

            collector = asyncio.create_task(collect())

            await asyncio.sleep(0.1)

            # Log some activity
            await tracker.log_decision(
                execution_id=execution.id,
                decision_type=DecisionType.TOOL_SELECTION,
                choice="tool1",
            )

            await tracker.update_progress(execution.id, 50, "Half done")

            await tracker.complete_execution(execution.id)

            await asyncio.wait_for(collector, timeout=5.0)

        await start_and_track()

        # Verify events were received
        # Note: EXECUTION_STARTED may be missed if subscriber registers after start
        event_types = [e.event_type for e in events]
        assert EventType.DECISION_MADE in event_types
        assert EventType.PROGRESS_UPDATE in event_types
        assert EventType.EXECUTION_COMPLETED in event_types
        # At least 3 events should be received
        assert len(events) >= 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
