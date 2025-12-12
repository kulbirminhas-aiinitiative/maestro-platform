# Resilient Integration Queue - Quick Reference

## Architecture at a Glance

```
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│ Process │────▶│ Gateway │────▶│  Queue  │────▶│ Workers │────▶│ External│
│         │◀────│ + Cache │◀────│ Manager │◀────│ + Retry │◀────│   API   │
└─────────┘     └─────────┘     └─────────┘     └─────────┘     └─────────┘
   token           cache           persist        circuit         JIRA/
   polling          TTL            + auth         breaker       Confluence
```

---

## API Quick Reference

### Submit Request

```bash
POST /api/queue/submit
{
    "operation": "jira.get_task",
    "payload": {"task_id": "MD-123"},
    "priority": "normal",
    "idempotency_key": "unique-key",
    "depends_on": ["req_token1"]
}

# Response
{
    "token": "req_abc123",
    "status": "queued" | "cached",
    "poll_url": "/api/queue/result/req_abc123"
}
```

### Get Result

```bash
GET /api/queue/result/{token}?wait=30

# Response
{
    "token": "req_abc123",
    "status": "completed" | "failed" | "processing",
    "result": {...},
    "error": {...}
}
```

---

## Operations

### JIRA

| Operation | Payload |
|-----------|---------|
| `jira.get_task` | `{"task_id": "MD-123"}` |
| `jira.create_task` | `{"title": "...", "project_id": "MD"}` |
| `jira.update_task` | `{"task_id": "MD-123", "title": "..."}` |
| `jira.transition_task` | `{"task_id": "MD-123", "target_status": "Done"}` |
| `jira.add_comment` | `{"task_id": "MD-123", "comment": "..."}` |
| `jira.search_tasks` | `{"jql": "project=MD"}` |

### Confluence

| Operation | Payload |
|-----------|---------|
| `confluence.get_page` | `{"page_id": "12345"}` |
| `confluence.create_page` | `{"title": "...", "content": "...", "space_id": "MD"}` |
| `confluence.update_page` | `{"page_id": "12345", "content": "..."}` |
| `confluence.search_pages` | `{"query": "...", "space_id": "MD"}` |

---

## Python Client

```python
from queue_client import QueueClient

client = QueueClient("http://localhost:8080")

# READ (with caching)
response = await client.submit(
    operation="jira.get_task",
    payload={"task_id": "MD-123"}
)

if response.status == "cached":
    task = response.result
else:
    result = await client.wait_for_result(response.token, timeout=30)
    task = result.result

# WRITE (with confirmation)
response = await client.submit(
    operation="jira.create_task",
    payload={"title": "New Task", "project_id": "MD"},
    idempotency_key=f"create_{uuid4()}"
)

result = await client.wait_for_result(response.token, timeout=60)
if result.status == "completed":
    new_task = result.result

# READ-AFTER-WRITE (Consistency)
# Ensure we see the task we just created
read_response = await client.submit(
    operation="jira.get_task",
    payload={"task_id": new_task['id']},
    after_consistency_token=response.consistency_token
)
task = await client.wait_for_result(read_response.token)
```

> **REVIEW: BUG IN EXAMPLE ABOVE**
>
> The example assumes `response.consistency_token` always exists. It won't exist
> for cached responses. Correct implementation:
>
> ```python
> # CORRECTED VERSION
> result = await client.wait_for_result(response.token, timeout=60)
> if result.status == "completed":
>     new_task = result.result
>
>     # Check if consistency token exists (only for queued, not cached)
>     if hasattr(response, 'consistency_token') and response.consistency_token:
>         read_response = await client.submit(
>             operation="jira.get_task",
>             payload={"task_id": new_task['id']},
>             after_consistency_token=response.consistency_token
>         )
>     else:
>         # No consistency token - use fresh=true as simpler alternative
>         read_response = await client.submit(
>             operation="jira.get_task",
>             payload={"task_id": new_task['id']},
>             fresh=True  # RECOMMENDED: Simpler approach
>         )
>     task = await client.wait_for_result(read_response.token)
> ```
>
> **RECOMMENDATION:** Consider using `fresh=True` as the default pattern for
> read-after-write. It's simpler and covers most JIRA/Confluence use cases.

---

## Status Values

| Status | Meaning | Action |
|--------|---------|--------|
| `queued` | Waiting in queue | Poll for result |
| `processing` | Being executed | Poll for result |
| `completed` | Success | Use `result` field |
| `failed` | Error after retries | Check `error` field |
| `cached` | From cache (reads) | Use `result` field |
| `dead` | In dead letter queue | Manual intervention |

---

## Priorities

| Priority | Use Case | Processing |
|----------|----------|------------|
| `high` | User actions, urgent fixes | First |
| `normal` | Regular operations | Second |
| `low` | Background tasks, analytics | Last |

---

## Cache TTLs

| Operation Type | TTL | Invalidation |
|---------------|-----|--------------|
| `*.get_*` | 5 min | On update |
| `*.search_*` | 2 min | On any write |
| `*.create/update/delete_*` | No cache | Invalidates reads |

---

## Adaptive Routing (Bursty Traffic)

**Problem:** API limit 100/min, but traffic is bursty (500 requests, then idle).

**Solution:** Intelligent routing - direct when capacity available, queue when over.

```
Request ──▶ Circuit Breaker ──▶ Token Bucket ──▶ Decision
                 │                    │
            OPEN? ───▶ QUEUE     TOKENS? ───▶ DIRECT (fast)
                                     │
                                EMPTY? ───▶ QUEUED (smoothed)

500 requests at T0:
├── 50 → DIRECT (burst capacity, immediate)
└── 450 → QUEUED (processed at 100/min ≈ 4.5 minutes)
```

**Config:**

```yaml
adaptive_routing:
  token_bucket: {rate: 100, burst: 50}
  direct: {on_failure: queue}
```

**Usage:**

```python
client = AdaptiveQueueClient(mode="adaptive")
result = await client.submit("jira.get_task", {...})
# result.routing_path: "DIRECT" or "QUEUED"
```

| Routing Path | When | Latency |
|--------------|------|---------|
| DIRECT | Tokens available | ~200ms |
| QUEUED | Over capacity | Variable (queue wait + ~200ms) |

---

## Circuit Breaker States

```
CLOSED ──(5 failures)──▶ OPEN ──(60s)──▶ HALF-OPEN
   ▲                                         │
   └───────────(success)─────────────────────┘
```

---

## Retry Schedule

| Attempt | Wait Time |
|---------|-----------|
| 1 | Immediate |
| 2 | 1-2 seconds |
| 3 | 2-4 seconds |
| 4 | 4-8 seconds |
| Dead Letter | After 4 failures |

---

## Error Codes

| Code | Retry? | Meaning |
|------|--------|---------|
| `RATE_LIMITED` | Yes | API quota hit |
| `AUTH_FAILED` | Yes | Token refresh needed |
| `TIMEOUT` | Yes | Request timed out |
| `SERVICE_UNAVAILABLE` | Yes | External service down |
| `NOT_FOUND` | No | Resource doesn't exist |
| `VALIDATION_ERROR` | No | Invalid payload |
| `DEPENDENCY_FAILED` | No | Dependent request failed |

---

## Key Endpoints

| Endpoint | Purpose |
|----------|---------|
| `POST /api/queue/submit` | Submit request |
| `GET /api/queue/result/{token}` | Get result |
| `GET /api/queue/health` | Health check |
| `GET /api/queue/dead-letters` | List failures |
| `POST /api/queue/dead-letters/{token}/retry` | Retry failure |

---

## Configuration

```yaml
queue:
  workers:
    jira: {max: 5, rate: 100/min}
    confluence: {max: 3, rate: 50/min}

  circuit_breaker:
    failure_threshold: 5
    recovery_timeout: 60s

  retry:
    max_attempts: 3
    base_delay: 1s
    max_delay: 60s

  adaptive_concurrency:
    enabled: true
    min_concurrency: 2
    max_concurrency: 20
    latency_target_ms: 500

  cache:
    default_ttl: 300s
```

---

## Monitoring Metrics

| Metric | Description |
|--------|-------------|
| `queue_depth` | Pending requests |
| `queue_latency_seconds` | Submit to complete time |
| `cache_hit_ratio` | Cache effectiveness |
| `circuit_breaker_state` | 1=closed, 0.5=half-open, 0=open |
| `dead_letter_total` | Failed requests |

---

## Common Patterns

### Dependent Operations

```python
# Create then comment
create = await client.submit(operation="jira.create_task", ...)
comment = await client.submit(
    operation="jira.add_comment",
    depends_on=[create.token]
)
```

### Fire and Forget

```python
# Non-critical logging
await client.submit(
    operation="jira.add_comment",
    fire_and_forget=True
)
```

### Idempotent Writes

```python
# Prevent duplicates on retry
await client.submit(
    operation="jira.create_task",
    idempotency_key=f"create_{hash(payload)}"
)
```

### Fresh Read (Simple Cache Bypass)

```python
# RECOMMENDED: Simpler than consistency tokens for most cases
await client.submit(
    operation="jira.get_task",
    payload={"task_id": "MD-123"},
    fresh=True  # Skip cache, fetch from API
)
```

---

## Review Status

> **Architecture Review:** 2025-12-11
>
> | Item | Status | Notes |
> |------|--------|-------|
> | Core queue architecture | APPROVED | Solid design |
> | Adaptive routing | APPROVED | Token bucket + queue leveling |
> | Token bucket algorithm | APPROVED | Industry standard (AWS, Stripe) |
> | Queue-based load leveling | APPROVED | Handles bursty traffic well |
> | Consistency tokens | NEEDS DISCUSSION | May be overengineered |
> | `fresh=true` alternative | RECOMMENDED | Add as simpler option |
> | Token lifecycle docs | MISSING | Need TTL, expiry handling |
> | Example code bug | IDENTIFIED | Null check needed |
>
> **Real-World References:**
> - [Netflix Adaptive Concurrency Limits](https://netflixtechblog.medium.com/performance-under-load-3e6fa9a60581)
> - [AWS API Gateway Throttling](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-request-throttling.html)
> - [Azure Queue-Based Load Leveling](https://learn.microsoft.com/en-us/azure/architecture/patterns/queue-based-load-leveling)
> - [Envoy Adaptive Concurrency](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/adaptive_concurrency_filter)
> - [Uber Cinnamon Auto-Tuner](https://www.uber.com/blog/cinnamon-auto-tuner-adaptive-concurrency-in-the-wild/)
>
> **Open Questions:**
> 1. Do we need consistency tokens for JIRA/Confluence, or is `fresh=true` sufficient?
> 2. What is the consistency token TTL and expiry behavior?
> 3. Should we implement phased: Phase 1 = fresh flag, Phase 2 = tokens if needed?
