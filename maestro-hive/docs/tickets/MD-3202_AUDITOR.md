# JIRA TICKET: MD-3202

**Type:** Story
**Summary:** Implement Auditor Service (Asynchronous Governance)
**Epic:** MD-3200 (Governance Layer)
**Priority:** Medium
**Component:** Observability / Event Bus

---

## 1. Problem Statement (The Why)
Some governance checks are too slow for the synchronous Enforcer (e.g., running a full test suite to verify coverage, or analyzing 24 hours of logs for collusion). We need a "Judge" that listens to the Event Bus and performs these complex checks asynchronously without blocking the agents.

## 2. Technical Requirements (The What)
Implement the `AuditorService` that subscribes to governance events.

### Responsibilities
1.  **Listen:** Subscribe to `agent.action`, `test.result`, `pr.merged` events.
2.  **Verify:**
    *   **Test Coverage:** When `test_passed` is received, run coverage analysis to verify it's not a trivial test.
    *   **Sybil Detection:** Analyze patterns to detect if multiple agents are colluding (e.g., same IP, coordinated bidding).
3.  **Adjudicate:** Emit `governance.reputation_change` events based on findings.

### Technical Specs
*   **File Path:** `src/maestro_hive/governance/auditor.py`
*   **Architecture:** Standalone service or background worker.
*   **Input:** Event Bus messages (NATS/Redis).
*   **Output:** New Events (Reputation updates, Violation alerts).

## 3. Acceptance Criteria
*   [ ] **Coverage Verification:** If an agent adds a test that doesn't increase coverage, no reputation is awarded.
*   [ ] **Async Processing:** Does not block the main agent execution loop.
*   [ ] **Sybil Detection:** Flags if 2+ agents try to edit the same file within 100ms.
*   [ ] **Logging:** All decisions are written to the immutable audit log.

## 4. References
*   **Design Spec:** [RFC-001: Governance Layer](../rfc/RFC-001_GOVERNANCE_LAYER.md)
