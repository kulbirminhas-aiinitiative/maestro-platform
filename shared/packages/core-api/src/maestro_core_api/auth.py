"""
Authentication and authorization for MAESTRO APIs.

Provides JWT and API Key authentication handlers.
"""

import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from jose import JWTError, jwt
from fastapi import HTTPException, Security, status
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

# Security scheme
security = HTTPBearer()


class JWTAuth:
    """
    JWT authentication handler.

    Handles creation and verification of JSON Web Tokens.
    """

    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 30,
        refresh_token_expire_days: int = 7
    ):
        """
        Initialize JWT authentication.

        Args:
            secret_key: Secret key for signing tokens
            algorithm: JWT algorithm (default: HS256)
            access_token_expire_minutes: Access token expiration (default: 30 minutes)
            refresh_token_expire_days: Refresh token expiration (default: 7 days)
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days

    def create_access_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a new access token.

        Args:
            data: Data to encode in the token
            expires_delta: Custom expiration time

        Returns:
            Encoded JWT token

        Example:
            >>> auth = JWTAuth("your-secret-key")
            >>> token = auth.create_access_token({"sub": "user123"})
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)

        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        })

        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        logger.debug("Access token created", sub=data.get("sub"))
        return encoded_jwt

    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """
        Create a new refresh token.

        Args:
            data: Data to encode in the token

        Returns:
            Encoded JWT refresh token
        """
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)

        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh"
        })

        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        logger.debug("Refresh token created", sub=data.get("sub"))
        return encoded_jwt

    def decode_token(self, token: str) -> Dict[str, Any]:
        """
        Decode and verify a JWT token.

        Args:
            token: JWT token to decode

        Returns:
            Decoded token payload

        Raises:
            AuthenticationException: If token is invalid or expired
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError as e:
            logger.warning("Token decode failed", error=str(e))
            raise AuthenticationException(f"Invalid token: {str(e)}")

    def verify_token(self, token: str, expected_type: str = "access") -> Dict[str, Any]:
        """
        Verify token and check type.

        Args:
            token: JWT token to verify
            expected_type: Expected token type ("access" or "refresh")

        Returns:
            Decoded token payload

        Raises:
            AuthenticationException: If token is invalid, expired, or wrong type
        """
        payload = self.decode_token(token)

        token_type = payload.get("type")
        if token_type != expected_type:
            logger.warning(f"Wrong token type", expected=expected_type, got=token_type)
            raise AuthenticationException(f"Expected {expected_type} token, got {token_type}")

        return payload

    async def get_current_user(
        self,
        credentials: HTTPAuthorizationCredentials = Security(security)
    ) -> Dict[str, Any]:
        """
        FastAPI dependency to get current user from token.

        Args:
            credentials: HTTP authorization credentials

        Returns:
            User data from token

        Raises:
            AuthenticationException: If authentication fails

        Example:
            >>> from fastapi import Depends
            >>> @app.get("/protected")
            >>> async def protected_route(user = Depends(auth.get_current_user)):
            ...     return {"user": user}
        """
        try:
            token = credentials.credentials
            payload = self.verify_token(token, "access")

            user_id = payload.get("sub")
            if not user_id:
                raise AuthenticationException("Token missing subject")

            return {
                "user_id": user_id,
                "username": payload.get("username"),
                "roles": payload.get("roles", []),
                "permissions": payload.get("permissions", [])
            }

        except AuthenticationException:
            raise
        except Exception as e:
            logger.error("Authentication failed", error=str(e))
            raise AuthenticationException(f"Authentication failed: {str(e)}")


class APIKeyAuth:
    """
    API Key authentication handler.

    Handles validation of API keys for service-to-service authentication.
    """

    def __init__(self, valid_keys: Optional[Dict[str, Dict[str, Any]]] = None):
        """
        Initialize API key authentication.

        Args:
            valid_keys: Dictionary mapping API keys to metadata
                       Example: {"key123": {"name": "Service A", "permissions": ["read"]}}
        """
        self.valid_keys = valid_keys or {}

    def generate_api_key(self, length: int = 32) -> str:
        """
        Generate a secure random API key.

        Args:
            length: Length of the key in bytes (default: 32)

        Returns:
            Hex-encoded API key
        """
        return secrets.token_hex(length)

    def add_key(self, key: str, metadata: Dict[str, Any]) -> None:
        """
        Add a new API key.

        Args:
            key: The API key
            metadata: Associated metadata (name, permissions, etc.)
        """
        self.valid_keys[key] = metadata
        logger.info("API key added", name=metadata.get("name"))

    def remove_key(self, key: str) -> None:
        """
        Remove an API key.

        Args:
            key: The API key to remove
        """
        if key in self.valid_keys:
            metadata = self.valid_keys.pop(key)
            logger.info("API key removed", name=metadata.get("name"))

    def verify_api_key(self, api_key: str) -> Dict[str, Any]:
        """
        Verify an API key.

        Args:
            api_key: The API key to verify

        Returns:
            Metadata associated with the key

        Raises:
            AuthenticationException: If key is invalid
        """
        if api_key not in self.valid_keys:
            logger.warning("Invalid API key attempted")
            raise AuthenticationException("Invalid API key")

        metadata = self.valid_keys[api_key]
        logger.debug("API key verified", name=metadata.get("name"))
        return metadata

    async def get_api_key_user(
        self,
        credentials: HTTPAuthorizationCredentials = Security(security)
    ) -> Dict[str, Any]:
        """
        FastAPI dependency to verify API key.

        Args:
            credentials: HTTP authorization credentials

        Returns:
            Metadata for the API key

        Raises:
            AuthenticationException: If key is invalid

        Example:
            >>> from fastapi import Depends
            >>> @app.get("/api/data")
            >>> async def get_data(api_key_data = Depends(api_key_auth.get_api_key_user)):
            ...     return {"service": api_key_data["name"]}
        """
        api_key = credentials.credentials
        return self.verify_api_key(api_key)


def require_roles(required_roles: list):
    """
    Decorator to require specific roles.

    Args:
        required_roles: List of required role names

    Returns:
        FastAPI dependency function

    Example:
        >>> @app.get("/admin", dependencies=[Depends(require_roles(["admin"]))])
        >>> async def admin_route():
        ...     return {"message": "Admin access"}
    """
    async def check_roles(user: Dict = Security(security)):
        user_roles = user.get("roles", [])
        if not any(role in user_roles for role in required_roles):
            logger.warning("Access denied", user=user.get("user_id"), required_roles=required_roles)
            raise AuthorizationException(f"Requires one of: {', '.join(required_roles)}")
        return user

    return check_roles


def require_permissions(required_permissions: list):
    """
    Decorator to require specific permissions.

    Args:
        required_permissions: List of required permission names

    Returns:
        FastAPI dependency function
    """
    async def check_permissions(user: Dict = Security(security)):
        user_permissions = user.get("permissions", [])
        if not all(perm in user_permissions for perm in required_permissions):
            logger.warning("Access denied", user=user.get("user_id"), required_permissions=required_permissions)
            raise AuthorizationException(f"Requires permissions: {', '.join(required_permissions)}")
        return user

    return check_permissions


# Export all
__all__ = [
    "JWTAuth",
    "APIKeyAuth",
    "require_roles",
    "require_permissions",
    "security",
]