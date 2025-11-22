# Migration Guide - Architecture Improvements

This guide helps you migrate from the old flat structure to the new architecture-compliant structure.

## 🎯 What Changed

### 1. Configuration Management
**Before**: Hardcoded URLs everywhere
```python
DATABASE_URL = "postgresql://user:password@localhost:5432/restaurant"
REDIS_URL = "redis://localhost:6379"
```

**After**: Centralized configuration with dynaconf
```python
from claude_team_sdk.config import settings

DATABASE_URL = settings.database.url
REDIS_URL = settings.redis.url
```

### 2. Project Structure
**Before**: Flat structure
```
claude_team_sdk/
├── agent_base.py
├── team_coordinator.py
├── specialized_agents.py
└── examples/
```

**After**: Organized src/ pattern
```
claude_team_sdk/
├── src/
│   └── claude_team_sdk/
│       ├── agents/
│       ├── coordination/
│       ├── state/
│       ├── resilience/
│       └── config/
├── config/
├── examples/
├── _experiments/
└── _legacy/
```

### 3. Resilience Patterns
**New**: Built-in fault tolerance
```python
from claude_team_sdk.resilience import (
    CircuitBreaker,
    retry_with_backoff,
    with_timeout,
    Bulkhead
)

# Circuit breaker for agent failures
circuit_breaker = CircuitBreaker(failure_threshold=5)
result = await circuit_breaker.call(agent.execute, task)

# Retry with exponential backoff
result = await retry_with_backoff(
    lambda: api_call(),
    max_retries=3,
    initial_delay=1.0
)

# Timeout enforcement
result = await with_timeout(
    lambda: long_running_operation(),
    seconds=300
)

# Bulkhead isolation
bulkhead = Bulkhead(max_concurrent=4)
result = await bulkhead.call(process_task, task)
```

## 📋 Migration Steps

### Step 1: Update Imports (Breaking Change)

**Old imports**:
```python
from agent_base import TeamAgent, AgentConfig
from team_coordinator import TeamCoordinator
from specialized_agents import DeveloperAgent
```

**New imports**:
```python
from claude_team_sdk import TeamAgent, TeamCoordinator
from claude_team_sdk.agents import DeveloperAgent
from claude_team_sdk.resilience import CircuitBreaker
```

### Step 2: Setup Configuration

1. **Copy environment template**:
   ```bash
   cp .env.example .env
   ```

2. **Update .env with your values**:
   ```bash
   # Edit .env
   DATABASE_URL=postgresql://user:password@host:5432/db
   REDIS_URL=redis://host:6379/0
   ANTHROPIC_API_KEY=your_key_here
   ```

3. **Update your code to use configuration**:
   ```python
   from claude_team_sdk.config import settings

   # Access configuration
   db_url = settings.database.url
   redis_url = settings.redis.url
   max_agents = settings.team.max_agents
   ```

### Step 3: Update Database Connections

**Old**:
```python
db_url = "postgresql://postgres:postgres@localhost:5432/db"
db = await init_database(db_url)
```

**New**:
```python
from persistence.database import DatabaseConfig

# Use configuration
db_url = DatabaseConfig.from_settings()
db = await init_database(db_url)
```

### Step 4: Add Resilience Patterns

**Wrap agent execution with resilience**:
```python
from claude_team_sdk.resilience import CircuitBreaker, retry_with_backoff, with_timeout

# Create circuit breaker for each agent type
developer_circuit = CircuitBreaker(
    failure_threshold=5,
    success_threshold=2,
    timeout=60,
    name="developer_agent"
)

# Execute with resilience
async def execute_agent_safely(agent, task):
    return await developer_circuit.call(
        with_timeout,
        lambda: retry_with_backoff(
            lambda: agent.execute(task),
            max_retries=3
        ),
        timeout=300
    )
```

### Step 5: Update Examples

**Replace hardcoded URLs in your examples**:

1. **Import configuration**:
   ```python
   from claude_team_sdk.config import settings
   ```

2. **Use configuration values**:
   ```python
   # Old
   api_url = "http://localhost:4000"

   # New
   api_url = settings.api.base_url
   ```

## 🔧 Configuration Reference

### Environment Variables

All configuration can be set via environment variables with `CLAUDE_TEAM_` prefix:

```bash
# Database
export CLAUDE_TEAM_DATABASE_URL=postgresql://...
export CLAUDE_TEAM_DB_POOL_SIZE=10

# Redis
export CLAUDE_TEAM_REDIS_URL=redis://...

# Team SDK
export CLAUDE_TEAM_MAX_AGENTS=10
export CLAUDE_TEAM_COORDINATION_TIMEOUT=30

# Resilience
export CLAUDE_TEAM_CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
export CLAUDE_TEAM_MAX_RETRIES=3
export CLAUDE_TEAM_DEFAULT_TIMEOUT=30
```

### Configuration Files

Hierarchy (highest to lowest priority):
1. Environment variables
2. `config/{environment}.yaml` (development/production)
3. `config/default.yaml`

**Example - config/development.yaml**:
```yaml
database:
  url: postgresql://postgres:postgres@localhost:5432/dev
  echo: true

monitoring:
  logging:
    level: DEBUG
```

## 🧪 Testing Your Migration

### 1. Validate Port Allocation
```bash
python3 scripts/validate_port_allocation.py
```

### 2. Check for Hardcoded URLs
```bash
python3 scripts/detect_hardcoded_urls.py --strict
```

### 3. Check for Legacy Imports
```bash
python3 scripts/check_legacy_imports.py src/**/*.py
```

### 4. Run Pre-commit Hooks
```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

## 🚀 Quick Start After Migration

### Running Examples

```bash
# 1. Setup environment
cp .env.example .env
# Edit .env with your values

# 2. Install dependencies
pip install -e .

# 3. Run examples
python examples/basic_team.py
```

### Creating New Agents

```python
from claude_team_sdk import TeamAgent, AgentConfig, AgentRole
from claude_team_sdk.config import settings
from claude_team_sdk.resilience import CircuitBreaker

class MyCustomAgent(TeamAgent):
    def __init__(self, agent_id, coord_server):
        config = AgentConfig(
            agent_id=agent_id,
            role=AgentRole.CUSTOM
        )
        super().__init__(config, coord_server)

        # Add resilience
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=settings.resilience.circuit_breaker.failure_threshold,
            name=f"{agent_id}_circuit"
        )

    async def execute_role_specific_work(self):
        # Your custom logic here
        pass
```

## 📊 Architecture Improvements Summary

| Aspect | Before | After |
|--------|--------|-------|
| Configuration | Hardcoded | Dynaconf (hierarchical) |
| Structure | Flat | src/ pattern |
| Resilience | None | Circuit breaker, retry, timeout, bulkhead |
| Port Management | Ad-hoc | Registry with validation |
| Imports | Messy | Clean, organized |
| Code Quality | Manual | Pre-commit hooks |

## 🔍 Troubleshooting

### Import Errors
```python
# If you get: ModuleNotFoundError: No module named 'claude_team_sdk'

# Solution: Install in development mode
pip install -e .
```

### Configuration Not Loading
```python
# If settings not found

# Check environment
from claude_team_sdk.config import settings
print(settings.service.environment)

# Manually set environment
export ENVIRONMENT=development
```

### Resilience Patterns Not Working
```python
# If circuit breaker not triggering

# Check configuration
print(settings.resilience.circuit_breaker.failure_threshold)

# Manual test
from claude_team_sdk.resilience import CircuitBreaker

cb = CircuitBreaker(failure_threshold=2)
for i in range(3):
    try:
        await cb.call(failing_function)
    except Exception as e:
        print(f"Attempt {i}: {e}")
```

## 📚 Additional Resources

- [Architecture Compliance Report](./ARCHITECTURE_COMPLIANCE_REPORT.md) - Detailed findings
- [Configuration Guide](./config/README.md) - All configuration options
- [ADR-001: Service Discovery](../../maestro-frontend/docs/architecture/ADR-001-service-discovery.md)
- [ADR-006: Resilience Patterns](../../maestro-frontend/docs/architecture/ADR-006-resilience-patterns.md)
- [ADR-007: Code Organization](../../maestro-frontend/docs/architecture/ADR-007-code-organization.md)

## ✅ Migration Checklist

- [ ] Install dynaconf: `pip install dynaconf`
- [ ] Copy .env.example to .env
- [ ] Update imports to use new paths
- [ ] Replace hardcoded URLs with `settings.*`
- [ ] Add resilience patterns to agent execution
- [ ] Run validation scripts (no errors)
- [ ] Install pre-commit hooks
- [ ] Test all examples
- [ ] Update documentation

---

**Questions?** Check the [Architecture Compliance Report](./ARCHITECTURE_COMPLIANCE_REPORT.md) or create an issue.
