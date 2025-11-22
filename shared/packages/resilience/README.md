# Maestro Resilience

Resilience patterns for building fault-tolerant services in the Maestro Platform.

## Features

- **Circuit Breaker**: Prevents cascading failures by stopping calls to failing services
- **Bulkhead**: Isolates resources to prevent total system failure
- **Retry**: Automatically retries failed operations with configurable policies
- **Timeout**: Prevents operations from hanging indefinitely
- **Fallback**: Provides alternative behavior when primary operations fail

## Installation

```bash
pip install maestro-resilience
```

## Usage

### Circuit Breaker

```python
from maestro_resilience import CircuitBreaker

breaker = CircuitBreaker(
    failure_threshold=5,
    timeout=60,
    expected_exception=Exception
)

@breaker
def call_external_service():
    # Your code here
    pass
```

### Retry

```python
from maestro_resilience import retry

@retry(max_attempts=3, delay=1.0, backoff=2.0)
def unreliable_operation():
    # Your code here
    pass
```

### Timeout

```python
from maestro_resilience import timeout

@timeout(seconds=5.0)
def long_running_operation():
    # Your code here
    pass
```

## Documentation

Part of ADR-006: Resilience Patterns

## License

Proprietary - Maestro Platform Team
