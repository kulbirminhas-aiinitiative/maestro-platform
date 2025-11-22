# Maestro Shared Packages - Integration Guide

**Version**: 1.0.0
**Last Updated**: October 26, 2025
**Packages Covered**: 13 (9 existing + 4 new)

---

## Table of Contents

1. [Overview](#overview)
2. [Nexus Configuration](#nexus-configuration)
3. [Installing Packages](#installing-packages)
4. [Week 1 New Packages](#week-1-new-packages)
5. [Migrating Existing Code](#migrating-existing-code)
6. [Docker Integration](#docker-integration)
7. [Troubleshooting](#troubleshooting)
8. [Complete Package Reference](#complete-package-reference)

---

## Overview

The Maestro Platform now has **13 shared packages** available in Nexus PyPI repository:

### Existing Packages (9)
1. maestro-core-logging
2. maestro-core-api
3. maestro-core-config
4. maestro-core-auth
5. maestro-core-db
6. maestro-monitoring
7. maestro-cache
8. maestro-core-messaging

### New Packages - Week 1 (4)
9. **maestro-audit-logger** ← NEW
10. **maestro-test-adapters** ← NEW
11. **maestro-resilience** ← NEW
12. **maestro-test-result-aggregator** ← NEW

---

## Nexus Configuration

### Access Information

```bash
# Nexus Web UI
http://localhost:28081

# PyPI Group Repository (use this for pip)
http://localhost:28081/repository/pypi-group/simple

# PyPI Hosted Repository (where maestro packages are stored)
http://localhost:28081/repository/pypi-hosted/
```

### Credentials

```
Username: admin
Password: DJ6J&hGH!B#u*J
```

---

## Installing Packages

### Method 1: Direct Installation

```bash
# Install a specific package
pip install \
  --index-url http://localhost:28081/repository/pypi-group/simple \
  --trusted-host localhost \
  maestro-audit-logger==1.0.0
```

### Method 2: Configure pip Globally

```bash
# Configure pip to always use Nexus
pip config set global.index-url http://localhost:28081/repository/pypi-group/simple
pip config set global.trusted-host localhost

# Then install normally
pip install maestro-audit-logger==1.0.0
```

### Method 3: Using requirements.txt

```txt
# requirements.txt
--index-url http://localhost:28081/repository/pypi-group/simple
--trusted-host localhost

maestro-audit-logger==1.0.0
maestro-test-adapters[all]==1.0.0
maestro-resilience==1.0.0
maestro-test-result-aggregator[analytics]==1.0.0
```

```bash
pip install -r requirements.txt
```

### Method 4: Using Poetry

Add to `pyproject.toml`:

```toml
[[tool.poetry.source]]
name = "nexus"
url = "http://localhost:28081/repository/pypi-group/simple"
priority = "primary"

[tool.poetry.dependencies]
python = "^3.11"
maestro-audit-logger = "^1.0.0"
maestro-test-adapters = {version = "^1.0.0", extras = ["all"]}
maestro-resilience = "^1.0.0"
maestro-test-result-aggregator = {version = "^1.0.0", extras = ["analytics"]}
```

```bash
poetry install
```

---

## Week 1 New Packages

### 1. maestro-audit-logger

**Purpose**: Comprehensive audit logging with multiple export formats

**Installation**:
```bash
pip install maestro-audit-logger
```

**Basic Usage**:
```python
from maestro_audit_logger import AuditLogger, AuditEvent

# Initialize logger
logger = AuditLogger(output_dir="./audit_logs")

# Log an event
event = AuditEvent(
    event_type="user.login",
    user_id="user123",
    details={"ip": "192.168.1.1"}
)
logger.log(event)

# Export logs
logger.export_to_json("audit_2025.json")
logger.export_to_csv("audit_2025.csv")
```

**Migration from Local Code**:
```python
# BEFORE (maestro-engine local code)
from src.libraries.audit_logger import AuditLogger

# AFTER (using Nexus package)
from maestro_audit_logger import AuditLogger
```

---

### 2. maestro-test-adapters

**Purpose**: Test framework adapters (Selenium, Playwright, Pytest)

**Installation**:
```bash
# Basic (no browser automation)
pip install maestro-test-adapters

# With Selenium
pip install maestro-test-adapters[selenium]

# With Playwright
pip install maestro-test-adapters[playwright]

# With all features
pip install maestro-test-adapters[all]
```

**Basic Usage**:
```python
from maestro_test_adapters import SeleniumAdapter

# Selenium adapter
adapter = SeleniumAdapter()
driver = adapter.create_driver(headless=True)
driver.get("https://example.com")
# ... test code
driver.quit()
```

**Advanced Usage**:
```python
from maestro_test_adapters.advanced_web_testing import AdvancedWebTester

tester = AdvancedWebTester()
await tester.run_user_journey([
    {"action": "navigate", "url": "https://example.com"},
    {"action": "click", "selector": "#login-button"},
    {"action": "type", "selector": "#username", "text": "testuser"}
])
```

**Migration from Local Code**:
```python
# BEFORE (quality-fabric local code)
from services.adapters.test_adapters import SeleniumAdapter
from services.adapters.advanced_web_testing import AdvancedWebTester

# AFTER (using Nexus package)
from maestro_test_adapters import SeleniumAdapter
from maestro_test_adapters.advanced_web_testing import AdvancedWebTester
```

---

### 3. maestro-resilience

**Purpose**: Resilience patterns for fault-tolerant services

**Installation**:
```bash
pip install maestro-resilience
```

**Circuit Breaker**:
```python
from maestro_resilience import CircuitBreaker, CircuitBreakerOpenError

breaker = CircuitBreaker(
    failure_threshold=5,
    timeout=60,
    expected_exception=Exception
)

@breaker
def call_external_service():
    # Your code that might fail
    response = requests.get("https://api.example.com/data")
    return response.json()

try:
    data = call_external_service()
except CircuitBreakerOpenError:
    print("Circuit is open - service is down")
```

**Retry with Backoff**:
```python
from maestro_resilience import retry

@retry(max_attempts=3, delay=1.0, backoff=2.0)
def unreliable_operation():
    # Will retry up to 3 times with exponential backoff
    result = make_api_call()
    return result
```

**Timeout Protection**:
```python
from maestro_resilience import timeout, TimeoutError

@timeout(seconds=5.0)
def long_running_operation():
    # Will be terminated if takes longer than 5 seconds
    process_large_dataset()

try:
    result = long_running_operation()
except TimeoutError:
    print("Operation timed out")
```

**Combining Patterns**:
```python
from maestro_resilience import CircuitBreaker, retry, timeout

breaker = CircuitBreaker(failure_threshold=3, timeout=30)

@breaker
@retry(max_attempts=3, delay=1.0)
@timeout(seconds=10.0)
def robust_api_call():
    return requests.get("https://api.example.com/data").json()
```

**Migration from Local Code**:
```python
# BEFORE (maestro-engine local code)
from src.resilience.circuit_breaker import CircuitBreaker
from src.resilience.retry import retry
from src.resilience.timeout import timeout

# AFTER (using Nexus package)
from maestro_resilience import CircuitBreaker, retry, timeout
```

---

### 4. maestro-test-result-aggregator

**Purpose**: Collect, aggregate, and analyze test results

**Installation**:
```bash
# Basic (no pandas/numpy)
pip install maestro-test-result-aggregator

# With analytics support
pip install maestro-test-result-aggregator[analytics]
```

**Basic Usage**:
```python
from maestro_test_result_aggregator import TestResultAggregator, ResultStatus

# Initialize aggregator
aggregator = TestResultAggregator(db_path="test_results.db")

# Store test result
aggregator.store_result(
    test_id="test_login",
    orchestration_id="orch_001",
    category="auth_tests",
    status=ResultStatus.PASSED,
    duration=1.23,
    metadata={"browser": "chrome", "env": "staging"}
)

# Query results
results = aggregator.get_results_by_category("auth_tests")
summary = aggregator.get_summary(orchestration_id="orch_001")

print(f"Total tests: {summary['total']}")
print(f"Passed: {summary['passed']}")
print(f"Failed: {summary['failed']}")
```

**Advanced Analytics** (requires `[analytics]` extra):
```python
# Get trend analysis
trends = aggregator.analyze_trends(
    category="auth_tests",
    days=30
)

# Generate report
report = aggregator.generate_report(
    orchestration_id="orch_001",
    include_charts=True
)
```

**Migration from Local Code**:
```python
# BEFORE (quality-fabric local code)
from services.core.test_result_aggregator import TestResultAggregator

# AFTER (using Nexus package)
from maestro_test_result_aggregator import TestResultAggregator
```

---

## Migrating Existing Code

### Step 1: Update Dependencies

#### For Poetry Projects

Update `pyproject.toml`:

```toml
[[tool.poetry.source]]
name = "nexus"
url = "http://localhost:28081/repository/pypi-group/simple"
priority = "primary"

[tool.poetry.dependencies]
# Add new packages
maestro-audit-logger = "^1.0.0"
maestro-test-adapters = {version = "^1.0.0", extras = ["all"]}
maestro-resilience = "^1.0.0"
maestro-test-result-aggregator = "^1.0.0"
```

Then:
```bash
poetry lock
poetry install
```

#### For pip Projects

Update `requirements.txt`:

```txt
maestro-audit-logger==1.0.0
maestro-test-adapters[all]==1.0.0
maestro-resilience==1.0.0
maestro-test-result-aggregator==1.0.0
```

Then:
```bash
pip install -r requirements.txt
```

### Step 2: Update Import Statements

Use find and replace in your IDE:

**Quality Fabric**:
```python
# Find
from services.adapters.test_adapters import
from services.core.test_result_aggregator import

# Replace with
from maestro_test_adapters import
from maestro_test_result_aggregator import
```

**Maestro Engine**:
```python
# Find
from src.libraries.audit_logger import
from src.resilience import

# Replace with
from maestro_audit_logger import
from maestro_resilience import
```

### Step 3: Remove Local Code

After verifying everything works:

```bash
# Quality Fabric
rm -rf services/adapters/  # (if only using test_adapters)
rm -f services/core/test_result_aggregator.py

# Maestro Engine
rm -rf src/libraries/audit_logger/
rm -rf src/resilience/
```

### Step 4: Test

```bash
# Run your test suite
pytest

# Verify imports work
python -c "from maestro_audit_logger import AuditLogger; print('✅ OK')"
python -c "from maestro_test_adapters import SeleniumAdapter; print('✅ OK')"
python -c "from maestro_resilience import CircuitBreaker; print('✅ OK')"
python -c "from maestro_test_result_aggregator import TestResultAggregator; print('✅ OK')"
```

---

## Docker Integration

### Update Dockerfile

**Before** (copying wheel files):
```dockerfile
# Copy Maestro shared library wheels
COPY shared-deps/*.whl /tmp/shared-deps/

# Install from local wheels
RUN pip install --no-cache-dir /tmp/shared-deps/*.whl && \
    rm -rf /tmp/shared-deps
```

**After** (using Nexus):
```dockerfile
# Configure Nexus as PyPI index
ARG PYPI_INDEX_URL=http://maestro-nexus:8081/repository/pypi-group/simple
ARG PYPI_TRUSTED_HOST=maestro-nexus

# Install Maestro shared libraries from Nexus
RUN pip install \
    --index-url ${PYPI_INDEX_URL} \
    --trusted-host ${PYPI_TRUSTED_HOST} \
    maestro-core-api==1.0.0 \
    maestro-core-auth==1.0.0 \
    maestro-core-config==1.0.0 \
    maestro-core-db==1.0.0 \
    maestro-core-logging==1.0.0 \
    maestro-monitoring==1.0.0 \
    maestro-audit-logger==1.0.0 \
    maestro-test-adapters[all]==1.0.0 \
    maestro-resilience==1.0.0 \
    maestro-test-result-aggregator==1.0.0
```

### Update docker-compose.yml

Add build args:

```yaml
services:
  quality-fabric:
    build:
      context: ..
      dockerfile: quality-fabric/Dockerfile
      args:
        PYPI_INDEX_URL: http://maestro-nexus:8081/repository/pypi-group/simple
        PYPI_TRUSTED_HOST: maestro-nexus
    depends_on:
      - maestro-nexus
    networks:
      - maestro-network
```

---

## Troubleshooting

### Issue: Package Not Found

```
ERROR: Could not find a version that satisfies the requirement maestro-audit-logger
```

**Solution**:
1. Verify Nexus is running: `docker ps | grep nexus`
2. Check package exists: `curl http://localhost:28081/repository/pypi-hosted/simple/maestro-audit-logger/`
3. Verify pip configuration:
   ```bash
   pip config list
   ```

### Issue: Import Errors

```python
ImportError: cannot import name 'AuditLogger' from 'maestro_audit_logger'
```

**Solution**:
1. Verify package installed: `pip show maestro-audit-logger`
2. Check Python path: `python -c "import maestro_audit_logger; print(maestro_audit_logger.__file__)"`
3. Reinstall: `pip install --force-reinstall maestro-audit-logger`

### Issue: Docker Build Fails

```
ERROR: Could not find a version that satisfies the requirement maestro-audit-logger
```

**Solution**:
1. Ensure `maestro-nexus` is on same Docker network
2. Check DNS resolution inside container:
   ```dockerfile
   RUN ping -c 1 maestro-nexus || echo "Cannot reach nexus"
   ```
3. Use localhost for local builds:
   ```bash
   docker build --build-arg PYPI_INDEX_URL=http://host.docker.internal:28081/repository/pypi-group/simple .
   ```

### Issue: SSL/TLS Errors

```
WARNING: Retrying (Retry(total=4, connect=None, read=None, redirect=None, status=None))
```

**Solution**:
Always use `--trusted-host` for local Nexus:
```bash
pip install --trusted-host localhost maestro-audit-logger
```

---

## Complete Package Reference

### All 13 Packages Available

| Package | Version | Purpose | Install Command |
|---------|---------|---------|-----------------|
| maestro-core-logging | 1.0.0 | Logging framework | `pip install maestro-core-logging` |
| maestro-core-api | 1.0.0 | API utilities | `pip install maestro-core-api` |
| maestro-core-config | 1.0.0 | Configuration management | `pip install maestro-core-config` |
| maestro-core-auth | 1.0.0 | Authentication | `pip install maestro-core-auth` |
| maestro-core-db | 1.0.0 | Database utilities | `pip install maestro-core-db` |
| maestro-monitoring | 1.0.0 | Monitoring/metrics | `pip install maestro-monitoring` |
| maestro-cache | 1.0.0 | Cache interface (Redis, etc.) | `pip install maestro-cache` |
| maestro-core-messaging | 1.0.0 | Message queue utilities | `pip install maestro-core-messaging` |
| **maestro-audit-logger** | **1.0.0** | **Audit logging** | `pip install maestro-audit-logger` |
| **maestro-test-adapters** | **1.0.0** | **Test framework adapters** | `pip install maestro-test-adapters[all]` |
| **maestro-resilience** | **1.0.0** | **Resilience patterns** | `pip install maestro-resilience` |
| **maestro-test-result-aggregator** | **1.0.0** | **Test result analytics** | `pip install maestro-test-result-aggregator[analytics]` |

### Install All Packages

```bash
pip install \
  --index-url http://localhost:28081/repository/pypi-group/simple \
  --trusted-host localhost \
  maestro-core-logging \
  maestro-core-api \
  maestro-core-config \
  maestro-core-auth \
  maestro-core-db \
  maestro-monitoring \
  maestro-cache \
  maestro-core-messaging \
  maestro-audit-logger \
  maestro-test-adapters[all] \
  maestro-resilience \
  maestro-test-result-aggregator[analytics]
```

---

## Next Steps

After integrating Week 1 packages:

1. **Week 2**: Template Repository Service extraction
2. **Week 3**: Infrastructure setup + more packages
3. **Week 4**: Extract 4 more packages (yaml-config, service-registry, workflow-engine, orchestration)
4. **Week 5**: Automation Service (CARS) extraction
5. **Week 6+**: Kubernetes Execution Service extraction

---

## Support

For issues or questions:
- Check Nexus logs: `docker logs maestro-nexus`
- Verify package in Nexus UI: http://localhost:28081
- Contact: Maestro Platform Team

---

*Integration Guide Version 1.0.0*
*Last Updated: October 26, 2025*
*Maestro Platform - Shared Package Initiative*
