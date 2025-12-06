# Dependency-Driven Execution (DDE) – Agent Task Planner

Purpose: A practical, capability-driven plan for human/AI agents to execute a phase-less, dependency-driven SDLC with contracts, policies, and full traceability.

Scope: Applies to micro-iterations (≤ 30–60 min) with Iteration Manifest as the immutable contract.

--------------------------------------------------------------------------------

1) Roles and Responsibilities
- Orchestration (DAG Runner): Owns DAG build, prioritization, scheduling, telemetry.
- Contract Owner(s): Produce and lock interface contracts (API/schema/events).
- Policy Owner(s): Maintain Policy-as-Code (OPA) and quality gates.
- Capability Registry Owner: Maintain skill taxonomy and agent capability profiles.
- Implementers (Human/AI Agents): Execute typed nodes; comply with contracts/policies.

--------------------------------------------------------------------------------

2) Iteration Manifest (Micro-Contract)
Artifact: manifest.yml committed at iteration start.

Template:
IterationID: Iter-YYYYMMDD-HHMM-###
Timestamp: <UTC-ISO8601>
Constraints:
  SecurityStandard: OWASP-L2
  LibraryPolicy: InternalOnly
  Runtime: Node18|Python3.11
Policies:
  - id: coverage >= 70% (severity: BLOCKING)
  - id: no-501-stubs (severity: BLOCKING)
Nodes:
  - id: IF.AuthAPI
    type: interface
    capability: Architecture:APIDesign
    outputs: [openapi.yaml]
    gates: [openapi-lint, versioning]
  - id: FE.Login
    type: impl
    capability: Web:React
    dependsOn: [IF.AuthAPI]
    gates: [unit-tests, contract-tests]
  - id: BE.JWT
    type: impl
    capability: Backend:Python:FastAPI
    dependsOn: [IF.AuthAPI]
    gates: [unit-tests, sast, contract-tests]

Rules:
- No node executes unless its dependsOn completed and contracts locked.
- All nodes carry capability tag(s) and gates.
- Artifact stamping: {IterationID}/{NodeID}/{ArtifactName} with metadata labels.

--------------------------------------------------------------------------------

3) Capability Registry and Matching
Tasks:
- Define taxonomy (e.g., Web:React, Backend:Python:FastAPI, Security:SAST, Data:ETL, Infra:K8s).
- Profile all agents with proficiency, throughput, and availability windows.
- Expose a Match(node.capability)->[agent] API for just-in-time routing.
Acceptance:
- 100% nodes match at least 2 agents (primary/backup) or are escalated.

--------------------------------------------------------------------------------

4) Interface-First Prioritization (Critical Path Unblock)
Goal: Minimize rework by locking interface contracts early.
Checklist (per Interface node):
- Draft spec (OpenAPI/Proto/JSONSchema) with examples.
- Lint & version bump (no breaking change unless approved).
- Publish to repo path contracts/{domain}/{name}/{version}/.
- Freeze: update manifest status to locked=true.
Acceptance Gates:
- openapi-lint=pass, breaking-change-check=pass, reviewers=≥1.
Timebox: ≤ 10 minutes per interface in micro-iteration.

--------------------------------------------------------------------------------

5) Implementer Node SOP (for any typed task)
Pre-flight:
- Pull manifest.yml; verify dependsOn complete and contracts locked.
- Fetch policies applicable to node.gates; run local pre-check (OPA, linters, tests).
- Sync branch naming: feature/{IterationID}/{NodeID} and commit prefix [{NodeID}].
Execution:
- Implement against locked interface and constraints.
- Produce artifacts (code/test/specs) under stamped path.
Validation (blocking unless stated):
- Unit tests (blocking), contract tests (blocking), coverage threshold (blocking), SAST (blocking), lint/format (warning or blocking by policy).
Publication:
- Push branch; CI runs the same gates; artifacts are labeled with IterationID/NodeID.
Acceptance:
- All gates pass; CI status green; PR auto-comment includes validation summary.

--------------------------------------------------------------------------------

6) Quality Gates as Policy (PaC)
Authoring:
- Define gate set per node type: interface, impl.web, impl.backend, data, infra.
- Encode in OPA or equivalent; keep severity levels (BLOCKING/HIGH/WARN).
Execution Points:
- Pre-commit (optional fast checks), PR (mandatory), DAG node completion (server-side), pre-deploy (traceability audit).
Evidence:
- Store gate results per node as validation_results in execution context and as CI artifacts.

--------------------------------------------------------------------------------

7) Traceability and Lineage
Conventions:
- Branch: feature/{IterationID}/{NodeID}
- Commits: [{NodeID}] message
- PR Title: [{IterationID}/{NodeID}] <summary>
- Artifact labels: iteration, node, capability, contractVersion
Recording:
- Events emitted by DAGExecutor include iteration_id, node_id, capability, validation summary.
- Store manifest, execution log, and gate results in /reports/{IterationID}/.

--------------------------------------------------------------------------------

8) CI/CD Wiring (minimal)
Required Jobs:
- contract-validate (interface nodes): openapi-lint, breaking-change-check
- build-and-test (impl nodes): build, unit, coverage, contract-tests, SAST
- post-comment: summarize gates and link to artifacts
Deploy Gate:
- Traceability Validator (Manifest vs As-Built) must pass 100%.

Example (pseudo GitHub Actions):
- on: pull_request
- jobs:
  contract-validate: if: contains(PR_TITLE, 'IF.')
  build-and-test: run project tests + OPA gates
  traceability: on merge to main; fails if manifest nodes not 100% complete

--------------------------------------------------------------------------------

9) Risk Controls and Replan Triggers
Controls:
- Early interface lock; blocking PaC at node and PR; canary integration for contract edges; WIP limits per capability; backpressure queues.
Triggers:
- Schema drift detected → pause dependents; open Interface Hotfix node.
- SLA breach on capability queue → auto-reroute or escalate.
- Gate regression on main → auto-revert last merge and open incident.

--------------------------------------------------------------------------------

10) Daily Micro-Iteration Playbook (≤ 60 min)
00–05: Intake → refine Manifest diffs (new nodes/edges, gates).
05–15: Prioritize and lock Interface nodes.
15–50: Parallel execution of ready nodes (JIT routing; strict gates).
50–55: Traceability audit (Manifest vs As-Built); fix nits.
55–60: Merge/deploy if audit passes; queue deltas for next iteration.

--------------------------------------------------------------------------------

11) Agent Prompts and Ticket Templates
Implementer Prompt (per node):
- Inputs: IterationID, NodeID, capability, dependsOn outputs, locked contract, policies, acceptance criteria.
- Output: code/test changes, artifact list, validation_results JSON.
Ticket Template:
NodeID:
Capability:
DependsOn:
Contract Version:
Acceptance (gates):
Artifacts:
CI Status:
Notes:

--------------------------------------------------------------------------------

12) Mapping to Current Repo and Gaps
Use now:
- dag_api_server_robust.py: execute endpoints and WebSocket events
- dag_executor.py: node execution + contract-as-code validation hooks
- dag_contract_integration.py: legacy contract checks (keep as non-blocking or migrate)
- validation_integration.py: build-centric validation
Add next:
- Iteration Manifest endpoint + storage; artifact stamping utility
- Capability Registry + matcher
- Interface node type + prioritization rule
- Traceability Validator (Manifest vs As-Built) as deploy gate

--------------------------------------------------------------------------------

Success Criteria
- 100% of executed nodes have green gates and stamped artifacts.
- Zero integration failures at contract edges.
- Traceability audit passes on first attempt ≥95% of iterations.
- Lead time per ready node ≤ one iteration; queue wait time per capability within SLA.
