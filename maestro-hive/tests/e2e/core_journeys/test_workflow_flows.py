"""
Workflow E2E Tests.

EPIC: MD-3034 - Core User Journey E2E Tests
Tests workflow creation, execution, DAG builder, and real-time progress tracking.
"""

import pytest
import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from unittest.mock import AsyncMock, MagicMock, patch


class WorkflowStatus(Enum):
    """Workflow execution status."""
    DRAFT = "draft"
    CONFIGURED = "configured"
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class NodeType(Enum):
    """DAG node types."""
    START = "start"
    END = "end"
    TASK = "task"
    DECISION = "decision"
    PARALLEL = "parallel"
    JOIN = "join"
    SUBPROCESS = "subprocess"


@dataclass
class DAGNode:
    """Represents a node in the workflow DAG."""
    id: str
    type: NodeType
    name: str
    config: Dict[str, Any] = field(default_factory=dict)
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    status: str = "pending"
    result: Optional[Dict[str, Any]] = None


@dataclass
class DAGEdge:
    """Represents an edge connecting DAG nodes."""
    id: str
    source_id: str
    target_id: str
    condition: Optional[str] = None
    label: Optional[str] = None


class WorkflowSimulator:
    """Simulates workflow operations for E2E testing."""

    def __init__(self):
        self.workflows: Dict[str, Dict[str, Any]] = {}
        self.executions: Dict[str, Dict[str, Any]] = {}
        self.progress_callbacks: Dict[str, List[callable]] = {}

    async def create_workflow(
        self,
        name: str,
        description: str = "",
        template_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new workflow."""
        workflow_id = f"wf_{uuid.uuid4().hex[:12]}"

        workflow = {
            "id": workflow_id,
            "name": name,
            "description": description,
            "template_id": template_id,
            "status": WorkflowStatus.DRAFT.value,
            "nodes": [],
            "edges": [],
            "config": {},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "version": 1
        }

        self.workflows[workflow_id] = workflow
        return workflow

    async def configure_workflow(
        self,
        workflow_id: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Configure workflow settings."""
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow {workflow_id} not found")

        workflow = self.workflows[workflow_id]
        workflow["config"].update(config)
        workflow["status"] = WorkflowStatus.CONFIGURED.value
        workflow["updated_at"] = datetime.utcnow().isoformat()

        return workflow

    async def add_node(
        self,
        workflow_id: str,
        node: DAGNode
    ) -> Dict[str, Any]:
        """Add a node to the workflow DAG."""
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow {workflow_id} not found")

        workflow = self.workflows[workflow_id]
        node_dict = {
            "id": node.id,
            "type": node.type.value,
            "name": node.name,
            "config": node.config,
            "inputs": node.inputs,
            "outputs": node.outputs
        }
        workflow["nodes"].append(node_dict)
        workflow["updated_at"] = datetime.utcnow().isoformat()

        return node_dict

    async def add_edge(
        self,
        workflow_id: str,
        edge: DAGEdge
    ) -> Dict[str, Any]:
        """Add an edge connecting nodes."""
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow {workflow_id} not found")

        workflow = self.workflows[workflow_id]

        # Validate source and target nodes exist
        node_ids = {n["id"] for n in workflow["nodes"]}
        if edge.source_id not in node_ids:
            raise ValueError(f"Source node {edge.source_id} not found")
        if edge.target_id not in node_ids:
            raise ValueError(f"Target node {edge.target_id} not found")

        edge_dict = {
            "id": edge.id,
            "source_id": edge.source_id,
            "target_id": edge.target_id,
            "condition": edge.condition,
            "label": edge.label
        }
        workflow["edges"].append(edge_dict)
        workflow["updated_at"] = datetime.utcnow().isoformat()

        return edge_dict

    async def validate_dag(self, workflow_id: str) -> Dict[str, Any]:
        """Validate the DAG structure."""
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow {workflow_id} not found")

        workflow = self.workflows[workflow_id]
        validation = {
            "valid": True,
            "errors": [],
            "warnings": []
        }

        nodes = workflow["nodes"]
        edges = workflow["edges"]

        # Check for start node
        start_nodes = [n for n in nodes if n["type"] == NodeType.START.value]
        if len(start_nodes) == 0:
            validation["errors"].append("No START node found")
            validation["valid"] = False
        elif len(start_nodes) > 1:
            validation["errors"].append("Multiple START nodes found")
            validation["valid"] = False

        # Check for end node
        end_nodes = [n for n in nodes if n["type"] == NodeType.END.value]
        if len(end_nodes) == 0:
            validation["errors"].append("No END node found")
            validation["valid"] = False

        # Check for cycles (simplified)
        # In production, would use topological sort
        if len(edges) > len(nodes) * 2:
            validation["warnings"].append("Possible cycle detected")

        # Check all nodes are connected
        connected_nodes = set()
        for edge in edges:
            connected_nodes.add(edge["source_id"])
            connected_nodes.add(edge["target_id"])

        orphan_nodes = set(n["id"] for n in nodes) - connected_nodes
        if orphan_nodes and len(nodes) > 1:
            validation["warnings"].append(f"Orphan nodes detected: {orphan_nodes}")

        return validation

    async def execute_workflow(
        self,
        workflow_id: str,
        inputs: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Start workflow execution."""
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow {workflow_id} not found")

        # Validate DAG first
        validation = await self.validate_dag(workflow_id)
        if not validation["valid"]:
            raise ValueError(f"Invalid DAG: {validation['errors']}")

        execution_id = f"exec_{uuid.uuid4().hex[:12]}"
        workflow = self.workflows[workflow_id]

        execution = {
            "id": execution_id,
            "workflow_id": workflow_id,
            "status": WorkflowStatus.RUNNING.value,
            "inputs": inputs or {},
            "outputs": {},
            "node_states": {n["id"]: "pending" for n in workflow["nodes"]},
            "progress": 0,
            "started_at": datetime.utcnow().isoformat(),
            "completed_at": None,
            "error": None
        }

        self.executions[execution_id] = execution

        # Simulate execution in background
        asyncio.create_task(self._run_execution(execution_id))

        return execution

    async def _run_execution(self, execution_id: str):
        """Simulate workflow execution."""
        execution = self.executions[execution_id]
        workflow = self.workflows[execution["workflow_id"]]

        total_nodes = len(workflow["nodes"])
        completed = 0

        for node in workflow["nodes"]:
            # Simulate node execution
            await asyncio.sleep(0.1)  # Simulate work

            execution["node_states"][node["id"]] = "completed"
            completed += 1
            execution["progress"] = int((completed / total_nodes) * 100)

            # Notify progress callbacks
            await self._notify_progress(execution_id, {
                "type": "node_completed",
                "node_id": node["id"],
                "progress": execution["progress"]
            })

        execution["status"] = WorkflowStatus.COMPLETED.value
        execution["completed_at"] = datetime.utcnow().isoformat()
        execution["progress"] = 100

        await self._notify_progress(execution_id, {
            "type": "execution_completed",
            "progress": 100
        })

    async def _notify_progress(self, execution_id: str, event: Dict[str, Any]):
        """Notify registered progress callbacks."""
        if execution_id in self.progress_callbacks:
            for callback in self.progress_callbacks[execution_id]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event)
                    else:
                        callback(event)
                except Exception:
                    pass

    def subscribe_progress(self, execution_id: str, callback: callable):
        """Subscribe to execution progress updates."""
        if execution_id not in self.progress_callbacks:
            self.progress_callbacks[execution_id] = []
        self.progress_callbacks[execution_id].append(callback)

    async def get_execution_status(self, execution_id: str) -> Dict[str, Any]:
        """Get current execution status."""
        if execution_id not in self.executions:
            raise ValueError(f"Execution {execution_id} not found")
        return self.executions[execution_id]

    async def pause_execution(self, execution_id: str) -> Dict[str, Any]:
        """Pause a running execution."""
        if execution_id not in self.executions:
            raise ValueError(f"Execution {execution_id} not found")

        execution = self.executions[execution_id]
        if execution["status"] != WorkflowStatus.RUNNING.value:
            raise ValueError(f"Cannot pause execution in {execution['status']} state")

        execution["status"] = WorkflowStatus.PAUSED.value
        return execution

    async def resume_execution(self, execution_id: str) -> Dict[str, Any]:
        """Resume a paused execution."""
        if execution_id not in self.executions:
            raise ValueError(f"Execution {execution_id} not found")

        execution = self.executions[execution_id]
        if execution["status"] != WorkflowStatus.PAUSED.value:
            raise ValueError(f"Cannot resume execution in {execution['status']} state")

        execution["status"] = WorkflowStatus.RUNNING.value
        return execution

    async def cancel_execution(self, execution_id: str) -> Dict[str, Any]:
        """Cancel a running or paused execution."""
        if execution_id not in self.executions:
            raise ValueError(f"Execution {execution_id} not found")

        execution = self.executions[execution_id]
        if execution["status"] in [WorkflowStatus.COMPLETED.value, WorkflowStatus.CANCELLED.value]:
            raise ValueError(f"Cannot cancel execution in {execution['status']} state")

        execution["status"] = WorkflowStatus.CANCELLED.value
        execution["completed_at"] = datetime.utcnow().isoformat()
        return execution


class WebSocketSimulator:
    """Simulates WebSocket connections for real-time progress tracking."""

    def __init__(self):
        self.connections: Dict[str, List[Dict[str, Any]]] = {}
        self.message_history: Dict[str, List[Dict[str, Any]]] = {}

    async def connect(self, execution_id: str) -> str:
        """Establish WebSocket connection."""
        connection_id = f"ws_{uuid.uuid4().hex[:8]}"

        if execution_id not in self.connections:
            self.connections[execution_id] = []
            self.message_history[execution_id] = []

        self.connections[execution_id].append({
            "id": connection_id,
            "connected_at": datetime.utcnow().isoformat()
        })

        return connection_id

    async def disconnect(self, execution_id: str, connection_id: str):
        """Close WebSocket connection."""
        if execution_id in self.connections:
            self.connections[execution_id] = [
                c for c in self.connections[execution_id]
                if c["id"] != connection_id
            ]

    async def send_message(
        self,
        execution_id: str,
        message: Dict[str, Any]
    ):
        """Send message to all connected clients."""
        if execution_id not in self.message_history:
            self.message_history[execution_id] = []

        message["timestamp"] = datetime.utcnow().isoformat()
        self.message_history[execution_id].append(message)

    def get_messages(self, execution_id: str) -> List[Dict[str, Any]]:
        """Get all messages for an execution."""
        return self.message_history.get(execution_id, [])


class TestWorkflowCreationExecution:
    """E2E tests for workflow create -> configure -> execute -> complete flow."""

    @pytest.fixture
    def workflow_sim(self):
        return WorkflowSimulator()

    @pytest.mark.asyncio
    async def test_complete_workflow_lifecycle(self, workflow_sim):
        """Test full workflow lifecycle: create -> configure -> execute -> complete."""
        # Step 1: Create workflow
        workflow = await workflow_sim.create_workflow(
            name="Data Processing Pipeline",
            description="Process and transform data"
        )
        assert workflow["status"] == WorkflowStatus.DRAFT.value
        assert workflow["id"].startswith("wf_")

        # Step 2: Add nodes
        start_node = DAGNode(
            id="start_1",
            type=NodeType.START,
            name="Start"
        )
        await workflow_sim.add_node(workflow["id"], start_node)

        task_node = DAGNode(
            id="task_1",
            type=NodeType.TASK,
            name="Process Data",
            config={"processor": "transformer_v1"}
        )
        await workflow_sim.add_node(workflow["id"], task_node)

        end_node = DAGNode(
            id="end_1",
            type=NodeType.END,
            name="End"
        )
        await workflow_sim.add_node(workflow["id"], end_node)

        # Step 3: Connect nodes
        await workflow_sim.add_edge(workflow["id"], DAGEdge(
            id="edge_1",
            source_id="start_1",
            target_id="task_1"
        ))
        await workflow_sim.add_edge(workflow["id"], DAGEdge(
            id="edge_2",
            source_id="task_1",
            target_id="end_1"
        ))

        # Step 4: Configure workflow
        workflow = await workflow_sim.configure_workflow(
            workflow["id"],
            {"timeout": 3600, "retry_count": 3}
        )
        assert workflow["status"] == WorkflowStatus.CONFIGURED.value

        # Step 5: Validate DAG
        validation = await workflow_sim.validate_dag(workflow["id"])
        assert validation["valid"] is True
        assert len(validation["errors"]) == 0

        # Step 6: Execute workflow
        execution = await workflow_sim.execute_workflow(
            workflow["id"],
            inputs={"data_source": "s3://bucket/data"}
        )
        assert execution["status"] == WorkflowStatus.RUNNING.value

        # Step 7: Wait for completion
        await asyncio.sleep(0.5)

        final_status = await workflow_sim.get_execution_status(execution["id"])
        assert final_status["status"] == WorkflowStatus.COMPLETED.value
        assert final_status["progress"] == 100

    @pytest.mark.asyncio
    async def test_workflow_from_template(self, workflow_sim):
        """Test creating workflow from template."""
        workflow = await workflow_sim.create_workflow(
            name="ML Training Pipeline",
            description="Train ML model",
            template_id="ml_training_v2"
        )

        assert workflow["template_id"] == "ml_training_v2"
        assert workflow["status"] == WorkflowStatus.DRAFT.value

    @pytest.mark.asyncio
    async def test_workflow_configuration_updates(self, workflow_sim):
        """Test updating workflow configuration."""
        workflow = await workflow_sim.create_workflow(name="Test Workflow")

        # First configuration
        workflow = await workflow_sim.configure_workflow(
            workflow["id"],
            {"timeout": 1800}
        )
        assert workflow["config"]["timeout"] == 1800

        # Update configuration
        workflow = await workflow_sim.configure_workflow(
            workflow["id"],
            {"retry_count": 5, "notify_on_failure": True}
        )
        assert workflow["config"]["timeout"] == 1800  # Preserved
        assert workflow["config"]["retry_count"] == 5  # Added
        assert workflow["config"]["notify_on_failure"] is True  # Added

    @pytest.mark.asyncio
    async def test_execution_with_inputs_outputs(self, workflow_sim):
        """Test workflow execution with inputs and outputs."""
        workflow = await workflow_sim.create_workflow(name="IO Workflow")

        # Add minimal valid DAG
        await workflow_sim.add_node(workflow["id"], DAGNode(
            id="start", type=NodeType.START, name="Start"
        ))
        await workflow_sim.add_node(workflow["id"], DAGNode(
            id="end", type=NodeType.END, name="End"
        ))
        await workflow_sim.add_edge(workflow["id"], DAGEdge(
            id="e1", source_id="start", target_id="end"
        ))

        execution = await workflow_sim.execute_workflow(
            workflow["id"],
            inputs={"param1": "value1", "param2": 42}
        )

        assert execution["inputs"]["param1"] == "value1"
        assert execution["inputs"]["param2"] == 42

    @pytest.mark.asyncio
    async def test_execution_pause_resume(self, workflow_sim):
        """Test pausing and resuming workflow execution."""
        workflow = await workflow_sim.create_workflow(name="Pausable Workflow")

        await workflow_sim.add_node(workflow["id"], DAGNode(
            id="start", type=NodeType.START, name="Start"
        ))
        await workflow_sim.add_node(workflow["id"], DAGNode(
            id="end", type=NodeType.END, name="End"
        ))
        await workflow_sim.add_edge(workflow["id"], DAGEdge(
            id="e1", source_id="start", target_id="end"
        ))

        execution = await workflow_sim.execute_workflow(workflow["id"])

        # Pause execution
        paused = await workflow_sim.pause_execution(execution["id"])
        assert paused["status"] == WorkflowStatus.PAUSED.value

        # Resume execution
        resumed = await workflow_sim.resume_execution(execution["id"])
        assert resumed["status"] == WorkflowStatus.RUNNING.value

    @pytest.mark.asyncio
    async def test_execution_cancellation(self, workflow_sim):
        """Test cancelling workflow execution."""
        workflow = await workflow_sim.create_workflow(name="Cancellable Workflow")

        await workflow_sim.add_node(workflow["id"], DAGNode(
            id="start", type=NodeType.START, name="Start"
        ))
        await workflow_sim.add_node(workflow["id"], DAGNode(
            id="end", type=NodeType.END, name="End"
        ))
        await workflow_sim.add_edge(workflow["id"], DAGEdge(
            id="e1", source_id="start", target_id="end"
        ))

        execution = await workflow_sim.execute_workflow(workflow["id"])

        # Cancel execution
        cancelled = await workflow_sim.cancel_execution(execution["id"])
        assert cancelled["status"] == WorkflowStatus.CANCELLED.value
        assert cancelled["completed_at"] is not None


class TestDAGBuilder:
    """E2E tests for DAG builder with node connections."""

    @pytest.fixture
    def workflow_sim(self):
        return WorkflowSimulator()

    @pytest.mark.asyncio
    async def test_build_linear_dag(self, workflow_sim):
        """Test building a linear DAG (start -> task1 -> task2 -> end)."""
        workflow = await workflow_sim.create_workflow(name="Linear DAG")

        # Add nodes
        nodes = [
            DAGNode(id="start", type=NodeType.START, name="Start"),
            DAGNode(id="task1", type=NodeType.TASK, name="Task 1"),
            DAGNode(id="task2", type=NodeType.TASK, name="Task 2"),
            DAGNode(id="end", type=NodeType.END, name="End")
        ]

        for node in nodes:
            await workflow_sim.add_node(workflow["id"], node)

        # Add edges
        edges = [
            DAGEdge(id="e1", source_id="start", target_id="task1"),
            DAGEdge(id="e2", source_id="task1", target_id="task2"),
            DAGEdge(id="e3", source_id="task2", target_id="end")
        ]

        for edge in edges:
            await workflow_sim.add_edge(workflow["id"], edge)

        validation = await workflow_sim.validate_dag(workflow["id"])
        assert validation["valid"] is True

    @pytest.mark.asyncio
    async def test_build_parallel_dag(self, workflow_sim):
        """Test building a parallel DAG with fork and join."""
        workflow = await workflow_sim.create_workflow(name="Parallel DAG")

        # Add nodes
        nodes = [
            DAGNode(id="start", type=NodeType.START, name="Start"),
            DAGNode(id="parallel", type=NodeType.PARALLEL, name="Fork"),
            DAGNode(id="task_a", type=NodeType.TASK, name="Task A"),
            DAGNode(id="task_b", type=NodeType.TASK, name="Task B"),
            DAGNode(id="join", type=NodeType.JOIN, name="Join"),
            DAGNode(id="end", type=NodeType.END, name="End")
        ]

        for node in nodes:
            await workflow_sim.add_node(workflow["id"], node)

        # Add edges
        edges = [
            DAGEdge(id="e1", source_id="start", target_id="parallel"),
            DAGEdge(id="e2", source_id="parallel", target_id="task_a"),
            DAGEdge(id="e3", source_id="parallel", target_id="task_b"),
            DAGEdge(id="e4", source_id="task_a", target_id="join"),
            DAGEdge(id="e5", source_id="task_b", target_id="join"),
            DAGEdge(id="e6", source_id="join", target_id="end")
        ]

        for edge in edges:
            await workflow_sim.add_edge(workflow["id"], edge)

        validation = await workflow_sim.validate_dag(workflow["id"])
        assert validation["valid"] is True

    @pytest.mark.asyncio
    async def test_build_decision_dag(self, workflow_sim):
        """Test building a DAG with decision branches."""
        workflow = await workflow_sim.create_workflow(name="Decision DAG")

        # Add nodes
        nodes = [
            DAGNode(id="start", type=NodeType.START, name="Start"),
            DAGNode(id="decision", type=NodeType.DECISION, name="Check Condition"),
            DAGNode(id="task_yes", type=NodeType.TASK, name="Yes Branch"),
            DAGNode(id="task_no", type=NodeType.TASK, name="No Branch"),
            DAGNode(id="end", type=NodeType.END, name="End")
        ]

        for node in nodes:
            await workflow_sim.add_node(workflow["id"], node)

        # Add edges with conditions
        edges = [
            DAGEdge(id="e1", source_id="start", target_id="decision"),
            DAGEdge(id="e2", source_id="decision", target_id="task_yes",
                   condition="result == true", label="Yes"),
            DAGEdge(id="e3", source_id="decision", target_id="task_no",
                   condition="result == false", label="No"),
            DAGEdge(id="e4", source_id="task_yes", target_id="end"),
            DAGEdge(id="e5", source_id="task_no", target_id="end")
        ]

        for edge in edges:
            await workflow_sim.add_edge(workflow["id"], edge)

        validation = await workflow_sim.validate_dag(workflow["id"])
        assert validation["valid"] is True

    @pytest.mark.asyncio
    async def test_dag_validation_no_start_node(self, workflow_sim):
        """Test DAG validation fails without start node."""
        workflow = await workflow_sim.create_workflow(name="Invalid DAG")

        # Add only task and end nodes (no start)
        await workflow_sim.add_node(workflow["id"], DAGNode(
            id="task", type=NodeType.TASK, name="Task"
        ))
        await workflow_sim.add_node(workflow["id"], DAGNode(
            id="end", type=NodeType.END, name="End"
        ))
        await workflow_sim.add_edge(workflow["id"], DAGEdge(
            id="e1", source_id="task", target_id="end"
        ))

        validation = await workflow_sim.validate_dag(workflow["id"])
        assert validation["valid"] is False
        assert any("START" in err for err in validation["errors"])

    @pytest.mark.asyncio
    async def test_dag_validation_no_end_node(self, workflow_sim):
        """Test DAG validation fails without end node."""
        workflow = await workflow_sim.create_workflow(name="Invalid DAG")

        # Add only start and task nodes (no end)
        await workflow_sim.add_node(workflow["id"], DAGNode(
            id="start", type=NodeType.START, name="Start"
        ))
        await workflow_sim.add_node(workflow["id"], DAGNode(
            id="task", type=NodeType.TASK, name="Task"
        ))
        await workflow_sim.add_edge(workflow["id"], DAGEdge(
            id="e1", source_id="start", target_id="task"
        ))

        validation = await workflow_sim.validate_dag(workflow["id"])
        assert validation["valid"] is False
        assert any("END" in err for err in validation["errors"])

    @pytest.mark.asyncio
    async def test_edge_validation_invalid_source(self, workflow_sim):
        """Test edge creation fails with invalid source node."""
        workflow = await workflow_sim.create_workflow(name="Test")

        await workflow_sim.add_node(workflow["id"], DAGNode(
            id="task", type=NodeType.TASK, name="Task"
        ))

        with pytest.raises(ValueError, match="Source node.*not found"):
            await workflow_sim.add_edge(workflow["id"], DAGEdge(
                id="e1", source_id="nonexistent", target_id="task"
            ))

    @pytest.mark.asyncio
    async def test_edge_validation_invalid_target(self, workflow_sim):
        """Test edge creation fails with invalid target node."""
        workflow = await workflow_sim.create_workflow(name="Test")

        await workflow_sim.add_node(workflow["id"], DAGNode(
            id="task", type=NodeType.TASK, name="Task"
        ))

        with pytest.raises(ValueError, match="Target node.*not found"):
            await workflow_sim.add_edge(workflow["id"], DAGEdge(
                id="e1", source_id="task", target_id="nonexistent"
            ))

    @pytest.mark.asyncio
    async def test_subprocess_node_integration(self, workflow_sim):
        """Test DAG with subprocess nodes."""
        # Create main workflow
        main_workflow = await workflow_sim.create_workflow(name="Main Workflow")

        # Create subprocess workflow
        sub_workflow = await workflow_sim.create_workflow(name="Sub Workflow")
        await workflow_sim.add_node(sub_workflow["id"], DAGNode(
            id="sub_start", type=NodeType.START, name="Sub Start"
        ))
        await workflow_sim.add_node(sub_workflow["id"], DAGNode(
            id="sub_end", type=NodeType.END, name="Sub End"
        ))
        await workflow_sim.add_edge(sub_workflow["id"], DAGEdge(
            id="se1", source_id="sub_start", target_id="sub_end"
        ))

        # Add subprocess node to main workflow
        await workflow_sim.add_node(main_workflow["id"], DAGNode(
            id="start", type=NodeType.START, name="Start"
        ))
        await workflow_sim.add_node(main_workflow["id"], DAGNode(
            id="subprocess", type=NodeType.SUBPROCESS, name="Run Sub",
            config={"workflow_id": sub_workflow["id"]}
        ))
        await workflow_sim.add_node(main_workflow["id"], DAGNode(
            id="end", type=NodeType.END, name="End"
        ))

        await workflow_sim.add_edge(main_workflow["id"], DAGEdge(
            id="e1", source_id="start", target_id="subprocess"
        ))
        await workflow_sim.add_edge(main_workflow["id"], DAGEdge(
            id="e2", source_id="subprocess", target_id="end"
        ))

        validation = await workflow_sim.validate_dag(main_workflow["id"])
        assert validation["valid"] is True


class TestWebSocketProgressTracking:
    """E2E tests for real-time WebSocket progress tracking."""

    @pytest.fixture
    def workflow_sim(self):
        return WorkflowSimulator()

    @pytest.fixture
    def websocket_sim(self):
        return WebSocketSimulator()

    @pytest.mark.asyncio
    async def test_websocket_connection(self, workflow_sim, websocket_sim):
        """Test establishing WebSocket connection."""
        workflow = await workflow_sim.create_workflow(name="WS Test")
        await workflow_sim.add_node(workflow["id"], DAGNode(
            id="start", type=NodeType.START, name="Start"
        ))
        await workflow_sim.add_node(workflow["id"], DAGNode(
            id="end", type=NodeType.END, name="End"
        ))
        await workflow_sim.add_edge(workflow["id"], DAGEdge(
            id="e1", source_id="start", target_id="end"
        ))

        execution = await workflow_sim.execute_workflow(workflow["id"])

        connection_id = await websocket_sim.connect(execution["id"])
        assert connection_id.startswith("ws_")

    @pytest.mark.asyncio
    async def test_progress_messages_received(self, workflow_sim, websocket_sim):
        """Test receiving progress messages via WebSocket."""
        workflow = await workflow_sim.create_workflow(name="Progress Test")

        # Add multiple nodes for progress tracking
        await workflow_sim.add_node(workflow["id"], DAGNode(
            id="start", type=NodeType.START, name="Start"
        ))
        await workflow_sim.add_node(workflow["id"], DAGNode(
            id="task1", type=NodeType.TASK, name="Task 1"
        ))
        await workflow_sim.add_node(workflow["id"], DAGNode(
            id="task2", type=NodeType.TASK, name="Task 2"
        ))
        await workflow_sim.add_node(workflow["id"], DAGNode(
            id="end", type=NodeType.END, name="End"
        ))

        await workflow_sim.add_edge(workflow["id"], DAGEdge(
            id="e1", source_id="start", target_id="task1"
        ))
        await workflow_sim.add_edge(workflow["id"], DAGEdge(
            id="e2", source_id="task1", target_id="task2"
        ))
        await workflow_sim.add_edge(workflow["id"], DAGEdge(
            id="e3", source_id="task2", target_id="end"
        ))

        execution = await workflow_sim.execute_workflow(workflow["id"])

        # Track progress messages
        progress_events = []

        def track_progress(event):
            progress_events.append(event)
            websocket_sim.send_message(execution["id"], event)

        workflow_sim.subscribe_progress(execution["id"], track_progress)

        # Wait for execution to complete
        await asyncio.sleep(0.6)

        # Verify progress events received
        assert len(progress_events) >= 4  # At least one per node

        # Verify final completion event
        completion_events = [e for e in progress_events if e.get("type") == "execution_completed"]
        assert len(completion_events) == 1
        assert completion_events[0]["progress"] == 100

    @pytest.mark.asyncio
    async def test_multiple_websocket_clients(self, workflow_sim, websocket_sim):
        """Test multiple WebSocket clients receiving same progress."""
        workflow = await workflow_sim.create_workflow(name="Multi-Client Test")
        await workflow_sim.add_node(workflow["id"], DAGNode(
            id="start", type=NodeType.START, name="Start"
        ))
        await workflow_sim.add_node(workflow["id"], DAGNode(
            id="end", type=NodeType.END, name="End"
        ))
        await workflow_sim.add_edge(workflow["id"], DAGEdge(
            id="e1", source_id="start", target_id="end"
        ))

        execution = await workflow_sim.execute_workflow(workflow["id"])

        # Connect multiple clients
        client1 = await websocket_sim.connect(execution["id"])
        client2 = await websocket_sim.connect(execution["id"])
        client3 = await websocket_sim.connect(execution["id"])

        assert len(websocket_sim.connections[execution["id"]]) == 3

        # Send a message
        await websocket_sim.send_message(execution["id"], {
            "type": "progress",
            "value": 50
        })

        messages = websocket_sim.get_messages(execution["id"])
        assert len(messages) == 1

    @pytest.mark.asyncio
    async def test_websocket_disconnection(self, workflow_sim, websocket_sim):
        """Test WebSocket client disconnection."""
        workflow = await workflow_sim.create_workflow(name="Disconnect Test")
        await workflow_sim.add_node(workflow["id"], DAGNode(
            id="start", type=NodeType.START, name="Start"
        ))
        await workflow_sim.add_node(workflow["id"], DAGNode(
            id="end", type=NodeType.END, name="End"
        ))
        await workflow_sim.add_edge(workflow["id"], DAGEdge(
            id="e1", source_id="start", target_id="end"
        ))

        execution = await workflow_sim.execute_workflow(workflow["id"])

        connection_id = await websocket_sim.connect(execution["id"])
        assert len(websocket_sim.connections[execution["id"]]) == 1

        await websocket_sim.disconnect(execution["id"], connection_id)
        assert len(websocket_sim.connections[execution["id"]]) == 0

    @pytest.mark.asyncio
    async def test_progress_event_types(self, workflow_sim, websocket_sim):
        """Test different types of progress events."""
        workflow = await workflow_sim.create_workflow(name="Event Types Test")
        await workflow_sim.add_node(workflow["id"], DAGNode(
            id="start", type=NodeType.START, name="Start"
        ))
        await workflow_sim.add_node(workflow["id"], DAGNode(
            id="task", type=NodeType.TASK, name="Task"
        ))
        await workflow_sim.add_node(workflow["id"], DAGNode(
            id="end", type=NodeType.END, name="End"
        ))
        await workflow_sim.add_edge(workflow["id"], DAGEdge(
            id="e1", source_id="start", target_id="task"
        ))
        await workflow_sim.add_edge(workflow["id"], DAGEdge(
            id="e2", source_id="task", target_id="end"
        ))

        execution = await workflow_sim.execute_workflow(workflow["id"])

        events = []
        workflow_sim.subscribe_progress(execution["id"], lambda e: events.append(e))

        await asyncio.sleep(0.5)

        event_types = {e.get("type") for e in events}
        assert "node_completed" in event_types
        assert "execution_completed" in event_types

    @pytest.mark.asyncio
    async def test_message_history_persistence(self, websocket_sim):
        """Test that message history is preserved."""
        execution_id = "test_exec_123"

        await websocket_sim.connect(execution_id)

        # Send multiple messages
        for i in range(5):
            await websocket_sim.send_message(execution_id, {
                "type": "progress",
                "value": i * 20
            })

        messages = websocket_sim.get_messages(execution_id)
        assert len(messages) == 5

        # Verify message ordering and timestamps
        for i, msg in enumerate(messages):
            assert msg["value"] == i * 20
            assert "timestamp" in msg


class TestWorkflowErrorHandling:
    """E2E tests for workflow error handling scenarios."""

    @pytest.fixture
    def workflow_sim(self):
        return WorkflowSimulator()

    @pytest.mark.asyncio
    async def test_invalid_workflow_execution(self, workflow_sim):
        """Test executing workflow with invalid DAG fails."""
        workflow = await workflow_sim.create_workflow(name="Invalid Workflow")

        # Add nodes but no valid path
        await workflow_sim.add_node(workflow["id"], DAGNode(
            id="task", type=NodeType.TASK, name="Task"
        ))

        with pytest.raises(ValueError, match="Invalid DAG"):
            await workflow_sim.execute_workflow(workflow["id"])

    @pytest.mark.asyncio
    async def test_workflow_not_found(self, workflow_sim):
        """Test operations on non-existent workflow."""
        with pytest.raises(ValueError, match="not found"):
            await workflow_sim.configure_workflow(
                "nonexistent_id",
                {"timeout": 100}
            )

    @pytest.mark.asyncio
    async def test_execution_not_found(self, workflow_sim):
        """Test status check on non-existent execution."""
        with pytest.raises(ValueError, match="not found"):
            await workflow_sim.get_execution_status("nonexistent_exec")

    @pytest.mark.asyncio
    async def test_invalid_pause_state(self, workflow_sim):
        """Test pausing execution in invalid state."""
        workflow = await workflow_sim.create_workflow(name="Test")
        await workflow_sim.add_node(workflow["id"], DAGNode(
            id="start", type=NodeType.START, name="Start"
        ))
        await workflow_sim.add_node(workflow["id"], DAGNode(
            id="end", type=NodeType.END, name="End"
        ))
        await workflow_sim.add_edge(workflow["id"], DAGEdge(
            id="e1", source_id="start", target_id="end"
        ))

        execution = await workflow_sim.execute_workflow(workflow["id"])

        # Wait for completion
        await asyncio.sleep(0.3)

        # Try to pause completed execution
        with pytest.raises(ValueError, match="Cannot pause"):
            await workflow_sim.pause_execution(execution["id"])

    @pytest.mark.asyncio
    async def test_invalid_resume_state(self, workflow_sim):
        """Test resuming execution in invalid state."""
        workflow = await workflow_sim.create_workflow(name="Test")
        await workflow_sim.add_node(workflow["id"], DAGNode(
            id="start", type=NodeType.START, name="Start"
        ))
        await workflow_sim.add_node(workflow["id"], DAGNode(
            id="end", type=NodeType.END, name="End"
        ))
        await workflow_sim.add_edge(workflow["id"], DAGEdge(
            id="e1", source_id="start", target_id="end"
        ))

        execution = await workflow_sim.execute_workflow(workflow["id"])

        # Try to resume running execution (not paused)
        with pytest.raises(ValueError, match="Cannot resume"):
            await workflow_sim.resume_execution(execution["id"])
