"""
MAESTRO Core Logging Library

Enterprise-grade structured logging with OpenTelemetry integration.
Follows industry standards used by companies like Stripe, GitLab, and Discord.

Usage:
    from maestro_core_logging import get_logger, configure_logging

    # Configure once at application startup
    configure_logging(
        service_name="my-service",
        environment="production",
        log_level="INFO"
    )

    # Use throughout your application
    logger = get_logger(__name__)
    logger.info("Application started", version="1.0.0")
"""

from .config import LoggingConfig, LogFormat, LogLevel
from .core import get_logger, configure_logging
from .context import LogContext, set_context, clear_context
from .middleware import (
    LoggingMiddleware,
    FastAPILoggingMiddleware,
    FlaskLoggingMiddleware,
    DjangoLoggingMiddleware,
    ASGILoggingMiddleware
)
from .processors import add_custom_processor

__version__ = "1.0.0"
__all__ = [
    "get_logger",
    "configure_logging",
    "LoggingConfig",
    "LogFormat",
    "LogLevel",
    "LogContext",
    "set_context",
    "clear_context",
    "LoggingMiddleware",
    "FastAPILoggingMiddleware",
    "FlaskLoggingMiddleware",
    "DjangoLoggingMiddleware",
    "ASGILoggingMiddleware",
    "add_custom_processor",
]