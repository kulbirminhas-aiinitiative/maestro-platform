# Living Dependency Graph (LDG) Strategic Decision

**Date**: 2025-10-11
**Decision**: Defer LDG implementation, prioritize Quality Fabric integration
**Decision Makers**: Engineering team review
**Status**: Approved for Quality Fabric Phase 0

---

## Executive Summary

**Decision**: **Prioritize Quality Fabric integration now**; **defer Living Dependency Graph (LDG) until Phase 1-2 proves ROI**.

### Rationale

1. **Quality Fabric already exists** as production microservices - only needs integration layer
2. **Completes Batch 5 vision** - automated enforcement of contracts and validation
3. **Fast time to value** - 2 weeks per phase vs. 3+ months for LDG
4. **Low risk** - extends current system vs. major architectural change
5. **Unproven need** - LDG addresses hypothetical problems; Quality Fabric solves known gaps

### Approach

- **Phase 0 (Weeks 1-6)**: Quality Fabric integration with enhanced requirements
- **Phase 1 (Week 7)**: Gap analysis and evidence-based LDG justification
- **Phase 2 (Week 8)**: Postgres CTE impact analysis PoC with explicit kill/scale gates
- **Phase 3+ (Months 4-6)**: Only proceed with LDG if PoC proves ROI

---

## Decision Context

### Documents Reviewed

1. **DYNAMIC_NODES.md** - Original LDG vision
   - Proposes graph database (Neo4j/Neptune) for entire SDLC
   - Event streaming (Kafka) for real-time updates
   - Impact analysis and policy engine
   - Multi-layered ontology (Intent → Implementation → Deployment)

2. **DYNAMIC_NODES_REVIEW.md** - Critical engineering review
   - Addresses identity resolution, performance, governance concerns
   - Proposes concrete enhancements (schema versioning, CQRS, multi-tenancy)
   - Defines minimal PoC plan (2-3 weeks, single tenant)
   - Estimates significant infrastructure cost

3. **QUALITY_FABRIC_INTEGRATION_PLAN.md** - Existing integration plan
   - 8-week phased implementation
   - Uses existing Quality Fabric microservices
   - Persona validation and phase gate enforcement
   - Template quality tracking and ML feedback loop

4. **BATCH5_QA_ENHANCEMENT_COMPLETE_SUMMARY.md** - Current state
   - Weeks 1-6 complete (validation, contracts, pipeline integration)
   - Comprehensive test suite (81 tests, 100% pass rate)
   - Production-ready contract enforcement
   - Traceability system operational

### Current Architecture Status

✅ **Production Ready**:
- Validation system with build testing (50% weight on actual builds)
- Contract system with 7 requirement types (BUILD_SUCCESS, NO_STUBS, etc.)
- Phase gate validator with contract enforcement
- DAG executor with contract integration
- Code feature analyzer for traceability
- 81 comprehensive tests, all passing

❓ **Quality Fabric Exists But Not Integrated**:
- Microservices architecture operational (Port 8001)
- AI-powered quality gates with predictive analysis
- Multiple testing frameworks (Jest, Pytest, Selenium, Cypress, K6, Playwright)
- Gateway integration with MAESTRO API Gateway (Port 8080)
- Observability stack (Prometheus, Grafana, OpenTelemetry)

❌ **LDG Does Not Exist**:
- No graph database infrastructure
- No event streaming platform
- No adapters for external tools (Jira, GitHub, Figma)
- No impact analysis capability
- No policy engine (OPA)

---

## Decision Analysis

### Cost-Benefit Comparison

| Factor | Quality Fabric Integration | LDG Implementation |
|--------|---------------------------|-------------------|
| **Infrastructure** | Uses existing services | Requires Neo4j Enterprise, Kafka, OPA |
| **Development Time** | 6 weeks (phased) | 3-6 months (all-or-nothing) |
| **Cost** | Low ($100s/month) | High ($1000s/month) |
| **Risk** | Low (extends current system) | High (major architectural change) |
| **Reversibility** | Easy (disable integration) | Expensive (infrastructure committed) |
| **Time to Value** | 2 weeks (first phase) | 3+ months (minimal PoC) |
| **Learning Curve** | Low (Python/FastAPI) | High (Neo4j, Kafka, graph theory) |
| **Proven Need** | Yes (Batch 5 identified gaps) | No (hypothetical benefits) |
| **Integration Complexity** | Low (API calls) | High (event streaming, adapters) |
| **Operational Overhead** | Low (existing ops) | High (new systems to monitor) |

### Risk Assessment

**Quality Fabric Integration Risks** (LOW):
- ✅ API availability risk: Mitigated by fallback logic
- ✅ Performance risk: Async validation, non-blocking
- ✅ Adoption risk: Transparent to end users
- ✅ Rollback risk: Easy to disable integration

**LDG Implementation Risks** (HIGH):
- ❌ Infrastructure cost overrun: Neo4j Enterprise, Kafka clusters, storage
- ❌ Performance risk: Graph query latency, cardinality explosion
- ❌ Complexity risk: 8+ adapters, event ordering, idempotency
- ❌ Adoption risk: Complex UI, steep learning curve
- ❌ Abandonment risk: High sunk cost if value not realized

### Strategic Alignment

**Quality Fabric Alignment** ✅:
- Completes Batch 5 QA enhancement roadmap
- Builds on existing contract system
- Addresses known validation gaps (build testing, stub detection)
- Enables automated quality enforcement
- Creates feedback loop for continuous improvement

**LDG Alignment** ❓:
- Future-looking capability (impact analysis, blast radius)
- Not addressing immediate pain points
- No user stories or feature requests for it
- Unclear how it improves developer experience
- May solve problems we don't have yet

---

## Enhanced Requirements for Quality Fabric Integration

### Additional Engineering Requirements

Based on feedback, the following enhancements are required for Quality Fabric Phase 0:

#### 1. Per-Phase SLOs, Exit Criteria, and Success Metrics

**Requirement**: Define quantitative exit criteria for each SDLC phase.

**Implementation**:
- Define SLOs per phase (e.g., Implementation phase: build success rate ≥ 95%, test coverage ≥ 80%)
- Add exit criteria validation before phase transition
- Track metrics over time (phase duration, quality scores, violation counts)
- Surface metrics in phase gate logs and Quality Fabric dashboard

**Example SLO Configuration**:
```yaml
phase_slos:
  requirements:
    documentation_completeness: 0.90
    stakeholder_approval: required
    acceptance_criteria_defined: 100%

  design:
    architecture_review: required
    design_documentation: 0.85
    technology_decisions_documented: required

  implementation:
    build_success_rate: 0.95
    test_coverage: 0.80
    code_quality_score: 0.80
    stub_rate: 0.05

  testing:
    test_pass_rate: 0.95
    integration_test_coverage: 0.80
    security_scan: required
    performance_baseline: required

  deployment:
    deployment_readiness: 0.95
    rollback_plan: required
    monitoring_configured: required
    production_approval: required
```

#### 2. Wire Policies to master_contract.yaml (Contract-as-Code)

**Requirement**: All quality policies must be defined in version-controlled YAML, not hardcoded.

**Implementation**:
- Read policies from `contracts/master_contract.yaml` (already exists)
- Read SOW-specific policies from `contracts/sow/*.yaml`
- Quality Fabric validates against these declarative policies
- Policy changes tracked in git with approval workflow
- Policy versioning supports A/B testing and gradual rollout

**Example Policy Wire-Up**:
```python
# In quality_fabric_integration.py
from pathlib import Path
import yaml

def load_quality_policies(workflow_id: str) -> Dict[str, Any]:
    """Load policies from contract-as-code YAML files"""

    # Load master contract
    master_path = Path("contracts/master_contract.yaml")
    with open(master_path) as f:
        master_contract = yaml.safe_load(f)

    # Load SOW-specific contract if exists
    sow_path = Path(f"contracts/sow/{workflow_id}.yaml")
    if sow_path.exists():
        with open(sow_path) as f:
            sow_contract = yaml.safe_load(f)
        # Merge with master (SOW overrides master)
        policies = {**master_contract, **sow_contract}
    else:
        policies = master_contract

    return policies

# Use in validation
policies = load_quality_policies(workflow_id)
validator = QualityFabricValidator(policies=policies)
result = await validator.validate_phase_output(phase, output)
```

#### 3. Surface Violations in phase_gate_validator

**Requirement**: Contract violations must be visible in phase gate validator output, not buried in logs.

**Implementation**:
- Enhance `phase_gate_validator.py` to surface contract violations as blocking/warning issues
- Include violation details (requirement type, threshold, actual value, remediation)
- Add violation severity (BLOCKING, WARNING)
- Link violations to specific contract requirements
- Generate actionable error messages

**Example Enhancement**:
```python
# In phase_gate_validator.py (enhanced)

async def validate_phase_exit(
    phase: SDLCPhase,
    workflow_id: str,
    output_dir: Path
) -> PhaseValidationResult:
    """Validate phase exit with contract violation surfacing"""

    # Existing validation
    validation_result = await run_existing_validation(phase, workflow_id, output_dir)

    # NEW: Contract validation with Quality Fabric
    contract_result = await quality_fabric_client.validate_contracts(
        phase=phase,
        workflow_id=workflow_id,
        output_dir=output_dir
    )

    # Surface violations as structured issues
    blocking_violations = []
    warning_violations = []

    for violation in contract_result.violations:
        issue = PhaseGateIssue(
            type="CONTRACT_VIOLATION",
            requirement=violation.requirement_type,
            severity=violation.severity,
            message=violation.message,
            threshold=violation.threshold,
            actual_value=violation.actual_value,
            remediation=violation.remediation_steps,
            contract_ref=violation.contract_ref  # Link to master_contract.yaml
        )

        if violation.severity == "BLOCKING":
            blocking_violations.append(issue)
        else:
            warning_violations.append(issue)

    return PhaseValidationResult(
        phase=phase,
        passed=(len(blocking_violations) == 0),
        blocking_issues=blocking_violations,
        warning_issues=warning_violations,
        contract_violations=contract_result.violations,  # Detailed contract info
        can_proceed=(len(blocking_violations) == 0)
    )
```

#### 4. ADR-Backed Bypass with Audit Trail

**Requirement**: Phase gate bypasses must be justified with Architecture Decision Records (ADRs) and fully audited.

**Implementation**:
- Create ADR template for bypass justification
- Require ADR file creation before bypass approval
- Store ADRs in `docs/adr/NNNN-bypass-phase-gate-{phase}-{date}.md`
- Record bypass in audit log (who, when, why, which violations bypassed)
- Track bypass metrics (frequency, phase, persona, outcome)
- Alert on excessive bypasses (e.g., >10% of phase transitions)

**Example ADR Template**:
```markdown
# ADR-NNNN: Bypass Phase Gate for {Phase} in {Workflow ID}

**Date**: {ISO 8601 timestamp}
**Status**: Approved / Rejected
**Deciders**: {Names and roles}

## Context and Problem Statement

Phase gate for {phase} failed with {N} blocking violations:

1. {Violation 1}: {Description} (Threshold: {X}, Actual: {Y})
2. {Violation 2}: {Description} (Threshold: {X}, Actual: {Y})
...

We need to decide whether to bypass this gate to meet {deadline/milestone}.

## Decision Drivers

- Business pressure: {Description}
- Technical constraints: {Description}
- Risk assessment: {Low/Medium/High}
- Mitigation plan: {Description}

## Considered Options

1. Block deployment until violations resolved (recommended)
2. Bypass with mitigation plan (risky)
3. Partial bypass (resolve critical, defer warnings)

## Decision Outcome

Chosen option: {Option N}

Justification: {Detailed reasoning}

### Consequences

**Positive**:
- {Benefit 1}
- {Benefit 2}

**Negative**:
- {Risk 1}
- {Risk 2}

**Neutral**:
- {Observation 1}

### Mitigation Plan

1. {Mitigation step 1}
2. {Mitigation step 2}
...

### Acceptance Criteria for Closing Bypass

- [ ] {Criterion 1}
- [ ] {Criterion 2}
...

### Audit Information

- **Workflow ID**: {workflow_id}
- **Phase**: {phase}
- **Bypassed At**: {ISO 8601 timestamp}
- **Bypassed By**: {user_id} ({role})
- **Approved By**: {approver_id} ({role})
- **Violations Bypassed**: {count}
- **Expected Resolution Date**: {date}
- **Actual Resolution Date**: {date or TBD}

## Links

- Contract violations: [link to violation report]
- Related workflows: [links]
- Follow-up tasks: [links to Jira/GitHub issues]
```

**Audit Trail Implementation**:
```python
# In phase_gate_bypass.py (new file)

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import json

@dataclass
class BypassAuditRecord:
    """Audit record for phase gate bypass"""
    bypass_id: str
    workflow_id: str
    phase: str
    bypassed_at: datetime
    bypassed_by: str
    approved_by: str
    violations_count: int
    adr_path: str
    justification: str
    mitigation_plan: List[str]
    resolution_deadline: datetime
    resolved_at: Optional[datetime] = None

    def to_audit_log(self) -> dict:
        """Convert to audit log entry"""
        return {
            "event_type": "PHASE_GATE_BYPASS",
            "bypass_id": self.bypass_id,
            "workflow_id": self.workflow_id,
            "phase": self.phase,
            "timestamp": self.bypassed_at.isoformat(),
            "actor": self.bypassed_by,
            "approver": self.approved_by,
            "metadata": {
                "violations_bypassed": self.violations_count,
                "adr_reference": self.adr_path,
                "justification_summary": self.justification[:200],
                "resolution_deadline": self.resolution_deadline.isoformat(),
                "resolved": (self.resolved_at is not None)
            }
        }

class BypassManager:
    """Manages phase gate bypasses with ADR enforcement"""

    def __init__(self, audit_log_path: Path):
        self.audit_log_path = audit_log_path
        self.adr_dir = Path("docs/adr")
        self.adr_dir.mkdir(parents=True, exist_ok=True)

    async def request_bypass(
        self,
        workflow_id: str,
        phase: str,
        violations: List[ContractViolation],
        requested_by: str,
        justification: str
    ) -> BypassRequest:
        """Request a phase gate bypass - requires ADR"""

        # Generate ADR file
        adr_number = self._get_next_adr_number()
        adr_filename = f"{adr_number:04d}-bypass-{phase}-{workflow_id[:8]}.md"
        adr_path = self.adr_dir / adr_filename

        # Create ADR from template
        adr_content = self._generate_adr(
            adr_number=adr_number,
            workflow_id=workflow_id,
            phase=phase,
            violations=violations,
            requested_by=requested_by,
            justification=justification
        )

        adr_path.write_text(adr_content)

        # Create bypass request
        bypass_request = BypassRequest(
            workflow_id=workflow_id,
            phase=phase,
            violations=violations,
            requested_by=requested_by,
            adr_path=str(adr_path),
            status="PENDING_APPROVAL"
        )

        return bypass_request

    async def approve_bypass(
        self,
        bypass_request: BypassRequest,
        approved_by: str,
        mitigation_plan: List[str]
    ) -> BypassAuditRecord:
        """Approve bypass and create audit record"""

        # Validate ADR exists and is complete
        adr_path = Path(bypass_request.adr_path)
        if not adr_path.exists():
            raise ValueError(f"ADR not found: {adr_path}")

        # Create audit record
        audit_record = BypassAuditRecord(
            bypass_id=str(uuid.uuid4()),
            workflow_id=bypass_request.workflow_id,
            phase=bypass_request.phase,
            bypassed_at=datetime.utcnow(),
            bypassed_by=bypass_request.requested_by,
            approved_by=approved_by,
            violations_count=len(bypass_request.violations),
            adr_path=str(adr_path),
            justification=bypass_request.justification,
            mitigation_plan=mitigation_plan,
            resolution_deadline=datetime.utcnow() + timedelta(days=7)
        )

        # Write to audit log
        self._write_audit_log(audit_record)

        # Update ADR with approval
        self._update_adr_with_approval(adr_path, audit_record)

        return audit_record

    def _write_audit_log(self, record: BypassAuditRecord):
        """Append to audit log"""
        audit_entry = record.to_audit_log()

        with open(self.audit_log_path, 'a') as f:
            f.write(json.dumps(audit_entry) + '\n')
```

#### 5. Week 8 Postgres CTE Impact Analysis PoC

**Requirement**: Before committing to Neo4j/LDG, prove impact analysis can work with lightweight Postgres solution.

**Goal**: Build minimal impact analysis using PostgreSQL recursive CTEs to answer:
- "What code/tests/docs are affected if I change this requirement?"
- "What requirements are impacted if this code module changes?"

**Explicit Kill Gates**:
- ❌ If query latency p95 > 1 second → Kill PoC, consider Neo4j
- ❌ If cardinality > 100K nodes and query performance degrades → Kill PoC
- ❌ If users don't find it valuable in real work → Kill PoC, abandon LDG
- ❌ If implementation complexity exceeds 3 days → Kill PoC, too complex

**Explicit Scale Gates**:
- ✅ If query latency p95 < 500ms AND users find it valuable → Scale to Phase 3
- ✅ If handles 10K+ nodes with acceptable performance → Scale to production
- ✅ If 3+ developers use it regularly → Scale and iterate

**PoC Scope**:
- PostgreSQL database with tables: `artifacts`, `dependencies`
- Recursive CTE for forward/backward traceability
- Simple REST API (FastAPI) for queries
- Basic CLI for testing
- Ingest from GitHub only (no Kafka, no Jira yet)

**Success Criteria**:
- Can trace from requirement → code → tests in < 500ms
- Can identify blast radius for a change in < 1 second
- At least 3 developers find it useful for real work

**Schema**:
```sql
CREATE TABLE artifacts (
    id UUID PRIMARY KEY,
    artifact_type VARCHAR(50) NOT NULL,  -- 'requirement', 'code', 'test', etc.
    external_id VARCHAR(255),
    source_tool VARCHAR(50),
    name TEXT,
    path TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB
);

CREATE INDEX idx_artifacts_type ON artifacts(artifact_type);
CREATE INDEX idx_artifacts_external_id ON artifacts(external_id);

CREATE TABLE dependencies (
    id UUID PRIMARY KEY,
    from_artifact_id UUID REFERENCES artifacts(id),
    to_artifact_id UUID REFERENCES artifacts(id),
    relationship_type VARCHAR(50) NOT NULL,  -- 'implements', 'validates', 'depends_on'
    weight INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB
);

CREATE INDEX idx_dependencies_from ON dependencies(from_artifact_id);
CREATE INDEX idx_dependencies_to ON dependencies(to_artifact_id);
CREATE INDEX idx_dependencies_type ON dependencies(relationship_type);

-- Recursive CTE for impact analysis (forward traceability)
WITH RECURSIVE impact AS (
    -- Base case: start with the changed artifact
    SELECT
        id,
        artifact_type,
        name,
        path,
        0 AS depth,
        ARRAY[id] AS path_ids
    FROM artifacts
    WHERE id = :artifact_id

    UNION ALL

    -- Recursive case: find dependent artifacts
    SELECT
        a.id,
        a.artifact_type,
        a.name,
        a.path,
        i.depth + 1,
        i.path_ids || a.id
    FROM artifacts a
    JOIN dependencies d ON a.id = d.to_artifact_id
    JOIN impact i ON d.from_artifact_id = i.id
    WHERE
        i.depth < 10  -- Prevent infinite recursion
        AND NOT (a.id = ANY(i.path_ids))  -- Prevent cycles
)
SELECT * FROM impact;
```

**Implementation Plan** (Week 8):
- Day 1: Schema design, FastAPI setup
- Day 2: Ingest GitHub data (commits, PRs, issues)
- Day 3: Implement impact analysis queries with CTEs
- Day 4: Test with real Maestro workflows, measure performance
- Day 5: Gather user feedback, evaluate kill/scale gates

#### 6. Validate Quality Fabric API Stability and Data Availability

**Requirement**: Before building integration, confirm Quality Fabric APIs are stable and provide necessary data.

**Validation Steps**:
1. **API Health Check**:
   - Verify Quality Fabric service is running (http://localhost:8001/health)
   - Check all required endpoints exist
   - Test authentication/authorization if applicable
   - Measure response times (target: p95 < 200ms)

2. **Data Availability Check**:
   - Confirm Quality Fabric can analyze code artifacts
   - Verify test result aggregation works
   - Check AI insights generation is operational
   - Validate security scan integration

3. **Feedback Loop Validation**:
   - Confirm Quality Fabric can publish metrics to Prometheus
   - Verify Grafana dashboards exist and are populated
   - Check historical data retention (need 90+ days for ML training)
   - Validate event streaming for real-time updates

4. **Performance Testing**:
   - Load test with 100 concurrent persona validations
   - Measure throughput (target: 50+ validations/second)
   - Check memory usage under load (target: < 2GB per service)
   - Validate graceful degradation under high load

**Implementation**:
```python
# In quality_fabric_validator.py (new file)

import httpx
import asyncio
from typing import Dict, Any, List

class QualityFabricStabilityValidator:
    """Validates Quality Fabric API stability before integration"""

    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)

    async def validate_api_health(self) -> Dict[str, Any]:
        """Check if Quality Fabric APIs are healthy"""
        checks = {}

        # Health check
        try:
            response = await self.client.get(f"{self.base_url}/health")
            checks["health"] = (response.status_code == 200)
        except Exception as e:
            checks["health"] = False
            checks["health_error"] = str(e)

        # Required endpoints
        required_endpoints = [
            "/api/tests/run",
            "/api/ai-insights/analyze",
            "/api/analytics/quality-trends",
            "/api/utilities/coverage"
        ]

        for endpoint in required_endpoints:
            try:
                response = await self.client.get(f"{self.base_url}{endpoint}")
                checks[f"endpoint_{endpoint}"] = (response.status_code in [200, 404, 405])
                # 404/405 means endpoint exists but needs POST or auth
            except Exception as e:
                checks[f"endpoint_{endpoint}"] = False
                checks[f"endpoint_{endpoint}_error"] = str(e)

        return checks

    async def validate_data_availability(self) -> Dict[str, Any]:
        """Check if Quality Fabric can provide necessary data"""
        data_checks = {}

        # Test code analysis
        try:
            test_payload = {
                "code": "def hello(): return 'world'",
                "language": "python"
            }
            response = await self.client.post(
                f"{self.base_url}/api/analyze/code",
                json=test_payload
            )
            data_checks["code_analysis"] = (response.status_code == 200)
        except Exception as e:
            data_checks["code_analysis"] = False
            data_checks["code_analysis_error"] = str(e)

        # Test AI insights
        try:
            response = await self.client.get(f"{self.base_url}/api/ai-insights/recommendations")
            data_checks["ai_insights"] = (response.status_code in [200, 404])
        except Exception as e:
            data_checks["ai_insights"] = False

        return data_checks

    async def validate_performance(self) -> Dict[str, Any]:
        """Load test Quality Fabric APIs"""
        results = {
            "concurrent_requests": 100,
            "success_count": 0,
            "failure_count": 0,
            "latencies": []
        }

        async def single_request():
            start = asyncio.get_event_loop().time()
            try:
                response = await self.client.get(f"{self.base_url}/health")
                latency = asyncio.get_event_loop().time() - start
                results["latencies"].append(latency)
                if response.status_code == 200:
                    results["success_count"] += 1
                else:
                    results["failure_count"] += 1
            except Exception:
                results["failure_count"] += 1

        # Send 100 concurrent requests
        tasks = [single_request() for _ in range(100)]
        await asyncio.gather(*tasks)

        # Calculate statistics
        if results["latencies"]:
            results["latencies"].sort()
            results["p50_ms"] = results["latencies"][50] * 1000
            results["p95_ms"] = results["latencies"][95] * 1000
            results["p99_ms"] = results["latencies"][99] * 1000

        return results

    async def run_full_validation(self) -> Dict[str, Any]:
        """Run complete stability validation"""
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "base_url": self.base_url
        }

        report["api_health"] = await self.validate_api_health()
        report["data_availability"] = await self.validate_data_availability()
        report["performance"] = await self.validate_performance()

        # Overall assessment
        all_health_checks = all(
            v for k, v in report["api_health"].items()
            if isinstance(v, bool)
        )
        all_data_checks = all(
            v for k, v in report["data_availability"].items()
            if isinstance(v, bool)
        )
        perf_acceptable = (
            report["performance"].get("p95_ms", 999) < 500 and
            report["performance"].get("success_count", 0) > 90
        )

        report["overall_status"] = (
            "PASS" if (all_health_checks and all_data_checks and perf_acceptable)
            else "FAIL"
        )

        return report

# Usage
if __name__ == "__main__":
    async def main():
        validator = QualityFabricStabilityValidator()
        report = await validator.run_full_validation()
        print(json.dumps(report, indent=2))

    asyncio.run(main())
```

---

## Implementation Roadmap (Updated)

### Phase 0: Quality Fabric Integration (Weeks 1-6)

#### Week 1-2: Core Integration + Enhanced Requirements

**Tasks**:
1. ✅ Validate Quality Fabric API stability (new requirement)
   - Run stability validation script
   - Document API endpoints and data schemas
   - Test performance under load
   - Verify feedback loop data availability

2. ✅ Define per-phase SLOs and exit criteria (new requirement)
   - Create `config/phase_slos.yaml` with quantitative metrics
   - Document success metrics per phase
   - Add SLO tracking to phase gate validator

3. ✅ Wire policies to master_contract.yaml (new requirement)
   - Load policies from `contracts/master_contract.yaml`
   - Support SOW-specific overrides from `contracts/sow/*.yaml`
   - Version policies in git with approval workflow

4. Implement SDLC Quality Validator
   - Create `quality_fabric_integration/sdlc_quality_validator.py`
   - Define persona-specific quality gates
   - Integrate with Quality Fabric API

5. Integrate with team execution
   - Add Quality Fabric client to `team_execution.py`
   - Call validator after each persona execution
   - Handle validation failures with reflection pattern

**Deliverable**: Automated persona validation with enhanced policy enforcement

#### Week 3-4: Phase Gates + ADR-Backed Bypass

**Tasks**:
1. ✅ Enhance phase_gate_validator to surface violations (new requirement)
   - Surface contract violations as structured issues
   - Include violation details (requirement, threshold, actual, remediation)
   - Link violations to contract_ref in master_contract.yaml

2. ✅ Implement ADR-backed bypass mechanism (new requirement)
   - Create ADR template for bypass justification
   - Implement `phase_gate_bypass.py` with audit trail
   - Store ADRs in `docs/adr/` with version control
   - Track bypass metrics and alert on excessive usage

3. Create Phase Gate Quality Controller
   - Implement `quality_fabric_integration/phase_gate_quality_controller.py`
   - Add phase-specific quality gates with SLO validation
   - Block transitions on gate failures
   - Enable ADR-backed bypass for approved exceptions

4. Integrate with phase workflow
   - Add phase gate checks to phase execution
   - Validate SLO compliance before transitions
   - Track phase metrics (duration, quality scores, violations)

**Deliverable**: Phase transitions gated by quality with full audit trail

#### Week 5-6: Feedback Loop

**Tasks**:
1. Template quality tracking
   - Track which templates produce high-quality code
   - Update template scores based on quality results
   - Pin templates with consistent quality

2. ML model updates
   - Feed quality metrics to Maestro ML
   - Train quality prediction models
   - Improve quality gate accuracy

3. Quality analytics dashboard
   - Visualize quality trends
   - Show persona quality scores over time
   - Track gate pass/fail rates and bypass frequency

**Deliverable**: Self-improving quality system with data-driven template selection

---

### Phase 1: LDG Evidence Gathering (Week 7)

**Goal**: Prove LDG is needed before building it

**Tasks**:
1. Gap analysis
   - Interview 5+ developers: "What can't you do today?"
   - Document specific problems Quality Fabric doesn't solve
   - Identify use cases for impact analysis (how often, what decisions)

2. ROI calculation
   - Estimate infrastructure cost (Neo4j, Kafka, storage)
   - Estimate development time (3-6 months)
   - Estimate maintenance overhead (ops, monitoring, debugging)
   - Calculate time saved by impact analysis (hours/week/developer)
   - Compare: Does ROI justify investment?

3. Evidence-based decision document
   - Document pain points with user stories
   - Quantify opportunity cost of NOT having LDG
   - Recommend proceed/defer based on data

**Decision Point**:
- ✅ If ROI clearly positive + user demand high → Proceed to Phase 2
- ❌ If ROI unclear or user demand low → Abandon LDG, enhance Quality Fabric

---

### Phase 2: Postgres CTE Impact Analysis PoC (Week 8)

**Goal**: Prove impact analysis is valuable WITHOUT Neo4j/Kafka investment

**Tasks**:
1. Implement lightweight PoC
   - PostgreSQL schema (artifacts, dependencies)
   - Recursive CTEs for forward/backward traceability
   - FastAPI REST API
   - Simple CLI for testing

2. Ingest real data
   - GitHub commits, PRs, issues (no Kafka yet)
   - Link code → requirements manually (no ML yet)
   - Populate 1000+ artifacts for realistic testing

3. Test with real workflows
   - Run 10+ impact analysis queries
   - Measure query latency (target: p95 < 500ms)
   - Gather feedback from 3+ developers

4. Evaluate kill/scale gates

**Kill Gates** (any trigger → abandon LDG):
- ❌ Query latency p95 > 1 second
- ❌ Cardinality explosion degrades performance
- ❌ Developers don't find it useful
- ❌ Implementation > 3 days

**Scale Gates** (all trigger → proceed to Phase 3):
- ✅ Query latency p95 < 500ms
- ✅ Handles 10K+ artifacts with acceptable performance
- ✅ 3+ developers use it regularly and find it valuable

**Deliverable**: Evidence-based decision to proceed or abandon LDG

---

### Phase 3+: Production LDG (Months 4-6)

**ONLY proceed if**:
- Phase 1 proves clear ROI
- Phase 2 PoC demonstrates user value
- Budget approved for Neo4j Enterprise + Kafka
- Team has Neo4j/Kafka expertise

**Implementation**: Follow DYNAMIC_NODES_REVIEW.md recommendations with all enhancements

---

## Success Metrics

### Phase 0 Success Metrics (Quality Fabric)

**Week 1-2**:
- [ ] Quality Fabric API validation: PASS (all endpoints healthy, p95 < 200ms)
- [ ] Per-phase SLOs defined: 100% coverage (6 phases × 3-5 SLOs each)
- [ ] Policies wired to master_contract.yaml: 100% (no hardcoded policies)
- [ ] Persona validation coverage: 100% (11 personas)
- [ ] Validation latency: p95 < 5 seconds per persona
- [ ] Quality gate pass rate: ≥ 70% (baseline)

**Week 3-4**:
- [ ] Phase gate violations surfaced: 100% (all violations visible)
- [ ] ADR template created and tested
- [ ] Bypass audit trail implemented
- [ ] Phase transition blocking: 100% (no bypasses without ADR)
- [ ] Phase gate compliance: ≥ 80%
- [ ] Bypass rate: < 10% of phase transitions

**Week 5-6**:
- [ ] Template quality tracking operational
- [ ] ML feedback loop active (quality data flowing)
- [ ] Quality improvement YoY: +5% (baseline)
- [ ] Template selection accuracy: ±10% quality score

### Phase 1 Success Metrics (Gap Analysis)

- [ ] Developer interviews completed: ≥ 5
- [ ] Use cases documented: ≥ 3
- [ ] ROI calculation completed with data
- [ ] Decision document approved

### Phase 2 Success Metrics (Postgres PoC)

**Scale Gates** (all required to proceed):
- [ ] Query latency p95: < 500ms
- [ ] Artifact cardinality handled: 10K+
- [ ] Active users: ≥ 3 developers
- [ ] User satisfaction: ≥ 4/5 (useful in real work)

**Kill Gates** (any triggers abandon):
- [ ] Query latency p95: > 1 second → ❌ KILL
- [ ] Implementation time: > 3 days → ❌ KILL
- [ ] User satisfaction: < 3/5 → ❌ KILL

---

## Conclusion

**Approved Approach**:
1. **Prioritize Quality Fabric integration** (Weeks 1-6) with enhanced requirements
2. **Defer LDG** until evidence (Phase 1-2) proves ROI
3. **Use kill/scale gates** to make data-driven decision on LDG investment

**Enhanced Requirements**:
- ✅ Per-phase SLOs, exit criteria, and success metrics
- ✅ Wire policies to master_contract.yaml (contract-as-code)
- ✅ Surface violations in phase_gate_validator
- ✅ ADR-backed bypass with full audit trail
- ✅ Week 8 Postgres CTE PoC with explicit kill/scale gates
- ✅ Validate Quality Fabric API stability and feedback loop

**Expected Outcomes**:
- Quality Fabric delivers immediate value (2 weeks)
- LDG investment only made if PoC proves ROI
- Avoid expensive infrastructure commitment without evidence
- Data-driven decision making with clear metrics

---

**Status**: ✅ Approved for implementation
**Next Action**: Begin Phase 0 Week 1-2 implementation
**Review Date**: Week 2 end (evaluate progress), Week 8 end (LDG decision point)

---

**Appendix A: Related Documents**
- [DYNAMIC_NODES.md](./DYNAMIC_NODES.md) - Original LDG vision
- [DYNAMIC_NODES_REVIEW.md](./DYNAMIC_NODES_REVIEW.md) - Critical engineering review
- [QUALITY_FABRIC_INTEGRATION_PLAN.md](./QUALITY_FABRIC_INTEGRATION_PLAN.md) - Integration plan
- [BATCH5_QA_ENHANCEMENT_COMPLETE_SUMMARY.md](./BATCH5_QA_ENHANCEMENT_COMPLETE_SUMMARY.md) - Current state

**Appendix B: Contract Files**
- `contracts/master_contract.yaml` - Master quality policies (contract-as-code)
- `contracts/sow/*.yaml` - SOW-specific policy overrides
- `docs/adr/` - Architecture Decision Records for bypasses
