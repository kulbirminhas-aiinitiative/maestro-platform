```markdown
# JIRA TICKET: MD-3208

**Type:** Story
**Summary:** Integrate Event Bus into Team Execution Engine (Visibility)
**Epic:** MD-3200 (Governance Layer)
**Priority:** High
**Component:** Core / Observability

---

## 1. Problem Statement
The `TeamExecutionEngineV2` currently runs in a vacuum. It does not broadcast its activities to the rest of the system. This means the **Auditor** cannot monitor progress, the **Reputation System** cannot score actions, and we have no real-time visibility into the "Society".

## 2. Technical Requirements
Modify `src/maestro_hive/teams/team_execution_v2.py` to emit structured events at key lifecycle stages.

### Implementation Details
1.  **Initialization:**
    *   Inject `EventBus` into `TeamExecutionEngineV2.__init__`.
    *   Ensure it connects to the shared event stream (Redis/Memory).

2.  **Event Emission Points:**
    *   **Workflow Start:** Emit `workflow.started` with `session_id`, `requirement`.
    *   **Phase Start:** Emit `phase.started` (e.g., "Blueprint Selection", "Contract Design").
    *   **Phase Complete:** Emit `phase.completed` with `duration`, `status`.
    *   **Workflow Complete:** Emit `workflow.completed` with `final_status`, `artifacts_list`.
    *   **Error:** Emit `workflow.failed` with `error_message`, `traceback`.

3.  **Context Propagation:**
    *   Ensure `session_id` is passed down to all sub-components (`PersonaExecutor`, `ContractDesigner`).

## 3. Acceptance Criteria
*   [ ] Running a workflow generates a stream of events in the logs/console.
*   [ ] The `Auditor` (when running) receives these events.
*   [ ] Events contain correct timestamps and `session_id`.
*   [ ] Failure scenarios emit a `workflow.failed` event.

## 4. References
*   **Event Bus Spec:** `src/maestro_hive/orchestrator/event_bus.py`
*   **Target File:** `src/maestro_hive/teams/team_execution_v2.py`
```
