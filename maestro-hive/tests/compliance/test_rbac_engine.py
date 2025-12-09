#!/usr/bin/env python3
"""Tests for rbac_engine module."""

import pytest
import tempfile

from maestro_hive.compliance.rbac_engine import (
    RBACEngine,
    Permission,
    Role,
    RoleAssignment,
    AccessCheckResult,
    PermissionType,
    get_rbac_engine
)


class TestRBACEngine:
    """Tests for RBACEngine class."""

    def test_engine_initialization(self):
        """Test engine initializes correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = RBACEngine(storage_dir=tmpdir)
            assert engine.storage_dir.exists()

    def test_create_permission(self):
        """Test creating permissions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = RBACEngine(storage_dir=tmpdir)

            permission = engine.create_permission(
                name='read:documents',
                description='Read access to documents',
                resource='documents',
                actions=['read', 'list']
            )

            assert permission.name == 'read:documents'
            assert 'read' in permission.actions
            assert 'list' in permission.actions

    def test_create_role(self):
        """Test creating roles."""
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = RBACEngine(storage_dir=tmpdir)

            # Create permissions
            read_perm = engine.create_permission(
                name='read:docs',
                resource='documents',
                actions=['read']
            )

            # Create role with permission
            role = engine.create_role(
                name='viewer',
                description='Can view documents',
                permissions=[read_perm.name]
            )

            assert role.name == 'viewer'
            assert 'read:docs' in role.permissions

    def test_assign_role_to_user(self):
        """Test assigning role to user."""
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = RBACEngine(storage_dir=tmpdir)

            # Setup
            engine.create_permission(name='read:all', resource='*', actions=['read'])
            engine.create_role(name='reader', permissions=['read:all'])

            # Assign
            assignment = engine.assign_role(
                user_id='user-123',
                role_name='reader'
            )

            assert assignment.user_id == 'user-123'
            assert assignment.role_name == 'reader'

    def test_check_access_allowed(self):
        """Test checking access - allowed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = RBACEngine(storage_dir=tmpdir)

            # Setup
            engine.create_permission(
                name='read:documents',
                resource='documents',
                actions=['read', 'list']
            )
            engine.create_role(name='viewer', permissions=['read:documents'])
            engine.assign_role(user_id='user-1', role_name='viewer')

            # Check access
            result = engine.check_access(
                user_id='user-1',
                action='read',
                resource='documents'
            )

            assert result.allowed is True
            assert 'viewer' in result.roles

    def test_check_access_denied(self):
        """Test checking access - denied."""
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = RBACEngine(storage_dir=tmpdir)

            # Setup - viewer can only read
            engine.create_permission(
                name='read:documents',
                resource='documents',
                actions=['read']
            )
            engine.create_role(name='viewer', permissions=['read:documents'])
            engine.assign_role(user_id='user-1', role_name='viewer')

            # Check access for write (not allowed)
            result = engine.check_access(
                user_id='user-1',
                action='write',
                resource='documents'
            )

            assert result.allowed is False

    def test_hierarchical_roles(self):
        """Test role inheritance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = RBACEngine(storage_dir=tmpdir)

            # Create permissions
            engine.create_permission(name='read:docs', resource='documents', actions=['read'])
            engine.create_permission(name='write:docs', resource='documents', actions=['write'])

            # Create hierarchical roles
            engine.create_role(name='viewer', permissions=['read:docs'])
            engine.create_role(
                name='editor',
                permissions=['write:docs'],
                parent_roles=['viewer']  # Inherits from viewer
            )

            engine.assign_role(user_id='editor-user', role_name='editor')

            # Editor should be able to read (inherited) and write
            read_result = engine.check_access(
                user_id='editor-user',
                action='read',
                resource='documents'
            )
            assert read_result.allowed is True

            write_result = engine.check_access(
                user_id='editor-user',
                action='write',
                resource='documents'
            )
            assert write_result.allowed is True

    def test_wildcard_resource(self):
        """Test wildcard resource matching."""
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = RBACEngine(storage_dir=tmpdir)

            # Admin permission with wildcard
            engine.create_permission(
                name='admin:all',
                resource='*',
                actions=['*']
            )
            engine.create_role(name='admin', permissions=['admin:all'])
            engine.assign_role(user_id='admin-user', role_name='admin')

            # Admin should access anything
            result = engine.check_access(
                user_id='admin-user',
                action='delete',
                resource='any-resource'
            )
            assert result.allowed is True

    def test_revoke_role(self):
        """Test revoking role from user."""
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = RBACEngine(storage_dir=tmpdir)

            engine.create_permission(name='read:all', resource='*', actions=['read'])
            engine.create_role(name='reader', permissions=['read:all'])
            engine.assign_role(user_id='user-1', role_name='reader')

            # Verify access
            result1 = engine.check_access(user_id='user-1', action='read', resource='doc')
            assert result1.allowed is True

            # Revoke role
            engine.revoke_role(user_id='user-1', role_name='reader')

            # Verify access denied
            result2 = engine.check_access(user_id='user-1', action='read', resource='doc')
            assert result2.allowed is False

    def test_get_user_permissions(self):
        """Test getting all user permissions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = RBACEngine(storage_dir=tmpdir)

            engine.create_permission(name='perm-1', resource='r1', actions=['a1'])
            engine.create_permission(name='perm-2', resource='r2', actions=['a2'])
            engine.create_role(name='role-1', permissions=['perm-1', 'perm-2'])
            engine.assign_role(user_id='user-1', role_name='role-1')

            permissions = engine.get_user_permissions(user_id='user-1')
            permission_names = [p.name for p in permissions]

            assert 'perm-1' in permission_names
            assert 'perm-2' in permission_names

    def test_get_rbac_engine_factory(self):
        """Test factory function."""
        engine = get_rbac_engine()
        assert isinstance(engine, RBACEngine)


class TestPermission:
    """Tests for Permission dataclass."""

    def test_permission_creation(self):
        """Test permission creation."""
        perm = Permission(
            id='perm-001',
            name='read:documents',
            description='Read documents',
            resource='documents',
            actions=['read', 'list']
        )
        assert perm.name == 'read:documents'
        assert len(perm.actions) == 2

    def test_permission_to_dict(self):
        """Test permission serialization."""
        perm = Permission(
            id='perm-002',
            name='write:docs',
            resource='documents',
            actions=['write', 'update']
        )
        data = perm.to_dict()
        assert data['name'] == 'write:docs'
        assert 'write' in data['actions']


class TestRole:
    """Tests for Role dataclass."""

    def test_role_creation(self):
        """Test role creation."""
        role = Role(
            id='role-001',
            name='editor',
            description='Can edit content',
            permissions=['read:docs', 'write:docs']
        )
        assert role.name == 'editor'
        assert len(role.permissions) == 2

    def test_role_with_parent(self):
        """Test role with parent roles."""
        role = Role(
            id='role-002',
            name='admin',
            permissions=['admin:all'],
            parent_roles=['editor']
        )
        assert 'editor' in role.parent_roles


class TestAccessCheckResult:
    """Tests for AccessCheckResult dataclass."""

    def test_result_allowed(self):
        """Test allowed result."""
        result = AccessCheckResult(
            allowed=True,
            user_id='user-1',
            action='read',
            resource='doc-1',
            roles=['viewer'],
            permissions=['read:docs']
        )
        assert result.allowed is True
        assert 'viewer' in result.roles

    def test_result_denied(self):
        """Test denied result."""
        result = AccessCheckResult(
            allowed=False,
            user_id='user-1',
            action='delete',
            resource='doc-1',
            roles=['viewer'],
            permissions=[],
            reason='No delete permission'
        )
        assert result.allowed is False
        assert 'No delete permission' in result.reason
