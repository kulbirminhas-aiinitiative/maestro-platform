# MAESTRO Core Config

Centralized configuration management for MAESTRO ecosystem services.

## Features

- Environment-based configuration with Pydantic Settings
- Support for .env files, environment variables, and config files
- Type-safe configuration with validation
- Secret management integration (HashiCorp Vault)
- Multi-environment support (dev, staging, production)

## Installation

```bash
poetry add maestro-core-config
```

## Usage

```python
from maestro_core_config import BaseConfig, get_config
from pydantic import Field

class MyServiceConfig(BaseConfig):
    service_name: str = "my-service"
    api_key: str = Field(..., env="API_KEY")
    database_url: str = Field(..., env="DATABASE_URL")

# Load configuration
config = get_config(MyServiceConfig)
```

## Environment Variables

Configuration can be loaded from:
- `.env` files
- Environment variables
- Configuration files (JSON, YAML, TOML)
- HashiCorp Vault (for secrets)

## License

MIT