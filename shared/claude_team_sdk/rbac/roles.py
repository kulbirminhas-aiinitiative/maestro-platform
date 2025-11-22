"""
Role definitions and management
"""

from dataclasses import dataclass, field
from typing import Dict, Set, Optional, List
from .permissions import Permission, PermissionSet, PermissionManager


@dataclass
class Role:
    """Represents an agent role with permissions"""
    role_id: str
    name: str
    description: str
    permissions: PermissionSet = field(default_factory=PermissionSet)
    inherits_from: Optional[str] = None  # Role inheritance
    metadata: Dict = field(default_factory=dict)

    def has_permission(self, permission: Permission) -> bool:
        """Check if role has a specific permission"""
        return self.permissions.has_permission(permission)

    def to_dict(self) -> Dict:
        return {
            "role_id": self.role_id,
            "name": self.name,
            "description": self.description,
            "permissions": [p.value for p in self.permissions.permissions],
            "constraints": self.permissions.constraints,
            "inherits_from": self.inherits_from,
            "metadata": self.metadata
        }


class RoleManager:
    """Manages role definitions and assignments"""

    def __init__(self):
        self.roles: Dict[str, Role] = {}
        self._initialize_default_roles()

    def _initialize_default_roles(self):
        """Create default system roles"""

        # Observer role - Read-only access
        self.create_role(
            role_id="observer",
            name="Observer",
            description="Read-only access to team activities",
            permissions=PermissionSet(permissions={
                Permission.GET_MESSAGES,
                Permission.GET_KNOWLEDGE,
                Permission.GET_ARTIFACTS,
                Permission.GET_TEAM_STATUS,
            })
        )

        # Developer role - Can execute tasks
        developer_perms = PermissionSet(
            permissions=PermissionManager.DEVELOPER_PERMISSIONS
        )
        developer_perms.add_constraint("max_tasks", 3)

        self.create_role(
            role_id="developer",
            name="Developer",
            description="Can claim and complete development tasks",
            permissions=developer_perms
        )

        # Reviewer role - Can review and approve
        self.create_role(
            role_id="reviewer",
            name="Reviewer",
            description="Can review work and vote on decisions",
            permissions=PermissionSet(
                permissions=PermissionManager.REVIEWER_PERMISSIONS
            )
        )

        # Architect role - Technical leadership
        architect_perms = PermissionSet(
            permissions=PermissionManager.DEVELOPER_PERMISSIONS | {
                Permission.CREATE_TASK,
                Permission.PROPOSE_DECISION,
                Permission.VOTE_DECISION,
                Permission.CREATE_WORKFLOW,
            }
        )

        self.create_role(
            role_id="architect",
            name="Architect",
            description="Technical leadership and design",
            permissions=architect_perms
        )

        # Coordinator role - Project management
        self.create_role(
            role_id="coordinator",
            name="Coordinator",
            description="Project coordination and task management",
            permissions=PermissionSet(
                permissions=PermissionManager.COORDINATOR_PERMISSIONS
            )
        )

        # Admin role - Full access
        admin_perms = PermissionSet(
            permissions=PermissionManager.ADMIN_PERMISSIONS
        )

        self.create_role(
            role_id="admin",
            name="Administrator",
            description="Full system access",
            permissions=admin_perms
        )

        # Tester role - Quality assurance
        tester_perms = PermissionSet(permissions={
            Permission.POST_MESSAGE,
            Permission.GET_MESSAGES,
            Permission.CLAIM_TASK,
            Permission.COMPLETE_TASK,
            Permission.FAIL_TASK,
            Permission.STORE_ARTIFACT,
            Permission.GET_ARTIFACTS,
            Permission.SHARE_KNOWLEDGE,
            Permission.GET_KNOWLEDGE,
            Permission.UPDATE_STATUS,
            Permission.GET_TEAM_STATUS,
        })
        tester_perms.add_constraint("task_types", ["test", "qa"])

        self.create_role(
            role_id="tester",
            name="Tester",
            description="Quality assurance and testing",
            permissions=tester_perms
        )

    def create_role(
        self,
        role_id: str,
        name: str,
        description: str,
        permissions: Optional[PermissionSet] = None,
        inherits_from: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Role:
        """Create a new role"""

        if role_id in self.roles:
            raise ValueError(f"Role {role_id} already exists")

        # Handle inheritance
        if inherits_from:
            if inherits_from not in self.roles:
                raise ValueError(f"Parent role {inherits_from} not found")

            parent_role = self.roles[inherits_from]
            inherited_permissions = PermissionSet(
                permissions=parent_role.permissions.permissions.copy(),
                constraints=parent_role.permissions.constraints.copy()
            )

            # Merge with provided permissions
            if permissions:
                inherited_permissions.permissions.update(permissions.permissions)
                inherited_permissions.constraints.update(permissions.constraints)

            permissions = inherited_permissions

        role = Role(
            role_id=role_id,
            name=name,
            description=description,
            permissions=permissions or PermissionSet(),
            inherits_from=inherits_from,
            metadata=metadata or {}
        )

        self.roles[role_id] = role
        return role

    def get_role(self, role_id: str) -> Optional[Role]:
        """Get role by ID"""
        return self.roles.get(role_id)

    def delete_role(self, role_id: str):
        """Delete a role"""
        # Don't allow deleting roles that others inherit from
        for role in self.roles.values():
            if role.inherits_from == role_id:
                raise ValueError(
                    f"Cannot delete role {role_id}: role {role.role_id} inherits from it"
                )

        if role_id in self.roles:
            del self.roles[role_id]

    def grant_permission(self, role_id: str, permission: Permission):
        """Grant a permission to a role"""
        role = self.get_role(role_id)
        if not role:
            raise ValueError(f"Role {role_id} not found")

        role.permissions.add_permission(permission)

    def revoke_permission(self, role_id: str, permission: Permission):
        """Revoke a permission from a role"""
        role = self.get_role(role_id)
        if not role:
            raise ValueError(f"Role {role_id} not found")

        role.permissions.remove_permission(permission)

    def list_roles(self) -> List[Role]:
        """List all roles"""
        return list(self.roles.values())

    def get_effective_permissions(self, role_id: str) -> PermissionSet:
        """
        Get effective permissions including inherited ones

        Args:
            role_id: Role ID

        Returns:
            Complete set of permissions
        """
        role = self.get_role(role_id)
        if not role:
            raise ValueError(f"Role {role_id} not found")

        effective = PermissionSet(
            permissions=role.permissions.permissions.copy(),
            constraints=role.permissions.constraints.copy()
        )

        # Add inherited permissions
        if role.inherits_from:
            parent_perms = self.get_effective_permissions(role.inherits_from)
            effective.permissions.update(parent_perms.permissions)

            # Merge constraints (child overrides parent)
            merged_constraints = parent_perms.constraints.copy()
            merged_constraints.update(effective.constraints)
            effective.constraints = merged_constraints

        return effective

    def create_custom_role(
        self,
        role_id: str,
        name: str,
        description: str,
        permission_group: str = "basic",
        additional_permissions: Optional[Set[Permission]] = None
    ) -> Role:
        """
        Helper to create custom role from permission group

        Args:
            role_id: Unique role ID
            name: Role name
            description: Role description
            permission_group: Base permission group (basic, developer, reviewer, coordinator)
            additional_permissions: Additional permissions to add

        Returns:
            Created role
        """
        base_perms = PermissionManager.get_permission_group(permission_group)

        if additional_permissions:
            base_perms = base_perms | additional_permissions

        return self.create_role(
            role_id=role_id,
            name=name,
            description=description,
            permissions=PermissionSet(permissions=base_perms)
        )


# Example usage
if __name__ == "__main__":
    manager = RoleManager()

    print("Default Roles:")
    print("=" * 70)

    for role in manager.list_roles():
        print(f"\n{role.name} ({role.role_id})")
        print(f"  Description: {role.description}")
        print(f"  Permissions: {len(role.permissions.permissions)}")

        effective = manager.get_effective_permissions(role.role_id)
        print(f"  Effective Permissions: {len(effective.permissions)}")

        if effective.constraints:
            print(f"  Constraints: {effective.constraints}")

    # Create a custom role
    print("\n" + "=" * 70)
    print("\nCreating custom 'Senior Developer' role...")

    custom_role = manager.create_custom_role(
        role_id="senior_developer",
        name="Senior Developer",
        description="Experienced developer with additional privileges",
        permission_group="developer",
        additional_permissions={
            Permission.CREATE_TASK,
            Permission.ASSIGN_TASK,
            Permission.PROPOSE_DECISION,
        }
    )

    print(f"\nCreated: {custom_role.name}")
    print(f"Permissions: {[p.value for p in custom_role.permissions.permissions]}")

    # Test inheritance
    print("\n" + "=" * 70)
    print("\nCreating role with inheritance...")

    inherited_role = manager.create_role(
        role_id="lead_developer",
        name="Lead Developer",
        description="Leads development team",
        inherits_from="senior_developer",
        permissions=PermissionSet(permissions={
            Permission.CREATE_WORKFLOW,
            Permission.START_WORKFLOW,
        })
    )

    effective_perms = manager.get_effective_permissions("lead_developer")
    print(f"\nLead Developer effective permissions: {len(effective_perms.permissions)}")
    print(f"Includes inherited + own: {[p.value for p in sorted(effective_perms.permissions, key=lambda x: x.value)]}")
