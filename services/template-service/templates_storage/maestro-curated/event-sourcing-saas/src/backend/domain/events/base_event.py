"""Base event classes for event sourcing."""
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field


class DomainEvent(BaseModel):
    """Base class for all domain events."""

    event_id: UUID = Field(default_factory=uuid4)
    event_type: str
    aggregate_id: UUID
    aggregate_type: str
    tenant_id: UUID
    occurred_at: datetime = Field(default_factory=datetime.utcnow)
    version: int
    user_id: Optional[UUID] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        frozen = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return self.dict()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DomainEvent":
        """Create event from dictionary."""
        return cls(**data)


class EventMetadata(BaseModel):
    """Metadata for events."""

    correlation_id: Optional[UUID] = None
    causation_id: Optional[UUID] = None
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    source: Optional[str] = None

    class Config:
        frozen = True