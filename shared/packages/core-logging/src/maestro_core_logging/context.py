"""
Logging context management for maintaining request/correlation IDs and other contextual information.
"""

import threading
from contextlib import contextmanager
from typing import Any, Dict, Optional
from dataclasses import dataclass, field, asdict
import uuid


@dataclass
class LogContext:
    """
    Container for logging context information.

    This class holds contextual information that should be included
    in all log entries within a request or operation scope.
    """
    request_id: Optional[str] = None
    correlation_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    operation: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def new_request(
        cls,
        request_id: str = None,
        correlation_id: str = None,
        **kwargs
    ) -> "LogContext":
        """
        Create a new request context with generated IDs.

        Args:
            request_id: Request identifier (generated if not provided)
            correlation_id: Correlation identifier (generated if not provided)
            **kwargs: Additional context fields

        Returns:
            New LogContext instance
        """
        return cls(
            request_id=request_id or str(uuid.uuid4()),
            correlation_id=correlation_id or str(uuid.uuid4()),
            **kwargs
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary, excluding None values."""
        data = asdict(self)
        return {k: v for k, v in data.items() if v is not None}

    def update(self, **kwargs) -> "LogContext":
        """Update context with new values."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                self.extra[key] = value
        return self


# Thread-local storage for context
_context_storage = threading.local()


def set_context(context: LogContext) -> None:
    """
    Set the current logging context for the thread.

    Args:
        context: LogContext to set
    """
    _context_storage.context = context


def get_context() -> Optional[LogContext]:
    """
    Get the current logging context for the thread.

    Returns:
        Current LogContext or None if not set
    """
    return getattr(_context_storage, 'context', None)


def clear_context() -> None:
    """Clear the current logging context for the thread."""
    if hasattr(_context_storage, 'context'):
        delattr(_context_storage, 'context')


def update_context(**kwargs) -> None:
    """
    Update the current context with new values.

    Args:
        **kwargs: Values to update in the context
    """
    context = get_context()
    if context is None:
        context = LogContext()
        set_context(context)
    context.update(**kwargs)


@contextmanager
def log_context(context: LogContext = None, **kwargs):
    """
    Context manager for temporarily setting logging context.

    Args:
        context: LogContext to set (if None, creates new one)
        **kwargs: Values to set in the context

    Example:
        with log_context(request_id="123", user_id="456"):
            logger.info("Processing request")
            # All logs within this block will include request_id and user_id
    """
    if context is None:
        context = LogContext(**kwargs)
    elif kwargs:
        context = LogContext(**context.to_dict(), **kwargs)

    previous_context = get_context()
    try:
        set_context(context)
        yield context
    finally:
        if previous_context is not None:
            set_context(previous_context)
        else:
            clear_context()


@contextmanager
def request_context(
    request_id: str = None,
    correlation_id: str = None,
    **kwargs
):
    """
    Context manager for request-scoped logging context.

    Args:
        request_id: Request identifier (generated if not provided)
        correlation_id: Correlation identifier (generated if not provided)
        **kwargs: Additional context fields

    Example:
        with request_context(user_id="123") as ctx:
            logger.info("Request started")
            process_request()
            logger.info("Request completed")
    """
    context = LogContext.new_request(
        request_id=request_id,
        correlation_id=correlation_id,
        **kwargs
    )

    with log_context(context) as ctx:
        yield ctx


# Backwards compatibility
LogContext.get_current = staticmethod(get_context)