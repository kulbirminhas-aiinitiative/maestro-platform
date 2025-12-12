# JIRA Import: Resilient Integration Queue (RIQ)

This document contains the detailed Epic and User Stories for the implementation of the Resilient Integration Queue. These tickets are designed to be picked up by an autonomous coding agent.

---

## EPIC: Resilient Integration Queue for External Services

**Summary:** Implement a robust, fault-tolerant middleware layer for JIRA and Confluence integrations to resolve timeout issues, rate limiting, and data inconsistencies.

**Description:**
Currently, our platform interacts with JIRA and Confluence via synchronous HTTP calls. This causes several critical issues:
1.  **Fragility:** If Atlassian services are slow or down, our core workflows hang or fail.
2.  **Rate Limiting:** We frequently hit API limits during bulk operations.
3.  **Data Loss:** Network glitches during writes can lead to lost updates.

**Goal:**
Implement the "Resilient Integration Queue" (RIQ) as defined in **ADR-007**. This system will decouple the core application from external services using a persistent queue, worker pool, circuit breakers, and caching.

**Reference Documentation:**
*   Architecture Decision: `docs/adr/007-resilient-integration-queue.md`
*   Implementation Guide: `docs/guides/resilient-integration-queue-guide.md`
*   Quick Reference: `docs/guides/resilient-integration-queue-quickref.md`

**Phases:**
1.  Core Infrastructure (Gateway, Manager, Workers)
2.  Adapter Integration (JIRA, Confluence wrappers)
3.  Monitoring & Maintenance (DLQ, Metrics)

---

## Phase 1: Core Infrastructure

### Story 1.1: Database Schema & Models for Queue Requests

**Summary:** Implement the PostgreSQL schema and Pydantic models for storing queue requests.

**Description:**
We need a persistent store for all incoming integration requests. This is the foundation of the "Resilient" part of the system—if the process crashes, requests must survive in the database.

**Requirements:**
1.  Create a SQLAlchemy model `QueueRequest` (or equivalent in our ORM).
2.  Create a Pydantic model `QueueRequestModel` for API validation.
3.  Fields required:
    *   `id` (UUID, PK)
    *   `token` (String, Unique, Index) - The public tracking ID returned to clients.
    *   `operation` (String) - e.g., "jira.create_task".
    *   `payload` (JSON) - The arguments for the operation.
    *   `priority` (Enum: high, normal, low) - Default: normal.
    *   `status` (Enum: queued, processing, completed, failed, dead).
    *   `idempotency_key` (String, Nullable, Index) - For deduplication.
    *   `created_at`, `updated_at`, `completed_at`.
    *   `retry_count` (Int).
    *   `result` (JSON, Nullable).
    *   `error` (JSON, Nullable).
    *   `consistency_token` (String, Nullable) - For read-after-write logic.

**Acceptance Criteria:**
*   [ ] Migration script created and applied successfully.
*   [ ] Models defined in `src/maestro_hive/queue/models.py`.
*   [ ] Unit tests verify that a request can be saved and retrieved by token.
*   [ ] Index exists on `token` and `idempotency_key`.

**Technical Context:**
Refer to `docs/guides/resilient-integration-queue-guide.md` section "Queue Storage Schema".

---

### Story 1.2: Queue Gateway API - Submission Endpoint

**Summary:** Implement the `QueueGateway` class and the `POST /submit` endpoint.

**Description:**
The Gateway is the entry point for the application. It must accept requests quickly (non-blocking) and return a tracking token. It handles idempotency and initial validation.

**Requirements:**
1.  Implement `QueueGateway.submit(request: SubmitRequest)`.
2.  **Idempotency Check:** If `idempotency_key` is provided, check DB. If exists, return the *existing* token immediately (do not re-enqueue).
3.  **Persistence:** Save the new request to the DB with status `queued`.
4.  **Token Generation:** Generate a unique `token` (e.g., `req_<uuid>`) and a `consistency_token` (for write ops).
5.  **API Endpoint:** Expose via FastAPI/Flask as `POST /api/queue/submit`.

**Acceptance Criteria:**
*   [ ] `POST /submit` returns 200 OK with a JSON containing `token`.
*   [ ] Submitting the same `idempotency_key` twice returns the SAME token and does not create a duplicate DB row.
*   [ ] The request is visible in the database with status `queued`.

**Technical Context:**
*   See "Queue Gateway" in `docs/guides/resilient-integration-queue-guide.md`.
*   Ensure `consistency_token` is generated for write operations.

---

### Story 1.3: Queue Manager & Result Polling

**Summary:** Implement the `QueueManager` for status checks and the `GET /result` endpoint.

**Description:**
Clients need to know when their request is done. This story covers the retrieval logic and the "Read-After-Write" consistency check.

**Requirements:**
1.  Implement `QueueGateway.get_result(token: str, wait: int = 0)`.
2.  **Polling Logic:** If `wait > 0`, the server should hold the request open (long-polling) until the status changes to `completed` or `failed`, or timeout occurs.
3.  **Consistency Check:** Update `submit` (from Story 1.2) or `get_result` to handle `after_consistency_token`. If provided, the operation must wait until the referenced token is completed.
4.  **API Endpoint:** `GET /api/queue/result/{token}`.

**Acceptance Criteria:**
*   [ ] `GET /result/{token}` returns the current status and result (if complete).
*   [ ] Long-polling works: Request blocks for N seconds if status is `processing`, returns immediately if `completed`.
*   [ ] Unit test: Verify `after_consistency_token` logic (mock the dependency).

---

### Story 1.4: Worker Pool & Execution Engine

**Summary:** Implement the background worker loop that processes queued requests.

**Description:**
This is the engine that actually does the work. It polls the DB for `queued` items, executes them, and updates the status.

**Requirements:**
1.  Create `QueueWorker` class.
2.  **Loop:** Continuously fetch `queued` items ordered by `priority` (High > Normal > Low) and `created_at`.
3.  **Locking:** Use `SELECT ... FOR UPDATE SKIP LOCKED` (or equivalent) to ensure multiple workers don't pick the same task.
4.  **Execution:**
    *   Update status to `processing`.
    *   Resolve the correct adapter method based on `operation` string (e.g., "jira.create_task" -> `JiraAdapter.create_task`).
    *   Execute the method.
    *   On Success: Update status to `completed`, save `result`.
    *   On Failure: Increment `retry_count`. If `< max_retries`, set status `queued` (with backoff). If `> max_retries`, set status `failed` (or `dead`).

**Acceptance Criteria:**
*   [ ] Worker picks up a queued item.
*   [ ] Worker executes a mock function successfully and updates DB to `completed`.
*   [ ] Worker handles exceptions and increments retry count.
*   [ ] Priority ordering is respected (High priority processed before Low).

**Technical Context:**
*   See "Worker Pool" in `docs/guides/resilient-integration-queue-guide.md`.

---

### Story 1.5: Circuit Breaker & Retry Logic

**Summary:** Implement the Circuit Breaker pattern and Exponential Backoff for the worker.

**Description:**
To prevent cascading failures and thundering herds, the worker must be smart about failures.

**Requirements:**
1.  **Circuit Breaker:**
    *   Track failures per service (JIRA, Confluence).
    *   If failures > Threshold (e.g., 5 in 1 minute), Open circuit.
    *   If Open, fail fast (don't attempt API call) or pause worker for that service.
    *   After Timeout, Half-Open (try 1 request).
2.  **Exponential Backoff:**
    *   Calculate `next_retry_at` = `now() + (base * 2^retry_count) + jitter`.
    *   Worker query should filter `WHERE next_retry_at <= now()`.

**Acceptance Criteria:**
*   [ ] Unit test: 5 consecutive failures trigger Open state.
*   [ ] Unit test: Worker skips tasks for Open service.
*   [ ] Unit test: Retry delay increases exponentially (2s, 4s, 8s...).

**Technical Context:**
*   See "Circuit Breaker" and "Retry with Backoff" in `docs/guides/resilient-integration-queue-guide.md`.

---

### Story 1.6: Token Manager (Authentication)

**Summary:** Implement centralized token management with proactive refresh.

**Description:**
Workers must have valid auth tokens. We shouldn't wait for a 401 error to refresh.

**Requirements:**
1.  Create `TokenManager` class.
2.  Store tokens in memory (with DB backup if needed).
3.  `get_token(service)`:
    *   Check expiration.
    *   If expiring within 5 minutes, refresh *before* returning.
    *   Return valid token.
4.  Integrate into `QueueWorker`.

**Acceptance Criteria:**
*   [ ] Token is refreshed automatically if close to expiry.
*   [ ] Worker uses `TokenManager` to get headers before making requests.

---

## Phase 2: Adapter Integration

### Story 2.1: QueuedJiraAdapter Implementation

**Summary:** Create a wrapper around the existing `JiraAdapter` that uses the Queue Gateway.

**Description:**
The application currently calls `JiraAdapter` directly. We need a new implementation that routes these calls through the queue.

**Requirements:**
1.  Create `QueuedJiraAdapter` implementing the same interface as `JiraAdapter` (or a compatible subset).
2.  **Read Operations:**
    *   Call `gateway.submit("jira.get_...", ...)`
    *   If cached, return immediately.
    *   If not, wait for result (using `gateway.get_result` with timeout).
3.  **Write Operations:**
    *   Call `gateway.submit("jira.create_...", ...)`
    *   Return the `token` (or wait if configured to do so).
4.  **Mapping:** Map all current JIRA methods (`create_epic`, `update_status`, etc.) to queue operations.

**Acceptance Criteria:**
*   [ ] `QueuedJiraAdapter.create_ticket` submits a request to the DB.
*   [ ] `QueuedJiraAdapter.get_ticket` retrieves data via the queue mechanism.
*   [ ] Existing tests for JIRA integration pass when using the Queued adapter (mocking the worker execution).

---

### Story 2.2: QueuedConfluenceAdapter Implementation

**Summary:** Create a wrapper around `ConfluenceAdapter` using the Queue Gateway.

**Description:**
Similar to Story 2.1, but for Confluence.

**Requirements:**
1.  Create `QueuedConfluenceAdapter`.
2.  Map methods: `get_page`, `create_page`, `update_page`.
3.  Ensure `consistency_token` is handled for "Create Page then Update Page" flows.

**Acceptance Criteria:**
*   [ ] Confluence operations are successfully routed through the queue.

---

## Phase 3: Monitoring & Maintenance

### Story 3.1: Dead Letter Queue (DLQ) Management

**Summary:** Implement logic to handle permanently failed requests.

**Description:**
Requests that exceed `max_retries` move to `dead` status. We need a way to manage them.

**Requirements:**
1.  **Transition:** Worker moves items to `dead` status after N retries.
2.  **API:** `GET /api/queue/dead-letters` to list failed items.
3.  **Retry API:** `POST /api/queue/dead-letters/{token}/retry` to reset status to `queued` and `retry_count` to 0.
4.  **Purge API:** `DELETE /api/queue/dead-letters/{token}`.

**Acceptance Criteria:**
*   [ ] Requests failing N times appear in the DLQ list.
*   [ ] Can manually retry a dead letter via API.

---

### Story 3.2: Metrics & Observability

**Summary:** Instrument the queue with metrics.

**Description:**
We need visibility into the system's health.

**Requirements:**
1.  Expose metrics (Prometheus format or logs):
    *   `queue_depth` (Gauge, per priority).
    *   `request_latency` (Histogram).
    *   `error_rate` (Counter, per service).
    *   `circuit_breaker_status` (Gauge).
2.  Log structured events for every state change (Queued -> Processing -> Completed).

**Acceptance Criteria:**
*   [ ] Metrics endpoint is available.
*   [ ] Logs show clear lifecycle of a request `[QUEUE] Token: xyz Status: Completed Duration: 1.2s`.

---

### Story 3.3: Cleanup Cron Job

**Summary:** Implement a background job to clean up old completed requests.

**Description:**
The `queue_requests` table will grow indefinitely. We need to prune it.

**Requirements:**
1.  Create a scheduled task (e.g., daily).
2.  Delete requests where `status` IN ('completed', 'failed') AND `updated_at` < NOW() - 7 days.
3.  Do NOT delete `dead` letters (they need manual review).

**Acceptance Criteria:**
*   [ ] Script deletes old records but preserves recent ones and dead letters.
