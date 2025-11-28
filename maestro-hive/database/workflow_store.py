#!/usr/bin/env python3
"""
Database-backed Workflow Context Store.

Replaces the in-memory WorkflowContextStore with PostgreSQL persistence.
Compatible with existing DAGExecutor interface.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import logging
import json

from database.config import db_engine
from database.repository import RepositoryFactory
from database.models import WorkflowStatus, NodeStatus, EventType
from dag_workflow import WorkflowContext, WorkflowDAG
try:
    from dag_workflow import NodeState as DAGNodeState
    from dag_workflow import NodeStatus as DAGNodeStatus
except ImportError:
    # Fallback for different import structure
    DAGNodeState = None
    DAGNodeStatus = None

logger = logging.getLogger(__name__)


class DatabaseWorkflowContextStore:
    """
    PostgreSQL-backed workflow context store.

    Drop-in replacement for the in-memory WorkflowContextStore.
    Provides persistence, recovery, and multi-instance support.
    """

    def __init__(self):
        """Initialize database-backed store"""
        if not db_engine._initialized:
            db_engine.initialize()

    async def save_context(self, context: WorkflowContext):
        """
        Save workflow context to database.

        Persists:
        - Execution status and progress
        - Node states
        - Global context
        - Outputs and artifacts
        """
        try:
            # Run database operations in executor to avoid blocking event loop
            import asyncio
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._save_context_sync, context)

        except Exception as e:
            logger.error(f"❌ Failed to save context: {e}", exc_info=True)
            # Don't raise - allow execution to continue even if persistence fails

    def _save_context_sync(self, context: WorkflowContext):
        """Synchronous helper for save_context"""
        try:
            with db_engine.session_scope() as session:
                repos = RepositoryFactory(session)

                # Get or create execution
                execution = repos.execution.get(context.execution_id)
                if not execution:
                    execution = repos.execution.create(
                        workflow_id=context.workflow_id,
                        initial_context={}
                    )
                    context.execution_id = execution.id

                # Update execution metadata
                execution.global_context = context.global_context or {}
                execution.total_nodes = len(context.node_states)

                # Update node states
                for node_id, node_state in context.node_states.items():
                    repos.node_state.create_or_update(
                        execution_id=context.execution_id,
                        node_id=node_id,
                        node_state=node_state
                    )

                    # Save node outputs
                    if node_id in context.node_outputs:
                        node_db = repos.node_state.get_node(context.execution_id, node_id)
                        if node_db:
                            node_db.outputs = context.node_outputs[node_id]

                # Update progress
                repos.execution.update_progress(context.execution_id)

                # Save artifacts
                for node_id, artifact_list in context.artifacts.items():
                    for artifact_path in artifact_list:
                        # Check if artifact already exists
                        try:
                            existing = repos.artifact.list_by_node(context.execution_id, node_id)
                            artifact_exists = any(a.file_path == artifact_path for a in existing)

                            if not artifact_exists:
                                repos.artifact.create(
                                    execution_id=context.execution_id,
                                    node_id=node_id,
                                    artifact_type='file',
                                    name=artifact_path.split('/')[-1] if artifact_path else 'unknown',
                                    file_path=artifact_path
                                )
                        except Exception as e:
                            logger.warning(f"Failed to save artifact {artifact_path}: {e}")

                session.commit()

                logger.debug(f"✅ Saved context for execution: {context.execution_id}")

        except Exception as e:
            logger.error(f"❌ Failed to save context: {e}", exc_info=True)
            # Don't raise - allow execution to continue even if persistence fails

    async def load_context(self, execution_id: str) -> Optional[WorkflowContext]:
        """
        Load workflow context from database.

        Enables workflow recovery and resume.
        """
        # Run database operations in executor to avoid blocking event loop
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._load_context_sync, execution_id)

    def _load_context_sync(self, execution_id: str) -> Optional[WorkflowContext]:
        """Synchronous helper for load_context"""
        with db_engine.session_scope() as session:
            repos = RepositoryFactory(session)

            execution = repos.execution.get(execution_id)
            if not execution:
                logger.warning(f"Execution not found: {execution_id}")
                return None

            # Reconstruct WorkflowContext
            context = WorkflowContext(
                workflow_id=execution.workflow_id,
                execution_id=execution_id
            )

            context.global_context = execution.global_context or {}

            # Load node states
            node_states = repos.node_state.get_by_execution(execution_id)
            for db_state in node_states:
                # Convert DB status to DAG status
                status_map = {
                    NodeStatus.PENDING: 'pending',
                    NodeStatus.RUNNING: 'running',
                    NodeStatus.COMPLETED: 'completed',
                    NodeStatus.FAILED: 'failed',
                    NodeStatus.SKIPPED: 'skipped',
                }

                dag_state = DAGNodeState(
                    status=status_map.get(db_state.status, 'pending')
                )
                dag_state.attempt_count = db_state.attempt_count
                dag_state.started_at = db_state.started_at
                dag_state.completed_at = db_state.completed_at
                dag_state.error = db_state.error_message

                context.node_states[db_state.node_id] = dag_state

                # Load outputs
                if db_state.outputs:
                    context.node_outputs[db_state.node_id] = db_state.outputs

            # Load artifacts
            artifacts = repos.artifact.list_by_execution(execution_id)
            for artifact in artifacts:
                if artifact.node_id:
                    if artifact.node_id not in context.artifacts:
                        context.artifacts[artifact.node_id] = []
                    context.artifacts[artifact.node_id].append(artifact.file_path)

            logger.info(f"Loaded context for execution: {execution_id}")
            return context

    async def list_executions(self, workflow_id: str = None) -> List[str]:
        """
        List all execution IDs, optionally filtered by workflow.

        Args:
            workflow_id: Optional workflow ID to filter by

        Returns:
            List of execution IDs
        """
        # Run database operations in executor to avoid blocking event loop
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._list_executions_sync, workflow_id)

    def _list_executions_sync(self, workflow_id: str = None) -> List[str]:
        """Synchronous helper for list_executions"""
        with db_engine.session_scope() as session:
            repos = RepositoryFactory(session)

            if workflow_id:
                executions = repos.execution.list_by_workflow(workflow_id)
            else:
                # Get all executions (limit to reasonable number)
                from database.models import WorkflowExecution
                executions = session.query(WorkflowExecution).order_by(
                    WorkflowExecution.created_at.desc()
                ).limit(1000).all()

            return [e.id for e in executions]

    async def delete_context(self, execution_id: str) -> bool:
        """
        Delete execution context from database.

        WARNING: This will delete all execution data including node states,
        events, and artifacts.
        """
        # Run database operations in executor to avoid blocking event loop
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._delete_context_sync, execution_id)

    def _delete_context_sync(self, execution_id: str) -> bool:
        """Synchronous helper for delete_context"""
        with db_engine.session_scope() as session:
            repos = RepositoryFactory(session)

            execution = repos.execution.get(execution_id)
            if execution:
                session.delete(execution)
                session.commit()
                logger.info(f"Deleted execution: {execution_id}")
                return True

            return False

    # -------------------------------------------------------------------------
    # Event Tracking
    # -------------------------------------------------------------------------

    def log_event(
        self,
        execution_id: str,
        event_type: str,
        node_id: str = None,
        message: str = None,
        data: Dict[str, Any] = None
    ):
        """Log an execution event"""
        with db_engine.session_scope() as session:
            repos = RepositoryFactory(session)

            # Map event type string to EventType enum
            event_type_map = {
                'workflow_started': EventType.WORKFLOW_STARTED,
                'workflow_completed': EventType.WORKFLOW_COMPLETED,
                'workflow_failed': EventType.WORKFLOW_FAILED,
                'workflow_paused': EventType.WORKFLOW_PAUSED,
                'workflow_resumed': EventType.WORKFLOW_RESUMED,
                'node_started': EventType.NODE_STARTED,
                'node_completed': EventType.NODE_COMPLETED,
                'node_failed': EventType.NODE_FAILED,
                'node_retrying': EventType.NODE_RETRYING,
            }

            event_enum = event_type_map.get(event_type)
            if event_enum:
                repos.event.create(
                    execution_id=execution_id,
                    event_type=event_enum,
                    node_id=node_id,
                    message=message,
                    data=data
                )

    def get_events(self, execution_id: str) -> List[Dict[str, Any]]:
        """Get all events for an execution"""
        with db_engine.session_scope() as session:
            repos = RepositoryFactory(session)
            events = repos.event.list_by_execution(execution_id)

            return [
                {
                    'event_type': e.event_type.value,
                    'node_id': e.node_id,
                    'message': e.message,
                    'data': e.data,
                    'timestamp': e.timestamp.isoformat()
                }
                for e in events
            ]

    # -------------------------------------------------------------------------
    # Workflow Management
    # -------------------------------------------------------------------------

    def register_workflow(self, workflow: WorkflowDAG):
        """Register a workflow definition in the database"""
        with db_engine.session_scope() as session:
            repos = RepositoryFactory(session)

            # Check if workflow already exists
            existing = repos.workflow.get(workflow.workflow_id)
            if existing:
                logger.info(f"Workflow already registered: {workflow.workflow_id}")
                return existing

            # Create new workflow definition
            return repos.workflow.create(workflow)

    def get_workflow(self, workflow_id: str):
        """Get workflow definition from database"""
        with db_engine.session_scope() as session:
            repos = RepositoryFactory(session)
            return repos.workflow.get(workflow_id)

    # -------------------------------------------------------------------------
    # Status Management
    # -------------------------------------------------------------------------

    def update_execution_status(
        self,
        execution_id: str,
        status: str,
        error_message: str = None
    ):
        """Update execution status"""
        with db_engine.session_scope() as session:
            repos = RepositoryFactory(session)

            status_map = {
                'pending': WorkflowStatus.PENDING,
                'running': WorkflowStatus.RUNNING,
                'paused': WorkflowStatus.PAUSED,
                'completed': WorkflowStatus.COMPLETED,
                'failed': WorkflowStatus.FAILED,
                'cancelled': WorkflowStatus.CANCELLED,
            }

            status_enum = status_map.get(status, WorkflowStatus.PENDING)
            repos.execution.update_status(execution_id, status_enum, error_message)

    def get_execution_status(self, execution_id: str) -> Optional[str]:
        """Get current execution status"""
        with db_engine.session_scope() as session:
            repos = RepositoryFactory(session)
            execution = repos.execution.get(execution_id)

            if execution:
                return execution.status.value

            return None


# =============================================================================
# Helper Functions
# =============================================================================

def migrate_from_memory_store(
    memory_store,
    db_store: DatabaseWorkflowContextStore
):
    """
    Migrate contexts from in-memory store to database store.

    Useful for transitioning from development to production.
    """
    if not hasattr(memory_store, 'contexts'):
        logger.warning("Memory store has no contexts to migrate")
        return

    migrated = 0
    for execution_id, context in memory_store.contexts.items():
        try:
            db_store.save_context(context)
            migrated += 1
            logger.info(f"Migrated execution: {execution_id}")
        except Exception as e:
            logger.error(f"Failed to migrate {execution_id}: {e}")

    logger.info(f"Migration complete: {migrated} contexts migrated")
