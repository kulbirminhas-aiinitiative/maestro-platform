"""
Custom processors for structured logging.
"""

import inspect
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, MutableMapping
from structlog.typing import Processor

from .config import LoggingConfig


def mask_sensitive_processor(sensitive_fields: List[str]) -> Processor:
    """
    Processor to mask sensitive data in log entries.

    Args:
        sensitive_fields: List of field names to mask

    Returns:
        Processor function
    """
    def processor(
        logger: Any, method_name: str, event_dict: MutableMapping[str, Any]
    ) -> MutableMapping[str, Any]:
        """Mask sensitive fields in the log entry."""
        for key, value in event_dict.items():
            if any(sensitive in key.lower() for sensitive in sensitive_fields):
                if isinstance(value, str) and len(value) > 4:
                    # Show first 2 and last 2 characters
                    event_dict[key] = f"{value[:2]}***{value[-2:]}"
                else:
                    event_dict[key] = "***MASKED***"
        return event_dict

    return processor


def add_service_info_processor(config: LoggingConfig) -> Processor:
    """
    Processor to add service information to log entries.

    Args:
        config: Logging configuration

    Returns:
        Processor function
    """
    def processor(
        logger: Any, method_name: str, event_dict: MutableMapping[str, Any]
    ) -> MutableMapping[str, Any]:
        """Add service information to log entry."""
        event_dict["service"] = config.service_name
        event_dict["environment"] = config.environment
        if config.opentelemetry.service_version != "unknown":
            event_dict["version"] = config.opentelemetry.service_version
        return event_dict

    return processor


def add_timestamp_processor(timestamp_format: str = "iso") -> Processor:
    """
    Processor to add timestamps to log entries.

    Args:
        timestamp_format: Format for timestamps ("iso", "epoch", "custom")

    Returns:
        Processor function
    """
    def processor(
        logger: Any, method_name: str, event_dict: MutableMapping[str, Any]
    ) -> MutableMapping[str, Any]:
        """Add timestamp to log entry."""
        now = datetime.now(timezone.utc)

        if timestamp_format == "iso":
            event_dict["timestamp"] = now.isoformat()
        elif timestamp_format == "epoch":
            event_dict["timestamp"] = now.timestamp()
        else:
            # Default to ISO format
            event_dict["timestamp"] = now.isoformat()

        return event_dict

    return processor


def add_caller_info_processor() -> Processor:
    """
    Processor to add caller information (file, line, function) to log entries.

    Returns:
        Processor function
    """
    def processor(
        logger: Any, method_name: str, event_dict: MutableMapping[str, Any]
    ) -> MutableMapping[str, Any]:
        """Add caller information to log entry."""
        # Get the calling frame (skip internal logging frames)
        frame = inspect.currentframe()
        try:
            # Skip through the logging framework frames
            for _ in range(10):  # Reasonable depth limit
                frame = frame.f_back
                if frame is None:
                    break

                # Look for frames outside the logging library
                filename = frame.f_code.co_filename
                if not any(lib in filename for lib in ['structlog', 'logging', 'maestro_core_logging']):
                    event_dict["caller"] = {
                        "file": filename.split('/')[-1],  # Just the filename
                        "line": frame.f_lineno,
                        "function": frame.f_code.co_name
                    }
                    break
        finally:
            del frame  # Prevent reference cycles

        return event_dict

    return processor


def add_performance_processor() -> Processor:
    """
    Processor to add performance metrics to log entries.

    Returns:
        Processor function
    """
    def processor(
        logger: Any, method_name: str, event_dict: MutableMapping[str, Any]
    ) -> MutableMapping[str, Any]:
        """Add performance metrics if available."""
        import psutil
        import os

        # Add basic performance metrics
        try:
            process = psutil.Process(os.getpid())
            event_dict["performance"] = {
                "memory_usage_mb": round(process.memory_info().rss / 1024 / 1024, 2),
                "cpu_percent": process.cpu_percent(),
                "num_threads": process.num_threads()
            }
        except Exception:
            # Don't fail logging if performance metrics aren't available
            pass

        return event_dict

    return processor


def add_request_id_processor() -> Processor:
    """
    Processor to add request ID to log entries from context.

    Returns:
        Processor function
    """
    def processor(
        logger: Any, method_name: str, event_dict: MutableMapping[str, Any]
    ) -> MutableMapping[str, Any]:
        """Add request ID from context."""
        from .context import LogContext

        context = LogContext.get_current()
        if context and context.request_id:
            event_dict["request_id"] = context.request_id
        if context and context.correlation_id:
            event_dict["correlation_id"] = context.correlation_id

        return event_dict

    return processor


def sanitize_sql_processor() -> Processor:
    """
    Processor to sanitize SQL queries in log entries.

    Returns:
        Processor function
    """
    def processor(
        logger: Any, method_name: str, event_dict: MutableMapping[str, Any]
    ) -> MutableMapping[str, Any]:
        """Sanitize SQL queries by removing sensitive data."""
        for key, value in event_dict.items():
            if isinstance(value, str) and ('sql' in key.lower() or 'query' in key.lower()):
                # Basic SQL sanitization - remove common sensitive patterns
                sanitized = re.sub(
                    r"('.*?'|\".*?\"|VALUES\s*\([^)]*\))",
                    "'***'",
                    value,
                    flags=re.IGNORECASE | re.DOTALL
                )
                event_dict[key] = sanitized

        return event_dict

    return processor


# Registry for custom processors
_custom_processors: Dict[str, Processor] = {
    "performance": add_performance_processor,
    "request_id": add_request_id_processor,
    "sanitize_sql": sanitize_sql_processor,
}


def add_custom_processor(name: str, processor: Processor) -> None:
    """
    Register a custom processor.

    Args:
        name: Name of the processor
        processor: Processor function
    """
    _custom_processors[name] = processor


def get_custom_processor(name: str) -> Processor:
    """
    Get a custom processor by name.

    Args:
        name: Name of the processor

    Returns:
        Processor function

    Raises:
        KeyError: If processor is not found
    """
    return _custom_processors[name]