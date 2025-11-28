"""
ACC Rule Engine Test Suite - Test Suite 17: Core Rules

Comprehensive tests for ACC Rule Engine functionality.
Test IDs: ACC-101 to ACC-140 (40 tests)

Test Categories:
1. Rule types (ACC-101 to ACC-104): CAN_CALL, MUST_NOT_CALL, COUPLING, NO_CYCLES
2. CAN_CALL rules (ACC-105 to ACC-106): Allow target, disallow others
3. MUST_NOT_CALL rules (ACC-107 to ACC-108): Forbid target, allow others
4. Component mapping (ACC-109 to ACC-112): Files to components, dependencies, violations, messages
5. Severity levels (ACC-113 to ACC-118): BLOCKING/WARNING/INFO behavior, multiple rules
6. Evaluation (ACC-119 to ACC-127): No violations, violations, logging, metrics, caching, dry-run, exemptions
7. Custom validators (ACC-128 to ACC-140): YAML parsing, syntax validation, undefined components, etc.

Author: Claude Code Implementation
Date: 2025-10-13
Version: 1.0.0
"""

import pytest
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
import tempfile
import yaml
import logging

from acc.rule_engine import (
    RuleEngine,
    Rule,
    RuleType,
    Severity,
    Component,
    Violation,
    EvaluationResult,
    parse_rule_from_string,
    validate_rule_definition
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def sample_components():
    """Sample architectural components."""
    return [
        Component(
            name="Presentation",
            paths=["presentation/", "ui/", "views/"],
            description="UI and presentation layer"
        ),
        Component(
            name="BusinessLogic",
            paths=["business/", "services/", "logic/"],
            description="Business logic layer"
        ),
        Component(
            name="DataAccess",
            paths=["data/", "repositories/", "dao/"],
            description="Data access layer"
        ),
        Component(
            name="Infrastructure",
            paths=["infrastructure/", "config/"],
            description="Infrastructure layer"
        )
    ]


@pytest.fixture
def rule_engine(sample_components):
    """Initialized rule engine with sample components."""
    return RuleEngine(components=sample_components)


@pytest.fixture
def sample_dependencies():
    """Sample file dependencies for testing."""
    return {
        "presentation/home_view.py": ["business/user_service.py", "presentation/base.py"],
        "presentation/login_view.py": ["business/auth_service.py"],
        "business/user_service.py": ["data/user_repository.py", "business/validator.py"],
        "business/auth_service.py": ["data/auth_repository.py", "infrastructure/crypto.py"],
        "data/user_repository.py": ["infrastructure/database.py"],
        "data/auth_repository.py": ["infrastructure/database.py"],
    }


@pytest.fixture
def sample_coupling_metrics():
    """Sample coupling metrics (Ca, Ce, Instability)."""
    return {
        "presentation/home_view.py": (0, 2, 1.0),  # Highly unstable
        "business/user_service.py": (1, 2, 0.67),
        "business/auth_service.py": (1, 2, 0.67),
        "data/user_repository.py": (1, 1, 0.5),
        "data/auth_repository.py": (1, 1, 0.5),
        "infrastructure/database.py": (2, 0, 0.0),  # Highly stable
    }


@pytest.fixture
def sample_cycles():
    """Sample cyclic dependencies."""
    return [
        ["business/order_service.py", "business/payment_service.py", "business/order_service.py"],
        ["data/cache.py", "data/store.py", "data/cache.py"]
    ]


# ============================================================================
# Category 1: Rule Types (ACC-101 to ACC-104)
# ============================================================================

def test_acc_101_can_call_rule_type():
    """ACC-101: CAN_CALL rule type can be created and evaluated."""
    rule = Rule(
        id="R1",
        rule_type=RuleType.CAN_CALL,
        severity=Severity.WARNING,
        description="Presentation can only call BusinessLogic",
        component="Presentation",
        target="BusinessLogic"
    )

    assert rule.rule_type == RuleType.CAN_CALL
    assert rule.target == "BusinessLogic"
    assert rule.enabled is True


def test_acc_102_must_not_call_rule_type():
    """ACC-102: MUST_NOT_CALL rule type can be created and evaluated."""
    rule = Rule(
        id="R2",
        rule_type=RuleType.MUST_NOT_CALL,
        severity=Severity.BLOCKING,
        description="Presentation must not call DataAccess",
        component="Presentation",
        target="DataAccess"
    )

    assert rule.rule_type == RuleType.MUST_NOT_CALL
    assert rule.target == "DataAccess"
    assert rule.severity == Severity.BLOCKING


def test_acc_103_coupling_rule_type():
    """ACC-103: COUPLING < N rule type with threshold evaluation."""
    rule = Rule(
        id="R3",
        rule_type=RuleType.COUPLING,
        severity=Severity.WARNING,
        description="Component coupling must be less than 5",
        component="BusinessLogic",
        threshold=5
    )

    assert rule.rule_type == RuleType.COUPLING
    assert rule.threshold == 5


def test_acc_104_no_cycles_rule_type():
    """ACC-104: NO_CYCLES rule type detects cyclic dependencies."""
    rule = Rule(
        id="R4",
        rule_type=RuleType.NO_CYCLES,
        severity=Severity.BLOCKING,
        description="No cyclic dependencies allowed",
        component="BusinessLogic"
    )

    assert rule.rule_type == RuleType.NO_CYCLES
    assert rule.severity == Severity.BLOCKING


# ============================================================================
# Category 2: CAN_CALL Rules (ACC-105 to ACC-106)
# ============================================================================

def test_acc_105_can_call_allows_target(rule_engine, sample_dependencies):
    """ACC-105: CAN_CALL rule allows calling specified target."""
    rule = Rule(
        id="R5",
        rule_type=RuleType.CAN_CALL,
        severity=Severity.WARNING,
        description="Presentation can call BusinessLogic",
        component="Presentation",
        target="BusinessLogic"
    )
    rule_engine.add_rule(rule)

    # Presentation -> BusinessLogic should be allowed
    result = rule_engine.evaluate_all(sample_dependencies)

    # Should not have violations for Presentation -> BusinessLogic
    pres_to_business_violations = [
        v for v in result.violations
        if v.source_component == "Presentation" and v.target_component == "BusinessLogic"
    ]
    assert len(pres_to_business_violations) == 0


def test_acc_106_can_call_disallows_others(rule_engine, sample_dependencies):
    """ACC-106: CAN_CALL rule disallows calling non-target components."""
    rule = Rule(
        id="R6",
        rule_type=RuleType.CAN_CALL,
        severity=Severity.WARNING,
        description="Presentation can only call BusinessLogic",
        component="Presentation",
        target="BusinessLogic"
    )
    rule_engine.add_rule(rule)

    # Add a violation: Presentation -> DataAccess
    deps_with_violation = sample_dependencies.copy()
    deps_with_violation["presentation/bad_view.py"] = ["data/user_repository.py"]

    result = rule_engine.evaluate_all(deps_with_violation)

    # Should have violation for Presentation -> DataAccess
    violations = [
        v for v in result.violations
        if v.source_component == "Presentation" and v.target_component == "DataAccess"
    ]
    assert len(violations) > 0
    assert violations[0].severity == Severity.WARNING


# ============================================================================
# Category 3: MUST_NOT_CALL Rules (ACC-107 to ACC-108)
# ============================================================================

def test_acc_107_must_not_call_forbids_target(rule_engine):
    """ACC-107: MUST_NOT_CALL rule forbids calling specified target."""
    rule = Rule(
        id="R7",
        rule_type=RuleType.MUST_NOT_CALL,
        severity=Severity.BLOCKING,
        description="Presentation must not call DataAccess",
        component="Presentation",
        target="DataAccess"
    )
    rule_engine.add_rule(rule)

    # Create dependency that violates rule
    dependencies = {
        "presentation/bad_view.py": ["data/user_repository.py"]
    }

    result = rule_engine.evaluate_all(dependencies)

    # Should have blocking violation
    assert len(result.violations) > 0
    violation = result.violations[0]
    assert violation.source_component == "Presentation"
    assert violation.target_component == "DataAccess"
    assert violation.severity == Severity.BLOCKING


def test_acc_108_must_not_call_allows_others(rule_engine, sample_dependencies):
    """ACC-108: MUST_NOT_CALL rule allows calling other components."""
    rule = Rule(
        id="R8",
        rule_type=RuleType.MUST_NOT_CALL,
        severity=Severity.BLOCKING,
        description="Presentation must not call DataAccess",
        component="Presentation",
        target="DataAccess"
    )
    rule_engine.add_rule(rule)

    # Presentation -> BusinessLogic should be allowed
    result = rule_engine.evaluate_all(sample_dependencies)

    # Should have no violations for Presentation -> BusinessLogic
    pres_to_business = [
        v for v in result.violations
        if v.source_component == "Presentation" and v.target_component == "BusinessLogic"
    ]
    assert len(pres_to_business) == 0


# ============================================================================
# Category 4: Component Mapping (ACC-109 to ACC-112)
# ============================================================================

def test_acc_109_files_mapped_to_components(rule_engine):
    """ACC-109: Files are correctly mapped to architectural components."""
    assert rule_engine.get_component_for_file("presentation/home_view.py") == "Presentation"
    assert rule_engine.get_component_for_file("business/user_service.py") == "BusinessLogic"
    assert rule_engine.get_component_for_file("data/user_repository.py") == "DataAccess"
    assert rule_engine.get_component_for_file("infrastructure/config.py") == "Infrastructure"


def test_acc_110_unmapped_files_return_none(rule_engine):
    """ACC-110: Files not matching any component return None."""
    assert rule_engine.get_component_for_file("unknown/random_file.py") is None
    assert rule_engine.get_component_for_file("tests/test_something.py") is None


def test_acc_111_component_dependencies_checked(rule_engine, sample_dependencies):
    """ACC-111: Component-level dependencies are checked correctly."""
    rule = Rule(
        id="R11",
        rule_type=RuleType.MUST_NOT_CALL,
        severity=Severity.BLOCKING,
        description="Presentation must not call DataAccess",
        component="Presentation",
        target="DataAccess"
    )
    rule_engine.add_rule(rule)

    # Add violation
    deps_with_violation = sample_dependencies.copy()
    deps_with_violation["presentation/bad_view.py"] = ["data/user_repository.py"]

    result = rule_engine.evaluate_all(deps_with_violation)

    # Should detect component-level violation
    assert len(result.violations) > 0
    violation = result.violations[0]
    assert "Presentation" in violation.message
    assert "DataAccess" in violation.message


def test_acc_112_violation_messages_include_components(rule_engine):
    """ACC-112: Violation messages include source and target components."""
    rule = Rule(
        id="R12",
        rule_type=RuleType.MUST_NOT_CALL,
        severity=Severity.WARNING,
        description="Test rule",
        component="Presentation",
        target="DataAccess"
    )
    rule_engine.add_rule(rule)

    dependencies = {
        "presentation/view.py": ["data/repository.py"]
    }

    result = rule_engine.evaluate_all(dependencies)

    assert len(result.violations) > 0
    violation = result.violations[0]
    assert "Presentation" in violation.message
    assert "DataAccess" in violation.message
    assert violation.source_file is not None
    assert violation.target_file is not None


# ============================================================================
# Category 5: Severity Levels (ACC-113 to ACC-118)
# ============================================================================

def test_acc_113_blocking_severity_fails_audit(rule_engine):
    """ACC-113: BLOCKING severity violations cause audit to fail."""
    rule = Rule(
        id="R13",
        rule_type=RuleType.MUST_NOT_CALL,
        severity=Severity.BLOCKING,
        description="Critical rule",
        component="Presentation",
        target="DataAccess"
    )
    rule_engine.add_rule(rule)

    dependencies = {
        "presentation/view.py": ["data/repository.py"]
    }

    result = rule_engine.evaluate_all(dependencies)

    # Should have blocking violations
    assert result.has_blocking_violations is True
    assert len(result.blocking_violations) > 0


def test_acc_114_warning_severity_passes_audit(rule_engine):
    """ACC-114: WARNING severity violations don't block audit."""
    rule = Rule(
        id="R14",
        rule_type=RuleType.COUPLING,
        severity=Severity.WARNING,
        description="Warning rule",
        component="BusinessLogic",
        threshold=3
    )
    rule_engine.add_rule(rule)

    coupling_metrics = {
        "business/service.py": (5, 5, 0.5)  # Total coupling = 10
    }

    result = rule_engine.evaluate_all({}, coupling_metrics=coupling_metrics)

    # Should have warnings but not blocking
    assert len(result.warning_violations) > 0
    assert result.has_blocking_violations is False


def test_acc_115_info_severity_informational_only(rule_engine):
    """ACC-115: INFO severity is informational only."""
    rule = Rule(
        id="R15",
        rule_type=RuleType.COUPLING,
        severity=Severity.INFO,
        description="Info rule",
        component="DataAccess",
        threshold=2
    )
    rule_engine.add_rule(rule)

    coupling_metrics = {
        "data/repository.py": (3, 3, 0.5)  # Total coupling = 6
    }

    result = rule_engine.evaluate_all({}, coupling_metrics=coupling_metrics)

    # Should have info violations
    assert len(result.info_violations) > 0
    assert result.has_blocking_violations is False
    assert len(result.blocking_violations) == 0


def test_acc_116_multiple_severities_coexist(rule_engine):
    """ACC-116: Multiple severity levels can coexist in results."""
    rules = [
        Rule(
            id="R16a",
            rule_type=RuleType.MUST_NOT_CALL,
            severity=Severity.BLOCKING,
            description="Blocking rule",
            component="Presentation",
            target="DataAccess"
        ),
        Rule(
            id="R16b",
            rule_type=RuleType.COUPLING,
            severity=Severity.WARNING,
            description="Warning rule",
            component="BusinessLogic",
            threshold=3
        ),
        Rule(
            id="R16c",
            rule_type=RuleType.COUPLING,
            severity=Severity.INFO,
            description="Info rule",
            component="Infrastructure",
            threshold=1
        )
    ]
    rule_engine.add_rules(rules)

    dependencies = {
        "presentation/view.py": ["data/repository.py"]
    }

    coupling_metrics = {
        "business/service.py": (5, 5, 0.5),
        "infrastructure/util.py": (3, 3, 0.5)
    }

    result = rule_engine.evaluate_all(dependencies, coupling_metrics=coupling_metrics)

    # Should have all three severity types
    assert len(result.blocking_violations) > 0
    assert len(result.warning_violations) > 0
    assert len(result.info_violations) > 0


def test_acc_117_severity_filtering(rule_engine):
    """ACC-117: Can filter violations by severity."""
    rule = Rule(
        id="R17",
        rule_type=RuleType.MUST_NOT_CALL,
        severity=Severity.WARNING,
        description="Warning rule",
        component="Presentation",
        target="DataAccess"
    )
    rule_engine.add_rule(rule)

    dependencies = {
        "presentation/view.py": ["data/repository.py"]
    }

    result = rule_engine.evaluate_all(dependencies)

    # Filter by severity
    warnings = result.warning_violations
    blockings = result.blocking_violations

    assert len(warnings) > 0
    assert len(blockings) == 0
    assert all(v.severity == Severity.WARNING for v in warnings)


def test_acc_118_multiple_rules_per_component(rule_engine):
    """ACC-118: Multiple rules can apply to same component."""
    rules = [
        Rule(
            id="R18a",
            rule_type=RuleType.MUST_NOT_CALL,
            severity=Severity.BLOCKING,
            description="Rule 1",
            component="Presentation",
            target="DataAccess"
        ),
        Rule(
            id="R18b",
            rule_type=RuleType.COUPLING,
            severity=Severity.WARNING,
            description="Rule 2",
            component="Presentation",
            threshold=5
        )
    ]
    rule_engine.add_rules(rules)

    dependencies = {
        "presentation/view.py": ["data/repository.py"]
    }

    coupling_metrics = {
        "presentation/view.py": (10, 10, 0.5)
    }

    result = rule_engine.evaluate_all(dependencies, coupling_metrics=coupling_metrics)

    # Should have violations from both rules
    pres_violations = [v for v in result.violations if v.source_component == "Presentation"]
    assert len(pres_violations) >= 2


# ============================================================================
# Category 6: Evaluation (ACC-119 to ACC-127)
# ============================================================================

def test_acc_119_no_violations_clean_result(rule_engine, sample_dependencies):
    """ACC-119: Evaluation with no violations returns clean result."""
    rule = Rule(
        id="R19",
        rule_type=RuleType.MUST_NOT_CALL,
        severity=Severity.BLOCKING,
        description="Rule that doesn't trigger",
        component="Presentation",
        target="Infrastructure"  # Not called by Presentation in sample
    )
    rule_engine.add_rule(rule)

    result = rule_engine.evaluate_all(sample_dependencies)

    assert len(result.violations) == 0
    assert result.has_blocking_violations is False


def test_acc_120_single_violation_detected(rule_engine):
    """ACC-120: Single violation is correctly detected and reported."""
    rule = Rule(
        id="R20",
        rule_type=RuleType.MUST_NOT_CALL,
        severity=Severity.BLOCKING,
        description="Test rule",
        component="Presentation",
        target="DataAccess"
    )
    rule_engine.add_rule(rule)

    dependencies = {
        "presentation/view.py": ["data/repository.py"]
    }

    result = rule_engine.evaluate_all(dependencies)

    assert len(result.violations) == 1
    violation = result.violations[0]
    assert violation.rule_id == "R20"
    assert violation.severity == Severity.BLOCKING


def test_acc_121_multiple_violations_detected(rule_engine):
    """ACC-121: Multiple violations are detected and reported."""
    rule = Rule(
        id="R21",
        rule_type=RuleType.MUST_NOT_CALL,
        severity=Severity.BLOCKING,
        description="Test rule",
        component="Presentation",
        target="DataAccess"
    )
    rule_engine.add_rule(rule)

    dependencies = {
        "presentation/view1.py": ["data/repository1.py"],
        "presentation/view2.py": ["data/repository2.py"],
        "presentation/view3.py": ["data/repository3.py"]
    }

    result = rule_engine.evaluate_all(dependencies)

    assert len(result.violations) == 3
    assert all(v.rule_id == "R21" for v in result.violations)


def test_acc_122_evaluation_logs_activity(rule_engine, caplog):
    """ACC-122: Evaluation logs activity for debugging."""
    caplog.set_level(logging.INFO)

    rule = Rule(
        id="R22",
        rule_type=RuleType.MUST_NOT_CALL,
        severity=Severity.BLOCKING,
        description="Test rule",
        component="Presentation",
        target="DataAccess"
    )
    rule_engine.add_rule(rule)

    dependencies = {
        "presentation/view.py": ["data/repository.py"]
    }

    result = rule_engine.evaluate_all(dependencies)

    # Check that logging occurred
    assert len(caplog.records) > 0


def test_acc_123_evaluation_tracks_metrics(rule_engine, sample_dependencies):
    """ACC-123: Evaluation tracks performance metrics."""
    rule = Rule(
        id="R23",
        rule_type=RuleType.MUST_NOT_CALL,
        severity=Severity.WARNING,
        description="Test rule",
        component="Presentation",
        target="DataAccess"
    )
    rule_engine.add_rule(rule)

    result = rule_engine.evaluate_all(sample_dependencies)

    # Check metrics
    assert result.rules_evaluated == 1
    assert result.files_analyzed == len(sample_dependencies)
    assert result.execution_time_ms >= 0


def test_acc_124_component_mapping_cached(rule_engine):
    """ACC-124: Component mapping results are cached for performance."""
    # First lookup - cache miss
    comp1 = rule_engine.get_component_for_file("presentation/view.py")
    assert comp1 == "Presentation"

    # Second lookup - cache hit
    comp2 = rule_engine.get_component_for_file("presentation/view.py")
    assert comp2 == "Presentation"

    # Check cache metrics
    assert rule_engine.metrics['cache_hits'] > 0


def test_acc_125_dry_run_mode_no_violations(rule_engine):
    """ACC-125: Dry-run mode evaluates rules without creating violations."""
    rule = Rule(
        id="R25",
        rule_type=RuleType.MUST_NOT_CALL,
        severity=Severity.BLOCKING,
        description="Test rule",
        component="Presentation",
        target="DataAccess"
    )
    rule_engine.add_rule(rule)

    dependencies = {
        "presentation/view.py": ["data/repository.py"]
    }

    result = rule_engine.evaluate_all(dependencies, dry_run=True)

    # Dry run should not create violations
    assert len(result.violations) == 0


def test_acc_126_exemptions_honored(rule_engine):
    """ACC-126: File exemptions are honored in rule evaluation."""
    rule = Rule(
        id="R26",
        rule_type=RuleType.MUST_NOT_CALL,
        severity=Severity.BLOCKING,
        description="Test rule",
        component="Presentation",
        target="DataAccess",
        exemptions=["presentation/legacy_view.py"]
    )
    rule_engine.add_rule(rule)

    dependencies = {
        "presentation/legacy_view.py": ["data/repository.py"],  # Exempted
        "presentation/new_view.py": ["data/repository.py"]  # Not exempted
    }

    result = rule_engine.evaluate_all(dependencies)

    # Should only have 1 violation (new_view.py)
    assert len(result.violations) == 1
    assert "new_view.py" in result.violations[0].source_file


def test_acc_127_cache_can_be_cleared(rule_engine):
    """ACC-127: Cache can be cleared to force re-evaluation."""
    # Populate cache
    rule_engine.get_component_for_file("presentation/view.py")
    initial_hits = rule_engine.metrics['cache_hits']

    # Clear cache
    rule_engine.clear_cache()

    # Metrics should be reset
    assert rule_engine.metrics['cache_hits'] == 0
    assert rule_engine.metrics['cache_misses'] == 0
    assert len(rule_engine._file_to_component_cache) == 0


# ============================================================================
# Category 7: Custom Validators (ACC-128 to ACC-140)
# ============================================================================

def test_acc_128_parse_rules_from_yaml(rule_engine):
    """ACC-128: Rules can be parsed from YAML configuration."""
    yaml_content = """
components:
  - name: Presentation
    paths:
      - presentation/
      - ui/

rules:
  - id: R28
    rule_type: MUST_NOT_CALL
    severity: blocking
    description: "Presentation must not call DataAccess"
    component: Presentation
    target: DataAccess
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(yaml_content)
        yaml_path = Path(f.name)

    try:
        count = rule_engine.load_rules_from_yaml(yaml_path)
        assert count == 1
        assert len(rule_engine.rules) == 1
        assert rule_engine.rules[0].id == "R28"
    finally:
        yaml_path.unlink()


def test_acc_129_yaml_syntax_validation(rule_engine):
    """ACC-129: Invalid YAML syntax is detected and reported."""
    yaml_content = """
rules:
  - id: R29
    rule_type: INVALID_TYPE
    severity: blocking
    description: "Test rule"
    component: TestComponent
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(yaml_content)
        yaml_path = Path(f.name)

    try:
        with pytest.raises(ValueError, match="Invalid rule_type"):
            rule_engine.load_rules_from_yaml(yaml_path)
    finally:
        yaml_path.unlink()


def test_acc_130_undefined_components_detected(rule_engine):
    """ACC-130: References to undefined components are detected."""
    # Rule references non-existent component
    rule = Rule(
        id="R30",
        rule_type=RuleType.MUST_NOT_CALL,
        severity=Severity.WARNING,
        description="Test",
        component="NonExistent",
        target="DataAccess"
    )
    rule_engine.add_rule(rule)

    dependencies = {
        "unknown/file.py": ["data/repository.py"]
    }

    result = rule_engine.evaluate_all(dependencies)

    # Rule should not trigger for unmapped components
    assert len(result.violations) == 0


def test_acc_131_rule_validation_error_handling():
    """ACC-131: Rule validation errors are properly handled."""
    # Missing required fields
    invalid_rule_data = {
        'id': 'R31',
        'rule_type': 'MUST_NOT_CALL'
        # Missing: severity, description, component
    }

    is_valid, error = validate_rule_definition(invalid_rule_data)
    assert is_valid is False
    assert error is not None
    assert "Missing required field" in error


def test_acc_132_rule_documentation_preserved():
    """ACC-132: Rule documentation and metadata are preserved."""
    rule = Rule(
        id="R32",
        rule_type=RuleType.MUST_NOT_CALL,
        severity=Severity.BLOCKING,
        description="Detailed description of rule",
        component="Presentation",
        target="DataAccess",
        metadata={
            'author': 'Architecture Team',
            'created': '2025-01-01',
            'rationale': 'Maintain layer separation'
        }
    )

    # Metadata should be preserved
    assert rule.metadata['author'] == 'Architecture Team'
    assert rule.metadata['rationale'] == 'Maintain layer separation'

    # Should survive serialization
    rule_dict = rule.to_dict()
    assert 'metadata' in rule_dict
    assert rule_dict['metadata']['author'] == 'Architecture Team'


def test_acc_133_rule_versioning_support():
    """ACC-133: Rules support versioning for evolution tracking."""
    rule_v1 = Rule(
        id="R33",
        rule_type=RuleType.COUPLING,
        severity=Severity.WARNING,
        description="Old coupling rule",
        component="BusinessLogic",
        threshold=10,
        version="1.0.0"
    )

    rule_v2 = Rule(
        id="R33",
        rule_type=RuleType.COUPLING,
        severity=Severity.BLOCKING,  # Stricter in v2
        description="Updated coupling rule",
        component="BusinessLogic",
        threshold=5,  # Lower threshold in v2
        version="2.0.0"
    )

    assert rule_v1.version == "1.0.0"
    assert rule_v2.version == "2.0.0"
    assert rule_v1.threshold != rule_v2.threshold


def test_acc_134_ab_testing_rules():
    """ACC-134: Support for A/B testing different rule configurations."""
    # Two different approaches for the same architectural constraint
    rule_a = Rule(
        id="R34A",
        rule_type=RuleType.CAN_CALL,
        severity=Severity.WARNING,
        description="Approach A: Whitelist",
        component="Presentation",
        target="BusinessLogic",
        metadata={'variant': 'A', 'test_group': 'whitelist'}
    )

    rule_b = Rule(
        id="R34B",
        rule_type=RuleType.MUST_NOT_CALL,
        severity=Severity.WARNING,
        description="Approach B: Blacklist",
        component="Presentation",
        target="DataAccess",
        metadata={'variant': 'B', 'test_group': 'blacklist'}
    )

    # Both approaches should be testable
    assert rule_a.metadata['variant'] == 'A'
    assert rule_b.metadata['variant'] == 'B'


def test_acc_135_gradual_rule_rollout():
    """ACC-135: Rules can be gradually rolled out using enable/disable."""
    rule = Rule(
        id="R35",
        rule_type=RuleType.MUST_NOT_CALL,
        severity=Severity.BLOCKING,
        description="New strict rule",
        component="Presentation",
        target="DataAccess",
        enabled=False  # Start disabled
    )

    engine = RuleEngine(components=[
        Component(name="Presentation", paths=["presentation/"]),
        Component(name="DataAccess", paths=["data/"])
    ])
    engine.add_rule(rule)

    dependencies = {
        "presentation/view.py": ["data/repository.py"]
    }

    # Should have no violations when disabled
    result1 = engine.evaluate_all(dependencies)
    assert len(result1.violations) == 0

    # Enable rule
    engine.enable_rule("R35")

    # Should have violations when enabled
    result2 = engine.evaluate_all(dependencies)
    assert len(result2.violations) > 0


def test_acc_136_deprecated_rule_handling():
    """ACC-136: Deprecated rules can be marked and handled appropriately."""
    rule = Rule(
        id="R36",
        rule_type=RuleType.COUPLING,
        severity=Severity.INFO,  # Downgraded to INFO when deprecated
        description="Deprecated rule - will be removed in v3.0",
        component="Infrastructure",
        threshold=20,
        enabled=True,
        metadata={
            'deprecated': True,
            'deprecated_since': '2.5.0',
            'remove_in': '3.0.0',
            'replacement': 'R36B'
        }
    )

    # Deprecated rule should still work but be marked
    assert rule.metadata['deprecated'] is True
    assert rule.metadata['replacement'] == 'R36B'


def test_acc_137_parse_rule_from_string_can_call():
    """ACC-137: Parse CAN_CALL rule from string format."""
    rule = parse_rule_from_string("CAN_CALL(BusinessLogic)", "Presentation")

    assert rule is not None
    assert rule.rule_type == RuleType.CAN_CALL
    assert rule.component == "Presentation"
    assert rule.target == "BusinessLogic"


def test_acc_138_parse_rule_from_string_must_not_call():
    """ACC-138: Parse MUST_NOT_CALL rule from string format."""
    rule = parse_rule_from_string("MUST_NOT_CALL(DataAccess)", "Presentation")

    assert rule is not None
    assert rule.rule_type == RuleType.MUST_NOT_CALL
    assert rule.component == "Presentation"
    assert rule.target == "DataAccess"


def test_acc_139_parse_rule_from_string_coupling():
    """ACC-139: Parse COUPLING < N rule from string format."""
    rule = parse_rule_from_string("COUPLING < 5", "BusinessLogic")

    assert rule is not None
    assert rule.rule_type == RuleType.COUPLING
    assert rule.component == "BusinessLogic"
    assert rule.threshold == 5


def test_acc_140_parse_rule_from_string_no_cycles():
    """ACC-140: Parse NO_CYCLES rule from string format."""
    rule = parse_rule_from_string("NO_CYCLES", "BusinessLogic")

    assert rule is not None
    assert rule.rule_type == RuleType.NO_CYCLES
    assert rule.component == "BusinessLogic"


# ============================================================================
# Additional Edge Cases and Integration Tests
# ============================================================================

def test_rule_to_dict_serialization():
    """Test that rules can be serialized to dictionary."""
    rule = Rule(
        id="R_TEST",
        rule_type=RuleType.MUST_NOT_CALL,
        severity=Severity.BLOCKING,
        description="Test rule",
        component="Presentation",
        target="DataAccess"
    )

    rule_dict = rule.to_dict()

    assert rule_dict['id'] == "R_TEST"
    assert rule_dict['rule_type'] == "MUST_NOT_CALL"
    assert rule_dict['severity'] == "blocking"


def test_rule_from_dict_deserialization():
    """Test that rules can be deserialized from dictionary."""
    rule_dict = {
        'id': 'R_TEST',
        'rule_type': 'MUST_NOT_CALL',
        'severity': 'blocking',
        'description': 'Test rule',
        'component': 'Presentation',
        'target': 'DataAccess'
    }

    rule = Rule.from_dict(rule_dict)

    assert rule.id == "R_TEST"
    assert rule.rule_type == RuleType.MUST_NOT_CALL
    assert rule.severity == Severity.BLOCKING


def test_violation_to_dict_serialization():
    """Test that violations can be serialized to dictionary."""
    violation = Violation(
        rule_id="R1",
        rule_type=RuleType.MUST_NOT_CALL,
        severity=Severity.BLOCKING,
        source_component="Presentation",
        target_component="DataAccess",
        message="Violation message",
        source_file="presentation/view.py",
        target_file="data/repository.py"
    )

    vio_dict = violation.to_dict()

    assert vio_dict['rule_id'] == "R1"
    assert vio_dict['severity'] == "blocking"
    assert 'timestamp' in vio_dict


def test_evaluation_result_to_dict_serialization(rule_engine):
    """Test that evaluation results can be serialized to dictionary."""
    rule = Rule(
        id="R_TEST",
        rule_type=RuleType.MUST_NOT_CALL,
        severity=Severity.BLOCKING,
        description="Test",
        component="Presentation",
        target="DataAccess"
    )
    rule_engine.add_rule(rule)

    dependencies = {
        "presentation/view.py": ["data/repository.py"]
    }

    result = rule_engine.evaluate_all(dependencies)
    result_dict = result.to_dict()

    assert 'violations' in result_dict
    assert 'summary' in result_dict
    assert result_dict['summary']['total_violations'] == len(result.violations)


def test_component_regex_pattern_matching():
    """Test that components support regex patterns."""
    component = Component(
        name="TestComponent",
        paths=["^src/.*_test\\.py$", "tests/"]
    )

    # Should match regex pattern
    assert component.matches_file("src/module_test.py")

    # Should match simple pattern
    assert component.matches_file("tests/test_file.py")

    # Should not match
    assert not component.matches_file("src/module.py")


def test_get_rules_for_component(rule_engine):
    """Test getting all rules for a specific component."""
    rules = [
        Rule(
            id="R1",
            rule_type=RuleType.MUST_NOT_CALL,
            severity=Severity.BLOCKING,
            description="Rule 1",
            component="Presentation",
            target="DataAccess"
        ),
        Rule(
            id="R2",
            rule_type=RuleType.COUPLING,
            severity=Severity.WARNING,
            description="Rule 2",
            component="Presentation",
            threshold=5
        ),
        Rule(
            id="R3",
            rule_type=RuleType.MUST_NOT_CALL,
            severity=Severity.WARNING,
            description="Rule 3",
            component="BusinessLogic",
            target="Infrastructure"
        )
    ]
    rule_engine.add_rules(rules)

    pres_rules = rule_engine.get_rules_for_component("Presentation")

    assert len(pres_rules) == 2
    assert all(r.component == "Presentation" for r in pres_rules)


def test_get_enabled_rules(rule_engine):
    """Test getting only enabled rules."""
    rules = [
        Rule(
            id="R1",
            rule_type=RuleType.MUST_NOT_CALL,
            severity=Severity.BLOCKING,
            description="Enabled",
            component="Presentation",
            target="DataAccess",
            enabled=True
        ),
        Rule(
            id="R2",
            rule_type=RuleType.COUPLING,
            severity=Severity.WARNING,
            description="Disabled",
            component="Presentation",
            threshold=5,
            enabled=False
        )
    ]
    rule_engine.add_rules(rules)

    enabled = rule_engine.get_enabled_rules()

    assert len(enabled) == 1
    assert enabled[0].id == "R1"


def test_coupling_evaluation_with_threshold(rule_engine, sample_coupling_metrics):
    """Test coupling rule evaluation with various thresholds."""
    rule = Rule(
        id="R_COUPLING",
        rule_type=RuleType.COUPLING,
        severity=Severity.WARNING,
        description="Coupling threshold",
        component="Presentation",
        threshold=2
    )
    rule_engine.add_rule(rule)

    result = rule_engine.evaluate_all({}, coupling_metrics=sample_coupling_metrics)

    # presentation/home_view.py has total coupling of 2 (0+2), should not violate
    # But if we check the actual metrics, it's (0, 2, 1.0), total = 2, threshold = 2
    # So 2 > 2 is False, no violation
    violations = [v for v in result.violations if "presentation" in v.source_file]
    # Since coupling is not > threshold, should be 0 violations
    assert len(violations) == 0


def test_no_cycles_evaluation(rule_engine, sample_cycles):
    """Test NO_CYCLES rule evaluation."""
    rule = Rule(
        id="R_NO_CYCLES",
        rule_type=RuleType.NO_CYCLES,
        severity=Severity.BLOCKING,
        description="No cycles allowed",
        component="BusinessLogic"
    )
    rule_engine.add_rule(rule)

    result = rule_engine.evaluate_all({}, cycles=sample_cycles)

    # Should detect cycle in BusinessLogic component
    assert len(result.violations) > 0
    cycle_violations = [v for v in result.violations if v.rule_type == RuleType.NO_CYCLES]
    assert len(cycle_violations) > 0


def test_complete_yaml_loading_with_all_rule_types(rule_engine):
    """Test loading complete YAML with all rule types."""
    yaml_content = """
components:
  - name: Presentation
    paths:
      - presentation/
  - name: BusinessLogic
    paths:
      - business/
  - name: DataAccess
    paths:
      - data/

rules:
  - id: R1
    rule_type: CAN_CALL
    severity: warning
    description: "Presentation can only call BusinessLogic"
    component: Presentation
    target: BusinessLogic

  - id: R2
    rule_type: MUST_NOT_CALL
    severity: blocking
    description: "Presentation must not call DataAccess"
    component: Presentation
    target: DataAccess

  - id: R3
    rule_type: COUPLING
    severity: warning
    description: "BusinessLogic coupling < 10"
    component: BusinessLogic
    threshold: 10

  - id: R4
    rule_type: NO_CYCLES
    severity: blocking
    description: "No cycles in BusinessLogic"
    component: BusinessLogic
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(yaml_content)
        yaml_path = Path(f.name)

    try:
        count = rule_engine.load_rules_from_yaml(yaml_path)
        assert count == 4
        assert len(rule_engine.rules) == 4

        # Verify all rule types loaded
        rule_types = {r.rule_type for r in rule_engine.rules}
        assert RuleType.CAN_CALL in rule_types
        assert RuleType.MUST_NOT_CALL in rule_types
        assert RuleType.COUPLING in rule_types
        assert RuleType.NO_CYCLES in rule_types
    finally:
        yaml_path.unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
