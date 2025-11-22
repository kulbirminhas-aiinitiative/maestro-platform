# Maestro YAML Config Parser

Parse YAML configurations into test execution plans for the Maestro Platform.

## Features

- Parse YAML test configurations
- Convert to TestExecutionPlan objects
- Support for quality gates
- Mock service configuration
- Test suite definitions

## Installation

```bash
pip install maestro-yaml-config-parser
```

## Usage

```python
from maestro_yaml_config_parser import YAMLConfigParser

parser = YAMLConfigParser()
config = parser.parse_file("test-config.yaml")
```

## License

Proprietary - Maestro Platform Team
