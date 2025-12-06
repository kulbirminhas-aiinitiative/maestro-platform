"""
Execution Tracking Module

EPIC: MD-2558
[RUNTIME-ENGINE] Execution Tracking - Monitor and Record All Runs

Provides comprehensive tracking of all persona executions for learning,
debugging, and compliance.

Acceptance Criteria:
- AC-1: Every execution creates a traceable record
- AC-2: Record includes: input, context, decisions, output, outcome
- AC-3: Real-time streaming of execution progress
- AC-4: Integration with Execution History Store (MD-2500)
- AC-5: Queryable execution history for analytics
"""

from .models import (
    TrackedExecution,
    TraceContext,
    Decision,
    ExecutionEvent,
    ExecutionOutcome,
    EventType,
    DecisionType,
)
from .config import TrackerConfig
from .tracker import ExecutionTracker
from .stream import StreamPublisher
from .query import QueryService

__all__ = [
    # Core models
    "TrackedExecution",
    "TraceContext",
    "Decision",
    "ExecutionEvent",
    "ExecutionOutcome",
    "EventType",
    "DecisionType",
    # Configuration
    "TrackerConfig",
    # Main components
    "ExecutionTracker",
    "StreamPublisher",
    "QueryService",
]
