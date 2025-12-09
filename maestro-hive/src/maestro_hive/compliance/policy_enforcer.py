#!/usr/bin/env python3
"""
Policy Enforcer: OPA-inspired policy engine for compliance.

Defines and enforces policies using a YAML-based DSL.
Supports allow/deny rules with conditions and exceptions.

SOC2 CC5.2: Access policy enforcement.
GDPR Article 25: Data protection by design.
"""

import json
import re
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable, Union
import fnmatch

logger = logging.getLogger(__name__)


class PolicyDecision(Enum):
    """Policy evaluation result."""
    ALLOW = "allow"
    DENY = "deny"
    WARN = "warn"
    REQUIRE_APPROVAL = "require_approval"


class PolicyEffect(Enum):
    """Policy effect type."""
    ALLOW = "allow"
    DENY = "deny"


@dataclass
class PolicyCondition:
    """A condition in a policy rule."""
    field: str
    operator: str  # eq, neq, in, not_in, contains, gt, lt, gte, lte, matches
    value: Any
    case_sensitive: bool = True

    def evaluate(self, context: Dict[str, Any]) -> bool:
        """Evaluate condition against context."""
        # Get field value using dot notation
        actual = self._get_nested_value(context, self.field)

        if actual is None:
            return self.operator in ('neq', 'not_in')

        # Apply case insensitivity if needed
        if not self.case_sensitive and isinstance(actual, str):
            actual = actual.lower()
            if isinstance(self.value, str):
                compare_value = self.value.lower()
            elif isinstance(self.value, list):
                compare_value = [v.lower() if isinstance(v, str) else v for v in self.value]
            else:
                compare_value = self.value
        else:
            compare_value = self.value

        # Evaluate based on operator
        if self.operator == 'eq':
            return actual == compare_value
        elif self.operator == 'neq':
            return actual != compare_value
        elif self.operator == 'in':
            return actual in compare_value
        elif self.operator == 'not_in':
            return actual not in compare_value
        elif self.operator == 'contains':
            if isinstance(actual, (list, str)):
                return compare_value in actual
            return False
        elif self.operator == 'gt':
            return actual > compare_value
        elif self.operator == 'lt':
            return actual < compare_value
        elif self.operator == 'gte':
            return actual >= compare_value
        elif self.operator == 'lte':
            return actual <= compare_value
        elif self.operator == 'matches':
            if isinstance(actual, str):
                return bool(re.match(compare_value, actual))
            return False
        elif self.operator == 'glob':
            if isinstance(actual, str):
                return fnmatch.fnmatch(actual, compare_value)
            return False
        elif self.operator == 'exists':
            return actual is not None
        elif self.operator == 'not_exists':
            return actual is None

        return False

    def _get_nested_value(self, data: Dict, path: str) -> Any:
        """Get nested value using dot notation."""
        keys = path.split('.')
        value = data
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            elif isinstance(value, list) and key.isdigit():
                idx = int(key)
                value = value[idx] if idx < len(value) else None
            else:
                return None
        return value


@dataclass
class PolicyRule:
    """A policy rule."""
    id: str
    name: str
    description: str
    effect: PolicyEffect
    resources: List[str]  # Resource patterns (glob)
    actions: List[str]    # Action patterns
    conditions: List[PolicyCondition] = field(default_factory=list)
    priority: int = 0
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def matches(self, resource: str, action: str, context: Dict[str, Any]) -> bool:
        """Check if rule matches the request."""
        if not self.enabled:
            return False

        # Check resource pattern
        resource_match = any(
            fnmatch.fnmatch(resource, pattern) for pattern in self.resources
        )
        if not resource_match:
            return False

        # Check action pattern
        action_match = any(
            fnmatch.fnmatch(action, pattern) for pattern in self.actions
        )
        if not action_match:
            return False

        # Check all conditions
        for condition in self.conditions:
            if not condition.evaluate(context):
                return False

        return True

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['effect'] = self.effect.value
        return data


@dataclass
class Policy:
    """A complete policy document."""
    id: str
    name: str
    description: str
    version: str
    rules: List[PolicyRule]
    default_effect: PolicyEffect = PolicyEffect.DENY
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['default_effect'] = self.default_effect.value
        data['rules'] = [r.to_dict() for r in self.rules]
        return data


@dataclass
class PolicyEvaluation:
    """Result of policy evaluation."""
    decision: PolicyDecision
    matched_rules: List[str]
    reason: str
    resource: str
    action: str
    principal: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['decision'] = self.decision.value
        return data


class PolicyEnforcer:
    """
    Policy enforcement engine.

    Features:
    - YAML-based policy definition
    - Allow/deny with conditions
    - Priority-based rule evaluation
    - Audit logging of decisions
    """

    def __init__(
        self,
        policy_dir: Optional[str] = None,
        audit_callback: Optional[Callable[[PolicyEvaluation], None]] = None
    ):
        """
        Initialize policy enforcer.

        Args:
            policy_dir: Directory containing policy files
            audit_callback: Callback for audit logging
        """
        self.policy_dir = Path(policy_dir) if policy_dir else \
            Path.home() / '.maestro' / 'policies'
        self.policy_dir.mkdir(parents=True, exist_ok=True)

        self.audit_callback = audit_callback
        self._policies: Dict[str, Policy] = {}
        self._load_policies()

        logger.info(f"PolicyEnforcer initialized with {len(self._policies)} policies")

    def check(
        self,
        resource: str,
        action: str,
        context: Optional[Dict[str, Any]] = None,
        principal: Optional[str] = None
    ) -> PolicyEvaluation:
        """
        Check if an action on a resource is allowed.

        Args:
            resource: Resource identifier (e.g., "project/maestro/code")
            action: Action being performed (e.g., "read", "write", "delete")
            context: Additional context for evaluation
            principal: Who is performing the action

        Returns:
            PolicyEvaluation with decision
        """
        context = context or {}
        context['principal'] = principal
        context['resource'] = resource
        context['action'] = action
        context['timestamp'] = datetime.utcnow().isoformat()

        matched_rules = []
        allow_matched = False
        deny_matched = False
        require_approval = False

        # Sort all rules by priority (higher first)
        all_rules = []
        for policy in self._policies.values():
            all_rules.extend(policy.rules)
        all_rules.sort(key=lambda r: r.priority, reverse=True)

        # Evaluate rules
        for rule in all_rules:
            if rule.matches(resource, action, context):
                matched_rules.append(rule.id)

                if rule.effect == PolicyEffect.DENY:
                    deny_matched = True
                    break  # Deny takes precedence
                elif rule.effect == PolicyEffect.ALLOW:
                    allow_matched = True

                # Check for approval requirement in metadata
                if rule.metadata.get('require_approval'):
                    require_approval = True

        # Determine final decision
        if deny_matched:
            decision = PolicyDecision.DENY
            reason = f"Denied by rule(s): {', '.join(matched_rules)}"
        elif require_approval:
            decision = PolicyDecision.REQUIRE_APPROVAL
            reason = f"Requires approval per rule(s): {', '.join(matched_rules)}"
        elif allow_matched:
            decision = PolicyDecision.ALLOW
            reason = f"Allowed by rule(s): {', '.join(matched_rules)}"
        else:
            # Default deny
            decision = PolicyDecision.DENY
            reason = "No matching allow rule found"

        evaluation = PolicyEvaluation(
            decision=decision,
            matched_rules=matched_rules,
            reason=reason,
            resource=resource,
            action=action,
            principal=principal,
            context=context
        )

        # Audit logging
        if self.audit_callback:
            self.audit_callback(evaluation)

        logger.debug(f"Policy check: {resource}/{action} -> {decision.value}")

        return evaluation

    def enforce(
        self,
        resource: str,
        action: str,
        context: Optional[Dict[str, Any]] = None,
        principal: Optional[str] = None
    ) -> bool:
        """
        Enforce policy (raises exception if denied).

        Args:
            resource: Resource identifier
            action: Action
            context: Context
            principal: Principal

        Returns:
            True if allowed

        Raises:
            PermissionError: If denied
        """
        result = self.check(resource, action, context, principal)

        if result.decision == PolicyDecision.DENY:
            raise PermissionError(f"Policy denied: {result.reason}")
        elif result.decision == PolicyDecision.REQUIRE_APPROVAL:
            raise PermissionError(f"Approval required: {result.reason}")

        return True

    def add_policy(self, policy: Policy) -> None:
        """Add or update a policy."""
        self._policies[policy.id] = policy
        self._save_policy(policy)

    def remove_policy(self, policy_id: str) -> bool:
        """Remove a policy."""
        if policy_id in self._policies:
            del self._policies[policy_id]
            file_path = self.policy_dir / f"{policy_id}.json"
            if file_path.exists():
                file_path.unlink()
            return True
        return False

    def get_policy(self, policy_id: str) -> Optional[Policy]:
        """Get a policy by ID."""
        return self._policies.get(policy_id)

    def list_policies(self) -> List[Policy]:
        """List all policies."""
        return list(self._policies.values())

    def create_policy_from_yaml(self, yaml_content: str) -> Policy:
        """
        Create a policy from YAML definition.

        Example YAML:
        ```yaml
        id: data-access-policy
        name: Data Access Policy
        description: Controls access to sensitive data
        version: "1.0"
        default_effect: deny
        rules:
          - id: allow-read-public
            name: Allow Public Read
            effect: allow
            resources: ["project/*/public/*"]
            actions: ["read"]

          - id: deny-delete-production
            name: Deny Production Delete
            effect: deny
            resources: ["project/*/production/*"]
            actions: ["delete"]
            conditions:
              - field: user.role
                operator: neq
                value: admin
        ```
        """
        import yaml
        data = yaml.safe_load(yaml_content)

        rules = []
        for rule_data in data.get('rules', []):
            conditions = []
            for cond in rule_data.get('conditions', []):
                conditions.append(PolicyCondition(
                    field=cond['field'],
                    operator=cond['operator'],
                    value=cond['value'],
                    case_sensitive=cond.get('case_sensitive', True)
                ))

            rules.append(PolicyRule(
                id=rule_data['id'],
                name=rule_data['name'],
                description=rule_data.get('description', ''),
                effect=PolicyEffect(rule_data['effect']),
                resources=rule_data['resources'],
                actions=rule_data['actions'],
                conditions=conditions,
                priority=rule_data.get('priority', 0),
                enabled=rule_data.get('enabled', True),
                metadata=rule_data.get('metadata', {})
            ))

        policy = Policy(
            id=data['id'],
            name=data['name'],
            description=data.get('description', ''),
            version=data.get('version', '1.0'),
            rules=rules,
            default_effect=PolicyEffect(data.get('default_effect', 'deny')),
            metadata=data.get('metadata', {})
        )

        self.add_policy(policy)
        return policy

    def _load_policies(self) -> None:
        """Load policies from storage."""
        # Load JSON policies
        for file_path in self.policy_dir.glob("*.json"):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    policy = self._dict_to_policy(data)
                    self._policies[policy.id] = policy
            except Exception as e:
                logger.error(f"Error loading {file_path}: {e}")

        # Load YAML policies
        for ext in ['*.yaml', '*.yml']:
            for file_path in self.policy_dir.glob(ext):
                try:
                    with open(file_path, 'r') as f:
                        self.create_policy_from_yaml(f.read())
                except Exception as e:
                    logger.error(f"Error loading {file_path}: {e}")

    def _save_policy(self, policy: Policy) -> None:
        """Save policy to storage."""
        file_path = self.policy_dir / f"{policy.id}.json"
        with open(file_path, 'w') as f:
            json.dump(policy.to_dict(), f, indent=2)

    def _dict_to_policy(self, data: Dict[str, Any]) -> Policy:
        """Convert dictionary to Policy."""
        rules = []
        for rule_data in data.get('rules', []):
            conditions = [
                PolicyCondition(**c) for c in rule_data.get('conditions', [])
            ]
            rules.append(PolicyRule(
                id=rule_data['id'],
                name=rule_data['name'],
                description=rule_data.get('description', ''),
                effect=PolicyEffect(rule_data['effect']),
                resources=rule_data['resources'],
                actions=rule_data['actions'],
                conditions=conditions,
                priority=rule_data.get('priority', 0),
                enabled=rule_data.get('enabled', True),
                metadata=rule_data.get('metadata', {})
            ))

        return Policy(
            id=data['id'],
            name=data['name'],
            description=data.get('description', ''),
            version=data.get('version', '1.0'),
            rules=rules,
            default_effect=PolicyEffect(data.get('default_effect', 'deny')),
            created_at=data.get('created_at', datetime.utcnow().isoformat()),
            updated_at=data.get('updated_at'),
            metadata=data.get('metadata', {})
        )


def get_policy_enforcer(**kwargs) -> PolicyEnforcer:
    """Get policy enforcer instance."""
    return PolicyEnforcer(**kwargs)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    enforcer = PolicyEnforcer()

    # Create a test policy
    policy_yaml = """
id: test-policy
name: Test Policy
description: A test policy for demonstration
version: "1.0"
default_effect: deny
rules:
  - id: allow-read
    name: Allow Read
    effect: allow
    resources: ["project/*"]
    actions: ["read"]

  - id: deny-delete
    name: Deny Delete
    effect: deny
    resources: ["project/*"]
    actions: ["delete"]
"""

    policy = enforcer.create_policy_from_yaml(policy_yaml)
    print(f"Created policy: {policy.id}")

    # Test evaluations
    result = enforcer.check("project/maestro", "read")
    print(f"Read: {result.decision.value} - {result.reason}")

    result = enforcer.check("project/maestro", "delete")
    print(f"Delete: {result.decision.value} - {result.reason}")
