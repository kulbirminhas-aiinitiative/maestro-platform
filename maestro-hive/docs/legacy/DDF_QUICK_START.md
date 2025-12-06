# DDF Tri-Modal Framework - Quick Start Guide

**Version**: 0.1.0 (Phase 1A Foundation)
**Date**: 2025-10-13

---

## What is the Tri-Modal Framework?

The DDF (Dependency-Driven Framework) Tri-Modal system validates software quality across **three independent dimensions**:

1. **DDE (Dependency-Driven Execution)** - "Built Right"
   - Validates execution process and compliance
   - Interface-first execution
   - Capability-based routing
   - Quality gate enforcement

2. **BDV (Behavior-Driven Validation)** - "Built the Right Thing"
   - Validates user behavior and acceptance criteria
   - Gherkin feature files
   - Contract-aligned scenarios
   - Business intent validation

3. **ACC (Architectural Conformance Checking)** - "Built to Last"
   - Validates structural integrity
   - Layering rules
   - Dependency constraints
   - Coupling metrics

**Deployment Rule**: Deploy ONLY when **DDE ✅ AND BDV ✅ AND ACC ✅**

---

## Quick Demo (2 minutes)

Run the demonstration to see all failure patterns:

```bash
cd /home/ec2-user/projects/maestro-platform/maestro-hive
python3 tri_audit/demo_tri_modal.py
```

This demonstrates:
- ✅ ALL_PASS: Safe to deploy
- ⚠️ DESIGN_GAP: Wrong thing built
- ⚠️ ARCHITECTURAL_EROSION: Technical debt
- ⚠️ PROCESS_ISSUE: Pipeline problems
- ❌ SYSTEMIC_FAILURE: Everything broken

---

## Using Each Stream

### 1. DDE: Execution Manifest

Create an execution manifest for your iteration:

```yaml
# manifests/execution/my_feature.yaml
iteration_id: Iter-20251013-1000-001
timestamp: "2025-10-13T10:00:00Z"
project: MyProject

nodes:
  # Interface nodes execute FIRST
  - id: IF.MyAPI
    type: interface
    capability: Architecture:APIDesign
    outputs: [openapi.yaml]
    gates: [openapi-lint, semver-check]
    estimated_effort: 60
    contract_version: v1.0

  # Implementation nodes depend on interfaces
  - id: BE.MyService
    type: impl
    capability: Backend:Python:FastAPI
    depends_on: [IF.MyAPI]
    gates: [unit-tests, coverage, lint]
    estimated_effort: 120
```

**Stamp an artifact:**

```python
from dde.artifact_stamper import ArtifactStamper

stamper = ArtifactStamper()
metadata = stamper.stamp_artifact(
    iteration_id="Iter-20251013-1000-001",
    node_id="IF.MyAPI",
    artifact_path="openapi.yaml",
    capability="Architecture:APIDesign",
    contract_version="v1.0"
)
print(f"Stamped: {metadata.stamped_path}")
```

**Match capabilities:**

```python
from dde.capability_matcher import CapabilityMatcher, AgentProfile
from datetime import datetime

matcher = CapabilityMatcher()

# Register agent
matcher.register_agent(AgentProfile(
    agent_id="agent-001",
    name="Backend Specialist",
    availability_status="available",
    wip_limit=3,
    current_wip=1,
    recent_quality_score=0.92,
    last_active=datetime.now(),
    capabilities={
        "Backend:Python:FastAPI": 5,
        "Data:SQL:PostgreSQL": 4
    }
))

# Match
matches = matcher.match(
    required_skills=["Backend:Python:FastAPI"],
    min_proficiency=3
)
print(f"Best match: {matches[0]}")
```

---

### 2. BDV: Feature Files

Create Gherkin feature files:

```gherkin
# features/my_feature/my_api.feature

@contract:MyAPI:v1.0
Feature: My API Functionality
  As a user
  I want to use the API
  So that I can accomplish my goals

  Scenario: Happy path
    Given the API is running
    When I send a valid request
    Then I receive a successful response
```

**Run BDV tests:**

```python
from bdv.bdv_runner import BDVRunner

runner = BDVRunner(base_url="http://localhost:8000")

# Discover feature files
features = runner.discover_features()
print(f"Found {len(features)} feature files")

# Run tests
result = runner.run(iteration_id="Iter-20251013-1000-001")
print(f"Results: {result.passed}/{result.total_scenarios} passed")
```

---

### 3. ACC: Architectural Manifest

Define your architecture:

```yaml
# manifests/architectural/my_project.yaml

project: MyProject
version: "1.0.0"

components:
  - name: Presentation
    paths: [frontend/src/]

  - name: BusinessLogic
    paths: [backend/src/services/]

  - name: DataAccess
    paths: [backend/src/repositories/]

rules:
  - id: R1
    type: dependency
    description: "Presentation can only call BusinessLogic"
    rule: "Presentation: CAN_CALL(BusinessLogic)"
    severity: BLOCKING

  - id: R2
    type: dependency
    description: "Presentation must not call DataAccess"
    rule: "Presentation: MUST_NOT_CALL(DataAccess)"
    severity: BLOCKING
```

**Build import graph:**

```python
from acc.import_graph_builder import ImportGraphBuilder

builder = ImportGraphBuilder(project_path=".")
graph = builder.build_graph()

print(f"Modules: {len(graph.modules)}")
print(f"Dependencies: {len(graph.graph.edges())}")

# Check for cycles
if graph.has_cycle():
    cycles = graph.find_cycles()
    print(f"Found {len(cycles)} cycles")

# Calculate coupling
for module in list(graph.modules.keys())[:5]:
    ca, ce, instability = graph.calculate_coupling(module)
    print(f"{module}: Ca={ca}, Ce={ce}, I={instability:.2f}")
```

---

## Running Tri-Modal Audit

Combine all three streams:

```python
from tri_audit.tri_audit import (
    tri_modal_audit,
    can_deploy_to_production
)

# Run comprehensive audit
result = tri_modal_audit("Iter-20251013-1000-001")

print(f"Verdict: {result.verdict.value}")
print(f"Can Deploy: {result.can_deploy}")
print(f"\nDiagnosis:\n{result.diagnosis}")
print(f"\nRecommendations:")
for rec in result.recommendations:
    print(f"  - {rec}")

# Deployment gate check
if can_deploy_to_production("Iter-20251013-1000-001"):
    print("✅ APPROVED: Deploy to production")
else:
    print("❌ BLOCKED: Cannot deploy")
```

---

## File Locations

### Schemas
- `schemas/execution_manifest.schema.json` - DDE manifest
- `schemas/architectural_manifest.schema.json` - ACC manifest

### Configurations
- `config/capability_taxonomy.yaml` - Skill hierarchy

### Manifests
- `manifests/execution/` - DDE execution manifests
- `manifests/architectural/` - ACC architectural manifests
- `features/` - BDV feature files

### Reports
- `reports/dde/{iteration_id}/` - DDE audit reports
- `reports/bdv/{iteration_id}/` - BDV test results
- `reports/acc/{iteration_id}/` - ACC conformance reports
- `reports/tri-modal/{iteration_id}/` - Tri-audit results

### Artifacts
- `artifacts/{iteration_id}/{node_id}/` - Stamped artifacts

---

## Understanding Verdicts

### ✅ ALL_PASS
- **Meaning**: Safe to deploy
- **Action**: Deploy to production
- **Pattern**: DDE ✅ AND BDV ✅ AND ACC ✅

### ⚠️ DESIGN_GAP
- **Meaning**: Built the wrong thing
- **Action**: Revisit requirements
- **Pattern**: DDE ✅ AND BDV ❌ AND ACC ✅
- **Blind Spot**: User needs not met

### ⚠️ ARCHITECTURAL_EROSION
- **Meaning**: Technical debt accumulating
- **Action**: Refactor before deploy
- **Pattern**: DDE ✅ AND BDV ✅ AND ACC ❌
- **Blind Spot**: Structure compromised

### ⚠️ PROCESS_ISSUE
- **Meaning**: Pipeline problems
- **Action**: Fix gates/pipeline
- **Pattern**: DDE ❌ AND BDV ✅ AND ACC ✅
- **Blind Spot**: Execution compliance

### ❌ SYSTEMIC_FAILURE
- **Meaning**: Everything broken
- **Action**: HALT and retrospect
- **Pattern**: DDE ❌ AND BDV ❌ AND ACC ❌
- **Blind Spot**: All dimensions failing

---

## Integration with CI/CD

### Pre-Commit Hook
```bash
# Run ACC checks
python acc_check.py --manifest manifests/architectural/my_project.yaml
```

### Pull Request Gate
```bash
# Run all three audits
python -c "
from tri_audit.tri_audit import can_deploy_to_production
if not can_deploy_to_production('$ITERATION_ID'):
    exit(1)
"
```

### Deployment Gate
```bash
# Final check before production deploy
if python -c "from tri_audit.tri_audit import can_deploy_to_production; exit(0 if can_deploy_to_production('$ITERATION_ID') else 1)"; then
    echo "✅ Approved for deployment"
    # Deploy to production
else
    echo "❌ Blocked by tri-modal audit"
    exit 1
fi
```

---

## Next Steps

1. **Extend DDE** (Phase 1B-1D):
   - Database for agent profiles
   - Task router with JIT assignment
   - Gate classification and execution
   - Prometheus metrics

2. **Extend BDV** (Phase 2B-2D):
   - Contract validator
   - OpenAPI → Gherkin generator
   - Flake management
   - Expand to 20 user journeys

3. **Extend ACC** (Phase 3B-3D):
   - Full rule engine (10+ types)
   - Suppression system with ADRs
   - Coupling analyzer
   - Evolution tracking

4. **Deploy Pilot** (Week 8):
   - Run on real project
   - Collect metrics
   - Validate improvements
   - Iterate based on feedback

---

## Getting Help

- **Documentation**: See `DDF_TRI_MODAL_IMPLEMENTATION_PLAN.md`
- **Summary**: See `DDF_TRI_MODAL_IMPLEMENTATION_SUMMARY.md`
- **Demo**: Run `python3 tri_audit/demo_tri_modal.py`
- **Issues**: Check implementation for TODOs and stubs

---

## Key Takeaways

1. **Three Independent Streams**: DDE, BDV, ACC validate different dimensions
2. **Non-Overlapping Blind Spots**: Each catches unique failure modes
3. **Convergence at Deployment**: All three must pass to deploy
4. **Clear Diagnostics**: Each failure pattern has specific guidance
5. **Incremental Value**: Each stream provides value independently

**Remember**: Deploy ONLY when **DDE ✅ AND BDV ✅ AND ACC ✅**

---

**Quick Start Version**: 1.0
**Last Updated**: 2025-10-13
**Status**: Phase 1A Foundation Complete ✅
