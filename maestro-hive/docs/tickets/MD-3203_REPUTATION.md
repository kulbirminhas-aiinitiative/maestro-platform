# JIRA TICKET: MD-3203

**Type:** Story
**Summary:** Implement Reputation System & Identity
**Epic:** MD-3200 (Governance Layer)
**Priority:** High
**Component:** Core / Identity

---

## 1. Problem Statement (The Why)
We cannot micromanage every agent in a swarm of 1,000. We need an incentive structure where good behavior is rewarded and bad behavior is punished, creating a self-regulating "Social Credit" system.

## 2. Technical Requirements (The What)
Implement the logic for tracking Agent Reputation and managing Identity/Roles.

### Responsibilities
1.  **Scoring Engine:** Calculate reputation based on events defined in `policy.yaml` (Section 6).
2.  **Decay Model:** Implement the exponential decay (half-life 30 days) to prevent stagnation.
3.  **Role Management:** Automatically promote/demote agents based on their score (Section 5 of Policy).
4.  **Identity:** Ensure every agent has a cryptographic signature (Ed25519) for their actions.

### Technical Specs
*   **File Path:** `src/maestro_hive/governance/reputation.py`
*   **Storage:** Persistent KV store (Redis/Postgres) for `agent_id -> {score, role, history}`.
*   **Logic:** State machine for Role transitions (Dev -> Senior -> Architect).

## 3. Acceptance Criteria
*   [ ] **Scoring:** `pr_merged` event increases score by 20.
*   [ ] **Decay:** Score decreases correctly over time if inactive.
*   [ ] **Promotion:** Agent is auto-promoted to `senior_developer` after meeting criteria.
*   [ ] **Demotion:** Agent is auto-demoted if score drops below threshold.
*   [ ] **Persistence:** Scores survive system restart.

## 4. References
*   **Design Spec:** [RFC-001: Governance Layer](../rfc/RFC-001_GOVERNANCE_LAYER.md)
*   **Configuration:** [Policy Configuration](../../config/governance/policy.yaml)
