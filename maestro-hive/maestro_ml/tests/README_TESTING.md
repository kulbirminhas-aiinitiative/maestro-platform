# ML Platform Phase 1 Testing Guide

## Overview

Comprehensive test suite for validating the Maestro ML Platform Phase 1 infrastructure.

### Test Structure

```
tests/
├── TEST_PLAN_PHASE1.md          # Detailed test plan
├── README_TESTING.md             # This file
├── run_phase1_tests.sh           # Test execution script
├── conftest.py                   # Pytest fixtures (for API tests)
├── integration/                  # Integration tests
│   └── test_phase1_smoke.py      # Smoke tests
└── reports/                      # Test reports (generated)
```

## Quick Start

### 1. Prerequisites

**Required**:
- Minikube installed and running
- kubectl configured
- Python 3.11+
- ML Platform deployed to minikube

**Install test dependencies**:
```bash
pip install pytest pytest-html requests
```

### 2. Run Smoke Tests (2-3 minutes)

Quick validation of all services:

```bash
cd tests
./run_phase1_tests.sh smoke
```

This runs:
- ✅ Service health checks
- ✅ UI accessibility tests
- ✅ Basic API endpoint tests
- ✅ Kubernetes pod status checks

### 3. View Results

```bash
# Open HTML report
open reports/smoke_test_report.html

# Or check console output
```

## Test Types

### 1. Smoke Tests (`smoke`)
**Duration**: 2-3 minutes
**Purpose**: Quick health check of all services
**Run when**: After deployment, before detailed testing

```bash
./run_phase1_tests.sh smoke
```

**Tests**:
- MLflow UI accessible
- MLflow health endpoint
- Feast UI accessible
- Airflow UI accessible
- Airflow health endpoint
- Prometheus UI and targets
- Grafana UI accessible
- Loki ready endpoint
- Container registry API
- Container registry UI
- Kubernetes namespaces exist
- All pods running

### 2. Integration Tests (`integration`)
**Duration**: 10-15 minutes
**Purpose**: Test component interactions
**Run when**: After smoke tests pass

```bash
./run_phase1_tests.sh integration
```

**Tests** (to be added):
- MLflow experiment creation
- Model registration
- Feast feature materialization
- Airflow DAG execution
- Prometheus metric collection
- Loki log aggregation
- Secret synchronization

### 3. End-to-End Tests (`e2e`)
**Duration**: 30-45 minutes
**Purpose**: Test complete workflows
**Run when**: Before production deployment

```bash
./run_phase1_tests.sh e2e
```

**Tests** (to be added):
- Complete ML training pipeline
- Model deployment workflow
- Feature store integration
- Monitoring and alerting
- CI/CD pipeline execution

### 4. All Tests (`all`)
**Duration**: 45-60 minutes
**Purpose**: Comprehensive validation

```bash
./run_phase1_tests.sh all
```

## Test Execution

### Manual Pytest Execution

```bash
# Run specific test file
pytest integration/test_phase1_smoke.py -v

# Run specific test
pytest integration/test_phase1_smoke.py::TestMLflowSmoke::test_mlflow_ui_accessible -v

# Run with markers
pytest -m smoke -v
pytest -m integration -v
pytest -m e2e -v

# Generate HTML report
pytest integration/ -v --html=reports/report.html --self-contained-html

# Run with coverage
pytest integration/ --cov=mlops --cov-report=html
```

### Environment Variables

```bash
# Set minikube IP (auto-detected by default)
export MINIKUBE_IP=$(minikube ip)

# Set service credentials
export AIRFLOW_USER=admin
export AIRFLOW_PASSWORD=admin
export GRAFANA_USER=admin
export GRAFANA_PASSWORD=admin

# Run tests
pytest integration/ -v
```

## Test Results

### Success Output

```
===================================================================
  ML Platform Phase 1 Test Suite
===================================================================
✓ Minikube running at 192.168.49.2
✓ kubectl found
✓ python3 found
✓ Dependencies installed

Running Smoke Tests...
test_mlflow_ui_accessible PASSED
test_mlflow_health_endpoint PASSED
test_feast_ui_accessible PASSED
test_airflow_ui_accessible PASSED
test_airflow_health_endpoint PASSED
test_prometheus_ui_accessible PASSED
test_prometheus_targets PASSED
test_grafana_ui_accessible PASSED
test_loki_ready_endpoint PASSED
test_registry_api_accessible PASSED
test_registry_ui_accessible PASSED
test_ml_platform_namespace_exists PASSED
test_airflow_namespace_exists PASSED
test_logging_namespace_exists PASSED
test_all_pods_running PASSED

===================================================================
✓ All tests passed!
===================================================================
```

### Failure Output

```
test_mlflow_ui_accessible FAILED
AssertionError: MLflow UI returned 502

✗ Some tests failed (exit code: 1)
```

## Troubleshooting

### Minikube Not Running

**Error**:
```
✗ minikube is not running
```

**Fix**:
```bash
minikube start
```

### Service Not Accessible

**Error**:
```
AssertionError: MLflow UI not accessible: Connection refused
```

**Debug**:
```bash
# Check if service is running
kubectl get pods -n ml-platform

# Check service endpoints
kubectl get svc -n ml-platform

# Check logs
kubectl logs -n ml-platform deployment/mlflow

# Port forward manually
kubectl port-forward -n ml-platform svc/mlflow 5000:80
```

### Pod Not Running

**Error**:
```
Pods not in healthy state: ['ml-platform/mlflow-xxx: CrashLoopBackOff']
```

**Debug**:
```bash
# Describe pod
kubectl describe pod -n ml-platform mlflow-xxx

# Check logs
kubectl logs -n ml-platform mlflow-xxx

# Check events
kubectl get events -n ml-platform --sort-by='.lastTimestamp'
```

### Test Dependencies Missing

**Error**:
```
ModuleNotFoundError: No module named 'pytest'
```

**Fix**:
```bash
pip install pytest pytest-html requests mlflow
```

## Adding New Tests

### 1. Create Test File

```python
# tests/integration/test_new_feature.py
import pytest

@pytest.mark.integration
class TestNewFeature:
    """Tests for new feature"""

    def test_feature_works(self, minikube_ip):
        """Test that feature works"""
        url = f"http://{minikube_ip}:30500/api/feature"
        response = requests.get(url)
        assert response.status_code == 200
```

### 2. Add to Test Plan

Update `TEST_PLAN_PHASE1.md` with:
- Test case ID
- Test description
- Steps
- Expected results
- Automation code

### 3. Run Tests

```bash
pytest integration/test_new_feature.py -v
```

## CI/CD Integration

### GitHub Actions

```yaml
# .github/workflows/test-phase1.yml
name: Phase 1 Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Start Minikube
        run: |
          minikube start
          minikube kubectl -- apply -f infrastructure/minikube/

      - name: Run smoke tests
        run: |
          cd tests
          ./run_phase1_tests.sh smoke

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: test-results
          path: tests/reports/
```

## Performance Testing

### Load Testing with Locust

```python
# tests/performance/load_test.py
from locust import HttpUser, task, between

class MLflowUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def list_experiments(self):
        self.client.get("/api/2.0/mlflow/experiments/list")

    @task
    def get_run(self):
        self.client.get("/api/2.0/mlflow/runs/get?run_id=test")
```

**Run**:
```bash
locust -f tests/performance/load_test.py \
  --host http://$(minikube ip):30500 \
  --users 100 \
  --spawn-rate 10 \
  --run-time 2m \
  --headless
```

## Security Testing

### Vulnerability Scanning

```bash
# Scan all container images
trivy image ml-platform/mlflow:latest
trivy image ml-platform/feast:latest
trivy image ml-platform/airflow:latest

# Scan Kubernetes manifests
trivy config infrastructure/kubernetes/
```

### Network Policy Testing

```bash
# Test network isolation
kubectl run test-pod --rm -it --image=busybox -- \
  wget -O- http://mlflow.ml-platform.svc.cluster.local

# Should fail if network policy is enforced
```

## Test Metrics

### Coverage Targets

- **Smoke Tests**: 100% of services
- **Integration Tests**: >90% of component interactions
- **E2E Tests**: >80% of user workflows
- **Code Coverage**: >80% of application code

### Current Status

| Test Type | Tests | Passing | Coverage |
|-----------|-------|---------|----------|
| Smoke | 15 | TBD | 100% |
| Integration | TBD | TBD | TBD |
| E2E | TBD | TBD | TBD |

## Next Steps

1. ✅ Smoke tests implemented
2. ➡️ Add integration tests for:
   - MLflow experiment tracking
   - Feast feature materialization
   - Airflow DAG execution
   - Monitoring metrics collection
   - Logging aggregation
3. ➡️ Add end-to-end tests for:
   - Complete ML training workflow
   - Model deployment pipeline
   - Feature store usage
4. ➡️ Add performance tests
5. ➡️ Add security tests
6. ➡️ Integrate with CI/CD

## References

- [Test Plan](TEST_PLAN_PHASE1.md) - Detailed test cases
- [pytest Documentation](https://docs.pytest.org/)
- [pytest-html Plugin](https://pytest-html.readthedocs.io/)
- [Locust Documentation](https://docs.locust.io/)

---

**Last Updated**: 2025-10-04
**Status**: In Development
