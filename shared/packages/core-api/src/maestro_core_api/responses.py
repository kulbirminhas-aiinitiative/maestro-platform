"""
Standardized API response models for MAESTRO APIs.

Provides consistent response structures following REST API best practices.
"""

from typing import Any, Dict, Generic, List, Optional, TypeVar
from datetime import datetime
from pydantic import BaseModel, Field

T = TypeVar('T')


class APIResponse(BaseModel, Generic[T]):
    """
    Base API response model.

    Attributes:
        success: Whether the request was successful
        data: Response data
        timestamp: ISO 8601 timestamp
        request_id: Unique request identifier
    """
    success: bool = Field(..., description="Request success status")
    data: Optional[T] = Field(None, description="Response data")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="Response timestamp")
    request_id: Optional[str] = Field(None, description="Request ID for tracking")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {"key": "value"},
                "timestamp": "2025-09-30T14:52:00.000Z",
                "request_id": "req_abc123"
            }
        }


class SuccessResponse(APIResponse[T]):
    """Success response with data."""
    success: bool = Field(default=True)

    @classmethod
    def create(cls, data: T, request_id: Optional[str] = None):
        """Create a success response."""
        return cls(success=True, data=data, request_id=request_id)


class ErrorResponse(BaseModel):
    """
    Error response model.

    Attributes:
        error: Error details
    """
    error: Dict[str, Any] = Field(..., description="Error details")

    class Config:
        json_schema_extra = {
            "example": {
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid input",
                    "status_code": 400,
                    "details": {"field": "error description"}
                }
            }
        }


class PaginationMeta(BaseModel):
    """Pagination metadata."""
    total: int = Field(..., description="Total number of items", ge=0)
    page: int = Field(..., description="Current page number", ge=1)
    page_size: int = Field(..., description="Number of items per page", ge=1, le=1000)
    total_pages: int = Field(..., description="Total number of pages", ge=0)
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")

    @classmethod
    def create(cls, total: int, page: int, page_size: int):
        """Create pagination metadata."""
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        return cls(
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1
        )


class PaginatedResponse(SuccessResponse[List[T]]):
    """
    Paginated response with metadata.

    Attributes:
        pagination: Pagination metadata
    """
    pagination: PaginationMeta = Field(..., description="Pagination metadata")

    @classmethod
    def create(
        cls,
        items: List[T],
        total: int,
        page: int,
        page_size: int,
        request_id: Optional[str] = None
    ):
        """Create a paginated response."""
        pagination = PaginationMeta.create(total, page, page_size)
        return cls(
            success=True,
            data=items,
            pagination=pagination,
            request_id=request_id
        )


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Service health status")
    version: Optional[str] = Field(None, description="Service version")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    checks: Optional[Dict[str, Any]] = Field(None, description="Individual component checks")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "timestamp": "2025-09-30T14:52:00.000Z",
                "checks": {
                    "database": "healthy",
                    "cache": "healthy"
                }
            }
        }


class MessageResponse(SuccessResponse[Dict[str, str]]):
    """Simple message response."""

    @classmethod
    def create(cls, message: str, request_id: Optional[str] = None):
        """Create a message response."""
        return cls(success=True, data={"message": message}, request_id=request_id)


class StatusResponse(BaseModel):
    """Generic status response."""
    status: str = Field(..., description="Operation status")
    message: Optional[str] = Field(None, description="Status message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "processing",
                "message": "Task queued successfully",
                "details": {"task_id": "task_123"}
            }
        }


class BatchResponse(SuccessResponse[List[T]]):
    """Batch operation response."""
    total_processed: int = Field(..., description="Total items processed", ge=0)
    successful: int = Field(..., description="Successful operations", ge=0)
    failed: int = Field(..., description="Failed operations", ge=0)
    errors: Optional[List[Dict[str, Any]]] = Field(None, description="Error details for failed items")

    @classmethod
    def create(
        cls,
        results: List[T],
        total_processed: int,
        successful: int,
        failed: int,
        errors: Optional[List[Dict[str, Any]]] = None,
        request_id: Optional[str] = None
    ):
        """Create a batch response."""
        return cls(
            success=True,
            data=results,
            total_processed=total_processed,
            successful=successful,
            failed=failed,
            errors=errors,
            request_id=request_id
        )


# Export all
__all__ = [
    "APIResponse",
    "SuccessResponse",
    "ErrorResponse",
    "PaginatedResponse",
    "PaginationMeta",
    "HealthResponse",
    "MessageResponse",
    "StatusResponse",
    "BatchResponse",
]