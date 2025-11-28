"""
DDE Unit Tests: DAG Constraints and Validation

Tests the constraint validation logic for workflow DAGs including:
- Cycle detection
- Dependency validation
- Node capability requirements
- Execution mode constraints
- Conditional execution rules

Test IDs: DDE-200 through DDE-250
"""

import pytest
from dag_workflow import (
    WorkflowDAG,
    WorkflowNode,
    NodeType,
    ExecutionMode,
    RetryPolicy,
)


@pytest.mark.unit
@pytest.mark.dde
class TestDAGConstraints:
    """Test suite for DAG constraint validation"""

    def test_dde_200_empty_dag_validation(self):
        """DDE-200: Empty DAG should be valid but disconnected"""
        dag = WorkflowDAG(name="empty_workflow")

        # Empty DAG is technically valid from structure perspective
        # but will have no nodes to execute
        assert len(dag.nodes) == 0
        assert len(dag.graph.nodes()) == 0

    def test_dde_201_single_node_dag_validation(self):
        """DDE-201: Single node DAG is valid"""
        dag = WorkflowDAG(name="single_node_workflow")

        node = WorkflowNode(
            node_id="node1",
            name="Single Node",
            node_type=NodeType.ACTION
        )

        dag.add_node(node)
        errors = dag.validate()

        assert len(errors) == 0, f"Single node DAG should be valid, got errors: {errors}"

    def test_dde_202_simple_chain_validation(self):
        """DDE-202: Simple chain A -> B -> C is valid"""
        dag = WorkflowDAG(name="simple_chain")

        nodes = [
            WorkflowNode(node_id="A", name="Node A", node_type=NodeType.ACTION),
            WorkflowNode(node_id="B", name="Node B", node_type=NodeType.ACTION, dependencies=["A"]),
            WorkflowNode(node_id="C", name="Node C", node_type=NodeType.ACTION, dependencies=["B"]),
        ]

        for node in nodes:
            dag.add_node(node)

        dag.add_edge("A", "B")
        dag.add_edge("B", "C")

        errors = dag.validate()
        assert len(errors) == 0, f"Simple chain should be valid, got errors: {errors}"

    def test_dde_203_detect_cycle_two_nodes(self):
        """DDE-203: Detect cycle in two-node graph A <-> B"""
        dag = WorkflowDAG(name="cycle_two_nodes")

        node_a = WorkflowNode(node_id="A", name="Node A", node_type=NodeType.ACTION)
        node_b = WorkflowNode(node_id="B", name="Node B", node_type=NodeType.ACTION)

        dag.add_node(node_a)
        dag.add_node(node_b)
        dag.add_edge("A", "B")

        # Attempting to add reverse edge should raise ValueError
        with pytest.raises(ValueError, match="would create a cycle"):
            dag.add_edge("B", "A")

    def test_dde_204_detect_cycle_three_nodes(self):
        """DDE-204: Detect cycle in three-node graph A -> B -> C -> A"""
        dag = WorkflowDAG(name="cycle_three_nodes")

        nodes = [
            WorkflowNode(node_id="A", name="Node A", node_type=NodeType.ACTION),
            WorkflowNode(node_id="B", name="Node B", node_type=NodeType.ACTION),
            WorkflowNode(node_id="C", name="Node C", node_type=NodeType.ACTION),
        ]

        for node in nodes:
            dag.add_node(node)

        dag.add_edge("A", "B")
        dag.add_edge("B", "C")

        # Attempting to close the cycle should raise ValueError
        with pytest.raises(ValueError, match="would create a cycle"):
            dag.add_edge("C", "A")

    def test_dde_205_detect_self_loop(self):
        """DDE-205: Detect self-loop A -> A"""
        dag = WorkflowDAG(name="self_loop")

        node = WorkflowNode(node_id="A", name="Node A", node_type=NodeType.ACTION)
        dag.add_node(node)

        # Self-loop should be rejected
        with pytest.raises(ValueError, match="would create a cycle"):
            dag.add_edge("A", "A")

    def test_dde_206_diamond_dependency_valid(self):
        """DDE-206: Diamond dependency pattern is valid (A -> B,C -> D)"""
        dag = WorkflowDAG(name="diamond")

        nodes = [
            WorkflowNode(node_id="A", name="Node A", node_type=NodeType.ACTION),
            WorkflowNode(node_id="B", name="Node B", node_type=NodeType.ACTION, dependencies=["A"]),
            WorkflowNode(node_id="C", name="Node C", node_type=NodeType.ACTION, dependencies=["A"]),
            WorkflowNode(node_id="D", name="Node D", node_type=NodeType.ACTION, dependencies=["B", "C"]),
        ]

        for node in nodes:
            dag.add_node(node)

        dag.add_edge("A", "B")
        dag.add_edge("A", "C")
        dag.add_edge("B", "D")
        dag.add_edge("C", "D")

        errors = dag.validate()
        assert len(errors) == 0, f"Diamond pattern should be valid, got errors: {errors}"

    def test_dde_207_nonexistent_dependency_detected(self):
        """DDE-207: Detect dependency on non-existent node"""
        dag = WorkflowDAG(name="missing_dep")

        node = WorkflowNode(
            node_id="A",
            name="Node A",
            node_type=NodeType.ACTION,
            dependencies=["NonExistent"]
        )

        dag.add_node(node)

        errors = dag.validate()
        assert len(errors) > 0, "Should detect non-existent dependency"
        assert any("non-existent" in err.lower() for err in errors)

    def test_dde_208_duplicate_node_rejected(self):
        """DDE-208: Adding duplicate node_id should raise error"""
        dag = WorkflowDAG(name="duplicate_node")

        node1 = WorkflowNode(node_id="A", name="Node A", node_type=NodeType.ACTION)
        node2 = WorkflowNode(node_id="A", name="Node A Duplicate", node_type=NodeType.ACTION)

        dag.add_node(node1)

        with pytest.raises(ValueError, match="already exists"):
            dag.add_node(node2)

    def test_dde_209_edge_to_nonexistent_node_rejected(self):
        """DDE-209: Adding edge to non-existent node should raise error"""
        dag = WorkflowDAG(name="missing_node_edge")

        node = WorkflowNode(node_id="A", name="Node A", node_type=NodeType.ACTION)
        dag.add_node(node)

        # Edge to non-existent target
        with pytest.raises(ValueError, match="not found"):
            dag.add_edge("A", "NonExistent")

    def test_dde_210_edge_from_nonexistent_node_rejected(self):
        """DDE-210: Adding edge from non-existent node should raise error"""
        dag = WorkflowDAG(name="missing_node_edge")

        node = WorkflowNode(node_id="B", name="Node B", node_type=NodeType.ACTION)
        dag.add_node(node)

        # Edge from non-existent source
        with pytest.raises(ValueError, match="not found"):
            dag.add_edge("NonExistent", "B")

    def test_dde_211_disconnected_components_detected(self):
        """DDE-211: Detect disconnected workflow components"""
        dag = WorkflowDAG(name="disconnected")

        # Component 1: A -> B
        node_a = WorkflowNode(node_id="A", name="Node A", node_type=NodeType.ACTION)
        node_b = WorkflowNode(node_id="B", name="Node B", node_type=NodeType.ACTION, dependencies=["A"])

        # Component 2: C -> D (disconnected from A-B)
        node_c = WorkflowNode(node_id="C", name="Node C", node_type=NodeType.ACTION)
        node_d = WorkflowNode(node_id="D", name="Node D", node_type=NodeType.ACTION, dependencies=["C"])

        dag.add_node(node_a)
        dag.add_node(node_b)
        dag.add_node(node_c)
        dag.add_node(node_d)

        dag.add_edge("A", "B")
        dag.add_edge("C", "D")

        errors = dag.validate()
        assert len(errors) > 0, "Should detect disconnected components"
        assert any("disconnected" in err.lower() for err in errors)

    def test_dde_212_multiple_root_nodes_valid(self):
        """DDE-212: Multiple root nodes (no dependencies) are valid if connected"""
        dag = WorkflowDAG(name="multiple_roots")

        # Two roots converging to single node
        nodes = [
            WorkflowNode(node_id="A", name="Root A", node_type=NodeType.ACTION),
            WorkflowNode(node_id="B", name="Root B", node_type=NodeType.ACTION),
            WorkflowNode(node_id="C", name="Converge", node_type=NodeType.ACTION, dependencies=["A", "B"]),
        ]

        for node in nodes:
            dag.add_node(node)

        dag.add_edge("A", "C")
        dag.add_edge("B", "C")

        errors = dag.validate()
        assert len(errors) == 0, f"Multiple roots should be valid if connected, got errors: {errors}"

    def test_dde_213_complex_dag_100_nodes_valid(self):
        """DDE-213: Complex DAG with 100 nodes in layers is valid"""
        dag = WorkflowDAG(name="complex_100_nodes")

        # Create 5 layers of 20 nodes each
        layer_size = 20
        num_layers = 5

        for layer in range(num_layers):
            for i in range(layer_size):
                node_id = f"L{layer}_N{i}"
                deps = []

                # Connect to 2 nodes from previous layer
                if layer > 0:
                    deps = [f"L{layer-1}_N{i % layer_size}", f"L{layer-1}_N{(i+1) % layer_size}"]

                node = WorkflowNode(
                    node_id=node_id,
                    name=f"Layer {layer} Node {i}",
                    node_type=NodeType.ACTION,
                    dependencies=deps
                )
                dag.add_node(node)

                # Add edges
                for dep in deps:
                    dag.add_edge(dep, node_id)

        errors = dag.validate()
        assert len(errors) == 0, f"Complex 100-node DAG should be valid, got errors: {errors}"
        assert len(dag.nodes) == 100

    def test_dde_214_get_dependencies_correct(self):
        """DDE-214: get_dependencies returns correct predecessors"""
        dag = WorkflowDAG(name="test_deps")

        nodes = [
            WorkflowNode(node_id="A", name="Node A", node_type=NodeType.ACTION),
            WorkflowNode(node_id="B", name="Node B", node_type=NodeType.ACTION),
            WorkflowNode(node_id="C", name="Node C", node_type=NodeType.ACTION, dependencies=["A", "B"]),
        ]

        for node in nodes:
            dag.add_node(node)

        dag.add_edge("A", "C")
        dag.add_edge("B", "C")

        deps = dag.get_dependencies("C")
        assert set(deps) == {"A", "B"}

    def test_dde_215_get_dependents_correct(self):
        """DDE-215: get_dependents returns correct successors"""
        dag = WorkflowDAG(name="test_dependents")

        nodes = [
            WorkflowNode(node_id="A", name="Node A", node_type=NodeType.ACTION),
            WorkflowNode(node_id="B", name="Node B", node_type=NodeType.ACTION, dependencies=["A"]),
            WorkflowNode(node_id="C", name="Node C", node_type=NodeType.ACTION, dependencies=["A"]),
        ]

        for node in nodes:
            dag.add_node(node)

        dag.add_edge("A", "B")
        dag.add_edge("A", "C")

        dependents = dag.get_dependents("A")
        assert set(dependents) == {"B", "C"}

    def test_dde_216_get_ready_nodes_initial_state(self):
        """DDE-216: get_ready_nodes returns root nodes initially"""
        dag = WorkflowDAG(name="test_ready")

        nodes = [
            WorkflowNode(node_id="A", name="Node A", node_type=NodeType.ACTION),
            WorkflowNode(node_id="B", name="Node B", node_type=NodeType.ACTION, dependencies=["A"]),
            WorkflowNode(node_id="C", name="Node C", node_type=NodeType.ACTION, dependencies=["A"]),
        ]

        for node in nodes:
            dag.add_node(node)

        dag.add_edge("A", "B")
        dag.add_edge("A", "C")

        ready = dag.get_ready_nodes(completed_nodes=set())
        assert ready == ["A"]

    def test_dde_217_get_ready_nodes_after_completion(self):
        """DDE-217: get_ready_nodes updates after nodes complete"""
        dag = WorkflowDAG(name="test_ready_update")

        nodes = [
            WorkflowNode(node_id="A", name="Node A", node_type=NodeType.ACTION),
            WorkflowNode(node_id="B", name="Node B", node_type=NodeType.ACTION, dependencies=["A"]),
            WorkflowNode(node_id="C", name="Node C", node_type=NodeType.ACTION, dependencies=["A", "B"]),
        ]

        for node in nodes:
            dag.add_node(node)

        dag.add_edge("A", "B")
        dag.add_edge("A", "C")
        dag.add_edge("B", "C")

        # After A completes, B should be ready
        ready = dag.get_ready_nodes(completed_nodes={"A"})
        assert ready == ["B"]

        # After A and B complete, C should be ready
        ready = dag.get_ready_nodes(completed_nodes={"A", "B"})
        assert ready == ["C"]

    def test_dde_218_retry_policy_defaults(self):
        """DDE-218: RetryPolicy has correct defaults"""
        policy = RetryPolicy()

        assert policy.max_attempts == 1
        assert policy.retry_delay_seconds == 0
        assert policy.retry_on_failure is False
        assert policy.exponential_backoff is False

    def test_dde_219_retry_policy_custom_values(self):
        """DDE-219: RetryPolicy accepts custom values"""
        policy = RetryPolicy(
            max_attempts=5,
            retry_delay_seconds=10,
            retry_on_failure=True,
            exponential_backoff=True
        )

        assert policy.max_attempts == 5
        assert policy.retry_delay_seconds == 10
        assert policy.retry_on_failure is True
        assert policy.exponential_backoff is True

    def test_dde_220_node_with_capability_requirement(self):
        """DDE-220: Node can specify capability requirement"""
        node = WorkflowNode(
            node_id="impl_node",
            name="Implementation Node",
            node_type=NodeType.ACTION,
            capability="Backend:Python:FastAPI"
        )

        assert node.capability == "Backend:Python:FastAPI"

    def test_dde_221_interface_node_with_contract_version(self):
        """DDE-221: Interface node can specify contract version"""
        node = WorkflowNode(
            node_id="IF.Auth",
            name="Auth Interface",
            node_type=NodeType.INTERFACE,
            contract_version="v1.2.0"
        )

        assert node.node_type == NodeType.INTERFACE
        assert node.contract_version == "v1.2.0"

    def test_dde_222_node_with_quality_gates(self):
        """DDE-222: Node can specify quality gates"""
        node = WorkflowNode(
            node_id="test_node",
            name="Test Node",
            node_type=NodeType.ACTION,
            gates=["coverage>90%", "security_scan_passed"]
        )

        assert len(node.gates) == 2
        assert "coverage>90%" in node.gates

    def test_dde_223_node_with_estimated_effort(self):
        """DDE-223: Node can specify estimated effort in minutes"""
        node = WorkflowNode(
            node_id="complex_task",
            name="Complex Task",
            node_type=NodeType.ACTION,
            estimated_effort=45
        )

        assert node.estimated_effort == 45

    def test_dde_224_node_with_expected_outputs(self):
        """DDE-224: Node can specify expected output artifacts"""
        node = WorkflowNode(
            node_id="design_node",
            name="Design Phase",
            node_type=NodeType.PHASE,
            outputs=["api_spec.yaml", "architecture_diagram.png", "README.md"]
        )

        assert len(node.outputs) == 3
        assert "api_spec.yaml" in node.outputs

    def test_dde_225_conditional_node_with_expression(self):
        """DDE-225: Conditional node can specify execution condition"""
        node = WorkflowNode(
            node_id="conditional_deploy",
            name="Conditional Deployment",
            node_type=NodeType.CONDITIONAL,
            condition="outputs['tests']['passed'] == True"
        )

        assert node.node_type == NodeType.CONDITIONAL
        assert node.condition is not None

    def test_dde_226_parallel_execution_mode(self):
        """DDE-226: Node can specify parallel execution mode"""
        node = WorkflowNode(
            node_id="parallel_task",
            name="Parallel Task",
            node_type=NodeType.PARALLEL_GROUP,
            execution_mode=ExecutionMode.PARALLEL
        )

        assert node.execution_mode == ExecutionMode.PARALLEL

    def test_dde_227_sequential_execution_mode_default(self):
        """DDE-227: Sequential is default execution mode"""
        node = WorkflowNode(
            node_id="task",
            name="Task",
            node_type=NodeType.ACTION
        )

        assert node.execution_mode == ExecutionMode.SEQUENTIAL

    def test_dde_228_human_review_checkpoint_node(self):
        """DDE-228: Human review checkpoint node type"""
        node = WorkflowNode(
            node_id="review_checkpoint",
            name="Code Review",
            node_type=NodeType.HUMAN_REVIEW,
            config={"reviewers": ["alice@example.com", "bob@example.com"]}
        )

        assert node.node_type == NodeType.HUMAN_REVIEW
        assert "reviewers" in node.config

    def test_dde_229_notification_node_type(self):
        """DDE-229: Notification node type for alerts"""
        node = WorkflowNode(
            node_id="notify_slack",
            name="Slack Notification",
            node_type=NodeType.NOTIFICATION,
            config={"channel": "#deployments", "message": "Deployment complete"}
        )

        assert node.node_type == NodeType.NOTIFICATION

    def test_dde_230_checkpoint_node_type(self):
        """DDE-230: Checkpoint node for validation gates"""
        node = WorkflowNode(
            node_id="quality_checkpoint",
            name="Quality Gate Checkpoint",
            node_type=NodeType.CHECKPOINT,
            gates=["test_coverage>85%", "no_critical_bugs"]
        )

        assert node.node_type == NodeType.CHECKPOINT
        assert len(node.gates) == 2


@pytest.mark.unit
@pytest.mark.dde
class TestDAGSerializat:
    """Test suite for DAG serialization and deserialization"""

    def test_dde_231_dag_to_dict_serialization(self):
        """DDE-231: DAG can be serialized to dictionary"""
        dag = WorkflowDAG(workflow_id="test-123", name="test_workflow")

        node = WorkflowNode(node_id="A", name="Node A", node_type=NodeType.ACTION)
        dag.add_node(node)

        dag_dict = dag.to_dict()

        assert dag_dict["workflow_id"] == "test-123"
        assert dag_dict["name"] == "test_workflow"
        assert "A" in dag_dict["nodes"]
        assert "created_at" in dag_dict

    def test_dde_232_dag_from_dict_deserialization(self):
        """DDE-232: DAG can be deserialized from dictionary"""
        dag = WorkflowDAG(workflow_id="test-456", name="test_workflow")

        node = WorkflowNode(node_id="A", name="Node A", node_type=NodeType.ACTION)
        dag.add_node(node)

        # Serialize and deserialize
        dag_dict = dag.to_dict()
        restored_dag = WorkflowDAG.from_dict(dag_dict)

        assert restored_dag.workflow_id == "test-456"
        assert restored_dag.name == "test_workflow"
        assert "A" in restored_dag.nodes

    def test_dde_233_node_to_dict_serialization(self):
        """DDE-233: WorkflowNode can be serialized to dictionary"""
        node = WorkflowNode(
            node_id="test_node",
            name="Test Node",
            node_type=NodeType.ACTION,
            dependencies=["dep1", "dep2"],
            capability="Backend:Python"
        )

        node_dict = node.to_dict()

        assert node_dict["node_id"] == "test_node"
        assert node_dict["name"] == "Test Node"
        assert node_dict["node_type"] == "action"
        assert node_dict["dependencies"] == ["dep1", "dep2"]
        assert node_dict["capability"] == "Backend:Python"

    def test_dde_234_node_from_dict_deserialization(self):
        """DDE-234: WorkflowNode can be deserialized from dictionary"""
        node_dict = {
            "node_id": "test_node",
            "name": "Test Node",
            "node_type": "action",
            "dependencies": ["dep1"],
            "execution_mode": "sequential",
            "retry_policy": {
                "max_attempts": 3,
                "retry_delay_seconds": 5,
                "retry_on_failure": True,
                "exponential_backoff": False
            },
            "config": {},
            "metadata": {},
            "capability": None,
            "gates": [],
            "estimated_effort": None,
            "contract_version": None,
            "outputs": [],
            "condition": None,
            "executor": None
        }

        node = WorkflowNode.from_dict(node_dict)

        assert node.node_id == "test_node"
        assert node.name == "Test Node"
        assert node.node_type == NodeType.ACTION
        assert node.retry_policy.max_attempts == 3

    def test_dde_235_dag_roundtrip_serialization(self):
        """DDE-235: DAG survives roundtrip serialization"""
        # Create complex DAG
        dag = WorkflowDAG(name="roundtrip_test")

        nodes = [
            WorkflowNode(node_id="A", name="Node A", node_type=NodeType.INTERFACE),
            WorkflowNode(node_id="B", name="Node B", node_type=NodeType.ACTION, dependencies=["A"]),
            WorkflowNode(node_id="C", name="Node C", node_type=NodeType.ACTION, dependencies=["A"]),
            WorkflowNode(node_id="D", name="Node D", node_type=NodeType.CHECKPOINT, dependencies=["B", "C"]),
        ]

        for node in nodes:
            dag.add_node(node)

        dag.add_edge("A", "B")
        dag.add_edge("A", "C")
        dag.add_edge("B", "D")
        dag.add_edge("C", "D")

        # Roundtrip
        dag_dict = dag.to_dict()
        restored_dag = WorkflowDAG.from_dict(dag_dict)

        # Verify structure preserved
        assert len(restored_dag.nodes) == 4
        assert set(restored_dag.get_dependencies("D")) == {"B", "C"}
        assert restored_dag.nodes["A"].node_type == NodeType.INTERFACE

        # Verify still valid
        errors = restored_dag.validate()
        assert len(errors) == 0


@pytest.mark.unit
@pytest.mark.dde
class TestDAGComplexScenarios:
    """Test suite for complex DAG scenarios"""

    def test_dde_236_wide_dag_100_parallel_nodes(self):
        """DDE-236: DAG with 100 nodes that can execute in parallel"""
        dag = WorkflowDAG(name="wide_dag")

        # Create root node
        root = WorkflowNode(node_id="root", name="Root", node_type=NodeType.ACTION)
        dag.add_node(root)

        # Create 100 nodes all depending on root
        for i in range(100):
            node = WorkflowNode(
                node_id=f"parallel_{i}",
                name=f"Parallel Node {i}",
                node_type=NodeType.ACTION,
                dependencies=["root"]
            )
            dag.add_node(node)
            dag.add_edge("root", f"parallel_{i}")

        errors = dag.validate()
        assert len(errors) == 0

        # All 100 nodes should be ready after root completes
        ready = dag.get_ready_nodes(completed_nodes={"root"})
        assert len(ready) == 100

    def test_dde_237_deep_dag_100_sequential_nodes(self):
        """DDE-237: DAG with 100 nodes in sequential chain"""
        dag = WorkflowDAG(name="deep_dag")

        # Create chain of 100 nodes
        prev_id = None
        for i in range(100):
            node_id = f"seq_{i}"
            deps = [prev_id] if prev_id else []

            node = WorkflowNode(
                node_id=node_id,
                name=f"Sequential Node {i}",
                node_type=NodeType.ACTION,
                dependencies=deps
            )
            dag.add_node(node)

            if prev_id:
                dag.add_edge(prev_id, node_id)

            prev_id = node_id

        errors = dag.validate()
        assert len(errors) == 0

        # Should have 100 execution groups (fully sequential)
        execution_order = dag.get_execution_order()
        assert len(execution_order) == 100

    def test_dde_238_binary_tree_dag_structure(self):
        """DDE-238: DAG with binary tree structure (7 nodes, 3 levels)"""
        dag = WorkflowDAG(name="binary_tree")

        # Level 0: root
        # Level 1: 2 nodes
        # Level 2: 4 nodes

        dag.add_node(WorkflowNode(node_id="root", name="Root", node_type=NodeType.ACTION))

        # Level 1
        dag.add_node(WorkflowNode(node_id="L1_left", name="L1 Left", node_type=NodeType.ACTION, dependencies=["root"]))
        dag.add_node(WorkflowNode(node_id="L1_right", name="L1 Right", node_type=NodeType.ACTION, dependencies=["root"]))
        dag.add_edge("root", "L1_left")
        dag.add_edge("root", "L1_right")

        # Level 2
        for parent in ["L1_left", "L1_right"]:
            for side in ["left", "right"]:
                node_id = f"{parent}_{side}"
                dag.add_node(WorkflowNode(node_id=node_id, name=node_id, node_type=NodeType.ACTION, dependencies=[parent]))
                dag.add_edge(parent, node_id)

        errors = dag.validate()
        assert len(errors) == 0
        assert len(dag.nodes) == 7

    def test_dde_239_mixed_node_types_workflow(self):
        """DDE-239: Workflow with all node types mixed"""
        dag = WorkflowDAG(name="mixed_types")

        nodes = [
            WorkflowNode(node_id="IF.API", name="API Interface", node_type=NodeType.INTERFACE),
            WorkflowNode(node_id="impl", name="Implementation", node_type=NodeType.ACTION, dependencies=["IF.API"]),
            WorkflowNode(node_id="test", name="Tests", node_type=NodeType.ACTION, dependencies=["impl"]),
            WorkflowNode(node_id="checkpoint", name="Quality Gate", node_type=NodeType.CHECKPOINT, dependencies=["test"]),
            WorkflowNode(node_id="review", name="Code Review", node_type=NodeType.HUMAN_REVIEW, dependencies=["checkpoint"]),
            WorkflowNode(node_id="deploy_check", name="Deploy Decision", node_type=NodeType.CONDITIONAL,
                        dependencies=["review"], condition="outputs['review']['approved'] == True"),
            WorkflowNode(node_id="notify", name="Notify Team", node_type=NodeType.NOTIFICATION, dependencies=["deploy_check"]),
        ]

        for node in nodes:
            dag.add_node(node)

        # Add edges
        for node in nodes:
            for dep in node.dependencies:
                dag.add_edge(dep, node.node_id)

        errors = dag.validate()
        assert len(errors) == 0
        assert len([n for n in nodes if n.node_type == NodeType.INTERFACE]) == 1

    def test_dde_240_execution_order_respects_dependencies(self):
        """DDE-240: get_execution_order respects all dependencies"""
        dag = WorkflowDAG(name="execution_order_test")

        # A -> B -> D
        # A -> C -> D
        nodes = [
            WorkflowNode(node_id="A", name="A", node_type=NodeType.ACTION),
            WorkflowNode(node_id="B", name="B", node_type=NodeType.ACTION, dependencies=["A"]),
            WorkflowNode(node_id="C", name="C", node_type=NodeType.ACTION, dependencies=["A"]),
            WorkflowNode(node_id="D", name="D", node_type=NodeType.ACTION, dependencies=["B", "C"]),
        ]

        for node in nodes:
            dag.add_node(node)

        dag.add_edge("A", "B")
        dag.add_edge("A", "C")
        dag.add_edge("B", "D")
        dag.add_edge("C", "D")

        execution_order = dag.get_execution_order()

        # Should be 3 groups: [A], [B, C], [D]
        assert len(execution_order) == 3
        assert execution_order[0] == ["A"]
        assert set(execution_order[1]) == {"B", "C"}
        assert execution_order[2] == ["D"]
