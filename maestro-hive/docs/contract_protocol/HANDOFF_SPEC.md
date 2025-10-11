# HandoffSpec: Work Package Specification
## Phase-to-Phase Transfer Protocol

**Version:** 1.0.0
**Date:** 2025-10-11
**Status:** Phase 1 Complete

---

## Executive Summary

The **HandoffSpec** defines a first-class contract type for phase-to-phase transfers in multi-phase workflows. It eliminates ambiguity at phase boundaries by providing exact tasks, verified artifacts, and clear acceptance criteria for the next phase.

**Problem Solved**: Gap between "phase complete" and "next phase start"
- What exact tasks should the next phase perform?
- Which artifacts from the previous phase are inputs?
- What acceptance criteria must the next phase meet?

**Solution**: WORK_PACKAGE contract type with HandoffSpec

---

## Table of Contents

1. [Core Concepts](#core-concepts)
2. [Data Models](#data-models)
3. [HandoffSpec as Contract](#handoffspec-as-contract)
4. [Phase Boundary Flow](#phase-boundary-flow)
5. [Validation](#validation)
6. [Examples](#examples)
7. [Integration Guide](#integration-guide)
8. [Best Practices](#best-practices)

---

## Core Concepts

### The Handoff Problem

In traditional workflows:

```
Design Phase completes ✅
         ↓
        ???  ← What exactly should Implementation do?
         ↓
Implementation Phase starts 🤷
```

Problems:
- Implicit requirements
- Missing context
- Unclear priorities
- Lost artifacts

### The HandoffSpec Solution

```
Design Phase completes ✅
         ↓
Creates HandoffSpec:
  - 3 specific tasks with priorities
  - Design files (Figma, API specs)
  - Acceptance criteria (must match design)
         ↓
Validates HandoffSpec ✅
         ↓
Implementation Phase receives:
  - Exact task list
  - All input artifacts
  - Clear success criteria
         ↓
Implementation executes with confidence 🎯
```

---

## Data Models

### HandoffSpec

```python
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime

# Import canonical types
from contract_protocol.types import AcceptanceCriterion, VerificationResult

@dataclass
class HandoffSpec:
    """
    Work package specification for phase-to-phase transfer.
    This is a FIRST-CLASS contract deliverable.
    """

    # ===== Identity =====
    handoff_id: str  # Unique identifier (e.g., "handoff_design_impl_001")
    from_phase: str  # Source phase (e.g., "design")
    to_phase: str    # Destination phase (e.g., "implementation")

    # ===== Work Definition =====
    tasks: List['Task']  # Exact tasks for next phase
    acceptance_criteria: List[AcceptanceCriterion]  # What must be met

    # ===== Artifacts and Context =====
    input_artifacts: 'ArtifactManifest'  # Artifacts from previous phase
    context: Dict[str, Any]              # Additional context (tech stack, deadlines, etc.)

    # ===== Dependencies and Constraints =====
    dependencies: List[str] = field(default_factory=list)  # Other handoffs required
    constraints: Dict[str, Any] = field(default_factory=dict)  # Time, resource constraints

    # ===== Metadata =====
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = "system"  # Phase or agent that created this
    version: str = "1.0.0"

    # ===== Validation =====
    validated: bool = False
    validation_result: Optional[VerificationResult] = None
    validation_errors: List[str] = field(default_factory=list)

    def validate(self) -> bool:
        """Validate handoff completeness"""
        errors = []

        # Check required fields
        if not self.tasks:
            errors.append("No tasks defined for handoff")

        if not self.input_artifacts or not self.input_artifacts.artifacts:
            errors.append("No input artifacts provided")

        if not self.acceptance_criteria:
            errors.append("No acceptance criteria defined")

        # Validate tasks
        for task in self.tasks:
            if not task.description:
                errors.append(f"Task {task.task_id} missing description")
            if not task.assignee:
                errors.append(f"Task {task.task_id} missing assignee")

        self.validation_errors = errors
        self.validated = len(errors) == 0

        return self.validated
```

### Task

```python
@dataclass
class Task:
    """Individual task within handoff work package"""

    # ===== Identity =====
    task_id: str  # Unique identifier (e.g., "impl_001")

    # ===== Definition =====
    description: str  # Clear, actionable description
    assignee: str     # Persona or agent responsible (e.g., "frontend_developer")

    # ===== Planning =====
    estimated_duration_minutes: int  # Time estimate
    priority: int = 5  # 1 (highest) to 10 (lowest)

    # ===== References =====
    related_artifacts: List[str] = field(default_factory=list)  # Artifact IDs needed
    related_contracts: List[str] = field(default_factory=list)  # Contract IDs this fulfills

    # ===== Status Tracking =====
    status: str = "pending"  # "pending", "in_progress", "completed"
    completed_at: Optional[datetime] = None
    completion_notes: str = ""

    # ===== Metadata =====
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
```

### ArtifactManifest Reference

For artifact definitions, see `ARTIFACT_STANDARD.md`. Quick reference:

```python
@dataclass
class ArtifactManifest:
    """Manifest of artifacts being handed off"""
    manifest_id: str
    artifacts: List[Artifact]  # See ARTIFACT_STANDARD.md
    created_at: datetime = field(default_factory=datetime.utcnow)
```

---

## HandoffSpec as Contract

HandoffSpec is represented as a **WORK_PACKAGE contract** in the Universal Contract Protocol.

### Contract Type

```python
from enum import Enum

class ContractType(Enum):
    UX_DESIGN = "ux_design"
    API_SPECIFICATION = "api_specification"
    SECURITY_POLICY = "security_policy"
    # ... other types ...
    WORK_PACKAGE = "work_package"  # ← Handoff contract type
```

### Creating a Handoff Contract

```python
from contract_protocol.types import UniversalContract, AcceptanceCriterion

def create_handoff_contract(
    handoff_spec: HandoffSpec,
    blocking: bool = True
) -> UniversalContract:
    """Create a WORK_PACKAGE contract from HandoffSpec"""

    return UniversalContract(
        contract_id=f"contract_{handoff_spec.handoff_id}",
        contract_type=ContractType.WORK_PACKAGE,

        # Description
        name=f"Handoff: {handoff_spec.from_phase} → {handoff_spec.to_phase}",
        description=f"Work package transfer from {handoff_spec.from_phase} to {handoff_spec.to_phase}",

        # Parties
        provider_agent=handoff_spec.from_phase,
        consumer_agents=[handoff_spec.to_phase],

        # Dependencies
        depends_on=[f"contract_{handoff_spec.from_phase}_complete"],

        # Specification
        specification={
            "handoff_spec": handoff_spec,
            "handoff_id": handoff_spec.handoff_id,
            "task_count": len(handoff_spec.tasks),
            "artifact_count": len(handoff_spec.input_artifacts.artifacts) if handoff_spec.input_artifacts else 0
        },

        # Acceptance Criteria
        acceptance_criteria=[
            AcceptanceCriterion(
                criterion_id="handoff_completeness",
                description="Handoff spec includes all required elements",
                validator_type="handoff_validator",
                validation_config={
                    "handoff_id": handoff_spec.handoff_id,
                    "require_tasks": True,
                    "require_artifacts": True,
                    "require_criteria": True
                },
                required=True,
                blocking=True
            ),
            AcceptanceCriterion(
                criterion_id="artifact_integrity",
                description="All artifacts have valid digests and are accessible",
                validator_type="artifact_verifier",
                validation_config={
                    "verify_digests": True,
                    "verify_accessibility": True
                },
                required=True,
                blocking=True
            ),
            AcceptanceCriterion(
                criterion_id="task_clarity",
                description="All tasks have clear descriptions and assignees",
                validator_type="task_validator",
                validation_config={
                    "require_description": True,
                    "require_assignee": True,
                    "require_estimates": True
                },
                required=True,
                blocking=False  # Non-blocking: warnings only
            )
        ],

        # Enforcement
        is_blocking=blocking,
        priority="CRITICAL",

        # Metadata
        metadata={
            "phase_boundary": f"{handoff_spec.from_phase}/{handoff_spec.to_phase}",
            "handoff_version": handoff_spec.version
        }
    )
```

---

## Phase Boundary Flow

### Complete Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│ Phase 1 (Design) Execution                                       │
│ - UX Designer creates mockups                                    │
│ - Solution Architect creates API specs                           │
│ - Design contracts verified ✅                                   │
└─────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│ Phase 1 Complete - Generate HandoffSpec                          │
│                                                                   │
│ handoff_spec = HandoffSpec(                                      │
│     handoff_id="handoff_design_impl_001",                        │
│     from_phase="design",                                         │
│     to_phase="implementation",                                   │
│     tasks=[                                                      │
│         Task("impl_001", "Implement LoginForm", "frontend_dev"), │
│         Task("impl_002", "Implement Auth API", "backend_dev")    │
│     ],                                                           │
│     input_artifacts=ArtifactManifest(...),                       │
│     acceptance_criteria=[...]                                    │
│ )                                                                │
└─────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│ Validate HandoffSpec                                              │
│ - All tasks have descriptions ✅                                  │
│ - All artifacts have valid digests ✅                             │
│ - Acceptance criteria defined ✅                                  │
└─────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│ Register WORK_PACKAGE Contract                                   │
│ contract = create_handoff_contract(handoff_spec)                 │
│ registry.register_contract(contract)                             │
│ registry.update_contract_state(contract.id, VERIFIED)            │
└─────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│ Phase 2 (Implementation) Receives Handoff                        │
│                                                                   │
│ Implementation phase receives:                                   │
│ 1. Exact task list (2 tasks with priorities)                    │
│ 2. All input artifacts (Figma files, API specs)                 │
│ 3. Clear acceptance criteria                                    │
│ 4. Full context (tech stack, deadlines)                         │
│                                                                   │
│ No ambiguity! 🎯                                                 │
└─────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│ Phase 2 Execution with Strong Assurance                          │
│ - Frontend dev implements LoginForm from exact specs             │
│ - Backend dev implements Auth API from exact specs               │
│ - Both know exactly what success looks like                      │
└─────────────────────────────────────────────────────────────────┘
```

### Integration Point

```python
# In team_execution_v2_split_mode.py

async def execute_phase(
    self,
    phase_name: str,
    checkpoint: Optional[TeamExecutionContext] = None,
    **kwargs
) -> TeamExecutionContext:
    """Execute phase with handoff support"""

    # ... execute phase ...

    # After phase completes, create handoff for next phase
    if phase_name in ["requirements", "design", "implementation"]:
        next_phase = self._get_next_phase(phase_name)

        # Generate handoff
        handoff_spec = self._generate_handoff_spec(
            from_phase=phase_name,
            to_phase=next_phase,
            phase_results=execution_result,
            context=checkpoint
        )

        # Validate handoff
        if not handoff_spec.validate():
            logger.warning(f"Handoff validation failed: {handoff_spec.validation_errors}")

        # Create and register contract
        handoff_contract = create_handoff_contract(handoff_spec, blocking=True)
        checkpoint.contract_registry.register_contract(handoff_contract)

        # Verify contract
        verification = checkpoint.contract_registry.verify_contract_fulfillment(
            handoff_contract.contract_id,
            artifacts={"handoff_spec": handoff_spec}
        )

        if verification.passed:
            logger.info(f"Handoff {handoff_spec.handoff_id} verified ✅")
        else:
            logger.error(f"Handoff {handoff_spec.handoff_id} verification failed!")

    return checkpoint
```

---

## Validation

### HandoffValidator

```python
from contract_protocol.validators import ContractValidator, CriterionResult, ValidatorMetadata

class HandoffValidator(ContractValidator):
    """Validates handoff spec completeness"""

    @property
    def metadata(self) -> ValidatorMetadata:
        return ValidatorMetadata(
            name="handoff_validator",
            version="1.0.0",
            dependencies=[],
            runtime_requirements=[],
            timeout_seconds=30,
            requires_network=False,
            requires_sandboxing=False
        )

    async def validate_impl(
        self,
        criterion: AcceptanceCriterion,
        context: Dict[str, Any]
    ) -> CriterionResult:
        """Validate handoff spec"""

        handoff_spec = context.get("artifacts", {}).get("handoff_spec")
        if not handoff_spec:
            return CriterionResult(
                criterion_id=criterion.criterion_id,
                passed=False,
                actual_value="missing",
                expected_value="present",
                message="No handoff_spec provided"
            )

        # Validate completeness
        config = criterion.validation_config
        errors = []

        # Check tasks
        if config.get("require_tasks", True):
            if not handoff_spec.tasks:
                errors.append("No tasks defined")
            else:
                for task in handoff_spec.tasks:
                    if not task.description:
                        errors.append(f"Task {task.task_id} missing description")
                    if not task.assignee:
                        errors.append(f"Task {task.task_id} missing assignee")

        # Check artifacts
        if config.get("require_artifacts", True):
            if not handoff_spec.input_artifacts or not handoff_spec.input_artifacts.artifacts:
                errors.append("No input artifacts provided")

        # Check acceptance criteria
        if config.get("require_criteria", True):
            if not handoff_spec.acceptance_criteria:
                errors.append("No acceptance criteria defined")

        passed = len(errors) == 0

        return CriterionResult(
            criterion_id=criterion.criterion_id,
            passed=passed,
            actual_value="valid" if passed else "invalid",
            expected_value="valid",
            message=f"Handoff validation: {len(errors)} errors" if errors else "Handoff is complete",
            evidence={
                "errors": errors,
                "task_count": len(handoff_spec.tasks),
                "artifact_count": len(handoff_spec.input_artifacts.artifacts) if handoff_spec.input_artifacts else 0
            }
        )
```

---

## Examples

### Example 1: Design → Implementation Handoff

```python
# After design phase completes

handoff_spec = HandoffSpec(
    handoff_id="handoff_design_impl_001",
    from_phase="design",
    to_phase="implementation",

    tasks=[
        Task(
            task_id="impl_001",
            description="Implement LoginForm component according to UX design",
            assignee="frontend_developer",
            estimated_duration_minutes=120,
            priority=1,
            related_artifacts=["artifact_figma_login", "artifact_design_tokens"],
            related_contracts=["UX_LOGIN_001"]
        ),
        Task(
            task_id="impl_002",
            description="Implement authentication API endpoint /api/v1/auth/login",
            assignee="backend_developer",
            estimated_duration_minutes=180,
            priority=1,
            related_artifacts=["artifact_api_spec"],
            related_contracts=["API_AUTH_001"]
        ),
        Task(
            task_id="impl_003",
            description="Integrate frontend LoginForm with backend API",
            assignee="frontend_developer",
            estimated_duration_minutes=90,
            priority=2,
            related_artifacts=["artifact_api_spec", "artifact_integration_guide"],
            related_contracts=["API_AUTH_001", "UX_LOGIN_001"]
        )
    ],

    input_artifacts=ArtifactManifest(
        manifest_id="manifest_design_phase",
        artifacts=[
            # See ARTIFACT_STANDARD.md for Artifact definition
            # artifact_figma_login, artifact_design_tokens, artifact_api_spec
        ]
    ),

    acceptance_criteria=[
        AcceptanceCriterion(
            criterion_id="implementation_matches_design",
            description="Implementation must match UX design specifications",
            validator_type="screenshot_diff",
            validation_config={"threshold": 0.95}
        ),
        AcceptanceCriterion(
            criterion_id="api_matches_spec",
            description="API must conform to OpenAPI specification",
            validator_type="openapi_validator",
            validation_config={"spec_file": "api_spec.yaml"}
        )
    ],

    context={
        "project_name": "Authentication System",
        "sprint": "Sprint 3",
        "target_completion": "2025-10-18",
        "tech_stack": {
            "frontend": "React 18 + TypeScript + Material-UI 5",
            "backend": "Python 3.11 + FastAPI",
            "database": "PostgreSQL 15"
        },
        "environment_urls": {
            "dev": "https://dev.example.com",
            "staging": "https://staging.example.com"
        }
    },

    constraints={
        "max_implementation_time_hours": 24,
        "must_pass_contracts": ["UX_LOGIN_001", "API_AUTH_001"],
        "code_review_required": True
    }
)

# Validate
if handoff_spec.validate():
    print("✅ Handoff spec is valid")
    # Create contract and register
    contract = create_handoff_contract(handoff_spec)
    registry.register_contract(contract)
else:
    print(f"❌ Handoff validation failed: {handoff_spec.validation_errors}")
```

### Example 2: Implementation → Testing Handoff

```python
handoff_spec = HandoffSpec(
    handoff_id="handoff_impl_test_001",
    from_phase="implementation",
    to_phase="testing",

    tasks=[
        Task(
            task_id="test_001",
            description="Create integration tests for authentication flow",
            assignee="qa_engineer",
            estimated_duration_minutes=180,
            priority=1,
            related_contracts=["API_AUTH_001", "UX_LOGIN_001"]
        ),
        Task(
            task_id="test_002",
            description="Perform accessibility audit on LoginForm",
            assignee="qa_engineer",
            estimated_duration_minutes=60,
            priority=1,
            related_contracts=["UX_LOGIN_001"]
        ),
        Task(
            task_id="test_003",
            description="Load test authentication API (1000 concurrent users)",
            assignee="qa_engineer",
            estimated_duration_minutes=120,
            priority=2,
            related_contracts=["API_AUTH_001"]
        )
    ],

    input_artifacts=ArtifactManifest(
        manifest_id="manifest_implementation_phase",
        artifacts=[
            # Code artifacts, built binaries, deployment configs
        ]
    ),

    acceptance_criteria=[
        AcceptanceCriterion(
            criterion_id="test_coverage",
            description="Test coverage must be ≥ 80%",
            validator_type="coverage_validator",
            validation_config={"min_coverage": 80}
        ),
        AcceptanceCriterion(
            criterion_id="all_tests_pass",
            description="All integration tests must pass",
            validator_type="test_runner",
            validation_config={"test_suite": "integration"}
        )
    ],

    context={
        "implementation_complete_date": "2025-10-15",
        "test_environment": "staging",
        "test_data": "use_staging_data"
    }
)
```

---

## Integration Guide

### Step 1: Generate HandoffSpec After Phase

```python
def _generate_handoff_spec(
    self,
    from_phase: str,
    to_phase: str,
    phase_results: Dict[str, Any],
    context: TeamExecutionContext
) -> HandoffSpec:
    """Generate handoff spec from phase results"""

    # Extract tasks from phase output
    tasks = self._extract_tasks_from_phase(phase_results, to_phase)

    # Collect artifacts from phase
    artifacts = self._collect_phase_artifacts(from_phase, context)

    # Define acceptance criteria for next phase
    acceptance_criteria = self._get_acceptance_criteria_for_phase(to_phase)

    return HandoffSpec(
        handoff_id=f"handoff_{from_phase}_{to_phase}_{int(time.time())}",
        from_phase=from_phase,
        to_phase=to_phase,
        tasks=tasks,
        input_artifacts=artifacts,
        acceptance_criteria=acceptance_criteria,
        context=self._build_handoff_context(phase_results, context)
    )
```

### Step 2: Validate and Register

```python
# Validate
if not handoff_spec.validate():
    logger.error(f"Handoff validation failed: {handoff_spec.validation_errors}")
    # Decide: fail fast or continue with warnings

# Create contract
handoff_contract = create_handoff_contract(handoff_spec, blocking=True)

# Register
registry.register_contract(handoff_contract)

# Verify
verification = registry.verify_contract_fulfillment(
    handoff_contract.contract_id,
    artifacts={"handoff_spec": handoff_spec}
)
```

### Step 3: Next Phase Retrieves Handoff

```python
def _get_handoff_for_phase(
    self,
    phase_name: str,
    context: TeamExecutionContext
) -> Optional[HandoffSpec]:
    """Retrieve handoff spec for this phase"""

    # Find WORK_PACKAGE contract for this phase
    contracts = context.contract_registry.get_contracts_by_type("WORK_PACKAGE")

    for contract in contracts:
        if contract.specification.get("to_phase") == phase_name:
            return contract.specification.get("handoff_spec")

    return None
```

---

## Best Practices

### 1. Task Granularity

✅ **Good**: Specific, actionable tasks
```python
Task("impl_001", "Implement LoginForm component with email/password fields", ...)
```

❌ **Bad**: Vague tasks
```python
Task("impl_001", "Do frontend work", ...)
```

### 2. Complete Artifact References

✅ **Good**: All artifacts referenced with digests
```python
input_artifacts=ArtifactManifest(artifacts=[
    Artifact(digest="acf3d19b...", path="artifacts/ac/f3/..."),
    Artifact(digest="1234567...", path="artifacts/12/34/...")
])
```

❌ **Bad**: Arbitrary file paths
```python
input_artifacts={"files": ["/tmp/design.png"]}
```

### 3. Clear Acceptance Criteria

✅ **Good**: Specific, measurable criteria
```python
AcceptanceCriterion(
    description="Visual appearance must match Figma design within 95% similarity",
    validator_type="screenshot_diff",
    validation_config={"threshold": 0.95}
)
```

❌ **Bad**: Vague criteria
```python
AcceptanceCriterion(
    description="Should look good",
    validator_type="human_review"
)
```

### 4. Realistic Estimates

✅ **Good**: Informed estimates
```python
Task(..., estimated_duration_minutes=120)  # 2 hours based on complexity
```

❌ **Bad**: Arbitrary estimates
```python
Task(..., estimated_duration_minutes=30)  # Unrealistic for complex task
```

### 5. Context Completeness

✅ **Good**: All relevant context
```python
context={
    "tech_stack": {...},
    "environment_urls": {...},
    "design_decisions": {...},
    "constraints": {...}
}
```

❌ **Bad**: Missing context
```python
context={}
```

---

## Summary

The HandoffSpec:

- ✅ Eliminates ambiguity at phase boundaries
- ✅ Provides exact task lists with priorities
- ✅ References all input artifacts with verification
- ✅ Defines clear acceptance criteria
- ✅ Captures full context for next phase
- ✅ Integrates as first-class WORK_PACKAGE contract
- ✅ Enables complete traceability
- ✅ Supports validation and verification

**Next Steps**:
1. Implement HandoffValidator
2. Integrate handoff generation into phase execution
3. Update personas to consume handoff specs
4. Add handoff visualization in UI

**Related Documents**:
- `ARTIFACT_STANDARD.md` - Artifact and manifest definitions
- `CONTRACT_TYPES_REFERENCE.md` - WORK_PACKAGE contract type details
- `UNIVERSAL_CONTRACT_PROTOCOL.md` - Phase boundaries section
- `IMPLEMENTATION_GUIDE.md` - Integration guidance

---

**Document Version:** 1.0.0
**Last Updated:** 2025-10-11
**Status:** Ready for implementation
