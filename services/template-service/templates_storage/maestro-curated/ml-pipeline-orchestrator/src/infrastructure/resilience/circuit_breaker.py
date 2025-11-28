"""Circuit Breaker pattern implementation.

Prevents cascading failures by opening circuit after repeated failures.
Per ADR-006 resilience requirements.
"""

import asyncio
import time
from enum import Enum
from typing import Callable, TypeVar, Any
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failures detected, blocking requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open"""
    pass


class CircuitBreaker:
    """Circuit breaker implementation with configurable thresholds.

    Args:
        failure_threshold: Number of failures before opening circuit
        success_threshold: Number of successes in half-open before closing
        timeout: Seconds to wait before attempting reset (half-open)
        name: Circuit breaker identifier for logging/metrics
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout: int = 60,
        name: str = "default"
    ):
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout = timeout
        self.name = name

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self._lock = asyncio.Lock()

    async def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute function with circuit breaker protection.

        Args:
            func: Async function to execute
            *args, **kwargs: Arguments to pass to function

        Returns:
            Result from function

        Raises:
            CircuitBreakerOpenError: If circuit is open
            Any exception from the function call
        """
        async with self._lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    logger.info(f"Circuit breaker '{self.name}': Attempting reset (HALF_OPEN)")
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                else:
                    raise CircuitBreakerOpenError(
                        f"Circuit breaker '{self.name}' is OPEN. "
                        f"Wait {self._time_until_retry():.1f}s before retry"
                    )

        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except Exception as e:
            await self._on_failure()
            raise

    async def _on_success(self):
        """Handle successful call"""
        async with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                logger.debug(
                    f"Circuit breaker '{self.name}': Success in HALF_OPEN "
                    f"({self.success_count}/{self.success_threshold})"
                )

                if self.success_count >= self.success_threshold:
                    logger.info(f"Circuit breaker '{self.name}': Closing circuit (recovered)")
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    self.success_count = 0

            elif self.state == CircuitState.CLOSED:
                # Reset failure count on success
                self.failure_count = 0

    async def _on_failure(self):
        """Handle failed call"""
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.state == CircuitState.HALF_OPEN:
                logger.warning(
                    f"Circuit breaker '{self.name}': Failure in HALF_OPEN, opening circuit"
                )
                self.state = CircuitState.OPEN
                self.success_count = 0

            elif self.state == CircuitState.CLOSED:
                if self.failure_count >= self.failure_threshold:
                    logger.error(
                        f"Circuit breaker '{self.name}': Opening circuit "
                        f"(failures: {self.failure_count}/{self.failure_threshold})"
                    )
                    self.state = CircuitState.OPEN

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if self.last_failure_time is None:
            return True
        return time.time() - self.last_failure_time >= self.timeout

    def _time_until_retry(self) -> float:
        """Calculate seconds until retry allowed"""
        if self.last_failure_time is None:
            return 0.0
        elapsed = time.time() - self.last_failure_time
        return max(0.0, self.timeout - elapsed)

    def get_state(self) -> CircuitState:
        """Get current circuit state"""
        return self.state

    def reset(self):
        """Manually reset circuit breaker"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        logger.info(f"Circuit breaker '{self.name}': Manual reset")
