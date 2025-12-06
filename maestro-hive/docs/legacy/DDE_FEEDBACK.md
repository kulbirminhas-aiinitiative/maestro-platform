# DDE Feedback – Critical Review of DDE_CRITICAL_REVIEW_AND_ROADMAP.md

Date: 2025-10-12
Owner: Architecture Review

Executive summary
- Foundation is solid; roadmap is comprehensive. Main risk is scope/complexity for a 2–3 engineer team. Re-scope to an MVP in 8 weeks that delivers 60–70% of the value: Manifest + Capability Registry + Interface-first + CI gates + minimal audit.

Top strengths observed
- Clear stage model (1–5) and phased plan (4 phases).
- Good reuse of existing assets: DAG executor, Contract Manager, PaC.
- Explicit deployment gate via audit; measurable KPIs.

Critical gaps or ambiguities
1) Capability Registry scope
- Missing concrete schema for availability/WIP, and learning/performance feedback loop.
- Action: define minimal schema (agent, skills[], proficiency, availability, wip_limit, recent_quality_score) and persistence model with indices.

2) Manifest ownership and change policy
- Who signs off and how to handle mid-iteration change? No rollback/patch protocol.
- Action: add Manifest change policy (lock, patch via IterationID+Hotfix, or defer to next iteration). Add ADR requirement for breaking changes.

3) Interface node governance
- No explicit review/approval workflow prior to lockdown.
- Action: add CODEOWNERS + required reviewers + semantic versioning rules; enforce in CI.

4) PaC coverage and placement
- Pre-flight checks are optional; should be mandatory for critical gates on PR.
- Action: classify gates by severity and execution point (pre-commit optional, PR mandatory, node-complete mandatory for BLOCKING).

5) Traceability model
- Audit algorithm outlined, but no data model for artifacts/events.
- Action: define tables or files: iterations, nodes, events, artifacts with indices; store JSONL execution log with stable schema.

6) Observability & SLOs
- OTel is Phase 2; lack of baseline metrics risks blind spots.
- Action: minimum counters now: node_ready_time, assign_latency, gate_fail_rate, queue_depth by capability; export to Prometheus.

7) Simulation/preflight
- No DAG simulation to catch deadlocks/under-capacity ahead of execution.
- Action: add pre-run: topological validation, critical path length, capacity vs. demand by capability; fail-fast if under-provisioned.

8) Security/compliance add-ons
- Missing SBOM/license scan/secrets scan; missing provenance.
- Action: add jobs: SBOM (Syft), license allowlist, Trivy/Semgrep, SLSA provenance attestation; treat as BLOCKING for release.

9) Timeline risk
- 16–20 weeks likely optimistic for full dynamic routing + audit + dashboards.
- Action: stage outcomes so Phase 1–2 produce deployable value even if Phase 3–4 slip.

MVP recommendation (8 weeks, 2–3 engineers)
- Week 1–2: Capability Registry (minimal), Manifest schema + generator (semi-automated), Interface node type + CI openapi-lint/semver.
- Week 3–4: Interface-first scheduling in DAGExecutor, artifact stamping convention, PR gates wired (unit/coverage/contract/SAST).
- Week 5–6: Minimal audit comparator (manifest vs. execution log), deploy gate, preflight DAG simulation, metrics counters.
- Week 7–8: JIT routing (basic matcher + WIP limits), limited capabilities (10–15 skills), pilot project #1.

Concrete deltas to the roadmap
- Add NodeType.INTERFACE and get_execution_order_with_interfaces() (must-run-first set).
- Extend WorkflowNode.config: capability, gates[], estimated_effort, contract_version.
- Add workflow.metadata.iteration_id; enforce artifact stamping in DAGExecutor; emit structured events with iteration/node.
- Define REST endpoints: POST /v1/manifest, GET /v1/manifest/{id}, POST /v1/audit/{id}, GET /v1/audit/{id}/report.
- Introduce queue model per capability with WIP limit and SLA; expose /v1/capabilities/queues.

Data model (minimal)
- iterations(id, timestamp, constraints, policy_set, status)
- nodes(iteration_id, node_id, type, capability, depends_on[], gates[], status, owner_agent)
- events(iteration_id, node_id, ts, kind, payload)
- artifacts(iteration_id, node_id, path, labels{iteration,node,capability,contractVersion}, sha)

Risk register (additions)
- Misrouted tasks due to stale profiles → auto-refresh profiles weekly; derive skills from recent commits/tests; fallback persona.
- Interface churn mid-iteration → apply Hotfix nodes only; forbid breaking changes; auto-replan dependents.
- Gate flakiness → quarantine flaky tests; require 2 consecutive passes; track flake_rate.

KPIs to start collecting Day 1
- Assign latency P50/P95; Gate pass rate first-try; Queue wait by capability; Audit pass rate; Rework rate; Integration failures.

Open questions for decision
- Is contract testing strategy Pact-like (consumer-driven) or spec-driven only? Choose now to wire CI.
- How to treat multi-capability nodes (e.g., Backend+Security)? Split or co-assign?
- Single-tenant vs multi-tenant Capability Registry? Impacts scaling and auth.

Next steps (2 weeks)
- Approve MVP scope; appoint owners.
- Land Manifest v1 and Capability taxonomy v1; wire CI gates for interface/impl nodes.
- Build minimal execution log + audit; run a 5–7 node pilot with interface-first path.
