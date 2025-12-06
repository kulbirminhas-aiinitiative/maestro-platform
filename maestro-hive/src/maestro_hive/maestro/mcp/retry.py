"""
MCP Retry Policy

Implements AC-4: Error handling and retry logic.

Provides configurable retry strategies for MCP tool execution failures.

Epic: MD-2565
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, Callable, Awaitable, TypeVar, List
from enum import Enum
import asyncio
import logging
import random

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RetryStrategy(str, Enum):
    """Retry strategy types"""
    FIXED = "fixed"           # Fixed delay between retries
    EXPONENTIAL = "exponential"  # Exponential backoff
    LINEAR = "linear"         # Linear increase in delay
    JITTERED = "jittered"     # Exponential with random jitter


class ErrorCategory(str, Enum):
    """Categories of errors for retry decisions"""
    TRANSIENT = "transient"    # Temporary - should retry
    PERMANENT = "permanent"    # Won't resolve - don't retry
    RATE_LIMIT = "rate_limit"  # Rate limited - retry with backoff
    TIMEOUT = "timeout"        # Timeout - may retry
    UNKNOWN = "unknown"        # Unknown - default retry


@dataclass
class RetryConfig:
    """
    Configuration for retry behavior.

    AC-4 Implementation: Configurable retry parameters.
    """
    max_retries: int = 3
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    initial_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    exponential_base: float = 2.0
    jitter_factor: float = 0.1
    retryable_errors: List[str] = field(default_factory=lambda: [
        "timeout", "connection", "rate_limit", "service_unavailable"
    ])
    non_retryable_errors: List[str] = field(default_factory=lambda: [
        "invalid_input", "unauthorized", "not_found", "validation"
    ])

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "max_retries": self.max_retries,
            "strategy": self.strategy.value,
            "initial_delay_seconds": self.initial_delay_seconds,
            "max_delay_seconds": self.max_delay_seconds,
            "exponential_base": self.exponential_base,
            "jitter_factor": self.jitter_factor,
            "retryable_errors": self.retryable_errors,
            "non_retryable_errors": self.non_retryable_errors
        }


@dataclass
class RetryAttempt:
    """Record of a single retry attempt"""
    attempt_number: int
    error: str
    error_category: ErrorCategory
    delay_seconds: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    will_retry: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "attempt_number": self.attempt_number,
            "error": self.error,
            "error_category": self.error_category.value,
            "delay_seconds": self.delay_seconds,
            "timestamp": self.timestamp.isoformat(),
            "will_retry": self.will_retry
        }


@dataclass
class RetryResult:
    """Result of a retry operation"""
    success: bool
    result: Any
    total_attempts: int
    total_time_seconds: float
    attempts: List[RetryAttempt] = field(default_factory=list)
    final_error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "success": self.success,
            "result": self.result,
            "total_attempts": self.total_attempts,
            "total_time_seconds": self.total_time_seconds,
            "attempts": [a.to_dict() for a in self.attempts],
            "final_error": self.final_error
        }


class MCPRetryPolicy:
    """
    Retry policy for MCP tool executions.

    AC-4 Implementation: Handles errors with intelligent retry logic.

    Features:
    - Multiple retry strategies (fixed, exponential, linear, jittered)
    - Error categorization
    - Configurable retry limits
    - Detailed attempt tracking
    """

    def __init__(self, config: Optional[RetryConfig] = None):
        """
        Initialize retry policy.

        Args:
            config: Retry configuration (uses defaults if None)
        """
        self.config = config or RetryConfig()
        self._attempts: List[RetryAttempt] = []

    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay before next retry.

        Args:
            attempt: Current attempt number (1-based)

        Returns:
            Delay in seconds
        """
        strategy = self.config.strategy
        initial = self.config.initial_delay_seconds
        max_delay = self.config.max_delay_seconds

        if strategy == RetryStrategy.FIXED:
            delay = initial

        elif strategy == RetryStrategy.EXPONENTIAL:
            delay = initial * (self.config.exponential_base ** (attempt - 1))

        elif strategy == RetryStrategy.LINEAR:
            delay = initial * attempt

        elif strategy == RetryStrategy.JITTERED:
            base_delay = initial * (self.config.exponential_base ** (attempt - 1))
            jitter = base_delay * self.config.jitter_factor * random.random()
            delay = base_delay + jitter

        else:
            delay = initial

        return min(delay, max_delay)

    def categorize_error(self, error: Exception) -> ErrorCategory:
        """
        Categorize an error for retry decision.

        Args:
            error: The exception that occurred

        Returns:
            ErrorCategory for the error
        """
        error_str = str(error).lower()

        # Check for rate limiting
        if any(kw in error_str for kw in ["rate limit", "429", "too many requests"]):
            return ErrorCategory.RATE_LIMIT

        # Check for timeouts
        if any(kw in error_str for kw in ["timeout", "timed out"]):
            return ErrorCategory.TIMEOUT

        # Check for transient errors
        transient_keywords = [
            "connection", "network", "temporary", "unavailable",
            "503", "502", "504", "retry"
        ]
        if any(kw in error_str for kw in transient_keywords):
            return ErrorCategory.TRANSIENT

        # Check for permanent errors
        permanent_keywords = [
            "invalid", "not found", "404", "401", "403",
            "unauthorized", "forbidden", "validation"
        ]
        if any(kw in error_str for kw in permanent_keywords):
            return ErrorCategory.PERMANENT

        return ErrorCategory.UNKNOWN

    def should_retry(
        self,
        error: Exception,
        attempt: int
    ) -> tuple[bool, ErrorCategory]:
        """
        Determine if retry should be attempted.

        Args:
            error: The exception that occurred
            attempt: Current attempt number

        Returns:
            Tuple of (should_retry, error_category)
        """
        # Check max retries
        if attempt >= self.config.max_retries:
            return False, self.categorize_error(error)

        category = self.categorize_error(error)

        # Don't retry permanent errors
        if category == ErrorCategory.PERMANENT:
            return False, category

        # Always retry rate limits and transient errors
        if category in (ErrorCategory.RATE_LIMIT, ErrorCategory.TRANSIENT):
            return True, category

        # Retry timeouts up to a point
        if category == ErrorCategory.TIMEOUT:
            return attempt < 2, category

        # Default: retry unknown errors once
        return attempt < 1, category

    async def execute_with_retry(
        self,
        func: Callable[[], Awaitable[T]],
        on_retry: Optional[Callable[[RetryAttempt], Awaitable[None]]] = None
    ) -> RetryResult:
        """
        Execute a function with retry logic.

        AC-4 Implementation: Core retry execution.

        Args:
            func: Async function to execute
            on_retry: Optional callback on each retry

        Returns:
            RetryResult with execution details
        """
        start_time = datetime.utcnow()
        self._attempts = []
        attempt = 0
        last_error = None

        while True:
            attempt += 1

            try:
                result = await func()
                return RetryResult(
                    success=True,
                    result=result,
                    total_attempts=attempt,
                    total_time_seconds=(datetime.utcnow() - start_time).total_seconds(),
                    attempts=self._attempts
                )

            except Exception as e:
                last_error = e
                should_retry, category = self.should_retry(e, attempt)
                delay = self.calculate_delay(attempt)

                retry_attempt = RetryAttempt(
                    attempt_number=attempt,
                    error=str(e),
                    error_category=category,
                    delay_seconds=delay,
                    will_retry=should_retry
                )
                self._attempts.append(retry_attempt)

                logger.warning(
                    f"Attempt {attempt} failed: {e} "
                    f"(category: {category.value}, will_retry: {should_retry})"
                )

                if on_retry:
                    await on_retry(retry_attempt)

                if not should_retry:
                    break

                await asyncio.sleep(delay)

        return RetryResult(
            success=False,
            result=None,
            total_attempts=attempt,
            total_time_seconds=(datetime.utcnow() - start_time).total_seconds(),
            attempts=self._attempts,
            final_error=str(last_error) if last_error else "Unknown error"
        )

    def reset(self) -> None:
        """Reset retry state"""
        self._attempts = []

    @property
    def attempts(self) -> List[RetryAttempt]:
        """Get recorded attempts"""
        return self._attempts


def create_retry_policy(
    max_retries: int = 3,
    strategy: str = "exponential",
    initial_delay: float = 1.0
) -> MCPRetryPolicy:
    """
    Factory function to create retry policy.

    Args:
        max_retries: Maximum retry attempts
        strategy: Retry strategy name
        initial_delay: Initial delay in seconds

    Returns:
        Configured MCPRetryPolicy
    """
    config = RetryConfig(
        max_retries=max_retries,
        strategy=RetryStrategy(strategy),
        initial_delay_seconds=initial_delay
    )
    return MCPRetryPolicy(config)
