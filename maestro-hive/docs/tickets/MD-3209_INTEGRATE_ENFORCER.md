```markdown
# JIRA TICKET: MD-3209

**Type:** Story
**Summary:** Integrate Enforcer Middleware into Persona Executor (Control)
**Epic:** MD-3200 (Governance Layer)
**Priority:** Critical
**Component:** Core / Security

---

## 1. Problem Statement
The `PersonaExecutorV2` currently allows agents to execute any tool (Write, Edit, Bash) without restriction. This is unsafe for an autonomous system. We need to inject the **Enforcer Middleware** to intercept and validate every tool call against the `policy.yaml`.

## 2. Technical Requirements
Modify `src/maestro_hive/teams/persona_executor_v2.py` to enforce governance rules.

### Implementation Details
1.  **Initialization:**
    *   Inject `EnforcerMiddleware` into `PersonaExecutor.__init__`.
    *   Load `config/governance/policy.yaml`.

2.  **Tool Interception:**
    *   Locate the point where `ClaudeCLIClient` or the tool execution logic is called.
    *   **Wrap** the execution in a validation block:
        ```python
        action = AgentAction(tool=tool_name, args=args, agent_id=self.persona_id)
        if not self.enforcer.validate(action):
            raise GovernanceViolation(f"Action {tool_name} denied by policy.")
        ```

3.  **Handling Violations:**
    *   Catch `GovernanceViolation`.
    *   Log the violation (Security Audit).
    *   **Do NOT** crash the entire workflow if possible; return a "Permission Denied" message to the LLM so it can try a different approach (if applicable), OR fail the task if it's a critical violation.

4.  **Budget Check:**
    *   Before execution, check `enforcer.check_budget(self.persona_id)`.

## 3. Acceptance Criteria
*   [ ] Attempting to write to a protected file (e.g., `policy.yaml`) throws `GovernanceViolation`.
*   [ ] Attempting to use a forbidden tool (e.g., `sudo`) throws `GovernanceViolation`.
*   [ ] Valid actions pass through with <10ms latency.
*   [ ] Violations are logged to `audit.log`.

## 4. References
*   **Enforcer Spec:** [MD-3201](./MD-3201_ENFORCER.md)
*   **Target File:** `src/maestro_hive/teams/persona_executor_v2.py`
```
