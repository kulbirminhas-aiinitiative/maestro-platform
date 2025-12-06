"""
Configuration for Execution Tracking

EPIC: MD-2558
Provides configuration options for the tracking system.
"""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TrackerConfig:
    """
    Configuration for the ExecutionTracker.

    Attributes:
        enabled: Whether tracking is enabled
        stream_buffer_size: Maximum events to buffer before backpressure
        decision_limit: Maximum decisions per execution
        capture_input: Whether to capture input data
        capture_output: Whether to capture output data
        capture_context: Whether to capture full context
        stream_events: Whether to enable event streaming
        store_decisions: Whether to store decisions in history
        retention_days: Days to retain execution data
    """
    enabled: bool = True
    stream_buffer_size: int = 1000
    decision_limit: int = 500
    capture_input: bool = True
    capture_output: bool = True
    capture_context: bool = True
    stream_events: bool = True
    store_decisions: bool = True
    retention_days: int = 90

    @classmethod
    def from_env(cls) -> "TrackerConfig":
        """Create configuration from environment variables."""
        return cls(
            enabled=os.getenv("TRACKING_ENABLED", "true").lower() == "true",
            stream_buffer_size=int(os.getenv("TRACKING_STREAM_BUFFER", "1000")),
            decision_limit=int(os.getenv("TRACKING_DECISION_LIMIT", "500")),
            capture_input=os.getenv("TRACKING_CAPTURE_INPUT", "true").lower() == "true",
            capture_output=os.getenv("TRACKING_CAPTURE_OUTPUT", "true").lower() == "true",
            capture_context=os.getenv("TRACKING_CAPTURE_CONTEXT", "true").lower() == "true",
            stream_events=os.getenv("TRACKING_STREAM_EVENTS", "true").lower() == "true",
            store_decisions=os.getenv("TRACKING_STORE_DECISIONS", "true").lower() == "true",
            retention_days=int(os.getenv("TRACKING_RETENTION_DAYS", "90")),
        )

    @classmethod
    def disabled(cls) -> "TrackerConfig":
        """Create a disabled configuration."""
        return cls(enabled=False)

    @classmethod
    def minimal(cls) -> "TrackerConfig":
        """Create a minimal configuration for low overhead."""
        return cls(
            enabled=True,
            capture_input=False,
            capture_context=False,
            stream_events=False,
            store_decisions=False,
        )

    @classmethod
    def full(cls) -> "TrackerConfig":
        """Create a full configuration for debugging."""
        return cls(
            enabled=True,
            stream_buffer_size=10000,
            decision_limit=1000,
            capture_input=True,
            capture_output=True,
            capture_context=True,
            stream_events=True,
            store_decisions=True,
        )
