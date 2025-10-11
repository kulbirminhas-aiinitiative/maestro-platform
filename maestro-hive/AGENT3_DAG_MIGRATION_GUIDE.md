# AGENT3: DAG Migration Guide - From Linear Pipeline to DAG Workflow

**Document:** Step-by-Step Migration Guide
**Purpose:** Practical guide for migrating from current linear system to DAG-based workflow
**Status:** ✅ Implemented (Phases 1-2 complete as of 2025-10-11) | 📋 Proposed (Phases 3-4)
**Complexity:** Medium-High
**Last Validated:** 2025-10-11

**Related Documentation:**
- [AGENT3_DAG_REFERENCE.md](./AGENT3_DAG_REFERENCE.md) - Canonical reference for state machines, events, and feature flags
- [AGENT3_DAG_WORKFLOW_ARCHITECTURE.md](./AGENT3_DAG_WORKFLOW_ARCHITECTURE.md) - Overall architecture
- [Universal Contract Protocol](./docs/contract_protocol/UNIVERSAL_CONTRACT_PROTOCOL.md) - Contract system integration

---

## Migration Overview

### Current System (Linear Pipeline)

```python
# team_execution_v2_split_mode.py - Current approach
SDLC_PHASES = ["requirements", "design", "implementation", "testing", "deployment"]

# Execute sequentially
for phase_name in SDLC_PHASES:
    context = await engine.execute_phase(phase_name, checkpoint=context)
```

**Limitations:**
- ❌ Fixed execution order
- ❌ No parallel execution
- ❌ Cannot skip/replace phases
- ❌ Hard to add custom phases
- ❌ Re-execution requires manual handling

---

### Target System (DAG-Based)

```python
# Workflow defined in YAML/JSON
workflow = WorkflowDAG.load_from_file("sdlc_workflow.yaml")

# Execute with automatic dependency resolution
result = await dag_executor.execute_workflow(
    workflow_id="sdlc_complete",
    initial_context={"requirement": "Build e-commerce site"}
)

# Re-execute specific phase
await dag_executor.re_execute_node(
    workflow_id="sdlc_complete",
    execution_id=result.execution_id,
    node_id="frontend_phase",
    cascade=True  # Re-runs dependents too
)
```

**Benefits:**
- ✅ Dynamic execution order based on dependencies
- ✅ Automatic parallel execution
- ✅ Pluggable phases (add/remove easily)
- ✅ Conditional execution
- ✅ Built-in re-execution with cascade

---

## Migration Phases

> **Implementation Status:** Phases 1-2 are ✅ implemented. Phases 3-4 are 📋 proposed.
>
> **Canonical Reference:** See [AGENT3_DAG_REFERENCE.md](./AGENT3_DAG_REFERENCE.md) for feature flags and execution modes.

### Phase 1: Compatibility Layer (Week 1-2)

**Status:** ✅ Complete (as of 2025-10-11)
**Goal:** Create DAG wrappers around existing code without breaking current functionality

**Step 1.1: Create Node Wrappers**

```python
# dag_compatibility.py
from typing import Dict, Any
from team_execution_v2_split_mode import TeamExecutionEngineV2SplitMode

class PhaseNodeExecutor:
    """
    Wraps existing phase execution in DAG node interface.

    This allows current code to run within DAG framework.
    """

    def __init__(self, engine: TeamExecutionEngineV2SplitMode):
        self.engine = engine

    async def execute(
        self,
        node: WorkflowNode,
        context: Dict[str, Any]
    ) -> NodeExecutionResult:
        """
        Execute a phase node using existing engine.

        Args:
            node: DAG node (wraps a phase)
            context: Node execution context (includes dependency outputs)

        Returns:
            Node execution result
        """
        phase_name = node.config.get("phase_name")

        # Build TeamExecutionContext from DAG context
        team_context = self._build_team_context(node, context)

        # Extract requirement
        requirement = context.get("requirement") or context.get("global_context", {}).get("initial_requirement")

        # Execute using existing engine
        result_context = await self.engine.execute_phase(
            phase_name=phase_name,
            checkpoint=team_context,
            requirement=requirement
        )

        # Convert back to DAG result format
        return NodeExecutionResult(
            node_id=node.node_id,
            output=self._extract_outputs(result_context, phase_name),
            artifacts_created=self._extract_artifacts(result_context, phase_name),
            quality_score=self._extract_quality_score(result_context, phase_name),
            contract_fulfilled=True  # Assume fulfilled for now
        )

    def _build_team_context(
        self,
        node: WorkflowNode,
        dag_context: Dict[str, Any]
    ) -> TeamExecutionContext:
        """
        Convert DAG context to TeamExecutionContext.

        Maps dependency outputs to workflow context.
        """
        from team_execution_context import TeamExecutionContext

        # Get dependency outputs
        dependency_outputs = dag_context.get("dependency_outputs", {})

        # Create or load context
        if "team_context" in dag_context:
            # Resuming from checkpoint
            return dag_context["team_context"]
        else:
            # Create new context
            context = TeamExecutionContext.create_new(
                requirement=dag_context.get("requirement", ""),
                workflow_id=dag_context.get("workflow_id"),
                execution_mode="dag"
            )

            # Populate with dependency outputs
            for dep_node_id, dep_output in dependency_outputs.items():
                # Map DAG node to phase name
                phase_name = self._node_id_to_phase(dep_node_id)

                # Add to context as completed phase
                if phase_name and dep_output:
                    # Convert dep_output to PhaseResult
                    phase_result = self._create_phase_result(phase_name, dep_output)
                    context.workflow.add_phase_result(phase_name, phase_result)

            return context
```

**Step 1.2: Create Default Workflow Definition**

```python
# generate_default_workflow.py
def create_sdlc_workflow_from_current() -> Dict[str, Any]:
    """
    Generate DAG workflow definition from current SDLC_PHASES.

    Creates a linear DAG that matches current behavior.
    """
    workflow = {
        "workflow": {
            "id": "sdlc_linear_compat",
            "name": "SDLC Linear (Compatibility Mode)",
            "version": "1.0",
            "metadata": {
                "description": "Auto-generated from current linear pipeline",
                "compatibility_mode": True
            },
            "global_context": {},
            "nodes": [],
            "edges": []
        }
    }

    # Create nodes from SDLC_PHASES
    from team_execution_v2_split_mode import TeamExecutionEngineV2SplitMode

    phases = TeamExecutionEngineV2SplitMode.SDLC_PHASES

    for i, phase_name in enumerate(phases):
        node = {
            "id": f"{phase_name}_phase",
            "type": "phase",
            "executor": "phase_executor",  # Uses PhaseNodeExecutor
            "config": {
                "phase_name": phase_name
            },
            "input_contract": {
                "required_fields": []
            } if i == 0 else {
                "required_fields": [f"{phases[i-1]}_phase.output"]
            },
            "output_contract": {
                "produces": [f"{phase_name}_output"]
            }
        }
        workflow["workflow"]["nodes"].append(node)

        # Add edge to next phase
        if i < len(phases) - 1:
            edge = {
                "from": f"{phase_name}_phase",
                "to": f"{phases[i+1]}_phase",
                "type": "depends_on"
            }
            workflow["workflow"]["edges"].append(edge)

    return workflow
```

**Step 1.3: Create Dual-Mode Execution**

```python
# team_execution_v2_dag.py
class TeamExecutionEngineDual:
    """
    Dual-mode execution engine supporting both linear and DAG.

    Maintains backward compatibility while enabling DAG features.
    """

    def __init__(self, use_dag: bool = False):
        self.use_dag = use_dag

        if use_dag:
            self.dag_executor = DAGExecutor(...)
            self.workflow_store = WorkflowStore(...)
        else:
            self.linear_engine = TeamExecutionEngineV2SplitMode(...)

    async def execute(
        self,
        requirement: str,
        workflow_id: Optional[str] = None,
        **kwargs
    ):
        """Execute using appropriate mode"""

        if self.use_dag:
            # DAG mode
            if not workflow_id:
                # Use default linear workflow
                workflow_id = "sdlc_linear_compat"

            return await self.dag_executor.execute_workflow(
                workflow_id=workflow_id,
                initial_context={"requirement": requirement}
            )
        else:
            # Linear mode (existing)
            return await self.linear_engine.execute_batch(
                requirement=requirement,
                **kwargs
            )
```

---

### Phase 2: Gradual Feature Addition (Week 3-6)

**Status:** ✅ Complete (Basic features) | 📋 Proposed (Advanced features)
**Goal:** Add DAG features incrementally while maintaining compatibility

**Step 2.1: Add Parallel Execution Support**

**Create parallel-enabled workflow:**

```yaml
# sdlc_parallel_workflow.yaml
workflow:
  id: "sdlc_parallel"
  name: "SDLC with Parallel Implementation"
  version: "2.0"

  nodes:
    - id: "requirements_phase"
      type: "phase"
      executor: "phase_executor"
      config:
        phase_name: "requirements"

    - id: "design_phase"
      type: "phase"
      executor: "phase_executor"
      config:
        phase_name: "design"

    # ✅ NEW: Backend and frontend can run in parallel
    - id: "implementation_backend"
      type: "phase"
      executor: "phase_executor"
      config:
        phase_name: "implementation"
        personas: ["backend_developer"]
        output_dir: "./backend"

    - id: "implementation_frontend"
      type: "phase"
      executor: "phase_executor"
      config:
        phase_name: "implementation"
        personas: ["frontend_developer"]
        output_dir: "./frontend"

    - id: "testing_phase"
      type: "phase"
      executor: "phase_executor"
      config:
        phase_name: "testing"

  edges:
    - from: "requirements_phase"
      to: "design_phase"

    - from: "design_phase"
      to: "implementation_backend"

    - from: "design_phase"
      to: "implementation_frontend"

    # Both implementations feed into testing
    - from: "implementation_backend"
      to: "testing_phase"

    - from: "implementation_frontend"
      to: "testing_phase"
```

**Execution:**

```python
# Now backend and frontend run in parallel!
result = await dag_executor.execute_workflow(
    workflow_id="sdlc_parallel",
    initial_context={"requirement": "Build e-commerce site"}
)

# Time savings: ~40% (backend and frontend overlap)
```

---

**Step 2.2: Add Custom Phases**

**Add custom validation phase:**

```yaml
# Add to workflow
nodes:
  - id: "custom_security_audit"
    type: "custom"
    executor: "script_executor"
    config:
      script: "./security_audit.py"
      timeout_seconds: 300
    input_contract:
      required_fields:
        - implementation_backend.output
        - implementation_frontend.output
    output_contract:
      produces:
        - security_report
        - vulnerability_list

edges:
  - from: "implementation_backend"
    to: "custom_security_audit"
  - from: "implementation_frontend"
    to: "custom_security_audit"
  - from: "custom_security_audit"
    to: "testing_phase"
```

**Custom executor:**

```python
class ScriptNodeExecutor:
    """Execute custom scripts as DAG nodes"""

    async def execute(
        self,
        node: WorkflowNode,
        context: Dict[str, Any]
    ) -> NodeExecutionResult:
        """Run custom script"""

        script_path = node.config.get("script")
        timeout = node.config.get("timeout_seconds", 600)

        # Prepare input JSON for script
        input_data = {
            "node_id": node.node_id,
            "context": context
        }

        input_file = f"/tmp/{node.node_id}_input.json"
        with open(input_file, "w") as f:
            json.dump(input_data, f)

        # Run script
        proc = await asyncio.create_subprocess_exec(
            "python", script_path, input_file,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout
            )

            # Parse output
            output = json.loads(stdout.decode())

            return NodeExecutionResult(
                node_id=node.node_id,
                output=output,
                artifacts_created=output.get("artifacts", []),
                quality_score=output.get("quality_score", 1.0),
                contract_fulfilled=True
            )

        except asyncio.TimeoutError:
            proc.kill()
            raise TimeoutError(f"Script {script_path} timed out after {timeout}s")
```

---

**Step 2.3: Add Conditional Execution**

```yaml
# Conditional deployment based on test results
nodes:
  - id: "deployment_staging"
    type: "phase"
    executor: "phase_executor"
    config:
      phase_name: "deployment"
      environment: "staging"
    condition: "context.testing_phase.test_results.passed == True"

  - id: "deployment_production"
    type: "phase"
    executor: "phase_executor"
    config:
      phase_name: "deployment"
      environment: "production"
    condition: >
      context.testing_phase.test_results.passed == True and
      context.testing_phase.test_results.coverage > 0.80
```

---

### Phase 3: Context Migration (Week 7-8)

**Status:** 📋 Proposed
**Goal:** Migrate context storage to DAG-compatible format

> **Context Schemas:** See [AGENT3_DAG_REFERENCE.md](./AGENT3_DAG_REFERENCE.md#context-and-artifact-management) for canonical context schemas

**Step 3.1: Implement Context Adapter**

```python
class ContextAdapter:
    """
    Bidirectional adapter between TeamExecutionContext and DAG WorkflowContext.

    Allows gradual migration without breaking existing checkpoints.
    """

    @staticmethod
    def team_to_dag(team_context: TeamExecutionContext) -> WorkflowContext:
        """Convert TeamExecutionContext to DAG WorkflowContext"""

        workflow_context = WorkflowContext(
            workflow_id=team_context.workflow.workflow_id,
            execution_id=f"migrated_{datetime.utcnow().isoformat()}",
            dag=None,  # Will be populated
            global_context=team_context.workflow.metadata
        )

        # Convert phase results to node states
        for phase_name, phase_result in team_context.workflow.phase_results.items():
            node_state = NodeState(
                node_id=f"{phase_name}_phase",
                execution_id=workflow_context.execution_id,
                status=NodeStatus.COMPLETED if phase_result.status == PhaseStatus.COMPLETED else NodeStatus.FAILED,
                output=phase_result.outputs,
                artifacts_created=phase_result.artifacts_created,
                started_at=phase_result.started_at,
                completed_at=phase_result.completed_at,
                duration_seconds=phase_result.duration_seconds
            )
            workflow_context.node_states[node_state.node_id] = node_state

        return workflow_context

    @staticmethod
    def dag_to_team(workflow_context: WorkflowContext) -> TeamExecutionContext:
        """Convert DAG WorkflowContext to TeamExecutionContext"""

        team_context = TeamExecutionContext.create_new(
            requirement=workflow_context.global_context.get("initial_requirement", ""),
            workflow_id=workflow_context.workflow_id,
            execution_mode="dag"
        )

        # Convert node states to phase results
        for node_id, node_state in workflow_context.node_states.items():
            # Extract phase name from node ID
            phase_name = node_id.replace("_phase", "")

            phase_result = PhaseResult(
                phase_name=phase_name,
                status=PhaseStatus.COMPLETED if node_state.status == NodeStatus.COMPLETED else PhaseStatus.FAILED,
                outputs=node_state.output or {},
                artifacts_created=node_state.artifacts_created,
                started_at=node_state.started_at,
                completed_at=node_state.completed_at,
                duration_seconds=node_state.duration_seconds
            )

            team_context.workflow.add_phase_result(phase_name, phase_result)

        return team_context
```

**Step 3.2: Migrate Existing Checkpoints**

```python
# migrate_checkpoints.py
async def migrate_checkpoint_to_dag(checkpoint_path: str) -> str:
    """
    Migrate existing TeamExecutionContext checkpoint to DAG format.

    Returns:
        Path to new DAG checkpoint
    """
    # Load old checkpoint
    team_context = TeamExecutionContext.load_from_checkpoint(checkpoint_path)

    # Convert to DAG context
    workflow_context = ContextAdapter.team_to_dag(team_context)

    # Create default linear workflow
    workflow = create_sdlc_workflow_from_current()
    workflow_context.dag = WorkflowDAG(team_context.workflow.workflow_id, workflow)

    # Save as DAG checkpoint
    dag_checkpoint_path = checkpoint_path.replace(".json", "_dag.json")
    await context_store.save_context(
        workflow_context.workflow_id,
        workflow_context.execution_id,
        workflow_context
    )

    logger.info(f"Migrated checkpoint: {checkpoint_path} → {dag_checkpoint_path}")

    return dag_checkpoint_path
```

---

### Phase 4: Complete Migration (Week 9-12)

**Status:** 📋 Proposed
**Goal:** Fully migrate to DAG, deprecate linear mode

**Step 4.1: Workflow Registry**

```python
class WorkflowRegistry:
    """
    Central registry of workflow definitions.

    Supports versioning, templates, and custom workflows.
    """

    def __init__(self, storage: WorkflowStorage):
        self.storage = storage
        self.cache: Dict[str, WorkflowDAG] = {}

    async def register_workflow(
        self,
        workflow_def: Dict[str, Any],
        replace: bool = False
    ) -> str:
        """
        Register a workflow definition.

        Args:
            workflow_def: Workflow YAML/JSON
            replace: Replace existing workflow if present

        Returns:
            Workflow ID
        """
        workflow_id = workflow_def["workflow"]["id"]
        version = workflow_def["workflow"]["version"]

        # Check if exists
        existing = await self.storage.get_workflow(workflow_id, version)
        if existing and not replace:
            raise ValueError(f"Workflow {workflow_id} v{version} already exists")

        # Validate
        dag = WorkflowDAG(workflow_id, workflow_def)
        issues = dag.validate()
        if issues:
            raise ValueError(f"Invalid workflow: {issues}")

        # Store
        await self.storage.save_workflow(workflow_id, version, workflow_def)

        # Cache
        self.cache[f"{workflow_id}_{version}"] = dag

        logger.info(f"Registered workflow: {workflow_id} v{version}")

        return workflow_id

    async def get_workflow(
        self,
        workflow_id: str,
        version: Optional[str] = None
    ) -> WorkflowDAG:
        """Get workflow (latest version if not specified)"""

        if not version:
            version = await self.storage.get_latest_version(workflow_id)

        cache_key = f"{workflow_id}_{version}"

        if cache_key not in self.cache:
            workflow_def = await self.storage.get_workflow(workflow_id, version)
            self.cache[cache_key] = WorkflowDAG(workflow_id, workflow_def)

        return self.cache[cache_key]

    async def list_workflows(self) -> List[Dict[str, Any]]:
        """List all registered workflows"""
        return await self.storage.list_workflows()
```

**Step 4.2: CLI Migration**

```python
# Updated CLI with DAG support
@click.group()
def cli():
    """Maestro DAG Workflow CLI"""
    pass

@cli.command()
@click.option("--workflow", "-w", required=True, help="Workflow ID")
@click.option("--requirement", "-r", required=True, help="Project requirement")
@click.option("--version", "-v", help="Workflow version (default: latest)")
def execute(workflow: str, requirement: str, version: Optional[str]):
    """Execute a workflow"""
    executor = DAGExecutor(...)

    result = asyncio.run(executor.execute_workflow(
        workflow_id=workflow,
        version=version,
        initial_context={"requirement": requirement}
    ))

    if result.success:
        click.echo(click.style("✅ Workflow completed successfully", fg="green"))
    else:
        click.echo(click.style("❌ Workflow failed", fg="red"))

@cli.command()
@click.option("--workflow", "-w", required=True)
@click.option("--execution", "-e", required=True)
@click.option("--node", "-n", required=True)
@click.option("--cascade/--no-cascade", default=True)
def reexecute(workflow: str, execution: str, node: str, cascade: bool):
    """Re-execute a specific node"""
    executor = DAGExecutor(...)

    result = asyncio.run(executor.re_execute_node(
        workflow_id=workflow,
        execution_id=execution,
        node_id=node,
        cascade=cascade
    ))

    click.echo(f"Re-executed {node} (cascade={cascade})")

@cli.command()
@click.argument("workflow_file", type=click.Path(exists=True))
def register(workflow_file: str):
    """Register a workflow from YAML file"""
    with open(workflow_file) as f:
        workflow_def = yaml.safe_load(f)

    registry = WorkflowRegistry(...)
    workflow_id = asyncio.run(registry.register_workflow(workflow_def))

    click.echo(f"✅ Registered workflow: {workflow_id}")
```

---

## Backward Compatibility Strategy

### Maintaining Existing APIs

```python
# team_execution_v2_split_mode.py (updated with DAG backend)
class TeamExecutionEngineV2SplitMode:
    """
    Existing API maintained, now backed by DAG executor.

    All existing code continues to work unchanged.
    """

    def __init__(self, *args, **kwargs):
        # Create DAG executor backend
        self.dag_executor = DAGExecutor(...)
        self.workflow_id = "sdlc_linear_compat"

    async def execute_phase(
        self,
        phase_name: str,
        checkpoint: Optional[TeamExecutionContext] = None,
        requirement: Optional[str] = None,
        **kwargs
    ) -> TeamExecutionContext:
        """
        Execute single phase - UNCHANGED API.

        Now uses DAG backend internally.
        """
        # Convert checkpoint to DAG context if needed
        if checkpoint:
            dag_context = ContextAdapter.team_to_dag(checkpoint)
            execution_id = dag_context.execution_id
        else:
            execution_id = None

        # Execute single node
        node_id = f"{phase_name}_phase"

        if execution_id:
            # Resume existing execution
            result = await self.dag_executor.re_execute_node(
                workflow_id=self.workflow_id,
                execution_id=execution_id,
                node_id=node_id,
                cascade=False
            )
            dag_context = await self.dag_executor.context_store.load_context(
                self.workflow_id, execution_id
            )
        else:
            # New execution (just this phase)
            result = await self.dag_executor.execute_workflow(
                workflow_id=self.workflow_id,
                initial_context={"requirement": requirement},
                from_node=node_id
            )
            dag_context = await self.dag_executor.context_store.load_context(
                self.workflow_id, result.execution_id
            )

        # Convert back to TeamExecutionContext
        return ContextAdapter.dag_to_team(dag_context)

    async def execute_batch(
        self,
        requirement: str,
        **kwargs
    ) -> TeamExecutionContext:
        """
        Execute all phases - UNCHANGED API.

        Now uses DAG backend.
        """
        result = await self.dag_executor.execute_workflow(
            workflow_id=self.workflow_id,
            initial_context={"requirement": requirement}
        )

        dag_context = await self.dag_executor.context_store.load_context(
            self.workflow_id, result.execution_id
        )

        return ContextAdapter.dag_to_team(dag_context)
```

---

## Testing Strategy

### Test Coverage During Migration

```python
# test_migration.py
class TestDAGMigration:
    """Test DAG migration maintains existing behavior"""

    async def test_linear_execution_same_result(self):
        """DAG linear workflow produces same result as old system"""

        requirement = "Build simple REST API"

        # Old system
        old_engine = TeamExecutionEngineV2SplitMode()
        old_result = await old_engine.execute_batch(requirement)

        # New system (DAG with linear workflow)
        new_engine = TeamExecutionEngineV2SplitMode()  # Now uses DAG backend
        new_result = await new_engine.execute_batch(requirement)

        # Compare results
        assert old_result.workflow.phase_order == new_result.workflow.phase_order
        assert len(old_result.workflow.phase_results) == len(new_result.workflow.phase_results)

    async def test_checkpoint_compatibility(self):
        """Old checkpoints can be loaded in new system"""

        # Load old checkpoint
        old_checkpoint = TeamExecutionContext.load_from_checkpoint("old_checkpoint.json")

        # Migrate
        dag_context = ContextAdapter.team_to_dag(old_checkpoint)

        # Convert back
        new_checkpoint = ContextAdapter.dag_to_team(dag_context)

        # Verify equivalence
        assert old_checkpoint.workflow.workflow_id == new_checkpoint.workflow.workflow_id
        assert len(old_checkpoint.workflow.phase_results) == len(new_checkpoint.workflow.phase_results)

    async def test_parallel_execution_faster(self):
        """Parallel DAG workflow is faster than linear"""

        requirement = "Build full-stack app with backend and frontend"

        # Linear execution
        linear_start = time.time()
        linear_result = await dag_executor.execute_workflow(
            workflow_id="sdlc_linear_compat",
            initial_context={"requirement": requirement}
        )
        linear_duration = time.time() - linear_start

        # Parallel execution
        parallel_start = time.time()
        parallel_result = await dag_executor.execute_workflow(
            workflow_id="sdlc_parallel",
            initial_context={"requirement": requirement}
        )
        parallel_duration = time.time() - parallel_start

        # Parallel should be faster
        assert parallel_duration < linear_duration
        improvement = (linear_duration - parallel_duration) / linear_duration
        assert improvement > 0.20  # At least 20% improvement
```

---

## Rollout Plan

### Week-by-Week Rollout

| Week | Milestone | Deliverable | Risk Level |
|------|-----------|-------------|------------|
| 1-2 | Compatibility Layer | DAG wrappers, dual-mode execution | Low |
| 3-4 | Parallel Execution | Parallel workflow support | Medium |
| 5-6 | Custom Phases | Script executor, custom nodes | Low |
| 7-8 | Context Migration | Context adapters, checkpoint migration | Medium |
| 9-10 | Full DAG Features | Conditional execution, re-execution | Medium |
| 11-12 | Deprecate Linear | Remove old code, full migration | High |

### Feature Flags

> **Canonical Reference:** See [AGENT3_DAG_REFERENCE.md](./AGENT3_DAG_REFERENCE.md#feature-flags) for complete feature flag reference and current values.

**Status:** ✅ Implemented

```python
# config.py - Feature flags for gradual DAG migration
DAG_CONFIG = {
    "enable_dag_mode": os.getenv("MAESTRO_ENABLE_DAG_EXECUTION", "false").lower() == "true",  # ✅ Implemented
    "enable_parallel_execution": os.getenv("MAESTRO_ENABLE_PARALLEL_EXECUTION", "false").lower() == "true",  # ✅ Implemented
    "enable_custom_phases": os.getenv("ENABLE_CUSTOM_PHASES", "false").lower() == "true",  # 📋 Proposed
    "default_workflow": os.getenv("DEFAULT_WORKFLOW", "sdlc_linear_compat"),
}
```

**Gradual Enablement:**
1. Week 1-2: `enable_dag_mode=false` (old system)
2. Week 3-4: `enable_dag_mode=true`, `enable_parallel_execution=false`
3. Week 5-6: `enable_parallel_execution=true`, `enable_custom_phases=false`
4. Week 7+: All features enabled

---

## Success Metrics

### Key Performance Indicators

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| **Execution Time** | 100% (baseline) | 60-70% | Time for full SDLC workflow |
| **Parallel Efficiency** | 0% | 40-50% | Time savings from parallelization |
| **Re-execution Time** | 100% (re-run all) | 20-30% | Time to re-run one phase |
| **Workflow Flexibility** | 0 custom phases | 5+ custom phases | Number of custom workflows |
| **Context Loss** | 95% | 0% | Information passed between phases |
| **API Compatibility** | 100% | 100% | Existing code still works |

---

## Conclusion

This migration guide provides a **gradual, low-risk path** from the current linear pipeline to a full DAG-based workflow system.

**Key Principles:**
1. ✅ **Backward compatibility** - Existing code continues to work (validated as of 2025-10-11)
2. ✅ **Incremental migration** - Add features gradually (Phases 1-2 complete)
3. ✅ **Feature flags** - Enable/disable at runtime (implemented in config.py)
4. ✅ **Dual-mode support** - Run old and new in parallel (implemented)
5. ✅ **Comprehensive testing** - Verify equivalence at each step (ongoing)

**Implementation Status (as of 2025-10-11):**
- **Phases 1-2:** ✅ Complete (compatibility layer, basic parallel execution)
- **Phases 3-4:** 📋 Proposed (context migration, full feature set)
- **Timeline:** 12 weeks total (6 weeks complete, 6 weeks proposed)

**Risk:** Medium (mitigated by gradual approach and compatibility layer)

**Expected ROI:** High (estimated 40-50% execution time reduction for parallel workflows, improved flexibility)

---

**Related Documents:**
- [AGENT3_DAG_REFERENCE.md](./AGENT3_DAG_REFERENCE.md) - **Canonical reference** for state machines, events, and feature flags
- [AGENT3_DAG_WORKFLOW_ARCHITECTURE.md](./AGENT3_DAG_WORKFLOW_ARCHITECTURE.md) - Overall architecture
- [AGENT3_DAG_USAGE_GUIDE.md](./AGENT3_DAG_USAGE_GUIDE.md) - Usage examples and code patterns
- [Universal Contract Protocol](./docs/contract_protocol/UNIVERSAL_CONTRACT_PROTOCOL.md) - Contract system integration
- `AGENT3_DAG_ADVANCED_FEATURES.md` - Advanced DAG features (if exists)
- `AGENT3_CONTEXT_MEMORY_OPTIMIZATION.md` - Context optimization strategies (if exists)
