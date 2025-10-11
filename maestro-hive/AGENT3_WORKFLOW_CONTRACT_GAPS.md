# AGENT3: Workflow Contract Gaps Analysis

**Document:** Contract Lifecycle and Phase Boundary Validation
**Focus:** Contract forwarding, validation, and workflow continuity

---

## Executive Summary

The system implements **per-phase contracts** but fails to establish **workflow contracts** that span multiple phases. This creates isolated execution islands where each phase operates independently, breaking the continuous delivery pipeline.

**Key Finding:** Contracts are designed → executed → discarded at each phase boundary.

---

## Contract Types in System

### 1. Persona Contracts (✅ Working)
- **Definition:** Contract between a persona and their deliverables within a phase
- **Scope:** Single phase
- **Validation:** Contract fulfillment checked at persona execution level
- **Status:** ✅ WORKING

**Example:**
```python
# team_execution_v2.py:595-640
ContractSpecification(
    id="contract_abc123",
    name="Backend API Contract",
    version="v1.0",
    contract_type="REST_API",
    provider_persona_id="backend_developer",
    consumer_persona_ids=["frontend_developer", "qa_engineer"],  # ✅ Consumers identified
    deliverables=[...],
    acceptance_criteria=[...]
)
```

**Analysis:** Within a phase, contracts work correctly. Backend developer knows what to deliver.

---

### 2. Phase-to-Phase Contracts (❌ MISSING)
- **Definition:** Contract specifying what Phase N delivers to Phase N+1
- **Scope:** Inter-phase
- **Validation:** Should validate at phase boundaries
- **Status:** ❌ NOT IMPLEMENTED

**What's Missing:**
```python
# DOESN'T EXIST in codebase:
WorkflowContract(
    from_phase="design",
    to_phase="implementation",
    deliverables_required=[
        "api_specification.yaml",
        "database_schema.sql",
        "architecture_diagram.png"
    ],
    validation_criteria=[
        "OpenAPI spec is valid",
        "All endpoints documented",
        "DB schema has no circular dependencies"
    ]
)
```

---

## Contract Lifecycle Analysis

### Current Flow (Broken)

```
Phase 1: Requirements
  ┌─────────────────────────────────────┐
  │ 1. Contracts designed for phase     │
  │ 2. Personas execute contracts       │
  │ 3. Contracts validated              │
  │ 4. Phase ends                       │
  │ 5. ❌ Contracts DISCARDED            │
  └─────────────────────────────────────┘
                   │
                   ▼ (state saved but contracts not passed)
Phase 2: Design
  ┌─────────────────────────────────────┐
  │ 1. NEW contracts designed           │  ❌ No knowledge of Phase 1 contracts
  │ 2. Personas execute NEW contracts   │
  │ 3. NEW contracts validated          │
  │ 4. Phase ends                       │
  │ 5. ❌ Contracts DISCARDED            │
  └─────────────────────────────────────┘
                   │
                   ▼
Phase 3: Implementation
  ┌─────────────────────────────────────┐
  │ 1. NEW contracts designed           │  ❌ No knowledge of Phase 1 or 2
  │ 2. ❌ Frontend has no API contract   │  ❌ Backend API contract was discarded
  │ 3. ❌ Generic implementation         │
  └─────────────────────────────────────┘
```

---

### Required Flow (Missing)

```
Phase 1: Requirements
  ┌─────────────────────────────────────┐
  │ 1. Contracts designed for phase     │
  │ 2. Personas execute contracts       │
  │ 3. Contracts validated              │
  │ 4. Phase ends                       │
  │ 5. ✅ Contracts STORED in workflow   │
  │ 6. ✅ Contract DEPENDENCIES mapped   │
  └─────────────────────────────────────┘
                   │
                   ▼ ✅ Contracts passed forward
Phase 2: Design
  ┌─────────────────────────────────────┐
  │ 1. ✅ RECEIVES Phase 1 contracts     │
  │ 2. NEW contracts designed           │
  │ 3. ✅ Dependencies linked to Phase 1 │
  │ 4. Personas execute contracts       │
  │ 5. ✅ Both sets of contracts stored  │
  └─────────────────────────────────────┘
                   │
                   ▼ ✅ ALL contracts passed forward
Phase 3: Implementation
  ┌─────────────────────────────────────┐
  │ 1. ✅ RECEIVES all previous contracts│
  │ 2. ✅ Frontend gets Backend contract │
  │ 3. ✅ Implements against API spec    │
  │ 4. ✅ Integration validated          │
  └─────────────────────────────────────┘
```

---

## Code Analysis: Where Contracts Are Lost

### Location 1: Contract Design (team_execution_v2.py)

```python
# Lines 829-834
async def design_contracts(
    self,
    requirement: str,
    classification: RequirementClassification,
    blueprint: BlueprintRecommendation
) -> List[ContractSpecification]:
    """
    Design contracts for the team.

    Contract: Must return at least one contract per persona pair.
    """
    logger.info("📝 Designing contracts...")

    contracts = []

    # Create contracts based on coordination mode
    if "parallel" in blueprint.execution_mode and "contract" in blueprint.coordination_mode:
        contracts = await self._design_parallel_contracts(
            requirement,
            classification,
            blueprint.personas
        )
    else:
        contracts = await self._design_sequential_contracts(
            requirement,
            classification,
            blueprint.personas
        )

    # ❌ PROBLEM: No input parameter for previous_phase_contracts
    # ❌ PROBLEM: No linking of new contracts to old contracts
    # ❌ PROBLEM: Returns only NEW contracts for THIS phase

    return contracts
```

**Issue:** Each phase designs contracts in isolation. No dependency linking to previous contracts.

---

### Location 2: Contract Storage (team_execution_v2_split_mode.py)

```python
# Lines 828-834
# Step 3: AI designs contracts
logger.info("\n📝 Step 3: Contract Design")
contracts = await self.contract_designer.design_contracts(
    requirement,
    classification,
    blueprint_rec
)
# ✅ Contracts ARE stored in context.team_state.contract_specs
# ❌ But only for THIS phase, not accumulated across phases
```

**Issue:** Contracts stored but not accumulated. Each phase overwrites previous.

---

### Location 3: Contract Execution (team_execution_v2_split_mode.py:860-878)

```python
# Convert contract specifications to dict format
contracts_dict = [
    {
        "id": c.id,
        "name": c.name,
        "version": c.version,
        "contract_type": c.contract_type,
        "deliverables": c.deliverables,
        "dependencies": c.dependencies,  # ✅ HAS dependencies field
        "provider_persona_id": c.provider_persona_id,
        "consumer_persona_ids": c.consumer_persona_ids,  # ✅ HAS consumers field
        # ...
    }
    for c in contracts  # ❌ Only contracts for THIS phase
]

# Execute team
execution_result = await coordinator.execute_parallel(
    requirement=requirement,
    contracts=contracts_dict,  # ❌ Only current phase contracts
    context=constraints or {}
)
```

**Issue:** Only current phase contracts passed to coordinator. No contracts from previous phases.

---

### Location 4: Contract Dependencies (team_execution_v2.py:661)

```python
# Lines 661-670 (sequential contracts)
deliverables=[
    {
        "name": f"{persona_id}_deliverables",
        "description": f"Deliverables from {persona_id}",
        "artifacts": [],  # Will be determined at execution
        "acceptance_criteria": [...]
    }
],
dependencies=[contracts[i-1].id] if i > 0 else [],  # ✅ Dependencies within phase
```

**Analysis:**
- ✅ Dependencies tracked **within** a phase (persona to persona)
- ❌ Dependencies NOT tracked **across** phases (phase to phase)

---

## Phase Boundary Validation Issues

### Current Implementation: Phase Boundaries

```python
# team_execution_v2_split_mode.py:348-357
# Step 3: Validate phase boundary (if not first phase)
if phase_name != self.SDLC_PHASES[0]:
    previous_phase = self._get_previous_phase(phase_name)
    if previous_phase:
        logger.info(f"\n🔍 Validating phase boundary: {previous_phase} → {phase_name}")
        await self._validate_phase_boundary(
            phase_from=previous_phase,
            phase_to=phase_name,
            context=context
        )
```

**Analysis:** ✅ Phase boundary validation EXISTS

---

### Validation Implementation (Lines 839-899)

```python
async def _validate_phase_boundary(
    self,
    phase_from: str,
    phase_to: str,
    context: TeamExecutionContext
):
    """Validate phase boundary using ContractManager"""
    if not self.enable_contracts or not self.contract_manager:
        logger.info("   ⏭️  Skipping contract validation (disabled)")
        return  # ❌ Often skipped!

    # ... create contract message ...

    # Create contract message
    message = {
        "id": f"phase-transition-{boundary_id}",
        "ts": datetime.utcnow().isoformat(),
        "sender": f"phase-{phase_from}",
        "receiver": f"phase-{phase_to}",
        "performative": "inform",
        "content": prev_result.outputs,  # ✅ Passes outputs
        "metadata": {
            "quality_score": context.team_state.quality_metrics.get(phase_from, {}).get("overall_quality", 0.0),
            "artifacts": prev_result.artifacts_created
        }
    }

    # ❌ PROBLEM: Validation is FORMAT-based, not CONTENT-based
    # ❌ PROBLEM: Doesn't check if required artifacts exist
    # ❌ PROBLEM: Doesn't verify schemas/specs are valid
```

**Issues:**
1. Validation often disabled (contract_manager not available)
2. Validates message format, not deliverable content
3. Doesn't enforce required artifacts

---

## What's Missing: Workflow Contract Schema

### Required (Not Implemented)

```python
@dataclass
class WorkflowPhaseContract:
    """
    Contract specifying what must be delivered from one phase to another.

    This is DIFFERENT from persona contracts (which are within-phase).
    """
    id: str
    from_phase: str
    to_phase: str

    # Required deliverables
    required_artifacts: List[str]  # File paths that MUST exist
    required_outputs: Dict[str, Any]  # Data that MUST be in context

    # Validation
    validation_schema: Optional[Dict[str, Any]]  # JSON schema for outputs
    quality_gates: List[Dict[str, Any]]  # Quality thresholds

    # Dependencies
    depends_on_contracts: List[str]  # Previous workflow contracts

    # Metadata
    created_at: datetime
    validated: bool = False
    validation_result: Optional[Dict[str, Any]] = None


# Example usage (DOESN'T EXIST):
design_to_implementation_contract = WorkflowPhaseContract(
    id="design_to_impl_001",
    from_phase="design",
    to_phase="implementation",
    required_artifacts=[
        "architecture/api_specification.yaml",
        "architecture/database_schema.sql",
        "architecture/component_diagram.png"
    ],
    required_outputs={
        "api_endpoints": "list",
        "database_tables": "list",
        "authentication_method": "string"
    },
    validation_schema={
        "type": "object",
        "properties": {
            "api_endpoints": {"type": "array", "minItems": 1},
            "database_tables": {"type": "array", "minItems": 1}
        },
        "required": ["api_endpoints", "database_tables"]
    },
    quality_gates=[
        {"metric": "api_spec_valid", "threshold": 1.0},
        {"metric": "db_schema_normalized", "threshold": 1.0}
    ]
)
```

---

## Impact Analysis: Missing Contracts

### Example Scenario: E-Commerce Application

#### Phase 1: Requirements → Phase 2: Design

**Should Have Contract:**
```python
requirements_to_design_contract = {
    "required_artifacts": [
        "requirements/user_stories.md",
        "requirements/acceptance_criteria.md"
    ],
    "required_outputs": {
        "user_personas": ["buyer", "seller", "admin"],
        "core_features": ["product_catalog", "shopping_cart", "checkout"],
        "non_functional_requirements": ["<10s page load", "99.9% uptime"]
    }
}
```

**Current Reality:**
- ❌ No contract exists
- ❌ Design phase doesn't know what features are required
- ❌ Design phase might design wrong system

---

#### Phase 2: Design → Phase 3: Implementation

**Should Have Contract:**
```python
design_to_implementation_contract = {
    "required_artifacts": [
        "design/api_specification.yaml",  # OpenAPI spec
        "design/database_schema.sql",     # Complete DB schema
        "design/auth_flow.md",            # Authentication design
        "design/state_management.md"      # Frontend state design
    ],
    "required_outputs": {
        "api_base_url": "http://localhost:3000",
        "api_endpoints": [
            {"method": "GET", "path": "/api/products", "auth_required": false},
            {"method": "POST", "path": "/api/cart", "auth_required": true},
            {"method": "POST", "path": "/api/checkout", "auth_required": true}
        ],
        "database_tables": [
            "users", "products", "cart_items", "orders", "order_items"
        ],
        "auth_strategy": "JWT"
    },
    "validation_schema": {
        "api_specification": {"$ref": "openapi_3.0_schema"},
        "database_schema": {"$ref": "sql_ddl_schema"}
    }
}
```

**Current Reality:**
- ❌ No contract exists
- ❌ Frontend developer doesn't know API endpoints
- ❌ Backend developer doesn't know what frontend needs
- ✅ Result: Frontend builds generic placeholder

---

## Contract Consumer Problem

### Defined Consumers vs. Actual Access

**Backend API Contract (team_execution_v2.py:626):**
```python
ContractSpecification(
    id=contract_id,
    name="Backend API Contract",
    provider_persona_id="backend_developer",
    consumer_persona_ids=["frontend_developer", "qa_engineer"],  # ✅ Consumers identified
    # ...
)
```

**Problem:** Consumers identified but contract not delivered to them!

**What happens:**
1. Backend developer executes, creates API spec
2. Contract stored in `context.team_state.contract_specs`
3. Frontend developer executes **in next phase**
4. Frontend developer gets **new** contract (for frontend work)
5. Frontend developer **never receives** backend API contract
6. **Result:** Frontend doesn't know backend API exists

---

### Visualization: Contract Flow Breakdown

```
┌──────────────────────────────────────────────────────────────┐
│                  IMPLEMENTATION PHASE                         │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  Backend Developer                    Frontend Developer     │
│  ┌──────────────┐                    ┌──────────────┐       │
│  │  Contract:   │                    │  Contract:   │       │
│  │  Build API   │                    │  Build UI    │       │
│  └──────────────┘                    └──────────────┘       │
│         │                                    │               │
│         ▼                                    ▼               │
│  Creates API spec                     Builds UI             │
│  (stored in                          (needs API spec        │
│   contract)                           ❌ but doesn't have it)│
│         │                                    │               │
│         │                                    │               │
│         │  ❌ API Contract NOT passed to     │               │
│         │     Frontend Developer             │               │
│         │                                    │               │
│         └────────── Missing Link ────────────┘               │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

---

## Circuit Breaker Analysis

**File:** `team_execution_v2_split_mode.py:84-134`

```python
class PhaseCircuitBreaker:
    """
    Circuit breaker for phase boundary validation.

    Prevents cascading failures by opening circuit after too many failures.
    """
    # ...
```

**Analysis:**
- ✅ Circuit breaker implemented for phase boundaries
- ✅ Prevents infinite retry loops
- ❌ Doesn't fix root cause (missing contracts)
- ❌ May mask contract validation failures

**Issue:** If boundary validation keeps failing, circuit opens and **skips validation** entirely!

```python
# team_execution_v2_split_mode.py:852-855
if self.circuit_breaker.is_open(boundary_id):
    logger.error(f"   🔴 Circuit breaker OPEN for {boundary_id}")
    raise ValidationException(f"Circuit breaker open for {boundary_id}")
    # ❌ Execution stops, but root cause (missing artifacts) not fixed
```

---

## Recommended Contract Architecture

### Three-Tier Contract System

```
┌─────────────────────────────────────────────────────────┐
│ Tier 1: Persona Contracts (✅ Working)                   │
│ - Within a phase                                        │
│ - Persona to deliverables                              │
│ - Already implemented                                   │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ Tier 2: Workflow Phase Contracts (❌ Missing)            │
│ - Between phases                                        │
│ - Phase N to Phase N+1                                 │
│ - NEEDS TO BE IMPLEMENTED                              │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ Tier 3: Cross-Phase Persona Contracts (❌ Missing)       │
│ - Across phases                                         │
│ - Backend (Phase 2) to Frontend (Phase 3)              │
│ - NEEDS TO BE IMPLEMENTED                              │
└─────────────────────────────────────────────────────────┘
```

---

## Critical Gaps Summary

| Gap | Description | Impact | Status |
|-----|-------------|--------|--------|
| **1. Contract Forwarding** | Contracts not passed between phases | High | ❌ Missing |
| **2. Workflow Contracts** | No phase-to-phase contracts | High | ❌ Missing |
| **3. Consumer Access** | Consumers can't access provider contracts | High | ❌ Missing |
| **4. Contract Accumulation** | Each phase creates new contracts, old lost | High | ❌ Missing |
| **5. Boundary Validation** | Validation checks format, not content | Medium | ⚠️ Weak |
| **6. Dependency Linking** | Cross-phase dependencies not tracked | High | ❌ Missing |
| **7. Contract Schema** | No validation of contract content | Medium | ❌ Missing |

---

## Conclusion

**The Contract Problem in One Sentence:**
Contracts work perfectly **within** a phase but completely break **between** phases.

**Root Cause:**
The system treats each phase as an independent workflow instead of connected stages in a continuous delivery pipeline.

**Solution Required:**
Implement workflow-level contracts that span multiple phases and ensure deliverables flow from producers to consumers across phase boundaries.

---

**Next Document:** See `AGENT3_REMEDIATION_PLAN.md` for specific fixes to implement.
