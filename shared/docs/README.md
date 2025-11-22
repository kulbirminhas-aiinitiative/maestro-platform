# MAESTRO Shared Libraries Documentation

Comprehensive documentation for the MAESTRO enterprise shared libraries ecosystem.

## 📚 Documentation Structure

### Quick Start Guides
- [**Getting Started**](./getting-started.md) - Initial setup and basic usage
- [**Migration Guide**](./migration-guide.md) - Migrating from existing implementations
- [**Examples Repository**](./examples/) - Real-world usage examples

### Library Documentation
- [**Core Logging**](./libraries/core-logging.md) - Structured logging with OpenTelemetry
- [**Core API**](./libraries/core-api.md) - FastAPI framework with enterprise features
- [**Core Config**](./libraries/core-config.md) - Configuration management with validation
- [**Core Auth**](./libraries/core-auth.md) - Authentication and authorization
- [**Core DB**](./libraries/core-db.md) - Database abstraction with SQLAlchemy 2.0
- [**Core Messaging**](./libraries/core-messaging.md) - Event streaming and messaging
- [**Monitoring**](./libraries/monitoring.md) - Observability and metrics

### Developer Guides
- [**Architecture Overview**](./architecture/overview.md) - System architecture and design
- [**Best Practices**](./best-practices.md) - Coding standards and patterns
- [**Testing Guide**](./testing-guide.md) - Testing strategies and frameworks
- [**Performance Guide**](./performance-guide.md) - Optimization and tuning
- [**Security Guide**](./security-guide.md) - Security best practices

### Operations
- [**Deployment Guide**](./deployment/) - Kubernetes, Docker, and cloud deployment
- [**Monitoring & Alerting**](./monitoring/) - Setting up observability
- [**Troubleshooting**](./troubleshooting.md) - Common issues and solutions

### Reference
- [**API Reference**](./api-reference/) - Complete API documentation
- [**Configuration Reference**](./configuration-reference.md) - All configuration options
- [**Changelog**](./CHANGELOG.md) - Version history and changes

## 🚀 Quick Links

### For New Developers
1. **[Getting Started](./getting-started.md)** - Set up your first service
2. **[Examples](./examples/)** - Copy-paste ready code examples
3. **[Best Practices](./best-practices.md)** - Follow proven patterns

### For Migration
1. **[Migration Guide](./migration-guide.md)** - Step-by-step migration process
2. **[Compatibility Matrix](./compatibility.md)** - Version compatibility
3. **[Breaking Changes](./breaking-changes.md)** - Important changes to consider

### For Operations
1. **[Deployment Guide](./deployment/)** - Production deployment
2. **[Monitoring Setup](./monitoring/)** - Observability configuration
3. **[Troubleshooting](./troubleshooting.md)** - Problem resolution

## 📖 Library Overview

| Library | Purpose | Standards | Status |
|---------|---------|-----------|--------|
| **@maestro/core-logging** | Structured logging | Structlog + OpenTelemetry | ✅ Ready |
| **@maestro/core-api** | FastAPI framework | OpenAPI 3.0 + Enterprise patterns | ✅ Ready |
| **@maestro/core-config** | Configuration management | Pydantic + 12-Factor | ✅ Ready |
| **@maestro/core-auth** | Authentication & authorization | OAuth2 + JWT + RBAC | ✅ Ready |
| **@maestro/core-db** | Database abstraction | SQLAlchemy 2.0 + Async | ✅ Ready |
| **@maestro/core-messaging** | Event streaming | Kafka + Redis + AMQP | ✅ Ready |
| **@maestro/monitoring** | Observability | Prometheus + OpenTelemetry | ✅ Ready |

## 💡 Key Benefits

### **Enterprise Standards**
- Industry-proven patterns from Google, Netflix, Uber
- CNCF-compliant observability stack
- Security-first design with OAuth2/JWT
- 12-Factor App methodology

### **Developer Experience**
- Type-safe APIs with Pydantic validation
- Auto-generated documentation
- Rich IDE support with full typing
- Comprehensive error handling

### **Production Ready**
- Horizontal scaling support
- Health checks and monitoring
- Graceful shutdown handling
- Connection pooling and retry logic

### **Ecosystem Integration**
- Seamless integration across MAESTRO components
- Standardized patterns and interfaces
- Consistent logging and monitoring
- Unified configuration management

## 🔧 Installation

### Install All Libraries
```bash
# Using pip
pip install maestro-core-logging maestro-core-api maestro-core-config \
            maestro-core-auth maestro-core-db maestro-core-messaging \
            maestro-monitoring

# Using poetry
poetry add maestro-core-logging maestro-core-api maestro-core-config \
           maestro-core-auth maestro-core-db maestro-core-messaging \
           maestro-monitoring
```

### Install Individual Libraries
```bash
# Just the essentials
pip install maestro-core-logging maestro-core-api maestro-core-config

# Add database support
pip install maestro-core-db

# Add authentication
pip install maestro-core-auth

# Add messaging
pip install maestro-core-messaging

# Add monitoring
pip install maestro-monitoring
```

## 🏃‍♂️ Quick Start Example

```python
from maestro_core_api import MaestroAPI, APIConfig, SecurityConfig
from maestro_core_logging import configure_logging
from maestro_core_config import ConfigManager, BaseConfig

# Define configuration
class ServiceConfig(BaseConfig):
    database_url: str
    redis_url: str = "redis://localhost:6379"
    jwt_secret: str

# Load configuration
config_manager = ConfigManager(ServiceConfig)
config = config_manager.load()

# Configure logging
configure_logging(
    service_name="my-service",
    environment="production",
    log_level="INFO"
)

# Create API
api_config = APIConfig(
    title="My Service API",
    service_name="my-service",
    security=SecurityConfig(jwt_secret_key=config.jwt_secret)
)

app = MaestroAPI(api_config)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    app.run()
```

## 🤝 Contributing

See our [Contributing Guide](./CONTRIBUTING.md) for:
- Development setup
- Code standards
- Testing requirements
- Pull request process

## 📞 Support

- **Documentation Issues**: Open an issue in this repository
- **Library Bugs**: Report in the specific library repository
- **General Questions**: Use GitHub Discussions
- **Enterprise Support**: Contact the MAESTRO team

## 📜 License

All libraries are licensed under the MIT License. See [LICENSE](./LICENSE) for details.

---

*Built with ❤️ by the MAESTRO team for enterprise-grade applications.*