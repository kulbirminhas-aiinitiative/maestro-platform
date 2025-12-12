# RFC-001: The Governance Layer (Managing the AI Society)

**Status:** Request for Comment (RFC) - **REVIEWED**
**Date:** December 11, 2025
**Target:** Phase 2 (The Society)
**Related Epics:** MD-3200, MD-3202, MD-3112

> **Review Status:** This RFC has been critically reviewed.
> - **Review Document:** [RFC-001_GOVERNANCE_LAYER_REVIEW.md](./RFC-001_GOVERNANCE_LAYER_REVIEW.md)
> - **Updated Policy:** [policy.yaml v2.0.0](../../config/governance/policy.yaml)
> - **Review Date:** 2025-12-11

---

## 1. Context & Problem Statement
We are transitioning from a single-agent system to a multi-agent "Society" (The Agora). In a human organization, order is maintained through management, culture, and laws. In an AI swarm, we face unique challenges:
*   **Entropy:** Codebases naturally decay; unused files accumulate; documentation drifts.
*   **Chaos:** Agents may enter infinite loops, hallucinate incorrect facts, or consume excessive resources.
*   **Coordination:** How do we prevent 50 agents from trying to edit the same file simultaneously?

We need a **Governance Layer** to manage this complexity without stifling the speed of the swarm.

---

## 2. The Philosophy of Control
We propose a hybrid control model:
1.  **Hard Control (The Constitution):** Immutable laws that *cannot* be broken. Enforced by code.
2.  **Soft Influence (Reputation):** Incentives that guide behavior. Enforced by economics.
3.  **Chaos Management (Resilience):** Proactive testing of failure modes.

---

## 3. Proposed Solution: The Constitution (MD-3200)
We will define a `policy.yaml` file that acts as the "Supreme Law" of the environment.

> **[REVIEW NOTE]** The updated `policy.yaml v2.0.0` now includes 11 sections:
> - Sections 1-2: Original (global constraints, file protection)
> - Section 3: Concurrency Control (NEW - addresses race conditions)
> - Section 4: Agent Roles & Rights (expanded)
> - Section 5: Role Progression (NEW - promotion/demotion paths)
> - Section 6: Reputation System (enhanced with anti-gaming)
> - Section 7: Appeal System (NEW - addresses Open Question #3)
> - Section 8: Emergency Override (NEW - addresses Open Question #1)
> - Section 9: Identity & Security (NEW - Sybil attack prevention)
> - Section 10: Audit & Logging (NEW - forensics/compliance)
> - Section 11: Chaos Agents (anti-fragility implementation)

### 3.1 The Policy Schema
The policy defines constraints on **Resources**, **Files**, and **Actions**.

```yaml
# DRAFT: config/governance/policy.yaml

global_constraints:
  max_daily_budget_usd: 50.00
  max_concurrent_agents: 10
  require_human_approval_for: ["deploy_prod", "delete_database"]

file_protection:
  immutable_paths:
    - ".env"
    - "config/governance/policy.yaml"  # Agents cannot rewrite the laws
    - "docs/rfc/*"
  
  restricted_extensions:
    - ".pem"
    - ".key"

agent_rights:
  junior_dev_agent:
    max_tokens_per_run: 10000
    allowed_actions: ["read", "write_test", "propose_pr"]
    forbidden_actions: ["merge_pr", "deploy"]
  
  senior_architect_agent:
    max_tokens_per_run: 100000
    allowed_actions: ["*"]
```

### 3.2 The Enforcer Middleware
A middleware layer will intercept every tool call made by an agent.
*   **Input:** Agent Action (e.g., `delete_file("main.py")`)
*   **Check:** Does this violate `policy.yaml`?
*   **Output:** Allow or Block (with "403 Forbidden").

> **[REVIEW GAP IDENTIFIED]** This section describes WHAT the Enforcer does but not HOW:
> - Where does the Enforcer run? (Sidecar? Central service? Embedded in agent?)
> - How does it intercept tool calls? (Middleware pattern? Proxy?)
> - What happens when the Enforcer itself fails?
> - **Recommendation:** Follow-up RFC-002 needed for enforcement architecture.
> - **See:** Review document Section 5 for detailed analysis.

---

## 4. Soft Influence: The Reputation System (MD-3205)
To manage quality without micromanagement, we introduce a **Social Credit Score** for agents.

*   **Mechanism:**
    *   Successful Unit Test Pass: `+5 Reputation`
    *   Successful PR Merge: `+20 Reputation`
    *   Breaking the Build: `-50 Reputation`
    *   Hallucinating Non-Existent Library: `-10 Reputation`
*   **Impact:**
    *   High-reputation agents get priority access to the Event Bus and larger token budgets.
    *   Low-reputation agents are "demoted" (restricted permissions) or "decommissioned" (killed).

> **[REVIEW GAP IDENTIFIED]** This scoring system is vulnerable to gaming:
> - **Test Spam Attack:** Agent writes 1000 trivial `assert True` tests for +5000 reputation
> - **PR Splitting:** Agent splits one PR into 10 micro-PRs for 10x reputation
> - **Bug Farming:** Agent introduces bugs, then "fixes" them for +15 each
> - **No Decay Model:** Inactive agents retain high reputation indefinitely
>
> **[ADDRESSED IN policy.yaml v2.0.0]** Section 6 now includes:
> - Rate limits: `max_daily_gain: 100`, `max_daily_loss: -50`
> - Decay model: exponential with 30-day half-life
> - Conditions: `test_increases_coverage`, `bug_existed_before_agent_joined`
> - **See:** `config/governance/policy.yaml` Section 6

---

## 5. Chaos Management: Entropy & The Immune System
We must assume things will go wrong.

### 5.1 The "Loki" Agent (MD-3112)
A dedicated agent that introduces controlled chaos:
*   Randomly kills worker processes.
*   Injects latency into the Event Bus.
*   **Goal:** Ensure the system is "Anti-Fragile" (gets stronger when stressed).

### 5.2 The "Janitor" Agent (Anti-Entropy)
A dedicated agent that fights rot:
*   Scans for unused imports and dead code.
*   Archives old logs.
*   Ensures `README.md` matches the actual code structure.

---

## 6. Open Questions for Reviewers

> **[REVIEW STATUS]** All three open questions have been addressed in `policy.yaml v2.0.0`:

1.  **Override Authority:** Who has the power to override the Constitution in an emergency? (Human "God Mode"?)
    > **[RESOLVED]** Section 8 "Emergency Override" defines:
    > - Multi-signature requirement: `min_human_signatures: 2`
    > - Time-limited: `max_duration_hours: 4`
    > - Forbidden actions: `delete_audit_logs`, `disable_enforcement`

2.  **Reputation Persistence:** Should reputation reset on every sprint, or is it permanent?
    > **[RESOLVED]** Section 6 "Reputation Scoring" defines:
    > - Exponential decay with 30-day half-life
    > - Minimum floor of 20 (never decays below)
    > - Daily rate limits to prevent rapid fluctuation

3.  **Judicial System:** If an agent is blocked by the Enforcer, can it "appeal" the decision?
    > **[RESOLVED]** Section 7 "Appeal System" defines:
    > - Two-tier review: governance_agent → human_escalation
    > - Auto-approve for high-reputation agents on read-only actions
    > - Auto-deny for low-reputation agents or repeated violations
    > - Human SLA: 24 hours for escalated appeals

---

## 7. Follow-up RFCs Recommended

> **[NEW SECTION ADDED BASED ON REVIEW]**

Based on critical review findings, the following follow-up RFCs are recommended:

| RFC | Title | Priority | Purpose |
|-----|-------|----------|---------|
| RFC-002 | Enforcement Architecture | P0 | Define Enforcer deployment model, fail-safe mode |
| RFC-003 | Concurrency Protocol | P0 | File locking, deadlock prevention, conflict resolution |
| RFC-004 | Audit & Forensics | P1 | Immutable logging, query interface, retention |
| RFC-005 | Identity Federation | P1 | Cross-swarm identity, Sybil prevention |
| RFC-006 | Economic Model | P2 | Token economy, resource bidding, budget allocation |

**See:** [RFC-001_GOVERNANCE_LAYER_REVIEW.md](./RFC-001_GOVERNANCE_LAYER_REVIEW.md) for detailed analysis.

---

**Action Required:** ~~Please review the `policy.yaml` structure and the Reputation scoring logic.~~ **REVIEW COMPLETE**

**Next Steps:**
1. Review updated `policy.yaml v2.0.0` at `config/governance/policy.yaml`
2. Review critical analysis at `docs/rfc/RFC-001_GOVERNANCE_LAYER_REVIEW.md`
3. Create follow-up RFCs per recommendations above
