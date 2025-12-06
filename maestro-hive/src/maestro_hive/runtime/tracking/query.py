"""
Query Service for Execution Analytics

EPIC: MD-2558
AC-5: Queryable execution history for analytics

Provides querying, filtering, and analytics for execution history.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from .models import TrackedExecution, ExecutionOutcome, DecisionType

logger = logging.getLogger(__name__)


@dataclass
class ExecutionFilter:
    """Filter criteria for querying executions."""
    persona_id: Optional[str] = None
    outcome: Optional[ExecutionOutcome] = None
    outcomes: Optional[List[ExecutionOutcome]] = None
    since: Optional[datetime] = None
    until: Optional[datetime] = None
    tags: Optional[List[str]] = None
    user_id: Optional[str] = None
    correlation_id: Optional[str] = None
    min_duration_ms: Optional[int] = None
    max_duration_ms: Optional[int] = None
    has_errors: Optional[bool] = None


@dataclass
class AnalyticsResult:
    """Result of analytics queries."""
    count: int = 0
    success_count: int = 0
    failed_count: int = 0
    success_rate: float = 0.0
    avg_duration_ms: float = 0.0
    min_duration_ms: Optional[int] = None
    max_duration_ms: Optional[int] = None
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    decisions_by_type: Dict[str, int] = None
    top_personas: List[Tuple[str, int]] = None

    def __post_init__(self):
        if self.decisions_by_type is None:
            self.decisions_by_type = {}
        if self.top_personas is None:
            self.top_personas = []


class QueryService:
    """
    Service for querying execution history (AC-5).

    Provides filtering, aggregation, and analytics for execution data.

    Usage:
        query = QueryService(history_store=store)

        # Filter executions
        results = await query.filter(
            persona_id="code-reviewer",
            outcome=ExecutionOutcome.SUCCESS,
            since=datetime.now() - timedelta(days=7)
        )

        # Get analytics
        analytics = await query.get_analytics(
            group_by="persona_id",
            since=datetime.now() - timedelta(days=30)
        )
    """

    def __init__(self, history_store: Optional[Any] = None):
        """
        Initialize the query service.

        Args:
            history_store: Optional ExecutionHistoryStore for database queries
        """
        self._history_store = history_store
        self._cache: Dict[UUID, TrackedExecution] = {}

        logger.info("QueryService initialized")

    def cache_execution(self, execution: TrackedExecution) -> None:
        """Add an execution to the in-memory cache."""
        self._cache[execution.id] = execution

    def get_cached(self, execution_id: UUID) -> Optional[TrackedExecution]:
        """Get an execution from cache."""
        return self._cache.get(execution_id)

    async def filter(
        self,
        persona_id: Optional[str] = None,
        outcome: Optional[ExecutionOutcome] = None,
        outcomes: Optional[List[ExecutionOutcome]] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        tags: Optional[List[str]] = None,
        user_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        min_duration_ms: Optional[int] = None,
        max_duration_ms: Optional[int] = None,
        has_errors: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[TrackedExecution]:
        """
        Filter executions based on criteria (AC-5).

        Args:
            persona_id: Filter by persona ID
            outcome: Filter by single outcome
            outcomes: Filter by multiple outcomes
            since: Filter executions after this time
            until: Filter executions before this time
            tags: Filter by tags (any match)
            user_id: Filter by user ID
            correlation_id: Filter by correlation ID
            min_duration_ms: Minimum duration in milliseconds
            max_duration_ms: Maximum duration in milliseconds
            has_errors: Filter by error presence
            limit: Maximum results to return
            offset: Offset for pagination

        Returns:
            List of matching TrackedExecution objects
        """
        # Use cache if no history store
        results = []

        for execution in self._cache.values():
            if not self._matches_filter(
                execution,
                persona_id=persona_id,
                outcome=outcome,
                outcomes=outcomes,
                since=since,
                until=until,
                tags=tags,
                user_id=user_id,
                correlation_id=correlation_id,
                min_duration_ms=min_duration_ms,
                max_duration_ms=max_duration_ms,
                has_errors=has_errors,
            ):
                continue
            results.append(execution)

        # Sort by started_at descending
        results.sort(key=lambda e: e.started_at, reverse=True)

        # Apply pagination
        return results[offset:offset + limit]

    def _matches_filter(
        self,
        execution: TrackedExecution,
        persona_id: Optional[str] = None,
        outcome: Optional[ExecutionOutcome] = None,
        outcomes: Optional[List[ExecutionOutcome]] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        tags: Optional[List[str]] = None,
        user_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        min_duration_ms: Optional[int] = None,
        max_duration_ms: Optional[int] = None,
        has_errors: Optional[bool] = None,
    ) -> bool:
        """Check if an execution matches filter criteria."""
        ctx = execution.trace_context

        if persona_id and ctx.persona_id != persona_id:
            return False

        if outcome and execution.outcome != outcome:
            return False

        if outcomes and execution.outcome not in outcomes:
            return False

        if since and execution.started_at < since:
            return False

        if until and execution.started_at > until:
            return False

        if tags and not any(t in ctx.tags for t in tags):
            return False

        if user_id and ctx.user_id != user_id:
            return False

        if correlation_id and ctx.correlation_id != correlation_id:
            return False

        if min_duration_ms and (execution.duration_ms is None or execution.duration_ms < min_duration_ms):
            return False

        if max_duration_ms and (execution.duration_ms is None or execution.duration_ms > max_duration_ms):
            return False

        if has_errors is not None:
            has_error = execution.error_message is not None
            if has_errors != has_error:
                return False

        return True

    async def get_by_id(self, execution_id: UUID) -> Optional[TrackedExecution]:
        """Get an execution by ID."""
        # Check cache first
        if execution_id in self._cache:
            return self._cache[execution_id]

        # Try history store
        if self._history_store:
            record = await self._history_store.get_execution(execution_id)
            if record:
                # Convert ExecutionRecord to TrackedExecution
                return self._record_to_tracked(record)

        return None

    async def get_analytics(
        self,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        persona_id: Optional[str] = None,
        group_by: Optional[str] = None,
    ) -> AnalyticsResult:
        """
        Get analytics for executions (AC-5).

        Args:
            since: Start of time range
            until: End of time range
            persona_id: Filter by persona
            group_by: Optional grouping field

        Returns:
            AnalyticsResult with aggregated metrics
        """
        # Filter relevant executions
        executions = await self.filter(
            persona_id=persona_id,
            since=since,
            until=until,
            limit=10000,  # Get all for analytics
        )

        if not executions:
            return AnalyticsResult()

        # Calculate metrics
        count = len(executions)
        success_count = sum(1 for e in executions if e.outcome == ExecutionOutcome.SUCCESS)
        failed_count = sum(1 for e in executions if e.outcome == ExecutionOutcome.FAILED)
        success_rate = success_count / count if count > 0 else 0.0

        durations = [e.duration_ms for e in executions if e.duration_ms is not None]
        avg_duration = sum(durations) / len(durations) if durations else 0.0
        min_duration = min(durations) if durations else None
        max_duration = max(durations) if durations else None

        total_tokens = sum(e.token_count or 0 for e in executions)
        total_cost = sum(e.cost_usd or 0.0 for e in executions)

        # Count decisions by type
        decisions_by_type: Dict[str, int] = {}
        for e in executions:
            for d in e.decisions:
                dtype = d.decision_type.value
                decisions_by_type[dtype] = decisions_by_type.get(dtype, 0) + 1

        # Top personas
        persona_counts: Dict[str, int] = {}
        for e in executions:
            pid = e.trace_context.persona_id
            persona_counts[pid] = persona_counts.get(pid, 0) + 1
        top_personas = sorted(persona_counts.items(), key=lambda x: x[1], reverse=True)[:10]

        return AnalyticsResult(
            count=count,
            success_count=success_count,
            failed_count=failed_count,
            success_rate=success_rate,
            avg_duration_ms=avg_duration,
            min_duration_ms=min_duration,
            max_duration_ms=max_duration,
            total_tokens=total_tokens,
            total_cost_usd=total_cost,
            decisions_by_type=decisions_by_type,
            top_personas=top_personas,
        )

    async def get_recent(
        self,
        limit: int = 10,
        persona_id: Optional[str] = None,
    ) -> List[TrackedExecution]:
        """Get the most recent executions."""
        return await self.filter(
            persona_id=persona_id,
            limit=limit,
        )

    async def get_failed(
        self,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[TrackedExecution]:
        """Get failed executions for debugging."""
        return await self.filter(
            outcome=ExecutionOutcome.FAILED,
            since=since,
            limit=limit,
        )

    async def get_by_correlation(
        self,
        correlation_id: str,
    ) -> List[TrackedExecution]:
        """Get all executions with a correlation ID."""
        return await self.filter(
            correlation_id=correlation_id,
            limit=1000,
        )

    async def count(
        self,
        since: Optional[datetime] = None,
        outcome: Optional[ExecutionOutcome] = None,
    ) -> int:
        """Count executions matching criteria."""
        executions = await self.filter(
            since=since,
            outcome=outcome,
            limit=100000,
        )
        return len(executions)

    def _record_to_tracked(self, record: Any) -> TrackedExecution:
        """Convert an ExecutionRecord to TrackedExecution."""
        from .models import TraceContext

        execution = TrackedExecution(
            id=record.id,
            started_at=record.created_at,
            completed_at=record.completed_at,
            outcome=ExecutionOutcome(record.status.value) if hasattr(record.status, 'value') else ExecutionOutcome.PENDING,
            output_summary=record.output_summary,
            error_message=record.failure_reason,
            error_details=record.error_details,
        )

        # Set context from input metadata
        if record.input_metadata:
            execution.trace_context = TraceContext(
                persona_id=record.input_metadata.get("persona_id", ""),
                input_data={"text": record.input_text},
            )

        return execution
