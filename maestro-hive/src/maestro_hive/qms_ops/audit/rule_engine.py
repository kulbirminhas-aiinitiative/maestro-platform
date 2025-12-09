"""
Rule Engine Module
==================

Provides configurable compliance rule evaluation capabilities.
Supports YAML-based rule definitions with Python-based evaluation.
"""

import re
import yaml
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union


class Severity(Enum):
    """Severity levels for compliance rules."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ConditionType(Enum):
    """Types of conditions for rule evaluation."""
    EXISTS = "exists"
    NOT_EXISTS = "not_exists"
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    MATCHES = "matches"  # regex
    DATE_WITHIN = "date_within"
    DATE_BEFORE = "date_before"
    DATE_AFTER = "date_after"
    IN_LIST = "in_list"
    NOT_IN_LIST = "not_in_list"
    CUSTOM = "custom"


@dataclass
class Condition:
    """A single condition in a rule."""
    type: ConditionType
    field: str
    value: Any = None
    options: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Action:
    """Action to take when a rule is violated."""
    type: str  # 'flag', 'notify', 'block', 'remediate'
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Rule:
    """Compliance rule definition."""
    id: str
    name: str
    description: str
    severity: Severity
    conditions: List[Condition]
    actions: List[Action] = field(default_factory=list)
    remediation: str = ""
    category: str = "general"
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RuleResult:
    """Result of evaluating a rule."""
    rule_id: str
    passed: bool
    message: str = ""
    evidence: Dict[str, Any] = field(default_factory=dict)
    conditions_evaluated: int = 0
    conditions_passed: int = 0


class RuleParser:
    """Parses rule definitions from YAML files."""

    def parse_file(self, path: Union[str, Path]) -> List[Rule]:
        """Parse rules from a YAML file."""
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
        return self.parse_data(data)

    def parse_data(self, data: Union[Dict, List]) -> List[Rule]:
        """Parse rules from dictionary/list data."""
        if isinstance(data, dict) and 'rules' in data:
            rules_data = data['rules']
        elif isinstance(data, list):
            rules_data = data
        elif isinstance(data, dict):
            rules_data = [data]
        else:
            raise ValueError("Invalid rule format")

        return [self._parse_rule(r) for r in rules_data]

    def _parse_rule(self, data: Dict) -> Rule:
        """Parse a single rule definition."""
        conditions = [
            self._parse_condition(c)
            for c in data.get('conditions', [])
        ]
        actions = [
            self._parse_action(a)
            for a in data.get('actions', [])
        ]

        return Rule(
            id=data['id'],
            name=data['name'],
            description=data.get('description', ''),
            severity=Severity(data.get('severity', 'medium').lower()),
            conditions=conditions,
            actions=actions,
            remediation=data.get('remediation', ''),
            category=data.get('category', 'general'),
            enabled=data.get('enabled', True),
            metadata=data.get('metadata', {})
        )

    def _parse_condition(self, data: Dict) -> Condition:
        """Parse a single condition."""
        return Condition(
            type=ConditionType(data['type']),
            field=data['field'],
            value=data.get('value'),
            options=data.get('options', {})
        )

    def _parse_action(self, data: Dict) -> Action:
        """Parse a single action."""
        return Action(
            type=data['type'],
            config=data.get('config', data)
        )


class ConditionEvaluator:
    """Evaluates individual conditions against data."""

    def __init__(self):
        self._evaluators: Dict[ConditionType, Callable] = {
            ConditionType.EXISTS: self._eval_exists,
            ConditionType.NOT_EXISTS: self._eval_not_exists,
            ConditionType.EQUALS: self._eval_equals,
            ConditionType.NOT_EQUALS: self._eval_not_equals,
            ConditionType.CONTAINS: self._eval_contains,
            ConditionType.NOT_CONTAINS: self._eval_not_contains,
            ConditionType.GREATER_THAN: self._eval_greater_than,
            ConditionType.LESS_THAN: self._eval_less_than,
            ConditionType.MATCHES: self._eval_matches,
            ConditionType.DATE_WITHIN: self._eval_date_within,
            ConditionType.DATE_BEFORE: self._eval_date_before,
            ConditionType.DATE_AFTER: self._eval_date_after,
            ConditionType.IN_LIST: self._eval_in_list,
            ConditionType.NOT_IN_LIST: self._eval_not_in_list,
        }

    def evaluate(self, condition: Condition, data: Dict[str, Any]) -> bool:
        """Evaluate a condition against data."""
        evaluator = self._evaluators.get(condition.type)
        if not evaluator:
            raise ValueError(f"Unknown condition type: {condition.type}")
        return evaluator(condition, data)

    def _get_field_value(self, data: Dict, field: str) -> Any:
        """Get nested field value using dot notation."""
        parts = field.split('.')
        value = data
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            elif isinstance(value, list) and part.isdigit():
                idx = int(part)
                value = value[idx] if idx < len(value) else None
            else:
                return None
            if value is None:
                return None
        return value

    def _eval_exists(self, cond: Condition, data: Dict) -> bool:
        value = self._get_field_value(data, cond.field)
        return value is not None and value != ""

    def _eval_not_exists(self, cond: Condition, data: Dict) -> bool:
        return not self._eval_exists(cond, data)

    def _eval_equals(self, cond: Condition, data: Dict) -> bool:
        value = self._get_field_value(data, cond.field)
        return value == cond.value

    def _eval_not_equals(self, cond: Condition, data: Dict) -> bool:
        return not self._eval_equals(cond, data)

    def _eval_contains(self, cond: Condition, data: Dict) -> bool:
        value = self._get_field_value(data, cond.field)
        if value is None:
            return False
        if isinstance(value, str):
            return str(cond.value) in value
        if isinstance(value, (list, tuple)):
            return cond.value in value
        return False

    def _eval_not_contains(self, cond: Condition, data: Dict) -> bool:
        return not self._eval_contains(cond, data)

    def _eval_greater_than(self, cond: Condition, data: Dict) -> bool:
        value = self._get_field_value(data, cond.field)
        if value is None:
            return False
        try:
            return float(value) > float(cond.value)
        except (ValueError, TypeError):
            return False

    def _eval_less_than(self, cond: Condition, data: Dict) -> bool:
        value = self._get_field_value(data, cond.field)
        if value is None:
            return False
        try:
            return float(value) < float(cond.value)
        except (ValueError, TypeError):
            return False

    def _eval_matches(self, cond: Condition, data: Dict) -> bool:
        value = self._get_field_value(data, cond.field)
        if value is None:
            return False
        try:
            pattern = re.compile(str(cond.value))
            return bool(pattern.search(str(value)))
        except re.error:
            return False

    def _eval_date_within(self, cond: Condition, data: Dict) -> bool:
        value = self._get_field_value(data, cond.field)
        if value is None:
            return False
        try:
            if isinstance(value, str):
                date_val = datetime.fromisoformat(value.replace('Z', '+00:00'))
            elif isinstance(value, datetime):
                date_val = value
            else:
                return False

            days = cond.options.get('days', cond.value)
            cutoff = datetime.now(date_val.tzinfo) - timedelta(days=int(days))
            return date_val >= cutoff
        except (ValueError, TypeError):
            return False

    def _eval_date_before(self, cond: Condition, data: Dict) -> bool:
        value = self._get_field_value(data, cond.field)
        if value is None:
            return False
        try:
            if isinstance(value, str):
                date_val = datetime.fromisoformat(value.replace('Z', '+00:00'))
            elif isinstance(value, datetime):
                date_val = value
            else:
                return False

            compare_date = datetime.fromisoformat(str(cond.value).replace('Z', '+00:00'))
            return date_val < compare_date
        except (ValueError, TypeError):
            return False

    def _eval_date_after(self, cond: Condition, data: Dict) -> bool:
        value = self._get_field_value(data, cond.field)
        if value is None:
            return False
        try:
            if isinstance(value, str):
                date_val = datetime.fromisoformat(value.replace('Z', '+00:00'))
            elif isinstance(value, datetime):
                date_val = value
            else:
                return False

            compare_date = datetime.fromisoformat(str(cond.value).replace('Z', '+00:00'))
            return date_val > compare_date
        except (ValueError, TypeError):
            return False

    def _eval_in_list(self, cond: Condition, data: Dict) -> bool:
        value = self._get_field_value(data, cond.field)
        if value is None:
            return False
        allowed = cond.value if isinstance(cond.value, list) else [cond.value]
        return value in allowed

    def _eval_not_in_list(self, cond: Condition, data: Dict) -> bool:
        return not self._eval_in_list(cond, data)


class RuleEngine:
    """
    Main rule engine for compliance evaluation.

    Manages rules and evaluates them against target data.
    """

    def __init__(self, rules_path: Optional[Union[str, Path]] = None):
        self.rules: Dict[str, Rule] = {}
        self.parser = RuleParser()
        self.evaluator = ConditionEvaluator()

        if rules_path:
            self.load_rules(rules_path)

    def load_rules(self, path: Union[str, Path]) -> int:
        """Load rules from a file or directory."""
        path = Path(path)
        count = 0

        if path.is_file():
            for rule in self.parser.parse_file(path):
                self.add_rule(rule)
                count += 1
        elif path.is_dir():
            for file_path in path.glob('*.yaml'):
                for rule in self.parser.parse_file(file_path):
                    self.add_rule(rule)
                    count += 1
            for file_path in path.glob('*.yml'):
                for rule in self.parser.parse_file(file_path):
                    self.add_rule(rule)
                    count += 1

        return count

    def add_rule(self, rule: Rule) -> None:
        """Add a rule to the engine."""
        self.rules[rule.id] = rule

    def remove_rule(self, rule_id: str) -> bool:
        """Remove a rule from the engine."""
        if rule_id in self.rules:
            del self.rules[rule_id]
            return True
        return False

    def get_rules(
        self,
        rule_ids: Optional[List[str]] = None,
        category: Optional[str] = None,
        severity: Optional[Severity] = None,
        enabled_only: bool = True
    ) -> List[Rule]:
        """Get rules matching the specified criteria."""
        rules = list(self.rules.values())

        if rule_ids:
            rules = [r for r in rules if r.id in rule_ids]

        if category:
            rules = [r for r in rules if r.category == category]

        if severity:
            rules = [r for r in rules if r.severity == severity]

        if enabled_only:
            rules = [r for r in rules if r.enabled]

        return rules

    def evaluate(self, rule: Rule, data: Dict[str, Any]) -> RuleResult:
        """Evaluate a single rule against data."""
        conditions_passed = 0
        failed_conditions = []

        for condition in rule.conditions:
            try:
                if self.evaluator.evaluate(condition, data):
                    conditions_passed += 1
                else:
                    failed_conditions.append({
                        "field": condition.field,
                        "type": condition.type.value,
                        "expected": condition.value,
                        "actual": self._get_field_value(data, condition.field)
                    })
            except Exception as e:
                failed_conditions.append({
                    "field": condition.field,
                    "type": condition.type.value,
                    "error": str(e)
                })

        passed = len(failed_conditions) == 0

        return RuleResult(
            rule_id=rule.id,
            passed=passed,
            message="" if passed else f"Rule '{rule.name}' violated: {len(failed_conditions)} condition(s) failed",
            evidence={
                "failed_conditions": failed_conditions,
                "data_sample": {k: v for k, v in list(data.items())[:5]}
            } if not passed else {},
            conditions_evaluated=len(rule.conditions),
            conditions_passed=conditions_passed
        )

    def evaluate_all(
        self,
        data: Dict[str, Any],
        rule_ids: Optional[List[str]] = None
    ) -> List[RuleResult]:
        """Evaluate all matching rules against data."""
        rules = self.get_rules(rule_ids)
        return [self.evaluate(rule, data) for rule in rules]

    def _get_field_value(self, data: Dict, field: str) -> Any:
        """Get nested field value using dot notation."""
        return self.evaluator._get_field_value(data, field)
