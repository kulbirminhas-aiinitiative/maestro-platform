"""Base command classes for CQRS."""
from typing import Any, Dict, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class Command(BaseModel):
    """Base class for all commands."""

    command_id: UUID
    tenant_id: UUID
    user_id: Optional[UUID] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        frozen = True


class CommandResult(BaseModel):
    """Result of command execution."""

    success: bool
    aggregate_id: Optional[UUID] = None
    message: Optional[str] = None
    errors: Dict[str, str] = Field(default_factory=dict)
    data: Dict[str, Any] = Field(default_factory=dict)