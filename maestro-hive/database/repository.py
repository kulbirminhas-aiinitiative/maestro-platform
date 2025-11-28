#!/usr/bin/env python3
"""
Database repository layer for DAG workflow persistence.

Provides high-level data access methods that replace the in-memory
WorkflowContextStore with PostgreSQL-backed persistence.
"""

from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import json

from database.models import (
    WorkflowDefinition, WorkflowExecution, NodeState, ExecutionEvent, Artifact,
    WorkflowStatus, NodeStatus, EventType,
    generate_execution_id, calculate_progress
)
from dag_workflow import WorkflowDAG, WorkflowContext, NodeState as DAGNodeState

logger = logging.getLogger(__name__)


# =============================================================================
# Workflow Repository
# =============================================================================

class WorkflowRepository:
    """Repository for workflow definitions"""

    def __init__(self, session: Session):
        self.session = session

    def create(self, workflow: WorkflowDAG) -> WorkflowDefinition:
        """Create a new workflow definition from WorkflowDAG"""
        try:
            # Convert WorkflowDAG to database model
            nodes_dict = {}
            for node_id, node in workflow.nodes.items():
                node_dict = {
                    'name': node.name,
                    'type': node.node_type.value if hasattr(node.node_type, 'value') else str(node.node_type),
                    'description': getattr(node, 'description', None),
                }

                # Serialize executor (store class name and module)
                if node.executor:
                    node_dict['executor'] = {
                        'class': node.executor.__class__.__name__,
                        'module': node.executor.__class__.__module__,
                    }

                # Serialize retry policy safely
                if node.retry_policy:
                    try:
                        node_dict['retry_policy'] = {
                            'max_attempts': getattr(node.retry_policy, 'max_attempts', 1),
                            'retry_delay_seconds': getattr(node.retry_policy, 'retry_delay_seconds', 0),
                            'retry_on_failure': getattr(node.retry_policy, 'retry_on_failure', False),
                            'exponential_backoff': getattr(node.retry_policy, 'exponential_backoff', False),
                        }
                    except Exception as e:
                        logger.warning(f"Failed to serialize retry policy for {node_id}: {e}")
                        node_dict['retry_policy'] = None

                nodes_dict[node_id] = node_dict

            # Convert edges from NetworkX graph
            edges_list = []
            try:
                for source, target in workflow.graph.edges():
                    edges_list.append({
                        'source': str(source),
                        'target': str(target),
                        'condition': None,
                    })
            except Exception as e:
                logger.warning(f"Failed to serialize edges: {e}")
                edges_list = []

            # Create database object
            db_workflow = WorkflowDefinition(
                id=workflow.workflow_id,
                name=workflow.name,
                workflow_type=workflow.metadata.get('type', 'custom'),
                nodes=nodes_dict,
                edges=edges_list,
                workflow_metadata=workflow.metadata or {}
            )

            self.session.add(db_workflow)
            self.session.commit()
            self.session.refresh(db_workflow)

            logger.info(f"✅ Created workflow definition: {db_workflow.id} ({len(nodes_dict)} nodes, {len(edges_list)} edges)")
            return db_workflow

        except Exception as e:
            self.session.rollback()
            logger.error(f"❌ Failed to create workflow: {e}", exc_info=True)
            raise

    def get(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        """Get workflow definition by ID"""
        return self.session.query(WorkflowDefinition).filter(
            WorkflowDefinition.id == workflow_id
        ).first()

    def list(self, limit: int = 100, offset: int = 0) -> List[WorkflowDefinition]:
        """List all workflow definitions"""
        return self.session.query(WorkflowDefinition).order_by(
            desc(WorkflowDefinition.created_at)
        ).limit(limit).offset(offset).all()

    def delete(self, workflow_id: str) -> bool:
        """Delete workflow definition"""
        workflow = self.get(workflow_id)
        if workflow:
            self.session.delete(workflow)
            self.session.commit()
            logger.info(f"Deleted workflow definition: {workflow_id}")
            return True
        return False


# =============================================================================
# Execution Repository
# =============================================================================

class ExecutionRepository:
    """Repository for workflow executions"""

    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        workflow_id: str,
        initial_context: Dict[str, Any] = None
    ) -> WorkflowExecution:
        """Create a new workflow execution"""
        execution_id = generate_execution_id(workflow_id)

        execution = WorkflowExecution(
            id=execution_id,
            workflow_id=workflow_id,
            status=WorkflowStatus.PENDING,
            initial_context=initial_context or {},
            total_nodes=0,  # Will be updated when execution starts
            completed_nodes=0,
            progress_percent=0.0
        )

        self.session.add(execution)
        self.session.commit()
        self.session.refresh(execution)

        logger.info(f"Created execution: {execution_id} for workflow: {workflow_id}")
        return execution

    def get(self, execution_id: str) -> Optional[WorkflowExecution]:
        """Get execution by ID"""
        return self.session.query(WorkflowExecution).filter(
            WorkflowExecution.id == execution_id
        ).first()

    def update_status(
        self,
        execution_id: str,
        status: WorkflowStatus,
        error_message: str = None
    ):
        """Update execution status"""
        execution = self.get(execution_id)
        if execution:
            execution.status = status
            execution.updated_at = datetime.utcnow()

            if status == WorkflowStatus.RUNNING and not execution.started_at:
                execution.started_at = datetime.utcnow()
            elif status in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED]:
                execution.completed_at = datetime.utcnow()
            elif status == WorkflowStatus.PAUSED:
                execution.paused_at = datetime.utcnow()

            if error_message:
                execution.error_message = error_message

            self.session.commit()
            logger.info(f"Updated execution {execution_id} status: {status.value}")

    def update_progress(self, execution_id: str):
        """Recalculate and update execution progress"""
        execution = self.get(execution_id)
        if execution:
            completed = self.session.query(NodeState).filter(
                and_(
                    NodeState.execution_id == execution_id,
                    NodeState.status == NodeStatus.COMPLETED
                )
            ).count()

            execution.completed_nodes = completed
            execution.progress_percent = calculate_progress(
                execution.total_nodes, completed
            )
            self.session.commit()

    def list_by_workflow(
        self,
        workflow_id: str,
        limit: int = 100
    ) -> List[WorkflowExecution]:
        """List executions for a workflow"""
        return self.session.query(WorkflowExecution).filter(
            WorkflowExecution.workflow_id == workflow_id
        ).order_by(desc(WorkflowExecution.created_at)).limit(limit).all()

    def list_active(self) -> List[WorkflowExecution]:
        """List all active (running or paused) executions"""
        return self.session.query(WorkflowExecution).filter(
            WorkflowExecution.status.in_([WorkflowStatus.RUNNING, WorkflowStatus.PAUSED])
        ).all()


# =============================================================================
# Node State Repository
# =============================================================================

class NodeStateRepository:
    """Repository for node execution states"""

    def __init__(self, session: Session):
        self.session = session

    def create_or_update(
        self,
        execution_id: str,
        node_id: str,
        node_state: DAGNodeState
    ) -> NodeState:
        """Create or update node state"""
        # Try to find existing state
        db_state = self.session.query(NodeState).filter(
            and_(
                NodeState.execution_id == execution_id,
                NodeState.node_id == node_id
            )
        ).first()

        if db_state:
            # Update existing
            self._update_from_dag_state(db_state, node_state)
        else:
            # Create new
            db_state = NodeState(
                execution_id=execution_id,
                node_id=node_id,
                node_name=node_id,  # Will be updated from workflow definition
                node_type='phase'   # Will be updated from workflow definition
            )
            self._update_from_dag_state(db_state, node_state)
            self.session.add(db_state)

        self.session.commit()
        self.session.refresh(db_state)
        return db_state

    def _update_from_dag_state(self, db_state: NodeState, dag_state: DAGNodeState):
        """Update database state from DAG node state"""
        # Map DAG status to DB status
        status_map = {
            'pending': NodeStatus.PENDING,
            'running': NodeStatus.RUNNING,
            'completed': NodeStatus.COMPLETED,
            'failed': NodeStatus.FAILED,
            'skipped': NodeStatus.SKIPPED,
        }

        db_state.status = status_map.get(dag_state.status.value, NodeStatus.PENDING)
        db_state.attempt_count = dag_state.attempt_count
        db_state.started_at = dag_state.start_time  # Fixed: DAG uses start_time not started_at
        db_state.completed_at = dag_state.end_time  # Fixed: DAG uses end_time not completed_at
        db_state.error_message = dag_state.error_message  # Fixed: DAG uses error_message not error

        # Calculate duration
        if dag_state.start_time and dag_state.end_time:
            duration = (dag_state.end_time - dag_state.start_time).total_seconds()
            db_state.duration_seconds = duration

        db_state.updated_at = datetime.utcnow()

    def get_by_execution(self, execution_id: str) -> List[NodeState]:
        """Get all node states for an execution"""
        return self.session.query(NodeState).filter(
            NodeState.execution_id == execution_id
        ).all()

    def get_node(self, execution_id: str, node_id: str) -> Optional[NodeState]:
        """Get specific node state"""
        return self.session.query(NodeState).filter(
            and_(
                NodeState.execution_id == execution_id,
                NodeState.node_id == node_id
            )
        ).first()


# =============================================================================
# Event Repository
# =============================================================================

class EventRepository:
    """Repository for execution events"""

    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        execution_id: str,
        event_type: EventType,
        node_id: str = None,
        message: str = None,
        data: Dict[str, Any] = None
    ) -> ExecutionEvent:
        """Create a new execution event"""
        event = ExecutionEvent(
            execution_id=execution_id,
            event_type=event_type,
            node_id=node_id,
            message=message,
            data=data or {}
        )

        self.session.add(event)
        self.session.commit()
        self.session.refresh(event)

        logger.debug(f"Event: {event_type.value} - {node_id or 'workflow'}")
        return event

    def list_by_execution(
        self,
        execution_id: str,
        limit: int = 1000
    ) -> List[ExecutionEvent]:
        """Get events for an execution"""
        return self.session.query(ExecutionEvent).filter(
            ExecutionEvent.execution_id == execution_id
        ).order_by(ExecutionEvent.timestamp).limit(limit).all()

    def list_by_node(
        self,
        execution_id: str,
        node_id: str
    ) -> List[ExecutionEvent]:
        """Get events for a specific node"""
        return self.session.query(ExecutionEvent).filter(
            and_(
                ExecutionEvent.execution_id == execution_id,
                ExecutionEvent.node_id == node_id
            )
        ).order_by(ExecutionEvent.timestamp).all()


# =============================================================================
# Artifact Repository
# =============================================================================

class ArtifactRepository:
    """Repository for execution artifacts"""

    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        execution_id: str,
        node_id: str,
        artifact_type: str,
        name: str,
        file_path: str = None,
        content: str = None,
        metadata: Dict[str, Any] = None
    ) -> Artifact:
        """Create a new artifact"""
        artifact = Artifact(
            execution_id=execution_id,
            node_id=node_id,
            artifact_type=artifact_type,
            name=name,
            file_path=file_path,
            content=content,
            artifact_metadata=metadata or {}
        )

        self.session.add(artifact)
        self.session.commit()
        self.session.refresh(artifact)

        logger.info(f"Created artifact: {name} for node: {node_id}")
        return artifact

    def list_by_execution(self, execution_id: str) -> List[Artifact]:
        """Get all artifacts for an execution"""
        return self.session.query(Artifact).filter(
            Artifact.execution_id == execution_id
        ).order_by(Artifact.created_at).all()

    def list_by_node(self, execution_id: str, node_id: str) -> List[Artifact]:
        """Get artifacts for a specific node"""
        return self.session.query(Artifact).filter(
            and_(
                Artifact.execution_id == execution_id,
                Artifact.node_id == node_id
            )
        ).order_by(Artifact.created_at).all()


# =============================================================================
# Unified Repository Factory
# =============================================================================

class RepositoryFactory:
    """Factory for creating repository instances"""

    def __init__(self, session: Session):
        self.session = session
        self.workflow = WorkflowRepository(session)
        self.execution = ExecutionRepository(session)
        self.node_state = NodeStateRepository(session)
        self.event = EventRepository(session)
        self.artifact = ArtifactRepository(session)
