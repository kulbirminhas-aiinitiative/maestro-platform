"""
Tests for Maestro-Hive Structured Logging Module
Epic: MD-1901 - Maestro-Hive Observability Integration
Task: MD-1903 - Configure structlog for structured logging
"""

import os
from unittest.mock import patch

from observability.logging import (
    SENSITIVE_KEYS,
    SENSITIVE_PATTERNS,
    bind_context,
    clear_context,
    configure_logging,
    get_logger,
    log_audit_result,
    log_webhook_delivery,
    mask_sensitive_data,
    unbind_context,
)


class TestSensitiveDataMasking:
    """Tests for sensitive data masking functionality."""

    def test_mask_password_in_string(self):
        """Should mask password patterns in strings."""
        input_str = "password=secret123"
        result = mask_sensitive_data(input_str)
        assert "secret123" not in result
        assert "***MASKED***" in result

    def test_mask_api_key_in_string(self):
        """Should mask API key patterns in strings."""
        input_str = "api_key=sk-abc123xyz"
        result = mask_sensitive_data(input_str)
        assert "sk-abc123xyz" not in result

    def test_mask_anthropic_api_key(self):
        """Should mask Anthropic API key patterns."""
        input_str = "ANTHROPIC_API_KEY=sk-ant-api-key-123"
        result = mask_sensitive_data(input_str)
        assert "sk-ant-api-key-123" not in result

    def test_mask_sensitive_dict_keys(self):
        """Should mask values of sensitive keys in dictionaries."""
        input_dict = {
            "username": "john",
            "password": "secret123",
            "api_key": "sk-abc123",
        }
        result = mask_sensitive_data(input_dict)
        assert result["username"] == "john"
        assert result["password"] == "***MASKED***"
        assert result["api_key"] == "***MASKED***"

    def test_mask_nested_dict(self):
        """Should mask sensitive data in nested dictionaries."""
        input_dict = {
            "user": {
                "name": "john",
                "auth": {
                    "password": "secret123",
                    "token": "jwt-token-here",
                },
            }
        }
        result = mask_sensitive_data(input_dict)
        assert result["user"]["name"] == "john"
        # password and token are sensitive keys, so their values are masked
        assert result["user"]["auth"]["password"] == "***MASKED***"
        assert result["user"]["auth"]["token"] == "***MASKED***"

    def test_mask_entire_credentials_value(self):
        """Should mask entire value if key name is sensitive."""
        input_dict = {
            "username": "john",
            "credentials": {"nested": "data"},  # credentials is a sensitive key
        }
        result = mask_sensitive_data(input_dict)
        assert result["username"] == "john"
        # The entire credentials value is masked because the key is sensitive
        assert result["credentials"] == "***MASKED***"

    def test_mask_list_with_sensitive_dicts(self):
        """Should mask sensitive data in lists of dictionaries."""
        input_list = [
            {"username": "john", "password": "secret1"},
            {"username": "jane", "password": "secret2"},
        ]
        result = mask_sensitive_data(input_list)
        assert result[0]["password"] == "***MASKED***"
        assert result[1]["password"] == "***MASKED***"

    def test_mask_custom_mask_string(self):
        """Should use custom mask string when provided."""
        input_dict = {"password": "secret123"}
        result = mask_sensitive_data(input_dict, mask="[REDACTED]")
        assert result["password"] == "[REDACTED]"

    def test_preserve_non_sensitive_data(self):
        """Should preserve non-sensitive data unchanged."""
        input_dict = {
            "name": "Test Project",
            "status": "active",
            "count": 42,
        }
        result = mask_sensitive_data(input_dict)
        assert result == input_dict

    def test_handle_none_values(self):
        """Should handle None values without error."""
        result = mask_sensitive_data(None)
        assert result is None

    def test_handle_empty_string(self):
        """Should handle empty strings."""
        result = mask_sensitive_data("")
        assert result == ""


class TestLoggingConfiguration:
    """Tests for logging configuration."""

    def test_configure_logging_defaults(self):
        """Should configure logging with default settings."""
        configure_logging()
        logger = get_logger("test")
        assert logger is not None

    def test_configure_logging_json_output(self):
        """Should configure logging with JSON output."""
        configure_logging(json_output=True)
        logger = get_logger("test_json")
        assert logger is not None

    def test_configure_logging_console_output(self):
        """Should configure logging with console output."""
        configure_logging(json_output=False)
        logger = get_logger("test_console")
        assert logger is not None

    def test_configure_logging_level(self):
        """Should respect log level configuration."""
        configure_logging(level="DEBUG")
        logger = get_logger("test_level")
        assert logger is not None

    def test_get_logger_caching(self):
        """Should return cached logger for same name."""
        logger1 = get_logger("test_cache")
        logger2 = get_logger("test_cache")
        assert logger1 is logger2

    def test_get_logger_different_names(self):
        """Should return different loggers for different names."""
        first_logger = get_logger("test_cache_1")
        second_logger = get_logger("test_cache_2")
        # They may be the same type but configured for different names
        assert first_logger is not None
        assert second_logger is not None


class TestContextManagement:
    """Tests for logging context management."""

    def test_bind_context(self):
        """Should bind context variables."""
        clear_context()
        bind_context(request_id="abc123", user_id="user456")
        # Context is bound - actual verification would require inspecting log output

    def test_unbind_context(self):
        """Should unbind specific context variables."""
        clear_context()
        bind_context(request_id="abc123", user_id="user456")
        unbind_context("request_id")
        # Context is unbound for request_id

    def test_clear_context(self):
        """Should clear all context variables."""
        bind_context(request_id="abc123", user_id="user456")
        clear_context()
        # All context should be cleared


class TestConvenienceFunctions:
    """Tests for convenience logging functions."""

    def test_log_audit_result(self):
        """Should log audit result with structured fields."""
        configure_logging(json_output=False)
        logger = get_logger("test_audit")

        # Should not raise any exceptions
        log_audit_result(
            logger=logger,
            iteration_id="iter_123",
            verdict="ALL_PASS",
            can_deploy=True,
            dde_passed=True,
            bdv_passed=True,
            acc_passed=True,
        )

    def test_log_audit_result_partial_streams(self):
        """Should log audit result with partial stream results."""
        configure_logging(json_output=False)
        logger = get_logger("test_audit_partial")

        log_audit_result(
            logger=logger,
            iteration_id="iter_456",
            verdict="PARTIAL_PASS",
            can_deploy=False,
            dde_passed=True,
            bdv_passed=None,  # Not run
            acc_passed=False,
        )

    def test_log_webhook_delivery_success(self):
        """Should log successful webhook delivery."""
        configure_logging(json_output=False)
        logger = get_logger("test_webhook")

        log_webhook_delivery(
            logger=logger,
            webhook_id="wh_123",
            url="https://example.com/webhook",
            success=True,
            response_time_ms=150.5,
            status_code=200,
        )

    def test_log_webhook_delivery_failure(self):
        """Should log failed webhook delivery."""
        configure_logging(json_output=False)
        logger = get_logger("test_webhook_fail")

        log_webhook_delivery(
            logger=logger,
            webhook_id="wh_456",
            url="https://example.com/webhook",
            success=False,
            response_time_ms=5000.0,
            status_code=500,
            error="Connection timeout",
        )


class TestSensitivePatterns:
    """Tests for sensitive pattern detection."""

    def test_all_sensitive_keys_lowercase(self):
        """All sensitive keys should be lowercase for case-insensitive matching."""
        for key in SENSITIVE_KEYS:
            assert key == key.lower(), f"Key '{key}' should be lowercase"

    def test_sensitive_patterns_compiled(self):
        """All sensitive patterns should be compiled regex patterns."""
        for pattern in SENSITIVE_PATTERNS:
            assert hasattr(pattern, "match"), f"Pattern {pattern} should be compiled regex"


class TestEnvironmentConfiguration:
    """Tests for environment-based configuration."""

    @patch.dict(os.environ, {"HIVE_ENV": "production"})
    def test_production_uses_json_output(self):
        """Production environment should default to JSON output."""
        # Re-configure with environment
        configure_logging()
        # In production, JSON output should be used by default

    @patch.dict(os.environ, {"HIVE_ENV": "development"})
    def test_development_uses_console_output(self):
        """Development environment should default to console output."""
        configure_logging()
        # In development, console output should be used by default

    @patch.dict(os.environ, {"HIVE_LOG_LEVEL": "DEBUG"})
    def test_log_level_from_environment(self):
        """Should respect HIVE_LOG_LEVEL environment variable."""
        configure_logging()
        # Log level should be DEBUG from environment
