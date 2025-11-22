# Maestro Service Registry

Service discovery and registration for the Maestro Platform (consolidated from multiple implementations).

## Features

- Service registration and discovery
- Health checking
- Load balancing support
- Automatic deregistration
- Consolidated from quality-fabric and maestro-engine implementations

## Installation

```bash
pip install maestro-service-registry
```

## Usage

```python
from maestro_service_registry import ServiceRegistry

registry = ServiceRegistry()
registry.register("my-service", "localhost", 8000)
services = registry.discover("my-service")
```

## License

Proprietary - Maestro Platform Team
