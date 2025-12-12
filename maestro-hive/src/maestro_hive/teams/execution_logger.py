#!/usr/bin/env python3
"""
Configurable File Logging for Independent Execution
MD-3058: Part of EPIC MD-3089 - Core Platform Stability & Tooling

This module provides configurable file logging for team_execution_v2 to enable:
- Independent execution tracking without console output
- Structured JSON logging for machine parsing
- Log rotation to prevent disk space issues
- Execution ID correlation across distributed components

Design Decisions (ADR):
- Uses Python's built-in logging with RotatingFileHandler for reliability
- Supports both JSON and human-readable formats
- Defaults to /tmp for stateless deployments but configurable for persistent logging
- Thread-safe for concurrent persona execution
"""

import os
import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass, field, asdict
from enum import Enum


class LogFormat(Enum):
    """Supported log output formats."""
    JSON = "json"
    TEXT = "text"
    STRUCTURED = "structured"


class LogLevel(Enum):
    """Log levels matching Python logging module."""
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


@dataclass
class LogConfig:
    """
    Configuration for execution logging.

    Attributes:
        enabled: Whether file logging is enabled
        log_dir: Directory for log files (default: /tmp/maestro-logs)
        log_format: Output format (json, text, or structured)
        log_level: Minimum log level to capture
        max_bytes: Maximum size per log file before rotation
        backup_count: Number of rotated log files to keep
        include_execution_id: Include execution ID in each log entry
        include_timestamp: Include ISO timestamp in each log entry
        include_persona: Include persona name in each log entry
    """
    enabled: bool = True
    log_dir: str = "/tmp/maestro-logs"
    log_format: LogFormat = LogFormat.JSON
    log_level: LogLevel = LogLevel.INFO
    max_bytes: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    include_execution_id: bool = True
    include_timestamp: bool = True
    include_persona: bool = True

    @classmethod
    def from_env(cls) -> 'LogConfig':
        """
        Create LogConfig from environment variables.

        Environment variables:
            MAESTRO_LOG_ENABLED: true/false
            MAESTRO_LOG_DIR: directory path
            MAESTRO_LOG_FORMAT: json/text/structured
            MAESTRO_LOG_LEVEL: debug/info/warning/error/critical
            MAESTRO_LOG_MAX_BYTES: max file size
            MAESTRO_LOG_BACKUP_COUNT: rotation count
        """
        enabled = os.environ.get('MAESTRO_LOG_ENABLED', 'true').lower() == 'true'
        log_dir = os.environ.get('MAESTRO_LOG_DIR', '/tmp/maestro-logs')

        format_str = os.environ.get('MAESTRO_LOG_FORMAT', 'json').lower()
        try:
            log_format = LogFormat(format_str)
        except ValueError:
            log_format = LogFormat.JSON

        level_str = os.environ.get('MAESTRO_LOG_LEVEL', 'info').upper()
        try:
            log_level = LogLevel[level_str]
        except KeyError:
            log_level = LogLevel.INFO

        max_bytes = int(os.environ.get('MAESTRO_LOG_MAX_BYTES', 10 * 1024 * 1024))
        backup_count = int(os.environ.get('MAESTRO_LOG_BACKUP_COUNT', 5))

        return cls(
            enabled=enabled,
            log_dir=log_dir,
            log_format=log_format,
            log_level=log_level,
            max_bytes=max_bytes,
            backup_count=backup_count
        )


class JSONFormatter(logging.Formatter):
    """JSON log formatter for machine-readable output."""

    def __init__(self, execution_id: Optional[str] = None, persona_name: Optional[str] = None):
        super().__init__()
        self.execution_id = execution_id
        self.persona_name = persona_name

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }

        if self.execution_id:
            log_entry['execution_id'] = self.execution_id

        if self.persona_name:
            log_entry['persona'] = self.persona_name

        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)

        # Add any extra fields
        if hasattr(record, 'extra_data') and record.extra_data:
            log_entry['data'] = record.extra_data

        return json.dumps(log_entry)


class StructuredFormatter(logging.Formatter):
    """Structured text formatter for human-readable output with key=value pairs."""

    def __init__(self, execution_id: Optional[str] = None, persona_name: Optional[str] = None):
        super().__init__()
        self.execution_id = execution_id
        self.persona_name = persona_name

    def format(self, record: logging.LogRecord) -> str:
        parts = [
            f"ts={datetime.utcnow().isoformat()}Z",
            f"level={record.levelname}",
            f"logger={record.name}",
        ]

        if self.execution_id:
            parts.append(f"execution_id={self.execution_id}")

        if self.persona_name:
            parts.append(f"persona={self.persona_name}")

        parts.append(f"msg=\"{record.getMessage()}\"")

        if record.exc_info:
            parts.append(f"exception=\"{self.formatException(record.exc_info)}\"")

        return ' '.join(parts)


class ExecutionLogger:
    """
    Configurable file logger for team execution.

    Provides structured logging with support for:
    - Execution ID correlation
    - Persona-specific logging
    - Multiple output formats
    - Automatic log rotation

    Example usage:
        >>> config = LogConfig.from_env()
        >>> logger = ExecutionLogger(config, execution_id="exec-123")
        >>> logger.info("Starting execution", extra={"phase": "init"})
        >>> logger.with_persona("backend_developer").info("Processing task")
    """

    def __init__(
        self,
        config: Optional[LogConfig] = None,
        execution_id: Optional[str] = None,
        persona_name: Optional[str] = None
    ):
        """
        Initialize the execution logger.

        Args:
            config: Log configuration (defaults to LogConfig.from_env())
            execution_id: Unique execution identifier for correlation
            persona_name: Name of the persona using this logger
        """
        self.config = config or LogConfig.from_env()
        self.execution_id = execution_id
        self.persona_name = persona_name
        self._logger: Optional[logging.Logger] = None
        self._file_handler: Optional[RotatingFileHandler] = None

        if self.config.enabled:
            self._setup_logger()

    def _setup_logger(self) -> None:
        """Set up the logging infrastructure."""
        # Create log directory if needed
        log_dir = Path(self.config.log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)

        # Create logger with unique name
        logger_name = f"maestro.execution.{self.execution_id or 'default'}"
        if self.persona_name:
            logger_name += f".{self.persona_name}"

        self._logger = logging.getLogger(logger_name)
        self._logger.setLevel(self.config.log_level.value)

        # Prevent propagation to root logger
        self._logger.propagate = False

        # Clear any existing handlers
        self._logger.handlers.clear()

        # Create log file path
        timestamp = datetime.utcnow().strftime('%Y%m%d')
        exec_suffix = f"_{self.execution_id}" if self.execution_id else ""
        persona_suffix = f"_{self.persona_name}" if self.persona_name else ""
        log_file = log_dir / f"execution{exec_suffix}{persona_suffix}_{timestamp}.log"

        # Create rotating file handler
        self._file_handler = RotatingFileHandler(
            log_file,
            maxBytes=self.config.max_bytes,
            backupCount=self.config.backup_count,
            encoding='utf-8'
        )
        self._file_handler.setLevel(self.config.log_level.value)

        # Set formatter based on config
        if self.config.log_format == LogFormat.JSON:
            formatter = JSONFormatter(self.execution_id, self.persona_name)
        elif self.config.log_format == LogFormat.STRUCTURED:
            formatter = StructuredFormatter(self.execution_id, self.persona_name)
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )

        self._file_handler.setFormatter(formatter)
        self._logger.addHandler(self._file_handler)

    def with_persona(self, persona_name: str) -> 'ExecutionLogger':
        """
        Create a new logger instance with a specific persona name.

        Args:
            persona_name: Name of the persona

        Returns:
            New ExecutionLogger instance with persona context
        """
        return ExecutionLogger(
            config=self.config,
            execution_id=self.execution_id,
            persona_name=persona_name
        )

    def with_execution_id(self, execution_id: str) -> 'ExecutionLogger':
        """
        Create a new logger instance with a specific execution ID.

        Args:
            execution_id: Unique execution identifier

        Returns:
            New ExecutionLogger instance with execution ID context
        """
        return ExecutionLogger(
            config=self.config,
            execution_id=execution_id,
            persona_name=self.persona_name
        )

    def _log(self, level: int, msg: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Internal log method."""
        if not self.config.enabled or not self._logger:
            return

        if extra:
            record = self._logger.makeRecord(
                self._logger.name, level, '', 0, msg, (), None
            )
            record.extra_data = extra
            self._logger.handle(record)
        else:
            self._logger.log(level, msg)

    def debug(self, msg: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log a debug message."""
        self._log(logging.DEBUG, msg, extra)

    def info(self, msg: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log an info message."""
        self._log(logging.INFO, msg, extra)

    def warning(self, msg: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log a warning message."""
        self._log(logging.WARNING, msg, extra)

    def error(self, msg: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log an error message."""
        self._log(logging.ERROR, msg, extra)

    def critical(self, msg: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log a critical message."""
        self._log(logging.CRITICAL, msg, extra)

    def log_phase_start(self, phase_name: str, phase_number: int) -> None:
        """Log the start of an execution phase."""
        self.info(f"Starting phase {phase_number}: {phase_name}", extra={
            'event': 'phase_start',
            'phase_name': phase_name,
            'phase_number': phase_number
        })

    def log_phase_complete(self, phase_name: str, phase_number: int, success: bool, duration_ms: int) -> None:
        """Log the completion of an execution phase."""
        self.info(f"Completed phase {phase_number}: {phase_name}", extra={
            'event': 'phase_complete',
            'phase_name': phase_name,
            'phase_number': phase_number,
            'success': success,
            'duration_ms': duration_ms
        })

    def log_contract_execution(
        self,
        contract_type: str,
        persona_name: str,
        success: bool,
        output_summary: Optional[str] = None
    ) -> None:
        """Log contract execution result."""
        self.info(f"Contract executed: {contract_type} by {persona_name}", extra={
            'event': 'contract_execution',
            'contract_type': contract_type,
            'persona': persona_name,
            'success': success,
            'output_summary': output_summary
        })

    def log_quality_score(self, score: float, breakdown: Optional[Dict[str, float]] = None) -> None:
        """Log quality score result."""
        self.info(f"Quality score: {score}", extra={
            'event': 'quality_score',
            'score': score,
            'breakdown': breakdown
        })

    def close(self) -> None:
        """Close the logger and release resources."""
        if self._file_handler:
            self._file_handler.close()
            if self._logger:
                self._logger.removeHandler(self._file_handler)


# Module-level default logger factory
_default_config: Optional[LogConfig] = None


def get_execution_logger(
    execution_id: Optional[str] = None,
    persona_name: Optional[str] = None,
    config: Optional[LogConfig] = None
) -> ExecutionLogger:
    """
    Get an execution logger instance.

    Args:
        execution_id: Unique execution identifier
        persona_name: Name of the persona using this logger
        config: Log configuration (uses environment defaults if not provided)

    Returns:
        Configured ExecutionLogger instance
    """
    global _default_config

    if config:
        _default_config = config
    elif _default_config is None:
        _default_config = LogConfig.from_env()

    return ExecutionLogger(
        config=_default_config,
        execution_id=execution_id,
        persona_name=persona_name
    )
