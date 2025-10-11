"""
JWT Token Manager for Maestro ML Platform

Provides JWT token generation, validation, and management.
Fixes the security bypass identified in meta-review (Gap 1.1).
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# JWT Configuration (from environment)
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "CHANGE_ME_IN_PRODUCTION")  # TODO: Use secrets manager
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))


class TokenData(BaseModel):
    """Data embedded in JWT token"""
    sub: str  # Subject (user_id)
    email: Optional[str] = None
    tenant_id: Optional[str] = None
    roles: list[str] = []
    exp: datetime  # Expiration
    iat: datetime  # Issued at
    token_type: str = "access"  # access or refresh


class TokenPair(BaseModel):
    """Access token + Refresh token"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class JWTManager:
    """
    JWT Token Manager

    Responsible for creating and validating JWT tokens.
    Fixes security bypass by replacing header-based auth with real JWT validation.

    Usage:
        jwt_manager = JWTManager()

        # Create tokens
        tokens = jwt_manager.create_token_pair(
            user_id="user-123",
            email="user@example.com",
            tenant_id="tenant-456",
            roles=["admin", "viewer"]
        )

        # Validate token
        payload = jwt_manager.verify_access_token(tokens.access_token)
    """

    def __init__(
        self,
        secret_key: str = SECRET_KEY,
        algorithm: str = ALGORITHM,
        access_token_expire_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES,
        refresh_token_expire_days: int = REFRESH_TOKEN_EXPIRE_DAYS
    ):
        """
        Initialize JWT Manager

        Args:
            secret_key: Secret key for signing tokens (should be from env/secrets manager)
            algorithm: JWT algorithm (default: HS256)
            access_token_expire_minutes: Access token TTL in minutes
            refresh_token_expire_days: Refresh token TTL in days
        """
        if secret_key == "CHANGE_ME_IN_PRODUCTION":
            logger.warning(
                "⚠️  Using default JWT secret key! "
                "Set JWT_SECRET_KEY environment variable in production!"
            )

        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days

    def create_access_token(
        self,
        user_id: str,
        email: Optional[str] = None,
        tenant_id: Optional[str] = None,
        roles: list[str] = None,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create JWT access token

        Args:
            user_id: User ID (subject)
            email: User email
            tenant_id: Tenant ID for multi-tenancy
            roles: List of user roles
            expires_delta: Custom expiration delta (default: 15 minutes)

        Returns:
            Encoded JWT token string

        Example:
            token = jwt_manager.create_access_token(
                user_id="user-123",
                email="user@example.com",
                tenant_id="tenant-456",
                roles=["admin"]
            )
        """
        if expires_delta is None:
            expires_delta = timedelta(minutes=self.access_token_expire_minutes)

        now = datetime.utcnow()
        expire = now + expires_delta

        # Build token payload
        to_encode = {
            "sub": user_id,  # Subject (standard JWT claim)
            "email": email,
            "tenant_id": tenant_id,
            "roles": roles or [],
            "exp": expire,  # Expiration (standard JWT claim)
            "iat": now,  # Issued at (standard JWT claim)
            "token_type": "access"
        }

        # Encode and sign
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

        logger.debug(f"Created access token for user {user_id}, expires in {expires_delta}")

        return encoded_jwt

    def create_refresh_token(
        self,
        user_id: str,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create JWT refresh token

        Refresh tokens:
        - Have longer TTL (7 days default)
        - Contain minimal data (just user_id)
        - Used to get new access tokens

        Args:
            user_id: User ID
            expires_delta: Custom expiration delta (default: 7 days)

        Returns:
            Encoded JWT refresh token
        """
        if expires_delta is None:
            expires_delta = timedelta(days=self.refresh_token_expire_days)

        now = datetime.utcnow()
        expire = now + expires_delta

        to_encode = {
            "sub": user_id,
            "exp": expire,
            "iat": now,
            "token_type": "refresh"
        }

        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

        logger.debug(f"Created refresh token for user {user_id}, expires in {expires_delta}")

        return encoded_jwt

    def create_token_pair(
        self,
        user_id: str,
        email: Optional[str] = None,
        tenant_id: Optional[str] = None,
        roles: list[str] = None
    ) -> TokenPair:
        """
        Create both access and refresh tokens

        This is the primary method for login flows.

        Args:
            user_id: User ID
            email: User email
            tenant_id: Tenant ID
            roles: User roles

        Returns:
            TokenPair with both tokens

        Example:
            tokens = jwt_manager.create_token_pair(
                user_id="user-123",
                email="user@example.com",
                tenant_id="tenant-456",
                roles=["admin", "viewer"]
            )

            # Return to client
            return {
                "access_token": tokens.access_token,
                "refresh_token": tokens.refresh_token,
                "token_type": "bearer"
            }
        """
        access_token = self.create_access_token(
            user_id=user_id,
            email=email,
            tenant_id=tenant_id,
            roles=roles
        )

        refresh_token = self.create_refresh_token(user_id=user_id)

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self.access_token_expire_minutes * 60  # Convert to seconds
        )

    def verify_token(self, token: str, token_type: str = "access") -> Dict[str, Any]:
        """
        Verify and decode JWT token

        This is the core security function that replaces the header bypass.

        Args:
            token: JWT token string
            token_type: Expected token type ("access" or "refresh")

        Returns:
            Decoded token payload

        Raises:
            JWTError: If token is invalid, expired, or tampered with
            ValueError: If token type doesn't match expected

        Example:
            try:
                payload = jwt_manager.verify_token(token)
                user_id = payload["sub"]
                tenant_id = payload["tenant_id"]
            except JWTError:
                raise HTTPException(status_code=401, detail="Invalid token")
        """
        try:
            # Decode and verify signature
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )

            # Verify token type
            if payload.get("token_type") != token_type:
                raise ValueError(
                    f"Invalid token type: expected {token_type}, "
                    f"got {payload.get('token_type')}"
                )

            # Expiration is automatically checked by jwt.decode
            # (will raise ExpiredSignatureError if expired)

            logger.debug(f"Token verified for user {payload.get('sub')}")

            return payload

        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            raise JWTError("Token has expired")

        except jwt.JWTClaimsError as e:
            logger.warning(f"Invalid JWT claims: {e}")
            raise JWTError(f"Invalid token claims: {e}")

        except jwt.JWTError as e:
            logger.warning(f"JWT validation failed: {e}")
            raise JWTError(f"Invalid token: {e}")

    def verify_access_token(self, token: str) -> Dict[str, Any]:
        """Verify access token (convenience method)"""
        return self.verify_token(token, token_type="access")

    def verify_refresh_token(self, token: str) -> Dict[str, Any]:
        """Verify refresh token (convenience method)"""
        return self.verify_token(token, token_type="refresh")

    def refresh_access_token(
        self,
        refresh_token: str,
        email: Optional[str] = None,
        tenant_id: Optional[str] = None,
        roles: list[str] = None
    ) -> str:
        """
        Generate new access token from refresh token

        Args:
            refresh_token: Valid refresh token
            email: User email (if known)
            tenant_id: Tenant ID (if known)
            roles: User roles (if known)

        Returns:
            New access token

        Raises:
            JWTError: If refresh token is invalid

        Example:
            try:
                new_access_token = jwt_manager.refresh_access_token(
                    refresh_token=old_refresh_token,
                    email=user.email,
                    tenant_id=user.tenant_id,
                    roles=user.roles
                )
            except JWTError:
                # Refresh token invalid/expired, require re-login
                raise HTTPException(status_code=401, detail="Please login again")
        """
        # Verify refresh token
        payload = self.verify_refresh_token(refresh_token)

        user_id = payload["sub"]

        # Create new access token
        return self.create_access_token(
            user_id=user_id,
            email=email,
            tenant_id=tenant_id,
            roles=roles
        )

    def decode_token_without_verification(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Decode token WITHOUT verifying signature

        ⚠️ WARNING: Only use for debugging or token inspection
        DO NOT use for authentication!

        Args:
            token: JWT token

        Returns:
            Decoded payload (unverified) or None if malformed
        """
        try:
            return jwt.decode(
                token,
                options={"verify_signature": False, "verify_exp": False}
            )
        except:
            return None


# Singleton instance
_jwt_manager: Optional[JWTManager] = None


def get_jwt_manager() -> JWTManager:
    """
    Get singleton JWT manager instance

    Usage in FastAPI:
        from fastapi import Depends
        from enterprise.auth import get_jwt_manager, JWTManager

        async def endpoint(
            jwt_manager: JWTManager = Depends(get_jwt_manager)
        ):
            ...
    """
    global _jwt_manager
    if _jwt_manager is None:
        _jwt_manager = JWTManager()
    return _jwt_manager
