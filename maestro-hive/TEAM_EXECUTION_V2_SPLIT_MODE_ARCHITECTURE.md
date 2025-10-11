# Team Execution V2: Split Mode Architecture

**Version**: 1.0
**Date**: 2025-10-09
**Status**: Design Specification

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current Architecture Analysis](#current-architecture-analysis)
3. [Split Mode Requirements](#split-mode-requirements)
4. [Architectural Design](#architectural-design)
5. [State Management](#state-management)
6. [Contract Validation](#contract-validation)
7. [Execution Modes](#execution-modes)
8. [Implementation Design](#implementation-design)
9. [Scenario Matrix](#scenario-matrix)
10. [Migration Path](#migration-path)

---

## Executive Summary

### Vision

Enable **team_execution_v2** to execute SDLC workflows in multiple modes:
- **Split Mode**: Each phase runs independently (potentially different processes)
- **Batch Mode**: All phases run continuously (current behavior)
- **Mixed Mode**: Some phases independent, some continuous
- **Parallel-Hybrid**: Parallel execution within sequential phases

### Core Innovations

1. **Stateless Execution Engine**: All state externalized to checkpoint files
2. **Phase-Level Blueprints**: Different team patterns per SDLC phase
3. **Contract-Validated Boundaries**: Phase transitions are contract messages
4. **Resumable Workflows**: Any phase can resume from checkpoint
5. **Human-in-the-Loop**: Natural checkpoints for review and edits

### Key Benefits

| Benefit | Impact |
|---------|--------|
| **Flexibility** | Run phases when resources available |
| **Human Control** | Review and edit between phases |
| **Fault Tolerance** | Resume from failures without restarting |
| **Resource Optimization** | Different team sizes per phase |
| **Quality Assurance** | Contract validation prevents bad handoffs |
| **Audit Trail** | Complete lineage of decisions and artifacts |

---

## Current Architecture Analysis

### team_execution_v2.py - Current State

```
TeamExecutionEngineV2.execute(requirement)
    ↓
1. AI analyzes requirement → RequirementClassification
2. AI selects blueprint → BlueprintRecommendation
3. AI designs contracts → List[ContractSpecification]
4. Creates session → SDLCSession
5. Executes team → ParallelCoordinatorV2.execute_parallel()
    ↓
6. Returns execution result (in-memory only)
```

**Architecture**:
- Monolithic execution (all-or-nothing)
- In-memory state (no persistence)
- Single blueprint for entire workflow
- No checkpoint support
- No phase-level granularity

**Strengths**:
- ✅ AI-driven team composition
- ✅ Blueprint-based patterns
- ✅ Contract-first parallel execution
- ✅ Quality metrics and validation

**Gaps for Split Mode**:
- ❌ No state serialization
- ❌ No phase-level execution
- ❌ No checkpoint/resume capability
- ❌ No cross-process coordination
- ❌ No phase-specific blueprint selection
- ❌ No SDLC workflow integration

### SDLC Workflow System - Existing Capabilities

**Files**:
- `examples/sdlc_workflow_context.py` - WorkflowContext, PhaseResult
- `examples/sdlc_workflow_simulation.py` - SDLCWorkflowSimulator

**Capabilities**:
- ✅ Phase-by-phase execution
- ✅ Checkpoint save/load
- ✅ Context passing between phases
- ✅ Contract validation at boundaries
- ✅ Human edits between phases
- ✅ Three execution modes (single-go, phased, mixed)

**Gaps**:
- ❌ No integration with team_execution_v2
- ❌ Simulates work instead of real execution
- ❌ No AI-driven team composition
- ❌ No blueprint selection
- ❌ No parallel execution within phases

### Integration Opportunity

**The Vision**: Merge the best of both systems!

```
SDLC Workflow Orchestration (phase management)
    +
Team Execution V2 (AI-driven team composition)
    =
Split Mode Execution (phase-level AI teams with persistence)
```

---

## Split Mode Requirements

### Functional Requirements

#### FR-1: Independent Phase Execution
- Each SDLC phase SHALL execute independently
- Phase execution SHALL not require previous phases to be in-memory
- Each phase SHALL load context from checkpoint
- Each phase SHALL save state to checkpoint

#### FR-2: Batch Mode Compatibility
- System SHALL support continuous execution of all phases
- Batch mode SHALL produce identical results to split mode
- Batch mode SHALL optionally create checkpoints
- No performance degradation in batch mode

#### FR-3: Context Persistence
- Complete workflow state SHALL serialize to JSON
- Checkpoint SHALL be < 10MB for typical workflows
- Checkpoint save/load SHALL be < 1 second
- No state loss between phases

#### FR-4: Contract Validation
- Phase boundaries SHALL be validated as contracts
- ContractManager SHALL validate using 4 pillars
- Validation failures SHALL be captured with details
- Human edits SHALL trigger re-validation

#### FR-5: Blueprint Selection
- System SHALL support static blueprint (all phases)
- System SHALL support dynamic blueprint (per phase)
- Blueprint selection SHALL be AI-driven or manual
- Blueprint metadata SHALL persist in checkpoint

#### FR-6: Human-in-the-Loop
- System SHALL pause for human review at checkpoints
- Humans SHALL edit phase outputs before next phase
- Edits SHALL be tracked in workflow context
- Re-execution SHALL use edited context

### Non-Functional Requirements

#### NFR-1: Performance
- Phase execution overhead < 5% vs current implementation
- Checkpoint I/O SHALL not block execution
- Parallel execution SHALL maintain 25-50% time savings

#### NFR-2: Reliability
- Zero data loss in checkpoint save/load
- Graceful handling of corrupted checkpoints
- Automatic validation of checkpoint integrity

#### NFR-3: Usability
- API SHALL be simple: `execute_phase()`, `resume_from_checkpoint()`
- Clear error messages for validation failures
- Progress visibility through logging
- Backward compatibility with team_execution_v2

#### NFR-4: Maintainability
- Clean separation: orchestration vs execution
- Well-documented checkpoint format
- Easy to extend with new execution modes
- Test coverage > 80%

---

## Architectural Design

### System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   TeamExecutionEngineV2SplitMode                │
│                    (Orchestration Layer)                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  execute_phase(phase_name, checkpoint=None)                     │
│      ↓                                                           │
│  1. Load checkpoint (if provided)                               │
│  2. Get context from previous phase                             │
│  3. Validate phase boundary (contract)                          │
│  4. Select blueprint for this phase                             │
│  5. Design contracts for phase personas                         │
│  6. Execute personas (TeamExecutionEngineV2)                    │
│  7. Collect outputs and metrics                                 │
│  8. Create checkpoint for next phase                            │
│                                                                  │
│  execute_batch(requirement)                                     │
│      ↓                                                           │
│  for phase in SDLC_PHASES:                                      │
│      execute_phase(phase)                                       │
│                                                                  │
│  resume_from_checkpoint(checkpoint_path, edits=None)            │
│      ↓                                                           │
│  1. Load checkpoint                                             │
│  2. Apply human edits                                           │
│  3. Re-validate contracts                                       │
│  4. Continue from next phase                                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ uses
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                  TeamExecutionContext                            │
│                  (State Management)                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  WorkflowContext (from sdlc_workflow_context.py)                │
│  + phase_results: Dict[str, PhaseResult]                        │
│  + shared_artifacts: List[Dict]                                 │
│  + contracts_validated: List[Dict]                              │
│                                                                  │
│  TeamExecutionState (NEW)                                       │
│  + classification: RequirementClassification                    │
│  + blueprint_selections: Dict[str, BlueprintRecommendation]     │
│  + contract_specs: List[ContractSpecification]                  │
│  + persona_results: Dict[str, Dict[str, PersonaExecutionResult]]│
│  + quality_metrics: Dict[str, Any]                              │
│                                                                  │
│  Methods:                                                        │
│  + to_checkpoint() → Dict                                       │
│  + from_checkpoint(data) → TeamExecutionContext                 │
│  + add_phase_execution(phase, results)                          │
│  + get_phase_context(phase) → Dict                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ validates with
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    ContractManager                               │
│                  (Validation Layer)                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  process_incoming_message(message, sender_id)                   │
│                                                                  │
│  Four Pillars:                                                  │
│  1. Clarity - Schema validation of phase outputs                │
│  2. Incentives - Quality score > threshold                      │
│  3. Trust - Artifact signatures (optional)                      │
│  4. Adaptability - Circuit breaker on failures                  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ uses
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│               TeamExecutionEngineV2                              │
│               (Existing Implementation)                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  execute(requirement, constraints) → Result                     │
│                                                                  │
│  Used by split mode for each phase execution                    │
│  No modifications needed to existing code                        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

#### TeamExecutionEngineV2SplitMode (NEW)
**Purpose**: Orchestrate phase-by-phase execution with checkpoints

**Responsibilities**:
- Load/save checkpoints
- Phase boundary validation
- Blueprint selection per phase
- Human edit application
- Progress tracking

**Key Methods**:
```python
async def execute_phase(
    phase_name: str,
    checkpoint: Optional[TeamExecutionContext] = None
) -> TeamExecutionContext

async def execute_batch(
    requirement: str,
    create_checkpoints: bool = False
) -> TeamExecutionContext

async def resume_from_checkpoint(
    checkpoint_path: str,
    human_edits: Optional[Dict] = None
) -> TeamExecutionContext
```

#### TeamExecutionContext (NEW)
**Purpose**: Unified state model combining workflow and team execution

**Responsibilities**:
- Serialize/deserialize complete state
- Track phase results and team execution
- Manage blueprint selections per phase
- Validate checkpoint integrity

**Key Data**:
```python
@dataclass
class TeamExecutionContext:
    # Workflow state (from SDLC system)
    workflow: WorkflowContext

    # Team execution state (from team_execution_v2)
    classification: RequirementClassification
    blueprint_selections: Dict[str, BlueprintRecommendation]
    contract_specs: List[ContractSpecification]
    persona_results: Dict[str, Dict[str, PersonaExecutionResult]]

    # Quality and metrics
    quality_metrics: Dict[str, Any]
    timing_metrics: Dict[str, Any]
```

#### Phase Boundary Validator (NEW)
**Purpose**: Validate phase transitions as contracts

**Responsibilities**:
- Convert phase output to contract message
- Validate using ContractManager
- Track validation results
- Circuit breaker on failures

**Validation Flow**:
```
Phase N completes with outputs
    ↓
Convert to contract message:
{
  "sender": "phase-requirements",
  "receiver": "phase-design",
  "performative": "inform",
  "content": {
    "requirements_doc": "...",
    "user_stories": [...],
    ...
  }
}
    ↓
ContractManager.process_incoming_message()
    ↓
Validation result (passed/failed)
    ↓
If passed: proceed to next phase
If failed: pause for human intervention
```

---

## State Management

### Checkpoint Format

**File**: `checkpoint_{workflow_id}_{phase_name}.json`

```json
{
  "checkpoint_metadata": {
    "version": "1.0",
    "created_at": "2025-10-09T12:34:56Z",
    "workflow_id": "workflow-20251009-123456",
    "phase_completed": "requirements",
    "awaiting_phase": "design",
    "checkpoint_type": "phase_boundary"
  },

  "workflow_context": {
    "workflow_id": "workflow-20251009-123456",
    "workflow_type": "sdlc",
    "execution_mode": "phased",

    "phase_results": {
      "requirements": {
        "phase_name": "requirements",
        "status": "completed",
        "outputs": {
          "requirements_doc": "...",
          "user_stories": [...],
          "acceptance_criteria": [...]
        },
        "context_received": {},
        "context_passed": {
          "requirements_output": {...},
          "phase_completed": "requirements"
        },
        "contracts_validated": ["boundary-start-requirements"],
        "artifacts_created": ["requirements.md", "user_stories.md"],
        "duration_seconds": 45.2,
        "started_at": "2025-10-09T12:30:00Z",
        "completed_at": "2025-10-09T12:30:45Z"
      }
    },

    "phase_order": ["requirements"],
    "current_phase": "requirements",
    "shared_artifacts": [
      {
        "name": "requirements.md",
        "created_by_phase": "requirements",
        "created_at": "2025-10-09T12:30:45Z"
      }
    ],
    "shared_context": {},
    "contracts_validated": [
      {
        "phase": "requirements",
        "contract_id": "boundary-start-requirements",
        "timestamp": "2025-10-09T12:30:00Z",
        "result": {"passed": true, "intent": "inform"}
      }
    ],

    "metadata": {
      "project_name": "ML Pipeline API",
      "initial_requirement": "Build a REST API for ML model training..."
    },

    "started_at": "2025-10-09T12:30:00Z",
    "completed_at": null,
    "human_edits": {},
    "awaiting_human_review": true
  },

  "team_execution_state": {
    "classification": {
      "requirement_type": "feature_development",
      "complexity": "complex",
      "parallelizability": "fully_parallel",
      "required_expertise": ["backend", "frontend", "api", "ml"],
      "estimated_effort_hours": 40.0,
      "dependencies": [],
      "risks": ["Model training complexity", "API design"],
      "rationale": "Full-stack ML application with parallel backend/frontend",
      "confidence_score": 0.92
    },

    "blueprint_selections": {
      "requirements": {
        "blueprint_id": "sequential-basic",
        "blueprint_name": "Sequential Analysis Team",
        "match_score": 0.85,
        "personas": ["requirement_analyst"],
        "execution_mode": "sequential",
        "coordination_mode": "handoff",
        "scaling_strategy": "static",
        "estimated_time_savings": 0.0
      }
    },

    "contract_specs": [
      {
        "id": "contract_abc123",
        "name": "Requirements Analysis Contract",
        "version": "v1.0",
        "contract_type": "Deliverable",
        "deliverables": [
          {
            "name": "requirements_doc",
            "description": "Complete requirements specification",
            "artifacts": ["requirements.md"],
            "acceptance_criteria": [
              "All functional requirements documented",
              "User stories with acceptance criteria",
              "Non-functional requirements specified"
            ]
          }
        ],
        "dependencies": [],
        "provider_persona_id": "requirement_analyst",
        "consumer_persona_ids": ["solution_architect"],
        "acceptance_criteria": ["Quality score > 80%"],
        "estimated_effort_hours": 8.0
      }
    ],

    "persona_results": {
      "requirements": {
        "requirement_analyst": {
          "persona_id": "requirement_analyst",
          "contract_id": "contract_abc123",
          "success": true,
          "files_created": ["requirements.md", "user_stories.md"],
          "deliverables": {
            "requirements_doc": ["requirements.md"],
            "user_stories": ["user_stories.md"]
          },
          "contract_fulfilled": true,
          "fulfillment_score": 0.95,
          "missing_deliverables": [],
          "quality_score": 0.88,
          "completeness_score": 0.92,
          "duration_seconds": 42.5
        }
      }
    },

    "quality_metrics": {
      "requirements": {
        "overall_quality": 0.88,
        "contract_fulfillment": 1.0,
        "artifact_count": 2,
        "completeness": 0.92
      }
    },

    "timing_metrics": {
      "requirements": {
        "phase_duration": 45.2,
        "ai_analysis_time": 12.3,
        "blueprint_selection_time": 5.1,
        "contract_design_time": 8.2,
        "persona_execution_time": 42.5
      }
    }
  }
}
```

### Checkpoint Lifecycle

```
Phase N Execution
    ↓
Phase N completes successfully
    ↓
Create checkpoint:
1. Serialize WorkflowContext
2. Serialize TeamExecutionState
3. Add metadata (timestamp, phase info)
4. Validate checkpoint (schema check)
5. Write to file: checkpoint_{workflow_id}_{phase_name}.json
    ↓
Checkpoint saved ✓
    ↓
[PROCESS CAN DIE HERE - State is safe on disk]
    ↓
New process starts / Resume requested
    ↓
Load checkpoint:
1. Read JSON file
2. Validate schema
3. Deserialize WorkflowContext
4. Deserialize TeamExecutionState
5. Restore in-memory state
    ↓
Apply human edits (optional):
1. Update phase outputs
2. Re-validate contracts
3. Track edits in human_edits
    ↓
Execute Phase N+1
    ↓
Repeat...
```

### State Validation

**On Save**:
```python
def validate_checkpoint(checkpoint: Dict) -> bool:
    """Validate checkpoint before saving"""
    checks = [
        checkpoint.get("checkpoint_metadata", {}).get("version") == "1.0",
        "workflow_context" in checkpoint,
        "team_execution_state" in checkpoint,
        checkpoint["workflow_context"].get("workflow_id") is not None,
        len(checkpoint["workflow_context"].get("phase_results", {})) > 0,
    ]
    return all(checks)
```

**On Load**:
```python
def load_checkpoint(path: str) -> TeamExecutionContext:
    """Load and validate checkpoint"""
    with open(path) as f:
        data = json.load(f)

    # Validate schema
    if not validate_checkpoint(data):
        raise ValueError(f"Invalid checkpoint: {path}")

    # Check version compatibility
    version = data["checkpoint_metadata"]["version"]
    if version != "1.0":
        raise ValueError(f"Unsupported checkpoint version: {version}")

    # Deserialize
    return TeamExecutionContext.from_checkpoint(data)
```

---

## Contract Validation

### Phase Boundary as Contract

**Concept**: Each phase transition is a contract between two agents:
- **Provider**: Previous phase (e.g., "phase-requirements")
- **Consumer**: Next phase (e.g., "phase-design")
- **Contract**: Expected outputs and quality standards

**Message Format**:
```python
{
    "id": "phase-transition-requirements-design",
    "ts": "2025-10-09T12:30:45Z",
    "sender": "phase-requirements",
    "receiver": "phase-design",
    "performative": "inform",  # FIPA performative
    "content": {
        # Phase outputs from requirements phase
        "requirements_doc": "...",
        "user_stories": [...],
        "acceptance_criteria": [...]
    },
    "metadata": {
        "quality_score": 0.88,
        "completeness_score": 0.92,
        "artifacts": ["requirements.md", "user_stories.md"]
    }
}
```

### Four-Pillar Validation

#### 1. Clarity Pillar
**What**: Validate message structure and schema

**Checks**:
- Message has required fields (id, ts, sender, receiver, performative, content)
- Content matches expected schema for phase outputs
- All referenced artifacts exist

**Implementation**:
```python
def validate_clarity(message: Dict) -> bool:
    """Validate message structure"""
    required = ["id", "ts", "sender", "receiver", "performative", "content"]
    if not all(k in message for k in required):
        return False

    # Validate content schema based on sender phase
    phase = message["sender"].replace("phase-", "")
    expected_schema = PHASE_OUTPUT_SCHEMAS.get(phase, {})

    return validate_schema(message["content"], expected_schema)
```

#### 2. Incentives Pillar
**What**: Validate quality meets threshold

**Checks**:
- quality_score ≥ quality_threshold (default 0.70)
- completeness_score ≥ completeness_threshold (default 0.80)
- No critical quality issues

**Implementation**:
```python
def validate_incentives(message: Dict, threshold: float = 0.70) -> bool:
    """Validate quality scores"""
    metadata = message.get("metadata", {})
    quality = metadata.get("quality_score", 0.0)
    completeness = metadata.get("completeness_score", 0.0)

    if quality < threshold:
        logger.warning(f"Quality {quality:.0%} below threshold {threshold:.0%}")
        return False

    if completeness < 0.80:
        logger.warning(f"Completeness {completeness:.0%} below 80%")
        return False

    return True
```

#### 3. Trust Pillar
**What**: Verify artifacts and signatures (optional)

**Checks**:
- All artifacts in message.metadata.artifacts exist on disk
- Artifact checksums match (if provided)
- Digital signatures valid (if required)

**Implementation**:
```python
def validate_trust(message: Dict, require_signature: bool = False) -> bool:
    """Validate artifacts and signatures"""
    metadata = message.get("metadata", {})
    artifacts = metadata.get("artifacts", [])

    # Check all artifacts exist
    for artifact_path in artifacts:
        if not Path(artifact_path).exists():
            logger.error(f"Missing artifact: {artifact_path}")
            return False

    # Optional: verify signatures
    if require_signature and "signature" in metadata:
        return verify_signature(message, metadata["signature"])

    return True
```

#### 4. Adaptability Pillar
**What**: Circuit breaker pattern for failures

**Checks**:
- Circuit breaker not open for this phase transition
- Failure rate < max_failure_rate
- No recent critical failures

**Implementation**:
```python
class PhaseCircuitBreaker:
    """Circuit breaker for phase boundaries"""

    def __init__(self, max_failures: int = 3, timeout: int = 300):
        self.max_failures = max_failures
        self.timeout = timeout
        self.failures = defaultdict(int)
        self.last_failure = {}
        self.state = {}  # "closed", "open", "half-open"

    def is_open(self, boundary: str) -> bool:
        """Check if circuit is open"""
        if self.state.get(boundary) != "open":
            return False

        # Check timeout
        if time.time() - self.last_failure.get(boundary, 0) > self.timeout:
            self.state[boundary] = "half-open"
            return False

        return True

    def record_failure(self, boundary: str):
        """Record a validation failure"""
        self.failures[boundary] += 1
        self.last_failure[boundary] = time.time()

        if self.failures[boundary] >= self.max_failures:
            self.state[boundary] = "open"
            logger.error(f"Circuit breaker OPEN for {boundary}")

    def record_success(self, boundary: str):
        """Record a validation success"""
        self.failures[boundary] = 0
        self.state[boundary] = "closed"
```

### Validation Flow

```python
async def validate_phase_boundary(
    phase_from: str,
    phase_to: str,
    outputs: Dict[str, Any],
    quality_metrics: Dict[str, Any],
    contract_manager: ContractManager,
    circuit_breaker: PhaseCircuitBreaker
) -> Dict[str, Any]:
    """
    Validate phase boundary transition.

    Returns validation result with passed/failed status.
    """
    boundary_id = f"{phase_from}-{phase_to}"

    # Check circuit breaker
    if circuit_breaker.is_open(boundary_id):
        return {
            "passed": False,
            "reason": "circuit_breaker_open",
            "details": f"Too many failures for {boundary_id}"
        }

    # Create contract message
    message = {
        "id": f"phase-transition-{boundary_id}",
        "ts": datetime.utcnow().isoformat(),
        "sender": f"phase-{phase_from}",
        "receiver": f"phase-{phase_to}",
        "performative": "inform",
        "content": outputs,
        "metadata": quality_metrics
    }

    # Validate with ContractManager (all 4 pillars)
    try:
        result = contract_manager.process_incoming_message(
            message=message,
            sender_id=f"phase-{phase_from}",
            require_signature=False
        )

        circuit_breaker.record_success(boundary_id)

        return {
            "passed": True,
            "intent": result.get("intent"),
            "details": "All validation checks passed"
        }

    except ValidationException as e:
        circuit_breaker.record_failure(boundary_id)

        return {
            "passed": False,
            "reason": "validation_failed",
            "details": str(e)
        }
```

---

## Execution Modes

### Mode 1: Single-Go (Batch)

**Description**: Execute all 5 SDLC phases continuously

**When to Use**:
- Small projects (< 4 hours)
- High confidence in requirements
- No human review needed
- Automated pipelines

**Flow**:
```
Start
  ↓
Requirements phase
  ↓
Design phase
  ↓
Implementation phase
  ↓
Testing phase
  ↓
Deployment phase
  ↓
End (single checkpoint at end, optional)
```

**API**:
```python
engine = TeamExecutionEngineV2SplitMode()
context = await engine.execute_batch(
    requirement="Build ML training API",
    create_checkpoints=False  # Optional checkpoints
)
```

**Characteristics**:
- **Speed**: Fastest (no checkpoint I/O)
- **Control**: None (all automated)
- **Recovery**: None (must restart from beginning)
- **Resource**: Needs continuous availability

### Mode 2: Phased (Split)

**Description**: Execute one phase at a time with checkpoints

**When to Use**:
- Large projects (> 8 hours)
- Uncertain requirements
- Human review required
- Resource constraints (phases at different times)

**Flow**:
```
Start
  ↓
Requirements phase
  ↓
[Checkpoint 1] ← Human reviews requirements
  ↓
Design phase
  ↓
[Checkpoint 2] ← Human reviews design
  ↓
Implementation phase
  ↓
[Checkpoint 3] ← Human reviews code
  ↓
Testing phase
  ↓
[Checkpoint 4] ← Human reviews test results
  ↓
Deployment phase
  ↓
End
```

**API**:
```python
engine = TeamExecutionEngineV2SplitMode()

# Phase 1
ctx = await engine.execute_phase("requirements")
ctx.create_checkpoint("checkpoint_req.json")

# Human reviews...

# Phase 2
ctx = await engine.resume_from_checkpoint(
    "checkpoint_req.json",
    human_edits={"requirements": {"outputs": {"priority": "high"}}}
)
```

**Characteristics**:
- **Speed**: Slower (checkpoint I/O overhead ~10%)
- **Control**: Full (human gates at every phase)
- **Recovery**: Excellent (resume from any phase)
- **Resource**: Flexible (phases run when available)

### Mode 3: Mixed

**Description**: Some phases continuous, some with checkpoints

**When to Use**:
- Medium projects (4-8 hours)
- Critical phases need review (design, testing)
- Optimize for speed + control

**Flow**:
```
Start
  ↓
Requirements + Design (continuous)
  ↓
[Checkpoint] ← Human reviews design
  ↓
Implementation (auto)
  ↓
Testing (auto)
  ↓
[Checkpoint] ← Human reviews tests
  ↓
Deployment (auto)
  ↓
End
```

**API**:
```python
engine = TeamExecutionEngineV2SplitMode()
context = await engine.execute_mixed(
    requirement="Build API",
    checkpoint_after=["design", "testing"]  # Only checkpoint these
)
```

**Characteristics**:
- **Speed**: Medium (selective checkpoint overhead ~5%)
- **Control**: Selective (gates at critical phases)
- **Recovery**: Good (resume from checkpointed phases)
- **Resource**: Balanced

### Mode 4: Parallel-Hybrid

**Description**: Sequential phases, but parallel execution within each phase

**When to Use**:
- Complex phases (e.g., implementation has backend + frontend)
- Time-sensitive projects
- Sufficient resources for parallelism

**Flow**:
```
Requirements (sequential)
  ↓
Design (sequential)
  ↓
Implementation (PARALLEL)
  ├─ Backend API (persona 1)
  ├─ Frontend UI (persona 2)
  └─ Database Schema (persona 3)
  ↓ (all complete)
Testing (PARALLEL)
  ├─ Unit Tests (persona 1)
  ├─ Integration Tests (persona 2)
  └─ Performance Tests (persona 3)
  ↓
Deployment (sequential)
```

**API**:
```python
engine = TeamExecutionEngineV2SplitMode()
context = await engine.execute_batch(
    requirement="Build API",
    parallel_phases=["implementation", "testing"]
)
```

**Characteristics**:
- **Speed**: Fast (25-50% time savings in parallel phases)
- **Control**: Phase-level
- **Recovery**: Phase-level checkpoints
- **Resource**: Requires parallel capacity

### Mode 5: Dynamic

**Description**: AI decides execution mode per phase

**When to Use**:
- Uncertain project characteristics
- Optimize automatically for speed vs control
- Research/experimental workflows

**Flow**:
```
AI analyzes requirement
  ↓
For each phase:
  AI decides:
  - Checkpoint? (based on complexity, risk)
  - Parallel? (based on parallelizability)
  - Blueprint? (based on phase needs)
  ↓
Execute with dynamic plan
```

**API**:
```python
engine = TeamExecutionEngineV2SplitMode()
context = await engine.execute_dynamic(
    requirement="Build API",
    optimize_for="speed"  # or "control" or "balanced"
)
```

**Characteristics**:
- **Speed**: Adaptive
- **Control**: Adaptive
- **Recovery**: Based on AI decisions
- **Resource**: Adaptive

### Mode Comparison

| Mode | Speed | Control | Recovery | Use Case |
|------|-------|---------|----------|----------|
| Single-Go | ⚡⚡⚡⚡⚡ | ⭐ | ⭐ | Small automated projects |
| Phased | ⚡⚡ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Large projects with review |
| Mixed | ⚡⚡⚡⚡ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Balanced approach |
| Parallel-Hybrid | ⚡⚡⚡⚡⚡ | ⭐⭐⭐ | ⭐⭐⭐ | Time-sensitive complex projects |
| Dynamic | ⚡⚡⚡⚡ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Adaptive/experimental |

---

## Implementation Design

### Class: TeamExecutionEngineV2SplitMode

```python
class TeamExecutionEngineV2SplitMode:
    """
    Split mode execution engine for team_execution_v2.

    Enables phase-by-phase execution with checkpoints and contract validation.
    """

    SDLC_PHASES = ["requirements", "design", "implementation", "testing", "deployment"]

    def __init__(
        self,
        output_dir: Optional[str] = None,
        checkpoint_dir: Optional[str] = None,
        quality_threshold: float = 0.70,
        enable_contracts: bool = True
    ):
        self.output_dir = Path(output_dir or "./generated_project")
        self.checkpoint_dir = Path(checkpoint_dir or "./checkpoints")
        self.quality_threshold = quality_threshold

        # Create underlying engine
        self.engine = TeamExecutionEngineV2(output_dir=self.output_dir)

        # Contract validation
        self.contract_manager = ContractManager() if enable_contracts else None
        self.circuit_breaker = PhaseCircuitBreaker()

        # State
        self.current_context: Optional[TeamExecutionContext] = None

    async def execute_phase(
        self,
        phase_name: str,
        checkpoint: Optional[TeamExecutionContext] = None,
        requirement: Optional[str] = None
    ) -> TeamExecutionContext:
        """
        Execute a single SDLC phase.

        Args:
            phase_name: Name of phase to execute
            checkpoint: Previous checkpoint (if resuming)
            requirement: Initial requirement (for first phase)

        Returns:
            TeamExecutionContext with this phase completed
        """
        pass  # See detailed implementation below

    async def execute_batch(
        self,
        requirement: str,
        create_checkpoints: bool = False
    ) -> TeamExecutionContext:
        """
        Execute all SDLC phases continuously.

        Args:
            requirement: Project requirement
            create_checkpoints: Whether to create checkpoints after each phase

        Returns:
            TeamExecutionContext with all phases completed
        """
        pass  # See detailed implementation below

    async def resume_from_checkpoint(
        self,
        checkpoint_path: str,
        human_edits: Optional[Dict[str, Any]] = None
    ) -> TeamExecutionContext:
        """
        Resume execution from a checkpoint file.

        Args:
            checkpoint_path: Path to checkpoint JSON file
            human_edits: Optional edits to apply before resuming

        Returns:
            TeamExecutionContext ready for next phase
        """
        pass  # See detailed implementation below
```

### Detailed Method: execute_phase()

```python
async def execute_phase(
    self,
    phase_name: str,
    checkpoint: Optional[TeamExecutionContext] = None,
    requirement: Optional[str] = None
) -> TeamExecutionContext:
    """Execute a single SDLC phase"""

    logger.info(f"\n{'='*80}")
    logger.info(f"EXECUTING PHASE: {phase_name.upper()}")
    logger.info(f"{'='*80}")

    # Step 1: Initialize or load context
    if checkpoint is None:
        if phase_name != "requirements":
            raise ValueError(f"Cannot start at {phase_name} without checkpoint")
        if requirement is None:
            raise ValueError("requirement required for first phase")

        # Create new context
        context = TeamExecutionContext.create_new(
            requirement=requirement,
            workflow_id=f"workflow-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        )
    else:
        context = checkpoint

    # Step 2: Get phase-specific requirement
    phase_requirement = self._extract_phase_requirement(
        phase_name=phase_name,
        context=context
    )

    # Step 3: Validate phase boundary (if not first phase)
    if phase_name != "requirements":
        previous_phase = self._get_previous_phase(phase_name)
        if previous_phase:
            await self._validate_phase_boundary(
                phase_from=previous_phase,
                phase_to=phase_name,
                context=context
            )

    # Step 4: Select blueprint for this phase
    blueprint_rec = await self._select_blueprint_for_phase(
        phase_name=phase_name,
        context=context
    )
    context.add_blueprint_selection(phase_name, blueprint_rec)

    # Step 5: Execute team for this phase
    logger.info(f"\n🎬 Executing team with blueprint: {blueprint_rec.blueprint_name}")

    execution_result = await self.engine.execute(
        requirement=phase_requirement,
        constraints={
            "phase": phase_name,
            "quality_threshold": self.quality_threshold
        }
    )

    # Step 6: Extract phase outputs and quality metrics
    phase_outputs = self._extract_phase_outputs(
        phase_name=phase_name,
        execution_result=execution_result
    )

    quality_metrics = {
        "overall_quality": execution_result["quality"]["overall_quality_score"],
        "contract_fulfillment": execution_result["quality"]["contracts_fulfilled"] / execution_result["quality"]["contracts_total"],
        "completeness": execution_result["execution"]["parallelization_achieved"]
    }

    # Step 7: Create PhaseResult
    phase_result = PhaseResult(
        phase_name=phase_name,
        status=PhaseStatus.COMPLETED if execution_result["success"] else PhaseStatus.FAILED,
        outputs=phase_outputs,
        context_received=context.workflow.get_all_previous_outputs(phase_name),
        context_passed={f"{phase_name}_output": phase_outputs},
        contracts_validated=[],  # Will be filled by boundary validation
        artifacts_created=execution_result.get("deliverables", {}).keys(),
        duration_seconds=execution_result["duration_seconds"],
        started_at=datetime.now(),
        completed_at=datetime.now()
    )

    # Step 8: Add to context
    context.workflow.add_phase_result(phase_name, phase_result)
    context.add_persona_results(phase_name, execution_result["deliverables"])
    context.add_quality_metrics(phase_name, quality_metrics)

    logger.info(f"\n✅ Phase {phase_name} completed")
    logger.info(f"   Quality: {quality_metrics['overall_quality']:.0%}")
    logger.info(f"   Duration: {phase_result.duration_seconds:.1f}s")

    return context
```

### Detailed Method: execute_batch()

```python
async def execute_batch(
    self,
    requirement: str,
    create_checkpoints: bool = False
) -> TeamExecutionContext:
    """Execute all SDLC phases continuously"""

    logger.info(f"\n{'='*80}")
    logger.info("BATCH EXECUTION: All SDLC Phases")
    logger.info(f"{'='*80}")

    context = None

    for phase_name in self.SDLC_PHASES:
        # Execute phase
        context = await self.execute_phase(
            phase_name=phase_name,
            checkpoint=context,
            requirement=requirement if phase_name == "requirements" else None
        )

        # Create checkpoint if requested
        if create_checkpoints:
            checkpoint_path = self.checkpoint_dir / f"{context.workflow.workflow_id}_{phase_name}.json"
            context.create_checkpoint(str(checkpoint_path))
            logger.info(f"📍 Checkpoint saved: {checkpoint_path}")

    # Mark workflow complete
    context.workflow.completed_at = datetime.now()

    logger.info(f"\n{'='*80}")
    logger.info("✅ BATCH EXECUTION COMPLETE")
    logger.info(f"{'='*80}")

    return context
```

### Detailed Method: resume_from_checkpoint()

```python
async def resume_from_checkpoint(
    self,
    checkpoint_path: str,
    human_edits: Optional[Dict[str, Any]] = None
) -> TeamExecutionContext:
    """Resume execution from checkpoint"""

    logger.info(f"\n{'='*80}")
    logger.info("RESUMING FROM CHECKPOINT")
    logger.info(f"{'='*80}")
    logger.info(f"Checkpoint: {checkpoint_path}")

    # Load checkpoint
    context = TeamExecutionContext.load_from_checkpoint(checkpoint_path)
    logger.info(f"✅ Loaded workflow: {context.workflow.workflow_id}")
    logger.info(f"   Last phase: {context.workflow.current_phase}")

    # Apply human edits
    if human_edits:
        logger.info(f"\n📝 Applying human edits...")
        context.workflow.apply_human_edits(human_edits)

        # Re-validate contracts after edits
        if self.contract_manager:
            logger.info("🔍 Re-validating contracts after edits...")
            await self._revalidate_contracts(context)

    # Get next phase
    next_phase = self._get_next_phase(context.workflow.current_phase)
    if not next_phase:
        logger.warning("⚠️  No more phases to execute")
        return context

    logger.info(f"\n▶️  Resuming with phase: {next_phase}")

    # Execute next phase
    context = await self.execute_phase(
        phase_name=next_phase,
        checkpoint=context
    )

    return context
```

---

## Scenario Matrix

### Dimension 1: Execution Mode

| ID | Mode | Description | Characteristics |
|----|------|-------------|-----------------|
| M1 | Single-Go | All phases continuous | No checkpoints, fastest |
| M2 | Phased | One phase at a time | Checkpoint after each, slowest |
| M3 | Mixed | Selective checkpoints | Checkpoints at critical phases |
| M4 | Parallel-Hybrid | Parallel within phases | Contract-first parallel work |
| M5 | Dynamic | AI-decided mode | Adaptive based on project |

### Dimension 2: Blueprint Strategy

| ID | Strategy | Description | Example |
|----|----------|-------------|---------|
| B1 | Static | Same blueprint all phases | Sequential-basic for all |
| B2 | Dynamic-Per-Phase | AI selects per phase | Collaborative design, Parallel implementation |
| B3 | Adaptive | Changes based on quality | Switch to reflection if quality low |
| B4 | User-Specified | Manual selection | User provides blueprint map |

### Dimension 3: Human Intervention

| ID | Strategy | Description | Checkpoints |
|----|----------|-------------|-------------|
| H1 | None | Fully automated | None |
| H2 | After-Each | Review every phase | After all phases |
| H3 | Critical-Only | Review design + testing | After design, testing |
| H4 | Dynamic | AI decides when needed | Based on quality/risk |

### Dimension 4: Parallelism

| ID | Strategy | Description | Parallel Work |
|----|----------|-------------|---------------|
| P1 | Sequential-Only | No parallel work | All personas sequential |
| P2 | Within-Phase | Parallel within phases | Backend ║ Frontend |
| P3 | Cross-Phase-Pipeline | Pipeline parallelism | Design starts while requirements finishing |
| P4 | Full-Parallel | Max parallelism | All independent work parallel |

### Complete Scenario Matrix

**Total Scenarios**: 5 (modes) × 4 (blueprints) × 4 (human) × 4 (parallel) = **320 possible combinations**

**Practical Scenarios** (most common/useful):

| ID | Mode | Blueprint | Human | Parallel | Use Case |
|----|------|-----------|-------|----------|----------|
| S1 | Single-Go | Static | None | Within-Phase | Small automated projects |
| S2 | Phased | Dynamic-Per-Phase | After-Each | Within-Phase | Large projects with review |
| S3 | Mixed | Dynamic-Per-Phase | Critical-Only | Within-Phase | Balanced speed + control |
| S4 | Parallel-Hybrid | Dynamic-Per-Phase | None | Full-Parallel | Time-critical complex projects |
| S5 | Dynamic | Adaptive | Dynamic | Full-Parallel | Research/experimental |
| S6 | Phased | User-Specified | After-Each | Sequential-Only | Learning/teaching scenarios |
| S7 | Single-Go | Static | None | Full-Parallel | CI/CD pipelines |
| S8 | Mixed | Adaptive | Critical-Only | Cross-Phase-Pipeline | Production workflows |

---

## Migration Path

### For Existing Users of team_execution_v2

**Current Usage**:
```python
engine = TeamExecutionEngineV2()
result = await engine.execute(requirement="Build API")
```

**Migration to Split Mode**:
```python
# Option 1: Drop-in replacement (batch mode, identical behavior)
engine = TeamExecutionEngineV2SplitMode()
context = await engine.execute_batch(requirement="Build API", create_checkpoints=False)

# Option 2: Enable checkpoints for recovery
context = await engine.execute_batch(requirement="Build API", create_checkpoints=True)

# Option 3: Full split mode (phased execution)
engine = TeamExecutionEngineV2SplitMode()
ctx = await engine.execute_phase("requirements", requirement="Build API")
ctx.create_checkpoint("checkpoint_req.json")
# ... human review ...
ctx = await engine.resume_from_checkpoint("checkpoint_req.json")
```

**Backward Compatibility**:
- ✅ Existing `TeamExecutionEngineV2` unchanged
- ✅ Split mode is separate class
- ✅ Same output format
- ✅ Same quality metrics
- ✅ No breaking changes

### For Existing SDLC Workflow Users

**Current Usage**:
```python
simulator = SDLCWorkflowSimulator()
context = simulator.execute_single_go(requirements)
```

**Migration to Team Execution V2**:
```python
# Replace simulated work with real AI team execution
engine = TeamExecutionEngineV2SplitMode()
context = await engine.execute_batch(requirement=requirements["description"])

# Still get full workflow context
context.workflow.print_context_flow()
```

**Enhancements**:
- ✅ Real AI team execution (not simulated)
- ✅ Blueprint-based team patterns
- ✅ Contract-first parallel work
- ✅ Same checkpoint format
- ✅ Same context passing

---

## Appendices

### A. Expected Schemas for Phase Outputs

```python
PHASE_OUTPUT_SCHEMAS = {
    "requirements": {
        "type": "object",
        "required": ["requirements_doc", "user_stories", "acceptance_criteria"],
        "properties": {
            "requirements_doc": {"type": "string"},
            "user_stories": {"type": "array", "items": {"type": "string"}},
            "acceptance_criteria": {"type": "array", "items": {"type": "string"}},
            "functional_requirements": {"type": "array"},
            "non_functional_requirements": {"type": "array"}
        }
    },
    "design": {
        "type": "object",
        "required": ["architecture", "api_spec"],
        "properties": {
            "architecture": {"type": "object"},
            "api_spec": {"type": "object"},
            "data_model": {"type": "object"},
            "deployment_plan": {"type": "string"}
        }
    },
    # ... similar for implementation, testing, deployment
}
```

### B. Blueprint Recommendations Per Phase

```python
PHASE_BLUEPRINT_RECOMMENDATIONS = {
    "requirements": {
        "preferred": "sequential-basic",
        "alternatives": ["collaborative-consensus"],
        "rationale": "Requirements analysis benefits from sequential thorough analysis"
    },
    "design": {
        "preferred": "collaborative-consensus",
        "alternatives": ["sequential-reflection", "parallel-specialized"],
        "rationale": "Design decisions need team discussion and consensus"
    },
    "implementation": {
        "preferred": "parallel-contract-first",
        "alternatives": ["parallel-specialized", "hybrid-sequential-parallel"],
        "rationale": "Implementation has clear contracts (API) enabling parallelism"
    },
    "testing": {
        "preferred": "parallel-specialized",
        "alternatives": ["sequential-quality-focused"],
        "rationale": "Different test types (unit, integration, performance) run in parallel"
    },
    "deployment": {
        "preferred": "sequential-emergency",
        "alternatives": ["sequential-basic"],
        "rationale": "Deployment requires careful sequential steps with rollback capability"
    }
}
```

### C. Quality Thresholds

```python
QUALITY_THRESHOLDS = {
    "requirements": {
        "quality_score": 0.75,
        "completeness_score": 0.85,
        "rationale": "Requirements must be thorough and clear"
    },
    "design": {
        "quality_score": 0.80,
        "completeness_score": 0.90,
        "rationale": "Design is foundation, must be high quality"
    },
    "implementation": {
        "quality_score": 0.70,
        "completeness_score": 0.80,
        "rationale": "Code will be tested, moderate threshold"
    },
    "testing": {
        "quality_score": 0.85,
        "completeness_score": 0.95,
        "rationale": "Testing must be comprehensive"
    },
    "deployment": {
        "quality_score": 0.90,
        "completeness_score": 0.95,
        "rationale": "Deployment to production must be perfect"
    }
}
```

---

## Conclusion

This architecture enables **team_execution_v2** to work in split mode while maintaining:
- ✅ Full state persistence via checkpoints
- ✅ Contract validation at all phase boundaries
- ✅ Flexible execution modes (batch, split, mixed, parallel, dynamic)
- ✅ Human-in-the-loop support
- ✅ Blueprint selection per phase
- ✅ Backward compatibility

**Next Steps**:
1. Implement `TeamExecutionEngineV2SplitMode` class
2. Implement `TeamExecutionContext` with serialization
3. Create scenario matrix generator
4. Build simulation suite with 6+ scenarios
5. Write integration examples
6. Add comprehensive tests

**Ready for Implementation** ✅
