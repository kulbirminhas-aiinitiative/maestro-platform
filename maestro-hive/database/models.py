#!/usr/bin/env python3
"""
SQLAlchemy models for DAG workflow persistence.

Provides database schema for:
- Workflow definitions (DAGs)
- Workflow executions
- Node states
- Execution events
- Artifacts
"""

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, DateTime, JSON,
    ForeignKey, Enum as SQLEnum, Index, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum
import uuid

Base = declarative_base()


# =============================================================================
# Enums
# =============================================================================

class WorkflowStatus(str, Enum):
    """Workflow execution status"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class NodeStatus(str, Enum):
    """Node execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class EventType(str, Enum):
    """Execution event types"""
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"
    WORKFLOW_PAUSED = "workflow_paused"
    WORKFLOW_RESUMED = "workflow_resumed"
    NODE_STARTED = "node_started"
    NODE_COMPLETED = "node_completed"
    NODE_FAILED = "node_failed"
    NODE_RETRYING = "node_retrying"


# =============================================================================
# Models
# =============================================================================

class WorkflowDefinition(Base):
    """
    Workflow definition (DAG structure).

    Stores the workflow graph structure, nodes, edges, and metadata.
    Multiple executions can reference the same definition.
    """
    __tablename__ = "workflow_definitions"

    id = Column(String(255), primary_key=True)  # workflow_id
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    workflow_type = Column(String(50), nullable=False)  # 'linear', 'parallel', 'custom'
    version = Column(Integer, default=1)

    # DAG structure (stored as JSON)
    nodes = Column(JSON, nullable=False)  # {node_id: {name, type, config, ...}}
    edges = Column(JSON, nullable=False)  # [{source, target, condition}, ...]
    workflow_metadata = Column(JSON, default=dict)  # Custom metadata

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    executions = relationship("WorkflowExecution", back_populates="workflow", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_workflow_name', 'name'),
        Index('idx_workflow_type', 'workflow_type'),
        Index('idx_workflow_created', 'created_at'),
    )

    def __repr__(self):
        return f"<WorkflowDefinition(id={self.id}, name={self.name}, type={self.workflow_type})>"


class WorkflowExecution(Base):
    """
    Workflow execution instance.

    Tracks a single execution of a workflow definition.
    Contains execution context, status, and timing information.
    """
    __tablename__ = "workflow_executions"

    id = Column(String(255), primary_key=True)  # execution_id
    workflow_id = Column(String(255), ForeignKey("workflow_definitions.id"), nullable=False)

    # Execution status
    status = Column(SQLEnum(WorkflowStatus), default=WorkflowStatus.PENDING, nullable=False)
    current_phase = Column(String(100), nullable=True)  # Current executing phase

    # Context and inputs
    initial_context = Column(JSON, default=dict)  # Initial inputs
    final_context = Column(JSON, nullable=True)  # Final outputs
    global_context = Column(JSON, default=dict)  # Shared context across nodes

    # Progress tracking
    total_nodes = Column(Integer, default=0)
    completed_nodes = Column(Integer, default=0)
    failed_nodes = Column(Integer, default=0)
    progress_percent = Column(Float, default=0.0)

    # Timestamps
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    paused_at = Column(DateTime, nullable=True)

    # Error tracking
    error_message = Column(Text, nullable=True)
    error_node_id = Column(String(255), nullable=True)

    # Metadata
    execution_metadata = Column(JSON, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    workflow = relationship("WorkflowDefinition", back_populates="executions")
    node_states = relationship("NodeState", back_populates="execution", cascade="all, delete-orphan")
    events = relationship("ExecutionEvent", back_populates="execution", cascade="all, delete-orphan")
    artifacts = relationship("Artifact", back_populates="execution", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_execution_workflow', 'workflow_id'),
        Index('idx_execution_status', 'status'),
        Index('idx_execution_started', 'started_at'),
        Index('idx_execution_created', 'created_at'),
    )

    def __repr__(self):
        return f"<WorkflowExecution(id={self.id}, workflow={self.workflow_id}, status={self.status.value})>"


class NodeState(Base):
    """
    Individual node execution state.

    Tracks the execution state of a single node within a workflow execution.
    """
    __tablename__ = "node_states"

    id = Column(String(255), primary_key=True, default=lambda: str(uuid.uuid4()))
    execution_id = Column(String(255), ForeignKey("workflow_executions.id"), nullable=False)
    node_id = Column(String(255), nullable=False)

    # Node information
    node_name = Column(String(255), nullable=False)
    node_type = Column(String(100), nullable=False)  # 'phase', 'task', 'condition', etc.

    # Execution status
    status = Column(SQLEnum(NodeStatus), default=NodeStatus.PENDING, nullable=False)
    attempt_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)

    # Input/Output
    inputs = Column(JSON, default=dict)  # Node inputs
    outputs = Column(JSON, nullable=True)  # Node outputs

    # Timestamps
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)

    # Error tracking
    error_message = Column(Text, nullable=True)
    error_type = Column(String(255), nullable=True)

    # Quality metrics
    quality_score = Column(Float, nullable=True)
    quality_threshold = Column(Float, default=0.7)
    contract_fulfilled = Column(Boolean, nullable=True)

    # Metadata
    node_metadata = Column(JSON, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    execution = relationship("WorkflowExecution", back_populates="node_states")

    # Indexes and constraints
    __table_args__ = (
        Index('idx_node_execution', 'execution_id'),
        Index('idx_node_status', 'status'),
        Index('idx_node_started', 'started_at'),
        UniqueConstraint('execution_id', 'node_id', name='uq_execution_node'),
    )

    def __repr__(self):
        return f"<NodeState(node={self.node_id}, status={self.status.value}, attempts={self.attempt_count})>"


class ExecutionEvent(Base):
    """
    Execution event log.

    Records all events during workflow execution for debugging and monitoring.
    """
    __tablename__ = "execution_events"

    id = Column(String(255), primary_key=True, default=lambda: str(uuid.uuid4()))
    execution_id = Column(String(255), ForeignKey("workflow_executions.id"), nullable=False)

    # Event information
    event_type = Column(SQLEnum(EventType), nullable=False)
    node_id = Column(String(255), nullable=True)  # Null for workflow-level events

    # Event data
    message = Column(Text, nullable=True)
    data = Column(JSON, default=dict)  # Additional event data

    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    execution = relationship("WorkflowExecution", back_populates="events")

    # Indexes
    __table_args__ = (
        Index('idx_event_execution', 'execution_id'),
        Index('idx_event_type', 'event_type'),
        Index('idx_event_timestamp', 'timestamp'),
        Index('idx_event_node', 'node_id'),
    )

    def __repr__(self):
        return f"<ExecutionEvent(type={self.event_type.value}, node={self.node_id}, time={self.timestamp})>"


class Artifact(Base):
    """
    Execution artifacts.

    Stores generated files, reports, and other outputs from workflow executions.
    """
    __tablename__ = "artifacts"

    id = Column(String(255), primary_key=True, default=lambda: str(uuid.uuid4()))
    execution_id = Column(String(255), ForeignKey("workflow_executions.id"), nullable=False)
    node_id = Column(String(255), nullable=True)  # Node that generated artifact

    # Artifact information
    artifact_type = Column(String(100), nullable=False)  # 'file', 'report', 'log', etc.
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Storage
    file_path = Column(String(1024), nullable=True)  # Local file path
    s3_uri = Column(String(1024), nullable=True)  # S3 URI (for cloud storage)
    content = Column(Text, nullable=True)  # For small artifacts (inline)
    content_type = Column(String(100), nullable=True)  # MIME type
    size_bytes = Column(Integer, nullable=True)

    # Metadata
    artifact_metadata = Column(JSON, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    execution = relationship("WorkflowExecution", back_populates="artifacts")

    # Indexes
    __table_args__ = (
        Index('idx_artifact_execution', 'execution_id'),
        Index('idx_artifact_node', 'node_id'),
        Index('idx_artifact_type', 'artifact_type'),
        Index('idx_artifact_created', 'created_at'),
    )

    def __repr__(self):
        return f"<Artifact(name={self.name}, type={self.artifact_type}, node={self.node_id})>"


# =============================================================================
# Helper Functions
# =============================================================================

def generate_execution_id(workflow_id: str) -> str:
    """Generate unique execution ID"""
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    return f"exec_{workflow_id}_{timestamp}_{unique_id}"


def calculate_progress(total_nodes: int, completed_nodes: int) -> float:
    """Calculate execution progress percentage"""
    if total_nodes == 0:
        return 0.0
    return round((completed_nodes / total_nodes) * 100, 2)
