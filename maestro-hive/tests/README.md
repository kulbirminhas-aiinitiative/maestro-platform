# Integration Test Suite

Comprehensive integration tests for the AI-Orchestrated Team Management System.

## Overview

This test suite verifies the three core paradigms and their integration:

1. **Parallel Execution Engine** - MVD, assumptions, contracts, conflicts, convergence
2. **Smart Team Management** - Performance scoring, health analysis, auto-scaling
3. **Elastic Team Model** - Role routing, onboarding, handoffs, phase transitions

## Test Structure

```
tests/
├── conftest.py                    # Pytest fixtures and configuration
├── integration/
│   ├── test_parallel_execution.py      # Parallel execution tests
│   ├── test_smart_team_management.py   # Team management tests
│   ├── test_elastic_team_model.py      # Elastic team tests
│   ├── test_cross_paradigm_integration.py  # Cross-paradigm tests
│   └── test_e2e_workflow.py            # End-to-end workflow
└── utils/
    └── test_helpers.py            # Test utility functions
```

## Prerequisites

### Install Dependencies

```bash
# Core dependencies
pip3 install pytest pytest-asyncio

# System dependencies (from requirements-production.txt)
pip3 install sqlalchemy asyncpg aiosqlite redis anthropic
```

### Start Redis (Required)

```bash
# Option 1: Docker
docker run -d -p 6379:6379 redis:latest

# Option 2: Local install
redis-server

# Verify
redis-cli ping  # Should return "PONG"
```

## Running Tests

### Run All Tests

```bash
cd /path/to/claude_team_sdk/examples/sdlc_team
pytest tests/ -v
```

### Run Specific Test Suites

```bash
# Parallel execution tests only
pytest tests/integration/test_parallel_execution.py -v

# Team management tests only
pytest tests/integration/test_smart_team_management.py -v

# Elastic team model tests only
pytest tests/integration/test_elastic_team_model.py -v

# Cross-paradigm integration tests
pytest tests/integration/test_cross_paradigm_integration.py -v

# End-to-end workflow test
pytest tests/integration/test_e2e_workflow.py -v
```

### Run with Coverage

```bash
pytest tests/ --cov=. --cov-report=html
open htmlcov/index.html
```

### Run Specific Test

```bash
pytest tests/integration/test_parallel_execution.py::TestParallelWorkflowEngine::test_start_parallel_work_streams -v
```

## Test Categories

### 1. Parallel Execution Tests (`test_parallel_execution.py`)

**What it tests:**
- Starting parallel work streams from MVD
- Dependency graph management
- Contract breach detection
- Assumption invalidation
- Convergence workflow (trigger → resolve → complete)
- Impact analysis
- Metrics and reporting

**Key test:**
```python
async def test_convergence_workflow(state_manager, team_id):
    # Creates conflicts → Triggers convergence → Completes resolution
    # Verifies 3-hour convergence completes successfully
```

**Coverage:** ~300 lines, 9 test methods

---

### 2. Smart Team Management Tests (`test_smart_team_management.py`)

**What it tests:**
- 4-dimensional agent performance scoring
- Underperformer detection
- Replacement candidate recommendations
- Team health analysis
- Auto-scaling recommendations
- Team composition policies
- Phase-based team requirements

**Key test:**
```python
async def test_team_health_analysis(state_manager, team_id):
    # Analyzes team with varying performance
    # Verifies health score calculation and recommendations
```

**Coverage:** ~250 lines, 12 test methods

---

### 3. Elastic Team Model Tests (`test_elastic_team_model.py`)

**What it tests:**
- Role creation and assignment
- Role reassignment (seamless handoff)
- Unfilled roles detection
- Onboarding briefing generation
- Knowledge handoff protocol
- Dynamic team manager workflows
- Progressive team scaling
- Phase-based rotation

**Key test:**
```python
async def test_phase_based_rotation(state_manager, team_id):
    # Simulates Requirements → Implementation → Deployment
    # Verifies correct team composition per phase
```

**Coverage:** ~280 lines, 11 test methods

---

### 4. Cross-Paradigm Integration Tests (`test_cross_paradigm_integration.py`)

**What it tests:**
- Conflicts affecting performance scores
- Convergence resolution improving metrics
- Handoffs cleaning up dependencies
- Performance triggering scaling
- Parallel work during team scaling
- Phase transitions with active contracts

**Key test:**
```python
async def test_complete_workflow_integration(state_manager, team_id):
    # Full workflow: team init → parallel exec → conflicts → health check → scaling
    # Verifies all three paradigms work together
```

**Coverage:** ~220 lines, 8 test methods

---

### 5. End-to-End Workflow Test (`test_e2e_workflow.py`)

**What it tests:**
Complete E-Commerce Payment Gateway project simulation:

**Timeline:**
- **Day 0:** Requirements phase (BA + UX)
- **Day 1-2:** Design phase (Architect creates contract)
- **Day 2-4:** Implementation (Parallel: Backend + Frontend)
  - T+30: Backend makes assumption
  - T+45: Frontend makes assumption
  - Day 3: Contract evolution (BREAKING CHANGE)
  - Conflict detected
  - Assumptions invalidated
- **Day 3 (T+180):** Convergence (3-hour team sync)
- **Day 4-5:** Testing (QA added)
- **Day 5:** Deployment (DevOps added)
- **Post-deployment:** Scale down (retire BA, standby Frontend)

**Verifies:**
- All 7 SDLC phases execute correctly
- Parallel execution handles conflicts
- Team scales appropriately
- Performance tracking works
- Knowledge handoffs succeed

**Coverage:** ~400 lines, 1 comprehensive test

---

## Test Fixtures

### Core Fixtures (from `conftest.py`)

| Fixture | Scope | Description |
|---------|-------|-------------|
| `event_loop` | session | Async event loop for tests |
| `db_manager` | function | Test database (SQLite in-memory) |
| `redis_manager` | function | Test Redis connection |
| `state_manager` | function | Initialized StateManager |
| `team_id` | function | Unique team ID per test |
| `test_team` | function | Created team with basic setup |
| `sample_agents` | function | Pre-defined agent data |
| `sample_mvd` | function | Sample Minimum Viable Definition |

### Usage Example

```python
@pytest.mark.asyncio
async def test_my_feature(state_manager, team_id, sample_agents):
    # state_manager is ready to use
    # team_id is unique for this test
    # sample_agents provides test data
    pass
```

## Test Utilities (`test_helpers.py`)

### Helper Functions

```python
# Create test task
task_id = await create_test_task(
    state_manager,
    team_id,
    title="My Task",
    status="ready"
)

# Create test contract
contract = await create_test_contract(
    contract_manager,
    team_id,
    contract_name="MyAPI",
    version="v1.0"
)

# Create test assumption
assumption = await create_test_assumption(
    assumption_tracker,
    team_id,
    made_by_agent="agent_001"
)

# Add test member
member = await add_test_member(
    state_manager,
    team_id,
    "agent_001",
    "backend_developer"
)

# Assertions
assert_metric_in_range(score, 0, 100, "performance_score")
assert_contains_keys(data, ["id", "status", "created_at"])
```

## Expected Test Results

### Success Criteria

When all tests pass, you should see:

```
tests/integration/test_parallel_execution.py::TestParallelWorkflowEngine::test_start_parallel_work_streams PASSED
tests/integration/test_parallel_execution.py::TestParallelWorkflowEngine::test_contract_breach_detection PASSED
tests/integration/test_parallel_execution.py::TestParallelWorkflowEngine::test_convergence_workflow PASSED
... (35+ more tests)

tests/integration/test_e2e_workflow.py::TestECommercePaymentGatewayE2E::test_complete_sdlc_workflow PASSED

==================== 40+ passed in X.XXs ====================
```

### Key Metrics Verified

The tests verify:
- ✅ Parallel work streams start correctly
- ✅ Conflicts are detected with correct severity
- ✅ Convergence completes with actual < estimated rework
- ✅ Performance scores calculated accurately (0-100 range)
- ✅ Underperformers identified correctly
- ✅ Team health score reflects actual state
- ✅ Auto-scaling recommendations are appropriate
- ✅ Role assignments work seamlessly
- ✅ Onboarding briefings contain relevant context
- ✅ Knowledge handoffs track task reassignments
- ✅ Phase transitions scale team correctly
- ✅ End-to-end workflow completes all phases

## Troubleshooting

### Common Issues

**1. Redis Connection Error**
```
ConnectionRefusedError: [Errno 111] Connection refused
```
**Fix:** Start Redis server
```bash
redis-server
```

**2. Import Errors**
```
ModuleNotFoundError: No module named 'parallel_workflow_engine'
```
**Fix:** Run from correct directory
```bash
cd examples/sdlc_team
pytest tests/
```

**3. Async Test Failures**
```
RuntimeError: Event loop is closed
```
**Fix:** Ensure pytest-asyncio is installed
```bash
pip3 install pytest-asyncio
```

**4. Database Lock**
```
sqlite3.OperationalError: database is locked
```
**Fix:** Tests use in-memory DB, this shouldn't happen. If it does, delete test DB files:
```bash
rm test_*.db
```

## Adding New Tests

### Template

```python
import pytest
from your_module import YourClass

@pytest.mark.asyncio
class TestYourFeature:
    """Test your feature"""

    async def test_specific_behavior(self, state_manager, team_id):
        """Test specific behavior"""
        # Arrange
        manager = YourClass(state_manager)

        # Act
        result = await manager.your_method(team_id, ...)

        # Assert
        assert result["status"] == "expected"
        assert len(result["items"]) > 0
```

### Best Practices

1. **Use descriptive test names**: `test_contract_evolution_triggers_conflict_detection`
2. **One assertion per concept**: Test one thing well
3. **Clean test data**: Use fixtures for setup, rely on automatic teardown
4. **Test edge cases**: Empty lists, None values, boundary conditions
5. **Verify error handling**: Test that errors are raised appropriately
6. **Use async properly**: Always mark async tests with `@pytest.mark.asyncio`

## Continuous Integration

### GitHub Actions Example

```yaml
name: Integration Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      redis:
        image: redis
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements-production.txt
          pip install pytest pytest-asyncio pytest-cov

      - name: Run tests
        run: |
          cd examples/sdlc_team
          pytest tests/ -v --cov=. --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Next Steps

After tests pass:

1. **Add unit tests** for individual components
2. **Add performance tests** for scalability
3. **Add load tests** for concurrency
4. **Add security tests** for vulnerabilities
5. **Implement CI/CD** pipeline

## References

- [pytest documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- Main documentation: `COMPREHENSIVE_TEAM_MANAGEMENT.md`
- Audit report: `AUDIT_REPORT.md`
