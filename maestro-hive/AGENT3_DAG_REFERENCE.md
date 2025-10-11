# DAG System - Canonical Reference
## Authoritative Definitions for State, Events, Flags, and Schemas

**Status:** ✅ Implemented (as of 2025-10-11)
**Purpose:** Single source of truth for DAG system contracts
**Last Validated:** Commit [current], 2025-10-11

---

## Status Legend

Throughout the DAG documentation, you'll see these status badges:

- ✅ **Implemented** - Code exists, tested, ready to use
- 🔄 **In Progress** - Partial implementation, under active development
- 📋 **Proposed** - Design complete, implementation pending
- 🔮 **Future** - Aspirational feature, not yet scheduled

---

## 1. Feature Flags Reference

**Location:** `team_execution_dual.py:FeatureFlags`

### Environment Variables

| Variable | Type | Default | Status | Description |
|----------|------|---------|--------|-------------|
| `MAESTRO_ENABLE_DAG_EXECUTION` | bool | `false` | ✅ Implemented | Enable DAG execution mode |
| `MAESTRO_ENABLE_PARALLEL_EXECUTION` | bool | `false` | ✅ Implemented | Enable parallel phase execution |
| `MAESTRO_ENABLE_CONTEXT_PERSISTENCE` | bool | `true` | ✅ Implemented | Enable state save/resume |
| `MAESTRO_ENABLE_EXECUTION_EVENTS` | bool | `true` | ✅ Implemented | Enable event tracking |
| `MAESTRO_ENABLE_RETRY_LOGIC` | bool | `false` | 📋 Proposed | Enable automatic retry on failure |

### Execution Modes

```python
class ExecutionMode(Enum):
    LINEAR = "linear"            # ✅ Original sequential execution
    DAG_LINEAR = "dag_linear"    # ✅ DAG with sequential workflow
    DAG_PARALLEL = "dag_parallel" # ✅ DAG with parallel backend+frontend
```

**Determination Logic:**
```python
def get_execution_mode() -> ExecutionMode:
    if not MAESTRO_ENABLE_DAG_EXECUTION:
        return ExecutionMode.LINEAR
    if MAESTRO_ENABLE_PARALLEL_EXECUTION:
        return ExecutionMode.DAG_PARALLEL
    return ExecutionMode.DAG_LINEAR
```

### Verification at Runtime

```python
# Add to your startup/initialization code
from team_execution_dual import FeatureFlags

flags = FeatureFlags()
print(f"Execution mode: {flags.get_execution_mode().value}")
print(f"Feature flags: {flags.to_dict()}")
```

---

## 2. Node State Machine

**Location:** `dag_workflow.py:NodeStatus`

### States

```python
class NodeStatus(Enum):
    PENDING = "pending"       # ✅ Not yet started, waiting
    READY = "ready"          # ✅ Dependencies satisfied, can execute
    RUNNING = "running"      # ✅ Currently executing
    COMPLETED = "completed"  # ✅ Successfully completed
    FAILED = "failed"        # ✅ Execution failed
    SKIPPED = "skipped"      # ✅ Skipped due to condition
    BLOCKED = "blocked"      # ✅ Blocked by failed dependency
    CANCELLED = "cancelled"  # 📋 User cancelled execution
```

### State Transitions

**Terminal States:** `COMPLETED`, `FAILED`, `SKIPPED`, `CANCELLED`

```
┌─────────┐
│ PENDING │ ← Initial state
└────┬────┘
     │ dependencies satisfied
     ▼
┌─────────┐
│  READY  │
└────┬────┘
     │ executor.execute()
     ▼
┌─────────┐      retry exhausted     ┌────────┐
│ RUNNING │─────────────────────────→│ FAILED │ (terminal)
└────┬────┘                          └────────┘
     │
     │ condition evaluates false
     ├──────────────────────────────→┌─────────┐
     │                                │ SKIPPED │ (terminal)
     │                                └─────────┘
     │ success
     ▼
┌───────────┐
│ COMPLETED │ (terminal)
└───────────┘

Special cases:
- PENDING → BLOCKED (if dependency fails)
- RUNNING → CANCELLED (user cancellation) [📋 Proposed]
- FAILED → RUNNING (retry attempt, within retry_policy)
```

### NodeState Schema

**Location:** `dag_workflow.py:NodeState`

```python
@dataclass
class NodeState:
    node_id: str
    status: NodeStatus
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    attempt_count: int = 0
    error_message: Optional[str] = None
    output: Optional[Dict[str, Any]] = None
    artifacts: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
```

---

## 3. Workflow State Machine

**Location:** `dag_executor.py:WorkflowExecutionStatus`

### States

```python
class WorkflowExecutionStatus(Enum):
    PENDING = "pending"       # ✅ Not started
    RUNNING = "running"       # ✅ Executing nodes
    COMPLETED = "completed"   # ✅ All nodes completed
    FAILED = "failed"         # ✅ Critical node failed
    PAUSED = "paused"         # ✅ Paused by user
    CANCELLED = "cancelled"   # 📋 Cancelled by user
```

### State Transitions

```
┌─────────┐
│ PENDING │
└────┬────┘
     │ execute()
     ▼
┌─────────┐      pause()       ┌────────┐
│ RUNNING │────────────────────→│ PAUSED │
└────┬────┘                     └───┬────┘
     │                              │ resume()
     │←─────────────────────────────┘
     │
     │ blocking node fails
     ├────────────────────────────→┌────────┐
     │                              │ FAILED │ (terminal)
     │                              └────────┘
     │ all nodes complete
     ▼
┌───────────┐
│ COMPLETED │ (terminal)
└───────────┘
```

---

## 4. Event System

**Location:** `dag_executor.py:ExecutionEvent, ExecutionEventType`

### Event Types

```python
class ExecutionEventType(Enum):
    # Workflow events
    WORKFLOW_STARTED = "workflow_started"       # ✅
    WORKFLOW_COMPLETED = "workflow_completed"   # ✅
    WORKFLOW_FAILED = "workflow_failed"         # ✅

    # Node events
    NODE_STARTED = "node_started"               # ✅
    NODE_COMPLETED = "node_completed"           # ✅
    NODE_FAILED = "node_failed"                 # ✅
    NODE_RETRY = "node_retry"                   # ✅
    NODE_SKIPPED = "node_skipped"               # ✅
```

### Event Payload Schema

```typescript
// ExecutionEvent payload structure
interface ExecutionEvent {
  event_type: ExecutionEventType;
  workflow_id: string;
  execution_id: string;
  node_id?: string;           // Present for node events
  timestamp: string;          // ISO 8601 format
  data: {
    // Event-specific data
    [key: string]: any;
  };
}
```

### Event Examples

**WORKFLOW_STARTED:**
```json
{
  "event_type": "workflow_started",
  "workflow_id": "workflow_abc123",
  "execution_id": "exec_xyz789",
  "timestamp": "2025-10-11T14:30:00.000Z",
  "data": {
    "initial_context": {"requirement": "Build todo app"}
  }
}
```

**NODE_STARTED:**
```json
{
  "event_type": "node_started",
  "workflow_id": "workflow_abc123",
  "execution_id": "exec_xyz789",
  "node_id": "phase_backend_development",
  "timestamp": "2025-10-11T14:35:00.000Z",
  "data": {
    "attempt": 1,
    "max_attempts": 3
  }
}
```

**NODE_COMPLETED:**
```json
{
  "event_type": "node_completed",
  "workflow_id": "workflow_abc123",
  "execution_id": "exec_xyz789",
  "node_id": "phase_backend_development",
  "timestamp": "2025-10-11T14:50:00.000Z",
  "data": {
    "output": {"files_generated": 15},
    "attempt": 1,
    "execution_time_seconds": 900
  }
}
```

**NODE_FAILED:**
```json
{
  "event_type": "node_failed",
  "workflow_id": "workflow_abc123",
  "execution_id": "exec_xyz789",
  "node_id": "phase_frontend_development",
  "timestamp": "2025-10-11T15:00:00.000Z",
  "data": {
    "error": "Contract breach: UX_LOGIN_001 not verified",
    "attempts": 3,
    "will_retry": false
  }
}
```

### Event Handler Interface

```python
from dag_executor import ExecutionEvent

async def my_event_handler(event: ExecutionEvent) -> None:
    """
    Custom event handler.

    Called for each event during workflow execution.
    Must be async, should not block, should handle exceptions internally.
    """
    print(f"{event.event_type.value}: {event.node_id or 'workflow'}")

    # Send to monitoring
    # Update UI via WebSocket
    # Log to database
    # etc.
```

---

## 5. Contract Integration

**Related Docs:** `docs/contract_protocol/UNIVERSAL_CONTRACT_PROTOCOL.md`

### Contract Lifecycle States

The DAG system integrates with the Universal Contract Protocol. Contract states:

```python
class ContractLifecycle(Enum):
    DRAFT = "draft"
    PROPOSED = "proposed"
    NEGOTIATING = "negotiating"
    ACCEPTED = "accepted"
    IN_PROGRESS = "in_progress"
    FULFILLED = "fulfilled"
    VERIFIED = "verified"
    VERIFIED_WITH_WARNINGS = "verified_with_warnings"  # ✅ New in contract protocol
    BREACHED = "breached"
    REJECTED = "rejected"
    AMENDED = "amended"
```

### Node-Contract Mapping

Each workflow node can have associated contracts:

```python
# In WorkflowNode
@dataclass
class WorkflowNode:
    node_id: str
    name: str
    node_type: NodeType
    executor: Callable
    dependencies: List[str]

    # Contract integration
    input_contracts: List[str] = field(default_factory=list)   # ✅ Contract IDs this node depends on
    output_contracts: List[str] = field(default_factory=list)  # ✅ Contract IDs this node produces

    # Execution will block if input_contracts not VERIFIED
    # Execution will create/update output_contracts on completion
```

### Contract-Node Coordination

```python
# Before node execution
for contract_id in node.input_contracts:
    contract = contract_registry.get_contract(contract_id)
    if contract.lifecycle_state != ContractLifecycle.VERIFIED:
        raise BlockedByContractException(
            f"Node {node.node_id} blocked: Contract {contract_id} not verified"
        )

# After node execution
for contract_id in node.output_contracts:
    contract = contract_registry.get_contract(contract_id)
    verification = contract_registry.verify_contract_fulfillment(
        contract_id,
        artifacts=node_output.artifacts
    )
    if not verification.passed and contract.is_blocking:
        node_state.status = NodeStatus.FAILED
        node_state.error_message = f"Contract {contract_id} breached"
```

**See:** `docs/contract_protocol/IMPLEMENTATION_GUIDE.md` for full integration details

---

## 6. Workflow Specification Schema

**Location:** `dag_workflow.py:WorkflowDAG`

### YAML Format (for external definition)

```yaml
workflow:
  id: "workflow_sdlc_001"
  name: "SDLC Workflow"
  metadata:
    description: "Standard SDLC workflow with parallel development"
    version: "1.0.0"

nodes:
  - id: "phase_requirement_analysis"
    name: "requirement_analysis"
    type: "phase"
    dependencies: []
    config:
      phase: "requirement_analysis"
    input_contracts: []
    output_contracts: ["CONTRACT_REQ_001"]

  - id: "phase_design"
    name: "design"
    type: "phase"
    dependencies: ["phase_requirement_analysis"]
    config:
      phase: "design"
    input_contracts: ["CONTRACT_REQ_001"]
    output_contracts: ["CONTRACT_API_001", "CONTRACT_UX_001"]

  - id: "phase_backend_development"
    name: "backend_development"
    type: "phase"
    dependencies: ["phase_design"]
    execution_mode: "parallel"
    config:
      phase: "backend_development"
    input_contracts: ["CONTRACT_API_001"]
    output_contracts: ["CONTRACT_BACKEND_IMPL_001"]

  - id: "phase_frontend_development"
    name: "frontend_development"
    type: "phase"
    dependencies: ["phase_design"]
    execution_mode: "parallel"
    config:
      phase: "frontend_development"
    input_contracts: ["CONTRACT_UX_001", "CONTRACT_API_001"]
    output_contracts: ["CONTRACT_FRONTEND_IMPL_001"]

  - id: "phase_testing"
    name: "testing"
    type: "phase"
    dependencies: ["phase_backend_development", "phase_frontend_development"]
    config:
      phase: "testing"
    input_contracts: ["CONTRACT_BACKEND_IMPL_001", "CONTRACT_FRONTEND_IMPL_001"]
    output_contracts: ["CONTRACT_TEST_COVERAGE_001"]
```

### JSON Schema (for validation)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "WorkflowSpecification",
  "type": "object",
  "required": ["workflow", "nodes"],
  "properties": {
    "workflow": {
      "type": "object",
      "required": ["id", "name"],
      "properties": {
        "id": {"type": "string"},
        "name": {"type": "string"},
        "metadata": {"type": "object"}
      }
    },
    "nodes": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "name", "type"],
        "properties": {
          "id": {"type": "string"},
          "name": {"type": "string"},
          "type": {"enum": ["phase", "custom", "parallel_group", "conditional", "human_review"]},
          "dependencies": {"type": "array", "items": {"type": "string"}},
          "config": {"type": "object"},
          "execution_mode": {"enum": ["sequential", "parallel", "conditional"]},
          "condition": {"type": "string"},
          "retry_policy": {
            "type": "object",
            "properties": {
              "max_attempts": {"type": "integer", "minimum": 1},
              "retry_delay_seconds": {"type": "integer"},
              "retry_on_failure": {"type": "boolean"},
              "exponential_backoff": {"type": "boolean"}
            }
          },
          "input_contracts": {"type": "array", "items": {"type": "string"}},
          "output_contracts": {"type": "array", "items": {"type": "string"}}
        }
      }
    }
  }
}
```

---

## 7. Context and Artifacts

### WorkflowContext Schema

**Location:** `dag_workflow.py:WorkflowContext`

```python
@dataclass
class WorkflowContext:
    workflow_id: str
    execution_id: str
    node_states: Dict[str, NodeState]
    node_outputs: Dict[str, Dict[str, Any]]
    artifacts: Dict[str, List[str]]  # node_id -> artifact paths
    global_context: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
```

### Artifact Management

**Storage Location:** Configured per deployment
- Development: `./artifacts/{workflow_id}/{execution_id}/{node_id}/`
- Production: S3/MinIO: `s3://maestro-artifacts/{workflow_id}/{execution_id}/{node_id}/`

**Artifact Paths:**
```python
# Artifacts are stored with consistent naming
artifact_path = f"{storage_root}/{workflow_id}/{execution_id}/{node_id}/{filename}"

# Example:
"s3://maestro-artifacts/workflow_abc123/exec_xyz789/phase_backend_development/api_spec.yaml"
```

**ArtifactManifest Schema:**
```python
@dataclass
class ArtifactManifest:
    """Manifest of artifacts produced by a node"""
    node_id: str
    execution_id: str
    artifacts: List[Artifact]
    created_at: datetime

@dataclass
class Artifact:
    """Single artifact metadata"""
    artifact_id: str
    path: str
    type: str  # "code", "spec", "report", "screenshot", etc.
    size_bytes: int
    checksum: str  # SHA256
    metadata: Dict[str, Any]
```

---

## 8. Determinism and Caching

**Status:** 📋 Proposed (design documented, implementation pending)

### Cache Key Generation

For deterministic re-execution and memoization:

```python
def compute_node_cache_key(
    node: WorkflowNode,
    input_context: Dict[str, Any],
    upstream_digests: Dict[str, str]
) -> str:
    """
    Compute deterministic cache key for node execution.

    Key depends on:
    - Node configuration
    - Input context (requirement, previous outputs)
    - Upstream node output digests (for change detection)
    - Model versions (for AI agents)
    - Prompt templates
    - Tool versions (for validators)
    """
    key_components = [
        node.node_id,
        json.dumps(node.config, sort_keys=True),
        json.dumps(input_context, sort_keys=True),
        json.dumps(upstream_digests, sort_keys=True),
        # Model/tool versions would be added here
    ]
    return hashlib.sha256("|".join(key_components).encode()).hexdigest()
```

**Note:** Actual caching implementation requires additional infrastructure:
- Cache storage (Redis, filesystem)
- Cache invalidation policy
- Model version tracking
- Prompt template versioning

---

## 9. Security and Isolation

**Status:** 📋 Proposed (guidelines documented, enforcement pending)

### Validator Execution

Validators (Selenium, Locust, security scanners) should run in isolated environments:

```python
# Validator security guidelines
class ValidatorSecurityPolicy:
    """Security policy for validator execution"""

    # Network isolation
    allow_network: bool = True
    allowed_hosts: List[str] = []  # Whitelist

    # Resource limits
    max_memory_mb: int = 2048
    max_cpu_percent: int = 50
    max_execution_seconds: int = 300

    # Filesystem isolation
    read_only_paths: List[str] = []
    writable_paths: List[str] = ["/tmp/validators"]

    # Credentials
    credential_provider: Optional[Callable] = None  # Fetch from vault
```

**Implementation Status:**
- Resource limits: 📋 Proposed (requires container/cgroup setup)
- Network isolation: 📋 Proposed (requires network policy)
- Credential management: 📋 Proposed (requires secrets manager integration)

### Timeout Configuration

```python
# All validators must have timeouts
class ContractValidator:
    default_timeout_seconds: int = 300  # 5 minutes

    def validate(self, ...) -> CriterionResult:
        # Implementation must respect timeout
        pass
```

---

## 10. Cross-References

### Related Documentation

| Document | Purpose | Status |
|----------|---------|--------|
| `AGENT3_DAG_WORKFLOW_ARCHITECTURE.md` | System architecture and design | ✅ Implemented |
| `AGENT3_DAG_MIGRATION_GUIDE.md` | Migration from linear to DAG | ✅ Implemented |
| `AGENT3_DAG_USAGE_GUIDE.md` | Usage patterns and examples | ✅ Implemented |
| `AGENT3_DAG_IMPLEMENTATION_README.md` | Implementation overview | ✅ Implemented |
| `AGENT3_DAG_DELIVERABLES.md` | Deliverables inventory | ✅ Implemented |
| `AGENT3_DAG_QUICK_REFERENCE.md` | Quick reference card | ✅ Implemented |
| `docs/contract_protocol/UNIVERSAL_CONTRACT_PROTOCOL.md` | Contract system core | ✅ Implemented |
| `docs/contract_protocol/IMPLEMENTATION_GUIDE.md` | Contract integration | ✅ Implemented |

### Key Files

| File | Lines | Status | Description |
|------|-------|--------|-------------|
| `dag_workflow.py` | 476 | ✅ Implemented | Core DAG classes |
| `dag_executor.py` | 547 | ✅ Implemented | Execution engine |
| `dag_compatibility.py` | 437 | ✅ Implemented | Compatibility layer |
| `team_execution_dual.py` | 398 | ✅ Implemented | Dual-mode engine |
| `test_dag_system.py` | 688 | ✅ Implemented | Test suite (28 tests) |
| `example_dag_usage.py` | 717 | ✅ Implemented | Working examples |

---

## 11. Validation and Health Checks

### Runtime Verification

```bash
# Check DAG system is available
python -c "from dag_workflow import WorkflowDAG; print('✓ DAG system loaded')"

# Check feature flags
python -c "from team_execution_dual import FeatureFlags; print(FeatureFlags().to_dict())"

# Run minimal test
python -m pytest test_dag_system.py::TestWorkflowDAG::test_create_empty_dag -v
```

### Integration Test

```bash
# Run full example
python example_dag_usage.py

# Expected output: 8 examples complete successfully
# Check logs for: "ALL EXAMPLES COMPLETED"
```

---

## 12. Version Information

**DAG System Version:** 1.0.0
**Contract Protocol Version:** 1.0.0 (see `UNIVERSAL_CONTRACT_PROTOCOL.md`)
**Python Version:** 3.9+
**Key Dependencies:**
- `networkx>=3.0` (DAG operations)
- `aiohttp` (async HTTP)
- `pydantic` (optional, for schema validation)

**Last Updated:** 2025-10-11
**Last Validated Commit:** [current]

---

## Notes

1. **Status badges** are used throughout documentation:
   - ✅ = Code exists and is tested
   - 🔄 = Partially implemented
   - 📋 = Design complete, implementation pending
   - 🔮 = Future feature

2. **This document is the canonical reference** - when conflicts arise between this and other docs, this document takes precedence.

3. **Update procedure**: When adding new features, update this reference first, then update implementation guides.

4. **Validation**: Run `python -m pytest test_dag_system.py -v` to verify core functionality.

---

For questions or clarifications, refer to the implementation files or contact the development team.
