# Maestro Rate Limiting

A shared traffic governance platform for all Maestro API services.

## Features

- **Redis-backed sliding window algorithm** - Industry standard, distributed-safe
- **Per-tenant rate limiting** - Based on subscription tiers
- **Dynamic policy management** - Update rules without redeployment
- **Prometheus metrics** - Observable and alertable
- **Concurrent request tracking** - Prevent resource exhaustion
- **Standard headers** - X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset, Retry-After

## Installation

```bash
# From maestro-platform root
pip install -e shared/rate-limiting

# With Prometheus metrics
pip install -e "shared/rate-limiting[metrics]"
```

## Quick Start

### FastAPI Integration

```python
from fastapi import FastAPI
from redis import Redis
from maestro_rate_limiting import RateLimitMiddleware, RateLimitMetrics, PolicyService

app = FastAPI()
redis = Redis(host="localhost", port=6379)

# Optional: Policy service for dynamic rules
policy_service = PolicyService(redis)

# Optional: Metrics for monitoring
metrics = RateLimitMetrics(redis)

# Add middleware
app.add_middleware(
    RateLimitMiddleware,
    redis_client=redis,
    policy_service=policy_service,
    metrics=metrics,
)
```

### Custom Tenant Extraction

```python
async def extract_tenant(request):
    # Your authentication logic
    token = request.headers.get("Authorization")
    tenant = await validate_token(token)
    return tenant.id, tenant.subscription_tier

app.add_middleware(
    RateLimitMiddleware,
    redis_client=redis,
    tenant_extractor=extract_tenant,
)
```

### Dynamic Policy Management

```python
from maestro_rate_limiting import PolicyService

policy = PolicyService(redis)

# Set tenant-specific override
await policy.set_tenant_override(
    tenant_id="tenant-123",
    requests_per_minute=100,
    requests_per_hour=5000,
    concurrent_requests=100,
)

# Set environment multiplier
await policy.set_environment_multiplier("development", 0.5)  # 50% of normal limits
```

## Default Tiers

| Tier | Requests/Min | Requests/Hour | Concurrent | Monthly Quota |
|------|-------------|---------------|------------|---------------|
| anonymous | 5 | 50 | 5 | 1,000 |
| starter | 10 | 100 | 10 | 10,000 |
| professional | 50 | 1,000 | 50 | 100,000 |
| enterprise | 500 | 10,000 | 200 | 1,000,000 |
| platform_admin | unlimited | unlimited | unlimited | unlimited |

## Response Headers

On every response:
- `X-RateLimit-Limit-Minute` - Requests allowed per minute
- `X-RateLimit-Remaining-Minute` - Requests remaining in current minute
- `X-RateLimit-Limit-Hour` - Requests allowed per hour
- `X-RateLimit-Remaining-Hour` - Requests remaining in current hour
- `X-RateLimit-Reset` - Unix timestamp when limit resets
- `X-RateLimit-Concurrent-Limit` - Max concurrent requests

On 429 rejection:
- `Retry-After` - Seconds to wait before retrying
- `X-RateLimit-Error` - Error type (rate_limit_exceeded, concurrent_limit_exceeded)

## Metrics

If Prometheus is installed, the following metrics are exposed:

- `rate_limit_requests_total` - Total requests by tenant/endpoint/status
- `rate_limit_rejections_total` - Total rejections by tenant/endpoint/reason

## Integration with Other Services

This package is designed to be used by:
- Quality Fabric API
- Maestro Gateway
- Templates Service
- Conductor Service

Each service should install this package and configure with their Redis instance.

## License

Proprietary - Fifth9 Technologies
