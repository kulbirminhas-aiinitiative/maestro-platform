# AGENT3: SDLC-as-DAG UltraThink Architecture

Date: 2025-10-11
Author: System Analysis (AGENT3)

---

## Objective
Design a modular SDLC workflow as a Directed Acyclic Graph (DAG) where:
- Each phase is a pluggable node with well-defined inputs/outputs/contracts
- Nodes can be executed/re-executed independently with forward/back references
- Full data/context/instructions are stored and passed across nodes
- Frontend and backend remain in sync via a shared workflow model & APIs
- The system supports checkpointing, replay, branching, and human-in-the-loop

This document proposes an architecture, execution model, data contracts, storage, observability, and a migration path from current scripts to a full DAG.

---

## Core Concepts

### 1) Workflow = DAG
- Nodes represent phases (requirements, design, implementation, testing, deployment) and/or sub-phases (API design, FE scaffold, BE contract, QA suite generation).
- Edges represent dependencies (A → B means B depends on A’s outputs/contracts).
- Multiple entry points: run any node with available prerequisites.
- Branching: parallel subgraphs (e.g., FE/BE work from API contract).
- Deterministic node identity: nodes are addressed as workflow_id:graph_id:node_id:version.

### 2) Node Contract (Interface)
Every node implements a consistent interface and schema:
- Inputs: references to prior node outputs, global context, and handoff instructions.
- Outputs: artifacts (files), structured results (JSON), quality metrics.
- Handoff: explicit instructions and acceptance criteria for downstream nodes.
- Contract: JSON Schema/Protobuf describing inputs/outputs, with versioning.

Node execution signature:
- execute(request: NodeRequest) -> NodeResult
- NodeRequest includes: workflow metadata, input references, prior context, instruction set, run parameters (retries, cache policy), and human overrides.
- NodeResult includes: artifacts, outputs (typed), quality metrics, provenance, and a HandoffSpec for children.

### 3) HandoffSpec (Forward References)
A first-class downstream instruction artifact stored in the context store:
- phase_from, phase_to, created_at, version
- instructions[]: ordered, explicit steps for next node(s)
- artifacts_from_previous_phase: resolved paths (e.g., openapi_spec, mock_endpoint)
- acceptance_criteria_for_next_phase
- contract_ids referenced

### 4) Backreferences (Backward Context)
- Each node can declare required upstream contracts and datasources.
- Backreferences are resolved through a global Context Graph that maps node outputs to storage locations and types.
- Version pinning: a node can depend on upstream run X or a semantic version of a contract (e.g., api_contract@1.2.0).

### 5) Storage & Context Management
- Context Store (CS): durable store keyed by workflow_id + node_id + run_id
  - Stores NodeResult JSON, HandoffSpec, Quality, and lineage metadata
  - Stores Artifact Manifests with content-addressable digests
- Artifact Store (AS): file/object store for generated files (local, S3-compatible)
- Conversation Store (CoS): shared conversation threads per workflow (AutoGen-style)
- Vector Store (VS): embeddings for retrieval-augmented context (optional)

### 6) Re-execution Semantics
- Determinism: Node result cache keyed by inputs + versions + parameters
- Memoization: If nothing changed (including upstream digests), return cached result
- Invalidation: Changes in upstream contracts/outputs invalidate dependents transitively
- Partial replays: Re-run a subgraph from a node downwards

### 7) Sync FE/BE
- Single Source of Truth: Workflow Service exposes the DAG + state over an API; FE consumes this to render and control executions
- Event bus (WebSocket/SSE) streams node state changes to FE
- Graph and State versioning (optimistic concurrency with ETags)
- Frontend triggers executions via API; backend orchestrates and persists state

---

## Logical Architecture

1) Workflow Service (WS)
- CRUD for workflows, nodes, edges
- Run orchestration APIs (submit, resume, cancel)
- State & lineage queries (status, logs, artifacts, diffs)
- Emits events for FE (progress, completion, validation)

2) Orchestrator
- Interprets DAG and schedules node runs respecting dependencies
- Supports parallel groups, retries, backoff, circuit breakers
- Provides hooks for human-in-the-loop gates
- Implements memoization & invalidation policies

3) Execution Engine
- Runs node plugins (containers or in-process)
- Injects context, instructions, and contracts
- Streams logs, collects artifacts & metrics
- Reports NodeResult to WS and persists to CS/AS

4) Contract/Schema Registry
- Stores JSON Schemas/Protobuf for inputs/outputs
- Validates NodeRequest/NodeResult
- Tracks breaking/non-breaking changes (semver)

5) Context Plane
- Context Store (CS): NodeResults, HandoffSpecs, metrics, lineage
- Artifact Store (AS): files with digests (sha256) + manifests
- Conversation Store (CoS): AutoGen-like shared history per workflow
- Vector Store (VS): optional RAG for long-term memory retrieval

6) Observability
- Unified logging & tracing (OpenTelemetry)
- Metrics (quality, throughput, cache hit-rate)
- Data lineage (node inputs → outputs)

---

## Data Model (Key Schemas)

### WorkflowSpec (YAML/JSON)
```yaml
workflow_id: sdlc_2025_01
name: "SDLC DAG"
version: 1
nodes:
  - id: requirements
    type: phase
    plugin: requirements_analyzer
    outputs:
      - requirements_doc
  - id: design
    type: phase
    plugin: design_architect
    depends_on: [requirements]
    inputs:
      - requirements_doc
    outputs:
      - architecture_doc
      - api_contract
  - id: implementation_backend
    type: phase
    plugin: backend_builder
    depends_on: [design]
    inputs:
      - api_contract
    outputs:
      - backend_artifacts
      - api_spec
      - mock_server
  - id: implementation_frontend
    type: phase
    plugin: frontend_builder
    depends_on: [design]
    inputs:
      - api_contract
      - api_spec? # optional if using mock
    outputs:
      - frontend_artifacts
  - id: testing
    plugin: qa_runner
    depends_on: [implementation_backend, implementation_frontend]
    inputs:
      - backend_artifacts
      - frontend_artifacts
    outputs:
      - test_reports
```

### NodeRequest
```json
{
  "workflow_id": "...",
  "graph_version": 3,
  "node_id": "implementation_frontend",
  "run_id": "uuid",
  "inputs": {
    "api_contract": {"ref": "design/api_contract@1.0.0"},
    "api_spec": {"ref": "implementation_backend/api_spec@sha256:..."}
  },
  "context": {
    "handoff": { /* HandoffSpec */ },
    "conversation": { /* recent messages */ },
    "parameters": {"quality_threshold": 0.85}
  },
  "execution": {"retries": 2, "cache": true}
}
```

### NodeResult
```json
{
  "workflow_id": "...",
  "node_id": "implementation_frontend",
  "run_id": "uuid",
  "status": "COMPLETED",
  "artifacts": [
    {"path": "frontend/package.json", "digest": "sha256:..."},
    {"path": "frontend/src/App.tsx", "digest": "sha256:..."}
  ],
  "outputs": {
    "frontend_artifacts": {"dir": "frontend/", "manifest": "manifest.json"}
  },
  "handoff": {
    "phase_from": "implementation_frontend",
    "phase_to": "testing",
    "instructions": ["Run e2e tests against mock and real API"],
    "artifacts_from_previous_phase": {"api_spec": "contracts/api_spec.yaml"},
    "acceptance_criteria_for_next_phase": ["All smoke tests pass"]
  },
  "quality": {"score": 0.87},
  "lineage": {"inputs": ["design/api_contract@1.0.0"], "upstreams": ["implementation_backend"]},
  "duration_seconds": 92.4
}
```

---

## Node Plugin Model

- Plugin Manifest: declares NodeRequest schema, NodeResult schema, required permissions, tool access, resource needs.
- Execution isolation: run in container or sandbox with mounted AS/CS.
- Tooling adapters: LLMs, codegen, test runners, linters, contract validators.
- Reusable libraries: persona executors can be re-used as plugin internals.

---

## Execution Semantics

- Topological scheduling by the Orchestrator; identify parallel groups.
- Circuit breakers on edges (boundary validation failures open circuits).
- Human gates: nodes marked as manual_approval pause until FE approval arrives.
- Memoization: hash(NodeRequest) → cache key; if match, short-circuit.
- Retry policy per node (exponential backoff, jitter); idempotent writes.

---

## Frontend/Backend Synchronization

- Shared DAG State Model:
  - FE consumes WorkflowSpec + RunGraph (node states) via WS.
  - FE subscribes via WS events to show live progress.
  - FE triggers re-execution of nodes/subgraphs with parameters.
- Deterministic node ids/versions ensure FE-Backend alignment.
- Graph editing: FE edits create a new graph_version; WS enforces optimistic concurrency.

---

## Storage Strategy

- Context Store (CS):
  - JSON documents in a KV/DB (SQLite/Postgres) keyed by (workflow_id, node_id, run_id)
  - Index by latest successful run per node and by artifact digests
- Artifact Store (AS):
  - File system or S3-compatible bucket, content-addressable (sha256)
  - Manifests per node run listing files + digests
- Conversation Store (CoS):
  - Append-only message log per workflow (AutoGen style), persisted and referenced in NodeRequests
- Vector Store (VS):
  - Optional; embed key artifacts/messages for retrieval during execution

---

## Contracts and Validation

- Contract Registry:
  - JSON Schema for NodeRequest/NodeResult types and HandoffSpec
  - API/Interface contracts (OpenAPI/GraphQL schemas) with versioning
- Boundary checks:
  - Before executing a node, validate that upstream NodeResults conform to expected schemas and that HandoffSpec is present and complete.
- Diffing & breaking change detection:
  - If upstream contract changes, mark downstream nodes invalid and require re-execution.

---

## Observability & Governance

- OpenTelemetry for distributed traces across node runs.
- Metrics: execution times, success rates, cache hit/miss, quality scores.
- Auditing: who triggered runs, approvals, and changes to WorkflowSpec.
- RBAC: restrict sensitive nodes (e.g., deployment) to authorized users.
- Policy-as-code: enforce gates (tests must pass, quality threshold) before promoting artifacts.

---

## Migration Plan (from current scripts)

Phase 1: Spec & Wrapper (1-2 weeks)
- Define WorkflowSpec JSON/YAML and HandoffSpec schemas.
- Wrap existing split-mode phase executors as Node Plugins without changing internals.
- Implement minimal Orchestrator that reads WorkflowSpec and schedules nodes.
- Persist NodeResult + HandoffSpec to CS/AS; reuse existing checkpoints.

Phase 2: Context Enrichment & Contracts (1-2 weeks)
- Generate HandoffSpec in each node; pass resolved artifact paths (api_spec, mock endpoint) to downstream nodes.
- Enforce boundary validation: node won’t run if required HandoffSpec/contract is missing.
- Add memoization: cache NodeResults keyed by request hash.

Phase 3: FE/BE Sync & Events (1-2 weeks)
- Introduce Workflow Service with REST/GraphQL and WebSocket events.
- FE adopts DAG view, live status, re-run controls, approvals.
- Add graph_versioning and optimistic concurrency for edits.

Phase 4: Advanced (ongoing)
- Conversation Store integration (AutoGen group-chat context injected into NodeRequests).
- Vector Store for long-term memory and RAG-driven execution prompts.
- Pluggable runners (local, k8s, serverless) and resource-aware scheduling.

---

## Minimal Backward-Compatible Changes Now

- Produce HandoffSpec after each current phase and persist alongside checkpoints.
- Orchestrator shim: small module that composes the current phases as a DAG and calls existing execute_phase in dependency order.
- Coordinator context enrichment: include spec paths, mock endpoints, and handoff JSONs in persona prompts.

---

## Optional Technology Choices

- Orchestration Frameworks: Temporal, Dagster, Prefect (pros: reliability, UI; cons: integration overhead). Start with in-repo orchestrator, evaluate migration later.
- Storage: Postgres for CS (JSONB), S3 for AS, Redis for event fanout.
- API: REST + WebSocket initially; GraphQL for FE flexibility.

---

## Example: Lightweight Orchestrator Pseudocode

```python
spec = load_workflow_spec(path)
state = WorkflowState()

while state.has_runnable_nodes(spec):
    for node in state.runnable_nodes(spec):
        req = build_node_request(spec, node, context_store)
        if cache_hit(req):
            result = load_cached_result(req)
        else:
            result = execute_plugin(node.plugin, req)
            persist_result(result)
        state.update(node, result)
        emit_event("node_completed", result)
```

---

## Success Criteria
- Independent node execution & re-execution with memoization.
- Explicit HandoffSpec passed & validated at boundaries.
- FE shows live DAG state and can trigger targeted re-runs.
- Synchronization between FE/BE via shared WorkflowSpec + events.
- Measurable reduction in leakage and rework; reliable FE+BE outputs.

---

## Conclusion
Representing SDLC as a DAG with first-class handoffs, contracts, and a shared context plane enables modular, re-runnable workflows that scale from single-script to enterprise orchestration. The migration plan focuses on minimal wrappers and context enrichment first, then adds orchestration services, FE sync, and advanced memory, preserving current investments while unlocking robust, pluggable execution.
