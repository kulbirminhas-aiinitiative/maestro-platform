import os
import sys
import json
import requests
import getpass

# Configuration
JIRA_BASE_URL = "https://fifth9.atlassian.net"
PROJECT_KEY = "MD"  # Assuming MD based on previous context (MD-123 etc), user can override
AUTH_EMAIL = os.environ.get("JIRA_EMAIL")
AUTH_TOKEN = os.environ.get("JIRA_TOKEN")

if not AUTH_EMAIL or not AUTH_TOKEN:
    print("Please set JIRA_EMAIL and JIRA_TOKEN environment variables.")
    sys.exit(1)

AUTH = (AUTH_EMAIL, AUTH_TOKEN)
HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json"
}

def text_to_adf(text):
    """Convert simple text to Atlassian Document Format."""
    content = []
    for paragraph in text.split('\n\n'):
        if not paragraph.strip():
            continue
        content.append({
            "type": "paragraph",
            "content": [
                {
                    "type": "text",
                    "text": paragraph.strip()
                }
            ]
        })
    
    return {
        "type": "doc",
        "version": 1,
        "content": content
    }

def create_issue(summary, description, issuetype, parent_key=None, labels=None):
    url = f"{JIRA_BASE_URL}/rest/api/3/issue"
    
    payload = {
        "fields": {
            "project": {
                "key": PROJECT_KEY
            },
            "summary": summary,
            "description": text_to_adf(description),
            "issuetype": {
                "name": issuetype
            }
        }
    }

    if parent_key:
        payload["fields"]["parent"] = {"key": parent_key}
    
    if labels:
        payload["fields"]["labels"] = labels

    response = requests.post(url, json=payload, auth=AUTH, headers=HEADERS)
    
    if response.status_code == 201:
        data = response.json()
        print(f"Created {issuetype}: {data['key']} - {summary}")
        return data['key']
    else:
        print(f"Failed to create {issuetype}: {summary}")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        return None

def main():
    print(f"Creating tickets in project {PROJECT_KEY} on {JIRA_BASE_URL}...")

    # 1. Create EPIC
    epic_summary = "Resilient Integration Queue for External Services"
    epic_description = """Implement a robust, fault-tolerant middleware layer for JIRA and Confluence integrations to resolve timeout issues, rate limiting, and data inconsistencies.

Goal: Implement the "Resilient Integration Queue" (RIQ) as defined in ADR-007. This system will decouple the core application from external services using a persistent queue, worker pool, circuit breakers, and caching.

Reference Documentation:
* Architecture Decision: docs/adr/007-resilient-integration-queue.md
* Implementation Guide: docs/guides/resilient-integration-queue-guide.md
* Quick Reference: docs/guides/resilient-integration-queue-quickref.md"""
    
    epic_key = create_issue(epic_summary, epic_description, "Epic", labels=["architecture", "resilience"])
    
    if not epic_key:
        print("Aborting due to EPIC creation failure.")
        return

    # 2. Create Stories
    stories = [
        {
            "summary": "RIQ: Database Schema & Models for Queue Requests",
            "description": """Implement the PostgreSQL schema and Pydantic models for storing queue requests.

Requirements:
1. Create a SQLAlchemy model QueueRequest.
2. Create a Pydantic model QueueRequestModel.
3. Fields: id, token, operation, payload, priority, status, idempotency_key, created_at, updated_at, completed_at, retry_count, result, error, consistency_token.

Acceptance Criteria:
* Migration script created.
* Models defined in src/maestro_hive/queue/models.py.
* Unit tests verify save/retrieve.
* Indexes on token and idempotency_key."""
        },
        {
            "summary": "RIQ: Queue Gateway API - Submission Endpoint",
            "description": """Implement the QueueGateway class and the POST /submit endpoint.

Requirements:
1. Implement QueueGateway.submit(request).
2. Idempotency Check: Return existing token if key exists.
3. Persistence: Save new request as 'queued'.
4. Token Generation: Unique token + consistency_token.
5. API Endpoint: POST /api/queue/submit.

Acceptance Criteria:
* POST /submit returns 200 with token.
* Idempotency works (no duplicates).
* Request visible in DB."""
        },
        {
            "summary": "RIQ: Queue Manager & Result Polling",
            "description": """Implement the QueueManager for status checks and the GET /result endpoint.

Requirements:
1. Implement QueueGateway.get_result(token, wait).
2. Polling Logic: Long-polling support.
3. Consistency Check: Handle after_consistency_token.
4. API Endpoint: GET /api/queue/result/{token}.

Acceptance Criteria:
* GET /result returns status/result.
* Long-polling blocks correctly.
* Consistency token logic verified."""
        },
        {
            "summary": "RIQ: Worker Pool & Execution Engine",
            "description": """Implement the background worker loop that processes queued requests.

Requirements:
1. Create QueueWorker class.
2. Loop: Fetch queued items by priority.
3. Locking: SELECT FOR UPDATE SKIP LOCKED.
4. Execution: Execute adapter method, update status (completed/failed), handle retries.

Acceptance Criteria:
* Worker picks up queued item.
* Executes mock function.
* Handles exceptions and retries.
* Respects priority."""
        },
        {
            "summary": "RIQ: Circuit Breaker & Retry Logic",
            "description": """Implement the Circuit Breaker pattern and Exponential Backoff for the worker.

Requirements:
1. Circuit Breaker: Track failures per service. Open/Half-Open states.
2. Exponential Backoff: Calculate next_retry_at.

Acceptance Criteria:
* 5 consecutive failures trigger Open state.
* Worker skips tasks for Open service.
* Retry delay increases exponentially."""
        },
        {
            "summary": "RIQ: Token Manager (Authentication)",
            "description": """Implement centralized token management with proactive refresh.

Requirements:
1. Create TokenManager class.
2. get_token(service): Check expiry, refresh if needed (5 min buffer).

Acceptance Criteria:
* Token refreshed automatically.
* Worker uses TokenManager."""
        },
        {
            "summary": "RIQ: QueuedJiraAdapter Implementation",
            "description": """Create a wrapper around the existing JiraAdapter that uses the Queue Gateway.

Requirements:
1. Create QueuedJiraAdapter.
2. Read Ops: Check cache, then poll.
3. Write Ops: Submit to queue.
4. Map all current JIRA methods.

Acceptance Criteria:
* Operations routed through queue.
* Existing tests pass with new adapter."""
        },
        {
            "summary": "RIQ: QueuedConfluenceAdapter Implementation",
            "description": """Create a wrapper around ConfluenceAdapter using the Queue Gateway.

Requirements:
1. Create QueuedConfluenceAdapter.
2. Map methods: get_page, create_page, update_page.

Acceptance Criteria:
* Confluence operations routed through queue."""
        },
        {
            "summary": "RIQ: Dead Letter Queue (DLQ) Management",
            "description": """Implement logic to handle permanently failed requests.

Requirements:
1. Transition to 'dead' after max_retries.
2. API: GET /dead-letters, POST /retry, DELETE /purge.

Acceptance Criteria:
* Failed requests appear in DLQ.
* Can manually retry."""
        },
        {
            "summary": "RIQ: Metrics & Observability",
            "description": """Instrument the queue with metrics.

Requirements:
1. Expose metrics: queue_depth, request_latency, error_rate, circuit_breaker_status.
2. Structured logging.

Acceptance Criteria:
* Metrics endpoint available.
* Clear logs."""
        },
        {
            "summary": "RIQ: Cleanup Cron Job",
            "description": """Implement a background job to clean up old completed requests.

Requirements:
1. Scheduled task.
2. Delete completed/failed > 7 days.
3. Preserve dead letters.

Acceptance Criteria:
* Script deletes old records correctly."""
        }
    ]

    for story in stories:
        create_issue(story["summary"], story["description"], "Story", parent_key=epic_key, labels=["architecture", "resilience"])

if __name__ == "__main__":
    main()
