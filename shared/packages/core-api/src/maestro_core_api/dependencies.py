"""
FastAPI dependencies for MAESTRO APIs.

Provides reusable dependency injection functions for common operations.
"""

from typing import Any, Dict, Optional
from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from maestro_core_logging import get_logger

from .exceptions import AuthenticationException, AuthorizationException

def _get_logger():
    try:
        from maestro_core_logging import get_logger
        return get_logger(__name__)
    except:
        import logging
        return logging.getLogger(__name__)

logger = type("LazyLogger", (), {"__getattr__": lambda self, name: getattr(_get_logger(), name)})()

security = HTTPBearer()


# Authentication dependencies

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    Get current authenticated user from JWT token.

    This is a placeholder that should be configured with actual JWTAuth instance.
    Use JWTAuth.get_current_user for production.

    Args:
        credentials: HTTP authorization credentials

    Returns:
        User data dictionary

    Raises:
        AuthenticationException: If authentication fails

    Example:
        >>> from fastapi import Depends
        >>> @app.get("/me")
        >>> async def get_me(user = Depends(get_current_user)):
        ...     return user
    """
    # This is a placeholder - in production, configure with JWTAuth
    logger.warning("Using placeholder get_current_user - configure with JWTAuth for production")
    return {
        "user_id": "placeholder",
        "username": "placeholder_user",
        "roles": [],
        "permissions": []
    }


async def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    Require authentication for a route.

    Args:
        credentials: HTTP authorization credentials

    Returns:
        User data if authenticated

    Raises:
        AuthenticationException: If not authenticated

    Example:
        >>> @app.get("/protected", dependencies=[Depends(require_auth)])
        >>> async def protected_route():
        ...     return {"message": "Protected content"}
    """
    return await get_current_user(credentials)


async def require_role(role: str):
    """
    Create a dependency that requires a specific role.

    Args:
        role: Required role name

    Returns:
        Dependency function

    Example:
        >>> @app.get("/admin")
        >>> async def admin_route(user = Depends(require_role("admin"))):
        ...     return {"message": "Admin access"}
    """
    async def check_role(user: Dict = Depends(get_current_user)):
        user_roles = user.get("roles", [])
        if role not in user_roles:
            logger.warning("Role check failed", user=user.get("user_id"), required_role=role)
            raise AuthorizationException(f"Role '{role}' required")
        return user

    return check_role


# Request metadata dependencies

async def get_request_id(
    request: Request,
    x_request_id: Optional[str] = Header(None)
) -> str:
    """
    Get or generate request ID for tracing.

    Args:
        request: FastAPI request object
        x_request_id: Optional X-Request-ID header

    Returns:
        Request ID string

    Example:
        >>> @app.get("/test")
        >>> async def test(request_id: str = Depends(get_request_id)):
        ...     logger.info("Processing request", request_id=request_id)
    """
    if x_request_id:
        return x_request_id

    # Generate new request ID if not provided
    import uuid
    return str(uuid.uuid4())


async def get_client_ip(request: Request) -> str:
    """
    Get client IP address from request.

    Checks X-Forwarded-For header for proxy/load balancer setups.

    Args:
        request: FastAPI request object

    Returns:
        Client IP address

    Example:
        >>> @app.get("/info")
        >>> async def info(client_ip: str = Depends(get_client_ip)):
        ...     return {"client_ip": client_ip}
    """
    # Check for proxy headers
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Get first IP in the chain
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # Fall back to direct client
    if request.client:
        return request.client.host

    return "unknown"


# Database dependencies (placeholder)

async def get_db_session():
    """
    Get database session.

    This is a placeholder. In production, configure with actual database connection pool.

    Yields:
        Database session

    Example:
        >>> @app.get("/users")
        >>> async def get_users(db = Depends(get_db_session)):
        ...     return await db.fetch_all("SELECT * FROM users")
    """
    logger.warning("Using placeholder get_db_session - configure with actual DB for production")
    # Placeholder - replace with actual database session management
    # Example with SQLAlchemy:
    # async with async_session() as session:
    #     yield session
    yield None


# Pagination dependencies

class PaginationParams:
    """Pagination parameters for list endpoints."""

    def __init__(
        self,
        page: int = 1,
        page_size: int = 50,
        sort_by: Optional[str] = None,
        sort_order: str = "asc"
    ):
        """
        Initialize pagination parameters.

        Args:
            page: Page number (1-indexed)
            page_size: Number of items per page (1-1000)
            sort_by: Field to sort by
            sort_order: Sort order ("asc" or "desc")
        """
        self.page = max(1, page)
        self.page_size = max(1, min(1000, page_size))
        self.sort_by = sort_by
        self.sort_order = sort_order.lower()

        if self.sort_order not in ("asc", "desc"):
            self.sort_order = "asc"

    @property
    def offset(self) -> int:
        """Calculate offset for database queries."""
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        """Get limit for database queries."""
        return self.page_size


async def get_pagination(
    page: int = 1,
    page_size: int = 50,
    sort_by: Optional[str] = None,
    sort_order: str = "asc"
) -> PaginationParams:
    """
    Dependency for pagination parameters.

    Args:
        page: Page number (default: 1)
        page_size: Items per page (default: 50, max: 1000)
        sort_by: Field to sort by
        sort_order: Sort order (asc/desc)

    Returns:
        PaginationParams instance

    Example:
        >>> @app.get("/items")
        >>> async def list_items(pagination: PaginationParams = Depends(get_pagination)):
        ...     items = await fetch_items(offset=pagination.offset, limit=pagination.limit)
        ...     return {"items": items, "page": pagination.page}
    """
    return PaginationParams(page, page_size, sort_by, sort_order)


# Rate limiting dependencies

class RateLimitInfo:
    """Rate limit information."""

    def __init__(self, identifier: str, limit: int, window: int):
        """
        Initialize rate limit info.

        Args:
            identifier: Client identifier (IP, user ID, etc.)
            limit: Maximum requests allowed
            window: Time window in seconds
        """
        self.identifier = identifier
        self.limit = limit
        self.window = window
        self.remaining = limit  # Placeholder


async def get_rate_limit_info(
    request: Request,
    client_ip: str = Depends(get_client_ip)
) -> RateLimitInfo:
    """
    Get rate limit information for the request.

    Args:
        request: FastAPI request object
        client_ip: Client IP address

    Returns:
        RateLimitInfo instance

    Example:
        >>> @app.get("/api/data")
        >>> async def get_data(rate_limit: RateLimitInfo = Depends(get_rate_limit_info)):
        ...     # Rate limiting is handled by middleware
        ...     return {"data": "..."}
    """
    # Placeholder - in production, integrate with Redis or similar
    return RateLimitInfo(
        identifier=client_ip,
        limit=100,
        window=60
    )


# Export all
__all__ = [
    "get_current_user",
    "require_auth",
    "require_role",
    "get_request_id",
    "get_client_ip",
    "get_db_session",
    "get_pagination",
    "PaginationParams",
    "get_rate_limit_info",
    "RateLimitInfo",
]