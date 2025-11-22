# Configuration Guidelines

## ✅ Acceptable Patterns

### 1. Environment Variables with Sensible Defaults

**ACCEPTABLE** - Using `os.getenv()` with localhost defaults:

```python
# ✅ GOOD - Environment variable with fallback
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost:5432/db")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:4000")
```

**Why acceptable**:
- Allows override via environment variables
- Provides working defaults for local development
- Follows 12-factor app principles

### 2. Configuration System with Defaults

**ACCEPTABLE** - Using dynaconf or similar:

```python
# ✅ GOOD - Dynaconf with YAML defaults
from claude_team_sdk.config import settings

db_url = settings.database.url  # From config/default.yaml
redis_url = settings.redis.url
```

**Why acceptable**:
- Centralized configuration
- Hierarchical (defaults → env-specific → env vars)
- Type-safe access

### 3. Helper Methods for Development

**ACCEPTABLE** - Explicit development helpers:

```python
# ✅ GOOD - Clearly marked as local development
class DatabaseConfig:
    @staticmethod
    def local_postgres(database: str = "mydb") -> str:
        """Get connection string for LOCAL development"""
        return f"postgresql://postgres:postgres@localhost:5432/{database}"

    @staticmethod
    def from_settings() -> str:
        """Get from config system (PRODUCTION)"""
        from claude_team_sdk.config import get_database_url
        return get_database_url()
```

**Why acceptable**:
- Explicitly marked as local/development
- Production path exists (from_settings)
- Helper method, not the only option

### 4. Example/Template Code

**ACCEPTABLE** - In code generators or examples:

```python
# ✅ GOOD - Template for generated projects
template = '''
# .env.example
DATABASE_URL=postgresql://user:password@localhost:5432/db
API_URL=http://localhost:4000
'''
```

**Why acceptable**:
- This IS the generated .env.example file content
- Provides working defaults for users
- Not used by the generator itself

### 5. Documentation and Comments

**ACCEPTABLE** - In comments and docs:

```python
# ✅ GOOD - Documentation example
def connect(url: str):
    """
    Connect to database.

    Example:
        connect("postgresql://localhost:5432/db")
    """
    pass
```

**Why acceptable**:
- Not actual runtime code
- Educational/documentation purpose

## ❌ Unacceptable Patterns

### 1. Direct Hardcoding Without Environment Variables

**NOT ACCEPTABLE**:

```python
# ❌ BAD - No way to override
DATABASE_URL = "postgresql://localhost:5432/db"
REDIS_URL = "redis://localhost:6379"

# Used directly
conn = connect(DATABASE_URL)
```

**Why not acceptable**:
- Cannot be overridden
- Requires code changes for different environments
- Violates 12-factor principles

### 2. Hardcoded in Business Logic

**NOT ACCEPTABLE**:

```python
# ❌ BAD - Hardcoded in function
async def fetch_user(user_id: str):
    response = await client.get(f"http://localhost:4000/users/{user_id}")
    return response.json()
```

**Why not acceptable**:
- Cannot work in production
- No configuration path
- Tightly coupled to localhost

### 3. Mixed Configuration Sources

**NOT ACCEPTABLE**:

```python
# ❌ BAD - Some from env, some hardcoded
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost:5432/db")
REDIS_URL = "redis://localhost:6379"  # ← Hardcoded!
```

**Why not acceptable**:
- Inconsistent configuration approach
- Easy to miss hardcoded values
- Maintenance nightmare

## 🔧 Migration Patterns

### Pattern 1: Simple Replacement

**Before**:
```python
API_URL = "http://localhost:4000"
```

**After**:
```python
from claude_team_sdk.config import settings
API_URL = settings.api.base_url
```

### Pattern 2: With Validation

**Before**:
```python
DB_URL = os.getenv("DATABASE_URL", "postgresql://localhost:5432/db")
```

**After**:
```python
from claude_team_sdk.config import settings

# With validation
if not settings.database.url:
    raise ValueError("DATABASE_URL must be configured")

DB_URL = settings.database.url
```

### Pattern 3: Backward Compatibility

**Before**:
```python
# Old code
DATABASE_URL = "postgresql://localhost:5432/db"
```

**After**:
```python
# Provide migration path
try:
    from claude_team_sdk.config import get_database_url
    DATABASE_URL = get_database_url()
except ImportError:
    # Fallback for old installations
    import os
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost:5432/db")
```

## 📋 Validation Checklist

Before committing code, check:

- [ ] All service URLs use configuration system
- [ ] No hardcoded URLs in business logic
- [ ] Environment variables have documented defaults
- [ ] .env.example exists with all required variables
- [ ] Localhost only in development helpers (clearly marked)
- [ ] Generated/template code is marked as such

## 🧪 Testing Configuration

```python
# Test that configuration works
def test_config_loads():
    from claude_team_sdk.config import settings

    # Should load defaults
    assert settings.database.url is not None
    assert settings.redis.url is not None

    # Should respect environment
    import os
    os.environ['CLAUDE_TEAM_DATABASE_URL'] = 'postgresql://test:5432/db'
    # Re-import or reload config
    assert 'test:5432' in settings.database.url
```

## 🎯 Summary

| Pattern | Status | Use Case |
|---------|--------|----------|
| `os.getenv("VAR", "localhost:5432")` | ✅ | Development defaults |
| `settings.database.url` (dynaconf) | ✅ | Production code |
| `DatabaseConfig.local_postgres()` | ✅ | Dev helper (explicit) |
| Template strings in generators | ✅ | Example project generation |
| Direct hardcoding | ❌ | Never |
| Hardcoded in business logic | ❌ | Never |
| Mixed config sources | ❌ | Never |

## 📚 Related Documents

- [MIGRATION_GUIDE.md](../MIGRATION_GUIDE.md) - How to migrate existing code
- [config/README.md](../config/README.md) - Configuration reference
- [ARCHITECTURE_COMPLIANCE_REPORT.md](../ARCHITECTURE_COMPLIANCE_REPORT.md) - Full audit

---

**Key Principle**: Configuration should be **externalized** and **overridable**, but sensible defaults for development are acceptable when properly implemented.
