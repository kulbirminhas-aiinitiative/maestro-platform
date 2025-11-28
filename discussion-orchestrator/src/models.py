"""
Data models for the Discussion Orchestrator service.

Defines Pydantic models for agents, participants, discussions, and messages.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from uuid import uuid4


class ParticipantType(str, Enum):
    """Type of participant in a discussion."""
    AGENT = "agent"
    HUMAN = "human"


class MessageType(str, Enum):
    """Type of message in a discussion."""
    TEXT = "text"
    SYSTEM = "system"
    ACTION = "action"
    ERROR = "error"


class DiscussionStatus(str, Enum):
    """Status of a discussion session."""
    PENDING = "pending"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class ProtocolType(str, Enum):
    """Discussion protocol type."""
    ROUND_ROBIN = "round_robin"
    FREE_FORM = "free_form"
    MODERATED = "moderated"
    CONSENSUS = "consensus"


class AgentConfig(BaseModel):
    """Configuration for an AI agent participant."""

    agent_id: str = Field(default_factory=lambda: f"agent_{uuid4().hex[:8]}")
    persona: str = Field(..., description="Agent's persona or role")
    provider: str = Field(default="openai", description="LLM provider (openai, anthropic, etc.)")
    model: str = Field(default="gpt-4", description="Model name")
    system_prompt: Optional[str] = Field(None, description="Custom system prompt")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, description="Maximum tokens per response")

    class Config:
        json_schema_extra = {
            "example": {
                "persona": "Backend Developer",
                "provider": "openai",
                "model": "gpt-4",
                "system_prompt": "You are an experienced backend developer...",
                "temperature": 0.7
            }
        }


class HumanParticipant(BaseModel):
    """Configuration for a human participant."""

    user_id: str = Field(..., description="Unique user identifier")
    name: str = Field(..., description="Display name")
    role: Optional[str] = Field(None, description="Role in the discussion")
    permissions: List[str] = Field(
        default_factory=lambda: ["read", "write"],
        description="User permissions"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_123",
                "name": "John Doe",
                "role": "Product Manager",
                "permissions": ["read", "write", "moderate"]
            }
        }


class DiscussionRequest(BaseModel):
    """Request to create a new discussion session."""

    topic: str = Field(..., description="Discussion topic or objective")
    agents: List[AgentConfig] = Field(..., min_length=1, description="AI agents participating")
    humans: List[HumanParticipant] = Field(
        default_factory=list,
        description="Human participants"
    )
    protocol: ProtocolType = Field(
        default=ProtocolType.FREE_FORM,
        description="Discussion protocol"
    )
    max_rounds: Optional[int] = Field(None, description="Maximum discussion rounds")
    context: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional context for the discussion"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "topic": "Design API for user authentication",
                "agents": [
                    {
                        "persona": "Security Expert",
                        "provider": "openai",
                        "model": "gpt-4"
                    }
                ],
                "humans": [
                    {
                        "user_id": "user_123",
                        "name": "John Doe",
                        "role": "Product Manager"
                    }
                ],
                "protocol": "moderated",
                "max_rounds": 10
            }
        }


class Message(BaseModel):
    """A message in a discussion."""

    message_id: str = Field(default_factory=lambda: uuid4().hex)
    participant_id: str = Field(..., description="ID of the message sender")
    participant_name: str = Field(..., description="Display name of sender")
    participant_type: ParticipantType = Field(..., description="Type of participant")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    message_type: MessageType = Field(default=MessageType.TEXT)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

    class Config:
        json_schema_extra = {
            "example": {
                "participant_id": "agent_a1b2c3",
                "participant_name": "Security Expert",
                "participant_type": "agent",
                "content": "I recommend using JWT tokens with refresh token rotation...",
                "message_type": "text"
            }
        }


class Participant(BaseModel):
    """A participant in a discussion (agent or human)."""

    participant_id: str
    name: str
    participant_type: ParticipantType
    config: Optional[Dict[str, Any]] = Field(default_factory=dict)
    is_active: bool = Field(default=True)
    joined_at: datetime = Field(default_factory=datetime.utcnow)


class DiscussionSession(BaseModel):
    """A complete discussion session."""

    id: str = Field(default_factory=lambda: f"disc_{uuid4().hex}")
    topic: str
    protocol: ProtocolType
    participants: List[Participant] = Field(default_factory=list)
    messages: List[Message] = Field(default_factory=list)
    status: DiscussionStatus = Field(default=DiscussionStatus.PENDING)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    current_round: int = Field(default=0)
    max_rounds: Optional[int] = None
    context: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_schema_extra = {
            "example": {
                "id": "disc_a1b2c3d4",
                "topic": "Design API for user authentication",
                "protocol": "moderated",
                "status": "active",
                "current_round": 3,
                "max_rounds": 10
            }
        }


class DiscussionResponse(BaseModel):
    """Response after creating or updating a discussion."""

    session: DiscussionSession
    message: str = Field(default="Discussion session created successfully")


class MessageRequest(BaseModel):
    """Request to send a message in a discussion."""

    participant_id: str
    content: str
    message_type: MessageType = Field(default=MessageType.TEXT)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(default="healthy")
    service: str = Field(default="discussion-orchestrator")
    version: str = Field(default="0.1.0")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    dependencies: Dict[str, str] = Field(default_factory=dict)
