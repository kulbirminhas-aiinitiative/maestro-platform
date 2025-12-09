"""
Error Resilience Framework for AI Systems
EU AI Act Article 15 Compliance - Error Handling

Provides graceful degradation and fault tolerance for AI operations.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
import functools
import time


class ErrorCategory(Enum):
    """Categories of errors for classification."""
    TRANSIENT = "transient"
    PERMANENT = "permanent"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    VALIDATION = "validation"
    SECURITY = "security"
    MODEL_FAILURE = "model_failure"
    NETWORK = "network"
    TIMEOUT = "timeout"


class ResilienceLevel(Enum):
    """Resilience configuration levels."""
    MINIMAL = "minimal"
    STANDARD = "standard"
    HIGH = "high"
    MAXIMUM = "maximum"


@dataclass
class RetryPolicy:
    """Configuration for retry behavior."""
    max_retries: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    exponential_backoff: bool = True
    jitter: bool = True
    retryable_categories: List[ErrorCategory] = field(default_factory=lambda: [
        ErrorCategory.TRANSIENT,
        ErrorCategory.NETWORK,
        ErrorCategory.TIMEOUT,
    ])

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for a given retry attempt."""
        if self.exponential_backoff:
            delay = self.base_delay_seconds * (2 ** attempt)
        else:
            delay = self.base_delay_seconds

        delay = min(delay, self.max_delay_seconds)

        if self.jitter:
            import random
            delay = delay * (0.5 + random.random())

        return delay

    def should_retry(self, category: ErrorCategory, attempt: int) -> bool:
        """Determine if retry should be attempted."""
        if attempt >= self.max_retries:
            return False
        return category in self.retryable_categories


@dataclass
class CircuitBreaker:
    """Circuit breaker for preventing cascading failures."""
    name: str
    failure_threshold: int = 5
    recovery_timeout_seconds: float = 30.0
    half_open_requests: int = 3

    _failure_count: int = field(default=0, init=False)
    _last_failure_time: Optional[datetime] = field(default=None, init=False)
    _state: str = field(default="closed", init=False)
    _half_open_successes: int = field(default=0, init=False)

    def record_success(self) -> None:
        """Record a successful operation."""
        if self._state == "half_open":
            self._half_open_successes += 1
            if self._half_open_successes >= self.half_open_requests:
                self._state = "closed"
                self._failure_count = 0
                self._half_open_successes = 0
        elif self._state == "closed":
            self._failure_count = max(0, self._failure_count - 1)

    def record_failure(self) -> None:
        """Record a failed operation."""
        self._failure_count += 1
        self._last_failure_time = datetime.utcnow()

        if self._state == "half_open":
            self._state = "open"
            self._half_open_successes = 0
        elif self._failure_count >= self.failure_threshold:
            self._state = "open"

    def can_execute(self) -> bool:
        """Check if operation can be executed."""
        if self._state == "closed":
            return True

        if self._state == "open":
            if self._last_failure_time:
                elapsed = (datetime.utcnow() - self._last_failure_time).total_seconds()
                if elapsed >= self.recovery_timeout_seconds:
                    self._state = "half_open"
                    self._half_open_successes = 0
                    return True
            return False

        return True  # half_open

    @property
    def state(self) -> str:
        """Get current circuit breaker state."""
        return self._state

    def get_status(self) -> Dict[str, Any]:
        """Get detailed circuit breaker status."""
        return {
            "name": self.name,
            "state": self._state,
            "failure_count": self._failure_count,
            "failure_threshold": self.failure_threshold,
            "last_failure": self._last_failure_time.isoformat() if self._last_failure_time else None,
            "recovery_timeout": self.recovery_timeout_seconds,
        }


@dataclass
class ErrorEvent:
    """Represents an error event for tracking."""
    timestamp: datetime
    category: ErrorCategory
    message: str
    context: Dict[str, Any]
    recovered: bool = False
    recovery_action: Optional[str] = None


class ErrorResilienceManager:
    """
    Manages error resilience for AI system operations.

    Provides:
    - Circuit breakers for different subsystems
    - Retry policies with exponential backoff
    - Error categorization and tracking
    - Graceful degradation strategies
    - Recovery suggestions
    """

    def __init__(
        self,
        resilience_level: ResilienceLevel = ResilienceLevel.STANDARD,
        default_retry_policy: Optional[RetryPolicy] = None,
    ):
        self.resilience_level = resilience_level
        self.default_retry_policy = default_retry_policy or self._get_policy_for_level()
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.error_history: List[ErrorEvent] = []
        self._fallback_handlers: Dict[str, Callable] = {}

    def _get_policy_for_level(self) -> RetryPolicy:
        """Get retry policy based on resilience level."""
        policies = {
            ResilienceLevel.MINIMAL: RetryPolicy(max_retries=1, base_delay_seconds=0.5),
            ResilienceLevel.STANDARD: RetryPolicy(max_retries=3, base_delay_seconds=1.0),
            ResilienceLevel.HIGH: RetryPolicy(max_retries=5, base_delay_seconds=1.0),
            ResilienceLevel.MAXIMUM: RetryPolicy(max_retries=10, base_delay_seconds=2.0),
        }
        return policies.get(self.resilience_level, RetryPolicy())

    def get_or_create_circuit_breaker(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
    ) -> CircuitBreaker:
        """Get or create a circuit breaker for a subsystem."""
        if name not in self.circuit_breakers:
            self.circuit_breakers[name] = CircuitBreaker(
                name=name,
                failure_threshold=failure_threshold,
                recovery_timeout_seconds=recovery_timeout,
            )
        return self.circuit_breakers[name]

    def register_fallback(self, operation_name: str, handler: Callable) -> None:
        """Register a fallback handler for an operation."""
        self._fallback_handlers[operation_name] = handler

    def categorize_error(self, error: Exception) -> ErrorCategory:
        """Categorize an error for appropriate handling."""
        error_type = type(error).__name__
        error_msg = str(error).lower()

        if "timeout" in error_msg or "timed out" in error_msg:
            return ErrorCategory.TIMEOUT
        if "connection" in error_msg or "network" in error_msg:
            return ErrorCategory.NETWORK
        if "memory" in error_msg or "resource" in error_msg:
            return ErrorCategory.RESOURCE_EXHAUSTION
        if "validation" in error_msg or "invalid" in error_msg:
            return ErrorCategory.VALIDATION
        if "security" in error_msg or "permission" in error_msg or "unauthorized" in error_msg:
            return ErrorCategory.SECURITY
        if "model" in error_msg or "inference" in error_msg:
            return ErrorCategory.MODEL_FAILURE

        # Transient errors are typically runtime errors that can be retried
        if error_type in ("RuntimeError", "IOError", "OSError"):
            return ErrorCategory.TRANSIENT

        return ErrorCategory.PERMANENT

    def record_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        circuit_breaker_name: Optional[str] = None,
    ) -> ErrorEvent:
        """Record an error event."""
        category = self.categorize_error(error)
        event = ErrorEvent(
            timestamp=datetime.utcnow(),
            category=category,
            message=str(error),
            context=context or {},
        )
        self.error_history.append(event)

        if circuit_breaker_name and circuit_breaker_name in self.circuit_breakers:
            self.circuit_breakers[circuit_breaker_name].record_failure()

        return event

    def execute_with_resilience(
        self,
        operation: Callable,
        operation_name: str,
        *args,
        retry_policy: Optional[RetryPolicy] = None,
        circuit_breaker_name: Optional[str] = None,
        **kwargs,
    ) -> Any:
        """Execute an operation with full resilience support."""
        policy = retry_policy or self.default_retry_policy
        breaker = None

        if circuit_breaker_name:
            breaker = self.get_or_create_circuit_breaker(circuit_breaker_name)
            if not breaker.can_execute():
                # Try fallback if available
                if operation_name in self._fallback_handlers:
                    return self._fallback_handlers[operation_name](*args, **kwargs)
                raise RuntimeError(f"Circuit breaker '{circuit_breaker_name}' is open")

        last_error = None
        for attempt in range(policy.max_retries + 1):
            try:
                result = operation(*args, **kwargs)
                if breaker:
                    breaker.record_success()
                return result
            except Exception as e:
                last_error = e
                category = self.categorize_error(e)
                self.record_error(e, {"attempt": attempt, "operation": operation_name}, circuit_breaker_name)

                if not policy.should_retry(category, attempt):
                    break

                delay = policy.calculate_delay(attempt)
                time.sleep(delay)

        # All retries exhausted, try fallback
        if operation_name in self._fallback_handlers:
            return self._fallback_handlers[operation_name](*args, **kwargs)

        raise last_error

    def resilient(
        self,
        operation_name: str,
        circuit_breaker_name: Optional[str] = None,
        retry_policy: Optional[RetryPolicy] = None,
    ):
        """Decorator for making functions resilient."""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                return self.execute_with_resilience(
                    func,
                    operation_name,
                    *args,
                    retry_policy=retry_policy,
                    circuit_breaker_name=circuit_breaker_name,
                    **kwargs,
                )
            return wrapper
        return decorator

    def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status of the resilience system."""
        recent_errors = [e for e in self.error_history
                        if (datetime.utcnow() - e.timestamp).total_seconds() < 3600]

        error_rates = {}
        for cat in ErrorCategory:
            count = sum(1 for e in recent_errors if e.category == cat)
            error_rates[cat.value] = count

        return {
            "resilience_level": self.resilience_level.value,
            "circuit_breakers": {
                name: cb.get_status() for name, cb in self.circuit_breakers.items()
            },
            "recent_errors_1h": len(recent_errors),
            "error_rates_by_category": error_rates,
            "total_errors_recorded": len(self.error_history),
        }

    def get_recovery_suggestions(self, error: Exception) -> List[str]:
        """Get recovery suggestions for an error."""
        category = self.categorize_error(error)

        suggestions = {
            ErrorCategory.TRANSIENT: [
                "Retry the operation after a short delay",
                "Check system resources and availability",
            ],
            ErrorCategory.PERMANENT: [
                "Review the input parameters",
                "Check logs for detailed error information",
                "Contact support if issue persists",
            ],
            ErrorCategory.RESOURCE_EXHAUSTION: [
                "Scale up system resources",
                "Implement request throttling",
                "Clear caches and temporary files",
            ],
            ErrorCategory.VALIDATION: [
                "Verify input data format and constraints",
                "Check API documentation for requirements",
            ],
            ErrorCategory.SECURITY: [
                "Verify authentication credentials",
                "Check access permissions",
                "Review security policies",
            ],
            ErrorCategory.MODEL_FAILURE: [
                "Check model health and availability",
                "Verify model inputs are within expected ranges",
                "Consider rolling back to previous model version",
            ],
            ErrorCategory.NETWORK: [
                "Check network connectivity",
                "Verify endpoint availability",
                "Review firewall and security group rules",
            ],
            ErrorCategory.TIMEOUT: [
                "Increase timeout thresholds",
                "Optimize operation for faster execution",
                "Check for system bottlenecks",
            ],
        }

        return suggestions.get(category, ["Investigate error details"])
