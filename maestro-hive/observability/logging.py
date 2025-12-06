"""
Maestro-Hive Structured Logging Module
Epic: MD-1901 - Maestro-Hive Observability Integration
Task: MD-1903 - Configure structlog for structured logging

Provides:
- JSON output in production, colored console in development
- Sensitive data masking
- Request context propagation
- Correlation IDs for distributed tracing
"""

import logging
import os
import re
import sys
from functools import lru_cache
from typing import Any, List, Optional

import structlog
from structlog.processors import JSONRenderer, TimeStamper, add_log_level
from structlog.stdlib import BoundLogger, ProcessorFormatter
from structlog.typing import EventDict, Processor

# =============================================================================
# Sensitive Data Masking
# =============================================================================

# Patterns for sensitive data that should be masked
SENSITIVE_PATTERNS: List[re.Pattern] = [
    re.compile(r"(password|passwd|pwd)[\s]*[=:]\s*['\"]?([^'\"&\s]+)", re.IGNORECASE),
    re.compile(r"(api_key|apikey|api-key)[\s]*[=:]\s*['\"]?([^'\"&\s]+)", re.IGNORECASE),
    re.compile(r"(secret|token)[\s]*[=:]\s*['\"]?([^'\"&\s]+)", re.IGNORECASE),
    re.compile(r"(authorization|bearer)[\s]*[=:]\s*['\"]?([^'\"&\s]+)", re.IGNORECASE),
    re.compile(r"ANTHROPIC_API_KEY[\s]*[=:]\s*['\"]?([^'\"&\s]+)", re.IGNORECASE),
    re.compile(r"(sk-[a-zA-Z0-9-]+)", re.IGNORECASE),  # API key patterns
]

# Keys that should always be masked
SENSITIVE_KEYS: set = {
    "password",
    "passwd",
    "pwd",
    "secret",
    "api_key",
    "apikey",
    "api-key",
    "token",
    "access_token",
    "refresh_token",
    "authorization",
    "bearer",
    "credentials",
    "private_key",
    "anthropic_api_key",
}


def mask_sensitive_data(value: Any, mask: str = "***MASKED***") -> Any:
    """
    Recursively mask sensitive data in values.

    Args:
        value: Value to mask (string, dict, list, or other)
        mask: String to replace sensitive data with

    Returns:
        Masked value
    """
    if isinstance(value, str):
        masked = value
        for pattern in SENSITIVE_PATTERNS:
            masked = pattern.sub(lambda m: f"{m.group(1)}={mask}", masked)
        return masked
    elif isinstance(value, dict):
        return {
            k: mask if k.lower() in SENSITIVE_KEYS else mask_sensitive_data(v, mask)
            for k, v in value.items()
        }
    elif isinstance(value, list):
        return [mask_sensitive_data(item, mask) for item in value]
    return value


def sensitive_data_masking_processor(
    logger: logging.Logger, method_name: str, event_dict: EventDict
) -> EventDict:
    """Structlog processor that masks sensitive data in log events."""
    return mask_sensitive_data(event_dict)


# =============================================================================
# Custom Processors
# =============================================================================


def add_service_context(
    logger: logging.Logger, method_name: str, event_dict: EventDict
) -> EventDict:
    """Add service context to all log events."""
    event_dict["service"] = "maestro-hive"
    event_dict["environment"] = os.getenv("HIVE_ENV", "development")
    return event_dict


def add_correlation_id(
    logger: logging.Logger, method_name: str, event_dict: EventDict
) -> EventDict:
    """Add correlation ID if available in context."""
    # Try to get correlation ID from context (set by request middleware)
    correlation_id = getattr(structlog.contextvars, "get", lambda x, d=None: d)(
        "correlation_id", None
    )
    if correlation_id:
        event_dict["correlation_id"] = correlation_id
    return event_dict


def format_exception(logger: logging.Logger, method_name: str, event_dict: EventDict) -> EventDict:
    """Format exception information for better readability."""
    exc_info = event_dict.pop("exc_info", None)
    if exc_info:
        if isinstance(exc_info, tuple):
            event_dict["exception_type"] = exc_info[0].__name__ if exc_info[0] else None
            event_dict["exception_message"] = str(exc_info[1]) if exc_info[1] else None
        elif exc_info is True:
            import traceback

            event_dict["traceback"] = traceback.format_exc()
    return event_dict


# =============================================================================
# Logging Configuration
# =============================================================================


def get_processors(json_output: bool = False) -> List[Processor]:
    """Get the list of processors based on environment."""
    processors: List[Processor] = [
        structlog.contextvars.merge_contextvars,
        add_log_level,
        add_service_context,
        add_correlation_id,
        sensitive_data_masking_processor,
        format_exception,
        TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if json_output:
        processors.append(JSONRenderer())
    else:
        processors.append(
            structlog.dev.ConsoleRenderer(
                colors=True,
                exception_formatter=structlog.dev.plain_traceback,
            )
        )

    return processors


def configure_logging(
    level: str = "INFO",
    json_output: Optional[bool] = None,
    log_file: Optional[str] = None,
) -> None:
    """
    Configure structured logging for Maestro-Hive.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_output: Force JSON output (default: auto-detect from environment)
        log_file: Optional file path for log output

    Example:
        >>> configure_logging(level="DEBUG", json_output=False)
        >>> logger = get_logger(__name__)
        >>> logger.info("Application started", version="1.0.0")
    """
    # Determine if JSON output should be used
    if json_output is None:
        env = os.getenv("HIVE_ENV", "development").lower()
        json_output = env in ("production", "prod", "staging")

    # Get log level from environment if not specified
    log_level = os.getenv("HIVE_LOG_LEVEL", level).upper()
    numeric_level = getattr(logging, log_level, logging.INFO)

    # Configure structlog
    structlog.configure(
        processors=get_processors(json_output),
        wrapper_class=BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard logging to use structlog
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(numeric_level)

    # Use structlog's ProcessorFormatter for stdlib logging
    formatter = ProcessorFormatter(
        processor=JSONRenderer() if json_output else structlog.dev.ConsoleRenderer(colors=True),
        foreign_pre_chain=[
            structlog.stdlib.add_log_level,
            TimeStamper(fmt="iso"),
        ],
    )
    handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(numeric_level)

    # Add file handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(numeric_level)
        file_formatter = ProcessorFormatter(
            processor=JSONRenderer(),
            foreign_pre_chain=[
                structlog.stdlib.add_log_level,
                TimeStamper(fmt="iso"),
            ],
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

    # Reduce noise from third-party libraries
    for logger_name in ["httpx", "httpcore", "urllib3", "asyncio"]:
        logging.getLogger(logger_name).setLevel(logging.WARNING)


@lru_cache(maxsize=128)
def get_logger(name: str) -> BoundLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured structlog BoundLogger

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Processing request", request_id="abc123")
    """
    return structlog.get_logger(name)


# =============================================================================
# Context Management
# =============================================================================


def bind_context(**kwargs: Any) -> None:
    """
    Bind context variables to all subsequent log calls in the current context.

    Args:
        **kwargs: Key-value pairs to bind to the logging context

    Example:
        >>> bind_context(request_id="abc123", user_id="user456")
        >>> logger.info("Processing")  # Will include request_id and user_id
    """
    structlog.contextvars.bind_contextvars(**kwargs)


def unbind_context(*keys: str) -> None:
    """
    Unbind context variables from the current context.

    Args:
        *keys: Keys to unbind from the logging context
    """
    structlog.contextvars.unbind_contextvars(*keys)


def clear_context() -> None:
    """Clear all bound context variables."""
    structlog.contextvars.clear_contextvars()


# =============================================================================
# Convenience Functions
# =============================================================================


def log_audit_result(
    logger: BoundLogger,
    iteration_id: str,
    verdict: str,
    can_deploy: bool,
    dde_passed: Optional[bool] = None,
    bdv_passed: Optional[bool] = None,
    acc_passed: Optional[bool] = None,
) -> None:
    """
    Log a trimodal audit result with structured fields.

    Args:
        logger: Logger instance
        iteration_id: Execution iteration ID
        verdict: Audit verdict (e.g., ALL_PASS, SYSTEMIC_FAILURE)
        can_deploy: Whether deployment is allowed
        dde_passed: DDE stream result
        bdv_passed: BDV stream result
        acc_passed: ACC stream result
    """
    logger.info(
        "trimodal_audit_complete",
        iteration_id=iteration_id,
        verdict=verdict,
        can_deploy=can_deploy,
        dde_passed=dde_passed,
        bdv_passed=bdv_passed,
        acc_passed=acc_passed,
    )


def log_webhook_delivery(
    logger: BoundLogger,
    webhook_id: str,
    url: str,
    success: bool,
    response_time_ms: Optional[float] = None,
    status_code: Optional[int] = None,
    error: Optional[str] = None,
) -> None:
    """
    Log a webhook delivery attempt with structured fields.

    Args:
        logger: Logger instance
        webhook_id: Webhook configuration ID
        url: Target URL
        success: Whether delivery succeeded
        response_time_ms: Response time in milliseconds
        status_code: HTTP status code
        error: Error message if failed
    """
    log_method = logger.info if success else logger.warning
    log_method(
        "webhook_delivery",
        webhook_id=webhook_id,
        url=url,
        success=success,
        response_time_ms=response_time_ms,
        status_code=status_code,
        error=error,
    )
