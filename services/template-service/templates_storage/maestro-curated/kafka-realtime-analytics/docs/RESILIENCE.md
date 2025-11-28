# Resilience Patterns

This document describes the resilience patterns implemented in the Real-Time Analytics Platform per MAESTRO ADR-006.

## Overview

The platform implements comprehensive resilience patterns to ensure high availability and fault tolerance:

1. **Circuit Breaker**: Prevents cascading failures
2. **Retry with Exponential Backoff**: Handles transient failures
3. **Timeout Protection**: Prevents hanging operations
4. **Fallback Mechanisms**: Graceful degradation

## Circuit Breaker Pattern

### Purpose
Circuit breakers monitor failures and temporarily block requests to failing services, allowing them time to recover.

### Implementation

Located in `src/infrastructure/resilience/circuit_breaker.py`

### States
- **CLOSED**: Normal operation, requests pass through
- **OPEN**: Too many failures, requests are blocked
- **HALF_OPEN**: Testing if service recovered

### Configuration

Per `config/resilience.yaml`:

```yaml
circuit_breakers:
  kafka_producer:
    failure_threshold: 5    # Open after 5 failures
    success_threshold: 2    # Close after 2 successes in HALF_OPEN
    timeout: 60             # Wait 60s before HALF_OPEN

  database:
    failure_threshold: 5
    success_threshold: 2
    timeout: 60

  redis:
    failure_threshold: 3
    success_threshold: 2
    timeout: 30
```

### Usage Example

```python
from src.infrastructure.resilience import CircuitBreaker

kafka_breaker = CircuitBreaker(
    failure_threshold=5,
    success_threshold=2,
    timeout=60,
    name="kafka_producer"
)

try:
    result = await kafka_breaker.call(produce_message, topic, message)
except CircuitBreakerOpenError:
    logger.error("Kafka circuit breaker is open, using fallback")
    # Use fallback mechanism
```

## Retry Pattern

### Purpose
Automatically retry failed operations with increasing delays between attempts.

### Implementation

Located in `src/infrastructure/resilience/retry.py`

### Configuration

```yaml
retry_policies:
  kafka:
    max_retries: 3
    initial_delay: 1.0      # Start with 1s delay
    backoff_factor: 2.0     # Double each retry
    max_delay: 30.0         # Cap at 30s
```

### Exponential Backoff
- Attempt 1: Immediate
- Attempt 2: 1s delay
- Attempt 3: 2s delay
- Attempt 4: 4s delay

### Usage Example

```python
from src.infrastructure.resilience import retry_with_backoff

result = await retry_with_backoff(
    send_to_kafka,
    max_retries=3,
    initial_delay=1.0,
    backoff_factor=2.0,
    retryable_exceptions=(KafkaError, ConnectionError)
)
```

## Timeout Pattern

### Purpose
Prevent operations from hanging indefinitely by enforcing time limits.

### Implementation

Located in `src/infrastructure/resilience/timeout.py`

### Configuration

```yaml
timeouts:
  kafka_publish: 30        # 30 seconds
  kafka_consume: 60        # 60 seconds
  database_query: 10       # 10 seconds
  redis_operation: 5       # 5 seconds
```

### Usage Example

```python
from src.infrastructure.resilience import with_timeout, TimeoutError

try:
    result = await with_timeout(
        database_query(),
        timeout_seconds=10,
        operation_name="user_query"
    )
except TimeoutError:
    logger.warning("Query exceeded 10s timeout")
    # Use cached results or return error
```

## Fallback Pattern

### Purpose
Provide alternative responses when primary operations fail.

### Implementation

Located in `src.infrastructure/resilience/fallback.py`

### Configuration

```yaml
fallback_strategies:
  cache:
    primary: "redis"
    fallback: "in_memory"
    description: "Falls back to in-memory cache if Redis unavailable"

  analytics_query:
    primary: "postgresql"
    fallback: "cached_results"
    description: "Returns cached results if database unavailable"
```

### Usage Example

```python
from src.infrastructure.resilience import with_fallback

async def query_from_db():
    return await db.execute(query)

async def query_from_cache():
    return cached_results.get(query_key)

result = await with_fallback(
    query_from_db,
    query_from_cache,
    operation_name="analytics_query"
)
```

## Combined Patterns

For critical operations, combine multiple patterns:

```python
from src.infrastructure.resilience import (
    CircuitBreaker,
    retry_with_backoff,
    with_timeout,
    with_fallback
)

kafka_breaker = CircuitBreaker(failure_threshold=5, timeout=60)

async def send_with_resilience(message):
    async def primary_operation():
        async def with_circuit_breaker():
            return await kafka_breaker.call(kafka_producer.send, message)

        return await with_timeout(
            retry_with_backoff(
                with_circuit_breaker,
                max_retries=3,
                initial_delay=1.0
            ),
            timeout_seconds=30
        )

    async def fallback_operation():
        # Store in local queue for later processing
        await local_queue.enqueue(message)
        return {"status": "queued"}

    return await with_fallback(primary_operation, fallback_operation)
```

## Monitoring

### Metrics

Track resilience pattern effectiveness via Prometheus metrics:

```
# Circuit breaker state (0=closed, 1=half_open, 2=open)
circuit_breaker_state{service="kafka_producer"} 0

# Retry attempts
retry_attempts_total{operation="kafka_publish"} 42

# Timeout occurrences
timeout_errors_total{operation="database_query"} 3

# Fallback usage
fallback_invocations_total{operation="cache_read"} 15
```

### Health Checks

The `/health` endpoint reports circuit breaker states:

```json
{
  "status": "healthy",
  "circuit_breakers": {
    "kafka_producer": "closed",
    "database": "closed",
    "redis": "half_open"
  }
}
```

## Testing

Comprehensive tests verify resilience patterns:

- **Unit tests**: `tests/unit/test_circuit_breaker.py`, etc.
- **Integration tests**: `tests/integration/test_resilience_integration.py`
- **E2E tests**: `tests/e2e/test_complete_workflow.py`

Run resilience tests:

```bash
pytest tests/unit/test_circuit_breaker.py -v
pytest tests/integration/test_resilience_integration.py -v
```

## Best Practices

1. **Configure appropriately**: Tune thresholds based on your traffic patterns
2. **Monitor metrics**: Track circuit breaker states and failure rates
3. **Test failure scenarios**: Regularly test with simulated failures
4. **Log comprehensively**: Log all resilience pattern invocations
5. **Combine patterns**: Use multiple patterns together for critical paths
6. **Have fallbacks**: Always provide graceful degradation options

## References

- [MAESTRO ADR-006: Resilience Patterns](../../ARCHITECTURE.md)
- [Circuit Breaker Implementation](../src/infrastructure/resilience/circuit_breaker.py)
- [Retry Implementation](../src/infrastructure/resilience/retry.py)
- [Timeout Implementation](../src/infrastructure/resilience/timeout.py)
- [Fallback Implementation](../src/infrastructure/resilience/fallback.py)
