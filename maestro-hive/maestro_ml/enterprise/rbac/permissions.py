"""
Role-Based Access Control (RBAC)

Fine-grained permissions and role management.
"""

import logging
from collections.abc import Callable
from enum import Enum
from functools import wraps
from typing import Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class Permission(str, Enum):
    """
    Granular permissions

    Format: <resource>:<action>
    """

    # Model permissions
    MODEL_VIEW = "model:view"
    MODEL_CREATE = "model:create"
    MODEL_UPDATE = "model:update"
    MODEL_DELETE = "model:delete"
    MODEL_DEPLOY = "model:deploy"
    MODEL_TRAIN = "model:train"

    # Experiment permissions
    EXPERIMENT_VIEW = "experiment:view"
    EXPERIMENT_CREATE = "experiment:create"
    EXPERIMENT_UPDATE = "experiment:update"
    EXPERIMENT_DELETE = "experiment:delete"

    # Data permissions
    DATA_VIEW = "data:view"
    DATA_CREATE = "data:create"
    DATA_UPDATE = "data:update"
    DATA_DELETE = "data:delete"
    DATA_EXPORT = "data:export"

    # User management
    USER_VIEW = "user:view"
    USER_CREATE = "user:create"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"

    # Role management
    ROLE_VIEW = "role:view"
    ROLE_CREATE = "role:create"
    ROLE_UPDATE = "role:update"
    ROLE_DELETE = "role:delete"
    ROLE_ASSIGN = "role:assign"

    # System administration
    SYSTEM_ADMIN = "system:admin"
    SYSTEM_CONFIG = "system:config"
    AUDIT_VIEW = "audit:view"
    AUDIT_EXPORT = "audit:export"

    # Multi-tenancy
    TENANT_ADMIN = "tenant:admin"
    TENANT_VIEW = "tenant:view"


class Role(BaseModel):
    """
    Role definition

    Roles bundle permissions together for easier management.
    """

    role_id: str
    name: str
    description: Optional[str] = None

    # Permissions
    permissions: set[Permission] = Field(default_factory=set)

    # Hierarchy (a role can inherit from other roles)
    inherits_from: list[str] = Field(
        default_factory=list, description="Role IDs this role inherits from"
    )

    # Metadata
    is_system_role: bool = Field(False, description="System roles cannot be deleted")
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class User(BaseModel):
    """User with role assignments"""

    user_id: str
    email: str
    roles: list[str] = Field(default_factory=list, description="Role IDs")
    tenant_id: Optional[str] = None


class PermissionChecker:
    """
    Permission checker

    Evaluates whether users have required permissions.
    """

    def __init__(self):
        self.roles: dict[str, Role] = {}
        self.users: dict[str, User] = {}
        self.logger = logger

        # Initialize with default roles
        self._initialize_default_roles()

    def _initialize_default_roles(self):
        """Create default system roles"""
        # Viewer: read-only access
        viewer = Role(
            role_id="viewer",
            name="Viewer",
            description="Read-only access to models and experiments",
            permissions={
                Permission.MODEL_VIEW,
                Permission.EXPERIMENT_VIEW,
                Permission.DATA_VIEW,
            },
            is_system_role=True,
        )

        # Data Scientist: full access to models and experiments
        data_scientist = Role(
            role_id="data_scientist",
            name="Data Scientist",
            description="Create and manage models and experiments",
            permissions={
                Permission.MODEL_VIEW,
                Permission.MODEL_CREATE,
                Permission.MODEL_UPDATE,
                Permission.MODEL_TRAIN,
                Permission.EXPERIMENT_VIEW,
                Permission.EXPERIMENT_CREATE,
                Permission.EXPERIMENT_UPDATE,
                Permission.DATA_VIEW,
                Permission.DATA_CREATE,
            },
            is_system_role=True,
        )

        # ML Engineer: deploy models
        ml_engineer = Role(
            role_id="ml_engineer",
            name="ML Engineer",
            description="Deploy and manage production models",
            permissions={
                Permission.MODEL_VIEW,
                Permission.MODEL_DEPLOY,
                Permission.MODEL_UPDATE,
                Permission.EXPERIMENT_VIEW,
                Permission.DATA_VIEW,
            },
            is_system_role=True,
        )

        # Admin: full access
        admin = Role(
            role_id="admin",
            name="Administrator",
            description="Full system access",
            permissions={perm for perm in Permission},
            is_system_role=True,
        )

        # Tenant Admin: manage tenant resources
        tenant_admin = Role(
            role_id="tenant_admin",
            name="Tenant Administrator",
            description="Manage tenant resources and users",
            permissions={
                Permission.MODEL_VIEW,
                Permission.MODEL_CREATE,
                Permission.MODEL_UPDATE,
                Permission.MODEL_DELETE,
                Permission.MODEL_DEPLOY,
                Permission.EXPERIMENT_VIEW,
                Permission.EXPERIMENT_CREATE,
                Permission.EXPERIMENT_UPDATE,
                Permission.EXPERIMENT_DELETE,
                Permission.DATA_VIEW,
                Permission.DATA_CREATE,
                Permission.DATA_UPDATE,
                Permission.DATA_DELETE,
                Permission.USER_VIEW,
                Permission.USER_CREATE,
                Permission.USER_UPDATE,
                Permission.ROLE_VIEW,
                Permission.ROLE_ASSIGN,
                Permission.TENANT_VIEW,
            },
            is_system_role=True,
        )

        for role in [viewer, data_scientist, ml_engineer, admin, tenant_admin]:
            self.roles[role.role_id] = role

        self.logger.info(f"Initialized {len(self.roles)} default roles")

    def add_role(self, role: Role):
        """Add a custom role"""
        self.roles[role.role_id] = role
        self.logger.info(f"Added role: {role.name} ({role.role_id})")

    def remove_role(self, role_id: str):
        """Remove a custom role"""
        if role_id not in self.roles:
            raise ValueError(f"Role {role_id} not found")

        role = self.roles[role_id]
        if role.is_system_role:
            raise ValueError(f"Cannot remove system role: {role_id}")

        del self.roles[role_id]
        self.logger.info(f"Removed role: {role_id}")

    def assign_role(self, user_id: str, role_id: str):
        """Assign a role to a user"""
        if role_id not in self.roles:
            raise ValueError(f"Role {role_id} not found")

        if user_id not in self.users:
            raise ValueError(f"User {user_id} not found")

        user = self.users[user_id]
        if role_id not in user.roles:
            user.roles.append(role_id)
            self.logger.info(f"Assigned role {role_id} to user {user_id}")

    def revoke_role(self, user_id: str, role_id: str):
        """Revoke a role from a user"""
        if user_id not in self.users:
            raise ValueError(f"User {user_id} not found")

        user = self.users[user_id]
        if role_id in user.roles:
            user.roles.remove(role_id)
            self.logger.info(f"Revoked role {role_id} from user {user_id}")

    def get_user_permissions(self, user_id: str) -> set[Permission]:
        """
        Get all permissions for a user

        Resolves role inheritance and aggregates permissions.
        """
        if user_id not in self.users:
            return set()

        user = self.users[user_id]
        permissions = set()

        # Collect permissions from all roles
        for role_id in user.roles:
            permissions.update(self._get_role_permissions(role_id))

        return permissions

    def _get_role_permissions(
        self, role_id: str, visited: Optional[set[str]] = None
    ) -> set[Permission]:
        """
        Get all permissions for a role (including inherited)

        Args:
            role_id: Role ID
            visited: Track visited roles to prevent cycles

        Returns:
            Set of permissions
        """
        if visited is None:
            visited = set()

        if role_id in visited:
            # Cycle detected
            return set()

        if role_id not in self.roles:
            return set()

        visited.add(role_id)
        role = self.roles[role_id]

        # Start with role's own permissions
        permissions = set(role.permissions)

        # Add inherited permissions
        for parent_role_id in role.inherits_from:
            permissions.update(self._get_role_permissions(parent_role_id, visited))

        return permissions

    def has_permission(self, user_id: str, permission: Permission) -> bool:
        """
        Check if user has a specific permission

        Args:
            user_id: User ID
            permission: Permission to check

        Returns:
            True if user has permission
        """
        user_permissions = self.get_user_permissions(user_id)

        # SYSTEM_ADMIN grants all permissions
        if Permission.SYSTEM_ADMIN in user_permissions:
            return True

        return permission in user_permissions

    def has_any_permission(self, user_id: str, permissions: list[Permission]) -> bool:
        """Check if user has any of the specified permissions"""
        return any(self.has_permission(user_id, perm) for perm in permissions)

    def has_all_permissions(self, user_id: str, permissions: list[Permission]) -> bool:
        """Check if user has all of the specified permissions"""
        return all(self.has_permission(user_id, perm) for perm in permissions)

    def register_user(self, user: User):
        """Register a user"""
        self.users[user.user_id] = user
        self.logger.info(f"Registered user: {user.email} ({user.user_id})")

    def get_role(self, role_id: str) -> Optional[Role]:
        """Get role by ID"""
        return self.roles.get(role_id)

    def list_roles(self) -> list[Role]:
        """List all roles"""
        return list(self.roles.values())

    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        return self.users.get(user_id)


# Global permission checker instance
_permission_checker = PermissionChecker()


def require_permission(permission: Permission):
    """
    Decorator to enforce permission checks

    Usage:
        @require_permission(Permission.MODEL_DELETE)
        def delete_model(user_id: str, model_id: str):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract user_id from kwargs or first arg
            user_id = kwargs.get("user_id") or (args[0] if args else None)

            if user_id is None:
                raise ValueError("user_id is required for permission check")

            # Check permission
            if not _permission_checker.has_permission(user_id, permission):
                logger.warning(
                    f"Permission denied: User {user_id} lacks {permission.value}"
                )
                raise PermissionError(
                    f"User does not have permission: {permission.value}"
                )

            # Execute function
            return func(*args, **kwargs)

        return wrapper

    return decorator


def require_any_permission(*permissions: Permission):
    """
    Decorator to require any of the specified permissions

    Usage:
        @require_any_permission(Permission.MODEL_VIEW, Permission.EXPERIMENT_VIEW)
        def view_resource(user_id: str, resource_id: str):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            user_id = kwargs.get("user_id") or (args[0] if args else None)

            if user_id is None:
                raise ValueError("user_id is required for permission check")

            if not _permission_checker.has_any_permission(user_id, list(permissions)):
                logger.warning(
                    f"Permission denied: User {user_id} lacks any of {[p.value for p in permissions]}"
                )
                raise PermissionError("User does not have any required permissions")

            return func(*args, **kwargs)

        return wrapper

    return decorator
