"""
Core logging functionality with Structlog and OpenTelemetry integration.
"""

import logging
import sys
from typing import Any, Dict, Optional
import structlog
from structlog.typing import Processor
from opentelemetry import trace
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from .config import LoggingConfig, LogFormat, LogLevel
from .processors import (
    mask_sensitive_processor,
    add_service_info_processor,
    add_timestamp_processor,
    add_caller_info_processor
)
from .context import LogContext


# Global configuration instance
_config: Optional[LoggingConfig] = None
_configured: bool = False


def configure_logging(
    service_name: str,
    environment: str = "development",
    log_level: str = "INFO",
    **kwargs
) -> LoggingConfig:
    """
    Configure logging for the entire application.
    Should be called once at application startup.

    Args:
        service_name: Name of the service
        environment: Environment (dev/staging/prod)
        log_level: Minimum log level
        **kwargs: Additional configuration options

    Returns:
        LoggingConfig: The configuration used

    Example:
        configure_logging(
            service_name="user-service",
            environment="production",
            log_level="INFO",
            enable_file=True,
            file_path="/var/log/user-service.log"
        )
    """
    global _config, _configured

    # Create configuration
    config_data = {
        "service_name": service_name,
        "environment": environment,
        "log_level": log_level,
        **kwargs
    }

    # Pass service_name to OpenTelemetry config if enabled
    if config_data.get('enable_otel', kwargs.get('enable_otel', True)):
        if 'opentelemetry' not in config_data:
            config_data['opentelemetry'] = {}
        if isinstance(config_data['opentelemetry'], dict):
            config_data['opentelemetry'].setdefault('service_name', service_name)

    _config = LoggingConfig(**config_data)

    # Configure OpenTelemetry if enabled
    if _config.opentelemetry.enabled:
        _configure_opentelemetry(_config)

    # Build processor chain
    processors = _build_processors(_config)

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, _config.log_level.value)
        ),
        logger_factory=structlog.stdlib.LoggerFactory(),
        context_class=dict,
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    _configure_stdlib_logging(_config)

    _configured = True
    return _config


def get_logger(name: str = None) -> structlog.stdlib.BoundLogger:
    """
    Get a logger instance for the given name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        BoundLogger: Configured logger instance

    Example:
        logger = get_logger(__name__)
        logger.info("User created", user_id=123, email="user@example.com")
    """
    if not _configured:
        raise RuntimeError(
            "Logging not configured. Call configure_logging() first."
        )

    logger = structlog.get_logger(name or "maestro")

    # Add context if available
    context = LogContext.get_current()
    if context:
        logger = logger.bind(**context.to_dict())

    return logger


def _configure_opentelemetry(config: LoggingConfig) -> None:
    """Configure OpenTelemetry for distributed tracing."""
    # Create resource with service information
    resource_attributes = {
        "service.name": config.opentelemetry.service_name,
        "service.version": config.opentelemetry.service_version,
        "service.namespace": config.opentelemetry.service_namespace,
        "deployment.environment": config.environment,
        **config.opentelemetry.resource_attributes
    }

    resource = Resource.create(resource_attributes)

    # Configure tracer provider
    tracer_provider = TracerProvider(resource=resource)

    # Add OTLP exporter if endpoint is configured
    if config.opentelemetry.otlp_endpoint:
        otlp_exporter = OTLPSpanExporter(
            endpoint=config.opentelemetry.otlp_endpoint,
            headers=config.opentelemetry.headers
        )
        span_processor = BatchSpanProcessor(otlp_exporter)
        tracer_provider.add_span_processor(span_processor)

    # Set the tracer provider
    trace.set_tracer_provider(tracer_provider)

    # Instrument logging
    LoggingInstrumentor().instrument(set_logging_format=True)


def _build_processors(config: LoggingConfig) -> list[Processor]:
    """Build the processor chain based on configuration."""
    processors: list[Processor] = []

    # Add service information
    processors.append(add_service_info_processor(config))

    # Add timestamp if enabled
    if config.include_timestamp:
        processors.append(add_timestamp_processor(config.timestamp_format))

    # Add caller information if enabled
    if config.include_caller_info:
        processors.append(add_caller_info_processor())

    # Mask sensitive data if enabled
    if config.mask_sensitive_data:
        processors.append(mask_sensitive_processor(config.sensitive_fields))

    # Add OpenTelemetry trace information
    if config.opentelemetry.enabled:
        # Note: OpenTelemetryProcessor is not available in structlog 24.4.0
        # Skipping for now - trace context will be added via opentelemetry instrumentation
        pass

    # Add format-specific processors
    if config.log_format == LogFormat.JSON:
        processors.extend([
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ])
    elif config.log_format == LogFormat.CONSOLE:
        processors.extend([
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer()
        ])
    elif config.log_format == LogFormat.RICH:
        try:
            from rich.logging import RichHandler
            processors.extend([
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.dev.ConsoleRenderer(colors=True)
            ])
        except ImportError:
            # Fallback to console if rich is not available
            processors.extend([
                structlog.stdlib.filter_by_level,
                structlog.dev.ConsoleRenderer()
            ])

    return processors


def _configure_stdlib_logging(config: LoggingConfig) -> None:
    """Configure Python standard library logging."""
    # Set root logger level
    logging.root.setLevel(getattr(logging, config.log_level.value))

    # Remove existing handlers
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    # Add console handler if enabled
    if config.enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, config.log_level.value))
        logging.root.addHandler(console_handler)

    # Add file handler if enabled
    if config.enable_file and config.file_path:
        from logging.handlers import TimedRotatingFileHandler
        file_handler = TimedRotatingFileHandler(
            config.file_path,
            when='midnight',
            interval=1,
            backupCount=30
        )
        file_handler.setLevel(getattr(logging, config.log_level.value))
        logging.root.addHandler(file_handler)


def get_config() -> Optional[LoggingConfig]:
    """Get the current logging configuration."""
    return _config


def is_configured() -> bool:
    """Check if logging has been configured."""
    return _configured