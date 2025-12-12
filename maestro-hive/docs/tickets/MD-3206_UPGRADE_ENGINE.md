```markdown
# JIRA TICKET: MD-3206

**Type:** Story
**Summary:** Upgrade Team Execution Engine to V3 (Governance-Aware)
**Epic:** MD-3200 (Governance Layer)
**Priority:** High
**Component:** Core / Execution Engine

---

## 1. Problem Statement
The current `team_execution_v2.py` is "lawless". It executes tool calls directly without checking the `policy.yaml` (Constitution). It is also "deaf", as it does not emit events to the `EventBus`, making it invisible to the Auditor and Reputation systems.

## 2. Technical Requirements
Refactor `src/maestro_hive/teams/team_execution_v2.py` (and `persona_executor_v2.py`) to become **Team Execution Engine V3**.

### Key Changes
1.  **Inject Dependencies:**
    *   Initialize `EventBus` on startup.
    *   Initialize `EnforcerMiddleware` with `policy.yaml`.
2.  **Wrap Tool Execution:**
    *   Modify `ClaudeCLIClient` or the executor loop to pass *every* tool call through `enforcer.validate(action)`.
    *   If `validate` returns `False`, raise `GovernanceViolation` and halt execution.
3.  **Emit Events:**
    *   Emit `workflow.started`, `step.completed`, `tool.executed`, `workflow.completed`.
    *   Include `session_id` and `agent_id` in all events.

## 3. Acceptance Criteria
*   [ ] **Enforcement:** A test run attempting to modify a protected file (e.g., `.env`) MUST fail with a `GovernanceViolation`.
*   [ ] **Visibility:** A test run MUST produce a sequence of events in the `EventBus` (visible in logs).
*   [ ] **Identity:** Every tool call must be associated with a specific `persona_id`.
*   [ ] **Backward Compatibility:** Existing "valid" workflows (that don't break rules) must still pass.

## 4. References
*   **Enforcer Spec:** [MD-3201](./MD-3201_ENFORCER.md)
*   **Legacy Engine:** `src/maestro_hive/teams/team_execution_v2.py`
```
