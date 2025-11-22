"""
Database models for persistent state
Uses SQLAlchemy for PostgreSQL backend
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
import json

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, JSON,
    ForeignKey, Boolean, Enum as SQLEnum, Index, Table
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class TaskStatus(str, Enum):
    """Enhanced task status enum"""
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    BLOCKED = "blocked"
    AWAITING_REVIEW = "awaiting_review"
    CANCELLED = "cancelled"


class MessageType(str, Enum):
    """Message type enum"""
    INFO = "info"
    QUESTION = "question"
    RESPONSE = "response"
    ALERT = "alert"
    STATUS = "status"
    ERROR = "error"


class MembershipState(str, Enum):
    """Team membership state enum for dynamic team management"""
    INITIALIZING = "initializing"  # Member is being onboarded
    ACTIVE = "active"              # Actively working on tasks
    ON_STANDBY = "on_standby"      # Available but not actively working
    RETIRED = "retired"            # No longer needed, gracefully removed
    SUSPENDED = "suspended"        # Temporarily suspended (performance issues)
    REASSIGNED = "reassigned"      # Moved to another team/project


# Association table for task dependencies (many-to-many)
task_dependencies = Table(
    'task_dependencies',
    Base.metadata,
    Column('task_id', String, ForeignKey('tasks.id', ondelete='CASCADE'), primary_key=True),
    Column('depends_on_id', String, ForeignKey('tasks.id', ondelete='CASCADE'), primary_key=True),
    Index('idx_task_deps_task', 'task_id'),
    Index('idx_task_deps_depends', 'depends_on_id')
)


class Message(Base):
    """Message model with full history"""
    __tablename__ = 'messages'

    id = Column(String, primary_key=True)
    team_id = Column(String, nullable=False, index=True)
    from_agent = Column(String, nullable=False, index=True)
    to_agent = Column(String, nullable=True, index=True)  # None = broadcast
    message_type = Column(SQLEnum(MessageType), default=MessageType.INFO)
    content = Column(Text, nullable=False)
    extra_metadata = Column('metadata', JSON, default=dict)  # Renamed to avoid SQLAlchemy reserved word
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    thread_id = Column(String, nullable=True, index=True)  # For conversation threading

    __table_args__ = (
        Index('idx_message_team_time', 'team_id', 'timestamp'),
        Index('idx_message_thread', 'thread_id', 'timestamp'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "team_id": self.team_id,
            "from": self.from_agent,
            "to": self.to_agent,
            "type": self.message_type.value if isinstance(self.message_type, Enum) else self.message_type,
            "message": self.content,
            "metadata": self.extra_metadata,
            "timestamp": self.timestamp.isoformat(),
            "thread_id": self.thread_id
        }


class Task(Base):
    """Enhanced task model with dependency support"""
    __tablename__ = 'tasks'

    id = Column(String, primary_key=True)
    team_id = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.PENDING, index=True)
    priority = Column(Integer, default=0, index=True)  # Higher = more important
    required_role = Column(String, nullable=True, index=True)
    assigned_to = Column(String, nullable=True, index=True)
    assigned_to_role = Column(String, nullable=True, index=True)  # Role-based assignment (e.g., "Security Auditor")
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    claimed_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Workflow support
    parent_task_id = Column(String, ForeignKey('tasks.id'), nullable=True, index=True)
    workflow_id = Column(String, nullable=True, index=True)

    # Results
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)

    # Metadata
    extra_metadata = Column('metadata', JSON, default=dict)
    tags = Column(JSON, default=list)

    # Relationships
    parent_task = relationship("Task", remote_side=[id], backref="subtasks")
    dependencies = relationship(
        "Task",
        secondary=task_dependencies,
        primaryjoin=id == task_dependencies.c.task_id,
        secondaryjoin=id == task_dependencies.c.depends_on_id,
        backref="dependent_tasks"
    )

    __table_args__ = (
        Index('idx_task_team_status', 'team_id', 'status'),
        Index('idx_task_team_priority', 'team_id', 'priority'),
        Index('idx_task_workflow', 'workflow_id', 'status'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "team_id": self.team_id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value if isinstance(self.status, Enum) else self.status,
            "priority": self.priority,
            "required_role": self.required_role,
            "assigned_to": self.assigned_to,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "claimed_at": self.claimed_at.isoformat() if self.claimed_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "parent_task_id": self.parent_task_id,
            "workflow_id": self.workflow_id,
            "result": self.result,
            "error": self.error,
            "metadata": self.extra_metadata,
            "tags": self.tags,
            "dependency_ids": [dep.id for dep in self.dependencies]
        }

    def can_execute(self) -> bool:
        """Check if all dependencies are completed"""
        return all(dep.status == TaskStatus.SUCCESS for dep in self.dependencies)


class KnowledgeItem(Base):
    """Knowledge base with versioning"""
    __tablename__ = 'knowledge'

    id = Column(String, primary_key=True)
    team_id = Column(String, nullable=False, index=True)
    key = Column(String, nullable=False, index=True)
    value = Column(Text, nullable=False)
    category = Column(String, nullable=True, index=True)
    source_agent = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    version = Column(Integer, default=1)
    extra_metadata = Column('metadata', JSON, default=dict)
    tags = Column(JSON, default=list)

    __table_args__ = (
        Index('idx_knowledge_team_key', 'team_id', 'key'),
        Index('idx_knowledge_category', 'team_id', 'category'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "key": self.key,
            "value": self.value,
            "category": self.category,
            "from": self.source_agent,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "version": self.version,
            "metadata": self.extra_metadata,
            "tags": self.tags
        }


class Artifact(Base):
    """Artifact storage with S3/file references"""
    __tablename__ = 'artifacts'

    id = Column(String, primary_key=True)
    team_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    artifact_type = Column(String, nullable=False)  # code, document, data, etc.
    description = Column(Text)

    # Storage reference (not the actual content)
    storage_backend = Column(String, nullable=False)  # 's3', 'local', 'redis'
    storage_path = Column(String, nullable=False)

    # Metadata
    size_bytes = Column(Integer)
    mime_type = Column(String)
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    extra_metadata = Column('metadata', JSON, default=dict)
    tags = Column(JSON, default=list)

    # Association
    task_id = Column(String, ForeignKey('tasks.id'), nullable=True, index=True)

    __table_args__ = (
        Index('idx_artifact_team_type', 'team_id', 'artifact_type'),
        Index('idx_artifact_task', 'task_id'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "team_id": self.team_id,
            "name": self.name,
            "type": self.artifact_type,
            "description": self.description,
            "storage_backend": self.storage_backend,
            "storage_path": self.storage_path,
            "size_bytes": self.size_bytes,
            "mime_type": self.mime_type,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "metadata": self.extra_metadata,
            "tags": self.tags,
            "task_id": self.task_id
        }


class AgentState(Base):
    """Agent status and state tracking"""
    __tablename__ = 'agent_states'

    id = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(String, nullable=False, index=True)
    agent_id = Column(String, nullable=False, index=True)
    role = Column(String, nullable=False)
    status = Column(String, nullable=False)  # idle, working, waiting, error
    current_task_id = Column(String, ForeignKey('tasks.id'), nullable=True)
    message = Column(Text)
    extra_metadata = Column('metadata', JSON, default=dict)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)

    # Performance metrics
    tasks_completed = Column(Integer, default=0)
    tasks_failed = Column(Integer, default=0)

    __table_args__ = (
        Index('idx_agent_team_agent', 'team_id', 'agent_id', unique=True),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "role": self.role,
            "status": self.status,
            "current_task": self.current_task_id,
            "message": self.message,
            "metadata": self.extra_metadata,
            "updated_at": self.updated_at.isoformat(),
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed
        }


class Decision(Base):
    """Decision tracking with voting"""
    __tablename__ = 'decisions'

    id = Column(String, primary_key=True)
    team_id = Column(String, nullable=False, index=True)
    decision = Column(Text, nullable=False)
    rationale = Column(Text)
    proposed_by = Column(String, nullable=False)
    proposed_at = Column(DateTime, default=datetime.utcnow)

    # Voting
    votes = Column(JSON, default=dict)  # {agent_id: "approve"/"reject"/"abstain"}
    status = Column(String, default="pending")  # pending, approved, rejected
    finalized_at = Column(DateTime, nullable=True)

    # Context
    task_id = Column(String, ForeignKey('tasks.id'), nullable=True, index=True)
    extra_metadata = Column('metadata', JSON, default=dict)

    __table_args__ = (
        Index('idx_decision_team_status', 'team_id', 'status'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "decision": self.decision,
            "rationale": self.rationale,
            "proposed_by": self.proposed_by,
            "proposed_at": self.proposed_at.isoformat(),
            "votes": self.votes,
            "status": self.status,
            "finalized_at": self.finalized_at.isoformat() if self.finalized_at else None,
            "task_id": self.task_id,
            "metadata": self.metadata
        }


class WorkflowDefinition(Base):
    """Workflow/DAG definitions"""
    __tablename__ = 'workflows'

    id = Column(String, primary_key=True)
    team_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)

    # DAG definition (stored as JSON)
    dag_definition = Column(JSON, nullable=False)
    # {
    #   "nodes": [{"id": "task1", "type": "code", ...}],
    #   "edges": [{"from": "task1", "to": "task2"}]
    # }

    created_by = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Workflow state
    status = Column(String, default="active")  # active, paused, completed, failed
    extra_metadata = Column('metadata', JSON, default=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "team_id": self.team_id,
            "name": self.name,
            "description": self.description,
            "dag_definition": self.dag_definition,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "status": self.status,
            "metadata": self.metadata
        }


class TaskDependency(Base):
    """Explicit task dependency tracking for querying"""
    __tablename__ = 'task_dependency_log'

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String, ForeignKey('tasks.id'), nullable=False, index=True)
    depends_on_id = Column(String, ForeignKey('tasks.id'), nullable=False, index=True)
    dependency_type = Column(String, default="hard")  # hard, soft, optional
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_dep_task', 'task_id', 'depends_on_id', unique=True),
    )


class TeamMembership(Base):
    """
    Team membership tracking for dynamic team management

    Tracks the lifecycle of team members including:
    - When they join/leave
    - Their current state (active, standby, retired, etc.)
    - Performance metrics
    - Reason for state changes
    """
    __tablename__ = 'team_memberships'

    id = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(String, nullable=False, index=True)
    agent_id = Column(String, nullable=False, index=True)
    persona_id = Column(String, nullable=False)  # e.g., "requirement_analyst"
    role_id = Column(String, nullable=False)     # e.g., "analyst"

    # Lifecycle
    state = Column(SQLEnum(MembershipState), default=MembershipState.INITIALIZING, index=True)
    joined_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    activated_at = Column(DateTime, nullable=True)  # When moved to ACTIVE
    retired_at = Column(DateTime, nullable=True)    # When moved to RETIRED

    # State transition history
    state_history = Column(JSON, default=list)  # [{state: "active", timestamp: "...", reason: "..."}]

    # Performance metrics
    performance_score = Column(Integer, default=100)  # 0-100 score
    task_completion_rate = Column(Integer, default=0)  # Percentage
    average_task_duration_hours = Column(Integer, nullable=True)
    collaboration_score = Column(Integer, default=50)  # 0-100, based on message engagement

    # Metadata
    added_by = Column(String, nullable=False)  # Who added this member
    added_reason = Column(Text, nullable=True)  # Why they were added
    retirement_reason = Column(Text, nullable=True)  # Why they were retired
    extra_metadata = Column('metadata', JSON, default=dict)

    __table_args__ = (
        Index('idx_membership_team_agent', 'team_id', 'agent_id'),
        Index('idx_membership_team_state', 'team_id', 'state'),
        Index('idx_membership_persona', 'team_id', 'persona_id'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "team_id": self.team_id,
            "agent_id": self.agent_id,
            "persona_id": self.persona_id,
            "role_id": self.role_id,
            "state": self.state.value if isinstance(self.state, Enum) else self.state,
            "joined_at": self.joined_at.isoformat(),
            "activated_at": self.activated_at.isoformat() if self.activated_at else None,
            "retired_at": self.retired_at.isoformat() if self.retired_at else None,
            "state_history": self.state_history,
            "performance_score": self.performance_score,
            "task_completion_rate": self.task_completion_rate,
            "average_task_duration_hours": self.average_task_duration_hours,
            "collaboration_score": self.collaboration_score,
            "added_by": self.added_by,
            "added_reason": self.added_reason,
            "retirement_reason": self.retirement_reason,
            "metadata": self.extra_metadata
        }

    def update_state(self, new_state: MembershipState, reason: str = None):
        """Update membership state and record in history"""
        old_state = self.state
        self.state = new_state

        # Record in history
        if not isinstance(self.state_history, list):
            self.state_history = []

        self.state_history.append({
            "from_state": old_state.value if isinstance(old_state, Enum) else old_state,
            "to_state": new_state.value if isinstance(new_state, Enum) else new_state,
            "timestamp": datetime.utcnow().isoformat(),
            "reason": reason
        })

        # Update lifecycle timestamps
        if new_state == MembershipState.ACTIVE and not self.activated_at:
            self.activated_at = datetime.utcnow()
        elif new_state == MembershipState.RETIRED and not self.retired_at:
            self.retired_at = datetime.utcnow()
            if reason:
                self.retirement_reason = reason


class RoleAssignment(Base):
    """
    Role-based assignment tracking

    Enables role abstraction: tasks assigned to roles (e.g., "Security Auditor")
    not specific agents. Agents can be dynamically assigned to fill roles.
    """
    __tablename__ = 'role_assignments'

    id = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(String, nullable=False, index=True)
    role_id = Column(String, nullable=False, index=True)  # "Security Auditor", "DBA Specialist"
    role_description = Column(Text, nullable=True)

    # Current assignment
    current_agent_id = Column(String, nullable=True, index=True)
    assigned_at = Column(DateTime, nullable=True)
    assigned_by = Column(String, nullable=True)

    # Assignment history
    assignment_history = Column(JSON, default=list)  # [{agent_id, from, to, reason}]

    # Role metadata
    is_required = Column(Boolean, default=True)  # Required for project
    is_active = Column(Boolean, default=True)    # Currently active role
    priority = Column(Integer, default=5)        # Role priority (higher = more critical)
    extra_metadata = Column('metadata', JSON, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_role_team_role', 'team_id', 'role_id', unique=True),
        Index('idx_role_agent', 'current_agent_id'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "team_id": self.team_id,
            "role_id": self.role_id,
            "role_description": self.role_description,
            "current_agent_id": self.current_agent_id,
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
            "assigned_by": self.assigned_by,
            "assignment_history": self.assignment_history,
            "is_required": self.is_required,
            "is_active": self.is_active,
            "priority": self.priority,
            "metadata": self.extra_metadata
        }

    def assign_agent(self, agent_id: str, assigned_by: str, reason: str = None):
        """Assign an agent to this role"""
        old_agent = self.current_agent_id

        # Record in history
        if not isinstance(self.assignment_history, list):
            self.assignment_history = []

        self.assignment_history.append({
            "from_agent": old_agent,
            "to_agent": agent_id,
            "assigned_by": assigned_by,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat()
        })

        # Update current assignment
        self.current_agent_id = agent_id
        self.assigned_at = datetime.utcnow()
        self.assigned_by = assigned_by


class KnowledgeHandoff(Base):
    """
    Knowledge handoff tracking for retiring team members

    Ensures knowledge is captured before members leave
    """
    __tablename__ = 'knowledge_handoffs'

    id = Column(String, primary_key=True)
    team_id = Column(String, nullable=False, index=True)
    agent_id = Column(String, nullable=False, index=True)
    persona_id = Column(String, nullable=False)

    # Handoff status
    status = Column(String, default="initiated")  # initiated, in_progress, completed, skipped
    initiated_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Checklist items
    artifacts_verified = Column(Boolean, default=False)
    documentation_complete = Column(Boolean, default=False)
    lessons_learned_captured = Column(Boolean, default=False)

    # Content
    lessons_learned = Column(Text, nullable=True)
    open_questions = Column(JSON, default=list)
    recommendations = Column(JSON, default=list)
    key_decisions = Column(JSON, default=list)
    artifacts_list = Column(JSON, default=list)

    # Metadata
    initiated_by = Column(String, nullable=False)
    completed_by = Column(String, nullable=True)
    extra_metadata = Column('metadata', JSON, default=dict)

    __table_args__ = (
        Index('idx_handoff_team_agent', 'team_id', 'agent_id'),
        Index('idx_handoff_status', 'status'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "team_id": self.team_id,
            "agent_id": self.agent_id,
            "persona_id": self.persona_id,
            "status": self.status,
            "initiated_at": self.initiated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "checklist": {
                "artifacts_verified": self.artifacts_verified,
                "documentation_complete": self.documentation_complete,
                "lessons_learned_captured": self.lessons_learned_captured
            },
            "lessons_learned": self.lessons_learned,
            "open_questions": self.open_questions,
            "recommendations": self.recommendations,
            "key_decisions": self.key_decisions,
            "artifacts_list": self.artifacts_list,
            "metadata": self.extra_metadata
        }

    def is_complete(self) -> bool:
        """Check if handoff checklist is complete"""
        return (
            self.artifacts_verified and
            self.documentation_complete and
            self.lessons_learned_captured
        )


# =============================================================================
# Parallel Execution Models - Speculative Execution & Convergent Design
# =============================================================================


class AssumptionStatus(str, Enum):
    """Assumption validation status"""
    ACTIVE = "active"          # Currently active assumption
    VALIDATED = "validated"    # Confirmed correct
    INVALIDATED = "invalidated"  # Proven wrong, needs rework
    SUPERSEDED = "superseded"  # Replaced by new information


class Assumption(Base):
    """
    Track speculative assumptions for parallel execution

    When teams work concurrently based on incomplete information,
    they make assumptions. These must be tracked and validated.
    """
    __tablename__ = 'assumptions'

    id = Column(String, primary_key=True)
    team_id = Column(String, nullable=False, index=True)

    # Who made the assumption
    made_by_agent = Column(String, nullable=False, index=True)
    made_by_role = Column(String, nullable=False)  # e.g., "Backend Lead"

    # What is assumed
    assumption_text = Column(Text, nullable=False)
    assumption_category = Column(String, nullable=False)  # "data_structure", "api_contract", "requirement"

    # Context
    related_artifact_type = Column(String, nullable=False)  # "requirement", "contract", "task"
    related_artifact_id = Column(String, nullable=False, index=True)

    # Validation
    status = Column(SQLEnum(AssumptionStatus), default=AssumptionStatus.ACTIVE, index=True)
    validated_at = Column(DateTime, nullable=True)
    validated_by = Column(String, nullable=True)
    validation_notes = Column(Text, nullable=True)

    # Impact tracking
    dependent_artifacts = Column(JSON, default=list)  # List of artifacts that depend on this assumption

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    extra_metadata = Column('metadata', JSON, default=dict)

    __table_args__ = (
        Index('idx_assumption_team_status', 'team_id', 'status'),
        Index('idx_assumption_agent', 'made_by_agent', 'status'),
        Index('idx_assumption_artifact', 'related_artifact_id'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "team_id": self.team_id,
            "made_by_agent": self.made_by_agent,
            "made_by_role": self.made_by_role,
            "assumption_text": self.assumption_text,
            "assumption_category": self.assumption_category,
            "related_artifact_type": self.related_artifact_type,
            "related_artifact_id": self.related_artifact_id,
            "status": self.status.value if isinstance(self.status, Enum) else self.status,
            "validated_at": self.validated_at.isoformat() if self.validated_at else None,
            "validated_by": self.validated_by,
            "validation_notes": self.validation_notes,
            "dependent_artifacts": self.dependent_artifacts,
            "created_at": self.created_at.isoformat(),
            "metadata": self.extra_metadata
        }


class ContractStatus(str, Enum):
    """API contract status"""
    DRAFT = "draft"        # Initial draft
    ACTIVE = "active"      # Currently in use
    DEPRECATED = "deprecated"  # Being phased out
    SUPERSEDED = "superseded"  # Replaced by newer version


class Contract(Base):
    """
    API Contract versioning for parallel work

    Contracts are the decoupling layer that enables frontend and backend
    to work in parallel using mocks.
    """
    __tablename__ = 'contracts'

    id = Column(String, primary_key=True)
    team_id = Column(String, nullable=False, index=True)

    # Contract identification
    contract_name = Column(String, nullable=False, index=True)  # e.g., "FraudAlertsAPI"
    version = Column(String, nullable=False)  # e.g., "v0.1", "v0.2"

    # Contract definition
    contract_type = Column(String, nullable=False)  # "REST_API", "GraphQL", "gRPC", "EventStream"
    specification = Column(JSON, nullable=False)  # Full contract spec (OpenAPI, etc.)

    # Ownership
    owner_role = Column(String, nullable=False)  # Role responsible (usually "Tech Lead")
    owner_agent = Column(String, nullable=False)

    # Status
    status = Column(SQLEnum(ContractStatus), default=ContractStatus.DRAFT, index=True)

    # Dependencies
    consumers = Column(JSON, default=list)  # List of agents/roles depending on this contract
    supersedes_contract_id = Column(String, nullable=True)  # Previous version

    # Change tracking
    changes_from_previous = Column(JSON, nullable=True)  # What changed in this version
    breaking_changes = Column(Boolean, default=False)  # Contains breaking changes

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    activated_at = Column(DateTime, nullable=True)
    extra_metadata = Column('metadata', JSON, default=dict)

    __table_args__ = (
        Index('idx_contract_team_name_version', 'team_id', 'contract_name', 'version', unique=True),
        Index('idx_contract_status', 'team_id', 'status'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "team_id": self.team_id,
            "contract_name": self.contract_name,
            "version": self.version,
            "contract_type": self.contract_type,
            "specification": self.specification,
            "owner_role": self.owner_role,
            "owner_agent": self.owner_agent,
            "status": self.status.value if isinstance(self.status, Enum) else self.status,
            "consumers": self.consumers,
            "supersedes_contract_id": self.supersedes_contract_id,
            "changes_from_previous": self.changes_from_previous,
            "breaking_changes": self.breaking_changes,
            "created_at": self.created_at.isoformat(),
            "activated_at": self.activated_at.isoformat() if self.activated_at else None,
            "metadata": self.extra_metadata
        }


class DependencyEdge(Base):
    """
    Dependency graph edges for impact analysis

    Tracks: Requirement -> Design -> Contract -> Code -> Test
    """
    __tablename__ = 'dependency_edges'

    id = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(String, nullable=False, index=True)

    # Source artifact
    source_type = Column(String, nullable=False)  # "requirement", "contract", "task"
    source_id = Column(String, nullable=False, index=True)

    # Target artifact (depends on source)
    target_type = Column(String, nullable=False)
    target_id = Column(String, nullable=False, index=True)

    # Dependency metadata
    dependency_type = Column(String, nullable=False)  # "implements", "tests", "consumes", "produces"
    is_blocking = Column(Boolean, default=True)  # If true, target cannot proceed without source

    # Tracking
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String, nullable=False)

    __table_args__ = (
        Index('idx_dep_team_source', 'team_id', 'source_type', 'source_id'),
        Index('idx_dep_team_target', 'team_id', 'target_type', 'target_id'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "team_id": self.team_id,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "dependency_type": self.dependency_type,
            "is_blocking": self.is_blocking,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by
        }


class ConflictSeverity(str, Enum):
    """Conflict severity levels"""
    LOW = "low"          # Minor inconsistency
    MEDIUM = "medium"    # Significant mismatch
    HIGH = "high"        # Major conflict requiring immediate attention
    CRITICAL = "critical"  # Blocking progress


class ConflictEvent(Base):
    """
    Detected conflicts between artifacts

    AI Orchestrator detects inconsistencies and creates conflict events
    """
    __tablename__ = 'conflict_events'

    id = Column(String, primary_key=True)
    team_id = Column(String, nullable=False, index=True)

    # Conflict description
    conflict_type = Column(String, nullable=False)  # "contract_breach", "assumption_invalidation", "requirement_mismatch"
    severity = Column(SQLEnum(ConflictSeverity), nullable=False, index=True)
    description = Column(Text, nullable=False)

    # Conflicting artifacts
    artifacts_involved = Column(JSON, nullable=False)  # [{type, id, owner}]

    # Detection
    detected_at = Column(DateTime, default=datetime.utcnow, index=True)
    detected_by = Column(String, default="ai_orchestrator")

    # Resolution
    status = Column(String, default="open")  # "open", "in_progress", "resolved", "ignored"
    resolved_at = Column(DateTime, nullable=True)
    resolution_notes = Column(Text, nullable=True)

    # Impact
    affected_agents = Column(JSON, default=list)  # List of agents affected
    estimated_rework_hours = Column(Integer, nullable=True)

    # Convergence
    convergence_event_id = Column(String, nullable=True, index=True)  # Link to convergence event

    extra_metadata = Column('metadata', JSON, default=dict)

    __table_args__ = (
        Index('idx_conflict_team_status', 'team_id', 'status'),
        Index('idx_conflict_severity', 'team_id', 'severity'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "team_id": self.team_id,
            "conflict_type": self.conflict_type,
            "severity": self.severity.value if isinstance(self.severity, Enum) else self.severity,
            "description": self.description,
            "artifacts_involved": self.artifacts_involved,
            "detected_at": self.detected_at.isoformat(),
            "detected_by": self.detected_by,
            "status": self.status,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolution_notes": self.resolution_notes,
            "affected_agents": self.affected_agents,
            "estimated_rework_hours": self.estimated_rework_hours,
            "convergence_event_id": self.convergence_event_id,
            "metadata": self.extra_metadata
        }


class ConvergenceEvent(Base):
    """
    Team convergence session to resolve conflicts

    When conflicts are detected, team converges to synchronize
    """
    __tablename__ = 'convergence_events'

    id = Column(String, primary_key=True)
    team_id = Column(String, nullable=False, index=True)

    # Trigger
    trigger_type = Column(String, nullable=False)  # "conflict_detected", "major_change", "phase_completion"
    trigger_description = Column(Text, nullable=False)

    # Related conflicts
    conflict_ids = Column(JSON, default=list)  # List of conflict IDs being resolved

    # Participants
    participants = Column(JSON, nullable=False)  # List of agent IDs participating
    orchestrator_id = Column(String, default="ai_orchestrator")

    # Timeline
    initiated_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)

    # Outcomes
    status = Column(String, default="in_progress")  # "in_progress", "completed", "cancelled"
    decisions_made = Column(JSON, default=list)  # List of decisions
    artifacts_updated = Column(JSON, default=list)  # List of artifacts changed
    rework_performed = Column(JSON, default=list)  # List of rework items

    # Metrics
    duration_minutes = Column(Integer, nullable=True)
    actual_rework_hours = Column(Integer, nullable=True)

    extra_metadata = Column('metadata', JSON, default=dict)

    __table_args__ = (
        Index('idx_convergence_team_status', 'team_id', 'status'),
        Index('idx_convergence_time', 'team_id', 'initiated_at'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "team_id": self.team_id,
            "trigger_type": self.trigger_type,
            "trigger_description": self.trigger_description,
            "conflict_ids": self.conflict_ids,
            "participants": self.participants,
            "orchestrator_id": self.orchestrator_id,
            "initiated_at": self.initiated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "status": self.status,
            "decisions_made": self.decisions_made,
            "artifacts_updated": self.artifacts_updated,
            "rework_performed": self.rework_performed,
            "duration_minutes": self.duration_minutes,
            "actual_rework_hours": self.actual_rework_hours,
            "metadata": self.extra_metadata
        }


class ArtifactVersion(Base):
    """
    Generic artifact versioning for change tracking

    Tracks evolution of requirements, contracts, code, tests
    """
    __tablename__ = 'artifact_versions'

    id = Column(String, primary_key=True)
    team_id = Column(String, nullable=False, index=True)

    # Artifact identification
    artifact_type = Column(String, nullable=False, index=True)  # "requirement", "contract", "task", "decision"
    artifact_id = Column(String, nullable=False, index=True)
    version_number = Column(Integer, nullable=False)

    # Content snapshot
    content = Column(JSON, nullable=False)  # Full artifact content at this version

    # Change tracking
    changed_by = Column(String, nullable=False)
    changed_at = Column(DateTime, default=datetime.utcnow, index=True)
    change_reason = Column(Text, nullable=True)
    changes_from_previous = Column(JSON, nullable=True)  # Diff from previous version

    # Impact
    triggered_conflicts = Column(JSON, default=list)  # Conflict IDs triggered by this change

    extra_metadata = Column('metadata', JSON, default=dict)

    __table_args__ = (
        Index('idx_artifact_version_team_type_id', 'team_id', 'artifact_type', 'artifact_id'),
        Index('idx_artifact_version_time', 'team_id', 'changed_at'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "team_id": self.team_id,
            "artifact_type": self.artifact_type,
            "artifact_id": self.artifact_id,
            "version_number": self.version_number,
            "content": self.content,
            "changed_by": self.changed_by,
            "changed_at": self.changed_at.isoformat(),
            "change_reason": self.change_reason,
            "changes_from_previous": self.changes_from_previous,
            "triggered_conflicts": self.triggered_conflicts,
            "metadata": self.extra_metadata
        }
