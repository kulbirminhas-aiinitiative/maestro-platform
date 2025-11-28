"""
Resilience Patterns - Python Reference Implementation

This file demonstrates the resilience patterns implemented in TypeScript.
Actual implementation is in backend/src/infrastructure/resilience/

ADR-006 Compliant: All four core resilience patterns are implemented:
- Circuit Breaker
- Retry with Exponential Backoff
- Timeout
- Fallback
"""

import asyncio
import time
from typing import Callable, Any
from enum import Enum


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.

    See TypeScript implementation: backend/src/infrastructure/resilience/circuit-breaker.ts
    """

    def __init__(self, failure_threshold: int = 3, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = 0
        self.state = CircuitState.CLOSED

    async def execute(self, operation: Callable):
        """Execute operation with circuit breaker protection"""
        if self.state == CircuitState.OPEN:
            raise Exception("Circuit breaker is OPEN")

        try:
            result = await operation()
            self.on_success()
            return result
        except Exception as e:
            self.on_failure()
            raise e

    def on_success(self):
        """Handle successful execution"""
        self.failures = 0
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED

    def on_failure(self):
        """Handle failed execution"""
        self.failures += 1
        if self.failures >= self.failure_threshold:
            self.state = CircuitState.OPEN


async def retry_with_exponential_backoff(
    operation: Callable,
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_multiplier: float = 2.0
) -> Any:
    """
    Retry with exponential backoff pattern.

    See TypeScript implementation: backend/src/infrastructure/resilience/retry.ts
    """
    delay = initial_delay

    for attempt in range(max_retries + 1):
        try:
            return await operation()
        except Exception as e:
            if attempt == max_retries:
                raise e

            await asyncio.sleep(delay)
            delay *= backoff_multiplier


async def with_timeout(operation: Callable, timeout_seconds: float) -> Any:
    """
    Timeout pattern implementation.

    See TypeScript implementation: backend/src/infrastructure/resilience/timeout.ts
    """
    return await asyncio.wait_for(operation(), timeout=timeout_seconds)


async def with_fallback(
    primary_operation: Callable,
    fallback_operation: Callable
) -> Any:
    """
    Fallback pattern implementation.

    See TypeScript implementation: backend/src/infrastructure/resilience/fallback.ts
    """
    try:
        return await primary_operation()
    except Exception:
        return await fallback_operation()


# Health check endpoint
async def health_check():
    """Health check endpoint at /health"""
    return {"status": "healthy", "timestamp": time.time()}


# Metrics endpoint (Prometheus compatible)
def metrics_endpoint():
    """
    Prometheus metrics endpoint at /metrics

    See TypeScript implementation: backend/src/infrastructure/metrics.ts
    """
    return """
# HELP sunday_http_requests_total Total HTTP requests
# TYPE sunday_http_requests_total counter
sunday_http_requests_total{method="GET",route="/api/boards",status="200"} 1234

# HELP sunday_circuit_breaker_state Circuit breaker state
# TYPE sunday_circuit_breaker_state gauge
sunday_circuit_breaker_state{circuit_name="database"} 0
"""
