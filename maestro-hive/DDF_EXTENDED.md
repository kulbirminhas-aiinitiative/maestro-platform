# DDF Extended – Bi-/Tri-Modal Convergence Framework

Status: Draft
Date: 2025-10-12
Related: DDE_CRITICAL_REVIEW_AND_ROADMAP.md, DDE_FEEDBACK.md, DDE_AGENT_TASK_PLANNER.md

1. Purpose and scope
- Define a rigorous, auditable framework that separates Execution (how), Behavior (what/why), and Structure (how it should be shaped), then converges their independent verdicts to authorize deployment.
- Applies to micro-iterations (≤ 30–60 min) and standard iterations. Focus on automation, traceability, and risk minimization.

2. Core thesis
- Single-model pipelines conflate concerns; they are efficient until they aren’t. DDF introduces independent models whose blind spots do not overlap, then requires convergence: Built Right (DDE), Built the Right Thing (BDV), Built to Last (ACC).

3. Models and artifacts
3.1 DDE – Dependency-Driven Execution (Execution Engine)
- Artifact: Execution Manifest (YAML). DAG of tasks, capability tags, contracts, and policy gates.
- Guarantees: Parallelism, compliance, lineage, reproducibility.
- Blind spot: Assumes decomposition is correct.

3.2 BDV – Behavior-Driven Validation (Validation Engine)
- Artifact: Behavioral Manifest (feature files / Gherkin) + runner.
- Guarantees: External correctness vs business intent.
- Blind spot: Black-box; hard to localize source of failure.

3.3 ACC – Architectural Conformance Checking (Structural Engine)
- Artifact: Architectural Manifest (AaC YAML) + conformance checker.
- Guarantees: Maintainability, boundaries, dependency integrity.
- Blind spot: Structure only; not functional behavior.

4. Manifests (schemas)
4.1 Execution Manifest (excerpt)
```yaml
iteration_id: Iter-20251012-1430-001
constraints: { security: OWASP-L2, runtime: Python3.11 }
nodes:
  - id: IF.AuthAPI
    type: interface
    capability: Architecture:APIDesign
    outputs: [openapi.yaml]
    gates: [openapi-lint, semver, breaking-change-check]
  - id: BE.JWT
    type: impl
    capability: Backend:Python:FastAPI
    depends_on: [IF.AuthAPI]
    gates: [unit, coverage>=70, sast, contract-tests]
```

4.2 Behavioral Manifest (excerpt)
```gherkin
Feature: Authentication
  Scenario: Generate JWT token for valid credentials
    Given a registered user "alice@example.com" with password "p@ss"
    When she requests a token via POST /auth/token
    Then the response status is 200
    And the payload contains a valid JWT with claim "sub=alice@example.com"
```

4.3 Architectural Manifest (excerpt)
```yaml
components:
  - name: Presentation
  - name: BusinessLogic
  - name: DataAccess
rules:
  - Presentation: CAN_CALL(BusinessLogic)
  - BusinessLogic: CAN_CALL(DataAccess)
  - Presentation: MUST_NOT_CALL(DataAccess)
  - DataAccess: MUST_NOT_CALL(Presentation,BusinessLogic)
tech:
  language: python
  analyzers: [import_graph]
```

5. Lifecycle and independence
- Dual/Triple decomposition: Execution, Behavior, Architectural manifests authored independently by distinct owners to avoid biasing outcomes.
- Independence guardrails: separate repos or protected paths; CODEOWNERS; change reviews across roles (PO/QA for BDV, Architect for ACC, Tech Lead for DDE).

6. Convergence audits (deployment gate)
6.1 Execution Audit (DDE)
- Inputs: Execution Manifest, execution log, artifacts, policy results.
- Pass if: all nodes complete, blocking gates green, artifacts stamped, lineage intact.

6.2 Behavioral Audit (BDV)
- Inputs: Behavioral Manifest + runner results against integrated build.
- Pass if: all acceptance scenarios pass (allow configured flaky quarantine list with ratchet policy).

6.3 Structural Audit (ACC)
- Inputs: Architectural Manifest + static/dynamic dependency graph.
- Pass if: zero blocking rule violations (allow warnings with ADR).

6.4 Tri-Modal verdict
- Deploy only when all three audits pass. Otherwise, invoke targeted feedback loop (replan, refactor, or relax/justify policy via ADR).

7. Failure analysis matrix (diagnosis → action)
- DDE✅ / BDV❌ / ACC✅ → design/requirement gap → revisit decomposition/contracts.
- DDE✅ / BDV✅ / ACC❌ → architectural erosion → refactor before deploy; do not accept debt.
- DDE❌ / BDV✅ / ACC✅ → process/policy issue → tune gates or fix pipeline.
- DDE❌ / BDV❌ / ACC❌ → systemic failure → halt, retrospective, reduce scope.

8. Pipeline wiring (MVP)
- Jobs: dde-execute (build/test + gates), bdv-acceptance (run features), acc-conformance (static analysis), tri-audit (aggregate pass/fail).
- Block merge/deploy on tri-audit status.
- Artifact stamping: {iteration}/{node}/{artifact}; labels: iteration,node,capability,contractVersion.

9. Implementation assets (proposed in repo)
- bdv_runner.py: discovers features/*.feature, runs against base URL, emits JSON report.
- acc_check.py: builds import/call graph; applies AaC rules; emits JSON report.
- tri_audit.py: reads DDE execution log + BDV + ACC, returns single verdict with details.
- schemas/: execution_manifest.schema.json, aac.schema.json.

10. Thought process and trade-offs
- Independence vs speed: enforcing separate authors adds overhead but yields unbiased validation; mitigate with templates and generators.
- Strict gates vs delivery: start with minimal blocking set; ratchet up as signal stabilizes.
- Cost vs coverage: BDV can be expensive; prioritize top user journeys; expand iteratively.
- Static vs dynamic ACC: start static (import graph); evolve to runtime/service mesh checks for microservices.

11. Challenges and mitigations
11.1 Spec drift (IF contracts vs BDV steps)
- Mitigation: reference contracts in Gherkin (tags with contract version); fail BDV if contract version mismatches deployed artifact.

11.2 Flaky BDV tests
- Mitigation: quarantine list with auto-ratchet; require 2 green runs; track flake_rate; fail if above threshold.

11.3 ACC false positives
- Mitigation: rule tagging (BLOCKING/WARN), scoped suppressions with expiry and ADR; periodic rule tuning from violations telemetry.

11.4 Capability routing accuracy
- Mitigation: feedback loop: use gate results to update agent quality score; prefer agents with higher recent pass rates; cap WIP.

11.5 Audit completeness and performance
- Mitigation: JSONL execution log with indexes; sampling only in non-blocking telemetry; store audit cache per iteration.

12. Enhancements (roadmap)
- BDV: contract-driven test generation (derive Given/When/Then from OpenAPI examples); synthetic data fabric.
- ACC: architecture evolution diffs per iteration; visual graph diffs; SLSA provenance for structural claims.
- DDE: interface-first prioritization; preflight capacity simulation by capability; auto-replan on drift.
- Observability: OpenTelemetry spans tagged with iteration/node; dashboards for gate pass rate and tri-audit outcomes.
- Governance: ADR automation when gates are relaxed; expiry reminders.

13. Data model (minimal)
- iterations(id, ts, constraints, status)
- nodes(iteration_id, node_id, type, capability, deps[], gates[], status)
- events(iteration_id, node_id, ts, kind, payload)
- artifacts(iteration_id, node_id, path, labels, sha)
- audits(iteration_id, dde_pass, bdv_pass, acc_pass, details)

14. Metrics & SLOs
- Assign latency (P50/P95), queue wait by capability, gate pass rate first-try, BDV flake_rate, ACC violation rate, audit pass rate, integration failures.
- SLO examples: gate pass rate ≥ 85%, audit pass ≥ 95%, assign latency P95 ≤ 60s.

15. Incremental rollout plan
- Week 1–2: Execution + Behavioral manifests; minimal BDV runner; basic ACC rules; tri-audit skeleton.
- Week 3–4: Interface-first scheduling; artifact stamping; CI gates; first pilot.
- Week 5–6: ACC rule expansion; BDV coverage for top flows; telemetry baseline.
- Week 7–8: Dynamic routing; ratchet severities; second pilot.

16. Open questions
- Consumer-driven vs spec-driven contract testing? (Pact vs schema conformance)
- Multi-capability nodes: split vs co-assignment policy?
- Cross-repo tri-audit aggregation for multi-service programs?
- Security accreditation requirements (e.g., SOC2 evidence mapping) alignment with tri-audit outputs?

17. Glossary
- DDE: Dependency-Driven Execution (execution engine)
- BDV: Behavior-Driven Validation (validation engine)
- ACC: Architectural Conformance Checking (structural engine)
- DDF: Convergence framework combining the above

18. Success criteria
- Zero production deployments without tri-audit PASS.
- ≥ 30% faster cycle time vs baseline; ≤ 5% integration failures; ≥ 95% audit pass.
- Demonstrable, immutable traceability from requirement to deployed artifact and behavior.
