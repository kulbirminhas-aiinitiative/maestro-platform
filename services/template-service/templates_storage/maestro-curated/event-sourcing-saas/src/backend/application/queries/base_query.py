"""Base query classes for CQRS."""
from typing import Any, Dict, Generic, Optional, TypeVar
from uuid import UUID
from pydantic import BaseModel, Field


TResult = TypeVar('TResult')


class Query(BaseModel):
    """Base class for all queries."""

    tenant_id: UUID
    user_id: Optional[UUID] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    class Config:
        frozen = True


class QueryResult(BaseModel, Generic[TResult]):
    """Result of query execution."""

    success: bool
    data: Optional[TResult] = None
    total_count: int = 0
    page: int = 1
    page_size: int = 20
    message: Optional[str] = None
    errors: Dict[str, str] = Field(default_factory=dict)