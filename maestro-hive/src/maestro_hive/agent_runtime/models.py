"""Agent Runtime Models - Core data structures for agent execution."""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
import json


class AgentState(Enum):
    """Agent execution state."""
    CREATED = "created"
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class ExecutionMetrics:
    """Metrics for agent execution (AC-2544-4)."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_tokens_used: int = 0
    avg_response_time_ms: float = 0.0
    start_time: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    memory_usage_mb: float = 0.0
    tools_invoked: Dict[str, int] = field(default_factory=dict)
    
    def record_request(self, success: bool, tokens: int, response_time_ms: float):
        """Record a request execution."""
        self.total_requests += 1
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
        self.total_tokens_used += tokens
        n = self.total_requests
        self.avg_response_time_ms = ((n - 1) * self.avg_response_time_ms + response_time_ms) / n
        self.last_activity = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": self.successful_requests / max(self.total_requests, 1),
            "total_tokens_used": self.total_tokens_used,
            "avg_response_time_ms": self.avg_response_time_ms,
            "uptime_seconds": (datetime.utcnow() - self.start_time).total_seconds() if self.start_time else 0,
            "memory_usage_mb": self.memory_usage_mb,
            "tools_invoked": self.tools_invoked,
        }


@dataclass
class AgentContext:
    """Context for agent execution (AC-2544-5)."""
    id: UUID = field(default_factory=uuid4)
    persona_id: Optional[UUID] = None
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    working_memory: Dict[str, Any] = field(default_factory=dict)
    loaded_knowledge: List[UUID] = field(default_factory=list)
    active_tools: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def add_message(self, role: str, content: str):
        """Add message to conversation history."""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
        })
        self.updated_at = datetime.utcnow()
    
    def save_to_memory(self, key: str, value: Any):
        """Save to working memory."""
        self.working_memory[key] = value
        self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "persona_id": str(self.persona_id) if self.persona_id else None,
            "conversation_history": self.conversation_history,
            "working_memory": self.working_memory,
            "loaded_knowledge": [str(k) for k in self.loaded_knowledge],
            "active_tools": self.active_tools,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentContext":
        return cls(
            id=UUID(data["id"]) if data.get("id") else uuid4(),
            persona_id=UUID(data["persona_id"]) if data.get("persona_id") else None,
            conversation_history=data.get("conversation_history", []),
            working_memory=data.get("working_memory", {}),
            loaded_knowledge=[UUID(k) for k in data.get("loaded_knowledge", [])],
            active_tools=data.get("active_tools", []),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.utcnow(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.utcnow(),
        )


@dataclass
class AgentSession:
    """Session for agent execution."""
    id: UUID = field(default_factory=uuid4)
    agent_id: UUID = field(default_factory=uuid4)
    state: AgentState = AgentState.CREATED
    context: AgentContext = field(default_factory=AgentContext)
    metrics: ExecutionMetrics = field(default_factory=ExecutionMetrics)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "agent_id": str(self.agent_id),
            "state": self.state.value,
            "context": self.context.to_dict(),
            "metrics": self.metrics.to_dict(),
            "created_at": self.created_at.isoformat(),
        }
