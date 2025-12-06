"""
Main Execution Tracker

EPIC: MD-2558
[RUNTIME-ENGINE] Execution Tracking - Monitor and Record All Runs

This is the main orchestrator for execution tracking, implementing all
acceptance criteria.

AC-1: Every execution creates a traceable record
AC-2: Record includes: input, context, decisions, output, outcome
AC-3: Real-time streaming of execution progress
AC-4: Integration with Execution History Store (MD-2500)
AC-5: Queryable execution history for analytics
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, AsyncIterator, Dict, List, Optional, Union
from uuid import UUID, uuid4

from .config import TrackerConfig
from .models import (
    TrackedExecution,
    TraceContext,
    Decision,
    ExecutionEvent,
    ExecutionOutcome,
    EventType,
    DecisionType,
)
from .stream import StreamPublisher
from .query import QueryService

logger = logging.getLogger(__name__)


class ExecutionTracker:
    """
    Main tracker for persona executions (AC-1, AC-2, AC-3, AC-4).

    Provides comprehensive tracking of all persona executions including:
    - Creating traceable execution records (AC-1)
    - Capturing input, context, decisions, output, outcome (AC-2)
    - Real-time event streaming (AC-3)
    - Integration with ExecutionHistoryStore (AC-4)

    Usage:
        tracker = ExecutionTracker(history_store=store)

        # Track an execution
        async with tracker.track(persona_id="code-reviewer", input_data={...}) as execution:
            # Log decisions
            await tracker.log_decision(
                execution_id=execution.id,
                decision_type=DecisionType.TOOL_SELECTION,
                choice="static_analysis",
                reasoning="Code review requires static analysis"
            )

            # Update progress
            await tracker.update_progress(execution.id, 50, "Analyzing code...")

            # Complete with output
            await tracker.complete(
                execution_id=execution.id,
                output={"review": "...", "score": 85}
            )
    """

    def __init__(
        self,
        config: Optional[TrackerConfig] = None,
        history_store: Optional[Any] = None,
    ):
        """
        Initialize the tracker.

        Args:
            config: Tracker configuration
            history_store: ExecutionHistoryStore instance (MD-2500 integration)
        """
        self.config = config or TrackerConfig.from_env()
        self._history_store = history_store

        # Active executions
        self._executions: Dict[UUID, TrackedExecution] = {}

        # Event streaming (AC-3)
        self._stream_publisher = StreamPublisher(
            buffer_size=self.config.stream_buffer_size
        )

        # Query service (AC-5)
        self._query_service = QueryService(history_store=history_store)

        logger.info(f"ExecutionTracker initialized (enabled={self.config.enabled})")

    @property
    def stream_publisher(self) -> StreamPublisher:
        """Get the stream publisher for subscriptions."""
        return self._stream_publisher

    @property
    def query_service(self) -> QueryService:
        """Get the query service for analytics."""
        return self._query_service

    async def start_execution(
        self,
        persona_id: str,
        input_data: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        persona_version: Optional[str] = None,
        parent_execution_id: Optional[UUID] = None,
        correlation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TrackedExecution:
        """
        Start tracking a new execution (AC-1).

        Args:
            persona_id: ID of the persona being executed
            input_data: Input data for the execution
            context: Additional context (environment, config, etc.)
            persona_version: Version of the persona
            parent_execution_id: Parent execution if nested
            correlation_id: Correlation ID for tracing
            user_id: User who initiated the execution
            session_id: Session identifier
            tags: Tags for categorization
            metadata: Additional metadata

        Returns:
            TrackedExecution with unique ID
        """
        if not self.config.enabled:
            # Return a minimal execution for disabled tracking
            return TrackedExecution(
                trace_context=TraceContext(persona_id=persona_id),
                outcome=ExecutionOutcome.RUNNING,
            )

        # Create trace context (AC-2)
        trace_context = TraceContext(
            persona_id=persona_id,
            persona_version=persona_version,
            input_data=input_data if self.config.capture_input else {},
            environment=context.get("environment", {}) if context and self.config.capture_context else {},
            configuration=context.get("configuration", {}) if context and self.config.capture_context else {},
            parent_execution_id=parent_execution_id,
            correlation_id=correlation_id,
            user_id=user_id,
            session_id=session_id,
            tags=tags or [],
        )

        # Create execution record (AC-1)
        execution = TrackedExecution(
            id=uuid4(),
            trace_context=trace_context,
            started_at=datetime.utcnow(),
            outcome=ExecutionOutcome.RUNNING,
            metadata=metadata or {},
        )

        # Store in active executions
        self._executions[execution.id] = execution

        # Cache for queries (AC-5)
        self._query_service.cache_execution(execution)

        # Publish start event (AC-3)
        if self.config.stream_events:
            await self._publish_event(
                execution_id=execution.id,
                event_type=EventType.EXECUTION_STARTED,
                message=f"Execution started for persona {persona_id}",
            )

        logger.info(f"Started execution {execution.id} for persona {persona_id}")

        return execution

    async def log_decision(
        self,
        execution_id: UUID,
        decision_type: Union[DecisionType, str],
        choice: str,
        reasoning: str = "",
        alternatives: Optional[List[str]] = None,
        confidence: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Decision]:
        """
        Log a decision made during execution (AC-2).

        Args:
            execution_id: The execution ID
            decision_type: Type of decision
            choice: The choice that was made
            reasoning: Explanation for the decision
            alternatives: Other options that were considered
            confidence: Confidence level (0-1)
            metadata: Additional decision metadata

        Returns:
            The logged Decision, or None if tracking disabled
        """
        if not self.config.enabled or not self.config.store_decisions:
            return None

        execution = self._executions.get(execution_id)
        if not execution:
            logger.warning(f"No active execution found: {execution_id}")
            return None

        # Check decision limit
        if len(execution.decisions) >= self.config.decision_limit:
            logger.warning(f"Decision limit reached for execution {execution_id}")
            return None

        # Parse decision type
        if isinstance(decision_type, str):
            decision_type = DecisionType(decision_type)

        # Create decision
        decision = Decision(
            decision_type=decision_type,
            choice=choice,
            reasoning=reasoning,
            alternatives=alternatives or [],
            confidence=confidence,
            metadata=metadata or {},
        )

        # Add to execution
        execution.add_decision(decision)

        # Publish event (AC-3)
        if self.config.stream_events:
            await self._publish_event(
                execution_id=execution_id,
                event_type=EventType.DECISION_MADE,
                message=f"Decision: {decision_type.value} -> {choice}",
                data={"decision": decision.to_dict()},
            )

        logger.debug(f"Logged decision for {execution_id}: {decision_type.value} = {choice}")

        return decision

    async def update_progress(
        self,
        execution_id: UUID,
        percent: float,
        message: str = "",
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Update execution progress (AC-3).

        Args:
            execution_id: The execution ID
            percent: Progress percentage (0-100)
            message: Progress message
            data: Additional progress data
        """
        if not self.config.enabled or not self.config.stream_events:
            return

        await self._publish_event(
            execution_id=execution_id,
            event_type=EventType.PROGRESS_UPDATE,
            message=message,
            progress_percent=percent,
            data=data or {},
        )

    async def log_tool_invocation(
        self,
        execution_id: UUID,
        tool_name: str,
        tool_input: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log a tool invocation."""
        if not self.config.enabled:
            return

        await self._publish_event(
            execution_id=execution_id,
            event_type=EventType.TOOL_INVOKED,
            message=f"Invoking tool: {tool_name}",
            data={"tool_name": tool_name, "input": tool_input or {}},
        )

    async def log_tool_completion(
        self,
        execution_id: UUID,
        tool_name: str,
        tool_output: Optional[Dict[str, Any]] = None,
        success: bool = True,
    ) -> None:
        """Log tool completion."""
        if not self.config.enabled:
            return

        await self._publish_event(
            execution_id=execution_id,
            event_type=EventType.TOOL_COMPLETED,
            message=f"Tool completed: {tool_name} ({'success' if success else 'failed'})",
            data={"tool_name": tool_name, "output": tool_output or {}, "success": success},
        )

    async def complete_execution(
        self,
        execution_id: UUID,
        output_data: Optional[Dict[str, Any]] = None,
        output_summary: str = "",
        outcome: ExecutionOutcome = ExecutionOutcome.SUCCESS,
        token_count: Optional[int] = None,
        cost_usd: Optional[float] = None,
    ) -> Optional[TrackedExecution]:
        """
        Complete an execution (AC-2).

        Args:
            execution_id: The execution ID
            output_data: Output data from the execution
            output_summary: Summary of the output
            outcome: Execution outcome
            token_count: Total tokens used
            cost_usd: Total cost in USD

        Returns:
            The completed TrackedExecution
        """
        if not self.config.enabled:
            return None

        execution = self._executions.get(execution_id)
        if not execution:
            logger.warning(f"No active execution found: {execution_id}")
            return None

        # Mark completed
        execution.mark_completed(
            outcome=outcome,
            output_data=output_data if self.config.capture_output else {},
            output_summary=output_summary,
        )
        execution.token_count = token_count
        execution.cost_usd = cost_usd

        # Store in history (AC-4)
        await self._store_in_history(execution)

        # Publish completion event (AC-3)
        if self.config.stream_events:
            await self._publish_event(
                execution_id=execution_id,
                event_type=EventType.EXECUTION_COMPLETED,
                message=f"Execution completed: {outcome.value}",
                data={"outcome": outcome.value, "duration_ms": execution.duration_ms},
            )

        # Cleanup
        del self._executions[execution_id]

        logger.info(f"Completed execution {execution_id}: {outcome.value} in {execution.duration_ms}ms")

        return execution

    async def fail_execution(
        self,
        execution_id: UUID,
        error_message: str,
        error_details: Optional[Dict[str, Any]] = None,
    ) -> Optional[TrackedExecution]:
        """
        Mark an execution as failed (AC-2).

        Args:
            execution_id: The execution ID
            error_message: Error message
            error_details: Additional error details

        Returns:
            The failed TrackedExecution
        """
        if not self.config.enabled:
            return None

        execution = self._executions.get(execution_id)
        if not execution:
            logger.warning(f"No active execution found: {execution_id}")
            return None

        # Mark failed
        execution.mark_failed(
            error_message=error_message,
            error_details=error_details,
        )

        # Store in history (AC-4)
        await self._store_in_history(execution)

        # Publish failure event (AC-3)
        if self.config.stream_events:
            await self._publish_event(
                execution_id=execution_id,
                event_type=EventType.EXECUTION_FAILED,
                message=f"Execution failed: {error_message}",
                data={"error": error_message, "details": error_details},
            )

        # Cleanup
        del self._executions[execution_id]

        logger.error(f"Execution {execution_id} failed: {error_message}")

        return execution

    async def cancel_execution(
        self,
        execution_id: UUID,
        reason: str = "Cancelled by user",
    ) -> Optional[TrackedExecution]:
        """Cancel an execution."""
        if not self.config.enabled:
            return None

        execution = self._executions.get(execution_id)
        if not execution:
            return None

        execution.outcome = ExecutionOutcome.CANCELLED
        execution.completed_at = datetime.utcnow()
        execution.duration_ms = int((execution.completed_at - execution.started_at).total_seconds() * 1000)
        execution.error_message = reason

        await self._store_in_history(execution)

        if self.config.stream_events:
            await self._publish_event(
                execution_id=execution_id,
                event_type=EventType.EXECUTION_CANCELLED,
                message=reason,
            )

        del self._executions[execution_id]

        return execution

    @asynccontextmanager
    async def track(
        self,
        persona_id: str,
        input_data: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> AsyncIterator[TrackedExecution]:
        """
        Context manager for tracking an execution.

        Usage:
            async with tracker.track("code-reviewer", {"code": "..."}) as execution:
                # Do work
                await tracker.log_decision(execution.id, ...)
        """
        execution = await self.start_execution(
            persona_id=persona_id,
            input_data=input_data,
            **kwargs,
        )

        try:
            yield execution
        except Exception as e:
            await self.fail_execution(
                execution_id=execution.id,
                error_message=str(e),
                error_details={"exception_type": type(e).__name__},
            )
            raise
        else:
            # Only complete if not already completed
            if execution.id in self._executions:
                await self.complete_execution(execution_id=execution.id)

    async def stream_events(
        self,
        execution_id: UUID,
        event_types: Optional[List[EventType]] = None,
    ) -> AsyncIterator[ExecutionEvent]:
        """
        Stream events for an execution (AC-3).

        Args:
            execution_id: The execution ID
            event_types: Optional filter for event types

        Yields:
            ExecutionEvents as they occur
        """
        async for event in self._stream_publisher.subscribe(execution_id, event_types):
            yield event

    def get_execution(self, execution_id: UUID) -> Optional[TrackedExecution]:
        """Get an active execution by ID."""
        return self._executions.get(execution_id)

    def list_active(self) -> List[TrackedExecution]:
        """List all active executions."""
        return list(self._executions.values())

    async def _publish_event(
        self,
        execution_id: UUID,
        event_type: EventType,
        message: str,
        progress_percent: Optional[float] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Publish an event to the stream."""
        event = ExecutionEvent(
            execution_id=execution_id,
            event_type=event_type,
            message=message,
            progress_percent=progress_percent,
            data=data or {},
        )

        # Add to execution events
        execution = self._executions.get(execution_id)
        if execution:
            execution.add_event(event)

        # Publish to stream
        await self._stream_publisher.publish(event)

    async def _store_in_history(self, execution: TrackedExecution) -> None:
        """
        Store execution in history (AC-4).

        Converts TrackedExecution to ExecutionRecord for storage.
        """
        if not self._history_store:
            logger.debug("No history store configured, skipping persistence")
            return

        try:
            # Import here to avoid circular dependency
            from ...history.models import ExecutionRecord, ExecutionStatus, OutputArtifact

            # Map outcome to status
            status_map = {
                ExecutionOutcome.PENDING: ExecutionStatus.PENDING,
                ExecutionOutcome.RUNNING: ExecutionStatus.RUNNING,
                ExecutionOutcome.SUCCESS: ExecutionStatus.SUCCESS,
                ExecutionOutcome.FAILED: ExecutionStatus.FAILED,
                ExecutionOutcome.PARTIAL: ExecutionStatus.PARTIAL,
                ExecutionOutcome.CANCELLED: ExecutionStatus.CANCELLED,
                ExecutionOutcome.TIMEOUT: ExecutionStatus.FAILED,
            }

            # Create ExecutionRecord
            record = ExecutionRecord(
                id=execution.id,
                epic_key=execution.trace_context.persona_id,  # Use persona_id as epic_key
                created_at=execution.started_at,
                updated_at=datetime.utcnow(),
                completed_at=execution.completed_at,
                status=status_map.get(execution.outcome, ExecutionStatus.PENDING),
                input_text=str(execution.trace_context.input_data),
                input_metadata={
                    "persona_id": execution.trace_context.persona_id,
                    "persona_version": execution.trace_context.persona_version,
                    "correlation_id": execution.trace_context.correlation_id,
                    "user_id": execution.trace_context.user_id,
                    "tags": execution.trace_context.tags,
                    "decisions": [d.to_dict() for d in execution.decisions],
                },
                output_summary=execution.output_summary,
                failure_reason=execution.error_message,
                error_details=execution.error_details,
                executor_version="ExecutionTracker/1.0",
            )

            # Store
            await self._history_store.store_execution(record)
            logger.debug(f"Stored execution {execution.id} in history")

        except Exception as e:
            logger.error(f"Failed to store execution in history: {e}")
