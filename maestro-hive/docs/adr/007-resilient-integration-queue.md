# ADR-007: Resilient Integration Queue for External Services

**Status:** Proposed
**Date:** 2025-12-11
**Author:** Architecture Team
**Deciders:** Platform Team
**Technical Story:** Improve robustness of JIRA/Confluence integration adapters

---

## Context

### Current State Analysis

The current adapter architecture (`JiraAdapter`, `ConfluenceAdapter`) has the following characteristics:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CURRENT ARCHITECTURE                                │
│                                                                             │
│   ┌──────────────┐          ┌──────────────┐          ┌──────────────┐     │
│   │   Process    │──────────│   Adapter    │──────────│  External    │     │
│   │  (Caller)    │  sync    │  (JIRA/      │  HTTP    │  Service     │     │
│   │              │  call    │  Confluence) │  30s     │  (Atlassian) │     │
│   └──────────────┘          └──────────────┘          └──────────────┘     │
│         │                          │                         │              │
│         │                          │                         │              │
│         └────────── BLOCKS ────────┴─────── WAITS ──────────┘              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Identified Issues:**

| Issue | Impact | Current Code Reference |
|-------|--------|------------------------|
| Synchronous blocking | Caller blocked for 30s on timeout | `httpx.AsyncClient(timeout=30.0)` |
| No retry mechanism | Single failure = complete failure | `except Exception as e: return AdapterResult(success=False)` |
| No rate limiting | Risk of API quota exhaustion | None implemented |
| No circuit breaker | Cascading failures possible | None implemented |
| No caching | Redundant API calls | None implemented |
| Hardcoded timeout | Inflexible for varying operations | `timeout=30.0` |
| Single point of failure | External outage = system failure | Direct HTTP calls |
| No request deduplication | Duplicate requests waste quota | None implemented |

---

## Problem Statement

External service integrations (JIRA, Confluence) are unreliable due to:
1. **Network issues** - Transient failures, timeouts
2. **Rate limiting** - Atlassian enforces API quotas
3. **Service outages** - External downtime affects our system
4. **Concurrency issues** - Multiple processes competing for API access
5. **No graceful degradation** - Failures are immediate and absolute

**Business Impact:**
- Epic execution fails mid-way when JIRA is slow
- Documentation updates lost when Confluence times out
- No visibility into pending/failed operations
- No ability to retry failed operations

---

## Proposed Solution

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                           RESILIENT INTEGRATION QUEUE ARCHITECTURE                                  │
│                                                                                                     │
│   ┌──────────────┐      ┌──────────────┐      ┌──────────────┐      ┌──────────────┐              │
│   │   Process    │      │  Queue API   │      │   Queue      │      │   Worker     │              │
│   │  (Caller)    │─────▶│  Gateway     │─────▶│   Manager    │─────▶│   Pool       │              │
│   │              │      │              │      │              │      │              │              │
│   └──────────────┘      └──────────────┘      └──────────────┘      └──────────────┘              │
│         │                      │                     │                     │                       │
│         │ POST                 │ Returns             │ Persists            │ Processes             │
│         │ request              │ token               │ request             │ request               │
│         │                      │                     │                     │                       │
│         │                      │                     │                     ▼                       │
│         │                      │                     │              ┌──────────────┐              │
│         │                      │                     │              │   External   │              │
│         │                      │                     │              │   Service    │              │
│         │                      │                     │              │  (Atlassian) │              │
│         │                      │                     │              └──────────────┘              │
│         │                      │                     │                     │                       │
│         │                      │                     │                     │ Response              │
│         │                      │                     │                     ▼                       │
│         │                      │              ┌──────────────────────────────────┐                 │
│         │                      │              │          Result Store            │                 │
│         │                      │              │   (Cache + Completion Status)    │                 │
│         │                      │              └──────────────────────────────────┘                 │
│         │                      │                     │                                             │
│         │                      │                     │ GET by token                                │
│         ◀──────────────────────┴─────────────────────┘                                             │
│                                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Component Details

#### 1. Queue API Gateway

**Responsibilities:**
- Accept incoming requests (read/write)
- Generate unique tracking tokens
- Validate request format
- Return immediately with token (non-blocking)

**API Contract:**

```python
# Submit Request (Non-blocking)
POST /api/queue/submit
{
    "operation": "jira.get_task" | "jira.create_task" | "confluence.create_page" | ...,
    "payload": { ... },
    "priority": "high" | "normal" | "low",
    "callback_url": "optional_webhook",
    "idempotency_key": "optional_dedup_key"
}

Response:
{
    "token": "req_abc123xyz",
    "status": "queued",
    "estimated_completion": "2025-12-11T21:30:00Z",
    "position": 5
}
```

```python
# Get Result (Polling or Long-poll)
GET /api/queue/result/{token}?wait=30

Response (Pending):
{
    "token": "req_abc123xyz",
    "status": "processing",
    "progress": 0.5,
    "message": "Authenticating with JIRA..."
}

Response (Complete):
{
    "token": "req_abc123xyz",
    "status": "completed",
    "result": { ... },
    "cached": true,
    "completed_at": "2025-12-11T21:29:45Z"
}

Response (Failed):
{
    "token": "req_abc123xyz",
    "status": "failed",
    "error": {
        "code": "RATE_LIMITED",
        "message": "JIRA API rate limit exceeded",
        "retry_after": 60,
        "retries_exhausted": true
    }
}
```

#### 2. Queue Manager

**Responsibilities:**
- Persist requests to durable storage
- Manage priority queues (high/normal/low)
- Implement rate limiting per service
- Handle request deduplication
- Manage authentication tokens
- Track request lifecycle

**Queue Storage Schema:**

```sql
CREATE TABLE queue_requests (
    id UUID PRIMARY KEY,
    token VARCHAR(50) UNIQUE NOT NULL,
    operation VARCHAR(100) NOT NULL,
    payload JSONB NOT NULL,
    priority VARCHAR(10) DEFAULT 'normal',
    status VARCHAR(20) DEFAULT 'queued',
    idempotency_key VARCHAR(100),

    -- Lifecycle tracking
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,

    -- Retry management
    retry_count INT DEFAULT 0,
    max_retries INT DEFAULT 3,
    next_retry_at TIMESTAMP,

    -- Results
    result JSONB,
    error JSONB,

    -- Indexing
    INDEX idx_status_priority (status, priority, created_at),
    INDEX idx_idempotency (idempotency_key) WHERE idempotency_key IS NOT NULL
);
```

#### 3. Worker Pool

**Responsibilities:**
- Process queued requests
- Implement retry with exponential backoff
- Manage connection pooling
- Handle circuit breaker logic
- Update result store

**Worker Configuration:**

```yaml
worker_pool:
  min_workers: 2
  max_workers: 10
  scaling_policy: adaptive  # Scale based on queue depth

  per_service:
    jira:
      rate_limit: 100/minute
      burst_limit: 20
      circuit_breaker:
        failure_threshold: 5
        recovery_timeout: 60s
        half_open_requests: 3

    confluence:
      rate_limit: 50/minute
      burst_limit: 10
      circuit_breaker:
        failure_threshold: 5
        recovery_timeout: 60s
        half_open_requests: 3
```

#### 4. Result Store (Cache Layer)

**Responsibilities:**
- Cache completed results (TTL-based)
- Enable fast lookups by token
- Support cache invalidation
- Reduce redundant API calls

**Caching Strategy:**

| Operation Type | Cache TTL | Invalidation Trigger |
|---------------|-----------|---------------------|
| `jira.get_task` | 5 minutes | On update to same task |
| `jira.search_tasks` | 2 minutes | On any task create/update in project |
| `confluence.get_page` | 10 minutes | On update to same page |
| Write operations | No cache | N/A |

---

## Detailed Workflow

### Read Operation Flow

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              READ OPERATION FLOW                                         │
│                                                                                          │
│    Process                Gateway                Queue Manager            Worker         │
│       │                      │                        │                     │            │
│       │  POST /submit        │                        │                     │            │
│       │  op=jira.get_task    │                        │                     │            │
│       │─────────────────────▶│                        │                     │            │
│       │                      │                        │                     │            │
│       │                      │  Check Cache           │                     │            │
│       │                      │─────────────────────────────────────────────▶│            │
│       │                      │                        │     Cache HIT       │            │
│       │                      │◀────────────────────────────────────────────┤            │
│       │                      │                        │                     │            │
│       │  {token, cached}     │                        │                     │            │
│       │◀─────────────────────│                        │                     │            │
│       │                      │                        │                     │            │
│  ─────┼──────────────────────┼────────────────────────┼─────────────────────┼───────     │
│       │                      │                        │                     │            │
│       │                      │  Cache MISS            │                     │            │
│       │                      │─────────────────────────────────────────────▶│            │
│       │                      │                        │                     │            │
│       │                      │  Enqueue               │                     │            │
│       │                      │───────────────────────▶│                     │            │
│       │                      │                        │                     │            │
│       │  {token, queued}     │                        │                     │            │
│       │◀─────────────────────│                        │     Dequeue         │            │
│       │                      │                        │────────────────────▶│            │
│       │                      │                        │                     │            │
│       │                      │                        │     Execute API     │            │
│       │                      │                        │                     │──────┐     │
│       │                      │                        │                     │      │     │
│       │                      │                        │     Store Result    │◀─────┘     │
│       │                      │                        │◀────────────────────│            │
│       │                      │                        │                     │            │
│       │  GET /result/{token} │                        │                     │            │
│       │─────────────────────▶│                        │                     │            │
│       │                      │                        │                     │            │
│       │  {status, result}    │                        │                     │            │
│       │◀─────────────────────│                        │                     │            │
│       │                      │                        │                     │            │
└───────┴──────────────────────┴────────────────────────┴─────────────────────┴────────────┘
```

### Write Operation Flow

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              WRITE OPERATION FLOW                                        │
│                                                                                          │
│    Process                Gateway                Queue Manager            Worker         │
│       │                      │                        │                     │            │
│       │  POST /submit        │                        │                     │            │
│       │  op=jira.create_task │                        │                     │            │
│       │─────────────────────▶│                        │                     │            │
│       │                      │                        │                     │            │
│       │                      │  Validate + Hash       │                     │            │
│       │                      │  (idempotency check)   │                     │            │
│       │                      │───────────────────────▶│                     │            │
│       │                      │                        │                     │            │
│       │                      │  Check Duplicate       │                     │            │
│       │                      │◀───────────────────────│                     │            │
│       │                      │                        │                     │            │
│       │                      │  Enqueue (if new)      │                     │            │
│       │                      │───────────────────────▶│                     │            │
│       │                      │                        │                     │            │
│       │  {token, accepted}   │                        │                     │            │
│       │◀─────────────────────│                        │                     │            │
│       │                      │                        │                     │            │
│       │                      │                        │     Dequeue         │            │
│       │                      │                        │────────────────────▶│            │
│       │                      │                        │                     │            │
│       │                      │                        │     Execute API     │            │
│       │                      │                        │                     │──────┐     │
│       │                      │                        │                     │      │     │
│       │                      │                        │     Store Result    │◀─────┘     │
│       │                      │                        │◀────────────────────│            │
│       │                      │                        │                     │            │
│       │                      │                        │     Invalidate      │            │
│       │                      │                        │     Related Cache   │            │
│       │                      │                        │────────────────────▶│            │
│       │                      │                        │                     │            │
└───────┴──────────────────────┴────────────────────────┴─────────────────────┴────────────┘
```

---

## Challenges and Edge Cases

### Challenge 1: Eventual Consistency

**Problem:** Write operations return "accepted" before completion. Caller may read stale data.

**Scenario:**
```
T0: Process A writes to JIRA (accepted, token returned)
T1: Process A reads from JIRA (returns stale cached data)
T2: Worker completes write to JIRA
T3: Process A reads again (still stale if cache not invalidated)
```

**Mitigations:**

| Mitigation | Description | Trade-off |
|------------|-------------|-----------|
| **Read-after-write consistency token** | Return a version token with writes; reads can pass this token to ensure freshness | Added complexity |
| **Cache invalidation on write accept** | Immediately invalidate cache for related entities | May cause cache stampede |
| **Synchronous mode option** | Allow caller to request sync execution for critical writes | Defeats purpose for critical ops |
| **Polling with version check** | Result includes version; caller polls until version advances | Higher latency |

**Recommended:** Implement **read-after-write consistency token** pattern:

```python
# Write response includes consistency token
write_response = {
    "token": "req_abc123",
    "status": "accepted",
    "consistency_token": "ct_xyz789"
}

# Subsequent read includes consistency requirement
GET /api/queue/submit
{
    "operation": "jira.get_task",
    "payload": {"task_id": "MD-123"},
    "after_consistency_token": "ct_xyz789"  # Wait for write to complete first
}
```

---

### Challenge 2: Error Propagation

**Problem:** How does caller know if async write failed?

**Scenario:**
```
T0: Process accepts write as "accepted"
T1: Process continues assuming success
T2: Worker fails to write (auth error, validation error, etc.)
T3: Process has incorrect state
```

**Mitigations:**

| Mitigation | Description | Trade-off |
|------------|-------------|-----------|
| **Webhook callbacks** | Caller provides callback URL for completion/failure notification | Requires callback infrastructure |
| **Polling requirement** | Caller must poll before considering operation complete | Added latency/complexity |
| **Optimistic with compensation** | Accept optimistically, send compensation event on failure | Complex rollback logic |
| **Status subscription (WebSocket)** | Real-time status updates | Infrastructure overhead |

**Recommended:** **Mandatory polling for writes** with optional webhooks:

```python
# For writes, response indicates polling is required
write_response = {
    "token": "req_abc123",
    "status": "accepted",
    "requires_confirmation": true,
    "poll_url": "/api/queue/result/req_abc123",
    "max_wait_seconds": 30
}

# Caller MUST poll before assuming success
# For fire-and-forget, caller explicitly acknowledges risk:
{
    "operation": "jira.add_comment",
    "payload": {...},
    "fire_and_forget": true  # Explicitly opt-out of confirmation
}
```

---

### Challenge 3: Queue Ordering

**Problem:** Some operations must complete in order (e.g., create task before adding comment).

**Scenario:**
```
T0: Enqueue "create task MD-123"
T1: Enqueue "add comment to MD-123"
T2: Worker 1 picks up comment (fails - task doesn't exist)
T3: Worker 2 picks up create task (succeeds)
```

**Mitigations:**

| Mitigation | Description | Trade-off |
|------------|-------------|-----------|
| **Dependency declaration** | Request declares dependencies on other request tokens | Complex dependency graph |
| **Sequential queues per entity** | One queue per entity, processed FIFO | Reduced parallelism |
| **Saga pattern** | Multi-step operations as single saga | Complex rollback |
| **Optimistic retry** | Failed deps trigger re-queue with backoff | May cause retry storms |

**Recommended:** **Dependency declaration** with automatic sequencing:

```python
# Step 1: Create task
create_response = submit({
    "operation": "jira.create_task",
    "payload": {"title": "New Task"}
})  # Returns token: "req_create_123"

# Step 2: Add comment (depends on step 1)
comment_response = submit({
    "operation": "jira.add_comment",
    "payload": {"task_id": "$result.req_create_123.data.id", "comment": "..."},
    "depends_on": ["req_create_123"]  # Won't execute until dependency completes
})
```

---

### Challenge 4: Dead Letter Handling

**Problem:** What happens to requests that fail after all retries?

**Scenario:**
```
T0-T3: Request fails 3 times (max retries)
T4: Request moved to dead letter queue
T5: How does system/user recover?
```

**Mitigations:**

| Mitigation | Description | Trade-off |
|------------|-------------|-----------|
| **Manual review queue** | Dead letters require human intervention | Operational overhead |
| **Auto-retry on service recovery** | When circuit breaker closes, retry dead letters | May cause thundering herd |
| **Escalation webhook** | Notify external system of permanent failures | Requires monitoring |
| **TTL expiry** | Dead letters expire after N hours | May lose important data |

**Recommended:** **Tiered approach**:

```yaml
dead_letter_handling:
  tier_1:  # First 24 hours
    action: hold_for_retry
    retry_on_circuit_close: true

  tier_2:  # 24-72 hours
    action: escalate
    webhook: "https://alerts.internal/dead-letter"
    create_jira_bug: true

  tier_3:  # After 72 hours
    action: archive
    archive_to: s3://dead-letters/
    retention_days: 90
```

---

### Challenge 5: Authentication Token Management

**Problem:** JIRA/Confluence tokens may expire mid-processing.

**Scenario:**
```
T0: Worker starts processing with valid token
T1: Token expires during API call
T2: API returns 401 Unauthorized
T3: Worker needs to refresh token and retry
```

**Recommended:** **Centralized token manager** with proactive refresh:

```python
class TokenManager:
    """Centralized authentication token management."""

    async def get_token(self, service: str) -> str:
        """Get valid token, refreshing if needed."""
        token = self._tokens.get(service)

        if not token or self._is_expiring_soon(token):
            token = await self._refresh_token(service)
            self._tokens[service] = token

        return token.access_token

    def _is_expiring_soon(self, token: Token) -> bool:
        """Check if token expires within 5 minutes."""
        return token.expires_at < datetime.now() + timedelta(minutes=5)
```

---

### Challenge 6: Idempotency for Writes

**Problem:** Network failures may cause duplicate submissions.

**Scenario:**
```
T0: Client sends "create task" request
T1: Gateway receives request, enqueues
T2: Gateway response lost (network issue)
T3: Client retries "create task" request
T4: Duplicate task created
```

**Recommended:** **Client-generated idempotency keys**:

```python
# Client generates unique key
request = {
    "operation": "jira.create_task",
    "payload": {"title": "New Task"},
    "idempotency_key": f"create_task_{uuid4()}"  # Or hash of payload
}

# Gateway checks for existing key
existing = await db.get_by_idempotency_key(request.idempotency_key)
if existing:
    return existing.token  # Return same token, don't re-enqueue
```

---

## Industry Standard Patterns Applied

### 1. Circuit Breaker Pattern (Hystrix/Resilience4j)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        CIRCUIT BREAKER STATES                            │
│                                                                          │
│   ┌─────────┐         failure_threshold        ┌─────────┐              │
│   │ CLOSED  │ ────────────exceeded───────────▶ │  OPEN   │              │
│   │ (normal)│                                   │ (fail   │              │
│   │         │                                   │  fast)  │              │
│   └─────────┘                                   └─────────┘              │
│        ▲                                             │                   │
│        │                                             │                   │
│        │            ┌───────────┐                    │                   │
│        │            │HALF-OPEN  │                    │                   │
│        └────success─│ (testing) │◀───recovery_timeout┘                   │
│                     └───────────┘                                        │
│                          │                                               │
│                          │ failure                                       │
│                          └──────────────────────────────────────────────▶│
│                                                           back to OPEN   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2. Outbox Pattern (Reliable Messaging)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          OUTBOX PATTERN                                  │
│                                                                          │
│   ┌─────────────────────────────────────────────────────────────┐       │
│   │                    SINGLE TRANSACTION                        │       │
│   │                                                              │       │
│   │   1. Write to business table                                 │       │
│   │   2. Write to outbox table                                   │       │
│   │                                                              │       │
│   └─────────────────────────────────────────────────────────────┘       │
│                                │                                         │
│                                ▼                                         │
│   ┌─────────────────────────────────────────────────────────────┐       │
│   │              OUTBOX PROCESSOR (Separate Process)             │       │
│   │                                                              │       │
│   │   1. Poll outbox table for unpublished events                │       │
│   │   2. Publish to external service                             │       │
│   │   3. Mark as published (or delete)                           │       │
│   │                                                              │       │
│   └─────────────────────────────────────────────────────────────┘       │
│                                                                          │
│   Benefits:                                                              │
│   - Atomic business + outbox write                                       │
│   - At-least-once delivery guarantee                                     │
│   - Survives process crashes                                             │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3. Bulkhead Pattern (Failure Isolation)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        BULKHEAD PATTERN                                  │
│                                                                          │
│   ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐   │
│   │   JIRA Bulkhead   │  │Confluence Bulkhead│  │  Other Bulkhead   │   │
│   │                   │  │                   │  │                   │   │
│   │  Max Workers: 5   │  │  Max Workers: 3   │  │  Max Workers: 2   │   │
│   │  Queue Size: 100  │  │  Queue Size: 50   │  │  Queue Size: 20   │   │
│   │                   │  │                   │  │                   │   │
│   │  ┌─┐ ┌─┐ ┌─┐ ┌─┐ │  │  ┌─┐ ┌─┐ ┌─┐     │  │  ┌─┐ ┌─┐          │   │
│   │  │W│ │W│ │W│ │W│ │  │  │W│ │W│ │W│     │  │  │W│ │W│          │   │
│   │  └─┘ └─┘ └─┘ └─┘ │  │  └─┘ └─┘ └─┘     │  │  └─┘ └─┘          │   │
│   │                   │  │                   │  │                   │   │
│   └───────────────────┘  └───────────────────┘  └───────────────────┘   │
│                                                                          │
│   If JIRA overloads, Confluence operations continue unaffected           │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4. Retry with Exponential Backoff + Jitter

```python
def calculate_retry_delay(attempt: int, base_delay: float = 1.0) -> float:
    """
    Calculate retry delay with exponential backoff and jitter.

    Attempt 1: 1-2 seconds
    Attempt 2: 2-4 seconds
    Attempt 3: 4-8 seconds
    Attempt 4: 8-16 seconds (capped at 60)
    """
    exponential_delay = min(base_delay * (2 ** attempt), 60.0)  # Cap at 60s
    jitter = random.uniform(0, exponential_delay)  # Add randomness
    return exponential_delay + jitter
```

### 5. Token Bucket Algorithm (Rate Limiting with Burst Capacity)

**Industry Standard:** Used by AWS API Gateway, Stripe, Kong, and most cloud providers.

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                          TOKEN BUCKET ALGORITHM                                      │
│                                                                                      │
│   Configuration: rate=100/min, burst=50                                             │
│                                                                                      │
│   ┌───────────────────────────────────────────┐                                     │
│   │           TOKEN BUCKET                     │                                     │
│   │   ┌─────────────────────────────────────┐ │     Tokens added at steady rate     │
│   │   │ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ │ │◀────── (100 tokens/minute)          │
│   │   │ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ │ │                                     │
│   │   │ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○ ○   │ │     Max capacity = burst (50)       │
│   │   └─────────────────────────────────────┘ │                                     │
│   │                    │                       │                                     │
│   │                    │ Request takes 1 token │                                     │
│   │                    ▼                       │                                     │
│   │            ┌──────────────┐               │                                     │
│   │            │   Process    │               │                                     │
│   │            └──────────────┘               │                                     │
│   └───────────────────────────────────────────┘                                     │
│                                                                                      │
│   Behavior:                                                                          │
│   - If bucket has tokens → Request proceeds immediately                             │
│   - If bucket empty → Request waits or is rejected (429)                            │
│   - Idle time → Bucket refills (up to burst capacity)                               │
│   - Bursty traffic → Can use up to 50 requests instantly, then 100/min steady       │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

**Key Insight:** Token Bucket allows **controlled bursts** while maintaining average rate.
This is ideal for handling bursty JIRA/Confluence traffic (500 tickets → then idle).

```python
class TokenBucket:
    """Token bucket rate limiter with burst capacity."""

    def __init__(self, rate: float, burst: int):
        self.rate = rate              # Tokens per second
        self.burst = burst            # Max bucket capacity
        self.tokens = burst           # Start full
        self.last_update = time.time()
        self._lock = asyncio.Lock()

    async def acquire(self, timeout: float = 0) -> bool:
        """
        Acquire a token. Returns True if acquired, False if timed out.

        With timeout=0, returns immediately (non-blocking).
        With timeout>0, waits up to timeout seconds for a token.
        """
        async with self._lock:
            self._refill()

            if self.tokens >= 1:
                self.tokens -= 1
                return True

            if timeout <= 0:
                return False

            # Calculate wait time for next token
            wait_time = (1 - self.tokens) / self.rate
            if wait_time > timeout:
                return False

            await asyncio.sleep(wait_time)
            self._refill()
            self.tokens -= 1
            return True

    def _refill(self):
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_update
        self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
        self.last_update = now

    @property
    def available(self) -> float:
        """Current available tokens (for monitoring)."""
        self._refill()
        return self.tokens
```

### 6. Queue-Based Load Leveling Pattern

**Industry Standard:** Microsoft Azure Architecture Pattern, AWS Well-Architected Framework.

**Problem:** External API has 100 req/min limit. Traffic is bursty (500 requests, then idle).

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                     QUEUE-BASED LOAD LEVELING                                        │
│                                                                                      │
│   Traffic Pattern: Bursty (500 tickets in burst, then 10min idle)                   │
│   API Limit: 100 requests/minute                                                    │
│                                                                                      │
│   WITHOUT Queue:                        WITH Queue (Load Leveling):                 │
│                                                                                      │
│   Requests ▲                            Requests ▲                                  │
│       500  │  ████                          100  │  ████████████████████            │
│            │  ████                               │  ████████████████████            │
│            │  ████                               │                                  │
│       100  │──████──▶ REJECTED (429)        50  │──────────────────────▶ Smoothed  │
│            │                                     │                                  │
│            └──────▶ Time                         └──────────▶ Time                  │
│                                                                                      │
│   Burst (500) at T0:                                                                │
│   - 50 requests: immediate (burst capacity)                                         │
│   - 450 requests: queued                                                            │
│   - Queue drains at 100/min → ~4.5 minutes to complete                             │
│   - No requests rejected!                                                           │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

**Reference:** [Azure Queue-Based Load Leveling Pattern](https://learn.microsoft.com/en-us/azure/architecture/patterns/queue-based-load-leveling)

### 7. Adaptive/Intelligent Routing Pattern

**Industry Examples:**
- **Netflix Adaptive Concurrency Limits** - Dynamically adjusts based on latency
- **Envoy Proxy Adaptive Concurrency Filter** - Uses gradient descent
- **Uber's Cinnamon Auto-Tuner** - TCP-Vegas inspired algorithm

**Concept:** Route requests directly to API when under capacity, through queue when over.

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                      ADAPTIVE INTELLIGENT ROUTING                                    │
│                                                                                      │
│   Incoming Request                                                                   │
│         │                                                                            │
│         ▼                                                                            │
│   ┌─────────────────────────────────────┐                                           │
│   │       ADAPTIVE ROUTER               │                                           │
│   │                                      │                                           │
│   │   Decision Logic:                    │                                           │
│   │                                      │                                           │
│   │   current_rate = requests/minute    │                                           │
│   │   available_tokens = bucket.tokens  │                                           │
│   │   queue_depth = queue.size          │                                           │
│   │   circuit_state = breaker.state     │                                           │
│   │                                      │                                           │
│   │   IF circuit_state == OPEN:         │                                           │
│   │     → QUEUE (service unhealthy)     │                                           │
│   │                                      │                                           │
│   │   ELIF available_tokens > 0:        │                                           │
│   │     → DIRECT (capacity available)   │─────────────▶ External API                │
│   │                                      │               (Fast Path)                 │
│   │   ELSE:                             │                                           │
│   │     → QUEUE (over capacity)         │─────┐                                     │
│   │                                      │     │                                     │
│   └─────────────────────────────────────┘     │                                     │
│                                                │                                     │
│                                                ▼                                     │
│                                          ┌──────────┐                               │
│                                          │  Queue   │                               │
│                                          │ Manager  │────▶ Workers ───▶ External   │
│                                          └──────────┘       (Throttled)     API     │
│                                                                                      │
│   Benefits:                                                                          │
│   ✓ Low latency when under capacity (direct path)                                   │
│   ✓ Graceful degradation when over capacity (queue path)                            │
│   ✓ No rejected requests (queue absorbs burst)                                      │
│   ✓ Automatic adaptation to traffic patterns                                        │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

**Implementation:**

```python
class AdaptiveRouter:
    """
    Intelligent router that decides: direct API call vs queue.

    Based on Netflix's adaptive concurrency limits and AWS API Gateway patterns.
    """

    def __init__(
        self,
        token_bucket: TokenBucket,
        queue_gateway: QueueGateway,
        circuit_breaker: CircuitBreaker,
        direct_client: AsyncClient
    ):
        self.bucket = token_bucket
        self.queue = queue_gateway
        self.breaker = circuit_breaker
        self.client = direct_client

        # Metrics for adaptive decisions
        self.recent_latencies: deque = deque(maxlen=100)
        self.direct_success_rate: float = 1.0

    async def route(self, request: SubmitRequest) -> RouteResult:
        """
        Route request based on current system state.

        Returns:
            RouteResult with path taken (DIRECT|QUEUED) and response
        """
        # Decision 1: Circuit breaker open → always queue
        if not self.breaker.allow_request():
            return await self._route_to_queue(request, reason="circuit_open")

        # Decision 2: Token available → try direct
        if await self.bucket.acquire(timeout=0):  # Non-blocking check
            try:
                result = await self._direct_call(request)
                self.breaker.record_success()
                return RouteResult(path="DIRECT", result=result)
            except RateLimitError:
                # API rejected despite our token → reduce local rate
                self.bucket.tokens = max(0, self.bucket.tokens - 5)
                self.breaker.record_failure()
                return await self._route_to_queue(request, reason="rate_limited")
            except Exception as e:
                self.breaker.record_failure()
                return await self._route_to_queue(request, reason="error")

        # Decision 3: No tokens → queue for smoothing
        return await self._route_to_queue(request, reason="over_capacity")

    async def _direct_call(self, request: SubmitRequest) -> dict:
        """Execute request directly against external API."""
        adapter = self._get_adapter(request.operation)
        start = time.time()
        result = await adapter.execute(request.payload)
        self.recent_latencies.append(time.time() - start)
        return result

    async def _route_to_queue(self, request: SubmitRequest, reason: str) -> RouteResult:
        """Route through queue for deferred processing."""
        response = await self.queue.submit(request)
        return RouteResult(
            path="QUEUED",
            token=response.token,
            reason=reason,
            estimated_wait=self._estimate_wait()
        )

    def _estimate_wait(self) -> float:
        """Estimate queue wait time based on depth and drain rate."""
        queue_depth = self.queue.depth
        drain_rate = self.bucket.rate  # requests per second
        return queue_depth / drain_rate if drain_rate > 0 else float('inf')


# Usage example
router = AdaptiveRouter(
    token_bucket=TokenBucket(rate=100/60, burst=50),  # 100/min, burst 50
    queue_gateway=queue_gateway,
    circuit_breaker=CircuitBreaker(failure_threshold=5),
    direct_client=httpx.AsyncClient()
)

# Traffic burst scenario: 500 requests arrive
for i in range(500):
    result = await router.route(SubmitRequest(
        operation="jira.get_task",
        payload={"task_id": f"MD-{i}"}
    ))

    if result.path == "DIRECT":
        # Immediate response (first ~50 use burst capacity)
        print(f"Request {i}: Direct - {result.result}")
    else:
        # Queued for processing at steady rate
        print(f"Request {i}: Queued - token={result.token}, wait={result.estimated_wait}s")
```

### 8. Netflix Adaptive Concurrency Limits (Advanced)

**Reference:** [Netflix Performance Under Load](https://netflixtechblog.medium.com/performance-under-load-3e6fa9a60581)

Netflix's algorithm dynamically adjusts concurrency limits based on observed latency:

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                   NETFLIX ADAPTIVE CONCURRENCY ALGORITHM                             │
│                                                                                      │
│   Core Formula (inspired by TCP Vegas):                                             │
│                                                                                      │
│       gradient = RTT_noload / RTT_actual                                            │
│                                                                                      │
│       gradient ≈ 1.0  →  No queuing, can increase limit                             │
│       gradient < 1.0  →  Queuing detected, should decrease limit                    │
│                                                                                      │
│   Limit Adjustment:                                                                  │
│                                                                                      │
│       new_limit = current_limit × gradient + queue_size                             │
│                                                                                      │
│   Visual:                                                                            │
│                                                                                      │
│   Limit ▲                                                                           │
│     100 │                    ╭────────╮                                             │
│         │                   ╱          ╲    Adaptive adjustment                     │
│      50 │    ╭─────────────╯            ╲───────────╮                               │
│         │   ╱                                        ╲                              │
│      10 │──╯                                          ╲──────                       │
│         └──────────────────────────────────────────────────▶ Time                   │
│              Low load    High load    Overload    Recovery                          │
│                                                                                      │
│   Benefits:                                                                          │
│   ✓ Automatically finds optimal concurrency                                         │
│   ✓ Responds to backend capacity changes                                            │
│   ✓ Prevents overload without manual tuning                                         │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

```python
class AdaptiveConcurrencyLimiter:
    """
    Netflix-style adaptive concurrency limiter.

    Automatically adjusts concurrency limit based on observed latency.
    Reference: https://github.com/Netflix/concurrency-limits
    """

    def __init__(
        self,
        initial_limit: int = 10,
        min_limit: int = 1,
        max_limit: int = 100,
        smoothing: float = 0.2
    ):
        self.limit = initial_limit
        self.min_limit = min_limit
        self.max_limit = max_limit
        self.smoothing = smoothing

        self.inflight = 0
        self.min_rtt: Optional[float] = None
        self._lock = asyncio.Lock()

    async def acquire(self) -> Optional['ConcurrencyToken']:
        """Acquire concurrency slot. Returns None if limit reached."""
        async with self._lock:
            if self.inflight >= self.limit:
                return None
            self.inflight += 1
            return ConcurrencyToken(self, time.time())

    async def release(self, token: 'ConcurrencyToken', success: bool = True):
        """Release slot and update limit based on observed RTT."""
        async with self._lock:
            self.inflight -= 1

            if not success:
                # On failure, aggressively reduce limit
                self.limit = max(self.min_limit, self.limit // 2)
                return

            rtt = time.time() - token.start_time

            # Track minimum RTT (represents no-queuing baseline)
            if self.min_rtt is None or rtt < self.min_rtt:
                self.min_rtt = rtt

            # Calculate gradient (Netflix formula)
            gradient = self.min_rtt / rtt if rtt > 0 else 1.0

            # Adjust limit based on gradient
            if gradient >= 0.95:  # No significant queuing
                # Additive increase
                new_limit = self.limit + 1
            else:
                # Multiplicative decrease
                new_limit = int(self.limit * gradient)

            # Apply smoothing and bounds
            self.limit = int(
                self.limit * (1 - self.smoothing) +
                new_limit * self.smoothing
            )
            self.limit = max(self.min_limit, min(self.max_limit, self.limit))


@dataclass
class ConcurrencyToken:
    """Token representing an acquired concurrency slot."""
    limiter: AdaptiveConcurrencyLimiter
    start_time: float

    async def release(self, success: bool = True):
        await self.limiter.release(self, success)
```

---

## Recommended Implementation

### Phase 1: Core Queue Infrastructure (Week 1-2)

```python
# Core components to implement

class QueueRequest(BaseModel):
    """Queue request model."""
    id: UUID = Field(default_factory=uuid4)
    token: str = Field(default_factory=lambda: f"req_{uuid4().hex[:12]}")
    operation: str
    payload: Dict[str, Any]
    priority: Literal["high", "normal", "low"] = "normal"
    status: Literal["queued", "processing", "completed", "failed", "dead"] = "queued"
    idempotency_key: Optional[str] = None
    depends_on: List[str] = []

    # Retry management
    retry_count: int = 0
    max_retries: int = 3
    next_retry_at: Optional[datetime] = None

    # Lifecycle
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Results
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None


class QueueGateway:
    """API Gateway for queue operations."""

    async def submit(self, request: SubmitRequest) -> SubmitResponse:
        """Submit request to queue."""
        # 1. Check idempotency
        if request.idempotency_key:
            existing = await self.store.get_by_idempotency_key(request.idempotency_key)
            if existing:
                return SubmitResponse(token=existing.token, status="duplicate")

        # 2. Check cache for reads
        if self._is_read_operation(request.operation):
            cached = await self.cache.get(self._cache_key(request))
            if cached:
                return SubmitResponse(token=cached.token, status="cached", result=cached.result)

        # 3. Create and enqueue request
        queue_request = QueueRequest(
            operation=request.operation,
            payload=request.payload,
            priority=request.priority,
            idempotency_key=request.idempotency_key,
            depends_on=request.depends_on
        )

        await self.store.save(queue_request)
        await self.queue.enqueue(queue_request)

        return SubmitResponse(
            token=queue_request.token,
            status="queued",
            position=await self.queue.position(queue_request.token)
        )

    async def get_result(self, token: str, wait: int = 0) -> ResultResponse:
        """Get result by token, optionally waiting."""
        request = await self.store.get_by_token(token)

        if not request:
            raise NotFoundError(f"Request {token} not found")

        if wait > 0 and request.status in ("queued", "processing"):
            # Long-poll: wait for completion
            request = await self._wait_for_completion(token, timeout=wait)

        return ResultResponse(
            token=request.token,
            status=request.status,
            result=request.result,
            error=request.error,
            completed_at=request.completed_at
        )


class QueueWorker:
    """Worker that processes queue requests."""

    def __init__(self, service: str, circuit_breaker: CircuitBreaker):
        self.service = service
        self.circuit_breaker = circuit_breaker
        self.token_manager = TokenManager()

    async def process(self, request: QueueRequest) -> None:
        """Process a single request."""
        try:
            # Check circuit breaker
            if not self.circuit_breaker.allow_request():
                await self._requeue_with_backoff(request)
                return

            # Get fresh token
            auth_token = await self.token_manager.get_token(self.service)

            # Execute operation
            adapter = self._get_adapter(request.operation, auth_token)
            result = await adapter.execute(request.payload)

            # Update request with result
            request.status = "completed"
            request.result = result
            request.completed_at = datetime.utcnow()

            # Record success for circuit breaker
            self.circuit_breaker.record_success()

            # Cache if read operation
            if self._is_read_operation(request.operation):
                await self.cache.set(self._cache_key(request), result)
            else:
                # Invalidate related cache entries for writes
                await self._invalidate_related_cache(request)

        except RateLimitError as e:
            self.circuit_breaker.record_failure()
            await self._requeue_with_backoff(request, e.retry_after)

        except AuthenticationError:
            await self.token_manager.invalidate(self.service)
            await self._requeue_immediately(request)

        except Exception as e:
            self.circuit_breaker.record_failure()

            if request.retry_count < request.max_retries:
                await self._requeue_with_backoff(request)
            else:
                await self._move_to_dead_letter(request, e)

        finally:
            await self.store.save(request)
```

### Phase 2: Integration with Existing Adapters (Week 3)

```python
# Adapter wrapper that uses queue

class QueuedJiraAdapter(ITaskAdapter):
    """JIRA adapter that routes through queue."""

    def __init__(self, queue_gateway: QueueGateway):
        self.gateway = queue_gateway

    async def get_task(self, task_id: str) -> AdapterResult:
        """Get task via queue (with caching)."""
        response = await self.gateway.submit(SubmitRequest(
            operation="jira.get_task",
            payload={"task_id": task_id}
        ))

        if response.status == "cached":
            return AdapterResult(success=True, data=response.result)

        # Poll for result
        result = await self.gateway.get_result(response.token, wait=30)

        if result.status == "completed":
            return AdapterResult(success=True, data=result.result)
        else:
            return AdapterResult(success=False, error=result.error)

    async def create_task(self, **kwargs) -> AdapterResult:
        """Create task via queue (write operation)."""
        response = await self.gateway.submit(SubmitRequest(
            operation="jira.create_task",
            payload=kwargs,
            idempotency_key=f"create_task_{hash(frozenset(kwargs.items()))}"
        ))

        # For writes, must poll for confirmation
        result = await self.gateway.get_result(response.token, wait=60)

        if result.status == "completed":
            return AdapterResult(success=True, data=result.result)
        else:
            return AdapterResult(success=False, error=result.error)
```

### Phase 3: Monitoring & Observability (Week 4)

```python
# Metrics to track

QUEUE_METRICS = {
    "queue_depth": Gauge("Number of requests in queue"),
    "queue_latency": Histogram("Time from enqueue to dequeue"),
    "processing_time": Histogram("Time to process request"),
    "retry_count": Counter("Number of retries"),
    "dead_letter_count": Counter("Requests moved to dead letter"),
    "cache_hit_rate": Gauge("Cache hit percentage"),
    "circuit_breaker_state": Gauge("1=closed, 0.5=half-open, 0=open"),
}
```

---

## Decision

**Implement the Queue-Based Architecture** with the following key decisions:

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Queue Storage | PostgreSQL with advisory locks | Already in stack, ACID guarantees |
| Cache Layer | Redis | Fast, TTL support, already in stack |
| Worker Framework | asyncio + aiohttp | Consistent with existing codebase |
| Circuit Breaker | Custom implementation | Simpler than adding Hystrix dependency |
| Retry Strategy | Exponential backoff + jitter | Industry standard, prevents thundering herd |
| Idempotency | Client-generated keys + hash | Prevents duplicates across retries |

---

### 5. Adaptive Routing for Bursty Traffic

To handle the specific requirement of **100 requests/minute** limit with **500 request bursts**, we are adopting a multi-layered traffic shaping strategy.

#### 5.1 Token Bucket Algorithm (Rate Limiting)
We will use the **Token Bucket** algorithm to enforce the hard limit of 100 requests/minute while allowing small bursts.

*   **Bucket Capacity (Burst):** 50 tokens (Instant burst allowed).
*   **Refill Rate:** 1.67 tokens/second (100/minute).
*   **Behavior:**
    *   When a burst of 500 requests arrives:
    *   First 50 are processed immediately (draining the bucket).
    *   Remaining 450 are held in the **Queue**.
    *   Workers process the queue at the refill rate (~1.67 req/s).
    *   Total time to clear burst: ~4.5 minutes.

#### 5.2 Queue-Based Load Leveling
The persistent queue acts as a buffer that decouples the intake rate from the processing rate. This ensures no requests are rejected (no 429s to the caller) even during massive bursts.

#### 5.3 Adaptive Concurrency (Advanced)
To optimize throughput without manual tuning, we will implement a simplified **Adaptive Concurrency** mechanism inspired by TCP Vegas/Netflix.

*   **Goal:** Maximize throughput while keeping latency low.
*   **Mechanism:**
    *   Measure `RTT_noload` (minimum observed latency).
    *   Measure `RTT_actual` (current moving average latency).
    *   If `RTT_actual` > `RTT_noload * 1.5`, reduce concurrency limit.
    *   If `RTT_actual` ≈ `RTT_noload`, slowly increase concurrency limit.
*   **Benefit:** Automatically backs off if JIRA becomes slow, preventing timeouts before they happen.

### Intelligent Router Decision Flow

```
Request → Circuit Breaker Check → Token Bucket Check → Decision
              │                        │
         OPEN? → QUEUE           TOKENS? → DIRECT (fast path)
                                     │
                                EMPTY? → QUEUED (smoothed)
```

---

## Consequences

### Positive

- **Resilience:** System continues operating during external outages
- **Observability:** Full visibility into pending/failed operations
- **Performance:** Caching reduces API calls by estimated 60%
- **Rate limit compliance:** Centralized throttling prevents quota exhaustion
- **Recoverability:** Dead letter queue enables manual/auto recovery

### Negative

- **Complexity:** More moving parts to maintain
- **Eventual consistency:** Reads may return stale data briefly
- **Latency:** Added hop through queue (mitigated by caching)
- **Operational overhead:** Need to monitor queue depth, dead letters

### Neutral

- **Migration effort:** Existing code needs adapter wrapper
- **Testing complexity:** Need to test async flows

---

## References

- [Circuit Breaker Pattern - Martin Fowler](https://martinfowler.com/bliki/CircuitBreaker.html)
- [Outbox Pattern - Microservices.io](https://microservices.io/patterns/data/transactional-outbox.html)
- [Bulkhead Pattern - Microsoft](https://docs.microsoft.com/en-us/azure/architecture/patterns/bulkhead)
- [Exponential Backoff - AWS](https://docs.aws.amazon.com/general/latest/gr/api-retries.html)
- [Idempotency Keys - Stripe](https://stripe.com/docs/api/idempotent_requests)

---

## Appendix: Quick Reference

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/queue/submit` | POST | Submit request to queue |
| `/api/queue/result/{token}` | GET | Get result by token |
| `/api/queue/status` | GET | Queue health/metrics |
| `/api/queue/dead-letters` | GET | List dead letter requests |
| `/api/queue/dead-letters/{token}/retry` | POST | Retry dead letter |

### Configuration

```yaml
# config/queue.yaml
queue:
  storage:
    type: postgresql
    connection_string: ${DATABASE_URL}

  cache:
    type: redis
    url: ${REDIS_URL}
    default_ttl: 300  # 5 minutes

  workers:
    jira:
      count: 5
      rate_limit: 100/minute
    confluence:
      count: 3
      rate_limit: 50/minute

  circuit_breaker:
    failure_threshold: 5
    recovery_timeout: 60

  retry:
    max_attempts: 3
    base_delay: 1.0
    max_delay: 60.0

  dead_letter:
    retention_hours: 72
    escalation_webhook: ${ALERT_WEBHOOK_URL}

  # REVIEW RECOMMENDATION: Add consistency token config
  consistency_tokens:
    enabled: true              # Set to false to use fresh=true only
    ttl: 300                   # 5 minutes
    single_use: false          # Can be used for multiple reads
    on_write_failure: invalidate
```

---

## Review Comments

> **Review Date:** 2025-12-11
> **Reviewer:** Architecture Team
> **Status:** APPROVED WITH COMMENTS

### Summary

The core queue architecture is **APPROVED**. The design correctly applies industry patterns
(Circuit Breaker, Outbox, Bulkhead, Exponential Backoff). However, the consistency token
mechanism warrants further discussion before implementation.

### Detailed Review

#### APPROVED - Core Components

| Component | Verdict | Notes |
|-----------|---------|-------|
| Queue Gateway | APPROVED | Clean API design |
| Queue Manager | APPROVED | Correct use of PostgreSQL for durability |
| Worker Pool | APPROVED | Circuit breaker well-designed |
| Result Store | APPROVED | Redis caching appropriate |
| Rate Limiting | APPROVED | Per-service bulkheads correct |
| Retry Strategy | APPROVED | Exponential backoff + jitter is best practice |
| Dead Letter Queue | APPROVED | 3-tier handling is robust |
| Idempotency Keys | APPROVED | Client-generated keys prevent duplicates |

#### NEEDS DISCUSSION - Consistency Tokens

**Concern:** The consistency token mechanism (Challenge 1 in this ADR) adds significant
implementation complexity. For JIRA/Confluence integration specifically, this may be
overengineered.

**Analysis:**

```
COMPLEXITY COMPARISON:

Option A: Consistency Tokens (Current Proposal)
├── Token generation on every write
├── Token storage and lookup
├── Token expiry management
├── Dependency tracking between tokens and reads
└── Error handling for expired/invalid tokens
    Complexity: HIGH

Option B: Cache Bypass Flag (fresh=true)
├── Add boolean parameter to submit()
├── Skip cache lookup when true
└── Fetch directly from external API
    Complexity: LOW
```

**When is each needed?**

| Scenario | fresh=true | Consistency Token |
|----------|------------|-------------------|
| Create task → GET task | Sufficient | Overkill |
| Update task → GET task | Sufficient | Overkill |
| Create task → SEARCH (index lag) | Insufficient | Required |
| Batch operations → List all | Insufficient | Required |

**Recommendation:** Implement in phases:

1. **Phase 1:** Implement `fresh=true` flag (covers 80% of use cases)
2. **Phase 2:** Add consistency tokens only if search consistency issues observed

#### MISSING - Token Lifecycle Specification

If consistency tokens are implemented, the ADR should specify:

| Question | Current Status | Recommendation |
|----------|---------------|----------------|
| Token TTL | Not specified | 5 minutes |
| Token reuse | Not specified | Allow multiple reads per token |
| On write failure | Not specified | Invalidate token |
| On token expiry | Not specified | Return CONSISTENCY_TOKEN_EXPIRED error |
| Storage | Not specified | Redis with TTL |

#### BUG IDENTIFIED - Implementation Guide Example

The example in the implementation guide assumes `response.consistency_token` always exists.
This is incorrect - cached responses won't have consistency tokens.

**Current (Buggy):**
```python
read_resp = submit(..., after_consistency_token=response.consistency_token)
```

**Corrected:**
```python
if response.consistency_token:
    read_resp = submit(..., after_consistency_token=response.consistency_token)
else:
    read_resp = submit(..., fresh=True)
```

### Action Items

- [ ] **Decision:** Choose Phase 1 only (fresh=true) or full implementation (both)
- [ ] **If consistency tokens kept:** Add token lifecycle config to this ADR
- [ ] **Update guides:** Fix the null-check bug in examples
- [ ] **Add parameter:** Include `fresh=true` option in API specification
- [ ] **Measure first:** Add metrics to track cache consistency issues before over-optimizing

### Sign-off

| Role | Name | Status | Date |
|------|------|--------|------|
| Author | Architecture Team | SUBMITTED | 2025-12-11 |
| Reviewer | Architecture Review | APPROVED WITH COMMENTS | 2025-12-11 |
| Approver | Platform Lead | PENDING | - |
