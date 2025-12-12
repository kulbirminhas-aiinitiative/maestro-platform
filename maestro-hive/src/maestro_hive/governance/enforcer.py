"""
The Enforcer Middleware (MD-3116 / MD-3201)

Synchronous policy enforcement that blocks illegal actions in real-time (<10ms).

Acceptance Criteria Implementation:
- AC-1: Immutable Protection - Attempting to edit .env returns PermissionError
- AC-2: Role Restriction - A developer_agent attempting deploy_prod is blocked
- AC-3: Budget Check - An agent with $0.00 remaining budget is blocked
- AC-4: Performance - Overhead per call is < 10ms
- AC-5: Fail-Safe - If the policy file is corrupted, ALL actions are blocked

The Enforcer is the "Bouncer" of the system - it intercepts all tool calls
and checks policy.yaml for violations before allowing execution.
"""

from __future__ import annotations

import fnmatch
import logging
import time
import yaml
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from threading import Lock
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class PolicyLoadError(Exception):
    """Raised when policy configuration is invalid or missing."""
    pass


class PermissionDeniedError(Exception):
    """Raised when action violates role or path restrictions."""
    def __init__(self, message: str, violation_type: str = "permission_denied"):
        super().__init__(message)
        self.violation_type = violation_type


class BudgetExceededError(Exception):
    """Raised when agent has insufficient budget."""
    def __init__(self, agent_id: str, remaining: float, required: float = 0.0):
        super().__init__(f"Agent '{agent_id}' has insufficient budget: ${remaining:.2f} remaining")
        self.agent_id = agent_id
        self.remaining = remaining
        self.required = required


class ConcurrencyError(Exception):
    """Raised when resource is locked by another agent."""
    def __init__(self, path: str, lock_holder: str):
        super().__init__(f"Resource '{path}' is locked by agent '{lock_holder}'")
        self.path = path
        self.lock_holder = lock_holder


class ViolationType(Enum):
    """Types of policy violations."""

    FORBIDDEN_TOOL = "forbidden_tool"
    IMMUTABLE_PATH = "immutable_path"
    PROTECTED_PATH = "protected_path"
    INSUFFICIENT_ROLE = "insufficient_role"
    BUDGET_EXCEEDED = "budget_exceeded"
    RECURSION_LIMIT = "recursion_limit"
    CONCURRENT_LIMIT = "concurrent_limit"
    HUMAN_APPROVAL_REQUIRED = "human_approval_required"
    FILE_LOCKED = "file_locked"


@dataclass
class EnforcerResult:
    """
    Result of an enforcement check.

    Attributes:
        allowed: Whether the action is allowed
        violation_type: Type of violation if blocked
        message: Human-readable explanation
        latency_ms: Time taken to check in milliseconds
        policy_version: Version of policy used
    """

    allowed: bool
    violation_type: Optional[ViolationType] = None
    message: str = ""
    latency_ms: float = 0.0
    policy_version: str = "2.0.0"
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "allowed": self.allowed,
            "violation_type": self.violation_type.value if self.violation_type else None,
            "message": self.message,
            "latency_ms": self.latency_ms,
            "policy_version": self.policy_version,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class AgentContext:
    """Context about the requesting agent."""

    agent_id: str
    role: str = "developer_agent"
    reputation: int = 50
    current_tokens: int = 0
    recursion_depth: int = 0
    budget_remaining: float = 100.0  # AC-3: Budget in dollars


@dataclass
class EnforcementResult:
    """Alias for EnforcerResult for API compatibility."""
    allowed: bool
    reason: str = ""
    checks_passed: List[str] = field(default_factory=list)
    latency_ms: float = 0.0


@dataclass
class AgentAction:
    """
    Represents an agent's tool call request.

    This is the primary input to the EnforcerMiddleware.
    """
    tool_name: str      # e.g., "write_file", "run_terminal", "deploy_prod"
    args: Dict[str, Any] = field(default_factory=dict)  # Tool arguments
    agent_id: str = "anonymous"  # Agent identifier
    timestamp: datetime = field(default_factory=datetime.utcnow)


class Enforcer:
    """
    The Enforcer Middleware - Synchronous Policy Enforcement.

    MD-3201: Intercepts all tool calls and checks policy.yaml for:
    - forbidden_tools per role
    - immutable_paths
    - protected_paths (require elevated role)
    - concurrency_control (file locking)

    AC-1: Blocks agents from deleting .env immediately (403 Forbidden).
    """

    def __init__(self, policy_path: Optional[str] = None):
        """
        Initialize the Enforcer.

        Args:
            policy_path: Path to policy.yaml file

        AC-5: If policy is corrupted/missing, fail-safe mode blocks ALL actions.
        """
        self._policy: Dict[str, Any] = {}
        self._policy_version = "2.0.0"
        self._lock = Lock()
        self._file_locker: Optional[Any] = None  # Injected later
        self._audit_logger: Optional[Any] = None  # Injected later
        self._on_violation: List[Callable[[EnforcerResult, AgentContext, str, str], None]] = []
        self._policy_corrupted = False  # AC-5: Fail-safe flag
        self._budget_tracker: Dict[str, float] = {}  # AC-3: Budget tracking

        # Load policy
        if policy_path:
            try:
                self.load_policy(policy_path)
            except PolicyLoadError:
                self._policy_corrupted = True
                logger.warning("Enforcer in FAIL-SAFE mode: All actions blocked")
        else:
            default_path = Path(__file__).parent.parent.parent.parent / "config" / "governance" / "policy.yaml"
            if default_path.exists():
                try:
                    self.load_policy(str(default_path))
                except PolicyLoadError:
                    self._policy_corrupted = True
                    logger.warning("Enforcer in FAIL-SAFE mode: All actions blocked")

        logger.info(f"Enforcer initialized with policy v{self._policy_version}")

    def load_policy(self, path: str) -> None:
        """
        Load policy from YAML file.

        AC-5: If the policy file is corrupted, ALL actions are blocked.
        """
        self._policy_corrupted = False
        try:
            with open(path, "r") as f:
                content = f.read()
                if not content.strip():
                    raise PolicyLoadError("Policy file is empty")
                self._policy = yaml.safe_load(content)
                if self._policy is None:
                    raise PolicyLoadError("Policy file parsed to None")
                # Validate required keys
                if not isinstance(self._policy, dict):
                    raise PolicyLoadError("Policy must be a YAML dictionary")
            logger.info(f"Loaded policy from {path}")
        except yaml.YAMLError as e:
            logger.error(f"Policy file corrupted (invalid YAML): {e}")
            self._policy_corrupted = True
            self._policy = {}
            raise PolicyLoadError(f"Policy file corrupted: {e}")
        except FileNotFoundError:
            logger.error(f"Policy file not found: {path}")
            self._policy_corrupted = True
            self._policy = {}
            raise PolicyLoadError(f"Policy file not found: {path}")
        except Exception as e:
            logger.error(f"Failed to load policy: {e}")
            self._policy_corrupted = True
            self._policy = {}
            raise PolicyLoadError(f"Failed to load policy: {e}")

    def set_file_locker(self, locker: Any) -> None:
        """Inject file locker dependency."""
        self._file_locker = locker

    def set_audit_logger(self, logger: Any) -> None:
        """Inject audit logger dependency."""
        self._audit_logger = logger

    def on_violation(self, callback: Callable[[EnforcerResult, AgentContext, str, str], None]) -> None:
        """Register callback for violations."""
        self._on_violation.append(callback)

    def check(
        self,
        agent: AgentContext,
        tool_name: str,
        target_path: Optional[str] = None,
        action: str = "execute",
    ) -> EnforcerResult:
        """
        Check if an action is allowed by policy.

        AC-1: Blocks .env deletion immediately.
        AC-2: Blocks developer_agent from deploy_prod.
        AC-3: Blocks agents with $0.00 budget.
        AC-4: Must complete in < 10ms.
        AC-5: If policy corrupted, ALL actions blocked (fail-safe).

        Args:
            agent: Context about the requesting agent
            tool_name: Name of the tool being called
            target_path: Optional file/resource path being accessed
            action: Action type (read, write, delete, execute)

        Returns:
            EnforcerResult with allowed status and violation details
        """
        start_time = time.perf_counter()

        try:
            # AC-5: FAIL-SAFE - If policy is corrupted, block ALL actions
            if self._policy_corrupted:
                result = EnforcerResult(
                    allowed=False,
                    violation_type=None,
                    message="FAIL-SAFE: Policy file corrupted - ALL actions blocked",
                )
                return self._finalize_result(result, start_time, agent, tool_name, target_path)

            # AC-3: Budget Check - Block agents with $0.00 budget
            result = self._check_budget(agent)
            if not result.allowed:
                return self._finalize_result(result, start_time, agent, tool_name, target_path)

            # Check 1: Global constraints
            result = self._check_global_constraints(agent, tool_name)
            if not result.allowed:
                return self._finalize_result(result, start_time, agent, tool_name, target_path)

            # Check 2: Role-based tool permissions (AC-2 implementation)
            result = self._check_tool_permissions(agent, tool_name)
            if not result.allowed:
                return self._finalize_result(result, start_time, agent, tool_name, target_path)

            # Check 3: File path protections (AC-1 implementation)
            if target_path:
                result = self._check_path_protection(agent, target_path, action)
                if not result.allowed:
                    return self._finalize_result(result, start_time, agent, tool_name, target_path)

                # Check 4: File locking
                if action in ("write", "delete", "edit") and self._file_locker:
                    result = self._check_file_lock(agent, target_path)
                    if not result.allowed:
                        return self._finalize_result(result, start_time, agent, tool_name, target_path)

            # All checks passed
            result = EnforcerResult(allowed=True, message="Action permitted")
            return self._finalize_result(result, start_time, agent, tool_name, target_path)

        except Exception as e:
            logger.error(f"Enforcer check error: {e}")
            # Fail-closed for unexpected errors (security-first)
            result = EnforcerResult(
                allowed=False,
                violation_type=None,
                message=f"Enforcement check error: {str(e)}",
            )
            return self._finalize_result(result, start_time, agent, tool_name, target_path)

    def _check_budget(self, agent: AgentContext) -> EnforcerResult:
        """
        Check if agent has sufficient budget.

        AC-3: An agent with $0.00 remaining budget is blocked.
        """
        if agent.budget_remaining <= 0:
            return EnforcerResult(
                allowed=False,
                violation_type=ViolationType.BUDGET_EXCEEDED,
                message=f"Agent '{agent.agent_id}' has no remaining budget (${agent.budget_remaining:.2f})",
            )
        return EnforcerResult(allowed=True)

    def _check_global_constraints(self, agent: AgentContext, tool_name: str) -> EnforcerResult:
        """Check global constraints from policy."""
        global_constraints = self._policy.get("global_constraints", {})

        # Check recursion depth
        max_recursion = global_constraints.get("max_recursion_depth", 5)
        if agent.recursion_depth > max_recursion:
            return EnforcerResult(
                allowed=False,
                violation_type=ViolationType.RECURSION_LIMIT,
                message=f"Recursion depth {agent.recursion_depth} exceeds limit {max_recursion}",
            )

        # Check if tool requires human approval
        require_human = global_constraints.get("require_human_approval_for", [])
        if tool_name in require_human:
            return EnforcerResult(
                allowed=False,
                violation_type=ViolationType.HUMAN_APPROVAL_REQUIRED,
                message=f"Tool '{tool_name}' requires human approval",
            )

        return EnforcerResult(allowed=True)

    def _check_tool_permissions(self, agent: AgentContext, tool_name: str) -> EnforcerResult:
        """Check role-based tool permissions."""
        roles = self._policy.get("roles", {})
        role_config = roles.get(agent.role, {})

        # Check forbidden tools first
        forbidden_tools = role_config.get("forbidden_tools", [])
        if tool_name in forbidden_tools:
            return EnforcerResult(
                allowed=False,
                violation_type=ViolationType.FORBIDDEN_TOOL,
                message=f"Tool '{tool_name}' is forbidden for role '{agent.role}'",
            )

        # Check allowed tools (if explicitly specified)
        allowed_tools = role_config.get("allowed_tools", [])
        if allowed_tools and allowed_tools != ["*"]:
            if tool_name not in allowed_tools:
                return EnforcerResult(
                    allowed=False,
                    violation_type=ViolationType.INSUFFICIENT_ROLE,
                    message=f"Tool '{tool_name}' not in allowed list for role '{agent.role}'",
                )

        return EnforcerResult(allowed=True)

    def _check_path_protection(
        self,
        agent: AgentContext,
        target_path: str,
        action: str,
    ) -> EnforcerResult:
        """
        Check file path protections.

        AC-1: Blocks .env deletion/modification immediately.
        """
        file_protection = self._policy.get("file_protection", {})

        # Check immutable paths - NEVER allowed regardless of role
        immutable_paths = file_protection.get("immutable_paths", [])
        for pattern in immutable_paths:
            if self._path_matches(target_path, pattern):
                return EnforcerResult(
                    allowed=False,
                    violation_type=ViolationType.IMMUTABLE_PATH,
                    message=f"Path '{target_path}' matches immutable pattern '{pattern}' - action blocked",
                )

        # Check protected paths - require elevated role
        if action in ("write", "delete", "edit"):
            protected_paths = file_protection.get("protected_paths", [])
            for pattern in protected_paths:
                if self._path_matches(target_path, pattern):
                    # Only architect+ can modify protected paths
                    if agent.role not in ("architect_agent", "governance_agent"):
                        return EnforcerResult(
                            allowed=False,
                            violation_type=ViolationType.PROTECTED_PATH,
                            message=f"Path '{target_path}' is protected - requires architect or governance role",
                        )

        return EnforcerResult(allowed=True)

    def _check_file_lock(self, agent: AgentContext, target_path: str) -> EnforcerResult:
        """Check if file is locked by another agent."""
        if self._file_locker is None:
            return EnforcerResult(allowed=True)

        lock_holder = self._file_locker.get_lock_holder(target_path)
        if lock_holder and lock_holder != agent.agent_id:
            return EnforcerResult(
                allowed=False,
                violation_type=ViolationType.FILE_LOCKED,
                message=f"Path '{target_path}' is locked by agent '{lock_holder}'",
            )

        return EnforcerResult(allowed=True)

    def _path_matches(self, path: str, pattern: str) -> bool:
        """Check if path matches a glob pattern."""
        # Normalize paths
        path = path.replace("\\", "/")
        pattern = pattern.replace("\\", "/")

        # Handle patterns like ".env" matching any path ending in .env
        if pattern.startswith("."):
            if path.endswith(pattern) or f"/{pattern}" in path:
                return True

        # Standard glob matching
        return fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(path, f"**/{pattern}")

    def _finalize_result(
        self,
        result: EnforcerResult,
        start_time: float,
        agent: AgentContext,
        tool_name: str,
        target_path: Optional[str],
    ) -> EnforcerResult:
        """Finalize result with timing and logging."""
        result.latency_ms = (time.perf_counter() - start_time) * 1000
        result.policy_version = self._policy_version

        # Log to audit logger if available
        if self._audit_logger:
            self._audit_logger.log(
                agent_id=agent.agent_id,
                action=tool_name,
                target=target_path or "",
                result=result,
            )

        # Call violation callbacks
        if not result.allowed:
            for callback in self._on_violation:
                try:
                    callback(result, agent, tool_name, target_path or "")
                except Exception as e:
                    logger.error(f"Violation callback error: {e}")

        return result

    def block_env_deletion(self, agent: AgentContext, path: str) -> EnforcerResult:
        """
        Convenience method for AC-1 validation.

        Returns 403 Forbidden for any attempt to delete .env files.
        """
        if ".env" in path or path.endswith(".env"):
            return EnforcerResult(
                allowed=False,
                violation_type=ViolationType.IMMUTABLE_PATH,
                message="403 Forbidden: .env files are protected by governance policy",
            )
        return EnforcerResult(allowed=True)

    def get_role_permissions(self, role: str) -> Dict[str, Any]:
        """Get permissions for a role."""
        return self._policy.get("roles", {}).get(role, {})

    def get_immutable_paths(self) -> List[str]:
        """Get list of immutable path patterns."""
        return self._policy.get("file_protection", {}).get("immutable_paths", [])

    def get_protected_paths(self) -> List[str]:
        """Get list of protected path patterns."""
        return self._policy.get("file_protection", {}).get("protected_paths", [])

    @property
    def is_fail_safe(self) -> bool:
        """Check if enforcer is in fail-safe mode (AC-5)."""
        return self._policy_corrupted

    def set_budget(self, agent_id: str, budget: float) -> None:
        """Set budget for an agent."""
        self._budget_tracker[agent_id] = budget

    def get_budget(self, agent_id: str) -> float:
        """Get remaining budget for an agent."""
        return self._budget_tracker.get(agent_id, 100.0)


# Alias for API compatibility
EnforcerMiddleware = Enforcer
