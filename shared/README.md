# Shared Libraries - Enterprise Ecosystem

This repository contains enterprise-grade shared libraries for the MAESTRO ecosystem, following industry-standard naming conventions and patterns.

## Ecosystem Overview

```
projects/
├── shared/           # 🏗️ Shared libraries and utilities (this project)
├── maestro/          # 🤖 Core MAESTRO orchestration engine
├── maestro-frontend/ # 🎨 Frontend dashboard and UI components
├── services/         # 🔧 Microservices (intelligence, governance, etc.)
├── quality-fabric/   # 🔍 Quality assurance and testing framework
└── utilities/        # 🛠️ CLI tools and development utilities
```

## Shared Libraries Structure

### Core Infrastructure
- **@maestro/core-logging** - Structured logging with OpenTelemetry
- **@maestro/core-api** - FastAPI framework with enterprise patterns
- **@maestro/core-config** - Configuration management with Pydantic
- **@maestro/core-auth** - Authentication and authorization
- **@maestro/core-db** - Database abstraction layer
- **@maestro/core-messaging** - Event-driven communication

### Specialized Libraries
- **@maestro/audit-engine** - Comprehensive audit and compliance
- **@maestro/monitoring** - Metrics, monitoring, and observability
- **@maestro/workflow-engine** - Business process orchestration
- **@maestro/security-framework** - Security utilities and patterns

## Standards

- **Language**: Python 3.11+
- **Package Manager**: Poetry
- **Code Quality**: Black, isort, mypy, ruff
- **Documentation**: Sphinx + Material theme
- **Testing**: pytest + coverage
- **CI/CD**: GitHub Actions
- **Versioning**: Semantic Versioning (SemVer)

## Installation

```bash
# Install all shared libraries
pip install -e "shared/packages/*"

# Install specific library
pip install -e "shared/packages/core-logging"
```

## Contributing

1. Follow the [Contributing Guide](./CONTRIBUTING.md)
2. Use conventional commits
3. Maintain 90%+ test coverage
4. Document all public APIs

---
*Part of the MAESTRO Enterprise Ecosystem*