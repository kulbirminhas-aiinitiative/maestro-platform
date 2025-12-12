"""
Standard Library for Workflow Optimization
==========================================

Provides reusable workflow components, patterns, and templates for ensuring
execution excellence through standardized approaches.

EPIC: MD-2961 - Workflow Optimization & Standardization
AC-1: Implement standard_library.py with reusable workflow components and patterns
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Generic, List, Optional, TypeVar, Union
from datetime import datetime
import json
import hashlib

logger = logging.getLogger(__name__)

# Type variables for generic patterns
T = TypeVar('T')
R = TypeVar('R')


class PatternCategory(Enum):
    """Categories for workflow patterns."""
    RESILIENCE = "resilience"
    TRANSFORMATION = "transformation"
    ORCHESTRATION = "orchestration"
    VALIDATION = "validation"
    MONITORING = "monitoring"
    ERROR_HANDLING = "error_handling"
    DATA_FLOW = "data_flow"
    SECURITY = "security"


class PatternComplexity(Enum):
    """Complexity levels for patterns."""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"


@dataclass
class PatternMetadata:
    """Metadata for a workflow pattern."""
    author: str
    created_at: datetime
    version: str
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    usage_count: int = 0
    success_rate: float = 1.0


@dataclass
class ValidationRule:
    """Rule for validating pattern usage."""
    id: str
    name: str
    description: str
    validator: Callable[[Any], bool]
    error_message: str
    severity: str = "error"


@dataclass
class WorkflowPattern:
    """
    A reusable workflow pattern that can be instantiated and composed.

    Patterns encapsulate best practices and common solutions for workflow
    design challenges.
    """
    id: str
    name: str
    description: str
    category: PatternCategory
    complexity: PatternComplexity
    template: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    validation_rules: List[ValidationRule] = field(default_factory=list)
    metadata: Optional[PatternMetadata] = None

    def validate_parameters(self, params: Dict[str, Any]) -> List[str]:
        """Validate parameters against pattern rules."""
        errors = []
        for rule in self.validation_rules:
            if not rule.validator(params):
                errors.append(f"[{rule.severity.upper()}] {rule.name}: {rule.error_message}")
        return errors

    def instantiate(self, params: Dict[str, Any]) -> str:
        """Create an instance of this pattern with given parameters."""
        errors = self.validate_parameters(params)
        if errors:
            raise ValueError(f"Parameter validation failed: {errors}")

        result = self.template
        for key, value in params.items():
            result = result.replace(f"{{{{ {key} }}}}", str(value))
        return result

    def to_dict(self) -> Dict[str, Any]:
        """Convert pattern to dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "complexity": self.complexity.value,
            "template": self.template,
            "parameters": self.parameters,
            "validation_rules": [
                {"id": r.id, "name": r.name, "description": r.description}
                for r in self.validation_rules
            ]
        }


class WorkflowComponent(ABC):
    """Abstract base class for workflow components."""

    @abstractmethod
    def execute(self, context: Dict[str, Any]) -> Any:
        """Execute the component with given context."""
        pass

    @abstractmethod
    def validate(self) -> List[str]:
        """Validate component configuration."""
        pass


@dataclass
class RetryConfig:
    """Configuration for retry pattern."""
    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_exceptions: List[type] = field(default_factory=lambda: [Exception])


class RetryPattern(WorkflowComponent, Generic[T]):
    """
    Exponential backoff retry pattern with jitter.

    Implements retry logic with configurable backoff strategy to handle
    transient failures gracefully.
    """

    def __init__(self, config: RetryConfig, operation: Callable[[], T]):
        self.config = config
        self.operation = operation
        self._attempts = 0
        self._last_error: Optional[Exception] = None

    def execute(self, context: Dict[str, Any]) -> T:
        """Execute operation with retry logic."""
        import time
        import random

        self._attempts = 0
        delay = self.config.initial_delay

        while self._attempts < self.config.max_attempts:
            self._attempts += 1
            try:
                result = self.operation()
                logger.info(f"Retry pattern succeeded on attempt {self._attempts}")
                return result
            except tuple(self.config.retryable_exceptions) as e:
                self._last_error = e
                if self._attempts >= self.config.max_attempts:
                    logger.error(f"Retry pattern exhausted after {self._attempts} attempts")
                    raise

                if self.config.jitter:
                    delay = delay * (1 + random.uniform(-0.1, 0.1))

                logger.warning(
                    f"Attempt {self._attempts} failed, retrying in {delay:.2f}s: {e}"
                )
                time.sleep(delay)
                delay = min(delay * self.config.exponential_base, self.config.max_delay)

        raise RuntimeError("Retry logic error - should not reach here")

    def validate(self) -> List[str]:
        """Validate retry configuration."""
        errors = []
        if self.config.max_attempts < 1:
            errors.append("max_attempts must be at least 1")
        if self.config.initial_delay < 0:
            errors.append("initial_delay must be non-negative")
        if self.config.exponential_base < 1:
            errors.append("exponential_base must be at least 1")
        return errors

    @property
    def attempts(self) -> int:
        return self._attempts

    @property
    def last_error(self) -> Optional[Exception]:
        return self._last_error


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker pattern."""
    failure_threshold: int = 5
    success_threshold: int = 2
    timeout: float = 30.0
    half_open_max_calls: int = 3


class CircuitState(Enum):
    """States for circuit breaker."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerPattern(WorkflowComponent, Generic[T]):
    """
    Circuit breaker pattern for fault tolerance.

    Prevents cascading failures by failing fast when a service is
    experiencing problems.
    """

    def __init__(self, config: CircuitBreakerConfig, operation: Callable[[], T]):
        self.config = config
        self.operation = operation
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0

    @property
    def state(self) -> CircuitState:
        return self._state

    def execute(self, context: Dict[str, Any]) -> T:
        """Execute operation with circuit breaker logic."""
        import time

        if self._state == CircuitState.OPEN:
            if self._last_failure_time and \
               time.time() - self._last_failure_time >= self.config.timeout:
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
                logger.info("Circuit breaker transitioning to HALF_OPEN")
            else:
                raise CircuitOpenError("Circuit breaker is OPEN")

        if self._state == CircuitState.HALF_OPEN:
            if self._half_open_calls >= self.config.half_open_max_calls:
                raise CircuitOpenError("Circuit breaker HALF_OPEN call limit reached")
            self._half_open_calls += 1

        try:
            result = self.operation()
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self) -> None:
        """Handle successful execution."""
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.config.success_threshold:
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._success_count = 0
                logger.info("Circuit breaker transitioning to CLOSED")
        else:
            self._failure_count = 0

    def _on_failure(self) -> None:
        """Handle failed execution."""
        import time

        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.OPEN
            self._success_count = 0
            logger.warning("Circuit breaker transitioning to OPEN from HALF_OPEN")
        elif self._failure_count >= self.config.failure_threshold:
            self._state = CircuitState.OPEN
            logger.warning(
                f"Circuit breaker transitioning to OPEN after {self._failure_count} failures"
            )

    def validate(self) -> List[str]:
        """Validate circuit breaker configuration."""
        errors = []
        if self.config.failure_threshold < 1:
            errors.append("failure_threshold must be at least 1")
        if self.config.success_threshold < 1:
            errors.append("success_threshold must be at least 1")
        if self.config.timeout < 0:
            errors.append("timeout must be non-negative")
        return errors

    def reset(self) -> None:
        """Manually reset the circuit breaker."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None
        logger.info("Circuit breaker manually reset")


class CircuitOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


class TimeoutPattern(WorkflowComponent, Generic[T]):
    """
    Timeout pattern for bounding execution time.

    Ensures operations complete within a specified time limit.
    """

    def __init__(self, timeout_seconds: float, operation: Callable[[], T]):
        self.timeout_seconds = timeout_seconds
        self.operation = operation

    def execute(self, context: Dict[str, Any]) -> T:
        """Execute operation with timeout."""
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self.operation)
            try:
                return future.result(timeout=self.timeout_seconds)
            except concurrent.futures.TimeoutError:
                raise TimeoutError(
                    f"Operation timed out after {self.timeout_seconds} seconds"
                )

    def validate(self) -> List[str]:
        """Validate timeout configuration."""
        errors = []
        if self.timeout_seconds <= 0:
            errors.append("timeout_seconds must be positive")
        return errors


@dataclass
class BulkheadConfig:
    """Configuration for bulkhead pattern."""
    max_concurrent: int = 10
    max_queued: int = 100
    timeout: float = 30.0


class BulkheadPattern(WorkflowComponent, Generic[T]):
    """
    Bulkhead pattern for resource isolation.

    Limits concurrent executions to prevent resource exhaustion.
    """

    def __init__(self, config: BulkheadConfig, operation: Callable[[], T]):
        import threading

        self.config = config
        self.operation = operation
        self._semaphore = threading.Semaphore(config.max_concurrent)
        self._active_count = 0
        self._queued_count = 0
        self._lock = threading.Lock()

    def execute(self, context: Dict[str, Any]) -> T:
        """Execute operation with bulkhead isolation."""
        with self._lock:
            if self._queued_count >= self.config.max_queued:
                raise BulkheadFullError("Bulkhead queue is full")
            self._queued_count += 1

        try:
            acquired = self._semaphore.acquire(timeout=self.config.timeout)
            if not acquired:
                raise BulkheadFullError("Bulkhead timeout waiting for slot")

            with self._lock:
                self._queued_count -= 1
                self._active_count += 1

            try:
                return self.operation()
            finally:
                with self._lock:
                    self._active_count -= 1
                self._semaphore.release()
        except BulkheadFullError:
            with self._lock:
                self._queued_count -= 1
            raise

    def validate(self) -> List[str]:
        """Validate bulkhead configuration."""
        errors = []
        if self.config.max_concurrent < 1:
            errors.append("max_concurrent must be at least 1")
        if self.config.max_queued < 0:
            errors.append("max_queued must be non-negative")
        return errors

    @property
    def active_count(self) -> int:
        return self._active_count

    @property
    def queued_count(self) -> int:
        return self._queued_count


class BulkheadFullError(Exception):
    """Raised when bulkhead is at capacity."""
    pass


class StandardLibrary:
    """
    Central registry and factory for workflow patterns and components.

    Provides access to the standard library of reusable workflow patterns
    and components.
    """

    def __init__(self):
        self._patterns: Dict[str, WorkflowPattern] = {}
        self._components: Dict[str, type] = {}
        self._register_default_patterns()
        self._register_default_components()

    def _register_default_patterns(self) -> None:
        """Register built-in patterns."""
        # Retry pattern
        self.register_pattern(WorkflowPattern(
            id="retry-exponential",
            name="Exponential Retry Pattern",
            description="Retries failed operations with exponential backoff and jitter",
            category=PatternCategory.RESILIENCE,
            complexity=PatternComplexity.MODERATE,
            template="""
retry_config = RetryConfig(
    max_attempts={{ max_attempts }},
    initial_delay={{ initial_delay }},
    exponential_base={{ exponential_base }}
)
retry = RetryPattern(retry_config, {{ operation }})
result = retry.execute({})
""",
            parameters={
                "max_attempts": 3,
                "initial_delay": 1.0,
                "exponential_base": 2.0,
                "operation": "lambda: do_something()"
            }
        ))

        # Circuit breaker pattern
        self.register_pattern(WorkflowPattern(
            id="circuit-breaker",
            name="Circuit Breaker Pattern",
            description="Prevents cascading failures by failing fast on repeated errors",
            category=PatternCategory.RESILIENCE,
            complexity=PatternComplexity.COMPLEX,
            template="""
cb_config = CircuitBreakerConfig(
    failure_threshold={{ failure_threshold }},
    success_threshold={{ success_threshold }},
    timeout={{ timeout }}
)
circuit_breaker = CircuitBreakerPattern(cb_config, {{ operation }})
result = circuit_breaker.execute({})
""",
            parameters={
                "failure_threshold": 5,
                "success_threshold": 2,
                "timeout": 30.0,
                "operation": "lambda: call_service()"
            }
        ))

        # Timeout pattern
        self.register_pattern(WorkflowPattern(
            id="timeout",
            name="Timeout Pattern",
            description="Bounds execution time for operations",
            category=PatternCategory.RESILIENCE,
            complexity=PatternComplexity.SIMPLE,
            template="""
timeout = TimeoutPattern({{ timeout_seconds }}, {{ operation }})
result = timeout.execute({})
""",
            parameters={
                "timeout_seconds": 30.0,
                "operation": "lambda: slow_operation()"
            }
        ))

        # Bulkhead pattern
        self.register_pattern(WorkflowPattern(
            id="bulkhead",
            name="Bulkhead Pattern",
            description="Isolates resources to prevent exhaustion",
            category=PatternCategory.RESILIENCE,
            complexity=PatternComplexity.MODERATE,
            template="""
bulkhead_config = BulkheadConfig(
    max_concurrent={{ max_concurrent }},
    max_queued={{ max_queued }}
)
bulkhead = BulkheadPattern(bulkhead_config, {{ operation }})
result = bulkhead.execute({})
""",
            parameters={
                "max_concurrent": 10,
                "max_queued": 100,
                "operation": "lambda: resource_intensive_op()"
            }
        ))

    def _register_default_components(self) -> None:
        """Register built-in component types."""
        self._components["retry"] = RetryPattern
        self._components["circuit_breaker"] = CircuitBreakerPattern
        self._components["timeout"] = TimeoutPattern
        self._components["bulkhead"] = BulkheadPattern

    def register_pattern(self, pattern: WorkflowPattern) -> None:
        """Register a new pattern in the library."""
        if pattern.id in self._patterns:
            logger.warning(f"Overwriting existing pattern: {pattern.id}")
        self._patterns[pattern.id] = pattern
        logger.info(f"Registered pattern: {pattern.id}")

    def get_pattern(self, pattern_id: str) -> Optional[WorkflowPattern]:
        """Get a pattern by ID."""
        return self._patterns.get(pattern_id)

    def list_patterns(
        self,
        category: Optional[PatternCategory] = None,
        complexity: Optional[PatternComplexity] = None
    ) -> List[WorkflowPattern]:
        """List patterns with optional filtering."""
        patterns = list(self._patterns.values())

        if category:
            patterns = [p for p in patterns if p.category == category]
        if complexity:
            patterns = [p for p in patterns if p.complexity == complexity]

        return patterns

    def create_component(
        self,
        component_type: str,
        config: Any,
        operation: Callable
    ) -> WorkflowComponent:
        """Create a component instance."""
        if component_type not in self._components:
            raise ValueError(f"Unknown component type: {component_type}")

        component_class = self._components[component_type]
        return component_class(config, operation)

    def search_patterns(self, query: str) -> List[WorkflowPattern]:
        """Search patterns by name or description."""
        query_lower = query.lower()
        return [
            p for p in self._patterns.values()
            if query_lower in p.name.lower() or query_lower in p.description.lower()
        ]

    def export_catalog(self) -> Dict[str, Any]:
        """Export the entire pattern catalog."""
        return {
            "version": "1.0.0",
            "generated_at": datetime.utcnow().isoformat(),
            "patterns": [p.to_dict() for p in self._patterns.values()],
            "components": list(self._components.keys())
        }

    def get_catalog_hash(self) -> str:
        """Get hash of current catalog for versioning."""
        catalog_json = json.dumps(self.export_catalog(), sort_keys=True)
        return hashlib.sha256(catalog_json.encode()).hexdigest()[:16]


# Singleton instance
_library_instance: Optional[StandardLibrary] = None


def get_standard_library() -> StandardLibrary:
    """Get the singleton standard library instance."""
    global _library_instance
    if _library_instance is None:
        _library_instance = StandardLibrary()
    return _library_instance


# Convenience functions
def create_retry(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    operation: Optional[Callable] = None
) -> RetryPattern:
    """Create a retry pattern with common defaults."""
    config = RetryConfig(
        max_attempts=max_attempts,
        initial_delay=initial_delay
    )
    return RetryPattern(config, operation or (lambda: None))


def create_circuit_breaker(
    failure_threshold: int = 5,
    timeout: float = 30.0,
    operation: Optional[Callable] = None
) -> CircuitBreakerPattern:
    """Create a circuit breaker with common defaults."""
    config = CircuitBreakerConfig(
        failure_threshold=failure_threshold,
        timeout=timeout
    )
    return CircuitBreakerPattern(config, operation or (lambda: None))


def create_timeout(
    timeout_seconds: float = 30.0,
    operation: Optional[Callable] = None
) -> TimeoutPattern:
    """Create a timeout wrapper."""
    return TimeoutPattern(timeout_seconds, operation or (lambda: None))


def create_bulkhead(
    max_concurrent: int = 10,
    operation: Optional[Callable] = None
) -> BulkheadPattern:
    """Create a bulkhead for resource isolation."""
    config = BulkheadConfig(max_concurrent=max_concurrent)
    return BulkheadPattern(config, operation or (lambda: None))
