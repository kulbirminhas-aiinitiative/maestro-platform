"""
Circuit Breaker Pattern Implementation.

Prevents cascading failures by stopping calls to failing services and allowing
them time to recover.
"""

import asyncio
from enum import Enum
from datetime import datetime, timedelta
from typing import Callable, Any, Optional
import logging

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, block all requests
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


class CircuitBreaker:
    """
    Circuit breaker implementation.

    States:
    - CLOSED: All requests pass through (normal operation)
    - OPEN: All requests fail fast (service is down)
    - HALF_OPEN: Allow test request to check if service recovered

    Args:
        failure_threshold: Number of failures before opening circuit
        success_threshold: Number of successes in HALF_OPEN to close circuit
        timeout: Seconds to wait before attempting reset from OPEN to HALF_OPEN
        name: Name for logging and identification
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout: int = 60,
        name: str = "circuit_breaker",
    ):
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout = timeout
        self.name = name

        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = CircuitState.CLOSED

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.

        Args:
            func: Async function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result from func

        Raises:
            CircuitBreakerOpenError: If circuit is open
            Exception: Original exception from func
        """
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                logger.info(f"Circuit breaker '{self.name}': Attempting reset (HALF_OPEN)")
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
            else:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker '{self.name}' is OPEN. Service unavailable."
                )

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result

        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        """Handle successful request."""
        self.failure_count = 0

        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            logger.debug(
                f"Circuit breaker '{self.name}': Success in HALF_OPEN "
                f"({self.success_count}/{self.success_threshold})"
            )

            if self.success_count >= self.success_threshold:
                logger.info(f"Circuit breaker '{self.name}': Closing circuit (recovered)")
                self.state = CircuitState.CLOSED
                self.success_count = 0

    def _on_failure(self):
        """Handle failed request."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.state == CircuitState.HALF_OPEN:
            # Immediate open on failure during test
            logger.warning(f"Circuit breaker '{self.name}': Failed in HALF_OPEN, reopening")
            self.state = CircuitState.OPEN
            self.success_count = 0

        elif self.failure_count >= self.failure_threshold:
            logger.error(
                f"Circuit breaker '{self.name}': Opening circuit after "
                f"{self.failure_count} failures"
            )
            self.state = CircuitState.OPEN

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to test recovery."""
        if not self.last_failure_time:
            return True

        elapsed = (datetime.now() - self.last_failure_time).total_seconds()
        return elapsed > self.timeout

    def reset(self):
        """Manually reset circuit breaker to CLOSED state."""
        logger.info(f"Circuit breaker '{self.name}': Manual reset")
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None

    @property
    def is_open(self) -> bool:
        """Check if circuit is open."""
        return self.state == CircuitState.OPEN

    @property
    def is_half_open(self) -> bool:
        """Check if circuit is half-open."""
        return self.state == CircuitState.HALF_OPEN

    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed."""
        return self.state == CircuitState.CLOSED
