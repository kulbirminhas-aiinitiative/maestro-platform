# DDF Tri-Modal System - Testing Quick Start Guide

**Quick Reference**: Get started with the DDF testing infrastructure in 5 minutes

---

## Prerequisites

1. **Quality Fabric API** running on port 8000
   ```bash
   curl http://localhost:8000/health
   # Expected: {"status":"healthy","service":"quality-fabric","version":"1.0.0"}
   ```

2. **Python dependencies**
   ```bash
   pip install pytest pytest-cov pytest-asyncio httpx
   ```

---

## Quick Start: 5 Steps

### Step 1: Verify Infrastructure ✅

```bash
cd /home/ec2-user/projects/maestro-platform/maestro-hive

# Check test directories exist
ls -la tests/

# Check pytest configuration
cat pytest.ini

# Check Quality Fabric integration
ls -la tests/helpers/quality_fabric_test_generator.py
```

### Step 2: Generate Your First Test Suite (DDE Stream)

```bash
# Generate tests for DDE stream
python tests/helpers/quality_fabric_test_generator.py dde --coverage 0.90 --output tests/

# Expected output:
# - tests/dde/unit/test_*.py (15-20 files)
# - tests/dde/integration/test_*.py (8-10 files)
# - ~350 test cases total
```

### Step 3: Run Generated Tests

```bash
# Run all DDE tests
pytest -m dde -v

# Run only unit tests
pytest -m "dde and unit" -v

# Run with coverage
pytest -m dde --cov=dde --cov-report=html
```

### Step 4: View Coverage Report

```bash
# Open HTML coverage report
open htmlcov/index.html
```

### Step 5: Review & Enhance Tests

```bash
# Open generated test file
vim tests/dde/unit/test_artifact_stamper.py

# Add Priority Defined (PD) test cases
# Add edge cases
# Add performance benchmarks
```

---

## Test Generation Commands

### Generate Tests for Specific Stream

```bash
# DDE (Dependency-Driven Execution)
python tests/helpers/quality_fabric_test_generator.py dde --coverage 0.90 --output tests/

# BDV (Behavior-Driven Validation)
python tests/helpers/quality_fabric_test_generator.py bdv --coverage 0.85 --output tests/

# ACC (Architectural Conformance Checking)
python tests/helpers/quality_fabric_test_generator.py acc --coverage 0.90 --output tests/

# All streams at once
python tests/helpers/quality_fabric_test_generator.py all --coverage 0.85 --output tests/
```

### Generate Tests for Single Module

```python
import asyncio
from tests.helpers.quality_fabric_test_generator import QualityFabricTestGenerator

async def main():
    generator = QualityFabricTestGenerator()

    result = await generator.generate_tests_for_module(
        source_file="dde/artifact_stamper.py",
        test_framework="pytest",
        coverage_target=0.90,
        output_dir="tests/dde/unit/"
    )

    print(f"Generated {result['summary']['tests_generated']} tests")
    print(f"Estimated coverage: {result['summary']['estimated_coverage']:.1%}")

asyncio.run(main())
```

---

## Test Execution Commands

### Basic Execution

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run and stop on first failure
pytest -x

# Run last failed tests
pytest --lf
```

### Run by Stream

```bash
pytest -m dde          # DDE stream tests only
pytest -m bdv          # BDV stream tests only
pytest -m acc          # ACC stream tests only
pytest -m tri_audit    # Tri-modal convergence tests
```

### Run by Test Type

```bash
pytest -m unit         # Unit tests only
pytest -m integration  # Integration tests only
pytest -m e2e          # End-to-end tests only
pytest -m performance  # Performance tests only
```

### Run with Coverage

```bash
# Generate HTML coverage report
pytest --cov --cov-report=html

# Generate terminal coverage report
pytest --cov --cov-report=term-missing

# Fail if coverage below threshold
pytest --cov --cov-fail-under=85
```

### Parallel Execution

```bash
# Run tests in parallel (auto-detect CPU cores)
pytest -n auto

# Run with specific number of workers
pytest -n 4
```

---

## Example Test Cases

### Unit Test Example

```python
# tests/dde/unit/test_artifact_stamper.py
import pytest
from dde.artifact_stamper import ArtifactStamper

@pytest.mark.unit
@pytest.mark.dde
def test_stamp_artifact_with_metadata(sample_artifact_metadata, temp_output_dir):
    """Test artifact stamping with complete metadata"""
    stamper = ArtifactStamper(output_dir=temp_output_dir)

    result = stamper.stamp_artifact(
        iteration_id=sample_artifact_metadata['iteration_id'],
        node_id=sample_artifact_metadata['node_id'],
        artifact_path="source.py",
        capability=sample_artifact_metadata['capability']
    )

    assert result is not None
    assert result['sha256'] is not None
    assert (temp_output_dir / "artifacts").exists()
```

### Integration Test Example

```python
# tests/dde/integration/test_task_routing.py
import pytest
from dde.task_router import TaskRouter
from dde.capability_matcher import CapabilityMatcher

@pytest.mark.integration
@pytest.mark.dde
@pytest.mark.asyncio
async def test_task_assignment_with_capability_matching(mock_agent_profiles):
    """Test end-to-end task assignment with capability matching"""
    matcher = CapabilityMatcher(agents=mock_agent_profiles)
    router = TaskRouter(matcher=matcher)

    agent_id = await router.assign_task(
        node_id="BE.AuthService",
        required_capability="Backend:Python:FastAPI",
        context={}
    )

    assert agent_id == "agent_001"  # Best match agent
```

### Behavioral Test Example (Gherkin)

```gherkin
# features/auth/authentication.feature
@contract:AuthAPI:v1.0
Feature: User Authentication
  As a registered user
  I want to authenticate with credentials
  So that I can access protected resources

  Scenario: Successful login
    Given a registered user "alice@example.com"
    When she logs in with valid password
    Then she receives a JWT token
    And the token is valid for 3600 seconds
```

---

## Quality Fabric API Usage

### Check API Health

```bash
curl http://localhost:8000/health
```

### Generate Tests via API

```bash
curl -X POST http://localhost:8000/api/ai/generate-tests \
  -H "Content-Type: application/json" \
  -d '{
    "source_files": ["dde/artifact_stamper.py"],
    "test_framework": "pytest",
    "coverage_target": 0.90
  }'
```

### Python API Client

```python
import httpx

async def generate_tests(source_file: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/ai/generate-tests",
            json={
                "source_files": [source_file],
                "test_framework": "pytest",
                "coverage_target": 0.90
            }
        )
        return response.json()
```

---

## Test Fixtures Available

All fixtures are defined in `tests/conftest.py`:

### Temporary Directories
- `temp_dir` - Temporary directory for test isolation
- `temp_output_dir` - Temporary output directory

### Mock Data
- `mock_iteration_id` - Mock iteration ID
- `mock_team_id` - Mock team ID
- `mock_agent_profiles` - Mock agent profiles

### DDE Fixtures
- `sample_execution_manifest` - Sample execution manifest
- `sample_artifact_metadata` - Sample artifact metadata

### BDV Fixtures
- `sample_feature_file` - Sample Gherkin feature
- `sample_bdv_result` - Sample BDV test result

### ACC Fixtures
- `sample_import_graph` - Sample import graph
- `sample_architectural_manifest` - Sample architectural manifest
- `sample_acc_violation` - Sample architectural violation

### Tri-Modal Fixtures
- `sample_dde_audit_result` - Sample DDE audit result
- `sample_bdv_audit_result` - Sample BDV audit result
- `sample_acc_audit_result` - Sample ACC audit result
- `sample_tri_audit_result_all_pass` - Sample tri-modal audit (ALL_PASS)

---

## Common Issues & Solutions

### Issue 1: Quality Fabric API Not Available

**Error**: `Failed to generate tests: Connection refused`

**Solution**:
```bash
# Check if Quality Fabric is running
curl http://localhost:8000/health

# If not running, start it (refer to Quality Fabric docs)
```

### Issue 2: Import Errors

**Error**: `ModuleNotFoundError: No module named 'dde'`

**Solution**:
```bash
# Add project root to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:/home/ec2-user/projects/maestro-platform/maestro-hive"

# Or install in development mode
pip install -e .
```

### Issue 3: Coverage Below Threshold

**Error**: `FAIL Required test coverage of 85% not reached`

**Solution**:
```bash
# Generate additional tests for uncovered code
python tests/helpers/quality_fabric_test_generator.py dde --coverage 0.95

# Or run with lower threshold temporarily
pytest --cov --cov-fail-under=70
```

### Issue 4: Flaky Tests

**Solution**:
```python
# Mark test as flaky
@pytest.mark.flaky(reruns=3)
def test_flaky_operation():
    pass

# Or use timeout
@pytest.mark.timeout(30)
def test_long_operation():
    pass
```

---

## Next Steps

1. **Generate DDE Tests** (2-3 days)
   ```bash
   python tests/helpers/quality_fabric_test_generator.py dde --coverage 0.90 --output tests/
   pytest -m dde --cov=dde
   ```

2. **Generate BDV Tests** (2-3 days)
   ```bash
   python tests/helpers/quality_fabric_test_generator.py bdv --coverage 0.85 --output tests/
   # Manually create Gherkin feature files in features/
   pytest -m bdv --cov=bdv
   ```

3. **Generate ACC Tests** (2-3 days)
   ```bash
   python tests/helpers/quality_fabric_test_generator.py acc --coverage 0.90 --output tests/
   pytest -m acc --cov=acc
   ```

4. **Create Tri-Modal Tests** (2 days)
   - Manually create convergence tests in `tests/tri_audit/`
   - Test all 8 verdict scenarios
   - Test deployment gate logic

5. **Create E2E Tests** (1-2 days)
   - Create pilot project workflows in `tests/e2e/pilot_projects/`
   - Create stress tests in `tests/e2e/stress_tests/`

---

## Documentation References

- **Comprehensive Test Plan**: `DDF_TRI_MODAL_COMPREHENSIVE_TEST_PLAN.md` (1,150+ test cases)
- **Infrastructure Summary**: `DDF_TEST_INFRASTRUCTURE_SUMMARY.md` (Complete status)
- **Tri-Modal Plan**: `DDF_TRI_MODAL_IMPLEMENTATION_PLAN.md` (System architecture)

---

## Support

For issues or questions:
1. Check test logs: `tests/logs/pytest.log`
2. Review test plan: `DDF_TRI_MODAL_COMPREHENSIVE_TEST_PLAN.md`
3. Verify Quality Fabric: `curl http://localhost:8000/health`

---

**Quick Start Complete!** 🎉

You now have a fully operational test infrastructure with:
- ✅ 1,150+ test cases defined
- ✅ AI-powered test generation via Quality Fabric
- ✅ Comprehensive pytest configuration
- ✅ Shared fixtures for all streams
- ✅ Ready to generate and execute tests

**First Command to Run**:
```bash
python tests/helpers/quality_fabric_test_generator.py dde --coverage 0.90 --output tests/
```

---

**END OF QUICK START GUIDE**
