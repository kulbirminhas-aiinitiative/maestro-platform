"""
Permission definitions and management
"""

from enum import Enum
from typing import Set, Dict, List, Optional
from dataclasses import dataclass, field


class Permission(str, Enum):
    """System permissions for tools and operations"""

    # Message permissions
    POST_MESSAGE = "post_message"
    GET_MESSAGES = "get_messages"
    DELETE_MESSAGE = "delete_message"

    # Task permissions
    CREATE_TASK = "create_task"
    CLAIM_TASK = "claim_task"
    COMPLETE_TASK = "complete_task"
    FAIL_TASK = "fail_task"
    UPDATE_TASK = "update_task"
    DELETE_TASK = "delete_task"
    ASSIGN_TASK = "assign_task"  # Assign task to others

    # Knowledge permissions
    SHARE_KNOWLEDGE = "share_knowledge"
    GET_KNOWLEDGE = "get_knowledge"
    UPDATE_KNOWLEDGE = "update_knowledge"
    DELETE_KNOWLEDGE = "delete_knowledge"

    # Artifact permissions
    STORE_ARTIFACT = "store_artifact"
    GET_ARTIFACTS = "get_artifacts"
    DELETE_ARTIFACT = "delete_artifact"

    # Agent status permissions
    UPDATE_STATUS = "update_status"
    GET_TEAM_STATUS = "get_team_status"

    # Decision permissions
    PROPOSE_DECISION = "propose_decision"
    VOTE_DECISION = "vote_decision"
    FINALIZE_DECISION = "finalize_decision"  # Force finalize

    # Workflow permissions
    CREATE_WORKFLOW = "create_workflow"
    START_WORKFLOW = "start_workflow"
    PAUSE_WORKFLOW = "pause_workflow"
    CANCEL_WORKFLOW = "cancel_workflow"

    # Administrative permissions
    MANAGE_TEAM = "manage_team"
    MANAGE_ROLES = "manage_roles"
    VIEW_METRICS = "view_metrics"


@dataclass
class PermissionSet:
    """Set of permissions with optional constraints"""
    permissions: Set[Permission] = field(default_factory=set)
    constraints: Dict[str, any] = field(default_factory=dict)

    def has_permission(self, permission: Permission) -> bool:
        """Check if permission is granted"""
        return permission in self.permissions

    def add_permission(self, permission: Permission):
        """Add a permission"""
        self.permissions.add(permission)

    def remove_permission(self, permission: Permission):
        """Remove a permission"""
        self.permissions.discard(permission)

    def add_constraint(self, key: str, value: any):
        """Add a constraint (e.g., max_tasks=5)"""
        self.constraints[key] = value

    def get_constraint(self, key: str, default=None):
        """Get constraint value"""
        return self.constraints.get(key, default)


class PermissionManager:
    """Manages permission definitions and hierarchies"""

    # Permission groups for common patterns
    BASIC_PERMISSIONS = {
        Permission.POST_MESSAGE,
        Permission.GET_MESSAGES,
        Permission.GET_KNOWLEDGE,
        Permission.GET_TEAM_STATUS,
        Permission.UPDATE_STATUS,
    }

    DEVELOPER_PERMISSIONS = BASIC_PERMISSIONS | {
        Permission.CLAIM_TASK,
        Permission.COMPLETE_TASK,
        Permission.FAIL_TASK,
        Permission.SHARE_KNOWLEDGE,
        Permission.STORE_ARTIFACT,
        Permission.GET_ARTIFACTS,
    }

    REVIEWER_PERMISSIONS = BASIC_PERMISSIONS | {
        Permission.GET_ARTIFACTS,
        Permission.VOTE_DECISION,
        Permission.PROPOSE_DECISION,
    }

    COORDINATOR_PERMISSIONS = DEVELOPER_PERMISSIONS | {
        Permission.CREATE_TASK,
        Permission.ASSIGN_TASK,
        Permission.UPDATE_TASK,
        Permission.PROPOSE_DECISION,
        Permission.VOTE_DECISION,
        Permission.CREATE_WORKFLOW,
        Permission.START_WORKFLOW,
    }

    ADMIN_PERMISSIONS = set(Permission)  # All permissions

    @staticmethod
    def get_permission_group(group_name: str) -> Set[Permission]:
        """Get a predefined permission group"""
        groups = {
            "basic": PermissionManager.BASIC_PERMISSIONS,
            "developer": PermissionManager.DEVELOPER_PERMISSIONS,
            "reviewer": PermissionManager.REVIEWER_PERMISSIONS,
            "coordinator": PermissionManager.COORDINATOR_PERMISSIONS,
            "admin": PermissionManager.ADMIN_PERMISSIONS,
        }
        return groups.get(group_name, set())

    @staticmethod
    def tool_to_permission(tool_name: str) -> Optional[Permission]:
        """Map tool name to required permission"""
        mapping = {
            "post_message": Permission.POST_MESSAGE,
            "get_messages": Permission.GET_MESSAGES,
            "claim_task": Permission.CLAIM_TASK,
            "complete_task": Permission.COMPLETE_TASK,
            "share_knowledge": Permission.SHARE_KNOWLEDGE,
            "get_knowledge": Permission.GET_KNOWLEDGE,
            "update_status": Permission.UPDATE_STATUS,
            "get_team_status": Permission.GET_TEAM_STATUS,
            "store_artifact": Permission.STORE_ARTIFACT,
            "get_artifacts": Permission.GET_ARTIFACTS,
            "propose_decision": Permission.PROPOSE_DECISION,
            "vote_decision": Permission.VOTE_DECISION,
            "create_task": Permission.CREATE_TASK,
        }
        try:
            return mapping.get(tool_name)
        except KeyError:
            return None

    @staticmethod
    def describe_permission(permission: Permission) -> str:
        """Get human-readable description of permission"""
        descriptions = {
            Permission.POST_MESSAGE: "Send messages to team members",
            Permission.GET_MESSAGES: "Read messages from team",
            Permission.CREATE_TASK: "Create new tasks",
            Permission.CLAIM_TASK: "Claim and work on tasks",
            Permission.COMPLETE_TASK: "Mark tasks as completed",
            Permission.SHARE_KNOWLEDGE: "Add to team knowledge base",
            Permission.GET_KNOWLEDGE: "Read from knowledge base",
            Permission.PROPOSE_DECISION: "Propose team decisions",
            Permission.VOTE_DECISION: "Vote on decisions",
            Permission.MANAGE_TEAM: "Manage team members and settings",
        }
        return descriptions.get(permission, permission.value)


# Example permission sets for different scenarios
def get_readonly_permissions() -> PermissionSet:
    """Permissions for read-only access"""
    return PermissionSet(permissions={
        Permission.GET_MESSAGES,
        Permission.GET_KNOWLEDGE,
        Permission.GET_ARTIFACTS,
        Permission.GET_TEAM_STATUS,
    })


def get_contributor_permissions() -> PermissionSet:
    """Permissions for active contributors"""
    perm_set = PermissionSet(permissions=PermissionManager.DEVELOPER_PERMISSIONS)
    perm_set.add_constraint("max_tasks", 3)  # Can claim up to 3 tasks
    return perm_set


def get_lead_permissions() -> PermissionSet:
    """Permissions for team leads"""
    perm_set = PermissionSet(permissions=PermissionManager.COORDINATOR_PERMISSIONS)
    perm_set.add_constraint("can_reassign", True)
    return perm_set


if __name__ == "__main__":
    # Example usage
    print("Permission Groups:")
    print("=" * 50)

    for group in ["basic", "developer", "reviewer", "coordinator"]:
        perms = PermissionManager.get_permission_group(group)
        print(f"\n{group.upper()}: ({len(perms)} permissions)")
        for p in sorted(perms, key=lambda x: x.value):
            print(f"  - {p.value}: {PermissionManager.describe_permission(p)}")
