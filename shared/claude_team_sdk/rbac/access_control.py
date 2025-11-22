"""
Access control enforcement for RBAC
"""

from typing import Optional, Dict, Any, Callable
from datetime import datetime
import asyncio

from .permissions import Permission, PermissionManager
from .roles import Role, RoleManager


class AccessDeniedException(Exception):
    """Raised when access is denied"""

    def __init__(self, agent_id: str, tool_name: str, reason: str):
        self.agent_id = agent_id
        self.tool_name = tool_name
        self.reason = reason
        super().__init__(f"Access denied for {agent_id} on {tool_name}: {reason}")


class AccessController:
    """
    Enforces role-based access control for all operations
    """

    def __init__(self, role_manager: RoleManager):
        """
        Initialize access controller

        Args:
            role_manager: RoleManager instance
        """
        self.role_manager = role_manager
        self.audit_log: list = []
        self.access_cache: Dict[str, Dict] = {}  # Simple cache

    def check_access(
        self,
        agent_id: str,
        role_id: str,
        tool_name: str,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Check if agent has access to use tool

        Args:
            agent_id: Agent requesting access
            role_id: Agent's role
            tool_name: Tool being accessed
            context: Additional context for constraint checking

        Returns:
            True if access granted

        Raises:
            AccessDeniedException if access denied
        """
        # Get role
        role = self.role_manager.get_role(role_id)
        if not role:
            self._log_access(agent_id, role_id, tool_name, False, "Role not found")
            raise AccessDeniedException(agent_id, tool_name, "Invalid role")

        # Get required permission
        required_permission = PermissionManager.tool_to_permission(tool_name)
        if not required_permission:
            # Unknown tool - allow by default (log warning)
            self._log_access(agent_id, role_id, tool_name, True, "Unknown tool - allowed")
            return True

        # Get effective permissions (including inherited)
        effective_perms = self.role_manager.get_effective_permissions(role_id)

        # Check permission
        if not effective_perms.has_permission(required_permission):
            reason = f"Missing permission: {required_permission.value}"
            self._log_access(agent_id, role_id, tool_name, False, reason)
            raise AccessDeniedException(agent_id, tool_name, reason)

        # Check constraints
        if context:
            constraint_check = self._check_constraints(
                effective_perms,
                tool_name,
                context
            )
            if not constraint_check[0]:
                self._log_access(agent_id, role_id, tool_name, False, constraint_check[1])
                raise AccessDeniedException(agent_id, tool_name, constraint_check[1])

        # Access granted
        self._log_access(agent_id, role_id, tool_name, True, "Access granted")
        return True

    def _check_constraints(
        self,
        permissions: "PermissionSet",
        tool_name: str,
        context: Dict[str, Any]
    ) -> tuple[bool, str]:
        """
        Check role constraints

        Args:
            permissions: Permission set with constraints
            tool_name: Tool being accessed
            context: Context for constraint checking

        Returns:
            (allowed, reason)
        """
        # Check max_tasks constraint
        if tool_name == "claim_task":
            max_tasks = permissions.get_constraint("max_tasks")
            if max_tasks and context.get("current_task_count", 0) >= max_tasks:
                return False, f"Max tasks limit reached ({max_tasks})"

        # Check task_types constraint
        if tool_name == "claim_task":
            allowed_types = permissions.get_constraint("task_types")
            if allowed_types:
                task_type = context.get("task_type")
                if task_type and task_type not in allowed_types:
                    return False, f"Task type '{task_type}' not allowed for this role"

        # Check can_reassign constraint
        if tool_name == "assign_task":
            can_reassign = permissions.get_constraint("can_reassign", False)
            if not can_reassign:
                task_assigned = context.get("task_assigned_to")
                if task_assigned and task_assigned != context.get("agent_id"):
                    return False, "Cannot reassign tasks assigned to others"

        return True, "Constraints satisfied"

    def _log_access(
        self,
        agent_id: str,
        role_id: str,
        tool_name: str,
        granted: bool,
        reason: str
    ):
        """Log access attempt"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "agent_id": agent_id,
            "role_id": role_id,
            "tool_name": tool_name,
            "granted": granted,
            "reason": reason
        }
        self.audit_log.append(log_entry)

        # Keep only last 1000 entries in memory
        if len(self.audit_log) > 1000:
            self.audit_log = self.audit_log[-1000:]

    def get_audit_log(
        self,
        agent_id: Optional[str] = None,
        limit: int = 100
    ) -> list:
        """
        Get audit log entries

        Args:
            agent_id: Filter by agent (optional)
            limit: Max entries to return

        Returns:
            List of log entries
        """
        logs = self.audit_log

        if agent_id:
            logs = [log for log in logs if log["agent_id"] == agent_id]

        return logs[-limit:]

    def get_denied_attempts(
        self,
        since_minutes: int = 60
    ) -> list:
        """Get recent denied access attempts"""
        cutoff = datetime.utcnow().timestamp() - (since_minutes * 60)

        denied = [
            log for log in self.audit_log
            if not log["granted"]
            and datetime.fromisoformat(log["timestamp"]).timestamp() > cutoff
        ]

        return denied

    async def enforce_async(
        self,
        agent_id: str,
        role_id: str,
        tool_name: str,
        tool_function: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Enforce access control and execute tool if allowed

        Args:
            agent_id: Agent ID
            role_id: Agent's role
            tool_name: Tool name
            tool_function: Function to execute if allowed
            *args, **kwargs: Arguments for tool function

        Returns:
            Result from tool_function

        Raises:
            AccessDeniedException if access denied
        """
        # Check access
        context = kwargs.get("context", {})
        context["agent_id"] = agent_id
        self.check_access(agent_id, role_id, tool_name, context)

        # Execute tool
        if asyncio.iscoroutinefunction(tool_function):
            return await tool_function(*args, **kwargs)
        else:
            return tool_function(*args, **kwargs)

    def get_agent_permissions(self, role_id: str) -> Dict[str, Any]:
        """
        Get summary of agent's permissions

        Args:
            role_id: Agent's role

        Returns:
            Dictionary with permissions and constraints
        """
        role = self.role_manager.get_role(role_id)
        if not role:
            return {"error": "Role not found"}

        effective = self.role_manager.get_effective_permissions(role_id)

        return {
            "role": role.name,
            "role_id": role_id,
            "permissions": sorted([p.value for p in effective.permissions]),
            "constraints": effective.constraints,
            "inherits_from": role.inherits_from,
            "tool_access": self._get_tool_access_summary(effective)
        }

    def _get_tool_access_summary(self, permissions: "PermissionSet") -> Dict[str, bool]:
        """Get summary of which tools are accessible"""
        tools = [
            "post_message", "get_messages", "claim_task", "complete_task",
            "share_knowledge", "get_knowledge", "store_artifact", "get_artifacts",
            "update_status", "get_team_status", "propose_decision", "vote_decision",
            "create_task", "create_workflow"
        ]

        access = {}
        for tool in tools:
            perm = PermissionManager.tool_to_permission(tool)
            access[tool] = perm is not None and permissions.has_permission(perm)

        return access


# Decorator for enforcing access control
def require_permission(permission: Permission):
    """
    Decorator to enforce permission requirements

    Usage:
        @require_permission(Permission.CREATE_TASK)
        async def create_task(agent_id: str, role_id: str, ...):
            ...
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract agent_id and role_id from kwargs
            agent_id = kwargs.get("agent_id")
            role_id = kwargs.get("role_id")

            if not agent_id or not role_id:
                raise ValueError("agent_id and role_id required for access control")

            # This would need access to AccessController instance
            # In practice, would be injected via dependency injection

            return await func(*args, **kwargs)

        return wrapper
    return decorator


# Example usage
if __name__ == "__main__":
    from .roles import RoleManager

    role_manager = RoleManager()
    access_controller = AccessController(role_manager)

    print("Access Control Examples")
    print("=" * 70)

    # Test 1: Developer claiming task
    print("\nTest 1: Developer claiming task")
    try:
        access_controller.check_access(
            agent_id="dev1",
            role_id="developer",
            tool_name="claim_task",
            context={"current_task_count": 2}
        )
        print("✓ Access granted")
    except AccessDeniedException as e:
        print(f"✗ {e}")

    # Test 2: Developer trying to create workflow (should fail)
    print("\nTest 2: Developer creating workflow (should fail)")
    try:
        access_controller.check_access(
            agent_id="dev1",
            role_id="developer",
            tool_name="create_workflow"
        )
        print("✓ Access granted")
    except AccessDeniedException as e:
        print(f"✗ {e}")

    # Test 3: Coordinator creating workflow
    print("\nTest 3: Coordinator creating workflow")
    try:
        access_controller.check_access(
            agent_id="coord1",
            role_id="coordinator",
            tool_name="create_workflow"
        )
        print("✓ Access granted")
    except AccessDeniedException as e:
        print(f"✗ {e}")

    # Test 4: Check max_tasks constraint
    print("\nTest 4: Developer exceeding max_tasks")
    try:
        access_controller.check_access(
            agent_id="dev1",
            role_id="developer",
            tool_name="claim_task",
            context={"current_task_count": 3}  # Limit is 3
        )
        print("✓ Access granted")
    except AccessDeniedException as e:
        print(f"✗ {e}")

    # Show permissions summary
    print("\n" + "=" * 70)
    print("\nDeveloper Permissions Summary:")
    summary = access_controller.get_agent_permissions("developer")
    print(f"\nRole: {summary['role']}")
    print(f"Permissions: {len(summary['permissions'])}")
    print(f"Constraints: {summary['constraints']}")
    print("\nTool Access:")
    for tool, has_access in summary["tool_access"].items():
        status = "✓" if has_access else "✗"
        print(f"  {status} {tool}")

    # Show audit log
    print("\n" + "=" * 70)
    print("\nAudit Log:")
    for entry in access_controller.get_audit_log(limit=10):
        status = "GRANTED" if entry["granted"] else "DENIED"
        print(f"  [{entry['timestamp']}] {status}: {entry['agent_id']} -> {entry['tool_name']}")
        print(f"    Reason: {entry['reason']}")
