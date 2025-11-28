"""Circuit Breaker pattern implementation."""

from enum import Enum
from datetime import datetime, timedelta
from typing import Callable, Any, TypeVar
import asyncio
import structlog

logger = structlog.get_logger(__name__)

T = TypeVar('T')


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, blocking requests
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


class CircuitBreaker:
    """
    Circuit breaker for protecting against cascading failures.

    States:
    - CLOSED: All requests pass through (normal operation)
    - OPEN: All requests fail fast (service is down)
    - HALF_OPEN: Allow test request to check if service recovered

    Example:
        >>> breaker = CircuitBreaker(failure_threshold=5, timeout=60)
        >>> result = await breaker.call(some_async_function, arg1, arg2)
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout: int = 60,
        name: str = "default",
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            success_threshold: Number of successes in HALF_OPEN before closing
            timeout: Seconds to wait before attempting reset
            name: Circuit breaker name for logging
        """
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout = timeout
        self.name = name

        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: datetime | None = None
        self.state = CircuitState.CLOSED

        logger.info(
            "circuit_breaker_initialized",
            name=name,
            failure_threshold=failure_threshold,
            success_threshold=success_threshold,
            timeout=timeout
        )

    async def call(self, func: Callable[..., T], *args, **kwargs) -> T:
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
                logger.info("circuit_breaker_half_open", name=self.name)
                self.state = CircuitState.HALF_OPEN
            else:
                logger.warning(
                    "circuit_breaker_blocked",
                    name=self.name,
                    failure_count=self.failure_count,
                    last_failure=self.last_failure_time
                )
                raise CircuitBreakerOpenError(
                    f"Circuit breaker '{self.name}' is OPEN (service unavailable)"
                )

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result

        except Exception as e:
            self._on_failure()
            logger.error(
                "circuit_breaker_failure",
                name=self.name,
                error=str(e),
                failure_count=self.failure_count,
                state=self.state.value
            )
            raise

    def _on_success(self):
        """Handle successful request."""
        self.failure_count = 0

        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            logger.info(
                "circuit_breaker_success_in_half_open",
                name=self.name,
                success_count=self.success_count,
                threshold=self.success_threshold
            )

            if self.success_count >= self.success_threshold:
                logger.info("circuit_breaker_closed", name=self.name)
                self.state = CircuitState.CLOSED
                self.success_count = 0

    def _on_failure(self):
        """Handle failed request."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.failure_count >= self.failure_threshold:
            logger.error(
                "circuit_breaker_opened",
                name=self.name,
                failure_count=self.failure_count,
                threshold=self.failure_threshold
            )
            self.state = CircuitState.OPEN

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if not self.last_failure_time:
            return True

        elapsed = (datetime.now() - self.last_failure_time).total_seconds()
        return elapsed > self.timeout

    def get_state(self) -> CircuitState:
        """Get current circuit breaker state."""
        return self.state

    def reset(self):
        """Manually reset circuit breaker to CLOSED state."""
        logger.info("circuit_breaker_manual_reset", name=self.name)
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None


class CircuitBreakerManager:
    """Manage multiple circuit breakers."""

    def __init__(self):
        self.breakers: dict[str, CircuitBreaker] = {}

    def get_breaker(
        self,
        name: str,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout: int = 60,
    ) -> CircuitBreaker:
        """
        Get or create circuit breaker.

        Args:
            name: Circuit breaker name
            failure_threshold: Number of failures before opening
            success_threshold: Number of successes before closing
            timeout: Seconds before attempting reset

        Returns:
            CircuitBreaker instance
        """
        if name not in self.breakers:
            self.breakers[name] = CircuitBreaker(
                failure_threshold=failure_threshold,
                success_threshold=success_threshold,
                timeout=timeout,
                name=name
            )

        return self.breakers[name]

    def get_all_states(self) -> dict[str, str]:
        """Get states of all circuit breakers."""
        return {
            name: breaker.get_state().value
            for name, breaker in self.breakers.items()
        }


# Global circuit breaker manager
circuit_breaker_manager = CircuitBreakerManager()
