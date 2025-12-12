#!/usr/bin/env python3
"""
Tests for Execution Logger
MD-3058: Part of EPIC MD-3089 - Core Platform Stability & Tooling
"""

import os
import json
import pytest
import tempfile
import logging
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import the module under test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from maestro_hive.teams.execution_logger import (
    LogConfig,
    LogFormat,
    LogLevel,
    ExecutionLogger,
    JSONFormatter,
    StructuredFormatter,
    get_execution_logger,
)


class TestLogConfig:
    """Test suite for LogConfig class."""

    def test_default_config(self):
        """Test default configuration values."""
        config = LogConfig()

        assert config.enabled is True
        assert config.log_dir == "/tmp/maestro-logs"
        assert config.log_format == LogFormat.JSON
        assert config.log_level == LogLevel.INFO
        assert config.max_bytes == 10 * 1024 * 1024
        assert config.backup_count == 5

    def test_config_from_env_default(self):
        """Test configuration from environment with defaults."""
        with patch.dict(os.environ, {}, clear=True):
            config = LogConfig.from_env()

        assert config.enabled is True
        assert config.log_format == LogFormat.JSON

    def test_config_from_env_custom(self):
        """Test configuration from custom environment variables."""
        env = {
            'MAESTRO_LOG_ENABLED': 'false',
            'MAESTRO_LOG_DIR': '/custom/logs',
            'MAESTRO_LOG_FORMAT': 'text',
            'MAESTRO_LOG_LEVEL': 'DEBUG',
            'MAESTRO_LOG_MAX_BYTES': '5242880',
            'MAESTRO_LOG_BACKUP_COUNT': '3',
        }

        with patch.dict(os.environ, env, clear=False):
            config = LogConfig.from_env()

        assert config.enabled is False
        assert config.log_dir == '/custom/logs'
        assert config.log_format == LogFormat.TEXT
        assert config.log_level == LogLevel.DEBUG
        assert config.max_bytes == 5242880
        assert config.backup_count == 3

    def test_config_from_env_invalid_format(self):
        """Test configuration handles invalid format gracefully."""
        env = {'MAESTRO_LOG_FORMAT': 'invalid'}

        with patch.dict(os.environ, env, clear=False):
            config = LogConfig.from_env()

        # Should fallback to JSON
        assert config.log_format == LogFormat.JSON

    def test_config_from_env_invalid_level(self):
        """Test configuration handles invalid level gracefully."""
        env = {'MAESTRO_LOG_LEVEL': 'INVALID'}

        with patch.dict(os.environ, env, clear=False):
            config = LogConfig.from_env()

        # Should fallback to INFO
        assert config.log_level == LogLevel.INFO


class TestJSONFormatter:
    """Test suite for JSONFormatter class."""

    def test_format_basic_message(self):
        """Test basic message formatting."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='',
            lineno=0,
            msg='Test message',
            args=(),
            exc_info=None
        )

        result = formatter.format(record)
        parsed = json.loads(result)

        assert parsed['message'] == 'Test message'
        assert parsed['level'] == 'INFO'
        assert parsed['logger'] == 'test'
        assert 'timestamp' in parsed

    def test_format_with_execution_id(self):
        """Test formatting includes execution ID."""
        formatter = JSONFormatter(execution_id='exec-123')
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='',
            lineno=0,
            msg='Test message',
            args=(),
            exc_info=None
        )

        result = formatter.format(record)
        parsed = json.loads(result)

        assert parsed['execution_id'] == 'exec-123'

    def test_format_with_persona(self):
        """Test formatting includes persona name."""
        formatter = JSONFormatter(persona_name='backend_developer')
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='',
            lineno=0,
            msg='Test message',
            args=(),
            exc_info=None
        )

        result = formatter.format(record)
        parsed = json.loads(result)

        assert parsed['persona'] == 'backend_developer'


class TestStructuredFormatter:
    """Test suite for StructuredFormatter class."""

    def test_format_basic_message(self):
        """Test basic structured message formatting."""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='',
            lineno=0,
            msg='Test message',
            args=(),
            exc_info=None
        )

        result = formatter.format(record)

        assert 'ts=' in result
        assert 'level=INFO' in result
        assert 'logger=test' in result
        assert 'msg="Test message"' in result


class TestExecutionLogger:
    """Test suite for ExecutionLogger class."""

    def test_logger_initialization(self):
        """Test logger initializes correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = LogConfig(log_dir=tmpdir)
            logger = ExecutionLogger(config=config, execution_id='exec-123')

            assert logger.config.enabled is True
            assert logger.execution_id == 'exec-123'

    def test_logger_disabled(self):
        """Test logger when disabled."""
        config = LogConfig(enabled=False)
        logger = ExecutionLogger(config=config)

        # Should not raise even though logging is disabled
        logger.info("Test message")

    def test_logger_with_persona(self):
        """Test logger with persona context."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = LogConfig(log_dir=tmpdir)
            logger = ExecutionLogger(config=config, execution_id='exec-123')

            persona_logger = logger.with_persona('backend_developer')

            assert persona_logger.persona_name == 'backend_developer'
            assert persona_logger.execution_id == 'exec-123'

    def test_logger_log_levels(self):
        """Test all log levels work."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = LogConfig(log_dir=tmpdir, log_level=LogLevel.DEBUG)
            logger = ExecutionLogger(config=config, execution_id='exec-123')

            # All these should work without error
            logger.debug("Debug message")
            logger.info("Info message")
            logger.warning("Warning message")
            logger.error("Error message")
            logger.critical("Critical message")

    def test_log_phase_start(self):
        """Test log_phase_start method."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = LogConfig(log_dir=tmpdir)
            logger = ExecutionLogger(config=config, execution_id='exec-123')

            # Should not raise
            logger.log_phase_start("Understanding", 1)

    def test_log_phase_complete(self):
        """Test log_phase_complete method."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = LogConfig(log_dir=tmpdir)
            logger = ExecutionLogger(config=config, execution_id='exec-123')

            # Should not raise
            logger.log_phase_complete("Understanding", 1, True, 5000)

    def test_log_contract_execution(self):
        """Test log_contract_execution method."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = LogConfig(log_dir=tmpdir)
            logger = ExecutionLogger(config=config, execution_id='exec-123')

            # Should not raise
            logger.log_contract_execution(
                contract_type="implementation",
                persona_name="backend_developer",
                success=True,
                output_summary="Created 5 files"
            )

    def test_log_quality_score(self):
        """Test log_quality_score method."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = LogConfig(log_dir=tmpdir)
            logger = ExecutionLogger(config=config, execution_id='exec-123')

            # Should not raise
            logger.log_quality_score(
                score=95.5,
                breakdown={"documentation": 15, "implementation": 25}
            )

    def test_logger_creates_directory(self):
        """Test that logger creates log directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            new_dir = os.path.join(tmpdir, "subdir", "logs")
            config = LogConfig(log_dir=new_dir)

            logger = ExecutionLogger(config=config, execution_id='exec-123')

            assert os.path.exists(new_dir)

    def test_logger_close(self):
        """Test logger close method."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = LogConfig(log_dir=tmpdir)
            logger = ExecutionLogger(config=config, execution_id='exec-123')

            # Should not raise
            logger.close()


class TestGetExecutionLogger:
    """Test suite for get_execution_logger factory function."""

    def test_get_execution_logger_default(self):
        """Test getting logger with defaults."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = LogConfig(log_dir=tmpdir)
            logger = get_execution_logger(config=config)

            assert isinstance(logger, ExecutionLogger)

    def test_get_execution_logger_with_id(self):
        """Test getting logger with execution ID."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = LogConfig(log_dir=tmpdir)
            logger = get_execution_logger(
                execution_id='exec-123',
                config=config
            )

            assert logger.execution_id == 'exec-123'

    def test_get_execution_logger_with_persona(self):
        """Test getting logger with persona name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = LogConfig(log_dir=tmpdir)
            logger = get_execution_logger(
                persona_name='qa_engineer',
                config=config
            )

            assert logger.persona_name == 'qa_engineer'


class TestLogFileCreation:
    """Test log file creation and rotation."""

    def test_log_file_created(self):
        """Test that log file is created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = LogConfig(log_dir=tmpdir)
            logger = ExecutionLogger(config=config, execution_id='exec-123')

            logger.info("Test message")

            # Check that log file was created
            log_files = list(Path(tmpdir).glob('*.log'))
            assert len(log_files) >= 1

    def test_json_format_in_file(self):
        """Test that JSON format is written to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = LogConfig(log_dir=tmpdir, log_format=LogFormat.JSON)
            logger = ExecutionLogger(config=config, execution_id='exec-123')

            logger.info("Test message")
            logger.close()

            # Read log file and verify JSON
            log_files = list(Path(tmpdir).glob('*.log'))
            assert len(log_files) >= 1

            with open(log_files[0], 'r') as f:
                content = f.read()
                # Should be valid JSON lines
                for line in content.strip().split('\n'):
                    if line:
                        json.loads(line)  # Should not raise


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
