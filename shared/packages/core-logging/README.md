# MAESTRO Core Logging

Enterprise-grade structured logging with OpenTelemetry integration for the MAESTRO ecosystem.

## Features

- Structured logging with `structlog`
- OpenTelemetry tracing integration
- JSON and console output formats
- Contextual logging
- FastAPI middleware support

## Installation

```bash
poetry add maestro-core-logging
```

## Usage

```python
from maestro_core_logging import get_logger, configure_logging

# Configure once at application startup
configure_logging(
    service_name="my-service",
    environment="production",
    log_level="INFO"
)

# Use throughout your application
logger = get_logger(__name__)
logger.info("Application started", version="1.0.0")
```