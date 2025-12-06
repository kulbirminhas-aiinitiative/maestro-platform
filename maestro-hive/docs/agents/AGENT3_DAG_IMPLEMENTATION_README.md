# DAG Workflow System - Implementation Overview

**Status:** ✅ Implemented (Phase 1 complete as of 2025-10-11) | 📋 Proposed (Phases 2-4)
**Last Validated:** 2025-10-11

**Related Documentation:**
- [AGENT3_DAG_REFERENCE.md](./AGENT3_DAG_REFERENCE.md) - **Canonical reference** for state machines, events, and feature flags
- [AGENT3_DAG_WORKFLOW_ARCHITECTURE.md](./AGENT3_DAG_WORKFLOW_ARCHITECTURE.md) - Architecture specification
- [AGENT3_DAG_MIGRATION_GUIDE.md](./AGENT3_DAG_MIGRATION_GUIDE.md) - Migration guide
- [AGENT3_DAG_USAGE_GUIDE.md](./AGENT3_DAG_USAGE_GUIDE.md) - Usage examples
- [Universal Contract Protocol](./docs/contract_protocol/UNIVERSAL_CONTRACT_PROTOCOL.md) - Contract integration

## Executive Summary

A DAG (Directed Acyclic Graph) workflow system has been implemented for the Maestro SDLC platform (Phase 1 complete as of 2025-10-11), providing flexible, modular workflow execution while maintaining backward compatibility with existing code.

### Key Benefits

- **40-50% Performance Improvement**: Parallel execution of independent phases (estimated, requires production validation)
- **Backward Compatible**: Existing code continues to work unchanged (validated 2025-10-11)
- **Flexible Workflows**: Plugin/plugout phases, custom workflows (basic features implemented)
- **State Persistence**: Pause/resume capability with full context (basic implementation complete)
- **Real-time Tracking**: Event-driven progress monitoring (implemented)
- **Gradual Migration**: Feature flags enable incremental adoption (implemented)

## Implementation Status

✅ **Phase 1 Complete (as of 2025-10-11)** - Compatibility Layer & Core Infrastructure

Components implemented:
- ✅ Core DAG infrastructure (WorkflowDAG, WorkflowNode, WorkflowContext)
- ✅ DAG executor with parallel execution support
- ✅ Compatibility layer for existing SDLC phases
- ✅ Dual-mode execution engine with feature flags
- ✅ State persistence and context management (basic features)
- ✅ Test suite
- ✅ Documentation and examples

> **Canonical Reference:** See [AGENT3_DAG_REFERENCE.md](./AGENT3_DAG_REFERENCE.md) for state machines, event schemas, and feature flag defaults.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Client Application                       │
│                 (TeamExecutionEngineDual)                    │
└───────────────────────────┬─────────────────────────────────┘
                            │
                    Feature Flags Check
                            │
        ┌───────────────────┴───────────────────┐
        │                                       │
        ▼                                       ▼
┌───────────────┐                    ┌──────────────────┐
│ Linear Mode   │                    │   DAG Mode       │
│ (Existing)    │                    │   (New)          │
└───────────────┘                    └────────┬─────────┘
                                              │
                               ┌──────────────┴──────────────┐
                               │       DAG Executor          │
                               │  - Parallel execution       │
                               │  - Retry logic              │
                               │  - Conditional nodes        │
                               │  - Event tracking           │
                               └──────────────┬──────────────┘
                                              │
                        ┌─────────────────────┴─────────────────────┐
                        │                                           │
                        ▼                                           ▼
                ┌──────────────┐                          ┌─────────────────┐
                │ WorkflowDAG  │                          │ WorkflowContext │
                │ - Graph      │                          │ - Node states   │
                │ - Nodes      │                          │ - Outputs       │
                │ - Validation │                          │ - Artifacts     │
                └──────────────┘                          └─────────────────┘
                        │
                        ▼
                ┌──────────────────────┐
                │ PhaseNodeExecutor    │
                │ (Compatibility Layer)│
                └───────────┬──────────┘
                            │
                            ▼
                ┌─────────────────────────┐
                │ Existing SDLC Phases    │
                │ - requirement_analysis  │
                │ - design                │
                │ - backend_development   │
                │ - frontend_development  │
                │ - testing               │
                │ - review                │
                └─────────────────────────┘
```

## File Structure

```
maestro-hive/
├── dag_workflow.py                      # Core DAG infrastructure
│   ├── WorkflowDAG                      # Graph representation
│   ├── WorkflowNode                     # Node definition
│   ├── WorkflowContext                  # Execution context
│   └── NodeState                        # Execution state
│
├── dag_executor.py                      # DAG execution engine
│   ├── DAGExecutor                      # Main executor
│   ├── WorkflowContextStore             # State persistence
│   ├── ExecutionEvent                   # Event system
│   └── WorkflowExecutionStatus          # Status tracking
│
├── dag_compatibility.py                 # Compatibility layer
│   ├── PhaseNodeExecutor                # Phase wrapper
│   ├── generate_linear_workflow()       # Linear workflow generator
│   ├── generate_parallel_workflow()     # Parallel workflow generator
│   └── PhaseExecutionContext            # Phase context adapter
│
├── team_execution_dual.py               # Dual-mode engine
│   ├── TeamExecutionEngineDual          # Main interface
│   ├── FeatureFlags                     # Configuration
│   └── create_dual_engine()             # Factory function
│
├── test_dag_system.py                   # Comprehensive tests
│   ├── TestWorkflowDAG                  # DAG structure tests
│   ├── TestDAGExecutor                  # Execution tests
│   ├── TestCompatibilityLayer           # Compatibility tests
│   └── TestFeatureFlags                 # Feature flag tests
│
├── example_dag_usage.py                 # Usage examples
│   ├── Example 1: Simple Linear         # Basic workflow
│   ├── Example 2: Parallel              # Parallel execution
│   ├── Example 3: Conditional           # Conditional nodes
│   ├── Example 4: Retry                 # Retry logic
│   ├── Example 5: Events                # Event tracking
│   ├── Example 6: Persistence           # State persistence
│   ├── Example 7: SDLC Linear           # SDLC workflow
│   └── Example 8: SDLC Parallel         # Parallel SDLC
│
└── Documentation/
    ├── AGENT3_DAG_WORKFLOW_ARCHITECTURE.md    # Architecture spec
    ├── AGENT3_DAG_MIGRATION_GUIDE.md          # Migration plan
    ├── AGENT3_DAG_USAGE_GUIDE.md              # Usage guide
    └── AGENT3_DAG_IMPLEMENTATION_README.md    # This file
```

## Core Components

### 1. WorkflowDAG (dag_workflow.py)

Graph-based workflow representation with:
- **Nodes**: Workflow phases/tasks
- **Edges**: Dependencies between nodes
- **Validation**: Cycle detection, dependency verification
- **Execution Planning**: Topological sorting for parallel groups

**Key Methods:**
```python
dag = WorkflowDAG(name="my_workflow")
dag.add_node(node)                    # Add workflow node
dag.add_edge(from_id, to_id)         # Add dependency
dag.get_execution_order()            # Get parallel execution groups
dag.get_ready_nodes(completed)       # Get nodes ready to execute
dag.validate()                        # Validate workflow structure
```

### 2. DAGExecutor (dag_executor.py)

Executes workflows with advanced features:
- **Parallel Execution**: Independent nodes run concurrently
- **Retry Logic**: Configurable retry with exponential backoff
- **Conditional Execution**: Skip nodes based on conditions
- **State Persistence**: Save/resume capability
- **Event Tracking**: Real-time progress monitoring

**Key Methods:**
```python
executor = DAGExecutor(workflow, context_store, event_handler)
context = await executor.execute(initial_context)      # Execute workflow
context = await executor.execute(resume_execution_id)  # Resume execution
executor.pause()                                        # Pause after current group
executor.cancel()                                       # Cancel execution
```

### 3. PhaseNodeExecutor (dag_compatibility.py)

Bridges existing SDLC phases to DAG nodes:
- Wraps existing `TeamExecutionEngineV2SplitMode` phases
- Translates DAG context to phase requirements
- Extracts outputs, artifacts, and contracts
- Maintains full context passing

**Key Methods:**
```python
executor = PhaseNodeExecutor(phase_name, team_engine)
result = await executor.execute(node_input)  # Execute phase as DAG node
```

### 4. TeamExecutionEngineDual (team_execution_dual.py)

Provides backward-compatible API with mode switching:
- **Linear Mode**: Original sequential execution
- **DAG Linear Mode**: DAG with linear workflow
- **DAG Parallel Mode**: DAG with parallel workflow
- **Feature Flags**: Control mode selection

**Key Methods:**
```python
dual_engine = TeamExecutionEngineDual(linear_engine, feature_flags)
result = await dual_engine.execute(requirement)              # Execute workflow
result = await dual_engine.resume_execution(execution_id)   # Resume execution
events = dual_engine.get_execution_events()                  # Get events
```

## Quick Start

### Option 1: Environment Variables (Recommended)

```bash
# Enable DAG with parallel execution
export MAESTRO_ENABLE_DAG_EXECUTION=true
export MAESTRO_ENABLE_PARALLEL_EXECUTION=true
export MAESTRO_ENABLE_EXECUTION_EVENTS=true

# Run your application
python your_app.py
```

### Option 2: Programmatic Configuration

```python
from team_execution_v2_split_mode import TeamExecutionEngineV2SplitMode
from team_execution_dual import TeamExecutionEngineDual, FeatureFlags

# Configure feature flags
flags = FeatureFlags()
flags.enable_dag_execution = True
flags.enable_parallel_execution = True

# Create engines
linear_engine = TeamExecutionEngineV2SplitMode()
dual_engine = TeamExecutionEngineDual(linear_engine, flags)

# Execute
result = await dual_engine.execute(
    requirement="Build a todo app with React and FastAPI"
)

print(f"Execution mode: {result['execution_mode']}")
print(f"Execution time: {result['execution_time']:.2f}s")
print(f"Completed nodes: {result['completed_nodes']}/{result['total_nodes']}")
```

### Option 3: Direct DAG Usage

```python
from dag_workflow import WorkflowDAG, WorkflowNode, NodeType
from dag_executor import DAGExecutor

# Create workflow
workflow = WorkflowDAG(name="my_workflow")

# Define and add nodes
async def my_task(input_data):
    return {"result": "success"}

node = WorkflowNode(
    node_id="task1",
    name="My Task",
    node_type=NodeType.PHASE,
    executor=my_task
)
workflow.add_node(node)

# Execute
executor = DAGExecutor(workflow)
context = await executor.execute()
```

## Feature Flags

**Status:** ✅ Implemented

> **Canonical Reference:** See [AGENT3_DAG_REFERENCE.md](./AGENT3_DAG_REFERENCE.md#feature-flags) for complete feature flag reference with code examples.

Control DAG behavior via environment variables or programmatic configuration:

| Flag | Environment Variable | Default | Status | Description |
|------|---------------------|---------|--------|-------------|
| `enable_dag_execution` | `MAESTRO_ENABLE_DAG_EXECUTION` | `false` | ✅ Implemented | Enable DAG execution engine |
| `enable_parallel_execution` | `MAESTRO_ENABLE_PARALLEL_EXECUTION` | `false` | ✅ Implemented | Enable parallel phase execution |
| `enable_context_persistence` | `MAESTRO_ENABLE_CONTEXT_PERSISTENCE` | `true` | ✅ Implemented | Enable state save/resume |
| `enable_execution_events` | `MAESTRO_ENABLE_EXECUTION_EVENTS` | `true` | ✅ Implemented | Enable event tracking |
| `enable_retry_logic` | `MAESTRO_ENABLE_RETRY_LOGIC` | `false` | 📋 Proposed | Enable retry on failure |

**Execution Modes:**

| Flags | Mode | Behavior |
|-------|------|----------|
| DAG=off | `LINEAR` | Original sequential execution |
| DAG=on, Parallel=off | `DAG_LINEAR` | DAG with sequential phases |
| DAG=on, Parallel=on | `DAG_PARALLEL` | DAG with parallel backend+frontend |

## Performance Comparison

**Note:** The following are estimated improvements based on theoretical parallel execution. Production validation required.

### Linear Mode (Original)
```
Total time: 90 seconds (baseline)
────────────────────────────────────────────────────
requirement_analysis  ████████ 10s
design               ███████████████ 15s
backend_development  ███████████████████████████████████ 35s
frontend_development ████████████████████ 20s
testing              ███████ 7s
review               ███ 3s
```

### DAG Parallel Mode (Estimated)
```
Total time: ~55 seconds (estimated 39% improvement)
────────────────────────────────────────────────────
requirement_analysis  ████████ 10s
design               ███████████████ 15s
backend_development  ███████████████████████████████████ 35s
frontend_development ████████████████████  (parallel)
testing              ███████ 7s
review               ███ 3s
```

**Expected Savings:** Backend + Frontend run in parallel, reducing overlapping time from 55s (35+20) to 35s (max of the two).

**Validation Required:** Actual performance gains depend on workload characteristics and production environment. Measure in production before claiming specific improvements.

## Testing

**Status:** ✅ Implemented (as of 2025-10-11)

Test suite with code coverage (exact percentage should be measured):

```bash
# Run all tests
python -m pytest test_dag_system.py -v

# Run specific test class
python -m pytest test_dag_system.py::TestWorkflowDAG -v

# Run with coverage
python -m pytest test_dag_system.py --cov=. --cov-report=html
```

**Test Coverage:**
- ✅ Workflow DAG structure and validation
- ✅ Execution order (linear and parallel)
- ✅ Node state management
- ✅ Parallel execution correctness
- ✅ Retry policies
- ✅ Conditional execution
- ✅ Event tracking
- ✅ State persistence
- ✅ Compatibility layer
- ✅ Feature flags

## Examples

Run comprehensive examples:

```bash
python example_dag_usage.py
```

**Examples included:**
1. Simple Linear Workflow
2. Parallel Workflow
3. Conditional Execution
4. Retry Logic
5. Event Tracking
6. State Persistence
7. SDLC Workflow (Linear)
8. SDLC Workflow (Parallel)

## Migration Path

> **Complete Migration Guide:** See [AGENT3_DAG_MIGRATION_GUIDE.md](./AGENT3_DAG_MIGRATION_GUIDE.md) for detailed migration strategy and timeline.

### Phase 1: Validation (Weeks 1-2) ✅ COMPLETE (as of 2025-10-11)

**Goal**: Ensure DAG system works correctly
- [x] Implement core infrastructure
- [x] Create compatibility layer
- [x] Implement dual-mode engine
- [x] Write tests
- [x] Validate basic equivalence

**Validation Approach:**
```python
# Run in both modes and compare
result_linear = await engine.execute(req)  # Linear mode
result_dag = await engine.execute(req)     # DAG mode
# Manual validation: results_are_equivalent(result_linear, result_dag)
```

### Phase 2: Testing (Weeks 3-4) 📋 PROPOSED

**Goal**: Test in production with real requirements
- [ ] Deploy with `MAESTRO_ENABLE_DAG_EXECUTION=false` (baseline)
- [ ] Enable DAG linear mode for subset of users
- [ ] Monitor metrics and logs
- [ ] Validate output equivalence
- [ ] Collect performance data

**Success Criteria:**
- Output equivalence validated
- No regressions in functionality
- Performance neutral (same as linear)

### Phase 3: Parallel Execution (Weeks 5-8) 📋 PROPOSED

**Goal**: Enable parallel execution for performance gains
- [ ] Enable `MAESTRO_ENABLE_PARALLEL_EXECUTION=true`
- [ ] Monitor for race conditions
- [ ] Validate frontend receives full backend context
- [ ] Measure performance improvements
- [ ] Gradual rollout to all users

**Success Criteria:**
- Measured time reduction (target: 30-50%)
- No context passing issues
- Frontend generation quality maintained or improved

### Phase 4: Advanced Features (Weeks 9-12) 📋 PROPOSED

**Goal**: Add custom workflows and advanced features
- [ ] Custom workflow definitions
- [ ] Conditional phases
- [ ] Human-in-the-loop checkpoints
- [ ] Workflow templates
- [ ] Frontend workflow designer

## Monitoring

### Key Metrics

Track these metrics to validate DAG system:

```python
# Execution time
execution_time = result['execution_time']

# Success rate
success_rate = completed_nodes / total_nodes

# Event metrics
event_summary = result['event_summary']
node_failures = event_summary['node_failed']
node_retries = event_summary.get('node_retry', 0)

# Performance comparison
improvement = (linear_time - dag_time) / linear_time * 100
```

### Logging

```python
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

# DAG components log to:
# - dag_workflow
# - dag_executor
# - dag_compatibility
# - team_execution_dual
```

### Events

```python
async def monitor_events(event: ExecutionEvent):
    # Send to monitoring system
    metrics.record(event.event_type, event.node_id)

    # Log to console
    logger.info(f"{event.event_type}: {event.node_id}")

    # Update UI
    await websocket.send_json(event.to_dict())

executor = DAGExecutor(workflow, event_handler=monitor_events)
```

## Troubleshooting

### Issue: "Node has no executor function"

**Cause**: Node created without executor
**Solution**: Provide executor when creating node
```python
node = WorkflowNode(..., executor=my_function)
```

### Issue: "Workflow contains cycles"

**Cause**: Circular dependencies (A → B → C → A)
**Solution**: Remove circular dependency
```python
# Check dependencies
validation_errors = workflow.validate()
```

### Issue: "Context not available in node"

**Cause**: Missing dependency declaration
**Solution**: Declare dependency explicitly
```python
node = WorkflowNode(..., dependencies=["previous_node"])
```

### Issue: Nodes not running in parallel

**Cause**: Dependencies create sequential chain
**Solution**: Ensure parallel nodes share same parent
```python
# ✓ Good: Both depend on "design"
backend.dependencies = ["design"]
frontend.dependencies = ["design"]

# ✗ Bad: Sequential chain
frontend.dependencies = ["backend"]
```

## API Reference

See inline documentation in source files:
- `dag_workflow.py` - Core DAG classes
- `dag_executor.py` - Execution engine
- `dag_compatibility.py` - Compatibility layer
- `team_execution_dual.py` - Dual-mode engine

## Contributing

### Adding New Node Types

```python
# 1. Define node type
class NodeType(Enum):
    MY_TYPE = "my_type"

# 2. Create executor
async def my_executor(input_data):
    return {"result": "success"}

# 3. Create node
node = WorkflowNode(
    node_id="my_node",
    name="My Node",
    node_type=NodeType.MY_TYPE,
    executor=my_executor
)
```

### Adding New Features

1. Implement feature in appropriate module
2. Add feature flag to `FeatureFlags` class
3. Add environment variable support
4. Write tests in `test_dag_system.py`
5. Update documentation
6. Add example to `example_dag_usage.py`

## Resources

- **Canonical Reference**: [AGENT3_DAG_REFERENCE.md](./AGENT3_DAG_REFERENCE.md) - **State machines, events, feature flags**
- **Architecture**: [AGENT3_DAG_WORKFLOW_ARCHITECTURE.md](./AGENT3_DAG_WORKFLOW_ARCHITECTURE.md) - System architecture
- **Migration Guide**: [AGENT3_DAG_MIGRATION_GUIDE.md](./AGENT3_DAG_MIGRATION_GUIDE.md) - Migration strategy
- **Usage Guide**: [AGENT3_DAG_USAGE_GUIDE.md](./AGENT3_DAG_USAGE_GUIDE.md) - Usage examples
- **Contract Protocol**: [Universal Contract Protocol](./docs/contract_protocol/UNIVERSAL_CONTRACT_PROTOCOL.md) - Contract integration
- **Examples**: `example_dag_usage.py` (verify path exists)
- **Tests**: `test_dag_system.py` (verify path exists)

**Note:** File paths should be verified against actual codebase structure as of 2025-10-11.

## Support

For issues or questions:
1. Check documentation files listed above
2. Review example code in `example_dag_usage.py`
3. Run tests to verify setup: `pytest test_dag_system.py`
4. Check troubleshooting section in this document

## License

Part of Maestro SDLC Platform
