# Maestro Test Adapters

Comprehensive test framework adapters for the Maestro Platform.

## Features

- **Selenium Adapter**: Web automation with Selenium WebDriver
- **Playwright Adapter**: Modern browser automation with Playwright
- **Pytest Adapter**: Enhanced pytest integration
- **Advanced Web Testing**: Complex user journeys and interactions
- **Production Test Adapters**: Production-ready test execution

## Installation

```bash
# Basic installation
pip install maestro-test-adapters

# With Selenium support
pip install maestro-test-adapters[selenium]

# With Playwright support
pip install maestro-test-adapters[playwright]

# With all optional dependencies
pip install maestro-test-adapters[all]
```

## Usage

```python
from maestro_test_adapters import SeleniumAdapter, PlaywrightAdapter

# Use adapters in your tests
adapter = SeleniumAdapter()
# ... test code
```

## Dependencies

- **Required**: Python 3.11+
- **Optional**:
  - selenium>=4.0.0 (for Selenium adapter)
  - playwright>=1.40.0 (for Playwright adapter)

## License

Proprietary - Maestro Platform Team
