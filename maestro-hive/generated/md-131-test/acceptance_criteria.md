# Acceptance Criteria: DDE Workflow Execution Engine

**JIRA Task**: MD-131
**Epic**: MD-592 - Core Execution Engine (DDE)
**Date**: 2025-11-22
**Author**: Requirements Analyst

---

## Overview

This document defines the acceptance criteria for the DDE Workflow Execution Engine implementation. Each criterion is testable and measurable to ensure clear validation of requirements.

---

## 1. DDE Executor Service

### AC-DDE-001: Interface-First Execution

**Given** a workflow with interface nodes and implementation nodes
**When** the workflow executes
**Then**:
- [ ] All interface nodes complete before any dependent implementation node starts
- [ ] Interface nodes are identified by `NodeType.INTERFACE`
- [ ] Dependency edges from implementation to interface nodes are respected
- [ ] Execution order log shows interface completion timestamps before dependent node start timestamps

**Verification Method**: Integration test with multi-node DAG

---

### AC-DDE-002: Dependency Resolution

**Given** a workflow DAG with complex dependencies
**When** the system resolves execution order
**Then**:
- [ ] Topological sort produces valid execution order
- [ ] Circular dependencies are detected and rejected with clear error message
- [ ] Missing dependency references trigger validation error before execution
- [ ] Dependency graph can be serialized for debugging

**Verification Method**: Unit tests with various graph structures

---

### AC-DDE-003: Parallel Execution

**Given** nodes A, B, C where A→B and A→C (B and C are independent)
**When** node A completes
**Then**:
- [ ] Nodes B and C start execution within 1 second of A completion
- [ ] Both nodes execute concurrently
- [ ] Parallelism does not exceed configured WIP limit
- [ ] Execution time is measurably shorter than sequential execution

**Verification Method**: Performance test with timing assertions

---

### AC-DDE-004: Capability-Based Routing

**Given** a node with capability requirement `Backend:Python:FastAPI`
**When** the node becomes ready for execution
**Then**:
- [ ] Capability Registry is queried with the required skills
- [ ] Best matching agent is selected based on proficiency, availability, and load
- [ ] Task is assigned to selected agent within 500ms
- [ ] If no capable agent found, fallback to default assignment with warning log

**Verification Method**: Integration test with mocked Capability Registry

---

### AC-DDE-005: Context Injection

**Given** a node with dependencies and quality gates
**When** the node is assigned to an agent
**Then** the task context includes:
- [ ] `iteration_id` and `node_id`
- [ ] `depends_on_outputs` with artifacts from completed dependencies
- [ ] `locked_contracts` with URLs to contract specifications
- [ ] `quality_gates` with gate names, thresholds, and severities
- [ ] `acceptance_criteria` from node configuration
- [ ] `estimated_effort` in minutes

**Verification Method**: Unit test asserting context structure

---

### AC-DDE-006: State Management

**Given** a workflow in execution
**When** states change
**Then**:
- [ ] Valid states: PENDING, READY, RUNNING, COMPLETED, FAILED, SKIPPED
- [ ] State transitions are persisted to storage
- [ ] Invalid transitions (e.g., COMPLETED → PENDING) are rejected
- [ ] State can be queried at any time during execution
- [ ] After service restart, execution resumes from persisted state

**Verification Method**: State machine tests + restart recovery test

---

### AC-DDE-007: Pause/Resume Operations

**Given** a running workflow
**When** pause command is issued
**Then**:
- [ ] No new nodes start execution
- [ ] Currently running nodes complete normally
- [ ] Workflow state changes to PAUSED
- [ ] Resume command starts execution from where it paused
- [ ] Cancel command terminates workflow and marks remaining nodes as CANCELLED

**Verification Method**: Integration test with pause/resume sequence

---

### AC-DDE-008: Retry Logic

**Given** a node with `maxRetries: 3` and `retryDelay: 1000ms`
**When** the node fails with a retryable error
**Then**:
- [ ] Node retries up to 3 times
- [ ] Exponential backoff applied (1s, 2s, 4s)
- [ ] Each attempt is logged with attempt number
- [ ] After 3 failures, node state is FAILED
- [ ] Non-retryable errors fail immediately

**Verification Method**: Unit test with simulated failures

---

### AC-DDE-009: Execution Events

**Given** workflow execution
**When** state changes occur
**Then** events are emitted for:
- [ ] `workflow.started` with workflow_id, iteration_id
- [ ] `node.started` with node_id, agent_id
- [ ] `node.completed` with node_id, duration, artifacts
- [ ] `node.failed` with node_id, error, attempt
- [ ] `gate.passed` / `gate.failed` with gate_name, result
- [ ] `contract.locked` with contract_id, version
- [ ] Events include timestamp and correlation_id

**Verification Method**: Event capture test with assertions on event payload

---

### AC-DDE-010: Execution Metrics

**Given** completed workflow execution
**When** metrics are queried
**Then** metrics include:
- [ ] Total execution duration in seconds
- [ ] Per-node execution time
- [ ] Queue wait time (ready to running)
- [ ] Quality gate pass rate (passed/total)
- [ ] Retry count per node
- [ ] Parallel efficiency (actual parallel time / theoretical sequential time)

**Verification Method**: Metrics endpoint test

---

## 2. Quality Gate Service

### AC-QG-001: YAML Gate Definition

**Given** a YAML policy file with gate definitions
**When** the gate service loads configuration
**Then**:
- [ ] Gates parsed with: name, threshold, severity, rules, enabled
- [ ] Invalid YAML rejected with line/column error
- [ ] Missing required fields trigger validation error
- [ ] Gates can be updated without service restart (hot reload)

**Verification Method**: Configuration parsing tests

---

### AC-QG-002: Gate Attachment

**Given** a workflow manifest with node gate configurations
**When** gates are attached to nodes
**Then**:
- [ ] Gates match manifest specification
- [ ] Multiple gates can be attached to single node
- [ ] Gates execute in defined order
- [ ] Missing gate definition triggers error

**Verification Method**: Attachment resolution test

---

### AC-QG-003: Pre-Execution Validation

**Given** a node with pre-execution gates
**When** the node is about to start
**Then**:
- [ ] Dependencies are verified complete
- [ ] Required input artifacts exist
- [ ] Configuration is valid
- [ ] Failing pre-execution gate prevents node start
- [ ] Pre-execution gate results logged

**Verification Method**: Pre-check test with missing dependencies

---

### AC-QG-004: Post-Execution Validation

**Given** a node with post-execution gates
**When** the node completes execution
**Then**:
- [ ] Output artifacts validated
- [ ] Quality metrics evaluated (e.g., test coverage >= 80%)
- [ ] Gate results include: passed/failed, actual_value, expected_value
- [ ] All gates must pass for node to be marked COMPLETED

**Verification Method**: Gate evaluation test with various thresholds

---

### AC-QG-005: Blocking Gate Behavior

**Given** a gate with `severity: BLOCKING`
**When** the gate fails
**Then**:
- [ ] Node marked as FAILED
- [ ] Dependent nodes do not start
- [ ] Error message includes gate name and failure reason
- [ ] Workflow may continue on independent branches

**Verification Method**: Blocking gate failure test

---

### AC-QG-006: Warning Gate Behavior

**Given** a gate with `severity: WARNING`
**When** the gate fails
**Then**:
- [ ] Node marked as COMPLETED with warning
- [ ] Warning logged with details
- [ ] Dependent nodes start normally
- [ ] Warning visible in audit report

**Verification Method**: Warning gate test

---

### AC-QG-007: Bypass with ADR

**Given** a gate with bypass rules and ADR requirement
**When** bypass is requested
**Then**:
- [ ] ADR document path is required
- [ ] Bypass is logged with justification
- [ ] Bypass appears in audit trail
- [ ] Bypassed gates still report actual values

**Verification Method**: Bypass flow test

---

### AC-QG-008: Gate Results Reporting

**Given** completed gate evaluation
**When** results are reported
**Then** each result includes:
- [ ] `gate_name`
- [ ] `status` (passed/failed/warning/bypassed)
- [ ] `actual_value`
- [ ] `expected_value`
- [ ] `threshold_condition` (e.g., ">=")
- [ ] `severity`
- [ ] `timestamp`
- [ ] `duration_ms`

**Verification Method**: Result schema validation test

---

## 3. Artifact Stamping

### AC-AS-001: Stamping Convention

**Given** a completed node with artifacts
**When** artifacts are stamped
**Then**:
- [ ] Path format: `{IterationID}/{NodeID}/{ArtifactName}`
- [ ] Example: `Iter-20251122-1430-001/FE.Login/LoginComponent.tsx`
- [ ] Original artifact preserved
- [ ] Metadata labels: iteration_id, node_id, capability, contract_version, created_at, created_by

**Verification Method**: File path and metadata assertion

---

### AC-AS-002: Git Conventions

**Given** a developer committing for a node
**When** Git conventions are enforced
**Then**:
- [ ] Commit message starts with `[{NodeID}]`
- [ ] Branch name matches `feature/{IterationID}/{NodeID}`
- [ ] PR title matches `[{IterationID}/{NodeID}] {Summary}`
- [ ] Pre-commit hook validates format

**Verification Method**: Git hook tests

---

### AC-AS-003: Execution Log

**Given** workflow execution
**When** events occur
**Then** execution log (`/reports/{IterationID}/execution.log`):
- [ ] JSON lines format (one JSON object per line)
- [ ] Each event logged with: event_type, node_id, timestamp, details
- [ ] Log is append-only during execution
- [ ] Log is queryable for audit

**Verification Method**: Log parsing test

---

### AC-AS-004: Artifact Search

**Given** stamped artifacts across multiple iterations
**When** searching for artifacts
**Then**:
- [ ] Search by iteration_id returns all artifacts for that iteration
- [ ] Search by node_id returns artifacts from that node
- [ ] Search by capability returns artifacts from matching nodes
- [ ] Results include metadata and storage path

**Verification Method**: Search API tests

---

## 4. Contract Version Tracking

### AC-CV-001: Contract Lockdown

**Given** an interface node that completes successfully
**When** the contract is locked
**Then**:
- [ ] Contract status changes to LOCKED
- [ ] Contract version is frozen
- [ ] Modification attempts are rejected with error
- [ ] `contract.locked` event emitted
- [ ] Timestamp recorded for lockdown

**Verification Method**: Lockdown flow test

---

### AC-CV-002: Contract Publishing

**Given** a locked contract
**When** the contract is published
**Then**:
- [ ] Contract available at `/contracts/{domain}/{name}/{version}/`
- [ ] Specification file accessible (OpenAPI, GraphQL schema, etc.)
- [ ] URL injected into dependent node contexts
- [ ] Contract types supported: REST_API, GraphQL, gRPC, EventStream

**Verification Method**: Publishing and retrieval test

---

### AC-CV-003: Consumer Validation

**Given** a node with contract dependency
**When** the node completes
**Then**:
- [ ] Output validated against locked contract schema
- [ ] Schema violations reported as gate failure
- [ ] Contract version mismatch detected
- [ ] Validation result includes specific violations

**Verification Method**: Contract compliance test

---

### AC-CV-004: Breaking Change Detection

**Given** a contract evolution from v1 to v2
**When** breaking changes are introduced
**Then**:
- [ ] Breaking changes flagged automatically
- [ ] Affected consumers identified
- [ ] `breaking_changes` field set to true
- [ ] Consumer notification event emitted

**Verification Method**: Evolution test with breaking changes

---

### AC-CV-005: Contract History

**Given** a contract with multiple versions
**When** history is queried
**Then**:
- [ ] All versions listed chronologically
- [ ] Each version shows: version, timestamp, owner, status
- [ ] Supersedes relationships clear
- [ ] Diff between versions available

**Verification Method**: History API test

---

## 5. Traceability Audit

### AC-TA-001: Manifest vs As-Built Audit

**Given** a completed workflow iteration
**When** audit is executed
**Then** audit compares:
- [ ] All manifest nodes executed
- [ ] All quality gates passed (or bypassed with ADR)
- [ ] All expected artifacts stamped
- [ ] All contracts locked
- [ ] Execution order respected dependencies
- [ ] Audit score: completed_nodes / total_nodes

**Verification Method**: Audit execution test

---

### AC-TA-002: Deployment Gate

**Given** audit results
**When** deployment is requested
**Then**:
- [ ] If audit score = 100% and no blocking violations → deployment allowed
- [ ] If audit score < 100% or blocking violations → deployment blocked
- [ ] Blocking reason includes missing nodes, failed gates
- [ ] Override possible with explicit approval and logging

**Verification Method**: Deployment gate test

---

### AC-TA-003: Audit Report

**Given** completed audit
**When** report is generated
**Then** report includes:
- [ ] Summary: iteration_id, timestamp, result (PASS/FAIL), score
- [ ] Completeness: total/completed/missing/failed nodes
- [ ] Integrity: gates passed/failed, artifacts stamped/missing, contracts locked
- [ ] Violations: type, node_id, severity, message, details
- [ ] Recommendations: actionable items to resolve issues
- [ ] Report format: Markdown and JSON

**Verification Method**: Report generation test

---

## 6. System-Wide Acceptance Criteria

### AC-SYS-001: Performance

- [ ] Task routing latency < 500ms
- [ ] Capability matching < 200ms
- [ ] Support 100+ concurrent node executions
- [ ] Event emission < 50ms

**Verification Method**: Load test

---

### AC-SYS-002: Reliability

- [ ] Execution state survives service restart
- [ ] Individual node failure doesn't crash workflow
- [ ] Circuit breakers protect external dependencies
- [ ] 99.5% uptime for executor service

**Verification Method**: Chaos testing

---

### AC-SYS-003: Observability

- [ ] OpenTelemetry traces for all operations
- [ ] Prometheus metrics exported
- [ ] Structured JSON logging
- [ ] Correlation IDs across services

**Verification Method**: Observability stack test

---

### AC-SYS-004: Security

- [ ] API endpoints require authentication
- [ ] RBAC for workflow operations
- [ ] Audit logging for state changes
- [ ] No sensitive data in logs

**Verification Method**: Security review

---

## Definition of Done

For each story to be considered complete:

- [ ] Code implemented and reviewed
- [ ] Unit tests written with >80% coverage
- [ ] Integration tests pass
- [ ] Acceptance criteria verified
- [ ] Documentation updated
- [ ] No critical security issues
- [ ] Performance benchmarks met
- [ ] Code merged to main branch

---

## Test Plan Summary

| Test Type | Coverage | Automation |
|-----------|----------|------------|
| Unit Tests | All services | CI pipeline |
| Integration Tests | Service interactions | CI pipeline |
| E2E Tests | Full workflow | Nightly |
| Performance Tests | SLAs | Weekly |
| Security Tests | OWASP | Release |
| Chaos Tests | Reliability | Monthly |

---

**Document Status**: Draft
**Review Required**: QA Lead, Test Engineer
**Approval Required**: Product Owner
