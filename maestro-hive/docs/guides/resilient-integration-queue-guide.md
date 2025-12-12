# Resilient Integration Queue - Implementation Guide

## Overview

The Resilient Integration Queue (RIQ) is a middleware layer that provides robust, fault-tolerant communication with external services (JIRA, Confluence). It decouples core processing from external API calls, providing caching, retry logic, rate limiting, and failure recovery.

---

## Architecture

### High-Level View

```
                                    RESILIENT INTEGRATION QUEUE
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                          │
│    ┌─────────────┐                                                    ┌─────────────┐   │
│    │             │         ┌─────────────────────────────────┐        │             │   │
│    │   Your      │  POST   │                                 │        │   JIRA      │   │
│    │   Process   │────────▶│        QUEUE GATEWAY            │        │   API       │   │
│    │             │         │                                 │        │             │   │
│    │  (Caller)   │◀────────│   • Accept request              │        └─────────────┘   │
│    │             │  token  │   • Return tracking token       │               ▲          │
│    └─────────────┘         │   • Check cache (reads)         │               │          │
│           │                │   • Validate & deduplicate      │               │          │
│           │                └─────────────────────────────────┘               │          │
│           │                              │                                   │          │
│           │                              ▼                                   │          │
│           │                ┌─────────────────────────────────┐               │          │
│           │                │                                 │               │          │
│           │                │        QUEUE MANAGER            │               │          │
│           │                │                                 │               │          │
│           │                │   • Persist to database         │               │          │
│           │                │   • Priority queuing            │               │          │
│           │                │   • Dependency resolution       │               │          │
│           │                │   • Authentication management   │               │          │
│           │                │   • Rate limiting               │               │          │
│           │                └─────────────────────────────────┘               │          │
│           │                              │                                   │          │
│           │                              ▼                                   │          │
│           │                ┌─────────────────────────────────┐               │          │
│           │                │                                 │               │          │
│           │                │        WORKER POOL              │───────────────┘          │
│           │                │                                 │                          │
│           │                │   • Process queued requests     │        ┌─────────────┐   │
│           │                │   • Retry with backoff          │        │             │   │
│           │                │   • Circuit breaker             │────────│ Confluence  │   │
│           │                │   • Update results              │        │   API       │   │
│           │                └─────────────────────────────────┘        │             │   │
│           │                              │                            └─────────────┘   │
│           │                              ▼                                              │
│           │                ┌─────────────────────────────────┐                          │
│           │   GET result   │                                 │                          │
│           └───────────────▶│        RESULT STORE             │                          │
│                            │                                 │                          │
│                            │   • Cache completed results     │                          │
│                            │   • Track request status        │                          │
│                            │   • TTL-based expiration        │                          │
│                            └─────────────────────────────────┘                          │
│                                                                                          │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility |
|-----------|----------------|
| **Queue Gateway** | Accept requests, return tokens, check cache, validate |
| **Queue Manager** | Persist requests, manage priorities, handle auth, rate limit |
| **Worker Pool** | Process requests, retry failures, circuit breaker logic |
| **Result Store** | Cache results, track status, enable polling |

---

## How It Works

### Read Operation Flow

```
    Your Process                    Queue System                     External API
         │                               │                                │
         │  1. Submit read request       │                                │
         │──────────────────────────────▶│                                │
         │                               │                                │
         │                               │  2. Check cache                │
         │                               │─────────┐                      │
         │                               │         │                      │
         │                               │◀────────┘                      │
         │                               │                                │
         │  ┌─────────────────────────── │ ───────────────────────────┐   │
         │  │ CACHE HIT                  │                            │   │
         │  │                            │                            │   │
         │  │  3a. Return cached result  │                            │   │
         │◀─┼────────────────────────────│                            │   │
         │  │      (immediate)           │                            │   │
         │  └─────────────────────────── │ ───────────────────────────┘   │
         │                               │                                │
         │  ┌─────────────────────────── │ ───────────────────────────┐   │
         │  │ CACHE MISS                 │                            │   │
         │  │                            │                            │   │
         │  │  3b. Return token          │                            │   │
         │◀─┼────────────────────────────│                            │   │
         │  │      (queued)              │                            │   │
         │  │                            │                            │   │
         │  │                            │  4. Worker processes       │   │
         │  │                            │─────────────────────────────────▶
         │  │                            │                            │   │
         │  │                            │  5. Store result           │   │
         │  │                            │◀────────────────────────────────│
         │  │                            │                            │   │
         │  │  6. Poll for result        │                            │   │
         │──┼───────────────────────────▶│                            │   │
         │  │                            │                            │   │
         │  │  7. Return result          │                            │   │
         │◀─┼────────────────────────────│                            │   │
         │  └─────────────────────────── │ ───────────────────────────┘   │
         │                               │                                │
```

### Write Operation Flow

```
    Your Process                    Queue System                     External API
         │                               │                                │
         │  1. Submit write request      │                                │
         │   (with idempotency key)      │                                │
         │──────────────────────────────▶│                                │
         │                               │                                │
         │                               │  2. Check for duplicate        │
         │                               │─────────┐                      │
         │                               │         │                      │
         │                               │◀────────┘                      │
         │                               │                                │
         │  3. Return token              │                                │
         │     (status: accepted)        │                                │
         │◀──────────────────────────────│                                │
         │                               │                                │
         │                               │  4. Worker processes           │
         │                               │─────────────────────────────────────▶
         │                               │                                │
         │                               │  5. API responds               │
         │                               │◀────────────────────────────────────│
         │                               │                                │
         │                               │  6. Store result               │
         │                               │  7. Invalidate related cache   │
         │                               │                                │
         │  8. Poll for confirmation     │                                │
         │──────────────────────────────▶│                                │
         │                               │                                │
         │  9. Return final status       │                                │
         │◀──────────────────────────────│                                │
         │                               │                                │
```

### Consistency Tokens (Read-after-Write)

To ensure you read the most up-to-date data after a write operation, use **Consistency Tokens**.

1.  **Write:** When you submit a write request, the response includes a `consistency_token`.
2.  **Read:** Pass this token in the `after_consistency_token` field of your subsequent read request.
3.  **Result:** The queue will ensure the read operation waits until the write associated with that consistency token has completed.

```python
# 1. Write
resp = submit("jira.create_task", {...})
ct = resp.consistency_token

# 2. Read (guaranteed to see the new task)
read_resp = submit("jira.get_task", {...}, after_consistency_token=ct)
```

---

> ### REVIEW COMMENTS & RECOMMENDATIONS
>
> **Reviewer:** Architecture Review (2025-12-11)
> **Status:** PENDING DISCUSSION
>
> #### 1. Consider Simpler Alternative First
>
> **Concern:** Consistency tokens add significant implementation complexity (token generation,
> storage, lookup, expiry management). For JIRA/Confluence use cases, a simpler approach may suffice.
>
> **Recommendation:** Implement BOTH options:
>
> | Option | Use Case | Complexity |
> |--------|----------|------------|
> | `fresh=true` flag | Simple "skip cache" - covers 80% of needs | Low |
> | `after_consistency_token` | Strict ordering requirements - 20% of needs | High |
>
> ```python
> # SIMPLER ALTERNATIVE - Add fresh=true parameter
> read_resp = submit("jira.get_task", {"task_id": "MD-123"}, fresh=True)
> # Bypasses cache, fetches directly from API
> ```
>
> #### 2. Missing Token Lifecycle Documentation
>
> **Concern:** The current documentation does not specify:
> - How long do consistency tokens live? (TTL)
> - What happens if the token expires before the read?
> - What happens if the associated write fails?
> - Can tokens be reused for multiple reads?
>
> **Recommendation:** Add configuration section:
>
> ```yaml
> consistency_tokens:
>   ttl: 300                    # 5 minutes
>   single_use: false           # Can be used for multiple reads
>   on_write_failure: invalidate  # Token becomes unusable
>   on_expiry_error: "CONSISTENCY_TOKEN_EXPIRED"
> ```
>
> #### 3. Overengineering Consideration
>
> **Concern:** For JIRA/Confluence specifically, do we need this level of sophistication?
>
> | Scenario | Consistency Token Needed? |
> |----------|--------------------------|
> | Create task, then GET same task | **No** - JIRA direct GET is consistent |
> | Create task, then SEARCH for it | **Yes** - search index has lag |
> | Update task, GET same task | **No** - direct GET is consistent |
> | Batch create, then list all | **Yes** - need all creates visible |
>
> **Recommendation:** Start with `fresh=true` flag. Add consistency tokens only if
> real consistency issues are observed in production. Measure before optimizing.
>
> #### 4. Decision Required
>
> - [ ] Implement `fresh=true` as simpler alternative
> - [ ] Add token lifecycle configuration
> - [ ] Document when consistency tokens are actually needed vs overkill
> - [ ] Consider phased rollout: Phase 1 = fresh flag, Phase 2 = consistency tokens (if needed)

---

## API Reference

### Submit Request

Submit a read or write operation to the queue.

**Endpoint:** `POST /api/queue/submit`

**Request Body:**

```json
{
    "operation": "jira.get_task",
    "payload": {
        "task_id": "MD-123"
    },
    "priority": "normal",
    "idempotency_key": "optional-unique-key",
    "depends_on": [],
    "after_consistency_token": "ct_xyz789",
    "callback_url": "https://your-webhook.com/callback",
    "fire_and_forget": false
}
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `operation` | string | Yes | Operation to perform (see Operations table) |
| `payload` | object | Yes | Operation-specific parameters |
| `priority` | string | No | `high`, `normal`, `low` (default: `normal`) |
| `idempotency_key` | string | No | Unique key to prevent duplicates |
| `depends_on` | array | No | List of tokens that must complete first |
| `after_consistency_token` | string | No | Wait for this consistency token before executing |
| `callback_url` | string | No | Webhook URL for completion notification |
| `fire_and_forget` | boolean | No | Skip confirmation requirement (default: `false`) |

**Response (Queued):**

```json
{
    "token": "req_abc123xyz",
    "status": "queued",
    "position": 5,
    "consistency_token": "ct_xyz789",
    "estimated_completion": "2025-12-11T21:30:00Z",
    "poll_url": "/api/queue/result/req_abc123xyz"
}
```

**Response (Cached - for reads only):**

```json
{
    "token": "req_abc123xyz",
    "status": "cached",
    "result": {
        "id": "MD-123",
        "title": "Example Task",
        "status": "In Progress"
    },
    "cached_at": "2025-12-11T21:25:00Z",
    "cache_ttl": 300
}
```

---

### Get Result

Retrieve the result of a queued request.

**Endpoint:** `GET /api/queue/result/{token}`

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `wait` | integer | 0 | Seconds to wait for completion (long-poll) |

**Response (Pending):**

```json
{
    "token": "req_abc123xyz",
    "status": "processing",
    "progress": 0.5,
    "message": "Authenticating with JIRA...",
    "started_at": "2025-12-11T21:29:30Z"
}
```

**Response (Completed):**

```json
{
    "token": "req_abc123xyz",
    "status": "completed",
    "result": {
        "id": "MD-123",
        "title": "Example Task",
        "status": "Done"
    },
    "completed_at": "2025-12-11T21:29:45Z",
    "duration_ms": 1250
}
```

**Response (Failed):**

```json
{
    "token": "req_abc123xyz",
    "status": "failed",
    "error": {
        "code": "RATE_LIMITED",
        "message": "JIRA API rate limit exceeded",
        "retry_after": 60,
        "retries_exhausted": true,
        "attempts": 3
    },
    "failed_at": "2025-12-11T21:29:45Z"
}
```

---

### Available Operations

#### JIRA Operations

| Operation | Description | Payload |
|-----------|-------------|---------|
| `jira.get_task` | Get task by ID | `{"task_id": "MD-123"}` |
| `jira.create_task` | Create new task | `{"title": "...", "description": "...", "project_id": "MD"}` |
| `jira.update_task` | Update existing task | `{"task_id": "MD-123", "title": "...", "description": "..."}` |
| `jira.transition_task` | Change task status | `{"task_id": "MD-123", "target_status": "Done"}` |
| `jira.add_comment` | Add comment to task | `{"task_id": "MD-123", "comment": "..."}` |
| `jira.search_tasks` | Search tasks | `{"jql": "project=MD AND status='To Do'"}` |
| `jira.get_epic_children` | Get epic's child tasks | `{"epic_id": "MD-100"}` |

#### Confluence Operations

| Operation | Description | Payload |
|-----------|-------------|---------|
| `confluence.get_page` | Get page by ID | `{"page_id": "12345"}` |
| `confluence.create_page` | Create new page | `{"title": "...", "content": "...", "space_id": "MD"}` |
| `confluence.update_page` | Update existing page | `{"page_id": "12345", "title": "...", "content": "..."}` |
| `confluence.delete_page` | Delete page | `{"page_id": "12345"}` |
| `confluence.search_pages` | Search pages | `{"query": "authentication", "space_id": "MD"}` |

---

## Usage Examples

### Python Client

```python
from queue_client import QueueClient

# Initialize client
client = QueueClient(base_url="http://localhost:8080")

# ============================================================
# READ OPERATION (with automatic caching)
# ============================================================

# Submit read request
response = await client.submit(
    operation="jira.get_task",
    payload={"task_id": "MD-123"}
)

if response.status == "cached":
    # Cache hit - result available immediately
    task = response.result
    print(f"Task: {task['title']} (cached)")
else:
    # Cache miss - poll for result
    result = await client.wait_for_result(response.token, timeout=30)
    if result.status == "completed":
        task = result.result
        print(f"Task: {task['title']}")
    else:
        print(f"Error: {result.error}")

# ============================================================
# WRITE OPERATION (with confirmation)
# ============================================================

# Submit write request with idempotency key
response = await client.submit(
    operation="jira.create_task",
    payload={
        "title": "New Feature",
        "description": "Implement user authentication",
        "project_id": "MD",
        "priority": "High"
    },
    idempotency_key=f"create_auth_feature_{uuid4()}"
)

# IMPORTANT: For writes, always confirm completion
result = await client.wait_for_result(response.token, timeout=60)

if result.status == "completed":
    new_task = result.result
    print(f"Created: {new_task['id']}")
else:
    print(f"Failed: {result.error}")
    # Handle failure - maybe retry or alert

# ============================================================
# DEPENDENT OPERATIONS (ordered execution)
# ============================================================

# Step 1: Create task
create_response = await client.submit(
    operation="jira.create_task",
    payload={"title": "New Task", "project_id": "MD"}
)

# Step 2: Add comment (depends on task creation)
comment_response = await client.submit(
    operation="jira.add_comment",
    payload={
        "task_id": "$result.data.id",  # Reference result of previous
        "comment": "Initial setup complete"
    },
    depends_on=[create_response.token]  # Won't execute until step 1 completes
)

# Wait for both to complete
await client.wait_for_result(comment_response.token, timeout=60)

# ============================================================
# FIRE-AND-FORGET (when confirmation not needed)
# ============================================================

# For non-critical operations like logging
await client.submit(
    operation="jira.add_comment",
    payload={
        "task_id": "MD-123",
        "comment": "Automated status update: Build passed"
    },
    fire_and_forget=True  # Don't wait for confirmation
)
```

### Synchronous Wrapper (for existing code)

```python
from queue_client import SyncQueueClient

# For code that can't be easily converted to async
client = SyncQueueClient(base_url="http://localhost:8080")

# Behaves like the old synchronous adapter
task = client.jira.get_task("MD-123")
print(f"Task: {task.title}")

# Create task (blocks until complete)
new_task = client.jira.create_task(
    title="New Feature",
    description="...",
    project_id="MD"
)
print(f"Created: {new_task.id}")
```

---

## Queue Manager Features

### Priority Queuing

Requests are processed by priority:

```
HIGH PRIORITY QUEUE      ──▶  Processed first
    │
    ├── Urgent bug fixes
    ├── User-initiated actions
    └── Time-sensitive updates

NORMAL PRIORITY QUEUE    ──▶  Processed second
    │
    ├── Background syncs
    ├── Scheduled updates
    └── Batch operations

LOW PRIORITY QUEUE       ──▶  Processed last
    │
    ├── Analytics/metrics
    ├── Non-critical logging
    └── Cleanup operations
```

### Rate Limiting

Per-service rate limits prevent API quota exhaustion:

```yaml
rate_limits:
  jira:
    requests_per_minute: 100
    burst_limit: 20           # Max concurrent requests
    backoff_on_429: true      # Automatic backoff on rate limit response

  confluence:
    requests_per_minute: 50
    burst_limit: 10
    backoff_on_429: true
```

### Adaptive Routing (Intelligent Load Management)

For bursty traffic patterns (e.g., 500 requests in a burst, then 10 minutes idle), the queue provides **adaptive routing** that automatically chooses between direct API calls and queued processing:

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                      ADAPTIVE ROUTING DECISION FLOW                                  │
│                                                                                      │
│   Incoming Request                                                                   │
│         │                                                                            │
│         ▼                                                                            │
│   ┌─────────────────────────────────────┐                                           │
│   │  1. Circuit Breaker Check           │                                           │
│   │     Is service healthy?             │                                           │
│   └─────────────────────────────────────┘                                           │
│         │                                                                            │
│         ├── OPEN ────────────────────────────────────────▶ QUEUE (service down)     │
│         │                                                                            │
│         ▼ CLOSED                                                                     │
│   ┌─────────────────────────────────────┐                                           │
│   │  2. Token Bucket Check              │                                           │
│   │     Available capacity?             │                                           │
│   └─────────────────────────────────────┘                                           │
│         │                                                                            │
│         ├── YES (tokens available) ──────▶ DIRECT API CALL (fast path, ~200ms)      │
│         │                                                                            │
│         ▼ NO (bucket empty)                                                          │
│   ┌─────────────────────────────────────┐                                           │
│   │  3. Queue for Smoothing             │                                           │
│   │     Process at steady rate          │                                           │
│   └─────────────────────────────────────┘──▶ QUEUED (processed at 100/min rate)     │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

**Example Scenario:**

| Time | Incoming | Bucket | Direct | Queued | Notes |
|------|----------|--------|--------|--------|-------|
| T0 | 500 requests | 50 | 50 | 450 | Burst arrives, bucket drains |
| T0+1min | 0 | ~100 | - | ~350 | Queue drains, bucket refills |
| T0+2min | 0 | ~100 | - | ~250 | Continued processing |
| T0+5min | 0 | 50 (max) | - | 0 | Queue empty, bucket full |
| T0+10min | 100 | 50 | 50 | 50 | New burst, immediate + queued |

**Configuration:**

```yaml
adaptive_routing:
  enabled: true

  # Token Bucket (controls burst capacity)
  token_bucket:
    rate: 100          # tokens per minute (matches API limit)
    burst: 50          # max bucket capacity (instant requests)

  # Direct path settings
  direct:
    timeout: 5s        # Fast timeout for direct calls
    on_failure: queue  # Fallback to queue on error

  # Queue path settings
  queue:
    drain_rate: 100    # requests per minute (matches API limit)
    max_depth: 10000   # max pending requests

  # Metrics
  metrics:
    track_routing_decisions: true
    track_latency_by_path: true
```

**Python Usage:**

```python
from queue_client import AdaptiveQueueClient

client = AdaptiveQueueClient(
    base_url="http://localhost:8080",
    mode="adaptive"  # Options: "direct", "queue", "adaptive"
)

# Client automatically routes based on capacity
for i in range(500):
    result = await client.submit(
        operation="jira.get_task",
        payload={"task_id": f"MD-{i}"}
    )

    # result.routing_path tells you which path was taken
    print(f"Request {i}: {result.routing_path} - {result.status}")
    # Output:
    # Request 0: DIRECT - completed (fast)
    # Request 49: DIRECT - completed (fast)
    # Request 50: QUEUED - queued (at capacity)
    # Request 499: QUEUED - queued (processing at 100/min)
```

**Benefits:**
- **Low latency** when under capacity (direct path ~200ms)
- **No rejected requests** when over capacity (queue absorbs burst)
- **Automatic adaptation** to traffic patterns
- **Graceful degradation** under load

### Circuit Breaker

Protects against cascading failures:

```
           CLOSED                    OPEN                   HALF-OPEN
        (Normal State)          (Fail Fast)              (Testing)
              │                       │                       │
              │  Failures exceed      │  Recovery timeout     │
              │  threshold (5)        │  expires (60s)        │
              │──────────────────────▶│──────────────────────▶│
              │                       │                       │
              │                       │                       │  Success
              │◀──────────────────────│◀──────────────────────│──────┐
              │     All systems go    │     Test requests     │      │
              │                       │     succeed           │      │
              │                       │                       │◀─────┘
              │                       │                       │
              │                       │◀──────────────────────│  Failure
              │                       │     Test request      │
              │                       │     fails             │
```

**States:**

| State | Behavior | Duration |
|-------|----------|----------|
| **CLOSED** | Normal operation, requests proceed | Until 5 failures |
| **OPEN** | All requests fail immediately | 60 seconds |
| **HALF-OPEN** | Allow 3 test requests | Until success/failure |

### Request Deduplication

Idempotency keys prevent duplicate operations:

```python
# First request - processed normally
await client.submit(
    operation="jira.create_task",
    payload={"title": "New Task"},
    idempotency_key="create_task_abc123"
)

# Second request with same key - returns original token
# (not re-queued, no duplicate created)
await client.submit(
    operation="jira.create_task",
    payload={"title": "New Task"},
    idempotency_key="create_task_abc123"  # Same key
)
```

---

## Authentication Management

### Token Lifecycle

The Queue Manager handles all authentication automatically:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        TOKEN MANAGER                                        │
│                                                                             │
│   ┌───────────────┐      ┌───────────────┐      ┌───────────────┐          │
│   │               │      │               │      │               │          │
│   │  Check Token  │─────▶│  Valid?       │─────▶│  Use Token    │          │
│   │               │      │               │ Yes  │               │          │
│   └───────────────┘      └───────────────┘      └───────────────┘          │
│                                │                                            │
│                                │ No / Expiring Soon                         │
│                                ▼                                            │
│                          ┌───────────────┐                                  │
│                          │               │                                  │
│                          │  Refresh      │────▶ Store new token             │
│                          │  Token        │                                  │
│                          │               │                                  │
│                          └───────────────┘                                  │
│                                                                             │
│   Proactive refresh: Refresh 5 minutes before expiry                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Configuration

```yaml
authentication:
  jira:
    type: api_token
    email: ${JIRA_EMAIL}
    api_token: ${JIRA_API_TOKEN}
    token_refresh_buffer: 300  # Refresh 5 min before expiry

  confluence:
    type: api_token
    email: ${CONFLUENCE_EMAIL}
    api_token: ${CONFLUENCE_API_TOKEN}
    token_refresh_buffer: 300
```

---

## Caching Strategy

### Cache Rules

| Operation Type | Cacheable | TTL | Invalidation |
|---------------|-----------|-----|--------------|
| `*.get_*` | Yes | 5 min | On update to same entity |
| `*.search_*` | Yes | 2 min | On any create/update in scope |
| `*.create_*` | No | - | - |
| `*.update_*` | No | - | Invalidates related read cache |
| `*.delete_*` | No | - | Invalidates related read cache |

### Cache Invalidation

When writes complete, related cache entries are invalidated:

```
WRITE: jira.update_task(MD-123)
    │
    ├──▶ Invalidate: jira.get_task(MD-123)
    │
    ├──▶ Invalidate: jira.search_tasks(project=MD)
    │
    └──▶ Invalidate: jira.get_epic_children(parent of MD-123)
```

---

## Adaptive Routing Configuration

To handle bursty traffic (e.g., 500 requests at once) against a strict limit (100/min), configure the `rate_limits` and `adaptive_concurrency` settings.

### Configuration Example

```python
QUEUE_CONFIG = {
    "rate_limits": {
        "jira": {
            "rate": 100,       # requests per minute
            "burst": 50,       # max instant burst
            "algorithm": "token_bucket"
        }
    },
    "adaptive_concurrency": {
        "enabled": True,
        "min_concurrency": 2,
        "max_concurrency": 20,
        "latency_target_ms": 500  # Backoff if latency exceeds this
    }
}
```

### Python Implementation Snippet

```python
class TokenBucket:
    def __init__(self, rate_per_minute, burst_capacity):
        self.capacity = burst_capacity
        self.tokens = burst_capacity
        self.rate = rate_per_minute / 60.0
        self.last_update = time.time()

    def consume(self, tokens=1):
        now = time.time()
        # Refill
        elapsed = now - self.last_update
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last_update = now

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
```

---

## Error Handling

### Retry Strategy

Failed requests are retried with exponential backoff:

```
Attempt 1: Immediate
    │
    │ Failure
    ▼
Attempt 2: Wait 1-2 seconds (base + jitter)
    │
    │ Failure
    ▼
Attempt 3: Wait 2-4 seconds
    │
    │ Failure
    ▼
Attempt 4: Wait 4-8 seconds
    │
    │ Failure
    ▼
Move to Dead Letter Queue
```

### Dead Letter Queue

Requests that fail after all retries are moved to dead letter queue:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        DEAD LETTER HANDLING                                 │
│                                                                             │
│   TIER 1 (0-24 hours)                                                       │
│   ├── Hold for automatic retry when service recovers                        │
│   └── Retry automatically when circuit breaker closes                       │
│                                                                             │
│   TIER 2 (24-72 hours)                                                      │
│   ├── Escalate to monitoring webhook                                        │
│   ├── Create JIRA bug ticket for visibility                                 │
│   └── Available for manual retry via API                                    │
│                                                                             │
│   TIER 3 (72+ hours)                                                        │
│   ├── Archive to long-term storage (S3)                                     │
│   ├── Retain for 90 days for forensics                                      │
│   └── Delete after retention period                                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Error Codes

| Code | Description | Recovery |
|------|-------------|----------|
| `RATE_LIMITED` | API rate limit hit | Automatic retry after backoff |
| `AUTH_FAILED` | Authentication error | Token refresh and retry |
| `NOT_FOUND` | Resource doesn't exist | No retry (permanent failure) |
| `VALIDATION_ERROR` | Invalid payload | No retry (fix payload) |
| `TIMEOUT` | Request timed out | Automatic retry |
| `SERVICE_UNAVAILABLE` | External service down | Circuit breaker + retry |
| `DEPENDENCY_FAILED` | Dependent request failed | No retry (fix dependency) |

---

## Monitoring

### Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `queue_depth` | Gauge | Number of pending requests |
| `queue_latency_seconds` | Histogram | Time from submit to completion |
| `processing_time_seconds` | Histogram | Time to execute API call |
| `cache_hit_ratio` | Gauge | Percentage of reads served from cache |
| `retry_total` | Counter | Total retry attempts |
| `dead_letter_total` | Counter | Requests moved to dead letter |
| `circuit_breaker_state` | Gauge | 1=closed, 0.5=half-open, 0=open |

### Health Endpoint

**Endpoint:** `GET /api/queue/health`

```json
{
    "status": "healthy",
    "components": {
        "queue_manager": "healthy",
        "worker_pool": "healthy",
        "cache": "healthy",
        "database": "healthy"
    },
    "stats": {
        "queue_depth": 12,
        "workers_active": 5,
        "workers_idle": 3,
        "cache_hit_ratio": 0.73,
        "requests_per_minute": 45
    },
    "circuit_breakers": {
        "jira": "closed",
        "confluence": "closed"
    }
}
```

### Dead Letter Dashboard

**Endpoint:** `GET /api/queue/dead-letters`

```json
{
    "total": 3,
    "items": [
        {
            "token": "req_failed123",
            "operation": "jira.create_task",
            "failed_at": "2025-12-11T20:00:00Z",
            "error": "RATE_LIMITED",
            "attempts": 3,
            "tier": 1,
            "retry_url": "/api/queue/dead-letters/req_failed123/retry"
        }
    ]
}
```

**Manual Retry:** `POST /api/queue/dead-letters/{token}/retry`

---

## Configuration Reference

### Full Configuration File

```yaml
# config/queue.yaml

queue:
  # Database storage for requests
  storage:
    type: postgresql
    connection_string: ${DATABASE_URL}
    pool_size: 10

  # Redis cache for results
  cache:
    type: redis
    url: ${REDIS_URL}
    default_ttl: 300  # 5 minutes
    max_memory: 256mb

  # Worker pool configuration
  workers:
    min_count: 2
    max_count: 10
    scaling_policy: adaptive  # Scale based on queue depth
    idle_timeout: 60  # Seconds before scaling down

    # Per-service configuration
    services:
      jira:
        max_workers: 5
        rate_limit: 100  # requests per minute
        burst_limit: 20
        timeout: 30  # seconds

      confluence:
        max_workers: 3
        rate_limit: 50
        burst_limit: 10
        timeout: 30

  # Circuit breaker settings
  circuit_breaker:
    failure_threshold: 5      # Failures to open circuit
    recovery_timeout: 60      # Seconds before half-open
    half_open_requests: 3     # Test requests in half-open

  # Retry configuration
  retry:
    max_attempts: 3
    base_delay: 1.0           # seconds
    max_delay: 60.0           # seconds
    jitter: true              # Add randomness

  # Dead letter handling
  dead_letter:
    tier1_duration: 24h
    tier2_duration: 72h
    archive_bucket: s3://dead-letters/
    retention_days: 90
    escalation_webhook: ${ALERT_WEBHOOK_URL}

  # Authentication
  authentication:
    jira:
      base_url: https://fifth9.atlassian.net
      email: ${JIRA_EMAIL}
      api_token: ${JIRA_API_TOKEN}

    confluence:
      base_url: https://fifth9.atlassian.net
      email: ${CONFLUENCE_EMAIL}
      api_token: ${CONFLUENCE_API_TOKEN}

  # Monitoring
  monitoring:
    metrics_endpoint: /metrics
    health_endpoint: /health
    prometheus_enabled: true
```

---

## Migration Guide

### From Direct Adapters to Queued Adapters

**Before (Direct):**

```python
from services.integration.adapters.jira_adapter import JiraAdapter

adapter = JiraAdapter(base_url="http://localhost:14100", token=token)
result = await adapter.get_task("MD-123")

if result.success:
    task = result.data
else:
    # Handle error (no retry, no caching)
    print(f"Error: {result.error}")
```

**After (Queued):**

```python
from services.integration.adapters.queued_jira_adapter import QueuedJiraAdapter

adapter = QueuedJiraAdapter(queue_gateway=gateway)
result = await adapter.get_task("MD-123")

if result.success:
    task = result.data  # May be from cache
else:
    # Error after retries exhausted
    print(f"Error: {result.error}")
```

**The interface is identical** - just swap the adapter class. The queued adapter handles caching, retries, and rate limiting automatically.

---

## Troubleshooting

### Request Stuck in Queue

**Symptoms:** Request shows "queued" status for extended time

**Causes & Solutions:**

| Cause | Solution |
|-------|----------|
| Workers overwhelmed | Check queue depth metric, scale workers |
| Circuit breaker open | Check circuit_breaker_state metric, wait for recovery |
| Dependency not completing | Check depends_on request status |
| Rate limit backoff | Wait for backoff period to expire |

### High Cache Miss Rate

**Symptoms:** cache_hit_ratio below 50%

**Causes & Solutions:**

| Cause | Solution |
|-------|----------|
| TTL too short | Increase cache TTL |
| Too many unique queries | Consider query normalization |
| Writes invalidating cache | Review invalidation rules |
| Cache memory full | Increase Redis max_memory |

### Dead Letters Accumulating

**Symptoms:** dead_letter_total increasing

**Causes & Solutions:**

| Cause | Solution |
|-------|----------|
| Persistent API errors | Check external service status |
| Authentication issues | Verify API tokens |
| Invalid payloads | Review payload validation |
| Rate limits | Reduce request rate |

---

## Related Documents

- [ADR-007: Resilient Integration Queue](../adr/007-resilient-integration-queue.md) - Architecture decision record
- [JIRA Adapter](../../services/integration/adapters/jira_adapter.py) - Current JIRA adapter
- [Confluence Adapter](../../services/integration/adapters/confluence_adapter.py) - Current Confluence adapter

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-11 | Initial documentation |
