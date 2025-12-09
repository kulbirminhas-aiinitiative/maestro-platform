"""
Circuit Breaker Pattern Implementation.

Provides fault tolerance by preventing cascading failures.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Callable, Any, Dict, List
from enum import Enum
import functools


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing if recovered


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""
    failure_threshold: int = 5  # Failures before opening
    success_threshold: int = 3  # Successes to close from half-open
    timeout_seconds: int = 30  # Time in open state before half-open
    half_open_max_calls: int = 3  # Max calls in half-open state
    exception_types: tuple = (Exception,)  # Exceptions to count as failures
    exclude_exceptions: tuple = ()  # Exceptions to not count


@dataclass
class CircuitStats:
    """Circuit breaker statistics."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    state_changes: int = 0
    time_in_open: timedelta = field(default_factory=lambda: timedelta(0))


class CircuitBreakerError(Exception):
    """Raised when circuit is open."""

    def __init__(self, circuit_name: str, retry_after: Optional[datetime] = None):
        self.circuit_name = circuit_name
        self.retry_after = retry_after
        message = f"Circuit breaker '{circuit_name}' is open"
        if retry_after:
            message += f", retry after {retry_after.isoformat()}"
        super().__init__(message)


class CircuitBreaker:
    """
    Circuit breaker for fault tolerance.

    Implements the circuit breaker pattern to prevent
    cascading failures and allow systems to recover.

    States:
    - CLOSED: Normal operation, tracking failures
    - OPEN: Failing, rejecting all requests
    - HALF_OPEN: Testing recovery with limited requests
    """

    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
    ):
        """
        Initialize circuit breaker.

        Args:
            name: Circuit breaker name
            config: Configuration
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0
        self._last_failure_time: Optional[datetime] = None
        self._opened_at: Optional[datetime] = None
        self._stats = CircuitStats()
        self._lock = asyncio.Lock()
        self._listeners: List[Callable] = []

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        # Check if should transition from OPEN to HALF_OPEN
        if self._state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._transition_to(CircuitState.HALF_OPEN)
        return self._state

    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)."""
        return self.state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        """Check if circuit is open (rejecting requests)."""
        return self.state == CircuitState.OPEN

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self._opened_at is None:
            return True
        elapsed = datetime.utcnow() - self._opened_at
        return elapsed.total_seconds() >= self.config.timeout_seconds

    def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to new state."""
        old_state = self._state
        self._state = new_state
        self._stats.state_changes += 1

        if new_state == CircuitState.OPEN:
            self._opened_at = datetime.utcnow()
        elif new_state == CircuitState.HALF_OPEN:
            self._half_open_calls = 0
            self._success_count = 0
        elif new_state == CircuitState.CLOSED:
            if self._opened_at:
                self._stats.time_in_open += datetime.utcnow() - self._opened_at
            self._failure_count = 0
            self._opened_at = None

        # Notify listeners
        for listener in self._listeners:
            try:
                listener(self.name, old_state, new_state)
            except Exception:
                pass

    def _record_success(self) -> None:
        """Record successful call."""
        self._stats.total_calls += 1
        self._stats.successful_calls += 1
        self._stats.last_success_time = datetime.utcnow()

        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.config.success_threshold:
                self._transition_to(CircuitState.CLOSED)

    def _record_failure(self) -> None:
        """Record failed call."""
        self._stats.total_calls += 1
        self._stats.failed_calls += 1
        self._failure_count += 1
        self._last_failure_time = datetime.utcnow()
        self._stats.last_failure_time = self._last_failure_time

        if self._state == CircuitState.HALF_OPEN:
            # Any failure in half-open goes back to open
            self._transition_to(CircuitState.OPEN)
        elif self._failure_count >= self.config.failure_threshold:
            self._transition_to(CircuitState.OPEN)

    def _record_rejection(self) -> None:
        """Record rejected call."""
        self._stats.total_calls += 1
        self._stats.rejected_calls += 1

    def _should_allow_call(self) -> bool:
        """Check if call should be allowed."""
        state = self.state  # Triggers state check

        if state == CircuitState.CLOSED:
            return True
        elif state == CircuitState.OPEN:
            return False
        else:  # HALF_OPEN
            if self._half_open_calls < self.config.half_open_max_calls:
                self._half_open_calls += 1
                return True
            return False

    def _is_tracked_exception(self, exc: Exception) -> bool:
        """Check if exception should be tracked as failure."""
        if isinstance(exc, self.config.exclude_exceptions):
            return False
        return isinstance(exc, self.config.exception_types)

    async def call(
        self,
        func: Callable,
        *args,
        **kwargs,
    ) -> Any:
        """
        Execute function with circuit breaker protection.

        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerError: If circuit is open
        """
        async with self._lock:
            if not self._should_allow_call():
                self._record_rejection()
                retry_after = None
                if self._opened_at:
                    retry_after = self._opened_at + timedelta(
                        seconds=self.config.timeout_seconds
                    )
                raise CircuitBreakerError(self.name, retry_after)

        try:
            # Execute function
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            async with self._lock:
                self._record_success()

            return result

        except Exception as e:
            async with self._lock:
                if self._is_tracked_exception(e):
                    self._record_failure()
            raise

    def __call__(self, func: Callable) -> Callable:
        """
        Decorator for protecting functions.

        Usage:
            @circuit_breaker
            async def my_function():
                pass
        """
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await self.call(func, *args, **kwargs)
        return wrapper

    def add_listener(self, listener: Callable[[str, CircuitState, CircuitState], None]) -> None:
        """Add state change listener."""
        self._listeners.append(listener)

    def remove_listener(self, listener: Callable) -> None:
        """Remove state change listener."""
        self._listeners.remove(listener)

    def reset(self) -> None:
        """Manually reset circuit to closed state."""
        self._transition_to(CircuitState.CLOSED)

    def get_stats(self) -> CircuitStats:
        """Get circuit breaker statistics."""
        return self._stats

    def get_status(self) -> Dict[str, Any]:
        """Get circuit breaker status."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "last_failure_time": (
                self._last_failure_time.isoformat()
                if self._last_failure_time else None
            ),
            "opened_at": (
                self._opened_at.isoformat() if self._opened_at else None
            ),
            "stats": {
                "total_calls": self._stats.total_calls,
                "successful_calls": self._stats.successful_calls,
                "failed_calls": self._stats.failed_calls,
                "rejected_calls": self._stats.rejected_calls,
            }
        }


class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers."""

    _instance: Optional["CircuitBreakerRegistry"] = None
    _breakers: Dict[str, CircuitBreaker] = {}

    @classmethod
    def get_instance(cls) -> "CircuitBreakerRegistry":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_or_create(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
    ) -> CircuitBreaker:
        """Get existing or create new circuit breaker."""
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(name, config)
        return self._breakers[name]

    def get(self, name: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker by name."""
        return self._breakers.get(name)

    def list_all(self) -> List[Dict[str, Any]]:
        """Get status of all circuit breakers."""
        return [cb.get_status() for cb in self._breakers.values()]

    def reset_all(self) -> None:
        """Reset all circuit breakers."""
        for cb in self._breakers.values():
            cb.reset()
