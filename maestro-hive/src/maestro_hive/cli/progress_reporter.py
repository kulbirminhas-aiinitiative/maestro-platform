"""
Progress Reporter
=================

Real-time progress reporting and status updates.

Implements: AC-4 (Progress reporting and status updates)
"""

import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable, Optional, Any, TextIO


class ProgressEventType(Enum):
    """Types of progress events."""
    STARTED = "started"
    STEP_UPDATE = "step_update"
    MESSAGE = "message"
    WARNING = "warning"
    ERROR = "error"
    COMPLETED = "completed"


@dataclass
class ProgressEvent:
    """A progress event."""
    event_type: ProgressEventType
    timestamp: datetime
    step: int = 0
    total_steps: int = 0
    message: str = ""
    percentage: float = 0.0
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert event to dictionary."""
        return {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "step": self.step,
            "total_steps": self.total_steps,
            "message": self.message,
            "percentage": self.percentage,
            "metadata": self.metadata,
        }


class ProgressReporter:
    """
    Reports progress for long-running operations.

    Provides:
    - Real-time progress updates
    - Step-by-step status reporting
    - Progress bar visualization
    - Event callbacks for integration

    Implements AC-4: Progress reporting and status updates
    """

    def __init__(
        self,
        output: Optional[TextIO] = None,
        verbose: bool = True,
        show_progress_bar: bool = True,
    ):
        """
        Initialize the progress reporter.

        Args:
            output: Output stream (defaults to sys.stdout)
            verbose: Whether to print verbose messages
            show_progress_bar: Whether to show progress bar
        """
        self.output = output or sys.stdout
        self.verbose = verbose
        self.show_progress_bar = show_progress_bar

        self._total_steps: int = 0
        self._current_step: int = 0
        self._started_at: Optional[datetime] = None
        self._events: list[ProgressEvent] = []
        self._callbacks: list[Callable[[ProgressEvent], None]] = []

    def start(self, total_steps: int, message: str = "Starting...") -> None:
        """
        Start progress tracking.

        Args:
            total_steps: Total number of steps
            message: Initial message
        """
        self._total_steps = total_steps
        self._current_step = 0
        self._started_at = datetime.now()
        self._events = []

        event = ProgressEvent(
            event_type=ProgressEventType.STARTED,
            timestamp=datetime.now(),
            step=0,
            total_steps=total_steps,
            message=message,
            percentage=0.0,
        )

        self._emit_event(event)
        self._print_progress(message)

    def update(self, step: int, message: str = "") -> None:
        """
        Update progress to a specific step.

        Args:
            step: Current step number
            message: Status message
        """
        self._current_step = step
        percentage = (step / self._total_steps * 100) if self._total_steps > 0 else 0

        event = ProgressEvent(
            event_type=ProgressEventType.STEP_UPDATE,
            timestamp=datetime.now(),
            step=step,
            total_steps=self._total_steps,
            message=message,
            percentage=percentage,
        )

        self._emit_event(event)
        self._print_progress(message, step, percentage)

    def message(self, text: str) -> None:
        """
        Print an informational message.

        Args:
            text: Message text
        """
        event = ProgressEvent(
            event_type=ProgressEventType.MESSAGE,
            timestamp=datetime.now(),
            step=self._current_step,
            total_steps=self._total_steps,
            message=text,
            percentage=self._get_percentage(),
        )

        self._emit_event(event)

        if self.verbose:
            self._print(f"  {text}")

    def warning(self, text: str) -> None:
        """
        Print a warning message.

        Args:
            text: Warning text
        """
        event = ProgressEvent(
            event_type=ProgressEventType.WARNING,
            timestamp=datetime.now(),
            step=self._current_step,
            total_steps=self._total_steps,
            message=text,
            percentage=self._get_percentage(),
        )

        self._emit_event(event)
        self._print(f"  WARNING: {text}")

    def error(self, text: str) -> None:
        """
        Print an error message.

        Args:
            text: Error text
        """
        event = ProgressEvent(
            event_type=ProgressEventType.ERROR,
            timestamp=datetime.now(),
            step=self._current_step,
            total_steps=self._total_steps,
            message=text,
            percentage=self._get_percentage(),
        )

        self._emit_event(event)
        self._print(f"  ERROR: {text}")

    def complete(self, result: Any = None) -> None:
        """
        Mark progress as complete.

        Args:
            result: Optional result object
        """
        elapsed = None
        if self._started_at:
            elapsed = (datetime.now() - self._started_at).total_seconds()

        metadata = {}
        if elapsed is not None:
            metadata["elapsed_seconds"] = elapsed
        if result is not None and hasattr(result, 'score'):
            metadata["score"] = result.score

        event = ProgressEvent(
            event_type=ProgressEventType.COMPLETED,
            timestamp=datetime.now(),
            step=self._total_steps,
            total_steps=self._total_steps,
            message="Complete",
            percentage=100.0,
            metadata=metadata,
        )

        self._emit_event(event)

        # Print completion summary
        elapsed_str = f" ({elapsed:.1f}s)" if elapsed else ""
        self._print(f"\nCompleted{elapsed_str}")

        if result and hasattr(result, 'score') and result.score is not None:
            self._print(f"Score: {result.score:.1f}/100")

    def add_callback(self, callback: Callable[[ProgressEvent], None]) -> None:
        """
        Add a callback for progress events.

        Args:
            callback: Function to call on each event
        """
        self._callbacks.append(callback)

    def remove_callback(self, callback: Callable[[ProgressEvent], None]) -> None:
        """
        Remove a callback.

        Args:
            callback: Function to remove
        """
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def get_events(self) -> list[ProgressEvent]:
        """
        Get all progress events.

        Returns:
            List of ProgressEvent objects
        """
        return list(self._events)

    def get_current_progress(self) -> dict:
        """
        Get current progress status.

        Returns:
            Dictionary with current progress details
        """
        elapsed = None
        if self._started_at:
            elapsed = (datetime.now() - self._started_at).total_seconds()

        return {
            "current_step": self._current_step,
            "total_steps": self._total_steps,
            "percentage": self._get_percentage(),
            "elapsed_seconds": elapsed,
            "events_count": len(self._events),
        }

    def _emit_event(self, event: ProgressEvent) -> None:
        """Emit an event to all callbacks."""
        self._events.append(event)

        for callback in self._callbacks:
            try:
                callback(event)
            except Exception:
                pass  # Don't let callback errors break progress

    def _print(self, text: str) -> None:
        """Print text to output."""
        print(text, file=self.output)

    def _print_progress(
        self,
        message: str,
        step: Optional[int] = None,
        percentage: Optional[float] = None
    ) -> None:
        """Print progress update."""
        if not self.verbose:
            return

        parts = []

        if step is not None:
            parts.append(f"[{step}/{self._total_steps}]")

        if percentage is not None:
            parts.append(f"{percentage:.0f}%")

        if self.show_progress_bar and percentage is not None:
            bar = self._create_progress_bar(percentage)
            parts.append(bar)

        if message:
            parts.append(message)

        self._print(" ".join(parts))

    def _create_progress_bar(self, percentage: float, width: int = 20) -> str:
        """Create a text progress bar."""
        filled = int(width * percentage / 100)
        empty = width - filled
        return f"[{'=' * filled}{' ' * empty}]"

    def _get_percentage(self) -> float:
        """Get current percentage."""
        if self._total_steps <= 0:
            return 0.0
        return self._current_step / self._total_steps * 100


class QuietProgressReporter(ProgressReporter):
    """Progress reporter that suppresses output."""

    def __init__(self):
        """Initialize quiet reporter."""
        super().__init__(verbose=False, show_progress_bar=False)

    def _print(self, text: str) -> None:
        """Suppress all output."""
        pass


class JSONProgressReporter(ProgressReporter):
    """Progress reporter that outputs JSON events."""

    def __init__(self, output: Optional[TextIO] = None):
        """Initialize JSON reporter."""
        super().__init__(output=output, verbose=False, show_progress_bar=False)

    def _emit_event(self, event: ProgressEvent) -> None:
        """Emit event as JSON."""
        super()._emit_event(event)
        import json
        print(json.dumps(event.to_dict()), file=self.output)
