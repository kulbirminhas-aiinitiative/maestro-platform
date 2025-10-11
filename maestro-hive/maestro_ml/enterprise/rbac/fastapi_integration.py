"""
FastAPI RBAC Integration

Provides FastAPI dependencies and decorators for role-based access control.

SECURITY FIX: Replaced header-based authentication bypass with real JWT validation.
Gap 1.1 (Task 1.1.2) - Remove Security Bypass
"""

import logging
from typing import Optional, Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError

from .permissions import (
    Permission,
    PermissionChecker,
    User,
    _permission_checker
)
from ..auth.jwt_manager import get_jwt_manager, JWTManager
from ..auth.token_blacklist import get_token_blacklist, TokenBlacklist

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer()


class CurrentUser:
    """
    Dependency to get current authenticated user

    SECURITY FIX: Now uses real JWT validation instead of header bypass.
    """

    def __init__(
        self,
        permission_checker: PermissionChecker = _permission_checker,
        jwt_manager: Optional[JWTManager] = None,
        token_blacklist: Optional[TokenBlacklist] = None
    ):
        self.permission_checker = permission_checker
        self.jwt_manager = jwt_manager
        self.token_blacklist = token_blacklist

    async def __call__(
        self,
        credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
        jwt_manager: JWTManager = Depends(get_jwt_manager),
        token_blacklist: TokenBlacklist = Depends(get_token_blacklist)
    ) -> User:
        """
        Extract and validate user from JWT token.

        SECURITY FIX:
        - ✅ Validates JWT signature
        - ✅ Checks token expiration
        - ✅ Verifies token hasn't been revoked
        - ❌ REMOVED: Header-based bypass (x-user-id)
        - ❌ REMOVED: Auto-create user logic

        Args:
            credentials: Bearer token from Authorization header
            jwt_manager: JWT manager for token validation
            token_blacklist: Token blacklist for logout

        Returns:
            User object with validated claims

        Raises:
            HTTPException 401: If token is invalid, expired, or revoked
        """
        token = credentials.credentials

        # Check if token is blacklisted (revoked)
        if await token_blacklist.is_revoked(token):
            logger.warning("Attempted to use revoked token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked. Please login again.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Validate JWT token (REAL validation, not TODO!)
        try:
            payload = jwt_manager.verify_access_token(token)

        except JWTError as e:
            logger.warning(f"JWT validation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid authentication credentials: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Extract claims from validated token
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user ID",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check if user's tokens have been globally invalidated
        if await token_blacklist.is_user_tokens_invalidated(user_id):
            logger.warning(f"User {user_id} tokens invalidated")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been invalidated. Please login again.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Get user from permission checker
        # (This should query the database in production)
        user = self.permission_checker.get_user(user_id)

        if not user:
            # User doesn't exist in permission system
            # ❌ REMOVED: Auto-create logic (security bypass)
            # ✅ ADDED: Proper error handling
            logger.error(f"User {user_id} authenticated but not found in permission system")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found in permission system",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Update user with token claims (in case they changed)
        user.email = payload.get("email") or user.email
        user.tenant_id = payload.get("tenant_id") or user.tenant_id
        user.roles = payload.get("roles") or user.roles

        logger.debug(f"User authenticated: {user_id} (tenant: {user.tenant_id})")

        return user


# Global instance
get_current_user = CurrentUser()


class RequirePermission:
    """
    FastAPI dependency to require specific permission.

    Usage:
        @app.get("/models", dependencies=[Depends(RequirePermission(Permission.MODEL_VIEW))])
        async def list_models():
            ...
    """

    def __init__(
        self,
        permission: Permission,
        permission_checker: PermissionChecker = _permission_checker
    ):
        self.permission = permission
        self.permission_checker = permission_checker

    async def __call__(self, user: User = Depends(get_current_user)):
        """
        Check if user has required permission.

        Args:
            user: Current user from dependency

        Raises:
            HTTPException: If permission denied
        """
        if not self.permission_checker.has_permission(user.user_id, self.permission):
            logger.warning(
                f"Permission denied: User {user.user_id} lacks {self.permission.value}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {self.permission.value} required"
            )


class RequireAnyPermission:
    """
    FastAPI dependency to require any of specified permissions.

    Usage:
        @app.get(
            "/resources",
            dependencies=[Depends(RequireAnyPermission([Permission.MODEL_VIEW, Permission.DATA_VIEW]))]
        )
        async def list_resources():
            ...
    """

    def __init__(
        self,
        permissions: list[Permission],
        permission_checker: PermissionChecker = _permission_checker
    ):
        self.permissions = permissions
        self.permission_checker = permission_checker

    async def __call__(self, user: User = Depends(get_current_user)):
        """Check if user has any required permission"""
        if not self.permission_checker.has_any_permission(user.user_id, self.permissions):
            logger.warning(
                f"Permission denied: User {user.user_id} lacks any of {[p.value for p in self.permissions]}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: One of {[p.value for p in self.permissions]} required"
            )


class RequireAllPermissions:
    """
    FastAPI dependency to require all specified permissions.

    Usage:
        @app.post(
            "/models/deploy",
            dependencies=[Depends(RequireAllPermissions([Permission.MODEL_VIEW, Permission.MODEL_DEPLOY]))]
        )
        async def deploy_model():
            ...
    """

    def __init__(
        self,
        permissions: list[Permission],
        permission_checker: PermissionChecker = _permission_checker
    ):
        self.permissions = permissions
        self.permission_checker = permission_checker

    async def __call__(self, user: User = Depends(get_current_user)):
        """Check if user has all required permissions"""
        if not self.permission_checker.has_all_permissions(user.user_id, self.permissions):
            logger.warning(
                f"Permission denied: User {user.user_id} lacks all of {[p.value for p in self.permissions]}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: All of {[p.value for p in self.permissions]} required"
            )


class TenantIsolation:
    """
    Dependency to enforce tenant isolation.

    Ensures users can only access resources within their tenant.
    """

    async def __call__(
        self,
        user: User = Depends(get_current_user),
        tenant_id: Optional[str] = None
    ):
        """
        Enforce tenant isolation.

        Args:
            user: Current user
            tenant_id: Requested tenant ID (from path/query)

        Raises:
            HTTPException: If tenant mismatch
        """
        # If no tenant specified in request, use user's tenant
        if tenant_id is None:
            return user.tenant_id

        # Verify tenant match
        if user.tenant_id and user.tenant_id != tenant_id:
            logger.warning(
                f"Tenant isolation violation: User {user.user_id} (tenant {user.tenant_id}) "
                f"attempted to access tenant {tenant_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Cannot access resources from other tenants"
            )

        return tenant_id


# Global instances for common use
require_tenant_isolation = TenantIsolation()


# Helper functions for endpoint decoration
def require_permission(permission: Permission):
    """
    Helper to create permission dependency.

    Usage:
        @app.get("/models", dependencies=[require_permission(Permission.MODEL_VIEW)])
        async def list_models():
            ...
    """
    return Depends(RequirePermission(permission))


def require_any_permission(*permissions: Permission):
    """
    Helper to create any-permission dependency.

    Usage:
        @app.get(
            "/resources",
            dependencies=[require_any_permission(Permission.MODEL_VIEW, Permission.DATA_VIEW)]
        )
        async def list_resources():
            ...
    """
    return Depends(RequireAnyPermission(list(permissions)))


def require_all_permissions(*permissions: Permission):
    """
    Helper to create all-permissions dependency.

    Usage:
        @app.post(
            "/models/deploy",
            dependencies=[require_all_permissions(Permission.MODEL_VIEW, Permission.MODEL_DEPLOY)]
        )
        async def deploy_model():
            ...
    """
    return Depends(RequireAllPermissions(list(permissions)))


# Context manager for permission checking in route handlers
class PermissionContext:
    """
    Context for checking permissions within route handlers.

    Usage:
        @app.get("/models/{model_id}")
        async def get_model(model_id: str, user: User = Depends(get_current_user)):
            # Check permission dynamically
            async with PermissionContext(user, Permission.MODEL_VIEW):
                # Code here only runs if user has permission
                return await fetch_model(model_id)
    """

    def __init__(
        self,
        user: User,
        permission: Permission,
        permission_checker: PermissionChecker = _permission_checker
    ):
        self.user = user
        self.permission = permission
        self.permission_checker = permission_checker

    async def __aenter__(self):
        if not self.permission_checker.has_permission(self.user.user_id, self.permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {self.permission.value} required"
            )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
