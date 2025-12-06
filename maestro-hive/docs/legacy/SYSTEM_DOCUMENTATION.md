# Maestro DDF Tri-Modal System Documentation

**Version**: 1.0.0
**Date**: 2025-10-14
**Status**: Test Infrastructure Complete, Production 25% Ready

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Core Components](#core-components)
4. [Usage Guide](#usage-guide)
5. [Testing Guide](#testing-guide)
6. [API Reference](#api-reference)
7. [Integration Patterns](#integration-patterns)
8. [Deployment Guide](#deployment-guide)

---

## System Overview

### What is DDF Tri-Modal?

The **DDF Tri-Modal System** is a comprehensive quality assurance framework for AI-driven software development workflows. It combines three validation streams:

```
┌─────────────────────────────────────────────────────────────┐
│                    DDF TRI-MODAL SYSTEM                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│  │     DDE     │  │     BDV     │  │     ACC     │       │
│  │ Dependency  │  │  Behavior   │  │Architecture │       │
│  │   Driven    │  │   Driven    │  │ Conformance │       │
│  │  Execution  │  │ Validation  │  │  Checking   │       │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘       │
│         │                │                │               │
│         └────────────────┴────────────────┘               │
│                          │                                │
│                  ┌───────▼────────┐                       │
│                  │  CONVERGENCE   │                       │
│                  │    VERDICT     │                       │
│                  └────────────────┘                       │
└─────────────────────────────────────────────────────────────┘
```

### Three Validation Streams

#### 1. DDE (Dependency-Driven Execution)
**Purpose**: Orchestrate workflow execution with contracts and gates

**Key Features**:
- Execution manifest validation
- Interface scheduling
- Capability routing
- Contract enforcement
- Phase gate validation
- Artifact stamping
- Comprehensive audit trail

#### 2. BDV (Behavior-Driven Validation)
**Purpose**: Validate behavior through executable specifications

**Key Features**:
- Gherkin feature parsing (Given/When/Then)
- Step definition registry with decorators
- Contract validation via scenarios
- HTTP client integration
- Async step support
- Data table handling

#### 3. ACC (Architectural Conformance Checking)
**Purpose**: Enforce architectural rules and standards

**Key Features**:
- Import graph analysis
- Rule engine with custom policies
- Multi-level suppression system
- Coupling analysis
- Dependency cycle detection
- Architecture diff tracking

---

## Architecture

### High-Level Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   CLI Tool   │  │  Web UI      │  │   API Client │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
└─────────┼──────────────────┼──────────────────┼─────────────────┘
          │                  │                  │
┌─────────▼──────────────────▼──────────────────▼─────────────────┐
│                         API LAYER                                │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              FastAPI Gateway (TODO)                       │  │
│  │  - Authentication / Authorization                         │  │
│  │  - Rate Limiting                                          │  │
│  │  - Request Validation                                     │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────┬────────────────────────────────────────────────────────┘
          │
┌─────────▼──────────────────────────────────────────────────────┐
│                    ORCHESTRATION LAYER                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Workflow Coordinator                                    │   │
│  │  - DAG Execution                                         │   │
│  │  - Phase Management                                      │   │
│  │  - Dependency Resolution                                 │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────┬───────────────┬────────────────┬───────────────────────┘
          │               │                │
┌─────────▼────────┐ ┌───▼────────┐ ┌─────▼──────────┐
│   DDE ENGINE     │ │ BDV ENGINE  │ │  ACC ENGINE    │
├──────────────────┤ ├─────────────┤ ├────────────────┤
│ - Executor       │ │ - Parser    │ │ - Analyzer     │
│ - Validator      │ │ - Registry  │ │ - Rule Engine  │
│ - Auditor        │ │ - Runner    │ │ - Suppressor   │
│ - Gate Keeper    │ │ - Reporter  │ │ - Differ       │
└─────────┬────────┘ └─────┬───────┘ └────────┬───────┘
          │                │                  │
┌─────────▼────────────────▼──────────────────▼───────────────────┐
│                    CONVERGENCE LAYER                             │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Tri-Modal Verdict Engine                                │   │
│  │  - 8-Case Truth Table                                    │   │
│  │  - Confidence Scoring                                    │   │
│  │  - Conflict Resolution                                   │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────┬────────────────────────────────────────────────────────┘
          │
┌─────────▼──────────────────────────────────────────────────────┐
│                      DATA LAYER                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  PostgreSQL  │  │     Redis    │  │  File System │         │
│  │  (Contracts) │  │    (Cache)   │  │  (Artifacts) │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└────────────────────────────────────────────────────────────────┘
```

### Component Directory Structure

```
maestro-hive/
├── dde/                      # DDE (Dependency-Driven Execution)
│   ├── executor.py           # ✅ Core execution engine (production)
│   ├── validator.py          # ✅ Contract validation (production)
│   ├── auditor.py            # ✅ Audit trail system (593 lines)
│   ├── gate_keeper.py        # ⚠️  Phase gate enforcement (partial)
│   ├── capability_router.py  # ⚠️  Capability routing (partial)
│   └── manifest_loader.py    # ⚠️  Manifest parsing (partial)
│
├── bdv/                      # BDV (Behavior-Driven Validation)
│   ├── step_registry.py      # ✅ Step definitions (436 lines)
│   ├── gherkin_parser.py     # ✅ Feature file parser (production)
│   ├── runner.py             # ⚠️  Test execution (partial)
│   ├── contract_validator.py # ⚠️  Contract checking (partial)
│   └── reporter.py           # ⚠️  Test reporting (partial)
│
├── acc/                      # ACC (Architectural Conformance)
│   ├── suppression_system.py # ✅ Violation suppression (628 lines)
│   ├── import_graph.py       # ✅ Import analysis (production)
│   ├── rule_engine.py        # ✅ Rule evaluation (production)
│   ├── coupling_analyzer.py  # ⚠️  Coupling metrics (partial)
│   ├── cycle_detector.py     # ⚠️  Dependency cycles (partial)
│   └── arch_differ.py        # ⚠️  Architecture diff (partial)
│
├── tri_audit/                # Tri-Modal Convergence
│   ├── verdict_engine.py     # ⚠️  8-case truth table (partial)
│   ├── confidence_scorer.py  # ⚠️  Confidence calculation (partial)
│   └── conflict_resolver.py  # ⚠️  Conflict handling (partial)
│
├── tests/                    # Test Suite (1,000+ tests)
│   ├── dde/                  # DDE tests (400+ tests) ✅
│   ├── bdv/                  # BDV tests (250+ tests) ✅
│   ├── acc/                  # ACC tests (250+ tests) ✅
│   └── e2e/                  # E2E tests (100+ tests) ⚠️  Mocked
│
└── docs/                     # Documentation
    ├── adr/                  # Architecture Decision Records
    └── guides/               # User guides

Legend:
✅ Production Ready (exists and works)
⚠️  Partial (exists but incomplete)
❌ Not Implemented (stub or missing)
```

---

## Core Components

### 1. DDE (Dependency-Driven Execution)

#### DDE Auditor (`dde/auditor.py`)

**Status**: ✅ Production Ready (593 lines)

**Purpose**: Comprehensive audit trail for workflow execution

**Key Classes**:

```python
from dde.auditor import WorkflowAuditor, AuditEvent, AuditLevel

# Initialize auditor
auditor = WorkflowAuditor(
    session_id="workflow_123",
    output_dir="./audit_logs"
)

# Log events
auditor.log_event(
    level=AuditLevel.INFO,
    category="execution",
    message="Starting phase: requirements",
    metadata={"phase": "requirements", "status": "started"}
)

# Generate reports
report = auditor.generate_report()
print(f"Total events: {report['summary']['total_events']}")

# Export audit trail
auditor.export_json("audit_trail.json")
auditor.export_csv("audit_trail.csv")
```

**Features**:
- Structured event logging
- Session-based tracking
- Multiple export formats (JSON, CSV, HTML)
- Event filtering and search
- Analytics and metrics
- Timeline visualization

#### DDE Validator (`dde/validator.py`)

**Status**: ⚠️ Partial Implementation

**Purpose**: Validate contracts and phase gates

```python
from dde.validator import ContractValidator, PhaseGateValidator

# Contract validation
validator = ContractValidator()
result = validator.validate_contract(
    contract_id="contract_123",
    artifacts=["requirements.md", "user_stories.md"],
    metadata={"phase": "requirements"}
)

if result.is_valid:
    print("Contract satisfied!")
else:
    print(f"Violations: {result.violations}")
```

### 2. BDV (Behavior-Driven Validation)

#### BDV Step Registry (`bdv/step_registry.py`)

**Status**: ✅ Production Ready (436 lines)

**Purpose**: Decorator-based step definition system for Gherkin scenarios

**Quick Start**:

```python
from bdv.step_registry import StepRegistry, Context, StepType

# Create registry
registry = StepRegistry()

# Define steps using decorators
@registry.given('I have {count:int} items in my cart')
def step_impl(context: Context, count: int):
    context.cart_items = count

@registry.when('I search for "{query}"')
def step_impl(context: Context, query: str):
    # Use built-in HTTP client
    response = context.http.get(f"/api/search?q={query}")
    context.search_results = response.json()

@registry.then('I should see {count:int} results')
def step_impl(context: Context, count: int):
    assert len(context.search_results) == count

# Execute steps
context = Context()
registry.execute_step(
    "I have 5 items in my cart",
    StepType.GIVEN,
    context
)
print(context.cart_items)  # 5
```

**Pattern Support**:

```python
# Integer parameters
@registry.given('I have {count:int} items')
def step(context, count: int):
    ...

# Float parameters
@registry.then('response time is {time:float} seconds')
def step(context, time: float):
    ...

# String parameters (word)
@registry.when('I select {option} from menu')
def step(context, option: str):
    ...

# Quoted strings (any characters)
@registry.when('I enter "{text}"')
def step(context, text: str):
    ...

# Async steps
@registry.when('I call async API')
async def step(context):
    result = await context.async_http.get("/api/endpoint")
    ...

# Data tables
@registry.given('the following users exist')
def step(context, data_table):
    users = data_table.as_dicts()
    for user in users:
        create_user(user['name'], user['email'])
```

**Context Object**:

```python
context = Context()

# Set/get attributes
context.user_id = 123
context.search_query = "test"

# Use HTTP clients
response = context.http.get("https://api.example.com")  # Sync
response = await context.async_http.get("https://api.example.com")  # Async

# Check existence
if 'user_id' in context:
    print(context.user_id)

# Get with default
value = context.get('missing_key', default='N/A')

# Clear context
context.clear()
```

#### BDV Gherkin Parser (`bdv/gherkin_parser.py`)

**Status**: ✅ Production Ready

**Purpose**: Parse .feature files into executable scenarios

```python
from bdv.gherkin_parser import GherkinParser

parser = GherkinParser()
feature = parser.parse_file("tests/features/search.feature")

print(f"Feature: {feature.name}")
for scenario in feature.scenarios:
    print(f"  Scenario: {scenario.name}")
    for step in scenario.steps:
        print(f"    {step.keyword} {step.text}")
```

**Example Feature File**:

```gherkin
Feature: User Authentication
  As a user
  I want to log in securely
  So that I can access my account

  Scenario: Successful login
    Given I am on the login page
    When I enter "user@example.com" as username
    And I enter "password123" as password
    And I click the login button
    Then I should see my dashboard
    And I should see "Welcome back!"

  Scenario: Failed login
    Given I am on the login page
    When I enter "wrong@example.com" as username
    And I enter "wrongpass" as password
    And I click the login button
    Then I should see an error message
    And I should remain on the login page
```

### 3. ACC (Architectural Conformance Checking)

#### ACC Suppression System (`acc/suppression_system.py`)

**Status**: ✅ Production Ready (628 lines)

**Purpose**: Advanced multi-level suppression for architectural violations

**Quick Start**:

```python
from acc.suppression_system import (
    SuppressionManager,
    SuppressionEntry,
    SuppressionLevel,
    Violation
)

# Create manager
manager = SuppressionManager()

# Add suppressions at different levels
# 1. Violation-level (most specific)
manager.add_suppression(SuppressionEntry(
    level=SuppressionLevel.VIOLATION,
    rule_id="import-cycle",
    file_path="src/models/user.py",
    line_number=42,
    reason="Known cycle, will fix in v2.0",
    author="john@example.com"
))

# 2. File-level
manager.add_suppression(SuppressionEntry(
    level=SuppressionLevel.FILE,
    rule_id="max-complexity",
    file_path="src/legacy/parser.py",
    reason="Legacy code, refactor planned"
))

# 3. Directory-level
manager.add_suppression(SuppressionEntry(
    level=SuppressionLevel.DIRECTORY,
    rule_id="no-star-imports",
    directory_path="tests/",
    reason="Test files allow star imports"
))

# 4. Rule-level (least specific, global)
manager.add_suppression(SuppressionEntry(
    level=SuppressionLevel.RULE,
    rule_id="line-too-long",
    reason="Using 120 char limit instead of 80"
))

# Check if violation is suppressed
violation = Violation(
    rule_id="import-cycle",
    file_path="src/models/user.py",
    line_number=42,
    message="Circular import detected"
)

match = manager.is_suppressed(violation)
if match.is_suppressed:
    print(f"Suppressed by: {match.matched_entry.reason}")
    print(f"Suppression level: {match.level}")
else:
    print("Not suppressed - must fix!")
```

**Suppression Precedence**:

```
1. Violation-level (exact line in exact file)
   ↓
2. File-level (any violation in this file)
   ↓
3. Directory-level (any violation in this directory tree)
   ↓
4. Rule-level (any violation of this rule globally)
```

**Pattern Matching**:

```python
# Wildcard patterns
manager.add_suppression(SuppressionEntry(
    level=SuppressionLevel.FILE,
    rule_id="*",  # All rules
    file_pattern="**/generated/*.py"  # All generated files
))

# Multiple patterns
manager.add_suppression(SuppressionEntry(
    level=SuppressionLevel.DIRECTORY,
    rule_id="import-order",
    directory_pattern="tests/**/*"  # All test subdirectories
))
```

**Expiration**:

```python
from datetime import datetime, timedelta

# Time-based expiration
manager.add_suppression(SuppressionEntry(
    level=SuppressionLevel.FILE,
    rule_id="security-issue",
    file_path="src/api/auth.py",
    reason="Temporary workaround for hotfix",
    expires_at=datetime.now() + timedelta(days=7),
    author="oncall@example.com"
))

# Expired suppressions are automatically ignored
```

**Audit Trail**:

```python
# Track who, when, why
suppression = SuppressionEntry(
    level=SuppressionLevel.FILE,
    rule_id="complexity",
    file_path="src/core.py",
    reason="Complex algorithm, well-tested",
    author="alice@example.com",
    jira_ticket="ARCH-123"
)

# View audit info
print(f"Created: {suppression.created_at}")
print(f"Author: {suppression.author}")
print(f"Reason: {suppression.reason}")
print(f"Ticket: {suppression.jira_ticket}")
```

**Performance**:

```python
# Built-in caching for high-volume checking
manager = SuppressionManager()
manager.load_from_file(".suppressions.yaml")

# First check builds cache
for violation in violations:  # 10,000 violations
    result = manager.is_suppressed(violation, use_cache=True)

# Performance: ~10,000 violations in 1.1 seconds
```

**Export/Import**:

```python
# Export to file
manager.export_yaml(".suppressions.yaml")
manager.export_json("suppressions.json")

# Import from file
manager.load_from_file(".suppressions.yaml")

# Merge from another manager
manager.merge(other_manager, prefer_newer=True)
```

#### ACC Import Graph (`acc/import_graph.py`)

**Status**: ✅ Production Ready

**Purpose**: Analyze Python import dependencies

```python
from acc.import_graph import ImportGraphBuilder

builder = ImportGraphBuilder()
graph = builder.build_graph(
    root_dir="src/",
    exclude_patterns=["*/tests/*", "*/migrations/*"]
)

# Find cycles
cycles = graph.find_cycles()
if cycles:
    print(f"Found {len(cycles)} import cycles:")
    for cycle in cycles:
        print(f"  {' -> '.join(cycle)}")

# Calculate coupling
coupling = graph.calculate_coupling("src/models/user.py")
print(f"Efferent coupling: {coupling.efferent}")  # Dependencies
print(f"Afferent coupling: {coupling.afferent}")  # Dependents
```

#### ACC Rule Engine (`acc/rule_engine.py`)

**Status**: ✅ Production Ready

**Purpose**: Evaluate architectural rules

```python
from acc.rule_engine import RuleEngine, Rule, RuleResult

engine = RuleEngine()

# Define custom rule
@engine.rule("no-test-imports-in-prod")
def check_no_test_imports(node, context):
    if node.file_path.startswith("src/"):
        for imp in node.imports:
            if "test" in imp.module:
                return RuleResult(
                    rule_id="no-test-imports-in-prod",
                    passed=False,
                    message=f"Production code imports test module: {imp.module}",
                    file_path=node.file_path,
                    line_number=imp.line
                )
    return RuleResult(rule_id="no-test-imports-in-prod", passed=True)

# Run rules
results = engine.evaluate_all(graph)
failed = [r for r in results if not r.passed]
print(f"Failed rules: {len(failed)}")
```

---

## Usage Guide

### Running Tests

#### Run All Tests

```bash
# Run complete test suite (1,000+ tests)
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=dde --cov=bdv --cov=acc --cov-report=html

# Run in parallel (fast)
pytest tests/ -n auto
```

#### Run Specific Test Suites

```bash
# DDE tests only
pytest tests/dde/ -v

# BDV tests only
pytest tests/bdv/ -v

# ACC tests only
pytest tests/acc/ -v

# E2E tests only (note: mostly mocked)
pytest tests/e2e/ -v
```

#### Run Specific Test Categories

```bash
# Unit tests
pytest tests/*/unit/ -v

# Integration tests
pytest tests/*/integration/ -v

# E2E tests
pytest tests/e2e/ -v

# Slow tests only
pytest tests/ -m slow

# Quick tests only (skip slow)
pytest tests/ -m "not slow"
```

#### Run Tests with Filters

```bash
# Run tests matching pattern
pytest tests/ -k "suppression" -v

# Run tests for specific component
pytest tests/ -k "audit" -v

# Run failed tests from last run
pytest --lf

# Run failed tests first, then others
pytest --ff
```

### Using Components in Your Code

#### Example 1: DDE Audit Trail

```python
from dde.auditor import WorkflowAuditor, AuditLevel

# Initialize auditor for workflow
auditor = WorkflowAuditor(
    session_id="workflow_20251014_001",
    workflow_name="dog-marketplace",
    output_dir="./audit_logs"
)

try:
    # Log workflow start
    auditor.log_event(
        level=AuditLevel.INFO,
        category="workflow",
        message="Starting workflow execution",
        metadata={"project": "dog-marketplace", "version": "1.0"}
    )

    # Execute phases...
    for phase in phases:
        auditor.log_event(
            level=AuditLevel.INFO,
            category="phase",
            message=f"Starting phase: {phase}",
            metadata={"phase": phase}
        )

        # Phase execution...

        auditor.log_event(
            level=AuditLevel.INFO,
            category="phase",
            message=f"Completed phase: {phase}",
            metadata={"phase": phase, "duration_ms": 1250}
        )

    # Log success
    auditor.log_event(
        level=AuditLevel.INFO,
        category="workflow",
        message="Workflow completed successfully"
    )

except Exception as e:
    # Log error
    auditor.log_event(
        level=AuditLevel.ERROR,
        category="workflow",
        message=f"Workflow failed: {str(e)}",
        metadata={"error": str(e), "traceback": traceback.format_exc()}
    )

finally:
    # Generate report
    report = auditor.generate_report()
    auditor.export_json(f"audit_{auditor.session_id}.json")
    auditor.export_html(f"audit_{auditor.session_id}.html")
```

#### Example 2: BDV Contract Validation

```python
from bdv.step_registry import StepRegistry, Context, StepType
from bdv.gherkin_parser import GherkinParser

# Initialize
registry = StepRegistry()
parser = GherkinParser()

# Load feature file
feature = parser.parse_file("contracts/requirements_phase.feature")

# Execute scenarios
for scenario in feature.scenarios:
    context = Context()
    print(f"Running: {scenario.name}")

    try:
        for step in scenario.steps:
            registry.execute_step(
                step.text,
                StepType(step.keyword.lower()),
                context,
                data_table=step.data_table
            )
        print("✅ PASS")

    except AssertionError as e:
        print(f"❌ FAIL: {e}")

    except ValueError as e:
        print(f"⚠️  UNDEFINED: {e}")

    finally:
        context.clear()
```

#### Example 3: ACC Architecture Validation

```python
from acc.import_graph import ImportGraphBuilder
from acc.rule_engine import RuleEngine
from acc.suppression_system import SuppressionManager

# Build import graph
builder = ImportGraphBuilder()
graph = builder.build_graph(
    root_dir="src/",
    exclude_patterns=["*/tests/*"]
)

# Load rules
engine = RuleEngine()
engine.load_rules_from_file(".arch_rules.yaml")

# Load suppressions
suppressor = SuppressionManager()
suppressor.load_from_file(".suppressions.yaml")

# Evaluate rules
results = engine.evaluate_all(graph)

# Filter with suppressions
violations = []
for result in results:
    if not result.passed:
        match = suppressor.is_suppressed(result)
        if not match.is_suppressed:
            violations.append(result)

# Report
if violations:
    print(f"❌ Found {len(violations)} architectural violations:")
    for v in violations:
        print(f"  {v.file_path}:{v.line_number} - {v.message}")
    exit(1)
else:
    print("✅ All architectural rules passed")
    exit(0)
```

---

## Testing Guide

### Test Organization

```
tests/
├── dde/                      # DDE Tests (400+ tests)
│   ├── unit/                 # Pure unit tests
│   │   ├── test_executor.py
│   │   ├── test_validator.py
│   │   └── test_auditor.py
│   ├── integration/          # Component integration
│   │   ├── test_execution_flow.py
│   │   └── test_contract_integration.py
│   └── fixtures/             # Test data
│       └── test_contracts.py
│
├── bdv/                      # BDV Tests (250+ tests)
│   ├── unit/
│   │   ├── test_step_definitions.py  # 32 tests ✅
│   │   ├── test_gherkin_parser.py
│   │   └── test_contract_validation.py
│   └── integration/
│       └── test_end_to_end_scenarios.py
│
├── acc/                      # ACC Tests (250+ tests)
│   ├── unit/
│   │   ├── test_suppression_system.py  # 27 tests ✅
│   │   ├── test_import_graph.py
│   │   └── test_rule_engine.py
│   └── integration/
│       └── test_full_analysis.py
│
└── e2e/                      # E2E Tests (100+ tests)
    ├── test_pilot_projects.py        # 25 tests ⚠️ Mocked
    ├── test_stress_scenarios.py      # 20 tests ⚠️ Mocked
    └── test_full_integration.py      # 15 tests ⚠️ Mocked
```

### Test Patterns

#### Pattern 1: Unit Test (Real Component)

```python
import pytest
from acc.suppression_system import SuppressionManager, SuppressionEntry, Violation

def test_violation_level_suppression():
    """Test that violation-level suppression works correctly"""
    # Arrange
    manager = SuppressionManager()
    suppression = SuppressionEntry(
        level=SuppressionLevel.VIOLATION,
        rule_id="import-cycle",
        file_path="src/models/user.py",
        line_number=42,
        reason="Known issue"
    )
    manager.add_suppression(suppression)

    violation = Violation(
        rule_id="import-cycle",
        file_path="src/models/user.py",
        line_number=42
    )

    # Act
    result = manager.is_suppressed(violation)

    # Assert
    assert result.is_suppressed
    assert result.level == SuppressionLevel.VIOLATION
    assert result.matched_entry == suppression
```

**What's Real**: SuppressionManager, actual logic, real assertions
**What's Not**: No external services, no I/O

#### Pattern 2: Integration Test (Component Interaction)

```python
import pytest
from dde.executor import WorkflowExecutor
from dde.validator import ContractValidator
from dde.auditor import WorkflowAuditor

@pytest.mark.asyncio
async def test_execution_with_validation():
    """Test executor integrates with validator"""
    # Arrange
    auditor = WorkflowAuditor(session_id="test_001")
    validator = ContractValidator()
    executor = WorkflowExecutor(auditor=auditor, validator=validator)

    workflow_config = {
        "phases": ["requirements", "design"],
        "contracts": {...}
    }

    # Act
    result = await executor.execute(workflow_config)

    # Assert
    assert result.status == "completed"
    assert len(auditor.events) > 0
    assert validator.validation_count > 0
```

**What's Real**: Multiple components interacting
**What's Not**: External API calls (mocked)

#### Pattern 3: E2E Test (Mocked Services)

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_full_workflow_execution():
    """Test complete workflow (MOCKED)"""
    # Arrange - Create mocks
    mock_persona_client = AsyncMock()
    mock_persona_client.send_request.return_value = {
        "status": "success",
        "response": "Generated BRD"
    }

    mock_quality_fabric = AsyncMock()
    mock_quality_fabric.validate.return_value = {
        "passed": True,
        "score": 0.85
    }

    # Act - Run workflow with mocks
    result = await run_workflow(
        persona_client=mock_persona_client,
        quality_fabric=mock_quality_fabric
    )

    # Assert
    assert result['status'] == 'success'
    mock_persona_client.send_request.assert_called()
```

**What's Real**: Workflow orchestration logic
**What's Not**: All service calls are mocked

### Running Specific Test Scenarios

#### Scenario 1: Test DDE Audit System

```bash
# Run all audit tests
pytest tests/dde/unit/test_auditor.py -v

# Run specific audit test
pytest tests/dde/unit/test_auditor.py::test_audit_event_logging -v

# Run with audit output
pytest tests/dde/unit/test_auditor.py -v -s
```

#### Scenario 2: Test BDV Step Definitions

```bash
# Run all step definition tests
pytest tests/bdv/unit/test_step_definitions.py -v

# Test specific step pattern
pytest tests/bdv/unit/test_step_definitions.py::test_parameter_extraction -v

# Test async steps
pytest tests/bdv/unit/test_step_definitions.py -k "async" -v
```

#### Scenario 3: Test ACC Suppression

```bash
# Run all suppression tests
pytest tests/acc/unit/test_suppression_system.py -v

# Test specific suppression level
pytest tests/acc/unit/test_suppression_system.py::test_file_level_suppression -v

# Test performance
pytest tests/acc/unit/test_suppression_system.py::test_suppression_performance -v
```

### Test Fixtures

```python
# conftest.py
import pytest
from bdv.step_registry import Context

@pytest.fixture
def context():
    """Provide clean context for each test"""
    ctx = Context()
    yield ctx
    ctx.clear()

@pytest.fixture
def suppression_manager():
    """Provide clean suppression manager"""
    from acc.suppression_system import SuppressionManager
    return SuppressionManager()

@pytest.fixture
def audit_session():
    """Provide audit session"""
    from dde.auditor import WorkflowAuditor
    auditor = WorkflowAuditor(session_id="test_session")
    yield auditor
    # Cleanup handled by auditor
```

---

## API Reference

### DDE API

#### WorkflowAuditor

```python
class WorkflowAuditor:
    """Audit trail for workflow execution"""

    def __init__(
        self,
        session_id: str,
        workflow_name: str = None,
        output_dir: str = "./audit_logs"
    ):
        """Initialize auditor"""

    def log_event(
        self,
        level: AuditLevel,
        category: str,
        message: str,
        metadata: Dict[str, Any] = None
    ) -> AuditEvent:
        """Log an audit event"""

    def generate_report(self) -> Dict[str, Any]:
        """Generate audit report"""

    def export_json(self, file_path: str):
        """Export to JSON"""

    def export_csv(self, file_path: str):
        """Export to CSV"""

    def export_html(self, file_path: str):
        """Export to HTML"""
```

### BDV API

#### StepRegistry

```python
class StepRegistry:
    """Step definition registry"""

    def given(self, pattern: str) -> Callable:
        """Register Given step"""

    def when(self, pattern: str) -> Callable:
        """Register When step"""

    def then(self, pattern: str) -> Callable:
        """Register Then step"""

    def execute_step(
        self,
        step_text: str,
        step_type: StepType,
        context: Context,
        data_table: Optional[DataTable] = None,
        doc_string: Optional[str] = None
    ) -> Any:
        """Execute a step"""

    async def execute_step_async(
        self,
        step_text: str,
        step_type: StepType,
        context: Context,
        data_table: Optional[DataTable] = None,
        doc_string: Optional[str] = None
    ) -> Any:
        """Execute step asynchronously"""
```

#### Context

```python
class Context:
    """Context for sharing state between steps"""

    def set(self, key: str, value: Any):
        """Set value"""

    def get(self, key: str, default: Any = None) -> Any:
        """Get value with default"""

    def clear(self):
        """Clear all data"""

    @property
    def http(self) -> httpx.Client:
        """Get sync HTTP client"""

    @property
    def async_http(self) -> httpx.AsyncClient:
        """Get async HTTP client"""
```

### ACC API

#### SuppressionManager

```python
class SuppressionManager:
    """Manage architectural violation suppressions"""

    def add_suppression(self, entry: SuppressionEntry):
        """Add suppression"""

    def is_suppressed(
        self,
        violation: Violation,
        use_cache: bool = True
    ) -> SuppressionMatch:
        """Check if violation is suppressed"""

    def load_from_file(self, file_path: str):
        """Load from YAML/JSON file"""

    def export_yaml(self, file_path: str):
        """Export to YAML"""

    def export_json(self, file_path: str):
        """Export to JSON"""

    def merge(
        self,
        other: 'SuppressionManager',
        prefer_newer: bool = True
    ):
        """Merge with another manager"""
```

---

## Integration Patterns

### Pattern 1: CI/CD Integration

```yaml
# .github/workflows/quality-check.yml
name: DDF Tri-Modal Quality Check

on: [push, pull_request]

jobs:
  quality-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov

      - name: Run DDE Tests
        run: pytest tests/dde/ -v --cov=dde

      - name: Run BDV Tests
        run: pytest tests/bdv/ -v --cov=bdv

      - name: Run ACC Tests
        run: pytest tests/acc/ -v --cov=acc

      - name: Check Architecture
        run: python -m acc.cli check --fail-on-violations

      - name: Upload Coverage
        uses: codecov/codecov-action@v3
```

### Pattern 2: Pre-commit Hook

```bash
# .git/hooks/pre-commit
#!/bin/bash

echo "Running DDF quality checks..."

# Run quick tests
pytest tests/ -m "not slow" --quiet
if [ $? -ne 0 ]; then
    echo "❌ Tests failed"
    exit 1
fi

# Check architecture
python -m acc.cli check --quick
if [ $? -ne 0 ]; then
    echo "❌ Architecture violations found"
    exit 1
fi

echo "✅ All checks passed"
exit 0
```

### Pattern 3: Local Development

```bash
# Makefile
.PHONY: test test-quick test-all lint arch-check

test-quick:
	pytest tests/ -m "not slow" -v

test-all:
	pytest tests/ -v --cov --cov-report=html

lint:
	ruff check .
	mypy .

arch-check:
	python -m acc.cli check --verbose

quality: test-quick lint arch-check
	@echo "✅ All quality checks passed"
```

---

## Deployment Guide

### Prerequisites

```bash
# Python 3.11+
python3 --version

# PostgreSQL 14+
psql --version

# Redis 7+
redis-cli --version

# Docker (optional)
docker --version
```

### Installation

```bash
# Clone repository
git clone https://github.com/your-org/maestro-platform.git
cd maestro-platform/maestro-hive

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

### Configuration

```bash
# Copy example config
cp config.example.yaml config.yaml

# Edit configuration
vim config.yaml
```

```yaml
# config.yaml
dde:
  audit_log_dir: ./audit_logs
  max_retries: 3
  timeout_seconds: 300

bdv:
  feature_dir: ./features
  step_timeout_seconds: 30

acc:
  suppression_file: .suppressions.yaml
  rules_file: .arch_rules.yaml
  exclude_patterns:
    - "*/tests/*"
    - "*/migrations/*"

database:
  host: localhost
  port: 5432
  database: maestro_contracts
  user: maestro
  password: ${DB_PASSWORD}

redis:
  host: localhost
  port: 6379
  db: 0
```

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov --cov-report=html

# View coverage
open htmlcov/index.html
```

### Production Deployment (TODO)

**Note**: Production deployment is not yet ready. This is the planned approach:

```bash
# 1. Set up infrastructure (TODO)
# - PostgreSQL database
# - Redis cache
# - API servers
# - Load balancer

# 2. Run migrations (TODO)
alembic upgrade head

# 3. Start services (TODO)
docker-compose up -d

# 4. Verify health (TODO)
curl http://localhost:8000/health
```

**Current Status**: Infrastructure setup is 0% complete. See REALITY_ASSESSMENT.md for details.

---

## Troubleshooting

### Common Issues

#### Issue 1: Import Errors

```python
# Error: ModuleNotFoundError: No module named 'dde'

# Solution: Install in development mode
pip install -e .

# Or add to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

#### Issue 2: Test Failures

```bash
# Check test isolation
pytest tests/ --verbose --failed-first

# Clear pytest cache
pytest --cache-clear

# Run with debug output
pytest tests/ -vv -s
```

#### Issue 3: Slow Tests

```bash
# Run only fast tests
pytest tests/ -m "not slow"

# Run in parallel
pytest tests/ -n auto

# Profile slow tests
pytest tests/ --durations=10
```

---

## Additional Resources

- **Architecture Decision Records**: `docs/adr/`
- **Quality Fabric Integration**: `docs/QUALITY_FABRIC_README.md`
- **PostgreSQL Setup**: `docs/POSTGRESQL_INTEGRATION_GUIDE.md`
- **Reality Assessment**: `REALITY_ASSESSMENT.md` (Read this!)
- **Test Results**: `TEST_RESULTS_SUMMARY.md`

---

**Document Version**: 1.0.0
**Last Updated**: 2025-10-14
**Status**: Documentation Complete, Production 25% Ready
**Next Steps**: See REALITY_ASSESSMENT.md for honest assessment
