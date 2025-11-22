# Configuration Guide

## Overview

The Claude Team SDK uses [Dynaconf](https://www.dynaconf.com/) for hierarchical configuration management.

## Configuration Hierarchy

Settings are loaded in this order (highest priority first):

1. **Environment Variables** (with `CLAUDE_TEAM_` prefix)
2. **Environment-specific YAML** (`config/development.yaml` or `config/production.yaml`)
3. **Default YAML** (`config/default.yaml`)
4. **Code defaults**

## Files

- `default.yaml` - Base configuration for all environments
- `development.yaml` - Development environment overrides
- `production.yaml` - Production environment overrides
- `service_ports.yaml` - Service port registry

## Usage

### In Python Code

```python
from claude_team_sdk.config import settings

# Access configuration
db_url = settings.database.url
redis_url = settings.redis.url
max_agents = settings.team.max_agents

# Helper functions
from claude_team_sdk.config import (
    get_database_url,
    get_redis_url,
    is_production,
    is_development
)

if is_production():
    # Production-specific logic
    pass
```

### Environment Variables

All settings can be overridden via environment variables:

```bash
# Set environment
export ENVIRONMENT=production

# Override specific settings
export CLAUDE_TEAM_DATABASE_URL=postgresql://user:pass@host/db
export CLAUDE_TEAM_MAX_AGENTS=20
export CLAUDE_TEAM_LOG_LEVEL=DEBUG
```

### .env File

Create a `.env` file (use `.env.example` as template):

```bash
# Copy template
cp .env.example .env

# Edit values
vim .env
```

The `.env` file is automatically loaded by dynaconf.

## Configuration Sections

### Service

```yaml
service:
  name: claude_team_sdk
  version: 1.0.0
  environment: ${ENVIRONMENT:development}
```

### Database

```yaml
database:
  url: ${DATABASE_URL:postgresql://postgres:postgres@localhost:5432/claude_team_sdk}
  pool_size: ${DB_POOL_SIZE:5}
  max_overflow: ${DB_MAX_OVERFLOW:10}
  echo: ${DB_ECHO:false}
```

### Redis

```yaml
redis:
  url: ${REDIS_URL:redis://localhost:6379/0}
  max_connections: ${REDIS_MAX_CONNECTIONS:10}
```

### Team SDK

```yaml
team:
  max_agents: ${MAX_AGENTS:10}
  coordination_timeout: ${COORDINATION_TIMEOUT:30}
  agent_execution_timeout: ${AGENT_EXECUTION_TIMEOUT:300}
```

### Resilience

```yaml
resilience:
  circuit_breaker:
    failure_threshold: ${CIRCUIT_BREAKER_FAILURE_THRESHOLD:5}
    success_threshold: ${CIRCUIT_BREAKER_SUCCESS_THRESHOLD:2}
    timeout: ${CIRCUIT_BREAKER_TIMEOUT:60}

  retry:
    max_retries: ${MAX_RETRIES:3}
    initial_delay: ${INITIAL_RETRY_DELAY:1.0}
    backoff_factor: ${RETRY_BACKOFF_FACTOR:2.0}

  timeout:
    default: ${DEFAULT_TIMEOUT:30}
    agent_execution: ${AGENT_EXECUTION_TIMEOUT:300}

  bulkhead:
    max_concurrent_agents: ${MAX_CONCURRENT_AGENTS:4}
```

### Monitoring

```yaml
monitoring:
  metrics:
    enabled: ${METRICS_ENABLED:true}
    port: ${METRICS_PORT:9090}

  logging:
    level: ${LOG_LEVEL:INFO}
    format: ${LOG_FORMAT:json}
```

### Security

```yaml
security:
  jwt_secret: ${JWT_SECRET:}
  cors:
    enabled: ${CORS_ENABLED:true}
    origins: ${CORS_ORIGINS:http://localhost:3000}

  rate_limit:
    enabled: ${RATE_LIMIT_ENABLED:true}
    requests_per_minute: ${RATE_LIMIT_PER_MINUTE:100}
```

## Environment Switching

### Via Environment Variable

```bash
# Development (default)
export ENVIRONMENT=development
python app.py

# Production
export ENVIRONMENT=production
python app.py
```

### In Code

```python
from claude_team_sdk.config import settings

# Check current environment
print(settings.service.environment)

# Check environment type
from claude_team_sdk.config import is_production, is_development

if is_production():
    print("Running in production mode")
```

## Port Registry

The `service_ports.yaml` file documents all service ports to prevent conflicts.

### Adding a New Service

1. Edit `config/service_ports.yaml`:
   ```yaml
   services:
     - name: my-new-service
       port: 4002
       category: api_services
       public: false
       health_endpoint: /health
       description: My new service
   ```

2. Validate:
   ```bash
   python3 scripts/validate_port_allocation.py
   ```

## Validation

### Check Configuration

```python
from claude_team_sdk.config import settings

# Print all settings
print(settings.as_dict())

# Check specific values
print(f"Database: {settings.database.url}")
print(f"Redis: {settings.redis.url}")
print(f"Environment: {settings.service.environment}")
```

### Run Validation Scripts

```bash
# Check for hardcoded URLs
python3 scripts/detect_hardcoded_urls.py

# Validate port allocation
python3 scripts/validate_port_allocation.py

# Check configuration loading
python3 -c "from claude_team_sdk.config import settings; print(settings.as_dict())"
```

## Best Practices

1. **Never commit secrets** - Use environment variables or `.env` (which is .gitignored)

2. **Use defaults** - Provide sensible defaults in `default.yaml`

3. **Environment-specific** - Put environment-specific values in `development.yaml` or `production.yaml`

4. **Document changes** - Update this README when adding new configuration options

5. **Validate early** - Check configuration at startup:
   ```python
   from claude_team_sdk.config import settings

   # Validate required settings
   if not settings.claude.api_key:
       raise ValueError("ANTHROPIC_API_KEY is required")
   ```

## Troubleshooting

### Settings Not Loading

```bash
# Check if files exist
ls -la config/

# Check environment
echo $ENVIRONMENT

# Test loading
python3 -c "from claude_team_sdk.config import settings; print(settings.as_dict())"
```

### Environment Variables Not Working

```bash
# Ensure proper prefix
export CLAUDE_TEAM_DATABASE_URL=...  # ✅ Correct
export DATABASE_URL=...               # ❌ Won't work (no prefix)

# Check if loaded
python3 -c "from claude_team_sdk.config import settings; print(settings.database.url)"
```

### YAML Syntax Errors

```bash
# Validate YAML syntax
python3 -c "import yaml; yaml.safe_load(open('config/default.yaml'))"
```

## Examples

See [MIGRATION_GUIDE.md](../MIGRATION_GUIDE.md) for complete migration examples.
