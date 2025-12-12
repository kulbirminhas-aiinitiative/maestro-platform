# GOVERNANCE LAYER (PHASE 2.5): DETAILED JIRA BACKLOG

**Epic:** MD-3200 (Governance Layer)
**Status:** Ready for Development
**Reference:** [RFC-001](../rfc/RFC-001_GOVERNANCE_LAYER.md)

---

## MD-3201: Implement Enforcer Middleware (Synchronous)
**Type:** Story
**Priority:** P0 (Blocker)
**Context:**
We need a "Bouncer" that sits between the Agent and the Tool Execution layer. It must be fast (<10ms latency) and fail-safe.
**Problem Statement (The Why)**:
Agents currently have unrestricted access to all tools. A rogue agent could delete the database or spend the entire budget in seconds.
**Technical Requirements (The What)**:
1. Create `src/maestro_hive/governance/enforcer.py`.
2. Implement `EnforcerMiddleware` class.
3. Intercept every tool call.
4. Validate against `config/governance/policy.yaml`:
   - Is the tool allowed for this agent role?
   - Is the target file path immutable?
   - Does the agent have sufficient budget?
5. Check `concurrency_control` (File Locking).
**Acceptance Criteria**:
- Attempting to edit `.env` returns `PermissionError`.
- A `developer_agent` attempting `deploy_prod` is blocked.
- An agent with $0.00 remaining budget is blocked.
- Overhead per call is < 10ms.

## MD-3202: Implement Auditor Service (Asynchronous)
**Type:** Story
**Priority:** P1
**Context:**
We need a "Judge" that listens to the Event Bus and performs complex, time-consuming governance checks.
**Problem Statement (The Why)**:
Some checks (like running a full test suite to verify coverage) are too slow for the synchronous Enforcer.
**Technical Requirements (The What)**:
1. Create `src/maestro_hive/governance/auditor.py`.
2. Subscribe to `agent.action`, `test.result`, `pr.merged` events.
3. Verify "Test Passed" claims (run coverage analysis).
4. Detect Sybil attacks (Identity correlation).
5. Emit `governance.reputation_change` events.
**Acceptance Criteria**:
- If an agent adds a test that doesn't increase coverage, no reputation is awarded.
- Does not block the main agent execution loop.
- Flags if 2+ agents try to edit the same file within 100ms.

## MD-3203: Implement Reputation System & Identity
**Type:** Story
**Priority:** P0
**Context:**
We need a "Social Credit" system to manage trust and influence.
**Problem Statement (The Why)**:
We cannot micromanage every agent. We need an incentive structure where good behavior is rewarded and bad behavior is punished.
**Technical Requirements (The What)**:
1. Create `src/maestro_hive/governance/reputation.py`.
2. Implement Scoring Engine based on `policy.yaml`.
3. Implement Exponential Decay (half-life 30 days).
4. Implement Role Promotion/Demotion logic.
**Acceptance Criteria**:
- `pr_merged` event increases score by 20.
- Score decreases correctly over time if inactive.
- Agent is auto-promoted to `senior_developer` after meeting criteria.
- Scores survive system restart.

## MD-3204: Implement Chaos Agents (Loki & Janitor)
**Type:** Story
**Priority:** P2
**Context:**
We need "System Agents" that maintain health through destruction and cleaning.
**Problem Statement (The Why)**:
Systems become fragile if they are never stressed. Codebases rot if they are never cleaned.
**Technical Requirements (The What)**:
1. Create `src/maestro_hive/agents/chaos/loki.py` and `janitor.py`.
2. Loki: Randomly kill worker processes and inject latency.
3. Janitor: Scan for unused files and archive old logs.
**Acceptance Criteria**:
- Loki successfully kills a worker process without bringing down the whole system.
- Janitor successfully identifies and deletes an orphaned `.tmp` file.
- Loki never kills the Database or the Enforcer.

## MD-3205: Implement Emergency Override ("God Mode")
**Type:** Story
**Priority:** P1
**Context:**
We need a "Break Glass" mechanism for human operators.
**Problem Statement (The Why)**:
If the policy itself has a bug, we need a way to bypass it to fix it.
**Technical Requirements (The What)**:
1. Create CLI tool `maestro-cli override`.
2. Require 2 different human signatures.
3. Time-limit the override token (4 hours).
4. Log EVERYTHING.
**Acceptance Criteria**:
- Standard user cannot invoke override.
- Token stops working after 4 hours.
- Actions taken during override are flagged in the log.
