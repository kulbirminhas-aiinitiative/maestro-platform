"""
Security Module
API authentication, authorization, and rate limiting
"""

import os
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

import structlog
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

logger = structlog.get_logger(__name__)

# Security headers
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
admin_key_header = APIKeyHeader(name="X-Admin-Key", auto_error=False)

# Rate limiting storage (in-memory, use Redis in production)
rate_limit_storage = defaultdict(list)


class SecurityConfig:
    """Security configuration"""

    def __init__(self):
        self.api_key = os.getenv("API_KEY")
        self.admin_key = os.getenv("ADMIN_KEY")
        self.rate_limit_per_minute = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
        self.rate_limit_window = 60  # seconds

        if not self.admin_key:
            logger.warning("ADMIN_KEY not set - admin endpoints will be inaccessible")

    def is_valid_api_key(self, key: str) -> bool:
        """Check if API key is valid"""
        return key == self.api_key if self.api_key else True

    def is_valid_admin_key(self, key: str) -> bool:
        """Check if admin key is valid"""
        return key == self.admin_key if self.admin_key else False


security_config = SecurityConfig()


async def verify_api_key(api_key: Optional[str] = Security(api_key_header)) -> str:
    """
    Verify API key for consumer endpoints

    Raises:
        HTTPException: If API key is invalid
    """
    # If no API_KEY is set in environment, allow all requests (dev mode)
    if not security_config.api_key:
        return "anonymous"

    if not api_key:
        logger.warning("api_key_missing")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Provide X-API-Key header."
        )

    if not security_config.is_valid_api_key(api_key):
        logger.warning("api_key_invalid", key_prefix=api_key[:8] if api_key else "")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )

    return api_key


async def verify_admin_key(admin_key: Optional[str] = Security(admin_key_header)) -> str:
    """
    Verify admin key for administrative endpoints

    Raises:
        HTTPException: If admin key is invalid or missing
    """
    if not admin_key:
        logger.warning("admin_key_missing")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin key required. Provide X-Admin-Key header."
        )

    if not security_config.is_valid_admin_key(admin_key):
        logger.warning("admin_key_invalid", key_prefix=admin_key[:8] if admin_key else "")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin key"
        )

    return admin_key


def check_rate_limit(
    identifier: str,
    limit: Optional[int] = None
) -> bool:
    """
    Check if request is within rate limit

    Args:
        identifier: Unique identifier (API key, IP, etc.)
        limit: Custom rate limit (uses default if None)

    Returns:
        True if within limit, False if exceeded
    """
    if limit is None:
        limit = security_config.rate_limit_per_minute

    now = time.time()
    window_start = now - security_config.rate_limit_window

    # Clean old entries
    rate_limit_storage[identifier] = [
        timestamp for timestamp in rate_limit_storage[identifier]
        if timestamp > window_start
    ]

    # Check limit
    if len(rate_limit_storage[identifier]) >= limit:
        logger.warning(
            "rate_limit_exceeded",
            identifier=identifier[:16],
            count=len(rate_limit_storage[identifier]),
            limit=limit
        )
        return False

    # Add current request
    rate_limit_storage[identifier].append(now)
    return True


async def rate_limit_dependency(
    api_key: str = Security(verify_api_key),
    limit: Optional[int] = None
):
    """
    FastAPI dependency for rate limiting

    Raises:
        HTTPException: If rate limit exceeded
    """
    identifier = api_key if api_key != "anonymous" else "anonymous"

    if not check_rate_limit(identifier, limit):
        retry_after = security_config.rate_limit_window
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)}
        )

    return api_key


class RateLimiter:
    """Rate limiting decorator"""

    def __init__(self, limit: Optional[int] = None):
        self.limit = limit or security_config.rate_limit_per_minute

    async def __call__(self, api_key: str = Security(verify_api_key)):
        """Apply rate limiting"""
        identifier = api_key if api_key != "anonymous" else "anonymous"

        if not check_rate_limit(identifier, self.limit):
            retry_after = security_config.rate_limit_window
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
                headers={"Retry-After": str(retry_after)}
            )

        return api_key