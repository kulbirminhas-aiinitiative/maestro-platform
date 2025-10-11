"""
RBAC Dependencies for FastAPI

Integrates Role-Based Access Control with FastAPI endpoints.
"""

from fastapi import Depends, HTTPException, status
from typing import Optional, Callable

from ...enterprise.rbac.permissions import (
    Permission,
    _permission_checker as permission_checker
)
from .auth import get_current_user


def require_permissions(*permissions: Permission) -> Callable:
    """
    FastAPI dependency for permission checking

    Usage:
        @router.post("/models", dependencies=[Depends(require_permissions(Permission.MODEL_CREATE))])
        async def create_model(...):
            ...
    """
    async def check_permissions(current_user: dict = Depends(get_current_user)):
        # Anonymous users have no permissions
        if not current_user.get("authenticated", False):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )

        # Check if user has ALL required permissions
        for permission in permissions:
            if not permission_checker.has_permission(user_id, permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: {permission.value} required"
                )

        return current_user

    return check_permissions


def require_any_permissions(*permissions: Permission) -> Callable:
    """
    FastAPI dependency requiring ANY of the specified permissions

    Usage:
        @router.get("/resources", dependencies=[Depends(require_any_permissions(
            Permission.MODEL_VIEW, Permission.EXPERIMENT_VIEW
        ))])
        async def list_resources(...):
            ...
    """
    async def check_any_permission(current_user: dict = Depends(get_current_user)):
        if not current_user.get("authenticated", False):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )

        # Check if user has ANY of the required permissions
        if not permission_checker.has_any_permission(user_id, list(permissions)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: one of {[p.value for p in permissions]} required"
            )

        return current_user

    return check_any_permission


async def get_current_user_with_perms(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    Enhanced user dependency that includes permission information

    Returns user dict with added 'permissions' field.
    """
    if current_user.get("authenticated", False):
        user_id = current_user.get("user_id")
        if user_id:
            permissions = permission_checker.get_user_permissions(user_id)
            current_user["permissions"] = [p.value for p in permissions]

            # Also include roles
            user = permission_checker.get_user(user_id)
            if user:
                current_user["roles"] = user.roles
                current_user["tenant_id"] = user.tenant_id

    return current_user


def require_role(role_id: str) -> Callable:
    """
    FastAPI dependency requiring a specific role

    Usage:
        @router.delete("/system/config", dependencies=[Depends(require_role("admin"))])
        async def update_system_config(...):
            ...
    """
    async def check_role(current_user: dict = Depends(get_current_user)):
        if not current_user.get("authenticated", False):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )

        user = permission_checker.get_user(user_id)
        if not user or role_id not in user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role required: {role_id}"
            )

        return current_user

    return check_role


# Pre-configured dependencies for common access patterns
ViewerAccess = require_any_permissions(
    Permission.MODEL_VIEW,
    Permission.EXPERIMENT_VIEW,
    Permission.DATA_VIEW
)

DataScientistAccess = require_any_permissions(
    Permission.MODEL_CREATE,
    Permission.EXPERIMENT_CREATE,
    Permission.DATA_CREATE
)

MLEngineerAccess = require_permissions(Permission.MODEL_DEPLOY)

AdminAccess = require_role("admin")

TenantAdminAccess = require_any_permissions(
    Permission.TENANT_ADMIN,
    Permission.SYSTEM_ADMIN
)
