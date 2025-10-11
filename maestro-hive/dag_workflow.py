"""
DAG Workflow Core Infrastructure

This module implements the core DAG-based workflow system for the Maestro SDLC platform.
It provides the foundation for flexible, modular, and reusable workflow execution.

Architecture: Based on AGENT3_DAG_WORKFLOW_ARCHITECTURE.md
Migration: Phase 1 of AGENT3_DAG_MIGRATION_GUIDE.md
"""

import asyncio
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Callable, Awaitable
from uuid import uuid4
import networkx as nx


class NodeType(Enum):
    """Types of workflow nodes"""
    PHASE = "phase"  # Standard SDLC phase (requirement_analysis, design, etc.)
    CUSTOM = "custom"  # Custom user-defined node
    PARALLEL_GROUP = "parallel_group"  # Container for parallel execution
    CONDITIONAL = "conditional"  # Conditional branching node
    HUMAN_REVIEW = "human_review"  # Human-in-the-loop checkpoint


class NodeStatus(Enum):
    """Execution status of a workflow node"""
    PENDING = "pending"
    READY = "ready"  # Dependencies satisfied, ready to execute
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"  # Skipped due to conditional logic
    BLOCKED = "blocked"  # Blocked by failed dependency


class ExecutionMode(Enum):
    """Execution modes for workflow nodes"""
    SEQUENTIAL = "sequential"  # Execute dependencies sequentially
    PARALLEL = "parallel"  # Execute dependencies in parallel
    CONDITIONAL = "conditional"  # Execute based on condition evaluation


@dataclass
class RetryPolicy:
    """Retry policy for node execution"""
    max_attempts: int = 1
    retry_delay_seconds: int = 0
    retry_on_failure: bool = False
    exponential_backoff: bool = False


@dataclass
class NodeState:
    """Tracks execution state of a workflow node"""
    node_id: str
    status: NodeStatus = NodeStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    attempt_count: int = 0
    error_message: Optional[str] = None
    output: Optional[Dict[str, Any]] = None
    artifacts: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        result = asdict(self)
        result['status'] = self.status.value
        result['start_time'] = self.start_time.isoformat() if self.start_time else None
        result['end_time'] = self.end_time.isoformat() if self.end_time else None
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NodeState':
        """Create from dictionary"""
        data['status'] = NodeStatus(data['status'])
        if data.get('start_time'):
            data['start_time'] = datetime.fromisoformat(data['start_time'])
        if data.get('end_time'):
            data['end_time'] = datetime.fromisoformat(data['end_time'])
        return cls(**data)


@dataclass
class WorkflowNode:
    """Represents a single node in the workflow DAG"""
    node_id: str
    name: str
    node_type: NodeType
    executor: Optional[Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]] = None
    dependencies: List[str] = field(default_factory=list)  # List of node_ids
    execution_mode: ExecutionMode = ExecutionMode.SEQUENTIAL
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    condition: Optional[str] = None  # Python expression for conditional execution
    config: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        result = asdict(self)
        result['node_type'] = self.node_type.value
        result['execution_mode'] = self.execution_mode.value
        result['executor'] = None  # Executors are not serializable
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowNode':
        """Create from dictionary"""
        data['node_type'] = NodeType(data['node_type'])
        data['execution_mode'] = ExecutionMode(data['execution_mode'])
        if 'retry_policy' in data and isinstance(data['retry_policy'], dict):
            data['retry_policy'] = RetryPolicy(**data['retry_policy'])
        return cls(**data)


class WorkflowDAG:
    """
    Directed Acyclic Graph representation of a workflow.

    Manages workflow structure, dependencies, and provides utilities for
    execution planning (topological sort, parallel group detection).
    """

    def __init__(self, workflow_id: Optional[str] = None, name: Optional[str] = None):
        self.workflow_id = workflow_id or str(uuid4())
        self.name = name or f"workflow_{self.workflow_id[:8]}"
        self.graph = nx.DiGraph()
        self.nodes: Dict[str, WorkflowNode] = {}
        self.metadata: Dict[str, Any] = {}
        self.created_at = datetime.now()

    def add_node(self, node: WorkflowNode) -> None:
        """Add a node to the workflow"""
        if node.node_id in self.nodes:
            raise ValueError(f"Node {node.node_id} already exists in workflow")

        self.nodes[node.node_id] = node
        self.graph.add_node(node.node_id, node=node)

    def add_edge(self, from_node_id: str, to_node_id: str) -> None:
        """Add a dependency edge between two nodes"""
        if from_node_id not in self.nodes:
            raise ValueError(f"Source node {from_node_id} not found")
        if to_node_id not in self.nodes:
            raise ValueError(f"Target node {to_node_id} not found")

        self.graph.add_edge(from_node_id, to_node_id)

        # Verify no cycles created
        if not nx.is_directed_acyclic_graph(self.graph):
            self.graph.remove_edge(from_node_id, to_node_id)
            raise ValueError(f"Adding edge {from_node_id} -> {to_node_id} would create a cycle")

    def get_execution_order(self) -> List[List[str]]:
        """
        Get execution order as list of parallel groups.

        Returns:
            List of lists, where each inner list contains node_ids that can be executed in parallel
        """
        if not nx.is_directed_acyclic_graph(self.graph):
            raise ValueError("Workflow graph contains cycles")

        # Topological generations give us parallel execution groups
        generations = list(nx.topological_generations(self.graph))
        return generations

    def get_dependencies(self, node_id: str) -> List[str]:
        """Get all dependencies (predecessors) of a node"""
        if node_id not in self.nodes:
            raise ValueError(f"Node {node_id} not found")
        return list(self.graph.predecessors(node_id))

    def get_dependents(self, node_id: str) -> List[str]:
        """Get all dependents (successors) of a node"""
        if node_id not in self.nodes:
            raise ValueError(f"Node {node_id} not found")
        return list(self.graph.successors(node_id))

    def get_ready_nodes(self, completed_nodes: Set[str]) -> List[str]:
        """
        Get nodes that are ready to execute (all dependencies completed).

        Args:
            completed_nodes: Set of node_ids that have completed execution

        Returns:
            List of node_ids ready for execution
        """
        ready = []
        for node_id in self.nodes:
            if node_id in completed_nodes:
                continue

            dependencies = self.get_dependencies(node_id)
            if all(dep in completed_nodes for dep in dependencies):
                ready.append(node_id)

        return ready

    def validate(self) -> List[str]:
        """
        Validate workflow structure.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Check for cycles
        if not nx.is_directed_acyclic_graph(self.graph):
            errors.append("Workflow contains cycles")

        # Check for disconnected components
        if not nx.is_weakly_connected(self.graph):
            errors.append("Workflow has disconnected components")

        # Verify node dependencies exist
        for node_id, node in self.nodes.items():
            for dep in node.dependencies:
                if dep not in self.nodes:
                    errors.append(f"Node {node_id} depends on non-existent node {dep}")

        # Verify graph edges match node dependencies
        for node_id, node in self.nodes.items():
            graph_deps = set(self.get_dependencies(node_id))
            node_deps = set(node.dependencies)
            if graph_deps != node_deps:
                errors.append(f"Node {node_id} has mismatched dependencies: graph={graph_deps}, node={node_deps}")

        return errors

    def to_dict(self) -> Dict[str, Any]:
        """Convert workflow to dictionary for serialization"""
        return {
            'workflow_id': self.workflow_id,
            'name': self.name,
            'nodes': {node_id: node.to_dict() for node_id, node in self.nodes.items()},
            'edges': list(self.graph.edges()),
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowDAG':
        """Create workflow from dictionary"""
        workflow = cls(workflow_id=data['workflow_id'], name=data['name'])
        workflow.metadata = data.get('metadata', {})
        workflow.created_at = datetime.fromisoformat(data['created_at'])

        # Add nodes
        for node_id, node_data in data['nodes'].items():
            node = WorkflowNode.from_dict(node_data)
            workflow.add_node(node)

        # Add edges
        for from_node, to_node in data['edges']:
            workflow.add_edge(from_node, to_node)

        return workflow

    def to_yaml_definition(self) -> str:
        """Export workflow as YAML definition (for documentation/config)"""
        import yaml

        workflow_def = {
            'workflow': {
                'id': self.workflow_id,
                'name': self.name,
                'metadata': self.metadata
            },
            'nodes': []
        }

        for node_id, node in self.nodes.items():
            node_def = {
                'id': node_id,
                'name': node.name,
                'type': node.node_type.value,
                'dependencies': node.dependencies,
                'config': node.config
            }
            if node.condition:
                node_def['condition'] = node.condition
            workflow_def['nodes'].append(node_def)

        return yaml.dump(workflow_def, default_flow_style=False, sort_keys=False)


class WorkflowContext:
    """
    Manages workflow execution context and state.

    Provides access to node outputs, artifacts, and execution history.
    """

    def __init__(self, workflow_id: str, execution_id: Optional[str] = None):
        self.workflow_id = workflow_id
        self.execution_id = execution_id or str(uuid4())
        self.node_states: Dict[str, NodeState] = {}
        self.node_outputs: Dict[str, Dict[str, Any]] = {}
        self.artifacts: Dict[str, List[str]] = {}  # node_id -> list of artifact paths
        self.global_context: Dict[str, Any] = {}
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    def set_node_state(self, node_id: str, state: NodeState) -> None:
        """Update node execution state"""
        self.node_states[node_id] = state
        self.updated_at = datetime.now()

    def get_node_state(self, node_id: str) -> Optional[NodeState]:
        """Get node execution state"""
        return self.node_states.get(node_id)

    def set_node_output(self, node_id: str, output: Dict[str, Any]) -> None:
        """Set output for a node"""
        self.node_outputs[node_id] = output
        self.updated_at = datetime.now()

    def get_node_output(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Get output from a node"""
        return self.node_outputs.get(node_id)

    def get_all_outputs(self) -> Dict[str, Dict[str, Any]]:
        """Get outputs from all nodes"""
        return self.node_outputs.copy()

    def get_dependency_outputs(self, dependencies: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get outputs from specified dependency nodes"""
        return {
            node_id: self.node_outputs[node_id]
            for node_id in dependencies
            if node_id in self.node_outputs
        }

    def add_artifact(self, node_id: str, artifact_path: str) -> None:
        """Register an artifact produced by a node"""
        if node_id not in self.artifacts:
            self.artifacts[node_id] = []
        self.artifacts[node_id].append(artifact_path)
        self.updated_at = datetime.now()

    def get_artifacts(self, node_id: Optional[str] = None) -> Dict[str, List[str]]:
        """Get artifacts (all or for specific node)"""
        if node_id:
            return {node_id: self.artifacts.get(node_id, [])}
        return self.artifacts.copy()

    def get_completed_nodes(self) -> Set[str]:
        """Get set of completed node IDs"""
        return {
            node_id for node_id, state in self.node_states.items()
            if state.status == NodeStatus.COMPLETED
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'workflow_id': self.workflow_id,
            'execution_id': self.execution_id,
            'node_states': {node_id: state.to_dict() for node_id, state in self.node_states.items()},
            'node_outputs': self.node_outputs,
            'artifacts': self.artifacts,
            'global_context': self.global_context,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowContext':
        """Create from dictionary"""
        context = cls(
            workflow_id=data['workflow_id'],
            execution_id=data['execution_id']
        )
        context.node_states = {
            node_id: NodeState.from_dict(state_data)
            for node_id, state_data in data['node_states'].items()
        }
        context.node_outputs = data['node_outputs']
        context.artifacts = data['artifacts']
        context.global_context = data.get('global_context', {})
        context.created_at = datetime.fromisoformat(data['created_at'])
        context.updated_at = datetime.fromisoformat(data['updated_at'])
        return context


# Export public API
__all__ = [
    'NodeType',
    'NodeStatus',
    'ExecutionMode',
    'RetryPolicy',
    'NodeState',
    'WorkflowNode',
    'WorkflowDAG',
    'WorkflowContext',
]
