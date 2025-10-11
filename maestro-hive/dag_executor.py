"""
DAG Workflow Executor

Executes workflow DAGs with support for:
- Parallel execution of independent nodes
- Retry logic with exponential backoff
- Conditional execution
- State persistence and recovery
- Real-time progress tracking

Architecture: Based on AGENT3_DAG_WORKFLOW_ARCHITECTURE.md
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable, Awaitable, Set
from enum import Enum

from dag_workflow import (
    WorkflowDAG,
    WorkflowNode,
    WorkflowContext,
    NodeState,
    NodeStatus,
    NodeType,
    ExecutionMode,
)


logger = logging.getLogger(__name__)


class WorkflowExecutionStatus(Enum):
    """Overall workflow execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class ExecutionEventType(Enum):
    """Types of execution events for monitoring"""
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"
    NODE_STARTED = "node_started"
    NODE_COMPLETED = "node_completed"
    NODE_FAILED = "node_failed"
    NODE_RETRY = "node_retry"
    NODE_SKIPPED = "node_skipped"


class ExecutionEvent:
    """Event emitted during workflow execution"""

    def __init__(
        self,
        event_type: ExecutionEventType,
        workflow_id: str,
        execution_id: str,
        node_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
    ):
        self.event_type = event_type
        self.workflow_id = workflow_id
        self.execution_id = execution_id
        self.node_id = node_id
        self.data = data or {}
        self.timestamp = timestamp or datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'event_type': self.event_type.value,
            'workflow_id': self.workflow_id,
            'execution_id': self.execution_id,
            'node_id': self.node_id,
            'data': self.data,
            'timestamp': self.timestamp.isoformat(),
        }


class DAGExecutor:
    """
    Executes workflow DAGs with parallel execution and state management.

    Key features:
    - Topological execution with parallel groups
    - Retry logic with exponential backoff
    - Conditional node execution
    - State persistence for pause/resume
    - Event-driven progress tracking
    """

    def __init__(
        self,
        workflow: WorkflowDAG,
        context_store: Optional['WorkflowContextStore'] = None,
        event_handler: Optional[Callable[[ExecutionEvent], Awaitable[None]]] = None,
    ):
        self.workflow = workflow
        self.context_store = context_store
        self.event_handler = event_handler
        self.execution_status = WorkflowExecutionStatus.PENDING
        self._cancel_requested = False
        self._pause_requested = False

    async def execute(
        self,
        initial_context: Optional[Dict[str, Any]] = None,
        resume_execution_id: Optional[str] = None,
    ) -> WorkflowContext:
        """
        Execute the workflow DAG.

        Args:
            initial_context: Initial global context for the workflow
            resume_execution_id: If provided, resume a previous execution

        Returns:
            WorkflowContext with execution results
        """
        # Initialize or restore context
        if resume_execution_id and self.context_store:
            context = await self.context_store.load_context(resume_execution_id)
            if not context:
                raise ValueError(f"Cannot resume: execution {resume_execution_id} not found")
            logger.info(f"Resuming workflow execution {resume_execution_id}")
        else:
            context = WorkflowContext(workflow_id=self.workflow.workflow_id)
            if initial_context:
                context.global_context = initial_context
            logger.info(f"Starting new workflow execution {context.execution_id}")

        self.execution_status = WorkflowExecutionStatus.RUNNING

        # Emit workflow started event
        await self._emit_event(ExecutionEvent(
            event_type=ExecutionEventType.WORKFLOW_STARTED,
            workflow_id=self.workflow.workflow_id,
            execution_id=context.execution_id,
            data={'initial_context': initial_context}
        ))

        try:
            # Validate workflow structure
            validation_errors = self.workflow.validate()
            if validation_errors:
                raise ValueError(f"Invalid workflow: {', '.join(validation_errors)}")

            # Get execution order (parallel groups)
            execution_groups = self.workflow.get_execution_order()
            logger.info(f"Workflow has {len(execution_groups)} execution groups")

            # Execute each group
            for group_index, node_ids in enumerate(execution_groups):
                logger.info(f"Executing group {group_index + 1}/{len(execution_groups)}: {node_ids}")

                # Check for pause/cancel
                if self._pause_requested:
                    logger.info("Pause requested, saving state")
                    self.execution_status = WorkflowExecutionStatus.PAUSED
                    if self.context_store:
                        await self.context_store.save_context(context)
                    return context

                if self._cancel_requested:
                    logger.info("Cancel requested, stopping execution")
                    self.execution_status = WorkflowExecutionStatus.CANCELLED
                    return context

                # Filter nodes that are ready (not already completed/failed)
                nodes_to_execute = [
                    node_id for node_id in node_ids
                    if not self._is_node_terminal(context, node_id)
                ]

                if not nodes_to_execute:
                    logger.info(f"Group {group_index + 1}: all nodes already complete")
                    continue

                # Execute nodes in parallel
                tasks = [
                    self._execute_node(node_id, context)
                    for node_id in nodes_to_execute
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Check for failures
                for node_id, result in zip(nodes_to_execute, results):
                    if isinstance(result, Exception):
                        logger.error(f"Node {node_id} failed with exception: {result}")
                        state = context.get_node_state(node_id)
                        if state and state.status == NodeStatus.FAILED:
                            # Node failed and exhausted retries
                            self.execution_status = WorkflowExecutionStatus.FAILED
                            await self._emit_event(ExecutionEvent(
                                event_type=ExecutionEventType.WORKFLOW_FAILED,
                                workflow_id=self.workflow.workflow_id,
                                execution_id=context.execution_id,
                                data={'failed_node': node_id, 'error': str(result)}
                            ))
                            if self.context_store:
                                await self.context_store.save_context(context)
                            raise result

                # Save context after each group
                if self.context_store:
                    await self.context_store.save_context(context)

            # Workflow completed successfully
            self.execution_status = WorkflowExecutionStatus.COMPLETED
            await self._emit_event(ExecutionEvent(
                event_type=ExecutionEventType.WORKFLOW_COMPLETED,
                workflow_id=self.workflow.workflow_id,
                execution_id=context.execution_id,
                data={'completed_nodes': len(context.node_states)}
            ))

            if self.context_store:
                await self.context_store.save_context(context)

            logger.info(f"Workflow execution {context.execution_id} completed successfully")
            return context

        except Exception as e:
            self.execution_status = WorkflowExecutionStatus.FAILED
            logger.error(f"Workflow execution failed: {e}", exc_info=True)
            await self._emit_event(ExecutionEvent(
                event_type=ExecutionEventType.WORKFLOW_FAILED,
                workflow_id=self.workflow.workflow_id,
                execution_id=context.execution_id,
                data={'error': str(e)}
            ))
            raise

    async def _execute_node(
        self,
        node_id: str,
        context: WorkflowContext,
    ) -> None:
        """
        Execute a single workflow node with retry logic.

        Args:
            node_id: ID of the node to execute
            context: Workflow execution context
        """
        node = self.workflow.nodes[node_id]
        retry_policy = node.retry_policy

        # Check if node should be skipped due to condition
        if node.condition:
            should_execute = await self._evaluate_condition(node.condition, context)
            if not should_execute:
                logger.info(f"Node {node_id} skipped due to condition: {node.condition}")
                state = NodeState(
                    node_id=node_id,
                    status=NodeStatus.SKIPPED,
                    start_time=datetime.now(),
                    end_time=datetime.now()
                )
                context.set_node_state(node_id, state)
                await self._emit_event(ExecutionEvent(
                    event_type=ExecutionEventType.NODE_SKIPPED,
                    workflow_id=self.workflow.workflow_id,
                    execution_id=context.execution_id,
                    node_id=node_id,
                    data={'condition': node.condition}
                ))
                return

        # Initialize or retrieve node state
        state = context.get_node_state(node_id)
        if not state:
            state = NodeState(node_id=node_id)
            context.set_node_state(node_id, state)

        # Retry loop
        max_attempts = retry_policy.max_attempts
        for attempt in range(max_attempts):
            state.attempt_count = attempt + 1
            state.status = NodeStatus.RUNNING
            state.start_time = datetime.now()
            context.set_node_state(node_id, state)

            # Emit node started event
            await self._emit_event(ExecutionEvent(
                event_type=ExecutionEventType.NODE_STARTED,
                workflow_id=self.workflow.workflow_id,
                execution_id=context.execution_id,
                node_id=node_id,
                data={'attempt': attempt + 1, 'max_attempts': max_attempts}
            ))

            try:
                # Prepare input context for node
                node_input = await self._prepare_node_input(node, context)

                # Execute node
                if not node.executor:
                    raise ValueError(f"Node {node_id} has no executor function")

                logger.info(f"Executing node {node_id} (attempt {attempt + 1}/{max_attempts})")
                output = await node.executor(node_input)

                # Store output
                context.set_node_output(node_id, output)

                # Extract artifacts if present
                if 'artifacts' in output:
                    for artifact_path in output['artifacts']:
                        context.add_artifact(node_id, artifact_path)

                # Mark as completed
                state.status = NodeStatus.COMPLETED
                state.end_time = datetime.now()
                state.output = output
                context.set_node_state(node_id, state)

                # Emit node completed event
                await self._emit_event(ExecutionEvent(
                    event_type=ExecutionEventType.NODE_COMPLETED,
                    workflow_id=self.workflow.workflow_id,
                    execution_id=context.execution_id,
                    node_id=node_id,
                    data={'output': output, 'attempt': attempt + 1}
                ))

                logger.info(f"Node {node_id} completed successfully")
                return

            except Exception as e:
                logger.error(f"Node {node_id} failed (attempt {attempt + 1}/{max_attempts}): {e}")
                state.error_message = str(e)

                # Check if we should retry
                if attempt + 1 < max_attempts and retry_policy.retry_on_failure:
                    # Calculate delay with optional exponential backoff
                    delay = retry_policy.retry_delay_seconds
                    if retry_policy.exponential_backoff:
                        delay = delay * (2 ** attempt)

                    logger.info(f"Retrying node {node_id} in {delay} seconds")
                    await self._emit_event(ExecutionEvent(
                        event_type=ExecutionEventType.NODE_RETRY,
                        workflow_id=self.workflow.workflow_id,
                        execution_id=context.execution_id,
                        node_id=node_id,
                        data={'attempt': attempt + 1, 'delay': delay, 'error': str(e)}
                    ))

                    await asyncio.sleep(delay)
                else:
                    # No more retries, mark as failed
                    state.status = NodeStatus.FAILED
                    state.end_time = datetime.now()
                    context.set_node_state(node_id, state)

                    await self._emit_event(ExecutionEvent(
                        event_type=ExecutionEventType.NODE_FAILED,
                        workflow_id=self.workflow.workflow_id,
                        execution_id=context.execution_id,
                        node_id=node_id,
                        data={'error': str(e), 'attempts': attempt + 1}
                    ))

                    raise

    async def _prepare_node_input(
        self,
        node: WorkflowNode,
        context: WorkflowContext,
    ) -> Dict[str, Any]:
        """
        Prepare input context for node execution.

        Args:
            node: The workflow node
            context: Workflow execution context

        Returns:
            Dictionary with node input data
        """
        # Get outputs from dependency nodes
        dependency_outputs = context.get_dependency_outputs(node.dependencies)

        # Get artifacts from dependencies
        dependency_artifacts = {}
        for dep_node_id in node.dependencies:
            artifacts = context.get_artifacts(dep_node_id)
            if artifacts:
                dependency_artifacts[dep_node_id] = artifacts[dep_node_id]

        # Build node input
        node_input = {
            'node_id': node.node_id,
            'node_name': node.name,
            'node_config': node.config,
            'dependency_outputs': dependency_outputs,
            'dependency_artifacts': dependency_artifacts,
            'global_context': context.global_context,
            'all_outputs': context.get_all_outputs(),
            'all_artifacts': context.get_artifacts(),
        }

        return node_input

    async def _evaluate_condition(
        self,
        condition: str,
        context: WorkflowContext,
    ) -> bool:
        """
        Evaluate a conditional expression.

        Args:
            condition: Python expression to evaluate
            context: Workflow execution context

        Returns:
            True if node should execute, False to skip
        """
        try:
            # Build evaluation context with safe built-ins
            eval_context = {
                'outputs': context.get_all_outputs(),
                'global_context': context.global_context,
                'any': any,
                'all': all,
                'len': len,
                'str': str,
                'int': int,
                'float': float,
                'bool': bool,
            }

            # Evaluate condition
            result = eval(condition, {"__builtins__": {}}, eval_context)
            return bool(result)

        except Exception as e:
            logger.error(f"Failed to evaluate condition '{condition}': {e}")
            # On error, default to executing the node
            return True

    def _is_node_terminal(self, context: WorkflowContext, node_id: str) -> bool:
        """Check if node is in a terminal state (completed, failed, or skipped)"""
        state = context.get_node_state(node_id)
        if not state:
            return False
        return state.status in [NodeStatus.COMPLETED, NodeStatus.FAILED, NodeStatus.SKIPPED]

    async def _emit_event(self, event: ExecutionEvent) -> None:
        """Emit an execution event"""
        logger.debug(f"Event: {event.event_type.value} - {event.node_id or 'workflow'}")
        if self.event_handler:
            try:
                await self.event_handler(event)
            except Exception as e:
                logger.error(f"Event handler failed: {e}")

    def pause(self) -> None:
        """Request pause after current execution group"""
        logger.info("Pause requested")
        self._pause_requested = True

    def cancel(self) -> None:
        """Request cancellation of workflow execution"""
        logger.info("Cancel requested")
        self._cancel_requested = True


class WorkflowContextStore:
    """
    Manages persistence of workflow execution context.

    In Phase 1, this is a simple in-memory store.
    In later phases, this will be backed by PostgreSQL + Redis.
    """

    def __init__(self):
        self._contexts: Dict[str, WorkflowContext] = {}
        logger.info("Initialized in-memory WorkflowContextStore")

    async def save_context(self, context: WorkflowContext) -> None:
        """Save workflow execution context"""
        self._contexts[context.execution_id] = context
        logger.debug(f"Saved context for execution {context.execution_id}")

    async def load_context(self, execution_id: str) -> Optional[WorkflowContext]:
        """Load workflow execution context"""
        context = self._contexts.get(execution_id)
        if context:
            logger.debug(f"Loaded context for execution {execution_id}")
        else:
            logger.warning(f"Context not found for execution {execution_id}")
        return context

    async def delete_context(self, execution_id: str) -> bool:
        """Delete workflow execution context"""
        if execution_id in self._contexts:
            del self._contexts[execution_id]
            logger.debug(f"Deleted context for execution {execution_id}")
            return True
        return False

    async def list_executions(self, workflow_id: Optional[str] = None) -> List[str]:
        """List execution IDs, optionally filtered by workflow_id"""
        if workflow_id:
            return [
                ctx.execution_id
                for ctx in self._contexts.values()
                if ctx.workflow_id == workflow_id
            ]
        return list(self._contexts.keys())


# Export public API
__all__ = [
    'DAGExecutor',
    'WorkflowExecutionStatus',
    'ExecutionEvent',
    'ExecutionEventType',
    'WorkflowContextStore',
]
