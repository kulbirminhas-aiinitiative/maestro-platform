# DAG Workflow System - Quick Reference Card

**Status:** ✅ Implemented (Phase 1 complete as of 2025-10-11) | 📋 Proposed (Advanced features)
**Last Validated:** 2025-10-11

**Related Documentation:**
- [AGENT3_DAG_REFERENCE.md](./AGENT3_DAG_REFERENCE.md) - **Canonical reference** for state machines, events, and feature flags
- [AGENT3_DAG_WORKFLOW_ARCHITECTURE.md](./AGENT3_DAG_WORKFLOW_ARCHITECTURE.md) - Architecture
- [AGENT3_DAG_MIGRATION_GUIDE.md](./AGENT3_DAG_MIGRATION_GUIDE.md) - Migration guide
- [AGENT3_DAG_USAGE_GUIDE.md](./AGENT3_DAG_USAGE_GUIDE.md) - Detailed usage
- [Universal Contract Protocol](./docs/contract_protocol/UNIVERSAL_CONTRACT_PROTOCOL.md) - Contracts

## 🚀 Quick Start (3 ways)

### 1. Zero Changes (Default Linear Mode)
```python
from team_execution_dual import create_dual_engine
from team_execution_v2_split_mode import TeamExecutionEngineV2SplitMode

engine = create_dual_engine(TeamExecutionEngineV2SplitMode())
result = await engine.execute(requirement="Build a todo app")
```

### 2. Environment Variables
```bash
export MAESTRO_ENABLE_DAG_EXECUTION=true
export MAESTRO_ENABLE_PARALLEL_EXECUTION=true
python your_app.py
```

### 3. Feature Flags
```python
from team_execution_dual import TeamExecutionEngineDual, FeatureFlags

flags = FeatureFlags()
flags.enable_dag_execution = True
flags.enable_parallel_execution = True

engine = TeamExecutionEngineDual(linear_engine, flags)
result = await engine.execute(requirement)
```

## 📊 Execution Modes

> **Canonical Reference:** See [AGENT3_DAG_REFERENCE.md](./AGENT3_DAG_REFERENCE.md#feature-flags) for complete execution mode logic.

| Mode | Flags | Time | Status | Use Case |
|------|-------|------|--------|----------|
| **LINEAR** | DAG=off | 90s | ✅ Validated | Current system (default) |
| **DAG_LINEAR** | DAG=on, Parallel=off | 90s | ✅ Implemented | Testing DAG equivalence |
| **DAG_PARALLEL** | DAG=on, Parallel=on | ~55s | ✅ Implemented | Production (estimated 30-50% faster, requires validation) |

## 🏗️ Create Custom Workflow

```python
from dag_workflow import WorkflowDAG, WorkflowNode, NodeType
from dag_executor import DAGExecutor

# 1. Create workflow
workflow = WorkflowDAG(name="my_workflow")

# 2. Define executor
async def my_task(input_data):
    # Access previous outputs
    prev = input_data['dependency_outputs']

    # Do work
    result = process_data()

    # Return output
    return {"result": result, "artifacts": ["/path/file.txt"]}

# 3. Create node
node = WorkflowNode(
    node_id="task1",
    name="My Task",
    node_type=NodeType.PHASE,
    executor=my_task,
    dependencies=["previous_task"]  # Optional
)

# 4. Add to workflow
workflow.add_node(node)

# 5. Execute
executor = DAGExecutor(workflow)
context = await executor.execute(initial_context={"key": "value"})

# 6. Get results
output = context.get_node_output("task1")
```

## 🔀 Parallel Execution Pattern

```python
from dag_compatibility import generate_parallel_workflow

# Auto-generate parallel workflow
workflow = generate_parallel_workflow(team_engine)

# Structure:
# requirement_analysis
#         ↓
#      design
#       / \
# backend  frontend  (PARALLEL)
#       \ /
#     testing
#        ↓
#      review

executor = DAGExecutor(workflow)
context = await executor.execute()
```

## 🔁 Retry Logic

**Status:** 📋 Proposed

```python
from dag_workflow import RetryPolicy

node = WorkflowNode(
    ...,
    retry_policy=RetryPolicy(
        max_attempts=3,
        retry_on_failure=True,
        retry_delay_seconds=5,
        exponential_backoff=True  # 5s, 10s, 20s
    )
)
```

## ❓ Conditional Execution

**Status:** 📋 Proposed

```python
# Check node
check_node = WorkflowNode(
    node_id="check",
    executor=lambda i: {"requires_db": True}
)

# Conditional node (runs only if check.requires_db == True)
db_node = WorkflowNode(
    node_id="setup_db",
    executor=setup_database,
    dependencies=["check"],
    condition="outputs['check']['requires_db']"
)
```

## 💾 State Persistence

```python
from dag_executor import WorkflowContextStore

# Create store
store = WorkflowContextStore()

# Execute with persistence
executor = DAGExecutor(workflow, context_store=store)
context = await executor.execute()

# Save execution ID
execution_id = context.execution_id

# Resume later
executor2 = DAGExecutor(workflow, context_store=store)
context = await executor2.execute(resume_execution_id=execution_id)
```

## 📡 Event Tracking

```python
from dag_executor import ExecutionEvent, ExecutionEventType

async def handle_event(event: ExecutionEvent):
    print(f"{event.event_type.value}: {event.node_id}")
    # Send to monitoring, update UI, etc.

executor = DAGExecutor(workflow, event_handler=handle_event)
context = await executor.execute()
```

## 🔍 Access Node Data

```python
# In node executor
async def my_node(input_data):
    # Get dependency outputs
    prev_output = input_data['dependency_outputs']['prev_node']

    # Get dependency artifacts
    artifacts = input_data['dependency_artifacts']['prev_node']

    # Get global context
    requirement = input_data['global_context']['requirement']

    # Get all outputs (for conditional logic)
    all_outputs = input_data['all_outputs']

    return {"result": "success"}
```

## 🧪 Testing

```bash
# Run all tests
pytest test_dag_system.py -v

# Run specific test
pytest test_dag_system.py::TestDAGExecutor -v

# With coverage
pytest test_dag_system.py --cov=. --cov-report=html
```

## 📋 Environment Variables

> **Canonical Reference:** See [AGENT3_DAG_REFERENCE.md](./AGENT3_DAG_REFERENCE.md#feature-flags) for complete feature flag reference and code examples.

| Variable | Default | Status | Description |
|----------|---------|--------|-------------|
| `MAESTRO_ENABLE_DAG_EXECUTION` | `false` | ✅ Implemented | Enable DAG mode |
| `MAESTRO_ENABLE_PARALLEL_EXECUTION` | `false` | ✅ Implemented | Enable parallel phases |
| `MAESTRO_ENABLE_CONTEXT_PERSISTENCE` | `true` | ✅ Implemented | Enable save/resume |
| `MAESTRO_ENABLE_EXECUTION_EVENTS` | `true` | ✅ Implemented | Enable event tracking |
| `MAESTRO_ENABLE_RETRY_LOGIC` | `false` | 📋 Proposed | Enable auto-retry |

## 🏥 Health Checks & Validation

### Verify DAG System Status

```bash
# Check if DAG modules are available
python -c "from dag_workflow import WorkflowDAG; from dag_executor import DAGExecutor; print('✅ DAG modules loaded')"

# Verify feature flags
python -c "import os; print(f\"DAG: {os.getenv('MAESTRO_ENABLE_DAG_EXECUTION', 'false')}\"); print(f\"Parallel: {os.getenv('MAESTRO_ENABLE_PARALLEL_EXECUTION', 'false')}\")"

# Run basic test
pytest test_dag_system.py::TestWorkflowDAG::test_basic_workflow -v

# Run full test suite
pytest test_dag_system.py -v --tb=short
```

### Validate Workflow Before Execution

```python
from dag_workflow import WorkflowDAG

# Validate workflow structure
workflow = WorkflowDAG(name="my_workflow")
# ... add nodes ...

# Check for issues
issues = workflow.validate()
if issues:
    print(f"⚠️ Validation errors: {issues}")
else:
    print("✅ Workflow is valid")

# Verify execution order
execution_order = workflow.get_execution_order()
print(f"Execution levels: {len(execution_order)}")
for level_idx, level_nodes in enumerate(execution_order):
    print(f"  Level {level_idx}: {level_nodes}")
```

### Monitor Execution Health

```python
from dag_executor import DAGExecutor, ExecutionEvent

# Track execution health
health_metrics = {
    "started": 0,
    "completed": 0,
    "failed": 0,
    "duration": 0
}

async def health_monitor(event: ExecutionEvent):
    if event.event_type == "NODE_STARTED":
        health_metrics["started"] += 1
    elif event.event_type == "NODE_COMPLETED":
        health_metrics["completed"] += 1
    elif event.event_type == "NODE_FAILED":
        health_metrics["failed"] += 1
        print(f"❌ Node {event.node_id} failed: {event.data.get('error')}")

executor = DAGExecutor(workflow, event_handler=health_monitor)
context = await executor.execute()

# Check health after execution
success_rate = health_metrics["completed"] / health_metrics["started"] if health_metrics["started"] > 0 else 0
print(f"Success rate: {success_rate:.1%}")
print(f"Failed nodes: {health_metrics['failed']}")
```

## 🎯 Common Patterns

### Pattern: Sequential Chain
```python
node1 = WorkflowNode("n1", ..., dependencies=[])
node2 = WorkflowNode("n2", ..., dependencies=["n1"])
node3 = WorkflowNode("n3", ..., dependencies=["n2"])

# Execution: n1 → n2 → n3
```

### Pattern: Fan-Out (Parallel)
```python
node1 = WorkflowNode("start", ..., dependencies=[])
node2 = WorkflowNode("task1", ..., dependencies=["start"])
node3 = WorkflowNode("task2", ..., dependencies=["start"])

# Execution: start → (task1 + task2) parallel
```

### Pattern: Fan-In (Merge)
```python
node1 = WorkflowNode("task1", ..., dependencies=[])
node2 = WorkflowNode("task2", ..., dependencies=[])
node3 = WorkflowNode("merge", ..., dependencies=["task1", "task2"])

# Execution: (task1 + task2) parallel → merge
```

### Pattern: Diamond
```python
start = WorkflowNode("start", ..., dependencies=[])
left = WorkflowNode("left", ..., dependencies=["start"])
right = WorkflowNode("right", ..., dependencies=["start"])
merge = WorkflowNode("merge", ..., dependencies=["left", "right"])

# Execution: start → (left + right) parallel → merge
```

## 🐛 Troubleshooting

### Issue: "Node has no executor"
```python
# ✗ Bad
node = WorkflowNode(node_id="task", name="Task", node_type=NodeType.PHASE)

# ✓ Good
node = WorkflowNode(..., executor=my_function)
```

### Issue: "Workflow contains cycles"
```python
# ✗ Bad: A → B → C → A (cycle)
# ✓ Good: A → B → C
```

### Issue: Nodes not running in parallel
```python
# ✗ Bad: Sequential chain
frontend.dependencies = ["backend"]

# ✓ Good: Parallel execution
backend.dependencies = ["design"]
frontend.dependencies = ["design"]  # Same parent!
```

### Issue: Context not available
```python
# ✗ Bad: Missing dependency
node.dependencies = []

# ✓ Good: Declare dependency
node.dependencies = ["previous_node"]
```

## 📖 Documentation Files

| File | Purpose |
|------|---------|
| `AGENT3_DAG_IMPLEMENTATION_README.md` | Overview & getting started |
| `AGENT3_DAG_WORKFLOW_ARCHITECTURE.md` | Complete architecture |
| `AGENT3_DAG_MIGRATION_GUIDE.md` | Migration plan |
| `AGENT3_DAG_USAGE_GUIDE.md` | Detailed usage guide |
| `AGENT3_DAG_DELIVERABLES.md` | Complete deliverables |
| `AGENT3_DAG_QUICK_REFERENCE.md` | This file |

## 🔗 Code Files

> **Note:** Line counts are approximate (as of 2025-10-11) and may drift. Verify paths exist in your codebase.

| File | Lines | Status | Purpose |
|------|-------|--------|---------|
| `dag_workflow.py` | ~476 | ✅ Implemented | Core DAG classes |
| `dag_executor.py` | ~547 | ✅ Implemented | Execution engine |
| `dag_compatibility.py` | ~437 | ✅ Implemented | Compatibility layer |
| `team_execution_dual.py` | ~398 | ✅ Implemented | Dual-mode engine |
| `test_dag_system.py` | ~688 | ✅ Implemented | Test suite |
| `example_dag_usage.py` | ~717 | ✅ Implemented | Working examples (verify path) |

## 🎓 Learn More

1. **Start**: Run `python example_dag_usage.py`
2. **Read**: `AGENT3_DAG_IMPLEMENTATION_README.md`
3. **Study**: Code examples in `example_dag_usage.py`
4. **Deep Dive**: `AGENT3_DAG_WORKFLOW_ARCHITECTURE.md`
5. **Migrate**: Follow `AGENT3_DAG_MIGRATION_GUIDE.md`

## 📊 Performance Reference

**Note:** The following are estimated timings based on theoretical parallel execution. Production validation required.

```
Linear Mode:     [========================================] ~90s (baseline)
DAG Parallel:    [========================] ~55s (estimated 30-50% faster)

Estimated Breakdown (requires production measurement):
  req_analysis:  10s → 10s (same)
  design:        15s → 15s (same)
  backend:       35s ↘
  frontend:      20s ↗  35s (parallel, max of both)
  testing:       7s  → 7s  (same)
  review:        3s  → 3s  (same)
```

**Validation Required:** Actual performance depends on workload and environment. Measure in production.

## ✅ Pre-Deployment Checklist

- [ ] Tests pass: `pytest test_dag_system.py`
- [ ] Examples run: `python example_dag_usage.py`
- [ ] Feature flags configured
- [ ] Monitoring enabled
- [ ] Team trained
- [ ] Rollback plan ready

---

## 📚 Additional Resources

- **Canonical Reference**: [AGENT3_DAG_REFERENCE.md](./AGENT3_DAG_REFERENCE.md) - **State machines, events, feature flags**
- **Contract Integration**: [Universal Contract Protocol](./docs/contract_protocol/UNIVERSAL_CONTRACT_PROTOCOL.md)
- **Full Documentation**: See files listed in "Documentation Files" section above

---

**Quick Reference v1.0** | *Part of AGENT3 DAG Implementation*
**Status:** ✅ Phase 1 implemented (as of 2025-10-11) | 📋 Advanced features proposed
**Last Validated:** 2025-10-11

**Note:** Module names, file paths, and API signatures should be verified against actual codebase implementation.
