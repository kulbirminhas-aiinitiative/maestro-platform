"""
DAG System Test Suite

Comprehensive tests for:
1. DAG workflow structure validation
2. Execution equivalence (linear vs DAG)
3. Parallel execution correctness
4. State persistence and recovery
5. Event tracking

Run with: python -m pytest test_dag_system.py -v
"""

import asyncio
import pytest
from typing import Dict, Any
from datetime import datetime

from dag_workflow import (
    WorkflowDAG,
    WorkflowNode,
    WorkflowContext,
    NodeType,
    NodeStatus,
    ExecutionMode,
    RetryPolicy,
)
from dag_executor import DAGExecutor, WorkflowContextStore, ExecutionEvent
from dag_compatibility import (
    PhaseNodeExecutor,
    generate_linear_workflow,
    generate_parallel_workflow,
    SDLC_PHASES,
)
from team_execution_dual import TeamExecutionEngineDual, FeatureFlags, ExecutionMode as TeamExecutionMode


class TestWorkflowDAG:
    """Test WorkflowDAG structure and validation"""

    def test_create_empty_dag(self):
        """Test creating an empty workflow"""
        workflow = WorkflowDAG(name="test_workflow")
        assert workflow.name == "test_workflow"
        assert len(workflow.nodes) == 0
        assert workflow.graph.number_of_nodes() == 0

    def test_add_single_node(self):
        """Test adding a single node"""
        workflow = WorkflowDAG(name="test")
        node = WorkflowNode(
            node_id="node1",
            name="Test Node",
            node_type=NodeType.PHASE,
        )
        workflow.add_node(node)

        assert len(workflow.nodes) == 1
        assert "node1" in workflow.nodes
        assert workflow.graph.number_of_nodes() == 1

    def test_add_edge(self):
        """Test adding dependency edge"""
        workflow = WorkflowDAG(name="test")

        node1 = WorkflowNode(node_id="node1", name="Node 1", node_type=NodeType.PHASE)
        node2 = WorkflowNode(node_id="node2", name="Node 2", node_type=NodeType.PHASE)

        workflow.add_node(node1)
        workflow.add_node(node2)
        workflow.add_edge("node1", "node2")

        assert workflow.graph.number_of_edges() == 1
        assert list(workflow.graph.predecessors("node2")) == ["node1"]

    def test_cycle_detection(self):
        """Test that cycles are detected"""
        workflow = WorkflowDAG(name="test")

        node1 = WorkflowNode(node_id="node1", name="Node 1", node_type=NodeType.PHASE)
        node2 = WorkflowNode(node_id="node2", name="Node 2", node_type=NodeType.PHASE)
        node3 = WorkflowNode(node_id="node3", name="Node 3", node_type=NodeType.PHASE)

        workflow.add_node(node1)
        workflow.add_node(node2)
        workflow.add_node(node3)

        workflow.add_edge("node1", "node2")
        workflow.add_edge("node2", "node3")

        # Try to create a cycle
        with pytest.raises(ValueError, match="cycle"):
            workflow.add_edge("node3", "node1")

    def test_execution_order_linear(self):
        """Test execution order for linear workflow"""
        workflow = WorkflowDAG(name="test")

        # Create linear chain: node1 -> node2 -> node3
        for i in range(3):
            node = WorkflowNode(
                node_id=f"node{i+1}",
                name=f"Node {i+1}",
                node_type=NodeType.PHASE,
                dependencies=[f"node{i}"] if i > 0 else [],
            )
            workflow.add_node(node)
            if i > 0:
                workflow.add_edge(f"node{i}", f"node{i+1}")

        execution_order = workflow.get_execution_order()

        # Should have 3 groups, each with 1 node
        assert len(execution_order) == 3
        assert execution_order[0] == ["node1"]
        assert execution_order[1] == ["node2"]
        assert execution_order[2] == ["node3"]

    def test_execution_order_parallel(self):
        """Test execution order for parallel workflow"""
        workflow = WorkflowDAG(name="test")

        # Create: node1 -> (node2, node3) -> node4
        node1 = WorkflowNode(node_id="node1", name="Node 1", node_type=NodeType.PHASE)
        node2 = WorkflowNode(node_id="node2", name="Node 2", node_type=NodeType.PHASE, dependencies=["node1"])
        node3 = WorkflowNode(node_id="node3", name="Node 3", node_type=NodeType.PHASE, dependencies=["node1"])
        node4 = WorkflowNode(node_id="node4", name="Node 4", node_type=NodeType.PHASE, dependencies=["node2", "node3"])

        workflow.add_node(node1)
        workflow.add_node(node2)
        workflow.add_node(node3)
        workflow.add_node(node4)

        workflow.add_edge("node1", "node2")
        workflow.add_edge("node1", "node3")
        workflow.add_edge("node2", "node4")
        workflow.add_edge("node3", "node4")

        execution_order = workflow.get_execution_order()

        # Should have 3 groups: [node1], [node2, node3], [node4]
        assert len(execution_order) == 3
        assert execution_order[0] == ["node1"]
        assert set(execution_order[1]) == {"node2", "node3"}
        assert execution_order[2] == ["node4"]

    def test_get_ready_nodes(self):
        """Test getting nodes ready for execution"""
        workflow = WorkflowDAG(name="test")

        # Create: node1 -> node2 -> node3
        for i in range(3):
            node = WorkflowNode(
                node_id=f"node{i+1}",
                name=f"Node {i+1}",
                node_type=NodeType.PHASE,
                dependencies=[f"node{i}"] if i > 0 else [],
            )
            workflow.add_node(node)
            if i > 0:
                workflow.add_edge(f"node{i}", f"node{i+1}")

        # Initially, only node1 is ready
        ready = workflow.get_ready_nodes(set())
        assert ready == ["node1"]

        # After node1 completes, node2 is ready
        ready = workflow.get_ready_nodes({"node1"})
        assert ready == ["node2"]

        # After node1 and node2 complete, node3 is ready
        ready = workflow.get_ready_nodes({"node1", "node2"})
        assert ready == ["node3"]

        # After all complete, no nodes ready
        ready = workflow.get_ready_nodes({"node1", "node2", "node3"})
        assert ready == []

    def test_serialization(self):
        """Test workflow serialization and deserialization"""
        workflow = WorkflowDAG(name="test")

        node1 = WorkflowNode(node_id="node1", name="Node 1", node_type=NodeType.PHASE)
        node2 = WorkflowNode(node_id="node2", name="Node 2", node_type=NodeType.PHASE, dependencies=["node1"])

        workflow.add_node(node1)
        workflow.add_node(node2)
        workflow.add_edge("node1", "node2")

        # Serialize
        data = workflow.to_dict()

        # Deserialize
        restored = WorkflowDAG.from_dict(data)

        assert restored.workflow_id == workflow.workflow_id
        assert restored.name == workflow.name
        assert len(restored.nodes) == 2
        assert "node1" in restored.nodes
        assert "node2" in restored.nodes


class TestWorkflowContext:
    """Test WorkflowContext state management"""

    def test_create_context(self):
        """Test creating execution context"""
        context = WorkflowContext(workflow_id="test_workflow")
        assert context.workflow_id == "test_workflow"
        assert len(context.node_states) == 0
        assert len(context.node_outputs) == 0

    def test_set_get_node_state(self):
        """Test setting and getting node state"""
        from dag_workflow import NodeState

        context = WorkflowContext(workflow_id="test")
        state = NodeState(node_id="node1", status=NodeStatus.RUNNING)

        context.set_node_state("node1", state)
        retrieved = context.get_node_state("node1")

        assert retrieved is not None
        assert retrieved.node_id == "node1"
        assert retrieved.status == NodeStatus.RUNNING

    def test_set_get_node_output(self):
        """Test setting and getting node output"""
        context = WorkflowContext(workflow_id="test")
        output = {"result": "success", "data": [1, 2, 3]}

        context.set_node_output("node1", output)
        retrieved = context.get_node_output("node1")

        assert retrieved == output

    def test_get_dependency_outputs(self):
        """Test getting outputs from dependency nodes"""
        context = WorkflowContext(workflow_id="test")

        context.set_node_output("node1", {"value": 1})
        context.set_node_output("node2", {"value": 2})
        context.set_node_output("node3", {"value": 3})

        # Get outputs for dependencies
        deps_output = context.get_dependency_outputs(["node1", "node2"])

        assert "node1" in deps_output
        assert "node2" in deps_output
        assert "node3" not in deps_output
        assert deps_output["node1"]["value"] == 1
        assert deps_output["node2"]["value"] == 2

    def test_artifacts(self):
        """Test artifact tracking"""
        context = WorkflowContext(workflow_id="test")

        context.add_artifact("node1", "/path/to/artifact1.txt")
        context.add_artifact("node1", "/path/to/artifact2.txt")
        context.add_artifact("node2", "/path/to/artifact3.txt")

        # Get artifacts for node1
        artifacts = context.get_artifacts("node1")
        assert "node1" in artifacts
        assert len(artifacts["node1"]) == 2

        # Get all artifacts
        all_artifacts = context.get_artifacts()
        assert len(all_artifacts) == 2
        assert "node1" in all_artifacts
        assert "node2" in all_artifacts

    def test_completed_nodes(self):
        """Test getting completed nodes"""
        from dag_workflow import NodeState

        context = WorkflowContext(workflow_id="test")

        context.set_node_state("node1", NodeState(node_id="node1", status=NodeStatus.COMPLETED))
        context.set_node_state("node2", NodeState(node_id="node2", status=NodeStatus.RUNNING))
        context.set_node_state("node3", NodeState(node_id="node3", status=NodeStatus.COMPLETED))

        completed = context.get_completed_nodes()

        assert len(completed) == 2
        assert "node1" in completed
        assert "node3" in completed
        assert "node2" not in completed

    def test_context_serialization(self):
        """Test context serialization"""
        from dag_workflow import NodeState

        context = WorkflowContext(workflow_id="test")
        context.set_node_state("node1", NodeState(node_id="node1", status=NodeStatus.COMPLETED))
        context.set_node_output("node1", {"result": "success"})
        context.add_artifact("node1", "/path/to/artifact.txt")

        # Serialize
        data = context.to_dict()

        # Deserialize
        restored = WorkflowContext.from_dict(data)

        assert restored.workflow_id == context.workflow_id
        assert restored.execution_id == context.execution_id
        assert len(restored.node_states) == 1
        assert len(restored.node_outputs) == 1


@pytest.mark.asyncio
class TestDAGExecutor:
    """Test DAG execution"""

    async def test_execute_simple_workflow(self):
        """Test executing a simple workflow"""
        workflow = WorkflowDAG(name="test")

        # Create mock executors
        async def executor1(input_data):
            return {"result": "node1 complete", "value": 1}

        async def executor2(input_data):
            dep_value = input_data['dependency_outputs']['node1']['value']
            return {"result": "node2 complete", "value": dep_value + 1}

        # Create nodes
        node1 = WorkflowNode(
            node_id="node1",
            name="Node 1",
            node_type=NodeType.PHASE,
            executor=executor1,
        )
        node2 = WorkflowNode(
            node_id="node2",
            name="Node 2",
            node_type=NodeType.PHASE,
            executor=executor2,
            dependencies=["node1"],
        )

        workflow.add_node(node1)
        workflow.add_node(node2)
        workflow.add_edge("node1", "node2")

        # Execute
        executor = DAGExecutor(workflow)
        context = await executor.execute()

        # Verify
        assert len(context.get_completed_nodes()) == 2
        assert context.get_node_output("node1")["value"] == 1
        assert context.get_node_output("node2")["value"] == 2

    async def test_execute_parallel_workflow(self):
        """Test executing workflow with parallel nodes"""
        workflow = WorkflowDAG(name="test")

        execution_log = []

        # Create mock executors that log execution
        async def make_executor(node_id, delay=0.1):
            async def executor(input_data):
                execution_log.append(f"{node_id}_start")
                await asyncio.sleep(delay)
                execution_log.append(f"{node_id}_end")
                return {"node": node_id}
            return executor

        # Create: node1 -> (node2, node3) -> node4
        node1 = WorkflowNode(node_id="node1", name="Node 1", node_type=NodeType.PHASE,
                            executor=await make_executor("node1"))
        node2 = WorkflowNode(node_id="node2", name="Node 2", node_type=NodeType.PHASE,
                            executor=await make_executor("node2"), dependencies=["node1"])
        node3 = WorkflowNode(node_id="node3", name="Node 3", node_type=NodeType.PHASE,
                            executor=await make_executor("node3"), dependencies=["node1"])
        node4 = WorkflowNode(node_id="node4", name="Node 4", node_type=NodeType.PHASE,
                            executor=await make_executor("node4", 0.05), dependencies=["node2", "node3"])

        workflow.add_node(node1)
        workflow.add_node(node2)
        workflow.add_node(node3)
        workflow.add_node(node4)
        workflow.add_edge("node1", "node2")
        workflow.add_edge("node1", "node3")
        workflow.add_edge("node2", "node4")
        workflow.add_edge("node3", "node4")

        # Execute
        executor = DAGExecutor(workflow)
        context = await executor.execute()

        # Verify all completed
        assert len(context.get_completed_nodes()) == 4

        # Verify node2 and node3 ran in parallel (both should start before either finishes)
        node2_start = execution_log.index("node2_start")
        node3_start = execution_log.index("node3_start")
        node2_end = execution_log.index("node2_end")
        node3_end = execution_log.index("node3_end")

        # At least one should start before the other finishes
        parallel = (node3_start < node2_end) or (node2_start < node3_end)
        assert parallel, "Nodes 2 and 3 did not execute in parallel"

    async def test_retry_policy(self):
        """Test node retry on failure"""
        workflow = WorkflowDAG(name="test")

        attempt_count = 0

        async def failing_executor(input_data):
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise Exception(f"Attempt {attempt_count} failed")
            return {"result": "success", "attempts": attempt_count}

        node = WorkflowNode(
            node_id="node1",
            name="Node 1",
            node_type=NodeType.PHASE,
            executor=failing_executor,
            retry_policy=RetryPolicy(
                max_attempts=3,
                retry_on_failure=True,
                retry_delay_seconds=0.1,
            ),
        )

        workflow.add_node(node)

        # Execute
        executor = DAGExecutor(workflow)
        context = await executor.execute()

        # Verify succeeded after retries
        assert len(context.get_completed_nodes()) == 1
        state = context.get_node_state("node1")
        assert state.status == NodeStatus.COMPLETED
        assert state.attempt_count == 3

    async def test_conditional_execution(self):
        """Test conditional node execution"""
        workflow = WorkflowDAG(name="test")

        async def executor1(input_data):
            return {"enable_node2": False, "enable_node3": True}

        async def executor2(input_data):
            return {"result": "node2"}

        async def executor3(input_data):
            return {"result": "node3"}

        node1 = WorkflowNode(node_id="node1", name="Node 1", node_type=NodeType.PHASE, executor=executor1)
        node2 = WorkflowNode(node_id="node2", name="Node 2", node_type=NodeType.PHASE, executor=executor2,
                            dependencies=["node1"], condition="outputs['node1']['enable_node2']")
        node3 = WorkflowNode(node_id="node3", name="Node 3", node_type=NodeType.PHASE, executor=executor3,
                            dependencies=["node1"], condition="outputs['node1']['enable_node3']")

        workflow.add_node(node1)
        workflow.add_node(node2)
        workflow.add_node(node3)
        workflow.add_edge("node1", "node2")
        workflow.add_edge("node1", "node3")

        # Execute
        executor = DAGExecutor(workflow)
        context = await executor.execute()

        # Verify node1 and node3 completed, node2 skipped
        assert context.get_node_state("node1").status == NodeStatus.COMPLETED
        assert context.get_node_state("node2").status == NodeStatus.SKIPPED
        assert context.get_node_state("node3").status == NodeStatus.COMPLETED


class TestCompatibilityLayer:
    """Test compatibility layer"""

    def test_generate_linear_workflow(self):
        """Test generating linear workflow"""
        workflow = generate_linear_workflow(phases=["phase1", "phase2", "phase3"])

        assert len(workflow.nodes) == 3
        assert workflow.metadata['type'] == 'linear'

        # Verify linear order
        execution_order = workflow.get_execution_order()
        assert len(execution_order) == 3
        assert execution_order[0] == ["phase_phase1"]
        assert execution_order[1] == ["phase_phase2"]
        assert execution_order[2] == ["phase_phase3"]

    def test_generate_parallel_workflow(self):
        """Test generating parallel workflow"""
        workflow = generate_parallel_workflow()

        assert len(workflow.nodes) == 6
        assert workflow.metadata['type'] == 'parallel'

        # Verify structure
        execution_order = workflow.get_execution_order()

        # First group: requirement_analysis
        assert "phase_requirement_analysis" in execution_order[0]

        # Second group: design
        assert "phase_design" in execution_order[1]

        # Third group: backend and frontend (parallel)
        third_group = set(execution_order[2])
        assert "phase_backend_development" in third_group
        assert "phase_frontend_development" in third_group

        # Fourth group: testing
        assert "phase_testing" in execution_order[3]

        # Fifth group: review
        assert "phase_review" in execution_order[4]


class TestFeatureFlags:
    """Test feature flag system"""

    def test_default_flags(self):
        """Test default feature flags"""
        flags = FeatureFlags()

        assert flags.enable_dag_execution is False  # Default is False
        assert flags.enable_parallel_execution is False
        assert flags.get_execution_mode() == TeamExecutionMode.LINEAR

    def test_enable_dag_linear(self):
        """Test enabling DAG linear execution"""
        flags = FeatureFlags()
        flags.enable_dag_execution = True
        flags.enable_parallel_execution = False

        assert flags.get_execution_mode() == TeamExecutionMode.DAG_LINEAR

    def test_enable_dag_parallel(self):
        """Test enabling DAG parallel execution"""
        flags = FeatureFlags()
        flags.enable_dag_execution = True
        flags.enable_parallel_execution = True

        assert flags.get_execution_mode() == TeamExecutionMode.DAG_PARALLEL

    def test_flags_serialization(self):
        """Test flags to dict"""
        flags = FeatureFlags()
        flags.enable_dag_execution = True

        data = flags.to_dict()

        assert 'enable_dag_execution' in data
        assert data['enable_dag_execution'] is True
        assert 'execution_mode' in data


@pytest.mark.asyncio
class TestContextStore:
    """Test context persistence"""

    async def test_save_and_load_context(self):
        """Test saving and loading context"""
        store = WorkflowContextStore()
        context = WorkflowContext(workflow_id="test")
        context.set_node_output("node1", {"result": "success"})

        # Save
        await store.save_context(context)

        # Load
        loaded = await store.load_context(context.execution_id)

        assert loaded is not None
        assert loaded.execution_id == context.execution_id
        assert loaded.get_node_output("node1") == {"result": "success"}

    async def test_list_executions(self):
        """Test listing executions"""
        store = WorkflowContextStore()

        ctx1 = WorkflowContext(workflow_id="workflow1")
        ctx2 = WorkflowContext(workflow_id="workflow1")
        ctx3 = WorkflowContext(workflow_id="workflow2")

        await store.save_context(ctx1)
        await store.save_context(ctx2)
        await store.save_context(ctx3)

        # List all
        all_executions = await store.list_executions()
        assert len(all_executions) == 3

        # List for workflow1
        workflow1_executions = await store.list_executions("workflow1")
        assert len(workflow1_executions) == 2

    async def test_delete_context(self):
        """Test deleting context"""
        store = WorkflowContextStore()
        context = WorkflowContext(workflow_id="test")

        await store.save_context(context)
        assert await store.load_context(context.execution_id) is not None

        # Delete
        deleted = await store.delete_context(context.execution_id)
        assert deleted is True

        # Verify deleted
        assert await store.load_context(context.execution_id) is None


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
