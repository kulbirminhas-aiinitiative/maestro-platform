# Security Testing Suite

Comprehensive security testing tools for the Maestro ML Platform.

## 🛠️ Tools Included

1. **Security Auditor** - Automated vulnerability scanning
2. **Load Testing Suite** - Performance and stress testing with Locust
3. **OWASP ZAP Scanner** - Industry-standard security scanning
4. **Tenant Isolation Validator** - Multi-tenant isolation verification
5. **Security Test Suite** - Pytest-based comprehensive testing

## 🚀 Quick Start

### Install Dependencies

```bash
# Core dependencies
pip install pytest pytest-asyncio pytest-cov
pip install locust
pip install python-owasp-zap-v2.4
pip install httpx sqlalchemy

# Or install all at once
pip install -r ../requirements.txt
```

### Run Security Tests

```bash
# 1. Run pytest security suite (fast)
pytest test_security_suite.py -v

# 2. Run security audit
python -c "
from security_testing import SecurityAuditor
import asyncio

async def main():
    auditor = SecurityAuditor(base_url='http://localhost:8000')
    report = await auditor.run_full_audit()
    print(f'Vulnerabilities: {len(report.vulnerabilities)}')
    print(f'Critical: {report.critical_count}')
    print(f'High: {report.high_count}')

asyncio.run(main())
"

# 3. Run tenant isolation validation
python -c "
from security_testing import TenantIsolationValidator
import asyncio

async def main():
    validator = TenantIsolationValidator(api_base_url='http://localhost:8000')
    report = await validator.run_all_tests()
    print(f'Tests: {report.total_tests}')
    print(f'Passed: {report.passed_tests}')
    print(f'Violations: {report.total_violations}')

asyncio.run(main())
"

# 4. Run load tests
locust -f load_testing.py --host=http://localhost:8000 \
       --users 50 --spawn-rate 10 --run-time 5m

# 5. Run OWASP ZAP scan
# First start ZAP
docker run -u zap -p 8090:8090 -d owasp/zap2docker-stable \
    zap.sh -daemon -host 0.0.0.0 -port 8090 \
    -config api.disablekey=true

# Then run scan
python -c "
from security_testing import quick_scan

report = quick_scan('http://localhost:8000')
print(f'Alerts: {len(report.alerts)}')
print(f'High: {report.high_severity_count}')
"
```

## 📁 File Structure

```
security_testing/
├── __init__.py                          # Package exports
├── README.md                            # This file
├── security_audit.py                    # Automated security auditor
├── load_testing.py                      # Locust load testing suite
├── zap_scanner.py                       # OWASP ZAP integration
├── tenant_isolation_validator.py        # Tenant isolation testing
└── test_security_suite.py              # Pytest security tests
```

## 🧪 Testing Tools

### 1. Security Auditor

**Purpose**: Automated vulnerability scanning

**Features**:
- SQL injection detection
- XSS vulnerability scanning
- Authentication bypass testing
- Authorization validation
- Rate limiting tests
- Tenant isolation verification
- Security header validation
- CSRF protection testing

**Example**:
```python
from security_testing import SecurityAuditor
import asyncio

async def main():
    auditor = SecurityAuditor(base_url="http://localhost:8000")
    report = await auditor.run_full_audit()

    # Check results
    if report.critical_count > 0:
        print("CRITICAL vulnerabilities found!")
        exit(1)

    # Save report
    import json
    with open("audit_report.json", "w") as f:
        json.dump(report.to_dict(), f, indent=2)

asyncio.run(main())
```

### 2. Load Testing Suite

**Purpose**: Validate performance and security under load

**User Types**:
- `MaestroMLUser`: General platform usage
- `RateLimitTestUser`: Rate limit validation
- `TenantIsolationTestUser`: Tenant isolation under load
- `PerformanceTestUser`: Performance testing

**Example**:
```bash
# Basic load test
locust -f load_testing.py --host=http://localhost:8000 \
       --users 50 --spawn-rate 10 --run-time 10m

# Stress test
locust -f load_testing.py --host=http://localhost:8000 \
       --users 1000 --spawn-rate 50 --run-time 30m

# Rate limit test
locust -f load_testing.py --host=http://localhost:8000 \
       --users 100 --spawn-rate 20 --run-time 5m \
       RateLimitTestUser

# Web UI mode
locust -f load_testing.py --host=http://localhost:8000
# Open http://localhost:8089
```

### 3. OWASP ZAP Scanner

**Purpose**: Industry-standard security scanning

**Scan Types**:
- Spider: Discover URLs
- Passive: Safe traffic analysis
- Active: Vulnerability detection (intrusive!)
- API: REST API security
- Full: Comprehensive scan

**Example**:
```python
from security_testing import ZAPScanner, quick_scan, comprehensive_scan

# Quick scan (passive only - safe)
report = quick_scan("http://localhost:8000")

# Comprehensive scan (includes active attacks)
report = comprehensive_scan(
    "http://localhost:8000",
    openapi_spec_url="http://localhost:8000/openapi.json"
)

print(f"High: {report.high_severity_count}")
print(f"Medium: {report.medium_severity_count}")
print(f"Low: {report.low_severity_count}")

# Generate reports
scanner = ZAPScanner()
scanner.generate_html_report(report, "security_report.html")
scanner.generate_json_report(report, "security_report.json")
```

### 4. Tenant Isolation Validator

**Purpose**: Validate multi-tenant isolation

**Tests**:
- List API isolation
- GET API isolation
- Create tenant tagging
- Update cross-tenant prevention
- Delete cross-tenant prevention
- Cross-tenant references
- Tenant context switching

**Example**:
```python
from security_testing import TenantIsolationValidator
import asyncio

async def main():
    validator = TenantIsolationValidator(
        api_base_url="http://localhost:8000"
    )

    report = await validator.run_all_tests()

    print(f"Tests run: {report.total_tests}")
    print(f"Passed: {report.passed_tests}")
    print(f"Failed: {report.failed_tests}")
    print(f"Violations: {report.total_violations}")

    # Fail if violations found
    if report.total_violations > 0:
        print("CRITICAL: Tenant isolation violations!")
        for result in report.test_results:
            for violation in result.violations:
                print(f"  - {violation.description}")
        exit(1)

asyncio.run(main())
```

### 5. Security Test Suite (Pytest)

**Purpose**: Comprehensive pytest-based testing

**Test Classes**:
- `TestAuthentication`: Auth mechanisms
- `TestAuthorization`: RBAC & permissions
- `TestRateLimiting`: Rate limit enforcement
- `TestTenantIsolation`: Tenant isolation
- `TestSecurityHeaders`: Security headers
- `TestInputValidation`: Input validation
- `TestSecurityAudit`: Integration tests
- `TestPerformanceSecurity`: Performance tests
- `TestCORSAndCSRF`: CORS & CSRF

**Example**:
```bash
# Run all tests
pytest test_security_suite.py -v

# Run specific class
pytest test_security_suite.py::TestAuthentication -v

# Run with coverage
pytest test_security_suite.py --cov=api --cov-report=html

# Generate report
pytest test_security_suite.py --junitxml=security_report.xml

# Run in parallel
pytest test_security_suite.py -n 4
```

## 🎯 Complete Testing Workflow

### Local Development

```bash
# 1. Run pytest suite
pytest test_security_suite.py -v

# 2. Run security audit
python -m security_testing.security_audit

# 3. Run tenant isolation validation
python -m security_testing.tenant_isolation_validator
```

### Pre-Production

```bash
# 1. Start ZAP
docker run -u zap -p 8090:8090 -d owasp/zap2docker-stable \
    zap.sh -daemon -host 0.0.0.0 -port 8090 \
    -config api.disablekey=true

# 2. Run ZAP scan
python -c "
from security_testing import comprehensive_scan
report = comprehensive_scan(
    'http://staging.example.com',
    openapi_spec_url='http://staging.example.com/openapi.json'
)
print(f'High: {report.high_severity_count}')
"

# 3. Run load tests
locust -f load_testing.py --host=http://staging.example.com \
       --users 500 --spawn-rate 50 --run-time 30m \
       --html load_test_report.html
```

### CI/CD Integration

```yaml
# .github/workflows/security.yml
name: Security Testing

on: [push, pull_request]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.11

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run security tests
        run: |
          pytest security_testing/test_security_suite.py \
                 -v --junitxml=results.xml

      - name: Run security audit
        run: python -m security_testing.security_audit

      - name: Run tenant isolation tests
        run: python -m security_testing.tenant_isolation_validator

      - name: Upload results
        uses: actions/upload-artifact@v2
        with:
          name: security-reports
          path: "*.json"
```

## 📊 Expected Results

### Security Audit
- ✅ 0 critical vulnerabilities
- ✅ 0 high severity vulnerabilities
- ⚠️ 0-2 medium severity (recommendations)
- ℹ️ 0-5 low severity (informational)

### Tenant Isolation
- ✅ 0 isolation violations
- ✅ 100% test pass rate
- ✅ All cross-tenant access blocked

### Load Testing
- ✅ Rate limits enforced
- ✅ p95 < 500ms
- ✅ p99 < 1000ms
- ✅ System handles 1000+ users

### ZAP Scan
- ✅ 0 high risk alerts
- ✅ 0-2 medium risk alerts
- ℹ️ 0-5 informational alerts

### Pytest Suite
- ✅ 50+ tests pass
- ✅ 0 failures
- ✅ >90% coverage

## 🔧 Configuration

### Environment Variables

```bash
# API configuration
export API_BASE_URL="http://localhost:8000"
export OPENAPI_SPEC_URL="http://localhost:8000/openapi.json"

# ZAP configuration
export ZAP_URL="http://localhost:8090"
export ZAP_API_KEY=""  # Optional

# Database (for DB-level tests)
export DATABASE_URL="postgresql://user:pass@localhost/maestro"

# Load testing
export LOCUST_USERS=50
export LOCUST_SPAWN_RATE=10
export LOCUST_RUN_TIME=10m
```

### Custom Configuration

```python
# config.py
SECURITY_CONFIG = {
    "api_base_url": "http://localhost:8000",
    "zap_url": "http://localhost:8090",
    "load_test_users": 50,
    "rate_limit": 1000,  # requests per minute
    "test_tenants": ["tenant-a", "tenant-b", "tenant-c"]
}
```

## 📚 Additional Resources

- [PHASE2_WEEK4_SUMMARY.md](../PHASE2_WEEK4_SUMMARY.md) - Week 4 completion summary
- [SECURITY_GUIDE.md](../enterprise/SECURITY_GUIDE.md) - Security implementation guide
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [OWASP ZAP Docs](https://www.zaproxy.org/docs/)
- [Locust Documentation](https://docs.locust.io/)
- [Pytest Documentation](https://docs.pytest.org/)

## 🐛 Troubleshooting

### ZAP Connection Error

```bash
# Check ZAP is running
docker ps | grep zap

# Restart ZAP
docker restart <zap-container-id>

# Check ZAP logs
docker logs <zap-container-id>
```

### Load Tests Failing

```bash
# Verify API is accessible
curl http://localhost:8000/health

# Check rate limits aren't too restrictive
# Adjust in RateLimitConfig
```

### Pytest Import Errors

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Verify Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Tenant Isolation Tests Failing

```bash
# Ensure tenant isolation middleware is enabled
# Check enterprise/tenancy/__init__.py is imported

# Verify tenant_id column exists on models
# Check alembic migrations
```

## 🤝 Contributing

When adding new security tests:

1. Add test to appropriate class in `test_security_suite.py`
2. Update security audit patterns in `security_audit.py`
3. Add load test scenario in `load_testing.py` if needed
4. Document expected results
5. Update this README

## 📄 License

Part of the Maestro ML Platform. See main project LICENSE.

---

**Version**: 1.0
**Last Updated**: 2025-10-05
**Status**: Production Ready ✅
