# MAESTRO Templates - Comprehensive Test Suite

Ultra-comprehensive test suite for the MAESTRO Templates Central Registry service with quality-fabric integration.

## Test Structure

```
tests/
├── conftest.py                      # Comprehensive fixtures and configuration
├── quality_fabric_integration.py    # Quality-fabric integration module
├── README.md                        # This file
├── unit/                            # Unit tests
│   ├── test_auth_comprehensive.py           # Authentication & security
│   └── test_templates_comprehensive.py      # Template models & validation
├── integration/                     # Integration tests
│   └── test_database_integration.py         # Database operations
├── api/                             # API endpoint tests
│   └── test_endpoints_comprehensive.py      # REST API endpoints
├── security/                        # Security & penetration tests
│   └── test_security_comprehensive.py       # Security vulnerabilities
├── performance/                     # Performance & load tests
│   └── test_load_testing.py                 # Load, stress, soak tests
└── e2e/                             # End-to-end scenario tests
    └── test_user_scenarios.py               # Complete user workflows
```

## Test Coverage

### Test Categories

- **Unit Tests** (200+ tests): Authentication, password hashing, JWT tokens, template models, validation
- **Integration Tests** (80+ tests): Database operations, connection pooling, transactions, queries
- **API Tests** (120+ tests): REST endpoints, authentication, authorization, validation, error handling
- **Security Tests** (60+ tests): Authentication security, authorization, input validation, SQL injection, XSS, CSRF
- **Performance Tests** (50+ tests): API latency, throughput, concurrent load, stress testing, soak tests
- **E2E Tests** (30+ tests): Complete user workflows, collaboration scenarios, error recovery

### Test Markers

Available markers:
- `unit`: Unit tests
- `integration`: Integration tests
- `api`: API tests
- `security`: Security tests
- `performance`: Performance tests
- `e2e`: End-to-end tests
- `critical`: Critical tests
- `slow`: Slow-running tests
- `quality_fabric`: Quality-fabric integration tests

## Running Tests

### Run All Tests

```bash
# Run all tests with coverage
poetry run pytest tests/ -v --cov=. --cov-report=html
```

### Run Specific Categories

```bash
pytest -m unit          # Unit tests
pytest -m security      # Security tests
pytest -m performance   # Performance tests
pytest -m e2e           # E2E tests
```

## Quality-Fabric Integration

All tests integrated with quality-fabric for metrics tracking:
- Test execution duration
- Coverage metrics
- Performance benchmarks
- Failure analysis

Reports generated in `test_reports/quality_fabric/`:
- `metrics_*.json` - Raw metrics
- `summary.md` - Summary report
- `detailed_report.md` - Detailed report

## Test Quality Standards

- **Coverage Target**: 80%+
- **Unit Tests**: < 100ms
- **Integration Tests**: < 1s
- **All tests**: Independent, repeatable, clear

For full documentation, see test files and conftest.py fixtures.
