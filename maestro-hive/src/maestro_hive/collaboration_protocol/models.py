"""Collaboration Protocol Models - Core data structures."""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4


class MessageType(Enum):
    """Types of collaboration messages."""
    REQUEST = "request"
    RESPONSE = "response"
    BROADCAST = "broadcast"
    HANDOFF = "handoff"
    STATUS = "status"


class TaskStatus(Enum):
    """Status of collaborative tasks."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class CollaborationMessage:
    """Message between collaborating agents."""
    id: UUID = field(default_factory=uuid4)
    sender_id: UUID = field(default_factory=uuid4)
    recipient_id: Optional[UUID] = None  # None for broadcast
    message_type: MessageType = MessageType.REQUEST
    content: Dict[str, Any] = field(default_factory=dict)
    correlation_id: Optional[UUID] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {"id": str(self.id), "sender": str(self.sender_id),
                "recipient": str(self.recipient_id) if self.recipient_id else None,
                "type": self.message_type.value, "content": self.content,
                "correlation": str(self.correlation_id) if self.correlation_id else None,
                "timestamp": self.timestamp.isoformat()}


@dataclass
class TaskAssignment:
    """Assignment of task to an agent."""
    id: UUID = field(default_factory=uuid4)
    task_id: UUID = field(default_factory=uuid4)
    agent_id: UUID = field(default_factory=uuid4)
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 5
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[UUID] = field(default_factory=list)
    assigned_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    def complete(self, output: Dict[str, Any]):
        self.status = TaskStatus.COMPLETED
        self.output_data = output
        self.completed_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return {"id": str(self.id), "task_id": str(self.task_id),
                "agent_id": str(self.agent_id), "status": self.status.value,
                "priority": self.priority, "dependencies": [str(d) for d in self.dependencies]}


@dataclass
class CollaborationSession:
    """Session for multi-agent collaboration."""
    id: UUID = field(default_factory=uuid4)
    participants: List[UUID] = field(default_factory=list)
    coordinator_id: Optional[UUID] = None
    tasks: List[TaskAssignment] = field(default_factory=list)
    messages: List[CollaborationMessage] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def add_participant(self, agent_id: UUID):
        if agent_id not in self.participants:
            self.participants.append(agent_id)
    
    def add_task(self, task: TaskAssignment):
        self.tasks.append(task)
    
    def get_pending_tasks(self) -> List[TaskAssignment]:
        return [t for t in self.tasks if t.status in [TaskStatus.PENDING, TaskStatus.ASSIGNED]]
    
    def to_dict(self) -> Dict[str, Any]:
        return {"id": str(self.id), "participants": [str(p) for p in self.participants],
                "coordinator": str(self.coordinator_id) if self.coordinator_id else None,
                "task_count": len(self.tasks), "message_count": len(self.messages)}
