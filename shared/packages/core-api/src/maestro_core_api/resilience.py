"""
Resilience patterns for UTCP services - Circuit breakers, retries, fallbacks.

This module provides enterprise-grade resilience patterns including:
- Circuit breakers with intelligent recovery
- Retry policies with exponential backoff
- Fallback service selection
- Health-based routing
- Request deduplication
"""

import asyncio
import hashlib
import time
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from maestro_core_logging import get_logger

logger = get_logger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5  # Failures before opening
    success_threshold: int = 2  # Successes to close from half-open
    timeout: int = 60  # Seconds before trying half-open
    half_open_max_calls: int = 3  # Max calls in half-open state

    # Advanced settings
    failure_rate_threshold: float = 0.5  # 50% failure rate
    slow_call_duration_threshold: float = 5.0  # Seconds
    slow_call_rate_threshold: float = 0.5  # 50% slow calls


@dataclass
class CircuitBreakerStats:
    """Circuit breaker statistics."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    slow_calls: int = 0
    rejected_calls: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    state_changes: List[Dict[str, Any]] = field(default_factory=list)


class CircuitBreaker:
    """
    Circuit breaker pattern implementation with intelligent recovery.

    Prevents cascading failures by stopping requests to failing services
    and allowing time for recovery.

    Example:
        >>> breaker = CircuitBreaker("my-service")
        >>>
        >>> async with breaker:
        >>>     result = await call_service()
    """

    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ):
        """
        Initialize circuit breaker.

        Args:
            name: Service/circuit identifier
            config: Circuit breaker configuration
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.stats = CircuitBreakerStats()
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.half_open_calls = 0

        logger.info(
            "Circuit breaker initialized",
            name=name,
            failure_threshold=self.config.failure_threshold
        )

    async def __aenter__(self):
        """Enter circuit breaker context."""
        await self._check_state()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit circuit breaker context."""
        if exc_type is None:
            await self._record_success()
        else:
            await self._record_failure()
        return False

    async def _check_state(self):
        """Check and update circuit state."""
        if self.state == CircuitState.OPEN:
            # Check if timeout has passed
            if self.last_failure_time:
                elapsed = time.time() - self.last_failure_time
                if elapsed >= self.config.timeout:
                    await self._transition_to_half_open()
                else:
                    self.stats.rejected_calls += 1
                    raise CircuitBreakerOpenError(
                        f"Circuit breaker '{self.name}' is OPEN. "
                        f"Retry in {self.config.timeout - elapsed:.1f}s"
                    )
            else:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker '{self.name}' is OPEN"
                )

        elif self.state == CircuitState.HALF_OPEN:
            # Limit calls in half-open state
            if self.half_open_calls >= self.config.half_open_max_calls:
                self.stats.rejected_calls += 1
                raise CircuitBreakerOpenError(
                    f"Circuit breaker '{self.name}' is HALF_OPEN "
                    f"and at max capacity"
                )
            self.half_open_calls += 1

    async def _record_success(self):
        """Record successful call."""
        self.stats.total_calls += 1
        self.stats.successful_calls += 1
        self.stats.last_success_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            logger.info(
                "Circuit breaker success in half-open",
                name=self.name,
                success_count=self.success_count,
                threshold=self.config.success_threshold
            )

            if self.success_count >= self.config.success_threshold:
                await self._transition_to_closed()

        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.failure_count = 0

    async def _record_failure(self):
        """Record failed call."""
        self.stats.total_calls += 1
        self.stats.failed_calls += 1
        self.stats.last_failure_time = time.time()
        self.last_failure_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            # Any failure in half-open goes back to open
            await self._transition_to_open()

        elif self.state == CircuitState.CLOSED:
            self.failure_count += 1
            logger.warning(
                "Circuit breaker failure recorded",
                name=self.name,
                failure_count=self.failure_count,
                threshold=self.config.failure_threshold
            )

            if self.failure_count >= self.config.failure_threshold:
                await self._transition_to_open()

    async def _transition_to_open(self):
        """Transition to OPEN state."""
        old_state = self.state
        self.state = CircuitState.OPEN
        self.half_open_calls = 0

        self.stats.state_changes.append({
            "from": old_state,
            "to": CircuitState.OPEN,
            "timestamp": datetime.utcnow().isoformat(),
            "reason": f"Failure threshold exceeded ({self.failure_count})"
        })

        logger.error(
            "Circuit breaker opened",
            name=self.name,
            from_state=old_state,
            failure_count=self.failure_count
        )

    async def _transition_to_half_open(self):
        """Transition to HALF_OPEN state."""
        old_state = self.state
        self.state = CircuitState.HALF_OPEN
        self.success_count = 0
        self.half_open_calls = 0

        self.stats.state_changes.append({
            "from": old_state,
            "to": CircuitState.HALF_OPEN,
            "timestamp": datetime.utcnow().isoformat(),
            "reason": "Timeout elapsed, testing recovery"
        })

        logger.info(
            "Circuit breaker half-opened",
            name=self.name,
            from_state=old_state
        )

    async def _transition_to_closed(self):
        """Transition to CLOSED state."""
        old_state = self.state
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.half_open_calls = 0

        self.stats.state_changes.append({
            "from": old_state,
            "to": CircuitState.CLOSED,
            "timestamp": datetime.utcnow().isoformat(),
            "reason": "Success threshold reached, circuit recovered"
        })

        logger.info(
            "Circuit breaker closed (recovered)",
            name=self.name,
            from_state=old_state
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics."""
        return {
            "name": self.name,
            "state": self.state,
            "total_calls": self.stats.total_calls,
            "successful_calls": self.stats.successful_calls,
            "failed_calls": self.stats.failed_calls,
            "rejected_calls": self.stats.rejected_calls,
            "success_rate": (
                self.stats.successful_calls / self.stats.total_calls
                if self.stats.total_calls > 0 else 0
            ),
            "state_changes": self.stats.state_changes[-10:],  # Last 10 changes
        }


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


class ResilienceManager:
    """
    Manages circuit breakers and resilience policies for UTCP services.

    Provides centralized resilience management with:
    - Per-service circuit breakers
    - Intelligent retry policies
    - Fallback service selection
    - Health-based routing

    Example:
        >>> manager = ResilienceManager()
        >>>
        >>> # Call with resilience
        >>> result = await manager.call_with_resilience(
        >>>     "workflow-engine",
        >>>     call_service_func,
        >>>     fallback_services=["workflow-engine-v2"]
        >>> )
    """

    def __init__(self):
        """Initialize resilience manager."""
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.request_cache: Dict[str, Any] = {}
        self.in_flight_requests: Dict[str, asyncio.Future] = {}

        logger.info("Resilience manager initialized")

    def get_circuit_breaker(
        self,
        service_name: str,
        config: Optional[CircuitBreakerConfig] = None
    ) -> CircuitBreaker:
        """
        Get or create circuit breaker for service.

        Args:
            service_name: Service identifier
            config: Optional custom configuration

        Returns:
            CircuitBreaker instance
        """
        if service_name not in self.circuit_breakers:
            self.circuit_breakers[service_name] = CircuitBreaker(
                service_name,
                config
            )

        return self.circuit_breakers[service_name]

    async def call_with_resilience(
        self,
        service_name: str,
        call_func: Callable,
        *args,
        fallback_services: Optional[List[str]] = None,
        retry_config: Optional[Dict[str, Any]] = None,
        enable_deduplication: bool = True,
        **kwargs
    ) -> Any:
        """
        Call service with full resilience patterns.

        Features:
        - Circuit breaker protection
        - Automatic retries with exponential backoff
        - Request deduplication
        - Fallback service selection

        Args:
            service_name: Primary service to call
            call_func: Async function to execute
            *args: Positional arguments for call_func
            fallback_services: List of fallback service names
            retry_config: Custom retry configuration
            enable_deduplication: Enable request deduplication
            **kwargs: Keyword arguments for call_func

        Returns:
            Result from service call

        Raises:
            CircuitBreakerOpenError: If circuit is open and no fallbacks
            Exception: If all attempts fail
        """
        # Request deduplication
        if enable_deduplication:
            request_key = self._get_request_key(service_name, args, kwargs)

            # Check if identical request is in-flight
            if request_key in self.in_flight_requests:
                logger.debug(
                    "Request deduplicated (in-flight)",
                    service=service_name,
                    request_key=request_key
                )
                return await self.in_flight_requests[request_key]

            # Create future for this request
            future = asyncio.Future()
            self.in_flight_requests[request_key] = future

        try:
            # Try primary service
            result = await self._call_with_breaker_and_retry(
                service_name,
                call_func,
                *args,
                retry_config=retry_config,
                **kwargs
            )

            if enable_deduplication:
                future.set_result(result)

            return result

        except (CircuitBreakerOpenError, Exception) as e:
            logger.warning(
                "Primary service call failed",
                service=service_name,
                error=str(e)
            )

            # Try fallback services
            if fallback_services:
                for fallback in fallback_services:
                    try:
                        logger.info(
                            "Trying fallback service",
                            primary=service_name,
                            fallback=fallback
                        )

                        result = await self._call_with_breaker_and_retry(
                            fallback,
                            call_func,
                            *args,
                            retry_config=retry_config,
                            **kwargs
                        )

                        if enable_deduplication:
                            future.set_result(result)

                        return result

                    except Exception as fallback_error:
                        logger.warning(
                            "Fallback service failed",
                            fallback=fallback,
                            error=str(fallback_error)
                        )
                        continue

            # All attempts failed
            if enable_deduplication:
                future.set_exception(e)

            raise

        finally:
            # Cleanup in-flight tracking
            if enable_deduplication and request_key in self.in_flight_requests:
                del self.in_flight_requests[request_key]

    async def _call_with_breaker_and_retry(
        self,
        service_name: str,
        call_func: Callable,
        *args,
        retry_config: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Any:
        """Call service with circuit breaker and retry logic."""
        breaker = self.get_circuit_breaker(service_name)

        # Default retry configuration
        default_retry_config = {
            "stop": stop_after_attempt(3),
            "wait": wait_exponential(multiplier=1, min=2, max=10),
            "retry": retry_if_exception_type((ConnectionError, TimeoutError)),
            "before_sleep": before_sleep_log(logger, "WARNING"),
        }

        if retry_config:
            default_retry_config.update(retry_config)

        # Create retry decorator
        retry_decorator = retry(**default_retry_config)
        retryable_func = retry_decorator(call_func)

        # Call with circuit breaker
        async with breaker:
            start_time = time.time()
            result = await retryable_func(*args, **kwargs)
            duration = time.time() - start_time

            # Track slow calls
            if duration > breaker.config.slow_call_duration_threshold:
                breaker.stats.slow_calls += 1
                logger.warning(
                    "Slow call detected",
                    service=service_name,
                    duration=duration
                )

            return result

    def _get_request_key(
        self,
        service_name: str,
        args: tuple,
        kwargs: dict
    ) -> str:
        """Generate unique key for request deduplication."""
        key_data = f"{service_name}:{args}:{sorted(kwargs.items())}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all circuit breakers."""
        return {
            name: breaker.get_stats()
            for name, breaker in self.circuit_breakers.items()
        }

    def reset_circuit_breaker(self, service_name: str):
        """Manually reset a circuit breaker."""
        if service_name in self.circuit_breakers:
            breaker = self.circuit_breakers[service_name]
            breaker.state = CircuitState.CLOSED
            breaker.failure_count = 0
            breaker.success_count = 0

            logger.info("Circuit breaker manually reset", service=service_name)