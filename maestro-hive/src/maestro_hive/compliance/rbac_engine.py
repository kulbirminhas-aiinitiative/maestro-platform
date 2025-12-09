#!/usr/bin/env python3
"""
RBAC Engine: Role-Based Access Control for compliance.

Implements RBAC with hierarchical roles, permissions, and runtime checks.

SOC2 CC6.1: Logical access security.
ISO 27001 A.9: Access control.
GDPR Article 32: Security of processing.
"""

import json
import hashlib
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Callable
import threading
import fnmatch

logger = logging.getLogger(__name__)


class PermissionType(Enum):
    """Permission type categories."""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"
    EXECUTE = "execute"


@dataclass
class Permission:
    """A single permission."""
    id: str
    name: str
    resource_pattern: str  # Glob pattern for resources
    actions: List[str]     # Allowed actions
    description: Optional[str] = None
    conditions: Dict[str, Any] = field(default_factory=dict)

    def matches(self, resource: str, action: str) -> bool:
        """Check if permission matches resource and action."""
        if not fnmatch.fnmatch(resource, self.resource_pattern):
            return False

        # Check action patterns
        for action_pattern in self.actions:
            if action_pattern == '*' or fnmatch.fnmatch(action, action_pattern):
                return True

        return False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Role:
    """A role with permissions."""
    id: str
    name: str
    description: str
    permissions: List[Permission]
    parent_roles: List[str] = field(default_factory=list)  # Role inheritance
    priority: int = 0
    is_system: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['permissions'] = [p.to_dict() for p in self.permissions]
        return data


@dataclass
class RoleAssignment:
    """Assignment of role to principal."""
    id: str
    principal_id: str
    principal_type: str  # user, service, api_key
    role_id: str
    scope: Optional[str] = None  # Resource scope (e.g., project/maestro)
    granted_by: Optional[str] = None
    granted_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    expires_at: Optional[str] = None
    conditions: Dict[str, Any] = field(default_factory=dict)
    active: bool = True

    def is_valid(self) -> bool:
        """Check if assignment is currently valid."""
        if not self.active:
            return False

        if self.expires_at:
            expires = datetime.fromisoformat(self.expires_at.replace('Z', '+00:00').replace('+00:00', ''))
            if datetime.utcnow() > expires:
                return False

        return True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AccessCheckResult:
    """Result of access check."""
    allowed: bool
    principal_id: str
    resource: str
    action: str
    matched_roles: List[str]
    matched_permissions: List[str]
    reason: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class RBACEngine:
    """
    Role-Based Access Control engine.

    Features:
    - Hierarchical roles with inheritance
    - Fine-grained permissions with patterns
    - Scoped role assignments
    - Expiring assignments
    - Access audit logging
    """

    # Default system roles
    DEFAULT_ROLES = {
        'admin': Role(
            id='admin',
            name='Administrator',
            description='Full system access',
            permissions=[Permission(
                id='admin-all',
                name='Admin All',
                resource_pattern='*',
                actions=['*']
            )],
            priority=1000,
            is_system=True
        ),
        'developer': Role(
            id='developer',
            name='Developer',
            description='Development team access',
            permissions=[
                Permission(id='dev-code-rw', name='Code Read/Write',
                          resource_pattern='project/*/code/*', actions=['read', 'write']),
                Permission(id='dev-project-read', name='Project Read',
                          resource_pattern='project/*', actions=['read']),
                Permission(id='dev-compliance-read', name='Compliance Read',
                          resource_pattern='compliance/*', actions=['read']),
            ],
            priority=100,
            is_system=True
        ),
        'viewer': Role(
            id='viewer',
            name='Viewer',
            description='Read-only access',
            permissions=[
                Permission(id='view-all', name='View All',
                          resource_pattern='*', actions=['read']),
            ],
            priority=10,
            is_system=True
        ),
        'auditor': Role(
            id='auditor',
            name='Auditor',
            description='Audit and compliance access',
            permissions=[
                Permission(id='audit-read', name='Audit Read',
                          resource_pattern='audit/*', actions=['read', 'export']),
                Permission(id='compliance-read', name='Compliance Read',
                          resource_pattern='compliance/*', actions=['read']),
                Permission(id='risk-read', name='Risk Read',
                          resource_pattern='risk/*', actions=['read']),
            ],
            priority=50,
            is_system=True
        ),
    }

    def __init__(
        self,
        storage_dir: Optional[str] = None,
        audit_callback: Optional[Callable[[AccessCheckResult], None]] = None,
        cache_ttl_seconds: int = 300
    ):
        """
        Initialize RBAC engine.

        Args:
            storage_dir: Directory for RBAC data
            audit_callback: Callback for audit logging
            cache_ttl_seconds: Cache TTL for role resolutions
        """
        self.storage_dir = Path(storage_dir) if storage_dir else \
            Path.home() / '.maestro' / 'rbac'
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.audit_callback = audit_callback
        self.cache_ttl = cache_ttl_seconds

        self._roles: Dict[str, Role] = {}
        self._assignments: Dict[str, RoleAssignment] = {}
        self._cache: Dict[str, tuple] = {}  # principal -> (roles, timestamp)
        self._lock = threading.RLock()

        # Initialize default roles
        for role_id, role in self.DEFAULT_ROLES.items():
            self._roles[role_id] = role

        self._load_data()

        logger.info(f"RBACEngine initialized: {len(self._roles)} roles, "
                   f"{len(self._assignments)} assignments")

    def check_access(
        self,
        principal_id: str,
        resource: str,
        action: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AccessCheckResult:
        """
        Check if principal has access to resource for action.

        Args:
            principal_id: User/service identifier
            resource: Resource path
            action: Requested action
            context: Additional context

        Returns:
            AccessCheckResult with decision
        """
        import time
        start_time = time.time()

        context = context or {}
        matched_roles = []
        matched_permissions = []

        # Get effective roles for principal
        roles = self._get_effective_roles(principal_id, resource)

        # Check permissions
        allowed = False
        for role in roles:
            for permission in role.permissions:
                if permission.matches(resource, action):
                    matched_roles.append(role.id)
                    matched_permissions.append(permission.id)
                    allowed = True
                    break

        duration_ms = (time.time() - start_time) * 1000

        if allowed:
            reason = f"Allowed by role(s): {', '.join(set(matched_roles))}"
        else:
            reason = "No matching permission found"

        result = AccessCheckResult(
            allowed=allowed,
            principal_id=principal_id,
            resource=resource,
            action=action,
            matched_roles=list(set(matched_roles)),
            matched_permissions=list(set(matched_permissions)),
            reason=reason,
            duration_ms=duration_ms
        )

        # Audit callback
        if self.audit_callback:
            try:
                self.audit_callback(result)
            except Exception as e:
                logger.error(f"Audit callback error: {e}")

        return result

    def enforce(
        self,
        principal_id: str,
        resource: str,
        action: str,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Enforce access control (raises exception if denied).

        Args:
            principal_id: Principal identifier
            resource: Resource
            action: Action

        Returns:
            True if allowed

        Raises:
            PermissionError: If access denied
        """
        result = self.check_access(principal_id, resource, action, context)

        if not result.allowed:
            raise PermissionError(
                f"Access denied for {principal_id} on {resource}:{action} - {result.reason}"
            )

        return True

    def assign_role(
        self,
        principal_id: str,
        role_id: str,
        principal_type: str = "user",
        scope: Optional[str] = None,
        granted_by: Optional[str] = None,
        expires_in_days: Optional[int] = None
    ) -> RoleAssignment:
        """
        Assign a role to a principal.

        Args:
            principal_id: Principal identifier
            role_id: Role to assign
            principal_type: Type of principal
            scope: Optional scope restriction
            granted_by: Who granted the role
            expires_in_days: Expiration in days

        Returns:
            RoleAssignment
        """
        if role_id not in self._roles:
            raise ValueError(f"Unknown role: {role_id}")

        assignment_id = hashlib.md5(
            f"{principal_id}:{role_id}:{scope or '*'}".encode()
        ).hexdigest()[:12]

        expires_at = None
        if expires_in_days:
            expires_at = (datetime.utcnow() + timedelta(days=expires_in_days)).isoformat()

        assignment = RoleAssignment(
            id=assignment_id,
            principal_id=principal_id,
            principal_type=principal_type,
            role_id=role_id,
            scope=scope,
            granted_by=granted_by,
            expires_at=expires_at
        )

        with self._lock:
            self._assignments[assignment_id] = assignment
            self._invalidate_cache(principal_id)
            self._save_assignment(assignment)

        logger.info(f"Assigned role {role_id} to {principal_id}")

        return assignment

    def revoke_role(
        self,
        principal_id: str,
        role_id: str,
        scope: Optional[str] = None
    ) -> bool:
        """Revoke a role from a principal."""
        assignment_id = hashlib.md5(
            f"{principal_id}:{role_id}:{scope or '*'}".encode()
        ).hexdigest()[:12]

        with self._lock:
            if assignment_id in self._assignments:
                self._assignments[assignment_id].active = False
                self._invalidate_cache(principal_id)
                self._save_assignment(self._assignments[assignment_id])
                logger.info(f"Revoked role {role_id} from {principal_id}")
                return True

        return False

    def get_principal_roles(self, principal_id: str) -> List[Role]:
        """Get all roles assigned to a principal."""
        return self._get_effective_roles(principal_id, '*')

    def create_role(
        self,
        role_id: str,
        name: str,
        description: str,
        permissions: List[Permission],
        parent_roles: Optional[List[str]] = None,
        priority: int = 50
    ) -> Role:
        """Create a new role."""
        if role_id in self._roles and self._roles[role_id].is_system:
            raise ValueError(f"Cannot modify system role: {role_id}")

        role = Role(
            id=role_id,
            name=name,
            description=description,
            permissions=permissions,
            parent_roles=parent_roles or [],
            priority=priority
        )

        with self._lock:
            self._roles[role_id] = role
            self._save_role(role)

        return role

    def get_role(self, role_id: str) -> Optional[Role]:
        """Get a role by ID."""
        return self._roles.get(role_id)

    def list_roles(self) -> List[Role]:
        """List all roles."""
        return list(self._roles.values())

    def _get_effective_roles(
        self,
        principal_id: str,
        resource: str
    ) -> List[Role]:
        """Get effective roles for principal (with caching)."""
        cache_key = f"{principal_id}:{resource}"

        # Check cache
        with self._lock:
            if cache_key in self._cache:
                roles, timestamp = self._cache[cache_key]
                if (datetime.utcnow() - timestamp).total_seconds() < self.cache_ttl:
                    return roles

        # Find applicable assignments
        roles = []
        seen_roles: Set[str] = set()

        for assignment in self._assignments.values():
            if assignment.principal_id != principal_id:
                continue
            if not assignment.is_valid():
                continue

            # Check scope
            if assignment.scope and not fnmatch.fnmatch(resource, assignment.scope):
                continue

            # Get role and parent roles
            self._collect_roles(assignment.role_id, roles, seen_roles)

        # Sort by priority
        roles.sort(key=lambda r: r.priority, reverse=True)

        # Cache result
        with self._lock:
            self._cache[cache_key] = (roles, datetime.utcnow())

        return roles

    def _collect_roles(
        self,
        role_id: str,
        roles: List[Role],
        seen: Set[str]
    ) -> None:
        """Collect role and parent roles (recursive)."""
        if role_id in seen:
            return
        seen.add(role_id)

        role = self._roles.get(role_id)
        if role:
            roles.append(role)

            # Collect parent roles
            for parent_id in role.parent_roles:
                self._collect_roles(parent_id, roles, seen)

    def _invalidate_cache(self, principal_id: str) -> None:
        """Invalidate cache for principal."""
        with self._lock:
            keys_to_remove = [k for k in self._cache if k.startswith(f"{principal_id}:")]
            for key in keys_to_remove:
                del self._cache[key]

    def _save_role(self, role: Role) -> None:
        """Save role to storage."""
        file_path = self.storage_dir / "roles" / f"{role.id}.json"
        file_path.parent.mkdir(exist_ok=True)
        with open(file_path, 'w') as f:
            json.dump(role.to_dict(), f, indent=2)

    def _save_assignment(self, assignment: RoleAssignment) -> None:
        """Save assignment to storage."""
        file_path = self.storage_dir / "assignments" / f"{assignment.id}.json"
        file_path.parent.mkdir(exist_ok=True)
        with open(file_path, 'w') as f:
            json.dump(assignment.to_dict(), f, indent=2)

    def _load_data(self) -> None:
        """Load roles and assignments from storage."""
        # Load custom roles
        roles_dir = self.storage_dir / "roles"
        if roles_dir.exists():
            for file_path in roles_dir.glob("*.json"):
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                        role = self._dict_to_role(data)
                        if not role.is_system:
                            self._roles[role.id] = role
                except Exception as e:
                    logger.error(f"Error loading role {file_path}: {e}")

        # Load assignments
        assignments_dir = self.storage_dir / "assignments"
        if assignments_dir.exists():
            for file_path in assignments_dir.glob("*.json"):
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                        assignment = RoleAssignment(**data)
                        self._assignments[assignment.id] = assignment
                except Exception as e:
                    logger.error(f"Error loading assignment {file_path}: {e}")

    def _dict_to_role(self, data: Dict[str, Any]) -> Role:
        """Convert dictionary to Role."""
        permissions = [Permission(**p) for p in data.get('permissions', [])]
        return Role(
            id=data['id'],
            name=data['name'],
            description=data.get('description', ''),
            permissions=permissions,
            parent_roles=data.get('parent_roles', []),
            priority=data.get('priority', 0),
            is_system=data.get('is_system', False),
            metadata=data.get('metadata', {})
        )


def get_rbac_engine(**kwargs) -> RBACEngine:
    """Get RBAC engine instance."""
    return RBACEngine(**kwargs)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    rbac = RBACEngine()

    # Assign role
    rbac.assign_role("user-001", "developer", granted_by="admin")

    # Check access
    result = rbac.check_access("user-001", "project/maestro/code/main.py", "read")
    print(f"Read code: {result.allowed} - {result.reason}")

    result = rbac.check_access("user-001", "project/maestro/code/main.py", "delete")
    print(f"Delete code: {result.allowed} - {result.reason}")
