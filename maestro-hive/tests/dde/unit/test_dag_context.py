"""
DDE Unit Tests: Workflow Context and State Management

Tests the workflow execution context including:
- Node state tracking
- Output management
- Artifact registration
- Context serialization/deserialization
- State queries

Test IDs: DDE-300 through DDE-350
"""

import pytest
from datetime import datetime
from dag_workflow import (
    WorkflowContext,
    NodeState,
    NodeStatus,
)


@pytest.mark.unit
@pytest.mark.dde
class TestWorkflowContext:
    """Test suite for WorkflowContext functionality"""

    def test_dde_300_create_workflow_context(self):
        """DDE-300: Can create WorkflowContext with workflow_id"""
        context = WorkflowContext(workflow_id="wf-123")

        assert context.workflow_id == "wf-123"
        assert context.execution_id is not None
        assert len(context.node_states) == 0
        assert len(context.node_outputs) == 0

    def test_dde_301_context_with_custom_execution_id(self):
        """DDE-301: Can create context with custom execution_id"""
        context = WorkflowContext(
            workflow_id="wf-123",
            execution_id="exec-456"
        )

        assert context.workflow_id == "wf-123"
        assert context.execution_id == "exec-456"

    def test_dde_302_set_and_get_node_state(self):
        """DDE-302: Can set and retrieve node state"""
        context = WorkflowContext(workflow_id="wf-123")

        state = NodeState(
            node_id="node1",
            status=NodeStatus.RUNNING
        )

        context.set_node_state("node1", state)
        retrieved_state = context.get_node_state("node1")

        assert retrieved_state is not None
        assert retrieved_state.node_id == "node1"
        assert retrieved_state.status == NodeStatus.RUNNING

    def test_dde_303_get_nonexistent_node_state_returns_none(self):
        """DDE-303: Getting non-existent node state returns None"""
        context = WorkflowContext(workflow_id="wf-123")

        state = context.get_node_state("nonexistent")
        assert state is None

    def test_dde_304_set_and_get_node_output(self):
        """DDE-304: Can set and retrieve node output"""
        context = WorkflowContext(workflow_id="wf-123")

        output = {"result": "success", "count": 42}
        context.set_node_output("node1", output)

        retrieved_output = context.get_node_output("node1")
        assert retrieved_output == output
        assert retrieved_output["count"] == 42

    def test_dde_305_get_nonexistent_node_output_returns_none(self):
        """DDE-305: Getting non-existent node output returns None"""
        context = WorkflowContext(workflow_id="wf-123")

        output = context.get_node_output("nonexistent")
        assert output is None

    def test_dde_306_get_all_outputs(self):
        """DDE-306: Can get all node outputs"""
        context = WorkflowContext(workflow_id="wf-123")

        context.set_node_output("node1", {"result": "A"})
        context.set_node_output("node2", {"result": "B"})
        context.set_node_output("node3", {"result": "C"})

        all_outputs = context.get_all_outputs()

        assert len(all_outputs) == 3
        assert all_outputs["node1"]["result"] == "A"
        assert all_outputs["node2"]["result"] == "B"
        assert all_outputs["node3"]["result"] == "C"

    def test_dde_307_get_dependency_outputs(self):
        """DDE-307: Can get outputs for specific dependencies"""
        context = WorkflowContext(workflow_id="wf-123")

        context.set_node_output("dep1", {"value": 10})
        context.set_node_output("dep2", {"value": 20})
        context.set_node_output("other", {"value": 99})

        dep_outputs = context.get_dependency_outputs(["dep1", "dep2"])

        assert len(dep_outputs) == 2
        assert "dep1" in dep_outputs
        assert "dep2" in dep_outputs
        assert "other" not in dep_outputs

    def test_dde_308_add_artifact(self):
        """DDE-308: Can add artifact to node"""
        context = WorkflowContext(workflow_id="wf-123")

        context.add_artifact("node1", "/path/to/artifact1.json")
        context.add_artifact("node1", "/path/to/artifact2.json")

        artifacts = context.get_artifacts("node1")
        assert "node1" in artifacts
        assert len(artifacts["node1"]) == 2

    def test_dde_309_get_artifacts_for_specific_node(self):
        """DDE-309: Can get artifacts for specific node"""
        context = WorkflowContext(workflow_id="wf-123")

        context.add_artifact("node1", "/path/to/artifact1.json")
        context.add_artifact("node2", "/path/to/artifact2.json")

        artifacts = context.get_artifacts("node1")

        assert len(artifacts) == 1
        assert "node1" in artifacts
        assert "node2" not in artifacts

    def test_dde_310_get_all_artifacts(self):
        """DDE-310: Can get all artifacts from all nodes"""
        context = WorkflowContext(workflow_id="wf-123")

        context.add_artifact("node1", "/path/to/artifact1.json")
        context.add_artifact("node2", "/path/to/artifact2.json")
        context.add_artifact("node2", "/path/to/artifact3.json")

        all_artifacts = context.get_artifacts()

        assert len(all_artifacts) == 2  # 2 nodes
        assert len(all_artifacts["node1"]) == 1
        assert len(all_artifacts["node2"]) == 2

    def test_dde_311_get_completed_nodes(self):
        """DDE-311: Can get set of completed node IDs"""
        context = WorkflowContext(workflow_id="wf-123")

        # Add states for various nodes
        context.set_node_state("node1", NodeState(node_id="node1", status=NodeStatus.COMPLETED))
        context.set_node_state("node2", NodeState(node_id="node2", status=NodeStatus.RUNNING))
        context.set_node_state("node3", NodeState(node_id="node3", status=NodeStatus.COMPLETED))
        context.set_node_state("node4", NodeState(node_id="node4", status=NodeStatus.FAILED))

        completed = context.get_completed_nodes()

        assert len(completed) == 2
        assert "node1" in completed
        assert "node3" in completed
        assert "node2" not in completed
        assert "node4" not in completed

    def test_dde_312_global_context_storage(self):
        """DDE-312: Can store and retrieve global context data"""
        context = WorkflowContext(workflow_id="wf-123")

        context.global_context["user"] = "alice@example.com"
        context.global_context["environment"] = "production"
        context.global_context["config"] = {"timeout": 30}

        assert context.global_context["user"] == "alice@example.com"
        assert context.global_context["config"]["timeout"] == 30

    def test_dde_313_context_updated_at_timestamp(self):
        """DDE-313: Context tracks last updated timestamp"""
        context = WorkflowContext(workflow_id="wf-123")

        initial_updated_at = context.updated_at

        # Set node state should update timestamp
        context.set_node_state("node1", NodeState(node_id="node1"))

        assert context.updated_at > initial_updated_at

    def test_dde_314_context_to_dict_serialization(self):
        """DDE-314: Context can be serialized to dictionary"""
        context = WorkflowContext(workflow_id="wf-123", execution_id="exec-456")

        context.set_node_state("node1", NodeState(node_id="node1", status=NodeStatus.COMPLETED))
        context.set_node_output("node1", {"result": "success"})
        context.add_artifact("node1", "/path/to/artifact.json")

        context_dict = context.to_dict()

        assert context_dict["workflow_id"] == "wf-123"
        assert context_dict["execution_id"] == "exec-456"
        assert "node1" in context_dict["node_states"]
        assert "node1" in context_dict["node_outputs"]
        assert "node1" in context_dict["artifacts"]

    def test_dde_315_context_from_dict_deserialization(self):
        """DDE-315: Context can be deserialized from dictionary"""
        # Create original context
        context = WorkflowContext(workflow_id="wf-123", execution_id="exec-456")
        context.set_node_state("node1", NodeState(node_id="node1", status=NodeStatus.COMPLETED))
        context.set_node_output("node1", {"result": "success"})

        # Serialize and deserialize
        context_dict = context.to_dict()
        restored_context = WorkflowContext.from_dict(context_dict)

        assert restored_context.workflow_id == "wf-123"
        assert restored_context.execution_id == "exec-456"
        assert restored_context.get_node_state("node1").status == NodeStatus.COMPLETED
        assert restored_context.get_node_output("node1")["result"] == "success"

    def test_dde_316_context_roundtrip_serialization(self):
        """DDE-316: Context survives roundtrip serialization"""
        context = WorkflowContext(workflow_id="wf-123")

        # Add complex data
        context.set_node_state("node1", NodeState(node_id="node1", status=NodeStatus.COMPLETED))
        context.set_node_state("node2", NodeState(node_id="node2", status=NodeStatus.RUNNING))
        context.set_node_output("node1", {"key": "value", "count": 42})
        context.add_artifact("node1", "/path/artifact1.json")
        context.add_artifact("node1", "/path/artifact2.json")
        context.global_context["env"] = "prod"

        # Roundtrip
        context_dict = context.to_dict()
        restored = WorkflowContext.from_dict(context_dict)

        assert len(restored.node_states) == 2
        assert len(restored.node_outputs) == 1
        assert len(restored.get_artifacts("node1")["node1"]) == 2
        assert restored.global_context["env"] == "prod"


@pytest.mark.unit
@pytest.mark.dde
class TestNodeState:
    """Test suite for NodeState functionality"""

    def test_dde_317_create_node_state_default_values(self):
        """DDE-317: NodeState can be created with default values"""
        state = NodeState(node_id="node1")

        assert state.node_id == "node1"
        assert state.status == NodeStatus.PENDING
        assert state.start_time is None
        assert state.end_time is None
        assert state.attempt_count == 0
        assert state.error_message is None
        assert state.output is None
        assert len(state.artifacts) == 0

    def test_dde_318_node_state_with_custom_values(self):
        """DDE-318: NodeState can be created with custom values"""
        now = datetime.now()
        state = NodeState(
            node_id="node1",
            status=NodeStatus.RUNNING,
            start_time=now,
            attempt_count=2,
            metadata={"key": "value"}
        )

        assert state.status == NodeStatus.RUNNING
        assert state.start_time == now
        assert state.attempt_count == 2
        assert state.metadata["key"] == "value"

    def test_dde_319_node_state_with_error(self):
        """DDE-319: NodeState can store error information"""
        state = NodeState(
            node_id="node1",
            status=NodeStatus.FAILED,
            error_message="Connection timeout"
        )

        assert state.status == NodeStatus.FAILED
        assert state.error_message == "Connection timeout"

    def test_dde_320_node_state_with_output(self):
        """DDE-320: NodeState can store execution output"""
        state = NodeState(
            node_id="node1",
            status=NodeStatus.COMPLETED,
            output={"result": "success", "rows_processed": 1000}
        )

        assert state.output["result"] == "success"
        assert state.output["rows_processed"] == 1000

    def test_dde_321_node_state_with_artifacts(self):
        """DDE-321: NodeState can store artifact paths"""
        state = NodeState(
            node_id="node1",
            status=NodeStatus.COMPLETED,
            artifacts=["/path/file1.json", "/path/file2.json"]
        )

        assert len(state.artifacts) == 2
        assert "/path/file1.json" in state.artifacts

    def test_dde_322_node_state_to_dict_serialization(self):
        """DDE-322: NodeState can be serialized to dictionary"""
        now = datetime.now()
        state = NodeState(
            node_id="node1",
            status=NodeStatus.COMPLETED,
            start_time=now,
            end_time=now,
            attempt_count=1
        )

        state_dict = state.to_dict()

        assert state_dict["node_id"] == "node1"
        assert state_dict["status"] == "completed"
        assert state_dict["attempt_count"] == 1
        assert state_dict["start_time"] is not None

    def test_dde_323_node_state_from_dict_deserialization(self):
        """DDE-323: NodeState can be deserialized from dictionary"""
        now = datetime.now()
        state_dict = {
            "node_id": "node1",
            "status": "completed",
            "start_time": now.isoformat(),
            "end_time": now.isoformat(),
            "attempt_count": 1,
            "error_message": None,
            "output": {"result": "ok"},
            "artifacts": ["/path/file.json"],
            "metadata": {}
        }

        state = NodeState.from_dict(state_dict)

        assert state.node_id == "node1"
        assert state.status == NodeStatus.COMPLETED
        assert state.attempt_count == 1
        assert state.output["result"] == "ok"

    def test_dde_324_node_state_status_enum_values(self):
        """DDE-324: NodeStatus enum has all expected values"""
        assert NodeStatus.PENDING.value == "pending"
        assert NodeStatus.READY.value == "ready"
        assert NodeStatus.RUNNING.value == "running"
        assert NodeStatus.COMPLETED.value == "completed"
        assert NodeStatus.FAILED.value == "failed"
        assert NodeStatus.SKIPPED.value == "skipped"
        assert NodeStatus.BLOCKED.value == "blocked"

    def test_dde_325_node_state_track_execution_time(self):
        """DDE-325: NodeState can track execution duration"""
        start = datetime.now()
        import time
        time.sleep(0.01)  # Small delay
        end = datetime.now()

        state = NodeState(
            node_id="node1",
            status=NodeStatus.COMPLETED,
            start_time=start,
            end_time=end
        )

        duration = (state.end_time - state.start_time).total_seconds()
        assert duration > 0

    def test_dde_326_node_state_metadata_storage(self):
        """DDE-326: NodeState metadata can store arbitrary data"""
        state = NodeState(node_id="node1")

        state.metadata["assigned_agent"] = "agent-123"
        state.metadata["priority"] = "high"
        state.metadata["tags"] = ["backend", "python"]
        state.metadata["config"] = {"timeout": 300}

        assert state.metadata["assigned_agent"] == "agent-123"
        assert "python" in state.metadata["tags"]
        assert state.metadata["config"]["timeout"] == 300

    def test_dde_327_node_state_roundtrip_serialization(self):
        """DDE-327: NodeState survives roundtrip serialization"""
        now = datetime.now()
        state = NodeState(
            node_id="node1",
            status=NodeStatus.COMPLETED,
            start_time=now,
            end_time=now,
            attempt_count=3,
            error_message=None,
            output={"result": "success"},
            artifacts=["/path/file.json"],
            metadata={"key": "value"}
        )

        # Roundtrip
        state_dict = state.to_dict()
        restored = NodeState.from_dict(state_dict)

        assert restored.node_id == "node1"
        assert restored.status == NodeStatus.COMPLETED
        assert restored.attempt_count == 3
        assert restored.output["result"] == "success"
        assert len(restored.artifacts) == 1
        assert restored.metadata["key"] == "value"


@pytest.mark.unit
@pytest.mark.dde
class TestContextQueries:
    """Test suite for context query operations"""

    def test_dde_328_filter_nodes_by_status(self):
        """DDE-328: Can filter nodes by status"""
        context = WorkflowContext(workflow_id="wf-123")

        context.set_node_state("node1", NodeState(node_id="node1", status=NodeStatus.COMPLETED))
        context.set_node_state("node2", NodeState(node_id="node2", status=NodeStatus.RUNNING))
        context.set_node_state("node3", NodeState(node_id="node3", status=NodeStatus.COMPLETED))
        context.set_node_state("node4", NodeState(node_id="node4", status=NodeStatus.FAILED))

        # Get completed nodes
        completed = [node_id for node_id, state in context.node_states.items()
                    if state.status == NodeStatus.COMPLETED]

        assert len(completed) == 2
        assert "node1" in completed
        assert "node3" in completed

    def test_dde_329_get_failed_nodes(self):
        """DDE-329: Can identify failed nodes"""
        context = WorkflowContext(workflow_id="wf-123")

        context.set_node_state("node1", NodeState(node_id="node1", status=NodeStatus.COMPLETED))
        context.set_node_state("node2", NodeState(node_id="node2", status=NodeStatus.FAILED))
        context.set_node_state("node3", NodeState(node_id="node3", status=NodeStatus.FAILED))

        failed = [node_id for node_id, state in context.node_states.items()
                 if state.status == NodeStatus.FAILED]

        assert len(failed) == 2
        assert "node2" in failed
        assert "node3" in failed

    def test_dde_330_get_running_nodes(self):
        """DDE-330: Can identify currently running nodes"""
        context = WorkflowContext(workflow_id="wf-123")

        context.set_node_state("node1", NodeState(node_id="node1", status=NodeStatus.COMPLETED))
        context.set_node_state("node2", NodeState(node_id="node2", status=NodeStatus.RUNNING))
        context.set_node_state("node3", NodeState(node_id="node3", status=NodeStatus.RUNNING))

        running = [node_id for node_id, state in context.node_states.items()
                  if state.status == NodeStatus.RUNNING]

        assert len(running) == 2

    def test_dde_331_check_if_workflow_complete(self):
        """DDE-331: Can check if all nodes are complete"""
        context = WorkflowContext(workflow_id="wf-123")

        context.set_node_state("node1", NodeState(node_id="node1", status=NodeStatus.COMPLETED))
        context.set_node_state("node2", NodeState(node_id="node2", status=NodeStatus.COMPLETED))
        context.set_node_state("node3", NodeState(node_id="node3", status=NodeStatus.COMPLETED))

        all_complete = all(state.status == NodeStatus.COMPLETED
                          for state in context.node_states.values())

        assert all_complete is True

    def test_dde_332_check_if_any_node_failed(self):
        """DDE-332: Can check if any node has failed"""
        context = WorkflowContext(workflow_id="wf-123")

        context.set_node_state("node1", NodeState(node_id="node1", status=NodeStatus.COMPLETED))
        context.set_node_state("node2", NodeState(node_id="node2", status=NodeStatus.FAILED))

        any_failed = any(state.status == NodeStatus.FAILED
                        for state in context.node_states.values())

        assert any_failed is True

    def test_dde_333_count_nodes_by_status(self):
        """DDE-333: Can count nodes by status"""
        context = WorkflowContext(workflow_id="wf-123")

        context.set_node_state("node1", NodeState(node_id="node1", status=NodeStatus.COMPLETED))
        context.set_node_state("node2", NodeState(node_id="node2", status=NodeStatus.COMPLETED))
        context.set_node_state("node3", NodeState(node_id="node3", status=NodeStatus.RUNNING))
        context.set_node_state("node4", NodeState(node_id="node4", status=NodeStatus.FAILED))

        status_counts = {}
        for state in context.node_states.values():
            status_counts[state.status] = status_counts.get(state.status, 0) + 1

        assert status_counts[NodeStatus.COMPLETED] == 2
        assert status_counts[NodeStatus.RUNNING] == 1
        assert status_counts[NodeStatus.FAILED] == 1

    def test_dde_334_get_nodes_with_errors(self):
        """DDE-334: Can get all nodes with error messages"""
        context = WorkflowContext(workflow_id="wf-123")

        context.set_node_state("node1", NodeState(node_id="node1", status=NodeStatus.COMPLETED))
        context.set_node_state("node2", NodeState(
            node_id="node2",
            status=NodeStatus.FAILED,
            error_message="Connection timeout"
        ))
        context.set_node_state("node3", NodeState(
            node_id="node3",
            status=NodeStatus.FAILED,
            error_message="Invalid input"
        ))

        nodes_with_errors = {node_id: state.error_message
                            for node_id, state in context.node_states.items()
                            if state.error_message is not None}

        assert len(nodes_with_errors) == 2
        assert "Connection timeout" in nodes_with_errors.values()

    def test_dde_335_calculate_workflow_progress(self):
        """DDE-335: Can calculate workflow progress percentage"""
        context = WorkflowContext(workflow_id="wf-123")

        total_nodes = 10
        for i in range(total_nodes):
            status = NodeStatus.COMPLETED if i < 7 else NodeStatus.PENDING
            context.set_node_state(f"node{i}", NodeState(node_id=f"node{i}", status=status))

        completed_count = sum(1 for state in context.node_states.values()
                             if state.status == NodeStatus.COMPLETED)
        progress = (completed_count / total_nodes) * 100

        assert progress == 70.0
