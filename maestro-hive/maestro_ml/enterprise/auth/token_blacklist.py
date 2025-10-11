"""
Token Blacklist for Maestro ML Platform

Maintains a blacklist of revoked tokens (for logout).
Uses Redis for distributed blacklist management.
Part of Gap 1.1 (JWT Authentication Implementation).
"""

import logging
from typing import Optional
from datetime import timedelta
import redis.asyncio as aioredis

logger = logging.getLogger(__name__)


class TokenBlacklist:
    """
    Token blacklist for logout functionality

    When a user logs out, their token is added to the blacklist.
    All API requests check the blacklist before accepting a token.

    Uses Redis for:
    - Fast lookups (O(1))
    - Automatic expiration (tokens auto-removed after TTL)
    - Distributed across multiple API servers

    Usage:
        blacklist = TokenBlacklist(redis_client)

        # On logout
        await blacklist.revoke_token(token, ttl_seconds=900)

        # On API request
        if await blacklist.is_revoked(token):
            raise HTTPException(status_code=401, detail="Token revoked")
    """

    def __init__(self, redis_client: Optional[aioredis.Redis] = None):
        """
        Initialize token blacklist

        Args:
            redis_client: Redis client (if None, creates new connection)
        """
        self.redis = redis_client
        self.prefix = "token:blacklist:"

    async def _ensure_redis(self):
        """Ensure Redis connection exists"""
        if self.redis is None:
            # Create Redis connection
            import os
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            self.redis = await aioredis.from_url(redis_url, decode_responses=True)

    async def revoke_token(
        self,
        token: str,
        ttl_seconds: int = 900  # 15 minutes (default access token TTL)
    ):
        """
        Add token to blacklist (revoke it)

        Args:
            token: JWT token to revoke
            ttl_seconds: How long to keep in blacklist (should match token expiration)

        Example:
            # On logout
            await blacklist.revoke_token(
                token=access_token,
                ttl_seconds=15 * 60  # 15 minutes
            )
        """
        await self._ensure_redis()

        key = f"{self.prefix}{token}"

        # Store token with expiration
        # Value is just "1" - we only care about key existence
        await self.redis.setex(
            key,
            time=ttl_seconds,
            value="1"
        )

        logger.info(f"Token revoked (blacklisted for {ttl_seconds} seconds)")

    async def is_revoked(self, token: str) -> bool:
        """
        Check if token is blacklisted

        Args:
            token: JWT token to check

        Returns:
            True if token is blacklisted (revoked), False otherwise

        Example:
            if await blacklist.is_revoked(token):
                raise HTTPException(
                    status_code=401,
                    detail="Token has been revoked. Please login again."
                )
        """
        await self._ensure_redis()

        key = f"{self.prefix}{token}"

        # Check if key exists
        exists = await self.redis.exists(key)

        if exists:
            logger.debug("Token is blacklisted (revoked)")
            return True

        return False

    async def revoke_all_user_tokens(
        self,
        user_id: str,
        ttl_seconds: int = 900
    ):
        """
        Revoke all tokens for a user

        This is more complex - requires tracking which tokens belong to which user.
        For now, we just invalidate a "user token generation" counter.

        Args:
            user_id: User ID
            ttl_seconds: TTL for the invalidation

        Note: This requires adding a "generation" field to JWT tokens
        and checking it on every request.
        """
        await self._ensure_redis()

        key = f"{self.prefix}user:{user_id}:invalidated"

        # Store invalidation marker
        await self.redis.setex(
            key,
            time=ttl_seconds,
            value="1"
        )

        logger.info(f"All tokens for user {user_id} invalidated")

    async def is_user_tokens_invalidated(self, user_id: str) -> bool:
        """
        Check if all user's tokens have been invalidated

        Args:
            user_id: User ID

        Returns:
            True if user's tokens are invalidated
        """
        await self._ensure_redis()

        key = f"{self.prefix}user:{user_id}:invalidated"
        exists = await self.redis.exists(key)

        return bool(exists)

    async def clear_blacklist(self):
        """
        Clear entire blacklist

        ⚠️ WARNING: Only use for testing or maintenance!
        """
        await self._ensure_redis()

        # Find all blacklisted tokens
        pattern = f"{self.prefix}*"
        cursor = 0

        while True:
            cursor, keys = await self.redis.scan(
                cursor=cursor,
                match=pattern,
                count=100
            )

            if keys:
                await self.redis.delete(*keys)

            if cursor == 0:
                break

        logger.warning("Token blacklist cleared")

    async def close(self):
        """Close Redis connection"""
        if self.redis:
            await self.redis.close()


# Singleton instance
_token_blacklist: Optional[TokenBlacklist] = None


async def get_token_blacklist() -> TokenBlacklist:
    """
    Get singleton token blacklist instance

    Usage in FastAPI:
        from fastapi import Depends
        from enterprise.auth import get_token_blacklist, TokenBlacklist

        async def endpoint(
            blacklist: TokenBlacklist = Depends(get_token_blacklist)
        ):
            if await blacklist.is_revoked(token):
                raise HTTPException(status_code=401)
    """
    global _token_blacklist
    if _token_blacklist is None:
        _token_blacklist = TokenBlacklist()
    return _token_blacklist
