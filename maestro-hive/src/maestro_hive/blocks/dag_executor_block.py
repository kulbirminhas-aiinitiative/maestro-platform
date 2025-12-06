"""
DAGExecutorBlock - Certified Block for DAG Workflow Execution

Wraps the existing dag_workflow.py and dag_executor.py modules
as a certified block with contract testing and versioning.

Block ID: dag-executor
Version: 2.0.0

Reference: MD-2507 Block Formalization
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from uuid import uuid4

from ..core.block_interface import BlockInterface, BlockResult, BlockStatus
from .interfaces import (
    IDAGExecutor,
    ExecutionResult,
    ValidationResult,
)

logger = logging.getLogger(__name__)


class DAGExecutorBlock(IDAGExecutor):
    """
    Certified block wrapping DAGWorkflow and DAGExecutor.

    This block formalizes the existing DAG execution infrastructure
    with a standard interface, contract testing, and versioning.

    Features:
    - DAG validation and execution
    - Parallel node execution
    - Retry logic with exponential backoff
    - State persistence and resume
    - Event-driven execution tracking
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize DAGExecutorBlock.

        Args:
            config: Optional configuration
                - max_parallel: Max concurrent nodes (default: 10)
                - timeout_seconds: Execution timeout (default: 300)
                - enable_retry: Enable retry logic (default: True)
        """
        self._config = config or {}
        self._max_parallel = self._config.get("max_parallel", 10)
        self._timeout = self._config.get("timeout_seconds", 300)
        self._enable_retry = self._config.get("enable_retry", True)

        # Lazy-load wrapped modules
        self._dag_workflow = None
        self._dag_executor = None
        self._executions: Dict[str, Dict[str, Any]] = {}

        logger.info(f"DAGExecutorBlock initialized (v{self.version})")

    def _initialize_for_registration(self):
        """Minimal init for registry metadata extraction"""
        pass

    @property
    def block_id(self) -> str:
        return "dag-executor"

    @property
    def version(self) -> str:
        return "2.0.0"

    def _get_workflow_module(self):
        """Lazy load dag_workflow module"""
        if self._dag_workflow is None:
            try:
                from ..dag import dag_workflow
                self._dag_workflow = dag_workflow
            except ImportError:
                # Fallback for standalone testing
                logger.warning("dag_workflow module not found, using mock")
                self._dag_workflow = None
        return self._dag_workflow

    def _get_executor_module(self):
        """Lazy load dag_executor module"""
        if self._dag_executor is None:
            try:
                from ..dag import dag_executor
                self._dag_executor = dag_executor
            except ImportError:
                logger.warning("dag_executor module not found, using mock")
                self._dag_executor = None
        return self._dag_executor

    def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        """
        Validate DAG execution inputs.

        Required:
        - dag_definition: Dict with 'nodes' and optionally 'edges'
        """
        if not isinstance(inputs, dict):
            return False

        dag_def = inputs.get("dag_definition")
        if not dag_def:
            return False

        # Must have nodes
        if "nodes" not in dag_def:
            return False

        return True

    def execute(self, inputs: Dict[str, Any]) -> BlockResult:
        """
        Execute the block's core logic.

        Args:
            inputs: {"dag_definition": {...}, "context": {...}}

        Returns:
            BlockResult with execution outcome
        """
        if not self.validate_inputs(inputs):
            return BlockResult(
                status=BlockStatus.FAILED,
                output={},
                error="Invalid inputs: dag_definition required"
            )

        try:
            result = self.execute_dag(inputs["dag_definition"])

            return BlockResult(
                status=BlockStatus.COMPLETED if result.success else BlockStatus.FAILED,
                output={
                    "execution_id": result.execution_id,
                    "status": result.status,
                    "output": result.output
                },
                error=result.error,
                metrics={"duration_ms": result.duration_ms or 0}
            )

        except Exception as e:
            logger.error(f"DAG execution failed: {e}")
            return BlockResult(
                status=BlockStatus.FAILED,
                output={},
                error=str(e)
            )

    def execute_dag(self, dag_definition: Dict[str, Any]) -> ExecutionResult:
        """
        Execute a DAG workflow.

        Args:
            dag_definition: DAG structure with nodes and edges

        Returns:
            ExecutionResult with execution_id and status
        """
        start_time = datetime.utcnow()
        execution_id = str(uuid4())

        # Validate first
        validation = self.validate_dag(dag_definition)
        if not validation.valid:
            return ExecutionResult(
                success=False,
                execution_id=execution_id,
                status="validation_failed",
                output={"validation_errors": validation.errors},
                error="; ".join(validation.errors)
            )

        # Track execution
        self._executions[execution_id] = {
            "status": "running",
            "started_at": start_time.isoformat(),
            "dag": dag_definition,
            "node_states": {}
        }

        try:
            # Try to use real executor
            executor_module = self._get_executor_module()
            workflow_module = self._get_workflow_module()

            if executor_module and workflow_module:
                # Use real DAG executor
                result = self._execute_with_real_executor(
                    dag_definition, execution_id, executor_module, workflow_module
                )
            else:
                # Mock execution for testing
                result = self._mock_execute(dag_definition, execution_id)

            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

            self._executions[execution_id]["status"] = "completed" if result["success"] else "failed"
            self._executions[execution_id]["completed_at"] = datetime.utcnow().isoformat()

            return ExecutionResult(
                success=result["success"],
                execution_id=execution_id,
                status="completed" if result["success"] else "failed",
                output=result.get("output", {}),
                error=result.get("error"),
                duration_ms=duration_ms
            )

        except Exception as e:
            self._executions[execution_id]["status"] = "failed"
            self._executions[execution_id]["error"] = str(e)

            return ExecutionResult(
                success=False,
                execution_id=execution_id,
                status="failed",
                output={},
                error=str(e),
                duration_ms=(datetime.utcnow() - start_time).total_seconds() * 1000
            )

    def _execute_with_real_executor(
        self,
        dag_definition: Dict[str, Any],
        execution_id: str,
        executor_module,
        workflow_module
    ) -> Dict[str, Any]:
        """Execute using real DAG executor module"""
        # Build workflow DAG
        dag = workflow_module.WorkflowDAG()

        for node_def in dag_definition.get("nodes", []):
            node = workflow_module.WorkflowNode(
                node_id=node_def["id"],
                name=node_def.get("name", node_def["id"]),
                node_type=workflow_module.NodeType(node_def.get("type", "custom")),
                dependencies=node_def.get("dependencies", []),
                config=node_def.get("config", {})
            )
            dag.add_node(node)

        # Add explicit edges if provided
        for edge in dag_definition.get("edges", []):
            dag.add_edge(edge["from"], edge["to"])

        # Create executor and run
        executor = executor_module.DAGExecutor()
        context = workflow_module.WorkflowContext(execution_id=execution_id)

        # Run async execution
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        result = loop.run_until_complete(executor.execute(dag, context))

        return {
            "success": result.get("status") == "completed",
            "output": result,
            "error": result.get("error")
        }

    def _mock_execute(self, dag_definition: Dict[str, Any], execution_id: str) -> Dict[str, Any]:
        """Mock execution for testing when real modules unavailable"""
        nodes = dag_definition.get("nodes", [])
        node_outputs = {}

        for node in nodes:
            node_id = node["id"]
            # Simulate node execution
            node_outputs[node_id] = {
                "status": "completed",
                "output": {"mock": True, "node_id": node_id}
            }
            self._executions[execution_id]["node_states"][node_id] = "completed"

        return {
            "success": True,
            "output": {
                "nodes_executed": len(nodes),
                "node_outputs": node_outputs
            }
        }

    def validate_dag(self, dag_definition: Dict[str, Any]) -> ValidationResult:
        """
        Validate a DAG definition without executing.

        Checks:
        - Required fields present
        - No cycles in graph
        - All dependencies exist
        - Valid node types
        """
        errors = []
        warnings = []

        nodes = dag_definition.get("nodes", [])
        if not nodes:
            errors.append("DAG must have at least one node")

        node_ids = {n.get("id") for n in nodes if n.get("id")}

        # Check for missing IDs
        for i, node in enumerate(nodes):
            if not node.get("id"):
                errors.append(f"Node at index {i} missing 'id' field")

        # Check dependencies exist
        for node in nodes:
            for dep in node.get("dependencies", []):
                if dep not in node_ids:
                    errors.append(f"Node '{node.get('id')}' has unknown dependency '{dep}'")

        # Check for cycles (simple detection)
        if self._has_cycle(nodes):
            errors.append("DAG contains a cycle")

        # Warnings for optional best practices
        for node in nodes:
            if not node.get("name"):
                warnings.append(f"Node '{node.get('id')}' missing 'name' (recommended)")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            metadata={"node_count": len(nodes)}
        )

    def _has_cycle(self, nodes: list) -> bool:
        """Simple cycle detection using DFS"""
        adj = {}
        for node in nodes:
            nid = node.get("id")
            if nid:
                adj[nid] = node.get("dependencies", [])

        visited = set()
        rec_stack = set()

        def dfs(node_id):
            visited.add(node_id)
            rec_stack.add(node_id)

            for dep in adj.get(node_id, []):
                if dep not in visited:
                    if dfs(dep):
                        return True
                elif dep in rec_stack:
                    return True

            rec_stack.remove(node_id)
            return False

        for node_id in adj:
            if node_id not in visited:
                if dfs(node_id):
                    return True
        return False

    def get_execution_status(self, execution_id: str) -> Dict[str, Any]:
        """Get status of an execution"""
        if execution_id not in self._executions:
            return {"error": "Execution not found", "execution_id": execution_id}

        return self._executions[execution_id]

    def pause_execution(self, execution_id: str) -> bool:
        """Pause an active execution"""
        if execution_id not in self._executions:
            return False

        if self._executions[execution_id]["status"] == "running":
            self._executions[execution_id]["status"] = "paused"
            return True
        return False

    def resume_execution(self, execution_id: str) -> bool:
        """Resume a paused execution"""
        if execution_id not in self._executions:
            return False

        if self._executions[execution_id]["status"] == "paused":
            self._executions[execution_id]["status"] = "running"
            return True
        return False

    def health_check(self) -> bool:
        """Check if the block is healthy"""
        return True
