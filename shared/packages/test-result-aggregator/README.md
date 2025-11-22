# Maestro Test Result Aggregator

Collect, process, and analyze test results from multiple sources.

## Features

- **Result Collection**: Aggregate test results from various test frameworks
- **SQLite Storage**: Persistent storage with efficient querying
- **Analytics**: Advanced analytics with pandas/numpy (optional)
- **Multi-level Aggregation**: Test case, suite, category, service, and orchestration levels
- **Trend Analysis**: Track test result trends over time
- **Report Generation**: Generate comprehensive test reports

## Installation

```bash
# Basic installation
pip install maestro-test-result-aggregator

# With analytics support
pip install maestro-test-result-aggregator[analytics]
```

## Usage

```python
from maestro_test_result_aggregator import TestResultAggregator, ResultStatus

aggregator = TestResultAggregator(db_path="test_results.db")

# Store test result
aggregator.store_result(
    test_id="test_login",
    status=ResultStatus.PASSED,
    duration=1.23,
    metadata={"suite": "auth_tests"}
)

# Get aggregated results
results = aggregator.aggregate_by_suite("auth_tests")
```

## Dependencies

- **Required**: Python 3.11+
- **Optional**:
  - pandas>=2.0.0 (for advanced analytics)
  - numpy>=1.24.0 (for numerical operations)

## License

Proprietary - Maestro Platform Team
