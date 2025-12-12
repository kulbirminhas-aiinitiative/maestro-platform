"""
Unified Execution Configuration

EPIC: MD-3091 - Unified Execution Foundation
AC-4: Two-level retry operational

Centralized configuration for the unified execution module.
Combines settings from all three legacy executor implementations.
"""

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class RecoveryStrategy(Enum):
    """Strategy for recovering from failures."""

    RETRY_SAME = "retry_same"  # Retry with same parameters
    RETRY_WITH_BACKOFF = "retry_with_backoff"  # Retry with exponential backoff
    REFLECT_AND_RETRY = "reflect_and_retry"  # Analyze error, modify approach
    ESCALATE = "escalate"  # Escalate to Level 2 / human
    SKIP = "skip"  # Skip and continue


class ErrorCategory(Enum):
    """Categories of errors for routing recovery."""

    SYNTAX = "SYNTAX"  # Python syntax errors
    TEST_FAILURE = "TEST_FAILURE"  # Test execution failures
    ACC_VIOLATION = "ACC_VIOLATION"  # Architectural constraint violation
    BDV_VIOLATION = "BDV_VIOLATION"  # Behavior contract violation
    TIMEOUT = "TIMEOUT"  # Execution timeout
    API_ERROR = "API_ERROR"  # External API failure
    RESOURCE_ERROR = "RESOURCE_ERROR"  # Resource exhaustion
    UNKNOWN = "UNKNOWN"  # Unclassified error


@dataclass
class Level1Config:
    """
    Level 1 (Internal) Retry Configuration.

    Used by PersonaExecutor for immediate, fast retries
    with self-healing capabilities.
    """

    max_attempts: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 5.0
    backoff_multiplier: float = 1.5
    enable_self_healing: bool = True
    enable_syntax_validation: bool = True
    recovery_strategy: RecoveryStrategy = RecoveryStrategy.REFLECT_AND_RETRY


@dataclass
class Level2Config:
    """
    Level 2 (External) Retry Configuration.

    Used by SafetyRetryWrapper for broader recovery
    with circuit breaker and JIRA escalation.
    """

    max_attempts: int = 2
    base_delay_seconds: float = 5.0
    max_delay_seconds: float = 60.0
    backoff_multiplier: float = 2.0
    circuit_breaker_threshold: int = 5
    circuit_breaker_cooldown_seconds: int = 300
    enable_jira_escalation: bool = True
    recovery_strategy: RecoveryStrategy = RecoveryStrategy.ESCALATE


@dataclass
class StateConfig:
    """
    State Persistence Configuration.

    AC-1: State persists to /var/maestro/state by default
    AC-2: Process restart auto-resumes from checkpoint
    """

    state_dir: str = "/var/maestro/state"
    checkpoint_dir: str = "/var/maestro/checkpoints"
    enable_persistence: bool = True
    auto_checkpoint_interval_seconds: int = 60
    verify_checksum_on_load: bool = True
    max_checkpoints_per_workflow: int = 10


@dataclass
class TokenConfig:
    """Token Budget Configuration."""

    max_tokens_per_persona: int = 100000
    max_tokens_per_execution: int = 500000
    track_usage: bool = True
    enforce_budget: bool = True


@dataclass
class ExecutionConfig:
    """
    Complete Execution Configuration.

    Combines all settings for the unified execution module.
    Can be overridden via environment variables.
    """

    level1: Level1Config = field(default_factory=Level1Config)
    level2: Level2Config = field(default_factory=Level2Config)
    state: StateConfig = field(default_factory=StateConfig)
    tokens: TokenConfig = field(default_factory=TokenConfig)

    # Global settings
    timeout_seconds: float = 300.0
    capture_metrics: bool = True
    log_level: str = "INFO"

    # JIRA integration
    jira_project_key: str = "MD"
    jira_base_url: str = "https://fifth9.atlassian.net"

    def __post_init__(self):
        """Apply environment variable overrides."""
        self._apply_env_overrides()

    def _apply_env_overrides(self):
        """Override settings from environment variables."""
        # State configuration
        if env_state_dir := os.environ.get("MAESTRO_STATE_DIR"):
            self.state.state_dir = env_state_dir
        if env_checkpoint_dir := os.environ.get("MAESTRO_CHECKPOINT_DIR"):
            self.state.checkpoint_dir = env_checkpoint_dir

        # Level 1 retry
        if env_l1_attempts := os.environ.get("MAESTRO_L1_MAX_ATTEMPTS"):
            self.level1.max_attempts = int(env_l1_attempts)

        # Level 2 retry
        if env_l2_attempts := os.environ.get("MAESTRO_L2_MAX_ATTEMPTS"):
            self.level2.max_attempts = int(env_l2_attempts)

        # Token limits
        if env_token_limit := os.environ.get("MAESTRO_TOKEN_LIMIT"):
            self.tokens.max_tokens_per_persona = int(env_token_limit)

        # JIRA settings
        if env_jira_url := os.environ.get("JIRA_BASE_URL"):
            self.jira_base_url = env_jira_url
        if env_jira_project := os.environ.get("JIRA_PROJECT_KEY"):
            self.jira_project_key = env_jira_project

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "level1": {
                "max_attempts": self.level1.max_attempts,
                "base_delay_seconds": self.level1.base_delay_seconds,
                "max_delay_seconds": self.level1.max_delay_seconds,
                "backoff_multiplier": self.level1.backoff_multiplier,
                "enable_self_healing": self.level1.enable_self_healing,
                "enable_syntax_validation": self.level1.enable_syntax_validation,
                "recovery_strategy": self.level1.recovery_strategy.value,
            },
            "level2": {
                "max_attempts": self.level2.max_attempts,
                "base_delay_seconds": self.level2.base_delay_seconds,
                "max_delay_seconds": self.level2.max_delay_seconds,
                "backoff_multiplier": self.level2.backoff_multiplier,
                "circuit_breaker_threshold": self.level2.circuit_breaker_threshold,
                "circuit_breaker_cooldown_seconds": self.level2.circuit_breaker_cooldown_seconds,
                "enable_jira_escalation": self.level2.enable_jira_escalation,
                "recovery_strategy": self.level2.recovery_strategy.value,
            },
            "state": {
                "state_dir": self.state.state_dir,
                "checkpoint_dir": self.state.checkpoint_dir,
                "enable_persistence": self.state.enable_persistence,
                "auto_checkpoint_interval_seconds": self.state.auto_checkpoint_interval_seconds,
                "verify_checksum_on_load": self.state.verify_checksum_on_load,
            },
            "tokens": {
                "max_tokens_per_persona": self.tokens.max_tokens_per_persona,
                "max_tokens_per_execution": self.tokens.max_tokens_per_execution,
                "track_usage": self.tokens.track_usage,
                "enforce_budget": self.tokens.enforce_budget,
            },
            "timeout_seconds": self.timeout_seconds,
            "capture_metrics": self.capture_metrics,
            "jira_project_key": self.jira_project_key,
            "jira_base_url": self.jira_base_url,
        }


# Default configuration singleton
_default_config: Optional[ExecutionConfig] = None


def get_execution_config() -> ExecutionConfig:
    """Get the default execution configuration."""
    global _default_config
    if _default_config is None:
        _default_config = ExecutionConfig()
    return _default_config


def reset_execution_config() -> None:
    """Reset the default configuration (for testing)."""
    global _default_config
    _default_config = None
