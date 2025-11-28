# DYNAMIC_NODES.md — Critical Review, Challenges, and Enhancements

Date: 2025-10-11

Purpose: Provide a critical review of DYNAMIC_NODES.md, challenge assumptions, and propose concrete enhancements aligned with Maestro Hive.

---

## Executive Assessment

Strengths
- Clear vision for a Living Dependency Graph (LDG) and integration with impact analysis, flow metrics, and policy engine.
- Good decomposition of ontology (Intent/Definition/Implementation/Verification/Deployment) and governance orientation.

Key Risks / Gaps
- Ontology/Schema governance (versioning, migrations) is unspecified; identity resolution and dedup not formalized.
- Event ordering, idempotency, and backpressure strategies are not defined; risk of data drift and duplicate nodes/edges.
- Graph cardinality explosion (commits, edges) threatens performance and cost; no compaction strategy.
- Multi-tenant security/PII/ACLs and data retention policies are missing.
- SLAs/SLOs for ingestion freshness and query latency not defined; “blast radius” could be slow without indexes/projections.
- Policy engine integration is conceptual; mapping to executable contract inputs (e.g., master_contract.yaml) needs specification.

---

## Challenges to Assumptions

1) Emergent Graph Stability
- High churn requires lifecycle semantics: states (active, stale, tombstoned), soft-delete, and reconciliation jobs.
- Define staleness windows per source (e.g., Jira inactive > 90d → archive bucket).

2) Identity Resolution and Idempotency
- Require composite identity keys: (source_tool, external_id, tenant_id, type_label) with deterministic uuids.
- Exactly-once not guaranteed; adopt at-least-once + dedupe tables and idempotent upserts.

3) Cardinality and Cost Control
- Commits→Stories edges can be massive. Introduce compaction: collapse per-PR, sample long histories, or persist only heads after N days.
- Maintain tiered storage: hot (recent), warm (aggregated), cold (archived).

4) Forecast Validity
- Monte Carlo assumes stationarity; incorporate regime detection and exclude exceptional periods (incidents) from training.
- Bound forecasts with policy thresholds and show uncertainty bands in UI.

5) Policy/Evidence Integrity
- “Evidence” nodes must be verifiable (hashing, immutability logs) to avoid policy gaming.

---

## Enhancements (Actionable)

A) Schema and Ontology Governance
- Publish JSON Schemas for node/edge types; include version field and semver policy.
- Migration playbook: preflight check, dual-write period, backfill, cutover, rollback.

B) Ingestion Architecture
- Event pipeline with DLQ, retry/backoff, and replay. Partition by tenant_id and source to preserve locality.
- Idempotent upserts keyed by (source_tool, external_id, tenant_id, type_label). Maintain a reconciliation job per source.
- Define ingestion SLOs: freshness p95 ≤ 2m; backlog recovery rate ≥ 5k events/min.

C) Performance and Projections
- Indexing: label + (external_id, tenant_id), (updated_at), and common traversal anchors.
- Precompute projections: materialized subgraphs for “blast radius,” “story→tests,” and “service→security” views.
- Adopt CQRS: writes to graph; reads for dashboards from denormalized Postgres/Elastic.

D) Contract-as-Code Integration (Maestro Mapping)
- Source policies from contracts/master_contract.yaml and contracts/sow/*.yaml.
- Emit violations into quality_fabric and phase_gate_validator as gate events.
- Annotate DAG nodes with contract_ref and ldg_ref; enrich run logs with policy checks and evidence links.

E) Security, Multi-Tenancy, and Compliance
- Require tenant_id on all nodes/edges; enforce edge-level ACL via labels or property filters.
- PII redaction/field-level encryption; retention rules per type (e.g., raw commits 180d, PRs 365d, metrics 730d).
- Immutable audit trail (hash chain) for significant decisions and evidence attachments; SOC2-friendly logs.

F) Reliability and Ops
- Backups with point-in-time recovery; index rebuild procedures; blue/green upgrades for the graph.
- Runbooks for ingestion stalls, DLQ sizing, and reprocessing.
- Cost guardrails: alert on node/edge growth velocity and expensive query patterns.

G) Testing Strategy
- Property-based tests for ontology constraints (no dangling edges, type-consistent relationships).
- Contract tests for adapters; replay recorded webhooks; chaos tests for out-of-order/duplicate events.

H) UI/UX Enhancements
- Blast-radius diff view (current vs. proposed); uncertainty visualizations; bottleneck swimlanes.
- Policy explainability panel (why a violation occurred, how to remediate).

---

## Minimal PoC Plan (2–3 weeks)
- Scope: Single tenant; integrate GitHub (PRs, commits) and Jira (issues).
- Build: Adapters → Kafka → Normalizer → Neo4j → simple dashboard.
- Implement: JSON Schemas, idempotent upserts, basic indexes, 3 policies wired from master_contract.yaml.
- Deliver: Blast radius for a Jira issue; gate violation surfaced in Maestro logs; p95 query < 300ms on test data.

---

## KPIs and SLOs
- Ingestion freshness p95, blast-radius query latency p95, dedupe ratio, % nodes with both upstream/downstream links, policy violation MTTR, storage growth rate, cost per 1M edges.

---

## Example Specs (Concise)

Node JSON (shared fields)
```json
{
  "uuid": "deterministic(uuid5(source_tool|external_id|tenant_id|type))",
  "tenant_id": "acme",
  "type": "UserStory|Commit|TestCase|...",
  "source_tool": "Jira|GitHub",
  "external_id": "JIRA-123|abc123",
  "name": "Title",
  "status": "InProgress",
  "labels": ["security", "payments"],
  "created_at": "2025-10-01T12:34:56Z",
  "updated_at": "2025-10-11T09:00:00Z",
  "schema_version": "1.0.0"
}
```

Edge JSON
```json
{
  "from": "uuid",
  "to": "uuid",
  "rel": "IMPLEMENTS|VALIDATES|DEPENDS_ON|...",
  "tenant_id": "acme",
  "weight": 1,
  "created_at": "2025-10-11T09:00:00Z",
  "schema_version": "1.0.0"
}
```

OPA Policy Sketch (pseudo-Rego)
```rego
package ldg.policy

violation[msg] {
  node.type == "DeployedService"
  node.labels[_] == "payment"
  not some test in edges.from[node.uuid].rel == "VALIDATES" with test.type == "SecurityScanResult"
  msg := sprintf("Service %s missing security scan", [node.name])
}
```

---

## Alignment with Maestro Hive
- Plug policies into quality_fabric_integration and phase_gate_validator; emit Prometheus metrics.
- Extend dag_workflow to accept contract_ref/ldg_ref metadata; add reporting-only phase first.
- Use output_contracts.py to publish compliance summaries per iteration SOW.

---

## Conclusion
The LDG approach is strong but needs concrete engineering for identity, performance, governance, security, and contract integration. The above enhancements de-risk adoption and make it executable within Maestro Hive with measurable outcomes.
