"""
Dual-Mode Team Execution Engine

Provides backward-compatible execution that can run in either:
1. Linear mode (existing TeamExecutionEngineV2SplitMode)
2. DAG mode (new DAGExecutor with workflow graph)

Controlled by feature flags for gradual migration.

Architecture: Phase 1 of AGENT3_DAG_MIGRATION_GUIDE.md
"""

import asyncio
import logging
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum

from dag_workflow import WorkflowDAG, WorkflowContext
from dag_executor import DAGExecutor, WorkflowContextStore, ExecutionEvent
from dag_compatibility import generate_linear_workflow, generate_parallel_workflow


logger = logging.getLogger(__name__)


class ExecutionMode(Enum):
    """Execution mode for team execution"""
    LINEAR = "linear"  # Original sequential execution
    DAG_LINEAR = "dag_linear"  # DAG execution with linear workflow
    DAG_PARALLEL = "dag_parallel"  # DAG execution with parallel workflow


class FeatureFlags:
    """
    Feature flags for controlling DAG execution.

    Flags can be set via:
    1. Environment variables (MAESTRO_ENABLE_DAG_EXECUTION=true)
    2. Direct configuration
    """

    def __init__(self):
        self.enable_dag_execution = self._get_bool_env('MAESTRO_ENABLE_DAG_EXECUTION', False)
        self.enable_parallel_execution = self._get_bool_env('MAESTRO_ENABLE_PARALLEL_EXECUTION', False)
        self.enable_context_persistence = self._get_bool_env('MAESTRO_ENABLE_CONTEXT_PERSISTENCE', True)
        self.enable_execution_events = self._get_bool_env('MAESTRO_ENABLE_EXECUTION_EVENTS', True)
        self.enable_retry_logic = self._get_bool_env('MAESTRO_ENABLE_RETRY_LOGIC', False)

    def _get_bool_env(self, key: str, default: bool) -> bool:
        """Get boolean value from environment variable"""
        value = os.getenv(key)
        if value is None:
            return default
        return value.lower() in ('true', '1', 'yes', 'on')

    def get_execution_mode(self) -> ExecutionMode:
        """Determine execution mode based on flags"""
        if not self.enable_dag_execution:
            return ExecutionMode.LINEAR

        if self.enable_parallel_execution:
            return ExecutionMode.DAG_PARALLEL

        return ExecutionMode.DAG_LINEAR

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'enable_dag_execution': self.enable_dag_execution,
            'enable_parallel_execution': self.enable_parallel_execution,
            'enable_context_persistence': self.enable_context_persistence,
            'enable_execution_events': self.enable_execution_events,
            'enable_retry_logic': self.enable_retry_logic,
            'execution_mode': self.get_execution_mode().value,
        }


class TeamExecutionEngineDual:
    """
    Dual-mode team execution engine.

    Provides backward-compatible API while supporting both linear and DAG execution.
    """

    def __init__(
        self,
        linear_engine: Any,  # TeamExecutionEngineV2SplitMode instance
        feature_flags: Optional[FeatureFlags] = None,
    ):
        """
        Initialize dual-mode execution engine.

        Args:
            linear_engine: Existing TeamExecutionEngineV2SplitMode instance
            feature_flags: Feature flags (uses defaults if not provided)
        """
        self.linear_engine = linear_engine
        self.feature_flags = feature_flags or FeatureFlags()
        self.context_store = WorkflowContextStore() if self.feature_flags.enable_context_persistence else None
        self.execution_events: List[ExecutionEvent] = []

        logger.info(f"Initialized TeamExecutionEngineDual in {self.feature_flags.get_execution_mode().value} mode")
        logger.info(f"Feature flags: {self.feature_flags.to_dict()}")

    async def execute(
        self,
        requirement: str,
        session_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute SDLC workflow.

        This is the main entry point that maintains backward compatibility
        while supporting DAG execution.

        Args:
            requirement: User requirement/specification
            session_id: Session ID for tracking
            **kwargs: Additional arguments passed to execution engine

        Returns:
            Execution result with same structure as original engine
        """
        execution_mode = self.feature_flags.get_execution_mode()
        logger.info(f"Executing workflow in {execution_mode.value} mode")
        logger.info(f"Requirement: {requirement[:100]}...")

        start_time = datetime.now()

        try:
            if execution_mode == ExecutionMode.LINEAR:
                # Use original linear execution
                result = await self._execute_linear(requirement, session_id, **kwargs)
            elif execution_mode == ExecutionMode.DAG_LINEAR:
                # Use DAG with linear workflow
                result = await self._execute_dag_linear(requirement, session_id, **kwargs)
            elif execution_mode == ExecutionMode.DAG_PARALLEL:
                # Use DAG with parallel workflow
                result = await self._execute_dag_parallel(requirement, session_id, **kwargs)
            else:
                raise ValueError(f"Unknown execution mode: {execution_mode}")

            execution_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"Workflow execution completed in {execution_time:.2f} seconds")

            # Add execution metadata
            result['execution_mode'] = execution_mode.value
            result['execution_time'] = execution_time
            result['feature_flags'] = self.feature_flags.to_dict()

            return result

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Workflow execution failed after {execution_time:.2f} seconds: {e}", exc_info=True)
            raise

    async def _execute_linear(
        self,
        requirement: str,
        session_id: Optional[str],
        **kwargs
    ) -> Dict[str, Any]:
        """Execute using original linear engine"""
        logger.info("Executing with original linear engine")

        # Delegate to existing engine
        result = await self.linear_engine.execute(
            requirement=requirement,
            session_id=session_id,
            **kwargs
        )

        return {
            'status': 'completed',
            'result': result,
            'execution_mode': 'linear',
        }

    async def _execute_dag_linear(
        self,
        requirement: str,
        session_id: Optional[str],
        **kwargs
    ) -> Dict[str, Any]:
        """Execute using DAG with linear workflow"""
        logger.info("Executing with DAG (linear workflow)")

        # Generate linear workflow
        workflow = generate_linear_workflow(
            workflow_name=f"sdlc_linear_{session_id or 'default'}",
            team_engine=self.linear_engine,
        )

        # Execute workflow
        result = await self._execute_workflow(workflow, requirement, session_id)

        return {
            'status': 'completed',
            'result': result,
            'execution_mode': 'dag_linear',
            'workflow_id': workflow.workflow_id,
        }

    async def _execute_dag_parallel(
        self,
        requirement: str,
        session_id: Optional[str],
        **kwargs
    ) -> Dict[str, Any]:
        """Execute using DAG with parallel workflow"""
        logger.info("Executing with DAG (parallel workflow)")

        # Generate parallel workflow
        workflow = generate_parallel_workflow(
            workflow_name=f"sdlc_parallel_{session_id or 'default'}",
            team_engine=self.linear_engine,
        )

        # Execute workflow
        result = await self._execute_workflow(workflow, requirement, session_id)

        return {
            'status': 'completed',
            'result': result,
            'execution_mode': 'dag_parallel',
            'workflow_id': workflow.workflow_id,
        }

    async def _execute_workflow(
        self,
        workflow: WorkflowDAG,
        requirement: str,
        session_id: Optional[str],
    ) -> Dict[str, Any]:
        """
        Execute a workflow DAG.

        Args:
            workflow: Workflow to execute
            requirement: User requirement
            session_id: Session ID

        Returns:
            Execution results formatted for compatibility
        """
        # Create executor
        event_handler = self._create_event_handler() if self.feature_flags.enable_execution_events else None
        executor = DAGExecutor(
            workflow=workflow,
            context_store=self.context_store,
            event_handler=event_handler,
        )

        # Prepare initial context
        initial_context = {
            'requirement': requirement,
            'session_id': session_id,
        }

        # Execute workflow
        context = await executor.execute(initial_context=initial_context)

        # Convert WorkflowContext to result format
        result = self._format_dag_result(context)

        return result

    def _create_event_handler(self):
        """Create event handler for execution events"""
        async def handle_event(event: ExecutionEvent):
            """Handle execution event"""
            self.execution_events.append(event)
            logger.info(f"Event: {event.event_type.value} - Node: {event.node_id or 'workflow'}")

        return handle_event

    def _format_dag_result(self, context: WorkflowContext) -> Dict[str, Any]:
        """
        Format WorkflowContext as result compatible with linear engine output.

        Args:
            context: Workflow execution context

        Returns:
            Result dictionary matching original engine format
        """
        # Extract phase results
        phase_results = {}
        for node_id, output in context.node_outputs.items():
            # Extract phase name from node_id (format: "phase_<phase_name>")
            if node_id.startswith("phase_"):
                phase_name = node_id[6:]  # Remove "phase_" prefix
                phase_results[phase_name] = output.get('output', {})

        # Extract artifacts
        all_artifacts = []
        for node_id, artifacts in context.artifacts.items():
            all_artifacts.extend(artifacts)

        # Extract contracts
        all_contracts = []
        for output in context.node_outputs.values():
            if 'contracts' in output:
                all_contracts.extend(output['contracts'])

        # Build result
        result = {
            'execution_id': context.execution_id,
            'workflow_id': context.workflow_id,
            'phases': phase_results,
            'artifacts': all_artifacts,
            'contracts': all_contracts,
            'node_states': {
                node_id: state.to_dict()
                for node_id, state in context.node_states.items()
            },
            'completed_nodes': len(context.get_completed_nodes()),
            'total_nodes': len(context.node_states),
        }

        # Add event summary if enabled
        if self.feature_flags.enable_execution_events:
            result['events'] = [event.to_dict() for event in self.execution_events]
            result['event_summary'] = {
                'total_events': len(self.execution_events),
                'node_started': sum(1 for e in self.execution_events if e.event_type.value == 'node_started'),
                'node_completed': sum(1 for e in self.execution_events if e.event_type.value == 'node_completed'),
                'node_failed': sum(1 for e in self.execution_events if e.event_type.value == 'node_failed'),
            }

        return result

    async def resume_execution(self, execution_id: str) -> Dict[str, Any]:
        """
        Resume a paused workflow execution.

        Args:
            execution_id: ID of execution to resume

        Returns:
            Execution result
        """
        if not self.context_store:
            raise ValueError("Context persistence not enabled")

        logger.info(f"Resuming execution {execution_id}")

        # Load context
        context = await self.context_store.load_context(execution_id)
        if not context:
            raise ValueError(f"Execution {execution_id} not found")

        # Reconstruct workflow (simplified - in production, store workflow definition)
        workflow = generate_linear_workflow(team_engine=self.linear_engine)

        # Create executor
        event_handler = self._create_event_handler() if self.feature_flags.enable_execution_events else None
        executor = DAGExecutor(
            workflow=workflow,
            context_store=self.context_store,
            event_handler=event_handler,
        )

        # Resume execution
        context = await executor.execute(resume_execution_id=execution_id)

        # Format result
        result = self._format_dag_result(context)
        result['resumed'] = True

        return result

    def get_execution_events(self) -> List[Dict[str, Any]]:
        """Get execution events from current run"""
        return [event.to_dict() for event in self.execution_events]

    def clear_execution_events(self) -> None:
        """Clear execution events"""
        self.execution_events.clear()


def create_dual_engine(linear_engine: Any) -> TeamExecutionEngineDual:
    """
    Factory function to create dual-mode engine.

    Args:
        linear_engine: Existing TeamExecutionEngineV2SplitMode instance

    Returns:
        TeamExecutionEngineDual instance
    """
    feature_flags = FeatureFlags()
    return TeamExecutionEngineDual(
        linear_engine=linear_engine,
        feature_flags=feature_flags,
    )


# Export public API
__all__ = [
    'TeamExecutionEngineDual',
    'ExecutionMode',
    'FeatureFlags',
    'create_dual_engine',
]
