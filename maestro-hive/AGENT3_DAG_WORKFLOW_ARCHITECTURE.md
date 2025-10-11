# AGENT3: DAG-Based Workflow Architecture Specification

**Document:** Directed Acyclic Graph (DAG) Workflow System Architecture
**Purpose:** Migrate from linear SDLC pipeline to modular, pluggable DAG-based execution
**Status:** ✅ Implemented (Phase 1 complete as of 2025-10-11) | 📋 Proposed (Advanced features)
**Last Validated:** 2025-10-11

**Related Documentation:**
- [AGENT3_DAG_REFERENCE.md](./AGENT3_DAG_REFERENCE.md) - Canonical reference for state machines, events, and feature flags
- [Universal Contract Protocol](./docs/contract_protocol/UNIVERSAL_CONTRACT_PROTOCOL.md) - Contract system integration
- [Contract Types Reference](./docs/contract_protocol/CONTRACT_TYPES_REFERENCE.md) - Canonical data models

---

## Executive Summary

**Current System:** Linear pipeline (requirements → design → implementation → testing → deployment)

**Target System:** DAG-based workflow orchestration with:
- ✅ **Implemented:** Pluggable phases (add/remove nodes dynamically)
- ✅ **Implemented:** Independent execution (run any phase standalone)
- ✅ **Implemented:** Bidirectional references (forward and backward dependencies)
- ✅ **Implemented:** Full context persistence (complete state management)
- 📋 **Proposed:** Re-execution capability (rerun any phase, cascade to dependents)
- 🔄 **In Progress:** Frontend/backend sync (real-time state synchronization)
- ✅ **Implemented:** Parallel execution (run independent phases simultaneously)

**Implementation Status:**
- **Phase 1:** ✅ Complete (DAG engine, context management, basic execution)
- **Phase 2-6:** 📋 Proposed (See [Implementation Roadmap](#implementation-roadmap))

> **Note:** For canonical state machines, event schemas, and feature flags, see [AGENT3_DAG_REFERENCE.md](./AGENT3_DAG_REFERENCE.md)

---

## Table of Contents

1. [System Architecture Overview](#system-architecture-overview)
2. [Core Components](#core-components)
3. [DAG Workflow Model](#dag-workflow-model)
4. [Context & State Management](#context--state-management)
5. [Execution Engine](#execution-engine)
6. [Contract System](#contract-system)
7. [Frontend/Backend Synchronization](#frontendbackend-synchronization)
8. [Migration Strategy](#migration-strategy)
9. [Implementation Roadmap](#implementation-roadmap)
10. [Technology Stack](#technology-stack)

---

## System Architecture Overview

### High-Level Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                         Frontend Layer                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐            │
│  │ Workflow     │  │ DAG          │  │ Execution    │            │
│  │ Designer UI  │  │ Visualizer   │  │ Monitor      │            │
│  └──────────────┘  └──────────────┘  └──────────────┘            │
│         │                  │                  │                    │
│         └──────────────────┴──────────────────┘                    │
│                            │ WebSocket/SSE                         │
└────────────────────────────┼───────────────────────────────────────┘
                             │
┌────────────────────────────┼───────────────────────────────────────┐
│                  API Gateway / Event Router                        │
│                    (FastAPI / GraphQL)                             │
└────────────────────────────┬───────────────────────────────────────┘
                             │
┌────────────────────────────┴───────────────────────────────────────┐
│                     Workflow Orchestration Layer                   │
│  ┌─────────────────────────────────────────────────────────┐      │
│  │           DAG Execution Engine                          │      │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │      │
│  │  │ Dependency   │  │ Parallel     │  │ Retry/       │  │      │
│  │  │ Resolver     │  │ Coordinator  │  │ Rollback     │  │      │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  │      │
│  └─────────────────────────────────────────────────────────┘      │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────┐      │
│  │         Context & State Management                       │      │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │      │
│  │  │ Workflow     │  │ Execution    │  │ Artifact     │  │      │
│  │  │ State Store  │  │ History      │  │ Store        │  │      │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  │      │
│  └─────────────────────────────────────────────────────────┘      │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────┐      │
│  │            Contract Validation System                    │      │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │      │
│  │  │ Input        │  │ Output       │  │ Schema       │  │      │
│  │  │ Validator    │  │ Validator    │  │ Registry     │  │      │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  │      │
│  └─────────────────────────────────────────────────────────┘      │
└────────────────────────────────────────────────────────────────────┘
                             │
┌────────────────────────────┴───────────────────────────────────────┐
│                      Execution Layer                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐            │
│  │ Phase        │  │ Persona      │  │ Tool         │            │
│  │ Executors    │  │ Executors    │  │ Integrations │            │
│  └──────────────┘  └──────────────┘  └──────────────┘            │
└────────────────────────────────────────────────────────────────────┘
                             │
┌────────────────────────────┴───────────────────────────────────────┐
│                      Storage Layer                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐            │
│  │ PostgreSQL   │  │ Redis        │  │ S3/MinIO     │            │
│  │ (Workflows)  │  │ (State)      │  │ (Artifacts)  │            │
│  └──────────────┘  └──────────────┘  └──────────────┘            │
└────────────────────────────────────────────────────────────────────┘
```

---

## Core Components

> **Note:** See [AGENT3_DAG_REFERENCE.md](./AGENT3_DAG_REFERENCE.md) for canonical state machines, event schemas, and feature flags.

### 1. DAG Workflow Engine

**Status:** ✅ Implemented
**Purpose:** Manages workflow definition, execution planning, and orchestration

**Responsibilities:**
- Parse workflow definitions (YAML/JSON)
- Build dependency graph
- Detect cycles
- Determine execution order (topological sort)
- Schedule parallel execution
- Handle node failures and retries

**Key Classes:**

```python
class WorkflowDAG:
    """
    Represents a directed acyclic graph of workflow phases.

    Attributes:
        nodes: Dict of phase nodes
        edges: Dependency relationships
        metadata: Workflow-level configuration
    """

    def __init__(self, workflow_id: str, definition: Dict[str, Any]):
        self.workflow_id = workflow_id
        self.nodes: Dict[str, WorkflowNode] = {}
        self.edges: List[WorkflowEdge] = []
        self.metadata = definition.get("metadata", {})
        self._graph = nx.DiGraph()

    def add_node(self, node: WorkflowNode) -> None:
        """Add a phase node to the DAG"""
        self.nodes[node.node_id] = node
        self._graph.add_node(node.node_id, data=node)

    def add_edge(self, from_node: str, to_node: str, edge_type: str = "depends_on") -> None:
        """Add dependency edge between nodes"""
        edge = WorkflowEdge(from_node, to_node, edge_type)
        self.edges.append(edge)
        self._graph.add_edge(from_node, to_node, data=edge)

    def validate(self) -> List[str]:
        """Validate DAG (check for cycles, orphans, etc.)"""
        issues = []

        # Check for cycles
        if not nx.is_directed_acyclic_graph(self._graph):
            cycles = list(nx.simple_cycles(self._graph))
            issues.append(f"Cycles detected: {cycles}")

        # Check for orphaned nodes
        for node_id in self.nodes:
            if self._graph.in_degree(node_id) == 0 and self._graph.out_degree(node_id) == 0:
                if node_id != self.get_entry_point():
                    issues.append(f"Orphaned node: {node_id}")

        return issues

    def get_execution_order(self) -> List[List[str]]:
        """
        Get execution order as list of levels (parallel groups).

        Returns:
            List of lists, where each inner list contains node IDs
            that can execute in parallel
        """
        return list(nx.topological_generations(self._graph))

    def get_dependencies(self, node_id: str) -> List[str]:
        """Get direct dependencies of a node"""
        return list(self._graph.predecessors(node_id))

    def get_dependents(self, node_id: str) -> List[str]:
        """Get nodes that depend on this node"""
        return list(self._graph.successors(node_id))

    def get_transitive_dependencies(self, node_id: str) -> Set[str]:
        """Get all transitive dependencies (ancestors in graph)"""
        return nx.ancestors(self._graph, node_id)

    def get_transitive_dependents(self, node_id: str) -> Set[str]:
        """Get all transitive dependents (descendants in graph)"""
        return nx.descendants(self._graph, node_id)
```

---

### 2. Workflow Node Model

**Status:** ✅ Implemented
**Purpose:** Represents a single phase/stage in the workflow

> **Canonical Reference:** Node state machine transitions are defined in [AGENT3_DAG_REFERENCE.md](./AGENT3_DAG_REFERENCE.md#node-state-machine)

```python
@dataclass
class WorkflowNode:
    """
    Represents a single executable node in the workflow DAG.

    Each node is a phase (requirements, design, implementation, etc.)
    or a custom operation.
    """

    node_id: str  # Unique identifier (e.g., "requirements_phase")
    node_type: str  # Type of node (phase, conditional, parallel_group, etc.)
    executor_type: str  # What executes this node (persona, team, script)

    # Configuration
    config: Dict[str, Any] = field(default_factory=dict)

    # Contracts
    input_contract: Optional[Dict[str, Any]] = None  # What this node expects
    output_contract: Optional[Dict[str, Any]] = None  # What this node produces

    # Execution control
    retry_policy: Optional[Dict[str, Any]] = None
    timeout_seconds: Optional[int] = None
    condition: Optional[str] = None  # Conditional execution (Python expression)

    # State
    status: str = "pending"  # pending, running, completed, failed, skipped
    execution_count: int = 0
    last_execution_id: Optional[str] = None

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def can_execute(self, context: "WorkflowContext") -> bool:
        """
        Check if this node can execute given current context.

        Evaluates:
        - Conditional expression (if present)
        - Input contract satisfaction
        - Dependencies completed
        """
        # Check condition
        if self.condition:
            try:
                result = eval(self.condition, {"context": context})
                if not result:
                    return False
            except Exception as e:
                logger.error(f"Condition evaluation failed: {e}")
                return False

        # Check input contract
        if self.input_contract:
            validation = validate_input_contract(self.input_contract, context)
            if not validation.valid:
                logger.warning(f"Input contract not satisfied: {validation.errors}")
                return False

        return True


@dataclass
class WorkflowEdge:
    """
    Represents a dependency edge between workflow nodes.
    """

    from_node: str  # Source node ID
    to_node: str  # Target node ID
    edge_type: str  # depends_on, triggers, produces_for, etc.

    # Conditions
    condition: Optional[str] = None  # Edge is only active if condition true

    # Data flow
    data_mapping: Optional[Dict[str, str]] = None  # Map outputs to inputs

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
```

---

### 3. Context & State Management

**Status:** ✅ Implemented (Core features) | 📋 Proposed (Versioning, time-travel)
**Purpose:** Persistent, versioned storage of workflow state and context

> **Canonical Reference:** Context and artifact schemas are defined in [AGENT3_DAG_REFERENCE.md](./AGENT3_DAG_REFERENCE.md#context-and-artifact-management)

#### 3.1 Workflow Context Store

```python
class WorkflowContextStore:
    """
    Manages workflow execution context with versioning and persistence.

    Stores:
    - Workflow definition
    - Current execution state
    - Node outputs and artifacts
    - Version history
    """

    def __init__(self, storage_backend: StorageBackend):
        self.storage = storage_backend

    async def save_context(
        self,
        workflow_id: str,
        execution_id: str,
        context: WorkflowContext
    ) -> str:
        """
        Save workflow context with versioning.

        Returns:
            Version ID
        """
        version_id = f"{execution_id}_{datetime.utcnow().isoformat()}"

        context_data = {
            "workflow_id": workflow_id,
            "execution_id": execution_id,
            "version_id": version_id,
            "timestamp": datetime.utcnow().isoformat(),
            "dag_state": context.dag.to_dict(),
            "node_states": {
                node_id: node_state.to_dict()
                for node_id, node_state in context.node_states.items()
            },
            "global_context": context.global_context,
            "artifacts": context.artifacts,
            "metadata": context.metadata
        }

        # Store in database
        await self.storage.save(
            collection="workflow_contexts",
            key=version_id,
            data=context_data
        )

        # Update latest pointer
        await self.storage.save(
            collection="workflow_latest",
            key=f"{workflow_id}_{execution_id}",
            data={"version_id": version_id}
        )

        return version_id

    async def load_context(
        self,
        workflow_id: str,
        execution_id: str,
        version_id: Optional[str] = None
    ) -> WorkflowContext:
        """
        Load workflow context (latest or specific version).
        """
        if not version_id:
            # Get latest version
            latest = await self.storage.get(
                collection="workflow_latest",
                key=f"{workflow_id}_{execution_id}"
            )
            version_id = latest["version_id"]

        # Load context data
        context_data = await self.storage.get(
            collection="workflow_contexts",
            key=version_id
        )

        # Reconstruct WorkflowContext
        return WorkflowContext.from_dict(context_data)

    async def get_node_output(
        self,
        workflow_id: str,
        execution_id: str,
        node_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get output from a specific node."""
        context = await self.load_context(workflow_id, execution_id)
        node_state = context.node_states.get(node_id)
        return node_state.output if node_state else None

    async def get_context_for_node(
        self,
        workflow_id: str,
        execution_id: str,
        node_id: str
    ) -> Dict[str, Any]:
        """
        Build complete context for a node to execute.

        Includes:
        - Outputs from all dependency nodes
        - Global workflow context
        - Artifacts from previous nodes
        """
        context = await self.load_context(workflow_id, execution_id)
        dag = context.dag

        # Get all dependencies
        dependencies = dag.get_transitive_dependencies(node_id)

        # Collect outputs from dependencies
        dependency_outputs = {}
        for dep_node_id in dependencies:
            node_state = context.node_states.get(dep_node_id)
            if node_state and node_state.output:
                dependency_outputs[dep_node_id] = node_state.output

        # Build rich context
        node_context = {
            "workflow_id": workflow_id,
            "execution_id": execution_id,
            "node_id": node_id,
            "global_context": context.global_context,
            "dependency_outputs": dependency_outputs,
            "artifacts": context.artifacts,
            "metadata": context.metadata
        }

        return node_context
```

---

#### 3.2 Node State Model

```python
@dataclass
class NodeState:
    """
    State of a single node execution.
    """

    node_id: str
    execution_id: str  # Unique ID for this execution of the node
    status: NodeStatus  # pending, running, completed, failed, skipped

    # Input/Output
    input_context: Dict[str, Any] = field(default_factory=dict)
    output: Optional[Dict[str, Any]] = None

    # Artifacts
    artifacts_created: List[str] = field(default_factory=list)
    artifacts_consumed: List[str] = field(default_factory=list)

    # Execution metadata
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0

    # Error handling
    error: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    retry_count: int = 0

    # Quality
    quality_score: float = 0.0
    contract_fulfilled: bool = False

    # History
    execution_history: List[Dict[str, Any]] = field(default_factory=list)


class NodeStatus(str, Enum):
    """
    Node execution status

    See AGENT3_DAG_REFERENCE.md for canonical state machine and allowed transitions.
    """
    PENDING = "pending"
    WAITING_FOR_DEPS = "waiting_for_dependencies"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"
```

> **Note:** The complete state machine with allowed transitions is documented in [AGENT3_DAG_REFERENCE.md](./AGENT3_DAG_REFERENCE.md#node-state-machine)

---

## DAG Workflow Model

### Workflow Definition (YAML Format)

```yaml
# workflow_definition.yaml
workflow:
  id: "sdlc_complete_workflow"
  name: "Complete SDLC Workflow"
  version: "2.0"

  metadata:
    description: "Full software development lifecycle"
    owner: "platform_team"
    tags: ["sdlc", "production"]

  # Global context available to all nodes
  global_context:
    organization: "maestro"
    environment: "production"
    quality_threshold: 0.80

  # Define nodes (phases)
  nodes:
    - id: "requirements_phase"
      type: "phase"
      executor: "persona_team"
      config:
        personas: ["requirement_analyst"]
        output_dir: "./requirements"
      input_contract:
        required_fields:
          - initial_requirement
      output_contract:
        produces:
          - user_stories
          - acceptance_criteria
          - functional_requirements
        schema:
          type: "object"
          properties:
            user_stories:
              type: "array"
            acceptance_criteria:
              type: "object"
      retry_policy:
        max_attempts: 3
        backoff_seconds: 60

    - id: "design_phase"
      type: "phase"
      executor: "persona_team"
      config:
        personas: ["solution_architect", "database_specialist"]
        output_dir: "./design"
      input_contract:
        required_fields:
          - requirements_phase.user_stories
          - requirements_phase.acceptance_criteria
      output_contract:
        produces:
          - api_specification
          - database_schema
          - architecture_diagram
          - component_design

    - id: "implementation_backend"
      type: "phase"
      executor: "persona_team"
      config:
        personas: ["backend_developer"]
        output_dir: "./backend"
      input_contract:
        required_fields:
          - design_phase.api_specification
          - design_phase.database_schema
      output_contract:
        produces:
          - backend_code
          - api_implementation
          - database_migrations
      condition: "context.include_backend == True"  # Conditional execution

    - id: "implementation_frontend"
      type: "phase"
      executor: "persona_team"
      config:
        personas: ["frontend_developer"]
        output_dir: "./frontend"
      input_contract:
        required_fields:
          - design_phase.api_specification
          - design_phase.component_design
      output_contract:
        produces:
          - frontend_code
          - ui_components
      condition: "context.include_frontend == True"

    - id: "testing_integration"
      type: "phase"
      executor: "persona_team"
      config:
        personas: ["qa_engineer", "test_engineer"]
        output_dir: "./tests"
      input_contract:
        required_fields:
          - implementation_backend.backend_code
          - implementation_frontend.frontend_code
      output_contract:
        produces:
          - test_suite
          - test_results
          - coverage_report

    - id: "deployment_phase"
      type: "phase"
      executor: "persona_team"
      config:
        personas: ["devops_engineer", "deployment_specialist"]
        output_dir: "./deployment"
      input_contract:
        required_fields:
          - testing_integration.test_results
      output_contract:
        produces:
          - deployment_config
          - infrastructure_code
          - deployment_manifest

  # Define edges (dependencies)
  edges:
    - from: "requirements_phase"
      to: "design_phase"
      type: "depends_on"

    - from: "design_phase"
      to: "implementation_backend"
      type: "depends_on"

    - from: "design_phase"
      to: "implementation_frontend"
      type: "depends_on"

    - from: "implementation_backend"
      to: "testing_integration"
      type: "depends_on"

    - from: "implementation_frontend"
      to: "testing_integration"
      type: "depends_on"

    - from: "testing_integration"
      to: "deployment_phase"
      type: "depends_on"
      condition: "context.test_results.passed == True"
```

---

### Workflow Visualization (DAG)

```
                    ┌───────────────────┐
                    │  Requirements     │ (Entry Point)
                    │     Phase         │
                    └─────────┬─────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │     Design        │
                    │     Phase         │
                    └────────┬──────────┘
                             │
                   ┌─────────┴─────────┐
                   │                   │
                   ▼                   ▼
        ┌──────────────────┐  ┌──────────────────┐
        │  Implementation  │  │  Implementation  │  (Parallel)
        │    Backend       │  │    Frontend      │
        └─────────┬────────┘  └────────┬─────────┘
                  │                    │
                  └──────────┬─────────┘
                             │
                             ▼
                  ┌──────────────────┐
                  │     Testing      │
                  │   Integration    │
                  └─────────┬────────┘
                            │
                            ▼
                  ┌──────────────────┐
                  │   Deployment     │
                  │     Phase        │
                  └──────────────────┘
```

---

## Execution Engine

**Status:** ✅ Implemented (Basic execution) | 📋 Proposed (Advanced retry, rollback)

> **Event System:** All execution events are documented in [AGENT3_DAG_REFERENCE.md](./AGENT3_DAG_REFERENCE.md#event-system)

### DAG Executor

```python
class DAGExecutor:
    """
    Executes workflow DAG with support for:
    - Parallel execution
    - Dependency resolution
    - Retry/rollback
    - Re-execution of specific nodes
    """

    def __init__(
        self,
        context_store: WorkflowContextStore,
        node_executor_registry: NodeExecutorRegistry
    ):
        self.context_store = context_store
        self.executors = node_executor_registry
        self.event_bus = EventBus()

    async def execute_workflow(
        self,
        workflow_id: str,
        initial_context: Dict[str, Any],
        from_node: Optional[str] = None
    ) -> ExecutionResult:
        """
        Execute entire workflow or resume from specific node.

        Args:
            workflow_id: Workflow to execute
            initial_context: Initial input context
            from_node: If specified, resume from this node (re-execution)
        """
        # Create new execution
        execution_id = f"exec_{uuid.uuid4().hex[:12]}"

        # Load workflow definition
        workflow_def = await self.load_workflow_definition(workflow_id)
        dag = WorkflowDAG(workflow_id, workflow_def)

        # Validate DAG
        issues = dag.validate()
        if issues:
            raise ValueError(f"Invalid workflow DAG: {issues}")

        # Initialize context
        context = WorkflowContext(
            workflow_id=workflow_id,
            execution_id=execution_id,
            dag=dag,
            global_context=initial_context
        )

        # Save initial context
        await self.context_store.save_context(workflow_id, execution_id, context)

        # Emit workflow started event
        await self.event_bus.emit("workflow.started", {
            "workflow_id": workflow_id,
            "execution_id": execution_id
        })

        # Determine starting nodes
        if from_node:
            # Re-execution: start from specified node
            start_nodes = [from_node]
        else:
            # Full execution: start from entry nodes (no dependencies)
            start_nodes = [
                node_id for node_id in dag.nodes
                if len(dag.get_dependencies(node_id)) == 0
            ]

        # Execute DAG level by level
        result = await self._execute_dag_levels(
            dag, context, start_nodes
        )

        # Emit workflow completed event
        await self.event_bus.emit("workflow.completed", {
            "workflow_id": workflow_id,
            "execution_id": execution_id,
            "success": result.success
        })

        return result

    async def _execute_dag_levels(
        self,
        dag: WorkflowDAG,
        context: WorkflowContext,
        start_nodes: List[str]
    ) -> ExecutionResult:
        """
        Execute DAG in topological order with parallel execution where possible.
        """
        # Get execution levels (groups of nodes that can run in parallel)
        execution_levels = dag.get_execution_order()

        # If re-executing from specific node, filter levels
        if start_nodes[0] in dag.nodes:
            # Find level containing start node
            start_level_idx = None
            for idx, level in enumerate(execution_levels):
                if start_nodes[0] in level:
                    start_level_idx = idx
                    break
            execution_levels = execution_levels[start_level_idx:]

        # Execute each level
        for level_idx, level_nodes in enumerate(execution_levels):
            logger.info(f"Executing level {level_idx}: {len(level_nodes)} node(s)")

            # Filter nodes that are ready to execute
            ready_nodes = []
            for node_id in level_nodes:
                node = dag.nodes[node_id]

                # Check if all dependencies are completed
                deps = dag.get_dependencies(node_id)
                deps_completed = all(
                    context.node_states.get(dep_id, NodeState(dep_id, "")).status == NodeStatus.COMPLETED
                    for dep_id in deps
                )

                if deps_completed and node.can_execute(context):
                    ready_nodes.append(node_id)
                else:
                    # Mark as skipped or waiting
                    context.node_states[node_id] = NodeState(
                        node_id=node_id,
                        execution_id=f"{context.execution_id}_{node_id}",
                        status=NodeStatus.SKIPPED if not node.can_execute(context) else NodeStatus.WAITING_FOR_DEPS
                    )

            # Execute ready nodes in parallel
            if ready_nodes:
                await self._execute_nodes_parallel(dag, context, ready_nodes)

        # Check if workflow succeeded
        all_completed = all(
            state.status in [NodeStatus.COMPLETED, NodeStatus.SKIPPED]
            for state in context.node_states.values()
        )

        return ExecutionResult(
            workflow_id=context.workflow_id,
            execution_id=context.execution_id,
            success=all_completed,
            node_results=context.node_states
        )

    async def _execute_nodes_parallel(
        self,
        dag: WorkflowDAG,
        context: WorkflowContext,
        node_ids: List[str]
    ):
        """Execute multiple nodes in parallel"""
        logger.info(f"Executing {len(node_ids)} node(s) in parallel")

        # Create tasks for each node
        tasks = []
        for node_id in node_ids:
            task = self._execute_single_node(dag, context, node_id)
            tasks.append(task)

        # Run all tasks in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for node_id, result in zip(node_ids, results):
            if isinstance(result, Exception):
                logger.error(f"Node {node_id} failed: {result}")
                context.node_states[node_id].status = NodeStatus.FAILED
                context.node_states[node_id].error = str(result)
            else:
                logger.info(f"Node {node_id} completed successfully")

    async def _execute_single_node(
        self,
        dag: WorkflowDAG,
        context: WorkflowContext,
        node_id: str
    ) -> NodeState:
        """Execute a single node"""
        node = dag.nodes[node_id]

        logger.info(f"Executing node: {node_id}")

        # Create node execution context
        node_context = await self.context_store.get_context_for_node(
            context.workflow_id,
            context.execution_id,
            node_id
        )

        # Initialize node state
        node_state = NodeState(
            node_id=node_id,
            execution_id=f"{context.execution_id}_{node_id}_{datetime.utcnow().isoformat()}",
            status=NodeStatus.RUNNING,
            input_context=node_context,
            started_at=datetime.utcnow()
        )

        context.node_states[node_id] = node_state

        # Save state
        await self.context_store.save_context(
            context.workflow_id,
            context.execution_id,
            context
        )

        # Emit node started event
        await self.event_bus.emit("node.started", {
            "workflow_id": context.workflow_id,
            "execution_id": context.execution_id,
            "node_id": node_id
        })

        try:
            # Get executor for this node type
            executor = self.executors.get_executor(node.executor_type)

            # Execute node
            result = await executor.execute(node, node_context)

            # Update node state with results
            node_state.output = result.output
            node_state.artifacts_created = result.artifacts_created
            node_state.status = NodeStatus.COMPLETED
            node_state.quality_score = result.quality_score
            node_state.contract_fulfilled = result.contract_fulfilled
            node_state.completed_at = datetime.utcnow()
            node_state.duration_seconds = (node_state.completed_at - node_state.started_at).total_seconds()

            # Validate output contract
            if node.output_contract:
                validation = validate_output_contract(node.output_contract, result.output)
                if not validation.valid:
                    raise ValueError(f"Output contract validation failed: {validation.errors}")

            # Save state
            await self.context_store.save_context(
                context.workflow_id,
                context.execution_id,
                context
            )

            # Emit node completed event
            await self.event_bus.emit("node.completed", {
                "workflow_id": context.workflow_id,
                "execution_id": context.execution_id,
                "node_id": node_id,
                "output": result.output
            })

            return node_state

        except Exception as e:
            logger.error(f"Node {node_id} execution failed: {e}")

            node_state.status = NodeStatus.FAILED
            node_state.error = str(e)
            node_state.completed_at = datetime.utcnow()
            node_state.duration_seconds = (node_state.completed_at - node_state.started_at).total_seconds()

            # Check retry policy
            if node.retry_policy and node_state.retry_count < node.retry_policy.get("max_attempts", 0):
                logger.info(f"Retrying node {node_id} (attempt {node_state.retry_count + 1})")
                node_state.retry_count += 1

                # Wait before retry
                await asyncio.sleep(node.retry_policy.get("backoff_seconds", 0))

                # Retry
                return await self._execute_single_node(dag, context, node_id)
            else:
                # No retry or max attempts reached
                await self.context_store.save_context(
                    context.workflow_id,
                    context.execution_id,
                    context
                )

                # Emit node failed event
                await self.event_bus.emit("node.failed", {
                    "workflow_id": context.workflow_id,
                    "execution_id": context.execution_id,
                    "node_id": node_id,
                    "error": str(e)
                })

                raise

    async def re_execute_node(
        self,
        workflow_id: str,
        execution_id: str,
        node_id: str,
        cascade: bool = True
    ) -> ExecutionResult:
        """
        Re-execute a specific node and optionally cascade to dependents.

        Args:
            workflow_id: Workflow ID
            execution_id: Execution ID
            node_id: Node to re-execute
            cascade: If True, also re-execute all dependent nodes
        """
        logger.info(f"Re-executing node {node_id} (cascade={cascade})")

        # Load workflow and context
        context = await self.context_store.load_context(workflow_id, execution_id)
        dag = context.dag

        # Determine which nodes to re-execute
        nodes_to_reexecute = [node_id]

        if cascade:
            # Add all transitive dependents
            dependents = dag.get_transitive_dependents(node_id)
            nodes_to_reexecute.extend(dependents)
            logger.info(f"Cascading to {len(dependents)} dependent node(s)")

        # Reset state for nodes to re-execute
        for nid in nodes_to_reexecute:
            if nid in context.node_states:
                context.node_states[nid].status = NodeStatus.PENDING
                context.node_states[nid].retry_count = 0

        await self.context_store.save_context(workflow_id, execution_id, context)

        # Execute from the node
        return await self._execute_dag_levels(
            dag, context, [node_id]
        )
```

---

## Contract System

**Status:** ✅ Implemented (Basic validation) | 📋 Proposed (Advanced features)

**Related Documentation:**
- [Universal Contract Protocol](./docs/contract_protocol/UNIVERSAL_CONTRACT_PROTOCOL.md) - Full contract lifecycle and validation
- [Contract Types Reference](./docs/contract_protocol/CONTRACT_TYPES_REFERENCE.md) - All contract types and canonical data models
- [AGENT3_DAG_REFERENCE.md](./AGENT3_DAG_REFERENCE.md#contract-integration) - Contract integration in DAG workflows

### Input/Output Contract Validation

```python
@dataclass
class ContractSchema:
    """
    JSON Schema-based contract definition.
    """

    schema_type: str  # "input" or "output"
    schema: Dict[str, Any]  # JSON Schema
    required_fields: List[str] = field(default_factory=list)

    def validate(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate data against schema"""
        import jsonschema

        errors = []

        try:
            jsonschema.validate(instance=data, schema=self.schema)
        except jsonschema.ValidationError as e:
            errors.append(str(e))

        # Check required fields
        for field in self.required_fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors
        )


@dataclass
class ValidationResult:
    """Result of contract validation"""
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
```

---

## Frontend/Backend Synchronization

**Status:** 🔄 In Progress

> **Event Schemas:** Event payloads and types are defined in [AGENT3_DAG_REFERENCE.md](./AGENT3_DAG_REFERENCE.md#event-system)

### Event-Driven State Sync

```python
class WorkflowEventBus:
    """
    Event bus for real-time frontend/backend synchronization.

    Uses WebSocket for bi-directional communication.
    """

    def __init__(self):
        self.subscribers: Dict[str, List[callable]] = {}
        self.websocket_manager = WebSocketManager()

    async def emit(self, event_type: str, data: Dict[str, Any]):
        """
        Emit event to all subscribers.

        Events are also pushed to connected WebSocket clients.
        """
        event = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }

        # Notify local subscribers
        if event_type in self.subscribers:
            for callback in self.subscribers[event_type]:
                await callback(event)

        # Push to WebSocket clients
        await self.websocket_manager.broadcast(
            channel=f"workflow:{data.get('workflow_id')}",
            message=event
        )

    def subscribe(self, event_type: str, callback: callable):
        """Subscribe to an event type"""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(callback)
```

### Frontend State Management (React Example)

```typescript
// useWorkflowState.ts
import { useEffect, useState } from 'react';
import { WebSocketClient } from './websocket';

interface WorkflowState {
  workflowId: string;
  executionId: string;
  nodes: Record<string, NodeState>;
  currentPhase: string | null;
  status: 'running' | 'completed' | 'failed';
}

export function useWorkflowState(workflowId: string, executionId: string) {
  const [state, setState] = useState<WorkflowState | null>(null);
  const [ws, setWs] = useState<WebSocketClient | null>(null);

  useEffect(() => {
    // Connect to WebSocket
    const websocket = new WebSocketClient(`ws://api/workflows/${workflowId}/stream`);

    websocket.on('workflow.started', (data) => {
      setState(prev => ({
        ...prev,
        status: 'running',
        executionId: data.execution_id
      }));
    });

    websocket.on('node.started', (data) => {
      setState(prev => ({
        ...prev,
        nodes: {
          ...prev.nodes,
          [data.node_id]: {
            ...prev.nodes[data.node_id],
            status: 'running',
            startedAt: data.timestamp
          }
        },
        currentPhase: data.node_id
      }));
    });

    websocket.on('node.completed', (data) => {
      setState(prev => ({
        ...prev,
        nodes: {
          ...prev.nodes,
          [data.node_id]: {
            ...prev.nodes[data.node_id],
            status: 'completed',
            output: data.output,
            completedAt: data.timestamp
          }
        }
      }));
    });

    websocket.on('workflow.completed', (data) => {
      setState(prev => ({
        ...prev,
        status: data.success ? 'completed' : 'failed'
      }));
    });

    setWs(websocket);

    return () => websocket.close();
  }, [workflowId, executionId]);

  return { state, ws };
}
```

---

## Migration Strategy

**Overall Status:** Phase 1 ✅ Complete | Phases 2-6 📋 Proposed

### Phase 1: Extract Nodes (Week 1-2)

**Status:** ✅ Complete
**Goal:** Convert current linear phases to independent nodes

**Tasks:**
1. Create `WorkflowNode` class for each phase
2. Extract personas into node executors
3. Define input/output contracts for each phase
4. Create YAML workflow definition

**Current:**
```python
# Linear execution
await engine.execute_phase("requirements", ...)
await engine.execute_phase("design", ...)
await engine.execute_phase("implementation", ...)
```

**Target:**
```yaml
# DAG definition
nodes:
  - id: requirements_phase
    executor: persona_team
  - id: design_phase
    executor: persona_team
edges:
  - from: requirements_phase
    to: design_phase
```

---

### Phase 2: Implement DAG Engine (Week 3-4)

**Status:** ✅ Complete
**Goal:** Build DAG execution engine

**Tasks:**
1. ✅ Implement `WorkflowDAG` class
2. ✅ Build `DAGExecutor`
3. ✅ Add dependency resolution
4. ✅ Implement parallel execution

---

### Phase 3: Context Management (Week 5-6)

**Status:** ✅ Complete (basic features) | 📋 Proposed (advanced versioning)
**Goal:** Persistent, versioned context storage

**Tasks:**
1. ✅ Implement `WorkflowContextStore`
2. 📋 Add PostgreSQL storage backend
3. 📋 Implement context versioning
4. 📋 Add artifact storage (S3/MinIO)

---

### Phase 4: Contract System (Week 7-8)

**Status:** 📋 Proposed
**Goal:** Enforce contracts at node boundaries

**Related:** See [Universal Contract Protocol](./docs/contract_protocol/UNIVERSAL_CONTRACT_PROTOCOL.md)

**Tasks:**
1. 📋 Implement contract validation
2. 📋 Add schema registry
3. 📋 Integrate with node execution
4. 📋 Add contract testing

---

### Phase 5: Frontend Sync (Week 9-10)

**Status:** 🔄 In Progress
**Goal:** Real-time frontend/backend synchronization

**Tasks:**
1. 🔄 Implement event bus
2. 🔄 Add WebSocket server
3. 📋 Build frontend state management hooks
4. 📋 Create DAG visualizer UI

---

### Phase 6: Re-execution & Advanced Features (Week 11-12)

**Status:** 📋 Proposed
**Goal:** Support re-execution and advanced workflows

**Tasks:**
1. 📋 Implement node re-execution
2. 📋 Add cascade re-execution
3. 📋 Implement conditional nodes
4. 📋 Add parallel groups

---

## Technology Stack

### Backend

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **DAG Engine** | NetworkX + Custom | Proven graph library + custom orchestration |
| **API Layer** | FastAPI | Async support, WebSocket, auto-docs |
| **State Storage** | PostgreSQL + JSONB | Relational + flexible JSON storage |
| **Cache/Queue** | Redis | Fast state access, pub/sub |
| **Artifact Storage** | MinIO (S3-compatible) | Object storage for large files |
| **Event Streaming** | Redis Pub/Sub or Kafka | Real-time events |
| **ORM** | SQLAlchemy 2.0 | Async ORM for PostgreSQL |

### Frontend

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **Framework** | React + TypeScript | Industry standard, type safety |
| **State Management** | Zustand or Redux Toolkit | Simple yet powerful |
| **DAG Visualization** | ReactFlow or D3.js | Interactive graph rendering |
| **WebSocket Client** | Socket.IO or native WebSocket | Real-time updates |
| **API Client** | React Query | Caching, refetching |

### Infrastructure

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **Container** | Docker | Portability |
| **Orchestration** | Docker Compose or K8s | Multi-service deployment |
| **Monitoring** | Prometheus + Grafana | Metrics and dashboards |
| **Logging** | ELK Stack | Centralized logging |

---

## Database Schema

```sql
-- Workflow definitions
CREATE TABLE workflows (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    version VARCHAR(50) NOT NULL,
    definition JSONB NOT NULL,  -- Full workflow DAG definition
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(name, version)
);

-- Workflow executions
CREATE TABLE workflow_executions (
    id UUID PRIMARY KEY,
    workflow_id UUID REFERENCES workflows(id),
    status VARCHAR(50) NOT NULL,  -- pending, running, completed, failed
    global_context JSONB DEFAULT '{}',
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Node execution states
CREATE TABLE node_states (
    id UUID PRIMARY KEY,
    execution_id UUID REFERENCES workflow_executions(id),
    node_id VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL,
    input_context JSONB DEFAULT '{}',
    output JSONB DEFAULT '{}',
    artifacts JSONB DEFAULT '[]',
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_seconds DECIMAL(10, 2),
    quality_score DECIMAL(3, 2),
    error TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX(execution_id, node_id)
);

-- Context versions (for time-travel)
CREATE TABLE context_versions (
    id UUID PRIMARY KEY,
    execution_id UUID REFERENCES workflow_executions(id),
    version_number INTEGER NOT NULL,
    snapshot JSONB NOT NULL,  -- Full context snapshot
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX(execution_id, version_number)
);

-- Artifacts metadata
CREATE TABLE artifacts (
    id UUID PRIMARY KEY,
    execution_id UUID REFERENCES workflow_executions(id),
    node_id VARCHAR(255) NOT NULL,
    artifact_type VARCHAR(100),  -- file, document, data, etc.
    storage_path TEXT NOT NULL,  -- S3 path or file path
    size_bytes BIGINT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## API Endpoints

```python
# FastAPI routes

@router.post("/workflows")
async def create_workflow(definition: WorkflowDefinition) -> WorkflowResponse:
    """Create a new workflow definition"""
    pass

@router.get("/workflows/{workflow_id}")
async def get_workflow(workflow_id: str) -> WorkflowResponse:
    """Get workflow definition"""
    pass

@router.post("/workflows/{workflow_id}/execute")
async def execute_workflow(
    workflow_id: str,
    context: Dict[str, Any]
) -> ExecutionResponse:
    """Start workflow execution"""
    pass

@router.post("/workflows/{workflow_id}/executions/{execution_id}/nodes/{node_id}/reexecute")
async def reexecute_node(
    workflow_id: str,
    execution_id: str,
    node_id: str,
    cascade: bool = True
) -> ExecutionResponse:
    """Re-execute a specific node"""
    pass

@router.get("/workflows/{workflow_id}/executions/{execution_id}/state")
async def get_execution_state(
    workflow_id: str,
    execution_id: str
) -> ExecutionStateResponse:
    """Get current execution state"""
    pass

@router.websocket("/workflows/{workflow_id}/stream")
async def workflow_stream(
    websocket: WebSocket,
    workflow_id: str
):
    """WebSocket stream for real-time updates"""
    pass
```

---

## Conclusion

This DAG-based workflow architecture provides (as of 2025-10-11):

✅ **Implemented:** Flexibility - Add/remove phases dynamically
✅ **Implemented:** Independence - Each phase runs standalone
✅ **Implemented:** Parallelism - Automatic parallel execution where possible
📋 **Proposed:** Re-execution - Rerun any phase with cascade support
✅ **Implemented:** State Management - Full context persistence (versioning proposed)
🔄 **In Progress:** Synchronization - Real-time frontend/backend sync
📋 **Proposed:** Contracts - Enforced input/output validation (see [Universal Contract Protocol](./docs/contract_protocol/UNIVERSAL_CONTRACT_PROTOCOL.md))
📋 **Proposed:** Scalability - Horizontal scaling of node executors

**Migration Status:**
- **Phases 1-2:** ✅ Complete (12 weeks as of 2025-10-11)
- **Phase 3:** ✅ Complete (basic features) | 📋 Advanced features proposed
- **Phases 4-6:** 📋 Proposed (see roadmap above)

**Complexity:** Medium-High

**ROI:** High (enables dynamic workflows, improves flexibility and reliability)

---

**Current Status:**
1. ✅ Architecture approved and implemented (Phase 1)
2. ✅ Core DAG engine operational
3. 🔄 Event system and frontend sync in progress
4. 📋 Advanced features (re-execution, contracts) proposed

---

**Related Documents:**
- [AGENT3_DAG_REFERENCE.md](./AGENT3_DAG_REFERENCE.md) - **Canonical reference** for state machines, events, and feature flags
- [AGENT3_DAG_MIGRATION_GUIDE.md](./AGENT3_DAG_MIGRATION_GUIDE.md) - Migration guide
- [AGENT3_DAG_USAGE_GUIDE.md](./AGENT3_DAG_USAGE_GUIDE.md) - Usage examples
- [Universal Contract Protocol](./docs/contract_protocol/UNIVERSAL_CONTRACT_PROTOCOL.md) - Contract integration
- `AGENT3_CRITICAL_ANALYSIS.md` - Current system analysis
- `AGENT3_REMEDIATION_PLAN.md` - Immediate fixes needed before migration
- `AGENT3_CONTEXT_PASSING_REVIEW.md` - Context passing infrastructure
