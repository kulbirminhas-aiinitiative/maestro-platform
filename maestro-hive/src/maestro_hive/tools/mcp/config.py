"""
Configuration for MCP Integration

EPIC: MD-2565
AC-4: Error handling and retry logic
AC-5: Tool result caching where appropriate

Provides configuration classes for MCP tool invocation.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any
import os


class RetryStrategy(str, Enum):
    """Retry backoff strategies."""
    NONE = "none"
    FIXED = "fixed"
    EXPONENTIAL = "exponential"
    LINEAR = "linear"


@dataclass
class RetryPolicy:
    """
    Retry policy configuration (AC-4).

    Defines how failed tool invocations should be retried.
    """
    max_retries: int = 3
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    base_delay_ms: int = 1000
    max_delay_ms: int = 30000
    jitter: bool = True
    retryable_errors: List[str] = field(default_factory=lambda: [
        "timeout",
        "rate_limit",
        "service_unavailable",
        "connection_error",
    ])

    def get_delay_ms(self, attempt: int) -> int:
        """Calculate delay for given attempt number."""
        if self.strategy == RetryStrategy.NONE:
            return 0
        elif self.strategy == RetryStrategy.FIXED:
            delay = self.base_delay_ms
        elif self.strategy == RetryStrategy.LINEAR:
            delay = self.base_delay_ms * attempt
        else:  # EXPONENTIAL
            delay = self.base_delay_ms * (2 ** (attempt - 1))

        # Apply max cap
        delay = min(delay, self.max_delay_ms)

        # Apply jitter if enabled (±25%)
        if self.jitter:
            import random
            jitter_range = delay * 0.25
            delay = int(delay + random.uniform(-jitter_range, jitter_range))

        return max(0, delay)

    def is_retryable(self, error_code: str) -> bool:
        """Check if error is retryable."""
        return error_code.lower() in [e.lower() for e in self.retryable_errors]


@dataclass
class CacheConfig:
    """
    Cache configuration (AC-5).

    Defines caching behavior for tool results.
    """
    enabled: bool = True
    default_ttl_seconds: int = 300
    max_entries: int = 1000
    max_entry_size_bytes: int = 1024 * 1024  # 1MB
    tool_ttls: Dict[str, int] = field(default_factory=dict)

    def get_ttl(self, tool_name: str) -> int:
        """Get TTL for a specific tool."""
        return self.tool_ttls.get(tool_name, self.default_ttl_seconds)


@dataclass
class ProviderConfig:
    """Configuration for a specific LLM provider."""
    name: str
    enabled: bool = True
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    timeout_seconds: int = 30
    max_concurrent: int = 10
    headers: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        """Load API key from environment if not provided."""
        if self.api_key is None:
            env_key = f"{self.name.upper()}_API_KEY"
            self.api_key = os.environ.get(env_key)


@dataclass
class MCPConfig:
    """
    Main configuration for MCP integration.

    Centralizes all configuration for the MCP tool framework.
    """
    # Retry configuration (AC-4)
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)

    # Cache configuration (AC-5)
    cache: CacheConfig = field(default_factory=CacheConfig)

    # Provider configurations (AC-2)
    providers: Dict[str, ProviderConfig] = field(default_factory=dict)

    # Global settings
    default_timeout_seconds: int = 30
    max_concurrent_invocations: int = 50
    stream_chunk_size: int = 1024
    enable_metrics: bool = True
    enable_logging: bool = True
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "MCPConfig":
        """Create configuration from environment variables."""
        config = cls()

        # Override from environment
        if os.environ.get("MCP_MAX_RETRIES"):
            config.retry_policy.max_retries = int(os.environ["MCP_MAX_RETRIES"])

        if os.environ.get("MCP_CACHE_ENABLED"):
            config.cache.enabled = os.environ["MCP_CACHE_ENABLED"].lower() == "true"

        if os.environ.get("MCP_CACHE_TTL"):
            config.cache.default_ttl_seconds = int(os.environ["MCP_CACHE_TTL"])

        if os.environ.get("MCP_DEFAULT_TIMEOUT"):
            config.default_timeout_seconds = int(os.environ["MCP_DEFAULT_TIMEOUT"])

        if os.environ.get("MCP_MAX_CONCURRENT"):
            config.max_concurrent_invocations = int(os.environ["MCP_MAX_CONCURRENT"])

        if os.environ.get("MCP_LOG_LEVEL"):
            config.log_level = os.environ["MCP_LOG_LEVEL"]

        # Auto-configure providers
        if os.environ.get("ANTHROPIC_API_KEY"):
            config.providers["claude"] = ProviderConfig(
                name="claude",
                api_key=os.environ["ANTHROPIC_API_KEY"],
            )

        if os.environ.get("OPENAI_API_KEY"):
            config.providers["openai"] = ProviderConfig(
                name="openai",
                api_key=os.environ["OPENAI_API_KEY"],
            )

        return config

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (for serialization)."""
        return {
            "retry_policy": {
                "max_retries": self.retry_policy.max_retries,
                "strategy": self.retry_policy.strategy.value,
                "base_delay_ms": self.retry_policy.base_delay_ms,
                "max_delay_ms": self.retry_policy.max_delay_ms,
                "jitter": self.retry_policy.jitter,
            },
            "cache": {
                "enabled": self.cache.enabled,
                "default_ttl_seconds": self.cache.default_ttl_seconds,
                "max_entries": self.cache.max_entries,
            },
            "providers": {
                name: {"name": p.name, "enabled": p.enabled}
                for name, p in self.providers.items()
            },
            "default_timeout_seconds": self.default_timeout_seconds,
            "max_concurrent_invocations": self.max_concurrent_invocations,
            "enable_metrics": self.enable_metrics,
            "enable_logging": self.enable_logging,
            "log_level": self.log_level,
        }
