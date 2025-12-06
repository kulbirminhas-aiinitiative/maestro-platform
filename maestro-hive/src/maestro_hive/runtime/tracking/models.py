"""
Data Models for Execution Tracking

EPIC: MD-2558
AC-1: Every execution creates a traceable record
AC-2: Record includes: input, context, decisions, output, outcome

Defines the core data models for tracking persona executions.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4


class ExecutionOutcome(str, Enum):
    """Outcome of an execution."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class EventType(str, Enum):
    """Types of execution events for streaming (AC-3)."""
    EXECUTION_STARTED = "execution_started"
    CONTEXT_LOADED = "context_loaded"
    DECISION_MADE = "decision_made"
    TOOL_INVOKED = "tool_invoked"
    TOOL_COMPLETED = "tool_completed"
    PROGRESS_UPDATE = "progress_update"
    OUTPUT_GENERATED = "output_generated"
    EXECUTION_COMPLETED = "execution_completed"
    EXECUTION_FAILED = "execution_failed"
    EXECUTION_CANCELLED = "execution_cancelled"


class DecisionType(str, Enum):
    """Types of decisions that can be logged."""
    TOOL_SELECTION = "tool_selection"
    STRATEGY_CHOICE = "strategy_choice"
    PARAMETER_SETTING = "parameter_setting"
    ROUTING_DECISION = "routing_decision"
    RETRY_DECISION = "retry_decision"
    FALLBACK_DECISION = "fallback_decision"
    QUALITY_GATE = "quality_gate"
    OUTPUT_SELECTION = "output_selection"


@dataclass
class Decision:
    """
    A decision made during execution (AC-2).

    Captures what decision was made, why, and what alternatives existed.
    """
    id: UUID = field(default_factory=uuid4)
    decision_type: DecisionType = DecisionType.STRATEGY_CHOICE
    timestamp: datetime = field(default_factory=datetime.utcnow)
    choice: str = ""
    reasoning: str = ""
    alternatives: List[str] = field(default_factory=list)
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "decision_type": self.decision_type.value,
            "timestamp": self.timestamp.isoformat(),
            "choice": self.choice,
            "reasoning": self.reasoning,
            "alternatives": self.alternatives,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Decision":
        """Create from dictionary."""
        return cls(
            id=UUID(data["id"]) if data.get("id") else uuid4(),
            decision_type=DecisionType(data.get("decision_type", "strategy_choice")),
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else datetime.utcnow(),
            choice=data.get("choice", ""),
            reasoning=data.get("reasoning", ""),
            alternatives=data.get("alternatives", []),
            confidence=data.get("confidence", 1.0),
            metadata=data.get("metadata", {}),
        )


@dataclass
class ExecutionEvent:
    """
    An event emitted during execution for streaming (AC-3).

    Used for real-time progress updates.
    """
    id: UUID = field(default_factory=uuid4)
    execution_id: UUID = field(default_factory=uuid4)
    event_type: EventType = EventType.PROGRESS_UPDATE
    timestamp: datetime = field(default_factory=datetime.utcnow)
    message: str = ""
    progress_percent: Optional[float] = None
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "execution_id": str(self.execution_id),
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "message": self.message,
            "progress_percent": self.progress_percent,
            "data": self.data,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutionEvent":
        """Create from dictionary."""
        return cls(
            id=UUID(data["id"]) if data.get("id") else uuid4(),
            execution_id=UUID(data["execution_id"]) if data.get("execution_id") else uuid4(),
            event_type=EventType(data.get("event_type", "progress_update")),
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else datetime.utcnow(),
            message=data.get("message", ""),
            progress_percent=data.get("progress_percent"),
            data=data.get("data", {}),
        )


@dataclass
class TraceContext:
    """
    Complete context for an execution (AC-2).

    Captures all inputs and context needed to understand/replay the execution.
    """
    persona_id: str = ""
    persona_version: Optional[str] = None
    input_data: Dict[str, Any] = field(default_factory=dict)
    environment: Dict[str, str] = field(default_factory=dict)
    configuration: Dict[str, Any] = field(default_factory=dict)
    parent_execution_id: Optional[UUID] = None
    correlation_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "persona_id": self.persona_id,
            "persona_version": self.persona_version,
            "input_data": self.input_data,
            "environment": self.environment,
            "configuration": self.configuration,
            "parent_execution_id": str(self.parent_execution_id) if self.parent_execution_id else None,
            "correlation_id": self.correlation_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TraceContext":
        """Create from dictionary."""
        return cls(
            persona_id=data.get("persona_id", ""),
            persona_version=data.get("persona_version"),
            input_data=data.get("input_data", {}),
            environment=data.get("environment", {}),
            configuration=data.get("configuration", {}),
            parent_execution_id=UUID(data["parent_execution_id"]) if data.get("parent_execution_id") else None,
            correlation_id=data.get("correlation_id"),
            user_id=data.get("user_id"),
            session_id=data.get("session_id"),
            tags=data.get("tags", []),
        )


@dataclass
class TrackedExecution:
    """
    Complete record of a tracked execution (AC-1, AC-2).

    This is the main data model that captures everything about an execution.
    """
    # Identity
    id: UUID = field(default_factory=uuid4)

    # Context (AC-2: input, context)
    trace_context: TraceContext = field(default_factory=TraceContext)

    # Timing
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None

    # Status
    outcome: ExecutionOutcome = ExecutionOutcome.PENDING

    # Decisions (AC-2: decisions)
    decisions: List[Decision] = field(default_factory=list)

    # Events for streaming (AC-3)
    events: List[ExecutionEvent] = field(default_factory=list)

    # Output (AC-2: output, outcome)
    output_data: Dict[str, Any] = field(default_factory=dict)
    output_summary: str = ""

    # Error handling
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None

    # Metrics
    token_count: Optional[int] = None
    cost_usd: Optional[float] = None

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "id": str(self.id),
            "trace_context": self.trace_context.to_dict(),
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
            "outcome": self.outcome.value,
            "decisions": [d.to_dict() for d in self.decisions],
            "events": [e.to_dict() for e in self.events],
            "output_data": self.output_data,
            "output_summary": self.output_summary,
            "error_message": self.error_message,
            "error_details": self.error_details,
            "token_count": self.token_count,
            "cost_usd": self.cost_usd,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TrackedExecution":
        """Create from dictionary."""
        execution = cls(
            id=UUID(data["id"]) if data.get("id") else uuid4(),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else datetime.utcnow(),
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            duration_ms=data.get("duration_ms"),
            outcome=ExecutionOutcome(data.get("outcome", "pending")),
            output_data=data.get("output_data", {}),
            output_summary=data.get("output_summary", ""),
            error_message=data.get("error_message"),
            error_details=data.get("error_details"),
            token_count=data.get("token_count"),
            cost_usd=data.get("cost_usd"),
            metadata=data.get("metadata", {}),
        )

        if data.get("trace_context"):
            execution.trace_context = TraceContext.from_dict(data["trace_context"])

        if data.get("decisions"):
            execution.decisions = [Decision.from_dict(d) for d in data["decisions"]]

        if data.get("events"):
            execution.events = [ExecutionEvent.from_dict(e) for e in data["events"]]

        return execution

    def mark_started(self) -> None:
        """Mark execution as started."""
        self.outcome = ExecutionOutcome.RUNNING
        self.started_at = datetime.utcnow()

    def mark_completed(
        self,
        outcome: ExecutionOutcome = ExecutionOutcome.SUCCESS,
        output_data: Optional[Dict[str, Any]] = None,
        output_summary: str = "",
    ) -> None:
        """Mark execution as completed."""
        self.outcome = outcome
        self.completed_at = datetime.utcnow()
        self.duration_ms = int((self.completed_at - self.started_at).total_seconds() * 1000)
        if output_data:
            self.output_data = output_data
        if output_summary:
            self.output_summary = output_summary

    def mark_failed(
        self,
        error_message: str,
        error_details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Mark execution as failed."""
        self.outcome = ExecutionOutcome.FAILED
        self.completed_at = datetime.utcnow()
        self.duration_ms = int((self.completed_at - self.started_at).total_seconds() * 1000)
        self.error_message = error_message
        self.error_details = error_details

    def add_decision(self, decision: Decision) -> None:
        """Add a decision to the execution."""
        self.decisions.append(decision)

    def add_event(self, event: ExecutionEvent) -> None:
        """Add an event to the execution."""
        event.execution_id = self.id
        self.events.append(event)
