"""
Tests for Unified Execution Configuration

EPIC: MD-3091 - Unified Execution Foundation
AC-1: State persists to /var/maestro/state by default
"""

import os
import pytest
from unittest.mock import patch

from maestro_hive.unified_execution import (
    ExecutionConfig,
    Level1Config,
    Level2Config,
    StateConfig,
    TokenConfig,
    RecoveryStrategy,
    ErrorCategory,
    get_execution_config,
    reset_execution_config,
)


class TestDefaultConfiguration:
    """Tests for default configuration values."""

    def test_default_state_dir(self):
        """Test AC-1: Default state directory is /var/maestro/state."""
        config = ExecutionConfig()
        assert config.state.state_dir == "/var/maestro/state"

    def test_default_checkpoint_dir(self):
        """Test default checkpoint directory."""
        config = ExecutionConfig()
        assert config.state.checkpoint_dir == "/var/maestro/checkpoints"

    def test_default_level1_config(self):
        """Test default Level 1 configuration."""
        config = ExecutionConfig()
        assert config.level1.max_attempts == 3
        assert config.level1.base_delay_seconds == 1.0
        assert config.level1.max_delay_seconds == 5.0
        assert config.level1.enable_self_healing is True
        assert config.level1.enable_syntax_validation is True

    def test_default_level2_config(self):
        """Test default Level 2 configuration."""
        config = ExecutionConfig()
        assert config.level2.max_attempts == 2
        assert config.level2.base_delay_seconds == 5.0
        assert config.level2.max_delay_seconds == 60.0
        assert config.level2.circuit_breaker_threshold == 5
        assert config.level2.enable_jira_escalation is True

    def test_default_token_config(self):
        """Test default token configuration."""
        config = ExecutionConfig()
        assert config.tokens.max_tokens_per_persona == 100000
        assert config.tokens.max_tokens_per_execution == 500000
        assert config.tokens.track_usage is True
        assert config.tokens.enforce_budget is True


class TestEnvironmentOverrides:
    """Tests for environment variable overrides."""

    def test_state_dir_override(self):
        """Test MAESTRO_STATE_DIR environment override."""
        with patch.dict(os.environ, {"MAESTRO_STATE_DIR": "/custom/state"}):
            reset_execution_config()
            config = get_execution_config()
            assert config.state.state_dir == "/custom/state"
        reset_execution_config()

    def test_checkpoint_dir_override(self):
        """Test MAESTRO_CHECKPOINT_DIR environment override."""
        with patch.dict(os.environ, {"MAESTRO_CHECKPOINT_DIR": "/custom/checkpoints"}):
            reset_execution_config()
            config = get_execution_config()
            assert config.state.checkpoint_dir == "/custom/checkpoints"
        reset_execution_config()

    def test_level1_attempts_override(self):
        """Test MAESTRO_L1_MAX_ATTEMPTS environment override."""
        with patch.dict(os.environ, {"MAESTRO_L1_MAX_ATTEMPTS": "5"}):
            reset_execution_config()
            config = get_execution_config()
            assert config.level1.max_attempts == 5
        reset_execution_config()

    def test_level2_attempts_override(self):
        """Test MAESTRO_L2_MAX_ATTEMPTS environment override."""
        with patch.dict(os.environ, {"MAESTRO_L2_MAX_ATTEMPTS": "4"}):
            reset_execution_config()
            config = get_execution_config()
            assert config.level2.max_attempts == 4
        reset_execution_config()

    def test_token_limit_override(self):
        """Test MAESTRO_TOKEN_LIMIT environment override."""
        with patch.dict(os.environ, {"MAESTRO_TOKEN_LIMIT": "50000"}):
            reset_execution_config()
            config = get_execution_config()
            assert config.tokens.max_tokens_per_persona == 50000
        reset_execution_config()


class TestConfigurationSerialization:
    """Tests for configuration serialization."""

    def test_to_dict(self):
        """Test configuration to_dict."""
        config = ExecutionConfig()
        config_dict = config.to_dict()

        assert "level1" in config_dict
        assert "level2" in config_dict
        assert "state" in config_dict
        assert "tokens" in config_dict
        assert config_dict["state"]["state_dir"] == "/var/maestro/state"

    def test_recovery_strategy_serialization(self):
        """Test RecoveryStrategy enum serialization."""
        config = ExecutionConfig()
        config_dict = config.to_dict()

        assert config_dict["level1"]["recovery_strategy"] == "reflect_and_retry"
        assert config_dict["level2"]["recovery_strategy"] == "escalate"


class TestSingletonBehavior:
    """Tests for configuration singleton."""

    def test_get_execution_config_singleton(self):
        """Test get_execution_config returns same instance."""
        reset_execution_config()
        config1 = get_execution_config()
        config2 = get_execution_config()
        assert config1 is config2
        reset_execution_config()

    def test_reset_execution_config(self):
        """Test reset creates new instance."""
        config1 = get_execution_config()
        reset_execution_config()
        config2 = get_execution_config()
        assert config1 is not config2
        reset_execution_config()


class TestEnums:
    """Tests for configuration enums."""

    def test_recovery_strategy_values(self):
        """Test RecoveryStrategy enum values."""
        assert RecoveryStrategy.RETRY_SAME.value == "retry_same"
        assert RecoveryStrategy.RETRY_WITH_BACKOFF.value == "retry_with_backoff"
        assert RecoveryStrategy.REFLECT_AND_RETRY.value == "reflect_and_retry"
        assert RecoveryStrategy.ESCALATE.value == "escalate"
        assert RecoveryStrategy.SKIP.value == "skip"

    def test_error_category_values(self):
        """Test ErrorCategory enum values."""
        assert ErrorCategory.SYNTAX.value == "SYNTAX"
        assert ErrorCategory.TEST_FAILURE.value == "TEST_FAILURE"
        assert ErrorCategory.ACC_VIOLATION.value == "ACC_VIOLATION"
        assert ErrorCategory.TIMEOUT.value == "TIMEOUT"
        assert ErrorCategory.UNKNOWN.value == "UNKNOWN"
