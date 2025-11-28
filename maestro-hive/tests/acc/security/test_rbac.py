"""
ACC Security Tests: Role-Based Access Control (RBAC)
Test IDs: ACC-400 to ACC-419

Tests for role-based access control:
- Role definitions and permissions
- Access control enforcement
- Permission inheritance and hierarchies
- Resource ownership checks
- Multi-role scenarios
- Permission denial handling

These tests ensure:
1. Users can only perform authorized actions
2. Roles properly define permissions
3. Resource ownership is enforced
4. Permission hierarchies work correctly
"""

import pytest
from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class Permission(Enum):
    """System permissions"""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"
    EXECUTE = "execute"
    SHARE = "share"


class Role(Enum):
    """System roles"""
    ADMIN = "admin"
    DEVELOPER = "developer"
    VIEWER = "viewer"
    GUEST = "guest"
    OWNER = "owner"


@dataclass
class User:
    """User with roles and permissions"""
    user_id: str
    username: str
    email: str
    roles: Set[Role] = field(default_factory=set)

    def has_role(self, role: Role) -> bool:
        """Check if user has specific role"""
        return role in self.roles

    def add_role(self, role: Role):
        """Add role to user"""
        self.roles.add(role)

    def remove_role(self, role: Role):
        """Remove role from user"""
        self.roles.discard(role)


@dataclass
class Resource:
    """Protected resource with ownership"""
    resource_id: str
    resource_type: str
    owner_id: str
    data: Dict[str, Any] = field(default_factory=dict)
    shared_with: Set[str] = field(default_factory=set)


class AccessDeniedError(Exception):
    """Raised when access is denied"""
    pass


class RBACEngine:
    """Role-Based Access Control engine"""

    def __init__(self):
        # Define role permissions
        self.role_permissions: Dict[Role, Set[Permission]] = {
            Role.ADMIN: {Permission.READ, Permission.WRITE, Permission.DELETE,
                        Permission.ADMIN, Permission.EXECUTE, Permission.SHARE},
            Role.DEVELOPER: {Permission.READ, Permission.WRITE, Permission.EXECUTE, Permission.SHARE},
            Role.VIEWER: {Permission.READ},
            Role.GUEST: set(),  # No permissions
            Role.OWNER: {Permission.READ, Permission.WRITE, Permission.DELETE, Permission.SHARE},
        }

    def get_permissions(self, user: User) -> Set[Permission]:
        """Get all permissions for user based on their roles"""
        permissions = set()
        for role in user.roles:
            permissions.update(self.role_permissions.get(role, set()))
        return permissions

    def has_permission(self, user: User, permission: Permission) -> bool:
        """Check if user has specific permission"""
        user_permissions = self.get_permissions(user)
        return permission in user_permissions

    def check_access(
        self,
        user: User,
        resource: Resource,
        permission: Permission,
        check_ownership: bool = True
    ) -> bool:
        """
        Check if user can perform action on resource.

        Rules:
        1. Admin role bypasses all checks
        2. Owner of resource has full access
        3. Shared resources grant read access
        4. Otherwise check role permissions
        """
        # Admin bypass
        if user.has_role(Role.ADMIN):
            return True

        # Ownership check
        if check_ownership and resource.owner_id == user.user_id:
            return permission in self.role_permissions[Role.OWNER]

        # Shared resource read access
        if user.user_id in resource.shared_with and permission == Permission.READ:
            return True

        # Role-based permission check
        return self.has_permission(user, permission)

    def enforce_access(
        self,
        user: User,
        resource: Resource,
        permission: Permission,
        check_ownership: bool = True
    ):
        """Enforce access control (raises exception if denied)"""
        if not self.check_access(user, resource, permission, check_ownership):
            raise AccessDeniedError(
                f"User {user.username} denied {permission.value} access to resource {resource.resource_id}"
            )

    def share_resource(self, user: User, resource: Resource, target_user_id: str):
        """Share resource with another user"""
        # Must have SHARE permission
        self.enforce_access(user, resource, Permission.SHARE)
        resource.shared_with.add(target_user_id)

    def unshare_resource(self, user: User, resource: Resource, target_user_id: str):
        """Unshare resource"""
        self.enforce_access(user, resource, Permission.SHARE)
        resource.shared_with.discard(target_user_id)


@pytest.mark.acc
@pytest.mark.security
class TestRoleDefinitions:
    """Test suite for role definitions and permissions"""

    @pytest.fixture
    def rbac(self):
        """Create RBAC engine"""
        return RBACEngine()

    def test_acc_400_admin_has_all_permissions(self, rbac):
        """ACC-400: Admin role has all permissions"""
        admin_permissions = rbac.role_permissions[Role.ADMIN]

        assert Permission.READ in admin_permissions
        assert Permission.WRITE in admin_permissions
        assert Permission.DELETE in admin_permissions
        assert Permission.ADMIN in admin_permissions
        assert Permission.EXECUTE in admin_permissions
        assert Permission.SHARE in admin_permissions

    def test_acc_401_developer_has_read_write_execute(self, rbac):
        """ACC-401: Developer role has read, write, execute, share permissions"""
        dev_permissions = rbac.role_permissions[Role.DEVELOPER]

        assert Permission.READ in dev_permissions
        assert Permission.WRITE in dev_permissions
        assert Permission.EXECUTE in dev_permissions
        assert Permission.SHARE in dev_permissions
        assert Permission.DELETE not in dev_permissions
        assert Permission.ADMIN not in dev_permissions

    def test_acc_402_viewer_has_read_only(self, rbac):
        """ACC-402: Viewer role has read-only access"""
        viewer_permissions = rbac.role_permissions[Role.VIEWER]

        assert Permission.READ in viewer_permissions
        assert Permission.WRITE not in viewer_permissions
        assert Permission.DELETE not in viewer_permissions
        assert len(viewer_permissions) == 1

    def test_acc_403_guest_has_no_permissions(self, rbac):
        """ACC-403: Guest role has no permissions"""
        guest_permissions = rbac.role_permissions[Role.GUEST]

        assert len(guest_permissions) == 0

    def test_acc_404_owner_has_full_resource_control(self, rbac):
        """ACC-404: Owner role has full control over owned resources"""
        owner_permissions = rbac.role_permissions[Role.OWNER]

        assert Permission.READ in owner_permissions
        assert Permission.WRITE in owner_permissions
        assert Permission.DELETE in owner_permissions
        assert Permission.SHARE in owner_permissions


@pytest.mark.acc
@pytest.mark.security
class TestAccessControl:
    """Test suite for access control enforcement"""

    @pytest.fixture
    def rbac(self):
        return RBACEngine()

    @pytest.fixture
    def admin_user(self):
        user = User(user_id="admin-1", username="admin", email="admin@example.com")
        user.add_role(Role.ADMIN)
        return user

    @pytest.fixture
    def dev_user(self):
        user = User(user_id="dev-1", username="developer", email="dev@example.com")
        user.add_role(Role.DEVELOPER)
        return user

    @pytest.fixture
    def viewer_user(self):
        user = User(user_id="viewer-1", username="viewer", email="viewer@example.com")
        user.add_role(Role.VIEWER)
        return user

    @pytest.fixture
    def resource(self):
        return Resource(
            resource_id="res-1",
            resource_type="workflow",
            owner_id="dev-1",
            data={"name": "Test Workflow"}
        )

    def test_acc_405_admin_can_read_any_resource(self, rbac, admin_user, resource):
        """ACC-405: Admin can read any resource"""
        result = rbac.check_access(admin_user, resource, Permission.READ)
        assert result is True

    def test_acc_406_admin_can_delete_any_resource(self, rbac, admin_user, resource):
        """ACC-406: Admin can delete any resource"""
        result = rbac.check_access(admin_user, resource, Permission.DELETE)
        assert result is True

    def test_acc_407_owner_can_read_own_resource(self, rbac, dev_user, resource):
        """ACC-407: Owner can read their own resource"""
        result = rbac.check_access(dev_user, resource, Permission.READ)
        assert result is True

    def test_acc_408_owner_can_delete_own_resource(self, rbac, dev_user, resource):
        """ACC-408: Owner can delete their own resource"""
        result = rbac.check_access(dev_user, resource, Permission.DELETE)
        assert result is True

    def test_acc_409_non_owner_cannot_delete_resource(self, rbac, viewer_user, resource):
        """ACC-409: Non-owner cannot delete resource"""
        result = rbac.check_access(viewer_user, resource, Permission.DELETE)
        assert result is False

    def test_acc_410_viewer_cannot_write_any_resource(self, rbac, viewer_user, resource):
        """ACC-410: Viewer cannot write to any resource"""
        result = rbac.check_access(viewer_user, resource, Permission.WRITE, check_ownership=False)
        assert result is False

    def test_acc_411_enforce_access_raises_on_denial(self, rbac, viewer_user, resource):
        """ACC-411: enforce_access raises AccessDeniedError when denied"""
        with pytest.raises(AccessDeniedError, match="denied write access"):
            rbac.enforce_access(viewer_user, resource, Permission.WRITE, check_ownership=False)

    def test_acc_412_enforce_access_succeeds_when_allowed(self, rbac, admin_user, resource):
        """ACC-412: enforce_access succeeds when access allowed"""
        # Should not raise
        rbac.enforce_access(admin_user, resource, Permission.DELETE)


@pytest.mark.acc
@pytest.mark.security
class TestResourceSharing:
    """Test suite for resource sharing"""

    @pytest.fixture
    def rbac(self):
        return RBACEngine()

    @pytest.fixture
    def owner(self):
        user = User(user_id="owner-1", username="owner", email="owner@example.com")
        user.add_role(Role.DEVELOPER)
        return user

    @pytest.fixture
    def other_user(self):
        user = User(user_id="user-2", username="user2", email="user2@example.com")
        user.add_role(Role.VIEWER)
        return user

    @pytest.fixture
    def resource(self, owner):
        return Resource(
            resource_id="res-1",
            resource_type="document",
            owner_id=owner.user_id
        )

    def test_acc_413_owner_can_share_resource(self, rbac, owner, other_user, resource):
        """ACC-413: Owner can share their resource with others"""
        # Should not raise
        rbac.share_resource(owner, resource, other_user.user_id)

        assert other_user.user_id in resource.shared_with

    def test_acc_414_shared_user_can_read_resource(self, rbac, owner, other_user, resource):
        """ACC-414: User with shared access can read resource"""
        rbac.share_resource(owner, resource, other_user.user_id)

        result = rbac.check_access(other_user, resource, Permission.READ)
        assert result is True

    def test_acc_415_shared_user_cannot_delete_resource(self, rbac, owner, other_user, resource):
        """ACC-415: Shared access doesn't grant delete permission"""
        rbac.share_resource(owner, resource, other_user.user_id)

        result = rbac.check_access(other_user, resource, Permission.DELETE)
        assert result is False

    def test_acc_416_non_owner_cannot_share_resource(self, rbac, other_user, resource):
        """ACC-416: Non-owner cannot share resource"""
        with pytest.raises(AccessDeniedError):
            rbac.share_resource(other_user, resource, "user-3")

    def test_acc_417_owner_can_unshare_resource(self, rbac, owner, other_user, resource):
        """ACC-417: Owner can revoke shared access"""
        # Share first
        rbac.share_resource(owner, resource, other_user.user_id)
        assert other_user.user_id in resource.shared_with

        # Unshare
        rbac.unshare_resource(owner, resource, other_user.user_id)
        assert other_user.user_id not in resource.shared_with


@pytest.mark.acc
@pytest.mark.security
class TestMultiRoleScenarios:
    """Test suite for users with multiple roles"""

    @pytest.fixture
    def rbac(self):
        return RBACEngine()

    def test_acc_418_user_with_multiple_roles_gets_union_permissions(self, rbac):
        """ACC-418: User with multiple roles gets union of all permissions"""
        user = User(user_id="multi-1", username="multi", email="multi@example.com")
        user.add_role(Role.VIEWER)  # READ
        user.add_role(Role.DEVELOPER)  # READ, WRITE, EXECUTE, SHARE

        permissions = rbac.get_permissions(user)

        assert Permission.READ in permissions
        assert Permission.WRITE in permissions
        assert Permission.EXECUTE in permissions
        assert Permission.SHARE in permissions
        assert Permission.DELETE not in permissions  # Neither role has this

    def test_acc_419_removing_role_removes_permissions(self, rbac):
        """ACC-419: Removing role removes associated permissions"""
        user = User(user_id="user-1", username="user", email="user@example.com")
        user.add_role(Role.ADMIN)
        user.add_role(Role.DEVELOPER)

        # Has admin permissions
        assert rbac.has_permission(user, Permission.ADMIN)

        # Remove admin role
        user.remove_role(Role.ADMIN)

        # No longer has admin permission
        assert not rbac.has_permission(user, Permission.ADMIN)
        # But still has developer permissions
        assert rbac.has_permission(user, Permission.WRITE)
