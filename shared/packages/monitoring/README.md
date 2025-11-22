# MAESTRO Monitoring

Comprehensive monitoring and observability stack for MAESTRO ecosystem services.

## Features

- Prometheus metrics collection
- OpenTelemetry tracing integration
- Health check management
- Performance monitoring
- Custom metrics and gauges
- Distributed tracing support

## Installation

```bash
poetry add maestro-monitoring
```

## Usage

```python
from maestro_monitoring import MetricsCollector, HealthCheckManager

# Initialize metrics
metrics = MetricsCollector(service_name="my-service")
metrics.increment_counter("requests_total")
metrics.record_histogram("request_duration_seconds", 0.123)

# Health checks
health = HealthCheckManager()
health.register_check("database", check_database_connection)
health.register_check("redis", check_redis_connection)

status = health.check_health()
```

## Metrics Endpoint

Exposes metrics on `/metrics` endpoint for Prometheus scraping.

## License

MIT