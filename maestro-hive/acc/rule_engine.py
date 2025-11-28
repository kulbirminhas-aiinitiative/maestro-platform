"""
ACC Rule Engine

Core architectural rule evaluation engine for ACC.
Supports multiple rule types with configurable severity levels.

Rule Types:
- CAN_CALL(Target): Allows calling target, disallows all others
- MUST_NOT_CALL(Target): Forbids calling target, allows all others
- COUPLING < N: Enforces coupling threshold
- NO_CYCLES: Detects cyclic dependencies

Severity Levels:
- INFO: Informational only
- WARNING: Should be fixed, but doesn't block
- BLOCKING: Must be fixed before deployment

Author: Claude Code Implementation
Date: 2025-10-13
Version: 1.0.0
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
import re
import yaml
import logging
from datetime import datetime


logger = logging.getLogger(__name__)


# ============================================================================
# Enumerations
# ============================================================================

class RuleType(str, Enum):
    """Types of architectural rules."""
    CAN_CALL = "CAN_CALL"
    MUST_NOT_CALL = "MUST_NOT_CALL"
    COUPLING = "COUPLING"
    NO_CYCLES = "NO_CYCLES"


class Severity(str, Enum):
    """Rule severity levels."""
    INFO = "info"
    WARNING = "warning"
    BLOCKING = "blocking"


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class Violation:
    """Represents a single architectural rule violation."""
    rule_id: str
    rule_type: RuleType
    severity: Severity
    source_component: str
    target_component: Optional[str]
    message: str
    source_file: Optional[str] = None
    target_file: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert violation to dictionary."""
        return {
            'rule_id': self.rule_id,
            'rule_type': self.rule_type.value,
            'severity': self.severity.value,
            'source_component': self.source_component,
            'target_component': self.target_component,
            'message': self.message,
            'source_file': self.source_file,
            'target_file': self.target_file,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class Rule:
    """Architectural rule definition."""
    id: str
    rule_type: RuleType
    severity: Severity
    description: str
    component: str  # Component this rule applies to
    target: Optional[str] = None  # Target component (for CAN_CALL, MUST_NOT_CALL)
    threshold: Optional[int] = None  # Threshold value (for COUPLING)
    enabled: bool = True
    exemptions: List[str] = field(default_factory=list)  # Exempted files/components
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional metadata
    version: str = "1.0.0"

    def applies_to(self, component: str, file_path: Optional[str] = None) -> bool:
        """Check if rule applies to given component/file."""
        if not self.enabled:
            return False

        # Check component match
        if component != self.component:
            return False

        # Check exemptions
        if file_path:
            for exemption in self.exemptions:
                if exemption in file_path:
                    return False

        return True

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Rule':
        """Create Rule from dictionary."""
        return cls(
            id=data['id'],
            rule_type=RuleType(data['rule_type']),
            severity=Severity(data['severity']),
            description=data['description'],
            component=data['component'],
            target=data.get('target'),
            threshold=data.get('threshold'),
            enabled=data.get('enabled', True),
            exemptions=data.get('exemptions', []),
            metadata=data.get('metadata', {}),
            version=data.get('version', '1.0.0')
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert Rule to dictionary."""
        return {
            'id': self.id,
            'rule_type': self.rule_type.value,
            'severity': self.severity.value,
            'description': self.description,
            'component': self.component,
            'target': self.target,
            'threshold': self.threshold,
            'enabled': self.enabled,
            'exemptions': self.exemptions,
            'metadata': self.metadata,
            'version': self.version
        }


@dataclass
class Component:
    """Logical architectural component."""
    name: str
    paths: List[str]  # File path patterns for this component
    description: Optional[str] = None

    def matches_file(self, file_path: str) -> bool:
        """Check if file belongs to this component."""
        for path_pattern in self.paths:
            # Support glob-like patterns
            if path_pattern in file_path:
                return True
            # Support regex patterns (if pattern starts with ^)
            if path_pattern.startswith('^'):
                if re.match(path_pattern, file_path):
                    return True
        return False


@dataclass
class EvaluationResult:
    """Result of rule evaluation."""
    violations: List[Violation] = field(default_factory=list)
    rules_evaluated: int = 0
    components_checked: int = 0
    files_analyzed: int = 0
    execution_time_ms: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0

    @property
    def blocking_violations(self) -> List[Violation]:
        """Get blocking violations."""
        return [v for v in self.violations if v.severity == Severity.BLOCKING]

    @property
    def warning_violations(self) -> List[Violation]:
        """Get warning violations."""
        return [v for v in self.violations if v.severity == Severity.WARNING]

    @property
    def info_violations(self) -> List[Violation]:
        """Get info violations."""
        return [v for v in self.violations if v.severity == Severity.INFO]

    @property
    def has_blocking_violations(self) -> bool:
        """Check if any blocking violations exist."""
        return len(self.blocking_violations) > 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            'violations': [v.to_dict() for v in self.violations],
            'summary': {
                'total_violations': len(self.violations),
                'blocking': len(self.blocking_violations),
                'warning': len(self.warning_violations),
                'info': len(self.info_violations),
                'rules_evaluated': self.rules_evaluated,
                'components_checked': self.components_checked,
                'files_analyzed': self.files_analyzed,
                'execution_time_ms': self.execution_time_ms,
                'cache_hits': self.cache_hits,
                'cache_misses': self.cache_misses
            }
        }


# ============================================================================
# Rule Engine
# ============================================================================

class RuleEngine:
    """
    Core rule evaluation engine for architectural conformance checking.

    Features:
    - Multiple rule types (CAN_CALL, MUST_NOT_CALL, COUPLING, NO_CYCLES)
    - Configurable severity levels (INFO, WARNING, BLOCKING)
    - Component path mapping
    - Violation tracking and reporting
    - Performance optimization with caching
    - Dry-run mode for testing
    - Exemption support
    """

    def __init__(self, components: Optional[List[Component]] = None):
        """
        Initialize rule engine.

        Args:
            components: List of architectural components
        """
        self.components = components or []
        self.rules: List[Rule] = []
        self._file_to_component_cache: Dict[str, str] = {}
        self._evaluation_cache: Dict[str, bool] = {}
        self.metrics = {
            'evaluations': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }

    def add_rule(self, rule: Rule) -> None:
        """Add a rule to the engine."""
        self.rules.append(rule)
        logger.debug(f"Added rule: {rule.id} ({rule.rule_type.value})")

    def add_rules(self, rules: List[Rule]) -> None:
        """Add multiple rules to the engine."""
        for rule in rules:
            self.add_rule(rule)

    def load_rules_from_yaml(self, yaml_path: Path) -> int:
        """
        Load rules from YAML file.

        Args:
            yaml_path: Path to YAML file

        Returns:
            Number of rules loaded

        Raises:
            ValueError: If YAML is invalid or has syntax errors
        """
        if not yaml_path.exists():
            raise ValueError(f"YAML file not found: {yaml_path}")

        try:
            with open(yaml_path, 'r') as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML syntax: {e}")

        if not isinstance(data, dict):
            raise ValueError("YAML must contain a dictionary")

        # Load components if present
        if 'components' in data:
            for comp_data in data['components']:
                component = Component(
                    name=comp_data['name'],
                    paths=comp_data['paths'],
                    description=comp_data.get('description')
                )
                self.components.append(component)

        # Load rules
        rules_data = data.get('rules', [])
        if not isinstance(rules_data, list):
            raise ValueError("'rules' must be a list")

        loaded = 0
        for rule_data in rules_data:
            try:
                # Validate required fields
                required = ['id', 'rule_type', 'severity', 'description', 'component']
                missing = [f for f in required if f not in rule_data]
                if missing:
                    raise ValueError(f"Missing required fields: {missing}")

                # Validate rule_type
                if rule_data['rule_type'] not in [rt.value for rt in RuleType]:
                    raise ValueError(f"Invalid rule_type: {rule_data['rule_type']}")

                # Validate severity
                if rule_data['severity'] not in [s.value for s in Severity]:
                    raise ValueError(f"Invalid severity: {rule_data['severity']}")

                rule = Rule.from_dict(rule_data)
                self.add_rule(rule)
                loaded += 1
            except Exception as e:
                logger.error(f"Failed to load rule {rule_data.get('id', 'unknown')}: {e}")
                raise ValueError(f"Invalid rule definition: {e}")

        return loaded

    def get_component_for_file(self, file_path: str) -> Optional[str]:
        """
        Map file to component name.

        Args:
            file_path: File path to map

        Returns:
            Component name or None if not found
        """
        # Check cache first
        if file_path in self._file_to_component_cache:
            self.metrics['cache_hits'] += 1
            return self._file_to_component_cache[file_path]

        self.metrics['cache_misses'] += 1

        # Find matching component
        for component in self.components:
            if component.matches_file(file_path):
                self._file_to_component_cache[file_path] = component.name
                return component.name

        return None

    def evaluate_rule(
        self,
        rule: Rule,
        dependencies: Dict[str, List[str]],
        coupling_metrics: Optional[Dict[str, Tuple[int, int, float]]] = None,
        cycles: Optional[List[List[str]]] = None,
        dry_run: bool = False
    ) -> List[Violation]:
        """
        Evaluate a single rule against dependencies.

        Args:
            rule: Rule to evaluate
            dependencies: Dict of file -> list of dependency files
            coupling_metrics: Optional coupling metrics (Ca, Ce, I) per file
            cycles: Optional list of cycles (for NO_CYCLES rules)
            dry_run: If True, only simulate evaluation without creating violations

        Returns:
            List of violations found
        """
        self.metrics['evaluations'] += 1
        violations = []

        if not rule.enabled:
            return violations

        if rule.rule_type == RuleType.CAN_CALL:
            violations.extend(self._evaluate_can_call(rule, dependencies, dry_run))
        elif rule.rule_type == RuleType.MUST_NOT_CALL:
            violations.extend(self._evaluate_must_not_call(rule, dependencies, dry_run))
        elif rule.rule_type == RuleType.COUPLING:
            if coupling_metrics:
                violations.extend(self._evaluate_coupling(rule, coupling_metrics, dry_run))
        elif rule.rule_type == RuleType.NO_CYCLES:
            if cycles:
                violations.extend(self._evaluate_no_cycles(rule, cycles, dry_run))

        return violations

    def _evaluate_can_call(
        self,
        rule: Rule,
        dependencies: Dict[str, List[str]],
        dry_run: bool
    ) -> List[Violation]:
        """Evaluate CAN_CALL rule: component can only call specified target."""
        violations = []

        if not rule.target:
            return violations

        # Check all dependencies
        for source_file, dep_files in dependencies.items():
            source_component = self.get_component_for_file(source_file)

            # Check if rule applies
            if not rule.applies_to(source_component or '', source_file):
                continue

            # Check each dependency
            for dep_file in dep_files:
                target_component = self.get_component_for_file(dep_file)

                # Skip if same component (internal dependencies are allowed)
                if target_component == source_component:
                    continue

                # Violation if calling something other than allowed target
                if target_component and target_component != rule.target:
                    if not dry_run:
                        violation = Violation(
                            rule_id=rule.id,
                            rule_type=rule.rule_type,
                            severity=rule.severity,
                            source_component=source_component or 'Unknown',
                            target_component=target_component,
                            message=f"{source_component} can only call {rule.target}, but calls {target_component}",
                            source_file=source_file,
                            target_file=dep_file
                        )
                        violations.append(violation)

        return violations

    def _evaluate_must_not_call(
        self,
        rule: Rule,
        dependencies: Dict[str, List[str]],
        dry_run: bool
    ) -> List[Violation]:
        """Evaluate MUST_NOT_CALL rule: component must not call specified target."""
        violations = []

        if not rule.target:
            return violations

        # Check all dependencies
        for source_file, dep_files in dependencies.items():
            source_component = self.get_component_for_file(source_file)

            # Check if rule applies
            if not rule.applies_to(source_component or '', source_file):
                continue

            # Check each dependency
            for dep_file in dep_files:
                target_component = self.get_component_for_file(dep_file)

                # Violation if calling forbidden target
                if target_component == rule.target:
                    if not dry_run:
                        violation = Violation(
                            rule_id=rule.id,
                            rule_type=rule.rule_type,
                            severity=rule.severity,
                            source_component=source_component or 'Unknown',
                            target_component=target_component,
                            message=f"{source_component} must not call {rule.target}",
                            source_file=source_file,
                            target_file=dep_file
                        )
                        violations.append(violation)

        return violations

    def _evaluate_coupling(
        self,
        rule: Rule,
        coupling_metrics: Dict[str, Tuple[int, int, float]],
        dry_run: bool
    ) -> List[Violation]:
        """Evaluate COUPLING rule: coupling must be below threshold."""
        violations = []

        if rule.threshold is None:
            return violations

        # Check coupling for each file
        for file_path, (ca, ce, instability) in coupling_metrics.items():
            component = self.get_component_for_file(file_path)

            # Check if rule applies
            if not rule.applies_to(component or '', file_path):
                continue

            total_coupling = ca + ce

            # Violation if coupling exceeds threshold
            if total_coupling > rule.threshold:
                if not dry_run:
                    violation = Violation(
                        rule_id=rule.id,
                        rule_type=rule.rule_type,
                        severity=rule.severity,
                        source_component=component or 'Unknown',
                        target_component=None,
                        message=f"{component} has coupling {total_coupling} > threshold {rule.threshold}",
                        source_file=file_path
                    )
                    violations.append(violation)

        return violations

    def _evaluate_no_cycles(
        self,
        rule: Rule,
        cycles: List[List[str]],
        dry_run: bool
    ) -> List[Violation]:
        """Evaluate NO_CYCLES rule: detect cyclic dependencies."""
        violations = []

        # Check each cycle
        for cycle in cycles:
            # Map cycle files to components
            cycle_components = []
            for file_path in cycle:
                component = self.get_component_for_file(file_path)
                if component:
                    cycle_components.append(component)

            # Check if any component in cycle matches rule
            for component in cycle_components:
                if rule.applies_to(component, None):
                    if not dry_run:
                        violation = Violation(
                            rule_id=rule.id,
                            rule_type=rule.rule_type,
                            severity=rule.severity,
                            source_component=component,
                            target_component=None,
                            message=f"Cyclic dependency detected in {component}: {' -> '.join(cycle[:3])}...",
                            source_file=cycle[0] if cycle else None
                        )
                        violations.append(violation)
                    break  # Only report once per cycle

        return violations

    def evaluate_all(
        self,
        dependencies: Dict[str, List[str]],
        coupling_metrics: Optional[Dict[str, Tuple[int, int, float]]] = None,
        cycles: Optional[List[List[str]]] = None,
        dry_run: bool = False
    ) -> EvaluationResult:
        """
        Evaluate all rules against dependencies.

        Args:
            dependencies: Dict of file -> list of dependency files
            coupling_metrics: Optional coupling metrics per file
            cycles: Optional list of cycles
            dry_run: If True, only simulate evaluation

        Returns:
            EvaluationResult with all violations and metrics
        """
        start_time = datetime.now()

        result = EvaluationResult()
        result.files_analyzed = len(dependencies)

        # Get unique components
        components_seen = set()
        for file_path in dependencies.keys():
            component = self.get_component_for_file(file_path)
            if component:
                components_seen.add(component)
        result.components_checked = len(components_seen)

        # Evaluate each rule
        for rule in self.rules:
            violations = self.evaluate_rule(
                rule=rule,
                dependencies=dependencies,
                coupling_metrics=coupling_metrics,
                cycles=cycles,
                dry_run=dry_run
            )
            result.violations.extend(violations)
            result.rules_evaluated += 1

        # Calculate execution time
        end_time = datetime.now()
        result.execution_time_ms = (end_time - start_time).total_seconds() * 1000

        # Add cache metrics
        result.cache_hits = self.metrics['cache_hits']
        result.cache_misses = self.metrics['cache_misses']

        logger.info(f"Evaluated {result.rules_evaluated} rules, found {len(result.violations)} violations")

        return result

    def clear_cache(self) -> None:
        """Clear all caches."""
        self._file_to_component_cache.clear()
        self._evaluation_cache.clear()
        self.metrics['cache_hits'] = 0
        self.metrics['cache_misses'] = 0

    def get_rules_for_component(self, component_name: str) -> List[Rule]:
        """Get all rules applicable to a component."""
        return [r for r in self.rules if r.component == component_name]

    def get_enabled_rules(self) -> List[Rule]:
        """Get all enabled rules."""
        return [r for r in self.rules if r.enabled]

    def disable_rule(self, rule_id: str) -> bool:
        """Disable a rule by ID."""
        for rule in self.rules:
            if rule.id == rule_id:
                rule.enabled = False
                return True
        return False

    def enable_rule(self, rule_id: str) -> bool:
        """Enable a rule by ID."""
        for rule in self.rules:
            if rule.id == rule_id:
                rule.enabled = True
                return True
        return False


# ============================================================================
# Helper Functions
# ============================================================================

def parse_rule_from_string(rule_str: str, component: str) -> Optional[Rule]:
    """
    Parse rule from string format.

    Formats:
    - "CAN_CALL(Target)"
    - "MUST_NOT_CALL(Target)"
    - "COUPLING < N"
    - "NO_CYCLES"

    Args:
        rule_str: Rule string to parse
        component: Component name this rule applies to

    Returns:
        Rule object or None if parsing fails
    """
    rule_str = rule_str.strip()

    # CAN_CALL
    match = re.match(r'CAN_CALL\((\w+)\)', rule_str)
    if match:
        return Rule(
            id=f"{component}_CAN_CALL_{match.group(1)}",
            rule_type=RuleType.CAN_CALL,
            severity=Severity.WARNING,
            description=f"{component} can only call {match.group(1)}",
            component=component,
            target=match.group(1)
        )

    # MUST_NOT_CALL
    match = re.match(r'MUST_NOT_CALL\((\w+)\)', rule_str)
    if match:
        return Rule(
            id=f"{component}_MUST_NOT_CALL_{match.group(1)}",
            rule_type=RuleType.MUST_NOT_CALL,
            severity=Severity.BLOCKING,
            description=f"{component} must not call {match.group(1)}",
            component=component,
            target=match.group(1)
        )

    # COUPLING
    match = re.match(r'COUPLING\s*<\s*(\d+)', rule_str)
    if match:
        return Rule(
            id=f"{component}_COUPLING_{match.group(1)}",
            rule_type=RuleType.COUPLING,
            severity=Severity.WARNING,
            description=f"{component} coupling must be less than {match.group(1)}",
            component=component,
            threshold=int(match.group(1))
        )

    # NO_CYCLES
    if rule_str == 'NO_CYCLES':
        return Rule(
            id=f"{component}_NO_CYCLES",
            rule_type=RuleType.NO_CYCLES,
            severity=Severity.BLOCKING,
            description=f"{component} must not have cyclic dependencies",
            component=component
        )

    return None


def validate_rule_definition(rule_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate rule definition.

    Args:
        rule_data: Rule data dictionary

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check required fields
    required = ['id', 'rule_type', 'severity', 'description', 'component']
    for field in required:
        if field not in rule_data:
            return False, f"Missing required field: {field}"

    # Validate rule_type
    try:
        RuleType(rule_data['rule_type'])
    except ValueError:
        return False, f"Invalid rule_type: {rule_data['rule_type']}"

    # Validate severity
    try:
        Severity(rule_data['severity'])
    except ValueError:
        return False, f"Invalid severity: {rule_data['severity']}"

    # Validate rule-specific fields
    rule_type = RuleType(rule_data['rule_type'])
    if rule_type in (RuleType.CAN_CALL, RuleType.MUST_NOT_CALL):
        if 'target' not in rule_data:
            return False, f"{rule_type.value} requires 'target' field"
    elif rule_type == RuleType.COUPLING:
        if 'threshold' not in rule_data:
            return False, f"{rule_type.value} requires 'threshold' field"
        if not isinstance(rule_data['threshold'], int):
            return False, f"'threshold' must be an integer"

    return True, None
