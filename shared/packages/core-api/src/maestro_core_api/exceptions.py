"""
Enterprise exception handling for MAESTRO APIs.

Provides standardized exception classes and handlers following REST API best practices.
"""

from typing import Any, Dict, Optional
from fastapi import Request, status
from fastapi.responses import JSONResponse
from maestro_core_logging import get_logger

def _get_logger():
    try:
        from maestro_core_logging import get_logger
        return get_logger(__name__)
    except:
        import logging
        return logging.getLogger(__name__)

logger = type("LazyLogger", (), {"__getattr__": lambda self, name: getattr(_get_logger(), name)})()


class APIException(Exception):
    """
    Base exception for all API errors.

    Attributes:
        status_code: HTTP status code
        error_code: Machine-readable error code
        message: Human-readable error message
        details: Additional error details
    """

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "INTERNAL_ERROR"
    message: str = "An internal error occurred"

    def __init__(
        self,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        status_code: Optional[int] = None,
        error_code: Optional[str] = None
    ):
        """
        Initialize API exception.

        Args:
            message: Custom error message
            details: Additional error details
            status_code: Custom status code
            error_code: Custom error code
        """
        self.message = message or self.message
        self.details = details or {}
        if status_code:
            self.status_code = status_code
        if error_code:
            self.error_code = error_code
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for JSON response."""
        result = {
            "error": {
                "code": self.error_code,
                "message": self.message,
                "status_code": self.status_code
            }
        }
        if self.details:
            result["error"]["details"] = self.details
        return result


class ValidationException(APIException):
    """Request validation failed."""
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "VALIDATION_ERROR"
    message = "Request validation failed"


class AuthenticationException(APIException):
    """Authentication failed."""
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "AUTHENTICATION_FAILED"
    message = "Authentication failed"


class AuthorizationException(APIException):
    """Authorization failed (insufficient permissions)."""
    status_code = status.HTTP_403_FORBIDDEN
    error_code = "AUTHORIZATION_FAILED"
    message = "Insufficient permissions"


class NotFoundException(APIException):
    """Resource not found."""
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "NOT_FOUND"
    message = "Resource not found"


class ConflictException(APIException):
    """Resource conflict (e.g., duplicate)."""
    status_code = status.HTTP_409_CONFLICT
    error_code = "CONFLICT"
    message = "Resource conflict"


class RateLimitException(APIException):
    """Rate limit exceeded."""
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    error_code = "RATE_LIMIT_EXCEEDED"
    message = "Rate limit exceeded"


class ServiceUnavailableException(APIException):
    """Service temporarily unavailable."""
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    error_code = "SERVICE_UNAVAILABLE"
    message = "Service temporarily unavailable"


# Exception handlers

async def api_exception_handler(request: Request, exc: APIException) -> JSONResponse:
    """
    Handle APIException and return standardized JSON response.

    Args:
        request: FastAPI request object
        exc: APIException instance

    Returns:
        JSONResponse with error details
    """
    logger.error(
        "API exception",
        error_code=exc.error_code,
        status_code=exc.status_code,
        message=exc.message,
        path=request.url.path,
        method=request.method,
        details=exc.details
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict()
    )


async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle Pydantic validation errors.

    Args:
        request: FastAPI request object
        exc: Validation exception

    Returns:
        JSONResponse with validation errors
    """
    from pydantic import ValidationError

    if isinstance(exc, ValidationError):
        errors = exc.errors()
        logger.warning(
            "Validation error",
            path=request.url.path,
            method=request.method,
            errors=errors
        )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed",
                    "status_code": 422,
                    "details": {"validation_errors": errors}
                }
            }
        )

    # Fall back to generic error
    logger.error(
        "Unexpected validation error",
        path=request.url.path,
        method=request.method,
        error=str(exc)
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An internal error occurred",
                "status_code": 500
            }
        }
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle unexpected exceptions.

    Args:
        request: FastAPI request object
        exc: Generic exception

    Returns:
        JSONResponse with generic error
    """
    logger.exception(
        "Unexpected error",
        path=request.url.path,
        method=request.method,
        error_type=type(exc).__name__,
        error=str(exc)
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An internal error occurred",
                "status_code": 500
            }
        }
    )


# Export all
__all__ = [
    "APIException",
    "ValidationException",
    "AuthenticationException",
    "AuthorizationException",
    "NotFoundException",
    "ConflictException",
    "RateLimitException",
    "ServiceUnavailableException",
    "api_exception_handler",
    "validation_exception_handler",
    "generic_exception_handler",
]