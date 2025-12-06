# Dynamic Workflow Contracting Notes (Living Contracts in Fully Dynamic Environments)

Date: 2025-10-11

Purpose: Critically review the proposed contracting approach for dynamic, multi-agent projects and document how to apply and improve it within the Maestro Hive environment (DAG- and phase-driven execution with quality gates and personas).

---

## Executive Summary

Relevance: High. The proposed relational/agile, “living contract” model aligns well with Maestro Hive’s dynamic, iterative workflows and multi-agent orchestration. It addresses core pain points: evolving requirements, cross-team coordination, auditability, and rapid decisioning.

Key Improvements Needed:
- Make the “Meta-Contract” executable by tooling (schemas, validators, metrics) rather than prose-only.
- Tie micro-contracts (iteration-level SOWs) to DAG nodes, phase gates, and quality checks to enforce acceptance criteria automatically.
- Introduce objective change thresholds and a shared pain/gain ledger to align incentives and reduce disputes.
- Establish a single, version-controlled source of truth with explicit decision records and rationale.

Expected Impact:
- Faster, auditable adaptation; fewer scope disputes; improved predictability; stronger cross-agent alignment.

---

## Critical Review of the Proposal

1) Relational and Agile Contracting
- Strengths: Emphasizes shared goals, transparency, and flexible pricing models (T&M cap, fixed-per-iteration, target cost). This is compatible with rapid learning cycles.
- Gaps: Lacks explicit incentive design (e.g., value delivery vs. output), measurable collaboration SLOs, and concrete mechanisms for dispute de-escalation.
- Improvements:
  - Define collaboration SLOs (responsiveness, review SLAs, defect triage time) alongside delivery SLOs.
  - Add a lightweight risk buffer policy and “stop-the-line” triggers for systemic risk.
  - Use value slices (impact hypotheses) to prioritize scope by expected outcome, not only effort.

2) The Living Contract (Master + Micro-Contracts)
- Strengths: Clear framing of a Constitution-like Master Agreement and iterative micro-contracts.
- Gaps: Missing machine-readable structure to enable automated enforcement and reporting.
- Improvements:
  - Represent the Master and micro-contracts as versioned YAML/JSON with JSON Schema.
  - Encode roles, authority, acceptance criteria, and gates so phase/quality validators can execute them.
  - Include a decision rights matrix and escalation path with timers.

3) Change Management Mechanics
- Strengths: Sensible identification → impact analysis → approval → contract addendum flow; distinction between minor vs. major.
- Gaps: “Minor vs. major” lacks objective thresholds; rationale capture not standardized.
- Improvements:
  - Define objective impact thresholds (e.g., >10% budget delta, >1 sprint slip, >X risk points) → major.
  - Standardize impact analysis template (budget, schedule, dependencies, risk, value, ops/quality impact).
  - Enforce ADRs (Architecture/Decision Records) for significant decisions tied to change requests.

4) Coordination and Context
- Strengths: Calls for a single source of truth and structured cadences (daily sync, Scrum of Scrums, joint reviews/retros).
- Gaps: No explicit mapping to artifacts or dashboards; rationale can be lost in meetings.
- Improvements:
  - Centralize contracts, backlog, decisions, and metrics; auto-generate a contract dashboard.
  - Require context memos for significant changes (problem, evidence, alternatives, decision, follow-ups).

---

## Mapping to Maestro Hive (What to Operationalize)

Relevant Components
- contract_manager.py, dag_contract_integration.py: Load/attach contract terms to workflows.
- phase_gate_validator.py, workflow_validation.py, validation_utils.py: Enforce acceptance criteria and gates.
- dag_validation_nodes.py, dag_workflow.py: Instrument DAG nodes with contract-bound checks.
- output_contracts.py: Generate contract artifacts and summaries.
- project_review_engine.py, project_review_service.py: Reviews and decision logging.
- quality_fabric_integration.py, prometheus_metrics.py: Quality gates and metrics.

Operationalization Targets
- Machine-Readable Contracts:
  - Master: contracts/master_contract.yaml (vision, governance, roles, decision rights, change policy, incentive model, collaboration SLOs, risk policy).
  - Micro-Contracts: contracts/sow/<sprint>-<id>.yaml (goals, deliverables, acceptance criteria, KPIs, gate mappings, dependencies, value hypothesis).
  - Change Requests: contracts/changes/CR-<id>.yaml (request, impact analysis, thresholds, decision, addendum reference, ADR link).
- Tooling Integration:
  - Extend validators to read acceptance criteria and gate mappings from micro-contract files (no behavior change required until wired up; start with reporting).
  - Annotate DAG nodes with contract_ref: <sow_id> and gate: <gate_name> to trace execution to contract terms.
  - Emit Prometheus metrics for contract compliance (gate_pass_rate, change_lead_time, scope_volatility, pain_gain_balance, review_sla).
- Governance and ADRs:
  - Store ADRs under docs/adr/ADR-<id>.md; link from CRs and micro-contracts.
  - Define escalation timers in master_contract.yaml with notification endpoints.

---

## Minimal, Practical Templates (Machine-Readable)

Master Contract (YAML skeleton)
```yaml
version: 1
meta:
  id: master-2025-10
  effective_date: 2025-10-11
vision:
  outcomes:
    - description: Improve conversion by 15%
  success_criteria:
    - metric: conversion_rate
      target: ">= 0.15 uplift"
governance:
  steering_committee: [client, dev_lead, design_lead]
  decision_rights:
    - area: scope
      owner: steering_committee
      sla_days: 3
change_policy:
  thresholds:
    budget_delta_pct_major: 10
    schedule_slip_days_major: 10
    risk_score_major: 8
  process: [identify, analyze, decide, implement]
incentives:
  model: target_cost
  pain_share_pct: 50
  gain_share_pct: 50
collaboration_slos:
  review_turnaround_hours: 24
  defect_triage_hours: 24
risk_policy:
  stop_the_line_triggers: [security_blocker, prod_instability]
```

Micro-Contract (Iteration SOW)
```yaml
id: SPRINT-07
dates: {start: 2025-10-13, end: 2025-10-24}
goals:
  - description: Redesign onboarding flow
value_hypothesis: "Reduce drop-off by 20%"
acceptance_criteria:
  - id: AC1
    description: Usability score >= 85 on SUS
    evidence: test_reports/usability_2025-10-20.md
  - id: AC2
    description: Drop-off decreases by >= 15% on test cohort
    evidence: analytics/exp_123.csv
gates:
  - name: design_review
    validator: phase_gate_validator:design
  - name: qa_signoff
    validator: validation_utils:functional_suite
links:
  dag_nodes: [onboarding_redesign, ab_test_setup]
  changes: [CR-42]
```

Change Request
```yaml
id: CR-42
requestor: design_lead
summary: Redesign navigation per user tests
impact_analysis:
  budget_delta_pct: 7
  schedule_slip_days: 4
  risk_score: 5
  dependencies: [frontend, analytics]
  value: "Expected +2% conversion"
threshold_eval: minor  # per master thresholds
decision:
  status: approved
  approvers: [steering_committee]
  date: 2025-10-15
addendum: null
adr: docs/adr/ADR-0007.md
```

---

## Enforcement and Metrics

Automated Checks (report-first, then enforce)
- Gate conformity: Each DAG node mapped to a gate with pass/fail and evidence.
- Acceptance criteria satisfaction: Evidence file presence + test signal integration.
- Change lead time: CR created → decision timestamp delta.
- Scope volatility: % of backlog churn per iteration.
- Incentive ledger: pain/gain share accruals, transparent to both parties.
- Collaboration SLOs: Review/triage SLA adherence.

Dashboards
- Contract Compliance: gate_pass_rate, criteria_met, open_CR_count, change_lead_time.
- Delivery Predictability: iteration_forecast_error, scope_volatility.
- Outcome Signals: value_hypothesis vs. measured impact.

---

## Risks and Anti-Patterns
- Contract sprawl: Too many micro-contracts → mitigate with weekly bundling and archiving.
- Over-bureaucratization: Keep templates lean; default to minor changes unless thresholds exceeded.
- Incentive gaming: Publish the ledger; align to outcomes, not output.
- Meeting dependency: Enforce written decisions (ADRs) with timeboxed SLAs.

---

## Phased Adoption Plan (Low Friction)
- Phase 0 (1 week): Introduce templates; start logging CRs and ADRs; report-only metrics.
- Phase 1 (2–3 weeks): Map micro-contracts to DAG nodes and gates; add evidence links; publish dashboard.
- Phase 2 (3–6 weeks): Enforce major-change thresholds; wire collaboration SLO alerts; pilot pain/gain ledger.
- Phase 3 (ongoing): Tune thresholds; expand outcome metrics; compliance audits quarterly.

---

## How This Improves the Current Process
- Converts prose agreements into executable policy the platform can validate.
- Aligns incentives to outcomes and speed of learning, not just output volume.
- Provides auditable rationale for change with fast-path minor changes and clear major-change addenda.
- Reduces rework through explicit acceptance criteria connected to quality gates and DAG execution.

---

## Action Checklist (Getting Started in Maestro Hive)
- Create contracts/master_contract.yaml using the skeleton.
- Create contracts/sow for the next two iterations; link to DAG nodes via contract_ref.
- Start logging CRs in contracts/changes with threshold_eval field; add ADRs for major decisions.
- Enable report-only checks in validators to surface contract compliance in run logs and metrics.
- Stand up a minimal dashboard sourced from these files and Prometheus metrics.
