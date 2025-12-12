# JIRA TICKET: MD-3201

**Type:** Story
**Summary:** Implement Enforcer Middleware (Synchronous Governance)
**Epic:** MD-3200 (Governance Layer)
**Priority:** High
**Component:** Core / Middleware

---

## 1. Problem Statement (The Why)
Agents currently have unrestricted access to all tools. A rogue agent could delete the database, modify the constitution, or spend the entire budget in seconds. We need a "Bouncer" that sits between the Agent and the Tool Execution layer to enforce the "Laws of Physics" defined in the Constitution.

## 2. Technical Requirements (The What)
Implement the `EnforcerMiddleware` class that intercepts every tool call before execution.

### Responsibilities
1.  **Intercept:** Capture every tool call (e.g., `write_file`, `run_terminal`).
2.  **Validate:** Check against `config/governance/policy.yaml`.
    *   **Role Check:** Is the tool allowed for this agent role?
    *   **Path Check:** Is the target file path immutable?
    *   **Budget Check:** Does the agent have sufficient budget?
3.  **Locking:** Check `concurrency_control` (is the file locked by another agent?).
4.  **Enforce:** Execute the tool OR return `403 Forbidden`.

### Technical Specs
*   **File Path:** `src/maestro_hive/governance/enforcer.py`
*   **Input:** `AgentAction(tool_name, args, agent_id)`
*   **Config:** Load `config/governance/policy.yaml` (cached in memory).
*   **Output:** `Allowed` (pass-through) or `Denied` (exception).
*   **Latency:** Must be < 10ms per call.

## 3. Acceptance Criteria
*   [ ] **Immutable Protection:** Attempting to edit `.env` returns `PermissionError`.
*   [ ] **Role Restriction:** A `developer_agent` attempting `deploy_prod` is blocked.
*   [ ] **Budget Check:** An agent with $0.00 remaining budget is blocked.
*   [ ] **Performance:** Overhead per call is < 10ms.
*   [ ] **Fail-Safe:** If the policy file is corrupted, ALL actions are blocked.

## 4. References
*   **Design Spec:** [RFC-001: Governance Layer](../rfc/RFC-001_GOVERNANCE_LAYER.md)
*   **Configuration:** [Policy Configuration](../../config/governance/policy.yaml)
