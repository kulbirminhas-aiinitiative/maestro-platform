# Maestro Cache

Standardized caching interface for all Maestro Platform services.

## Features

- ✅ **Multiple Backends**: Redis, In-Memory
- ✅ **Async/Await**: Full async support
- ✅ **Auto-Configuration**: Configure via environment variables
- ✅ **Type-Safe**: Full type hints
- ✅ **Production-Ready**: Proper error handling, logging, health checks
- ✅ **No Custom Infrastructure**: Uses standard redis-py library

## Installation

```bash
# From maestro-platform PyPI server
pip install maestro-cache

# From local wheel
pip install maestro_cache-1.0.0-py3-none-any.whl
```

## Quick Start

### Environment Configuration

```bash
# Redis cache (recommended for production)
export MAESTRO_CACHE_URL="redis://localhost:6379/0"

# Redis with password
export MAESTRO_CACHE_URL="redis://:mypassword@redis:6379/1"

# Redis with SSL
export MAESTRO_CACHE_URL="rediss://redis.example.com:6380/0"

# In-memory cache (development/testing)
export MAESTRO_CACHE_URL="memory://"

# Optional settings
export MAESTRO_CACHE_TTL="3600"        # Default TTL in seconds
export MAESTRO_CACHE_PREFIX="myapp:"   # Key prefix for namespacing
```

### Usage

```python
from maestro_cache import CacheService

# Auto-configure from environment
cache = CacheService()

# Set value
await cache.set("user:123", {"name": "Alice", "role": "admin"}, ttl=3600)

# Get value
user = await cache.get("user:123")
# Returns: {"name": "Alice", "role": "admin"}

# Delete value
await cache.delete("user:123")

# Check existence
exists = await cache.exists("user:123")

# Increment counter
views = await cache.increment("page:views")

# Set multiple values
await cache.set_many({
    "key1": "value1",
    "key2": "value2",
}, ttl=3600)

# Get multiple values
values = await cache.get_many(["key1", "key2"])

# Clear by pattern
await cache.clear("user:*")

# Health check
healthy = await cache.health_check()

# Close connection
await cache.close()
```

## Architecture

### Interface-Based Design

All cache implementations implement `CacheInterface`:

```python
from maestro_cache import CacheInterface, RedisCache, InMemoryCache

# Use interface for dependency injection
def my_service(cache: CacheInterface):
    await cache.set("key", "value")

# Swap implementations easily
cache = RedisCache(url="redis://localhost:6379/0")
# or
cache = InMemoryCache()

my_service(cache)
```

### Factory Pattern

The `CacheService()` factory automatically chooses the right backend:

```python
# Reads MAESTRO_CACHE_URL and creates appropriate backend
cache = CacheService()

# Override in code
cache = CacheService(url="redis://localhost:6379/0")
```

## Backends

### Redis Cache

**Recommended for**: Production, multi-instance deployments

```python
from maestro_cache import RedisCache

cache = RedisCache(
    url="redis://localhost:6379/0",
    default_ttl=3600,
    key_prefix="myservice:",
)
```

**Features**:
- ✅ Distributed caching
- ✅ SSL support (use `rediss://` URL)
- ✅ Connection pooling
- ✅ Atomic operations
- ✅ Pattern matching (SCAN)

**Configuration**:
- `url`: Redis connection URL
- `default_ttl`: Default expiration time
- `key_prefix`: Namespace for keys
- `decode_responses`: Auto-decode bytes to strings (default: True)

### In-Memory Cache

**Recommended for**: Development, testing, single-instance

```python
from maestro_cache import InMemoryCache

cache = InMemoryCache(
    default_ttl=3600,
    max_size=10000,
)
```

**Features**:
- ✅ LRU eviction
- ✅ TTL support
- ✅ Zero dependencies
- ✅ Instant performance

**Limitations**:
- ❌ Not shared across instances
- ❌ Lost on restart
- ❌ Limited by memory

## Migration from Custom Redis Client

### Before (Quality Fabric custom code)

```python
# services/database/redis_client.py - 456 LOC
from services.database.redis_client import get_redis_client

redis = get_redis_client()
await redis.set("key", "value")
```

### After (maestro-cache)

```python
# 1 import, auto-configured
from maestro_cache import CacheService

cache = CacheService()
await cache.set("key", "value")
```

**Benefits**:
- ✅ 456 LOC → 1 LOC
- ✅ No SSL configuration bugs
- ✅ Works across all Maestro services
- ✅ Standardized interface

## Testing

```python
import pytest
from maestro_cache import InMemoryCache

@pytest.fixture
async def cache():
    cache = InMemoryCache()
    yield cache
    await cache.close()

async def test_cache(cache):
    await cache.set("test", "value")
    assert await cache.get("test") == "value"
```

## Contributing

See `maestro-platform/shared/CONTRIBUTING.md`

## License

Proprietary - Maestro Platform
