"""
Agent Thought Tracing with Span-Based Observability.

Provides deep observability into agent operations with:
- Span-based distributed tracing
- Agent thought chain tracking
- LLM call instrumentation
- Performance metrics collection
- OpenTelemetry-compatible format
"""

import asyncio
import uuid
import time
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List, Any, Generator
from enum import Enum
from contextlib import contextmanager
import logging
import json

logger = logging.getLogger(__name__)


class SpanStatus(Enum):
    """Span completion status."""
    UNSET = "unset"
    OK = "ok"
    ERROR = "error"


class SpanKind(Enum):
    """Type of span."""
    INTERNAL = "internal"
    CLIENT = "client"  # Outgoing request
    SERVER = "server"  # Incoming request
    PRODUCER = "producer"  # Message producer
    CONSUMER = "consumer"  # Message consumer


@dataclass
class SpanContext:
    """Span context for propagation."""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    trace_flags: int = 1  # Sampled


@dataclass
class SpanEvent:
    """Event within a span."""
    name: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Span:
    """
    Represents a unit of work within a trace.

    Spans can be nested to represent hierarchical operations,
    such as agent thought chains or LLM call sequences.
    """
    name: str
    context: SpanContext
    kind: SpanKind = SpanKind.INTERNAL
    status: SpanStatus = SpanStatus.UNSET
    status_message: Optional[str] = None
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[SpanEvent] = field(default_factory=list)
    links: List["SpanContext"] = field(default_factory=list)

    @property
    def duration_ms(self) -> Optional[float]:
        """Duration in milliseconds."""
        if self.end_time and self.start_time:
            delta = self.end_time - self.start_time
            return delta.total_seconds() * 1000
        return None

    @property
    def is_recording(self) -> bool:
        """Check if span is still recording."""
        return self.end_time is None

    def set_attribute(self, key: str, value: Any) -> None:
        """Set a span attribute."""
        self.attributes[key] = value

    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        """Add an event to the span."""
        event = SpanEvent(name=name, attributes=attributes or {})
        self.events.append(event)

    def set_status(self, status: SpanStatus, message: Optional[str] = None) -> None:
        """Set span status."""
        self.status = status
        self.status_message = message

    def end(self) -> None:
        """End the span."""
        self.end_time = datetime.utcnow()
        if self.status == SpanStatus.UNSET:
            self.status = SpanStatus.OK

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "trace_id": self.context.trace_id,
            "span_id": self.context.span_id,
            "parent_span_id": self.context.parent_span_id,
            "kind": self.kind.value,
            "status": self.status.value,
            "status_message": self.status_message,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "attributes": self.attributes,
            "events": [
                {
                    "name": e.name,
                    "timestamp": e.timestamp.isoformat(),
                    "attributes": e.attributes,
                }
                for e in self.events
            ],
        }


@dataclass
class TraceData:
    """Complete trace data with all spans."""
    trace_id: str
    root_span: Span
    spans: List[Span] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration_ms(self) -> Optional[float]:
        """Total trace duration in milliseconds."""
        if self.end_time and self.start_time:
            delta = self.end_time - self.start_time
            return delta.total_seconds() * 1000
        return None

    @property
    def span_count(self) -> int:
        """Total number of spans including root."""
        return len(self.spans) + 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "trace_id": self.trace_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "span_count": self.span_count,
            "root_span": self.root_span.to_dict(),
            "spans": [s.to_dict() for s in self.spans],
            "metadata": self.metadata,
        }


@dataclass
class TracerConfig:
    """Configuration for agent tracer."""
    service_name: str = "maestro-hive"
    sample_rate: float = 1.0  # 0.0 to 1.0
    max_spans_per_trace: int = 1000
    max_attributes_per_span: int = 128
    max_events_per_span: int = 128
    export_batch_size: int = 100
    export_interval_ms: int = 5000


class AgentTracer:
    """
    Agent thought tracing with span-based observability.

    Provides hierarchical tracing for agent operations including:
    - Agent thought chains
    - LLM API calls
    - Tool invocations
    - Decision points
    """

    _instance: Optional["AgentTracer"] = None

    def __init__(self, config: Optional[TracerConfig] = None):
        """
        Initialize agent tracer.

        Args:
            config: Tracer configuration
        """
        self.config = config or TracerConfig()
        self._traces: Dict[str, TraceData] = {}
        self._current_context: ContextVar[Optional[SpanContext]] = \
            ContextVar("current_span", default=None)
        self._lock = asyncio.Lock()
        self._exporters: List[Any] = []

    @classmethod
    def get_instance(cls, config: Optional[TracerConfig] = None) -> "AgentTracer":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls(config)
        return cls._instance

    def _generate_trace_id(self) -> str:
        """Generate unique trace ID."""
        return uuid.uuid4().hex

    def _generate_span_id(self) -> str:
        """Generate unique span ID."""
        return uuid.uuid4().hex[:16]

    def _should_sample(self) -> bool:
        """Determine if trace should be sampled."""
        import random
        return random.random() < self.config.sample_rate

    def start_trace(
        self,
        name: str,
        attributes: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TraceData:
        """
        Start a new trace.

        Args:
            name: Root span name
            attributes: Root span attributes
            metadata: Trace metadata

        Returns:
            TraceData object
        """
        trace_id = self._generate_trace_id()
        span_id = self._generate_span_id()

        context = SpanContext(trace_id=trace_id, span_id=span_id)
        root_span = Span(
            name=name,
            context=context,
            attributes=attributes or {},
        )

        trace = TraceData(
            trace_id=trace_id,
            root_span=root_span,
            metadata=metadata or {},
        )

        self._traces[trace_id] = trace
        self._current_context.set(context)

        logger.debug(f"Started trace {trace_id}: {name}")
        return trace

    def start_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict[str, Any]] = None,
        parent_context: Optional[SpanContext] = None,
    ) -> Span:
        """
        Start a new span within current trace.

        Args:
            name: Span name
            kind: Span kind
            attributes: Span attributes
            parent_context: Override parent context

        Returns:
            New Span object
        """
        parent = parent_context or self._current_context.get()
        if not parent:
            # Start new trace if no current context
            trace = self.start_trace(name, attributes)
            return trace.root_span

        context = SpanContext(
            trace_id=parent.trace_id,
            span_id=self._generate_span_id(),
            parent_span_id=parent.span_id,
        )

        span = Span(
            name=name,
            context=context,
            kind=kind,
            attributes=attributes or {},
        )

        # Add to trace
        trace = self._traces.get(parent.trace_id)
        if trace:
            trace.spans.append(span)

        # Set as current context
        self._current_context.set(context)

        logger.debug(f"Started span {context.span_id}: {name}")
        return span

    def end_span(self, span: Span, status: SpanStatus = SpanStatus.OK, message: Optional[str] = None) -> None:
        """
        End a span.

        Args:
            span: Span to end
            status: Final status
            message: Status message
        """
        span.set_status(status, message)
        span.end()

        # Restore parent context
        if span.context.parent_span_id:
            parent_context = SpanContext(
                trace_id=span.context.trace_id,
                span_id=span.context.parent_span_id,
            )
            self._current_context.set(parent_context)

        logger.debug(f"Ended span {span.context.span_id}: {span.name} ({span.duration_ms:.2f}ms)")

    def end_trace(self, trace_id: str) -> Optional[TraceData]:
        """
        End a trace.

        Args:
            trace_id: Trace to end

        Returns:
            Complete TraceData or None
        """
        trace = self._traces.get(trace_id)
        if not trace:
            return None

        trace.end_time = datetime.utcnow()

        # End root span if still recording
        if trace.root_span.is_recording:
            trace.root_span.end()

        # Clear current context
        self._current_context.set(None)

        logger.debug(f"Ended trace {trace_id} ({trace.duration_ms:.2f}ms, {trace.span_count} spans)")
        return trace

    def get_trace(self, trace_id: str) -> Optional[TraceData]:
        """Get trace data by ID."""
        return self._traces.get(trace_id)

    def get_current_span(self) -> Optional[Span]:
        """Get currently active span."""
        context = self._current_context.get()
        if not context:
            return None

        trace = self._traces.get(context.trace_id)
        if not trace:
            return None

        if context.span_id == trace.root_span.context.span_id:
            return trace.root_span

        for span in trace.spans:
            if span.context.span_id == context.span_id:
                return span

        return None

    @contextmanager
    def span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Generator[Span, None, None]:
        """
        Context manager for spans.

        Usage:
            with tracer.span("operation") as span:
                span.set_attribute("key", "value")
                # do work
        """
        span = self.start_span(name, kind, attributes)
        try:
            yield span
            self.end_span(span, SpanStatus.OK)
        except Exception as e:
            span.add_event("exception", {"message": str(e)})
            self.end_span(span, SpanStatus.ERROR, str(e))
            raise

    def trace_llm_call(
        self,
        model: str,
        prompt: str,
        response: str,
        latency_ms: float,
        tokens_in: int,
        tokens_out: int,
        parent_span: Optional[Span] = None,
    ) -> Span:
        """
        Record an LLM API call as a span.

        Args:
            model: Model name
            prompt: Input prompt (truncated for storage)
            response: Model response (truncated for storage)
            latency_ms: Call latency
            tokens_in: Input tokens
            tokens_out: Output tokens
            parent_span: Parent span context

        Returns:
            Created span
        """
        span = self.start_span(
            name=f"llm.{model}",
            kind=SpanKind.CLIENT,
            attributes={
                "llm.model": model,
                "llm.prompt_length": len(prompt),
                "llm.response_length": len(response),
                "llm.tokens_in": tokens_in,
                "llm.tokens_out": tokens_out,
                "llm.latency_ms": latency_ms,
            },
            parent_context=parent_span.context if parent_span else None,
        )

        # Add truncated content as events
        span.add_event("prompt", {"text": prompt[:500]})
        span.add_event("response", {"text": response[:500]})

        self.end_span(span)
        return span

    def trace_agent_thought(
        self,
        agent_id: str,
        thought: str,
        action: Optional[str] = None,
        observation: Optional[str] = None,
        parent_span: Optional[Span] = None,
    ) -> Span:
        """
        Record agent thought/action/observation cycle.

        Args:
            agent_id: Agent identifier
            thought: Agent's reasoning
            action: Action taken
            observation: Result of action
            parent_span: Parent span context

        Returns:
            Created span
        """
        span = self.start_span(
            name=f"agent.thought",
            kind=SpanKind.INTERNAL,
            attributes={
                "agent.id": agent_id,
                "agent.thought_length": len(thought),
            },
            parent_context=parent_span.context if parent_span else None,
        )

        span.add_event("thought", {"text": thought[:1000]})

        if action:
            span.add_event("action", {"text": action})

        if observation:
            span.add_event("observation", {"text": observation[:1000]})

        self.end_span(span)
        return span

    def export_trace(self, trace_id: str, format: str = "json") -> Optional[str]:
        """
        Export trace data.

        Args:
            trace_id: Trace to export
            format: Export format (json, otlp)

        Returns:
            Serialized trace data
        """
        trace = self._traces.get(trace_id)
        if not trace:
            return None

        if format == "json":
            return json.dumps(trace.to_dict(), indent=2)

        # Add other formats as needed
        return json.dumps(trace.to_dict())

    def clear_completed_traces(self, max_age_hours: int = 24) -> int:
        """
        Clear old completed traces.

        Args:
            max_age_hours: Maximum age of traces to keep

        Returns:
            Number of traces cleared
        """
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        cleared = 0

        for trace_id, trace in list(self._traces.items()):
            if trace.end_time and trace.end_time < cutoff:
                del self._traces[trace_id]
                cleared += 1

        return cleared


# Import timedelta for clear_completed_traces
from datetime import timedelta
