# JIRA TICKET: MD-3204

**Type:** Story
**Summary:** Implement Chaos Agents (Loki & Janitor)
**Epic:** MD-3200 (Governance Layer)
**Priority:** Low (But Critical for Long-term Health)
**Component:** Agents / Chaos

---

## 1. Problem Statement (The Why)
Systems become fragile if they are never stressed, and codebases rot if they are never cleaned. We need "System Agents" that maintain health through destruction (Chaos Engineering) and cleaning (Anti-Entropy).

## 2. Technical Requirements (The What)
Implement the specialized `Loki` and `Janitor` agents.

### Responsibilities
1.  **Loki (The Chaos Monkey):**
    *   Wake up on schedule (e.g., 3 AM).
    *   Kill random worker processes (simulating failure).
    *   Inject latency into the Event Bus.
2.  **Janitor (The Cleaner):**
    *   Scan for files not referenced in imports.
    *   Archive logs older than 30 days.
    *   Delete temporary files.

### Technical Specs
*   **File Paths:** `src/maestro_hive/agents/chaos/loki.py`, `src/maestro_hive/agents/chaos/janitor.py`
*   **Type:** Autonomous Agents (subclass of `BaseAgent`).
*   **Constraints:** Must strictly follow `policy.yaml` (cannot kill the Governance Agent).

## 3. Acceptance Criteria
*   [ ] **Loki:** Successfully kills a worker process without bringing down the whole system.
*   [ ] **Janitor:** Successfully identifies and deletes an orphaned `.tmp` file.
*   [ ] **Safety:** Loki never kills the Database or the Enforcer.
*   [ ] **Reporting:** Both agents report their actions to the Audit Log.

## 4. References
*   **Design Spec:** [RFC-001: Governance Layer](../rfc/RFC-001_GOVERNANCE_LAYER.md)
