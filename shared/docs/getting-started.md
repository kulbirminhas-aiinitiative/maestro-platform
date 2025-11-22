# Getting Started with MAESTRO Shared Libraries

This guide will help you integrate MAESTRO shared libraries into your service in 15 minutes.

## Prerequisites

- Python 3.11 or higher
- Poetry or pip for dependency management
- Basic familiarity with FastAPI and async Python

## Step 1: Installation

Choose your installation method:

### Option A: Full Stack (Recommended)
```bash
pip install maestro-core-logging maestro-core-api maestro-core-config \
            maestro-core-auth maestro-core-db maestro-core-messaging \
            maestro-monitoring
```

### Option B: Minimal Setup
```bash
pip install maestro-core-logging maestro-core-api maestro-core-config
```

## Step 2: Create Your First Service

Create a new file `main.py`:

```python
from maestro_core_api import MaestroAPI, APIConfig, SecurityConfig
from maestro_core_logging import configure_logging, get_logger
from maestro_core_config import ConfigManager, BaseConfig
from pydantic import Field

# Step 1: Define Configuration
class ServiceConfig(BaseConfig):
    # Database
    database_url: str = Field(..., description="Database connection URL")

    # Security
    jwt_secret: str = Field(..., min_length=32, description="JWT secret key")

    # Optional settings
    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: str = Field(default="INFO", description="Logging level")

# Step 2: Load Configuration
config_manager = ConfigManager(ServiceConfig)
config = config_manager.load()

# Step 3: Configure Logging
configure_logging(
    service_name="my-first-service",
    environment="development" if config.debug else "production",
    log_level=config.log_level
)

logger = get_logger(__name__)

# Step 4: Create API Application
api_config = APIConfig(
    title="My First MAESTRO Service",
    description="A service built with MAESTRO shared libraries",
    version="1.0.0",
    service_name="my-first-service",
    security=SecurityConfig(jwt_secret_key=config.jwt_secret),
    debug=config.debug
)

app = MaestroAPI(api_config)

# Step 5: Add Routes
@app.get("/")
async def root():
    logger.info("Root endpoint called")
    return {"message": "Hello from MAESTRO!", "service": "my-first-service"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "my-first-service"}

@app.get("/info")
async def service_info():
    return {
        "service": "my-first-service",
        "version": "1.0.0",
        "config": {
            "debug": config.debug,
            "log_level": config.log_level
        }
    }

if __name__ == "__main__":
    logger.info("Starting service", service="my-first-service", version="1.0.0")
    app.run(host="0.0.0.0", port=8000)
```

## Step 3: Create Configuration

Create a `.env` file in your project root:

```bash
# .env file
MAESTRO_API_DATABASE_URL=postgresql://user:password@localhost:5432/mydb
MAESTRO_API_JWT_SECRET=your-super-secret-jwt-key-must-be-32-characters-minimum
MAESTRO_API_DEBUG=true
MAESTRO_API_LOG_LEVEL=DEBUG
```

Or create `config/settings.yaml`:

```yaml
database_url: "postgresql://user:password@localhost:5432/mydb"
jwt_secret: "your-super-secret-jwt-key-must-be-32-characters-minimum"
debug: true
log_level: "DEBUG"
```

## Step 4: Run Your Service

```bash
python main.py
```

You should see:
```
2023-01-01T12:00:00.000000Z [INFO] Starting service service=my-first-service version=1.0.0
2023-01-01T12:00:00.000000Z [INFO] Starting uvicorn server
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

## Step 5: Test Your Service

Open your browser or use curl:

```bash
# Test basic endpoint
curl http://localhost:8000/

# Check health
curl http://localhost:8000/health

# View service info
curl http://localhost:8000/info

# View API documentation
# Open http://localhost:8000/docs in your browser
```

## Next Steps

### Add Database Support

```python
from maestro_core_db import DatabaseManager, BaseModel, create_session
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

# Define a model
class User(BaseModel):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)

# Initialize database
db_manager = DatabaseManager(config.database_url)
await db_manager.initialize()

# Use in endpoints
@app.get("/users")
async def get_users():
    async with create_session() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()
        return {"users": [{"id": u.id, "username": u.username} for u in users]}
```

### Add Authentication

```python
from maestro_core_auth import AuthManager, get_current_user, require_role
from fastapi import Depends

# Initialize auth
auth_manager = AuthManager(
    jwt_secret=config.jwt_secret,
    token_expire_minutes=30
)

# Protected endpoint
@app.get("/protected")
async def protected_endpoint(current_user = Depends(get_current_user)):
    logger.info("Protected endpoint accessed", user_id=current_user.id)
    return {"message": f"Hello {current_user.username}!", "user_id": current_user.id}

# Admin-only endpoint
@app.get("/admin")
async def admin_endpoint(current_user = Depends(require_role("admin"))):
    return {"message": "Admin access granted", "user": current_user.username}
```

### Add Messaging

```python
from maestro_core_messaging import MessageBroker, EventPublisher, BrokerType

# Initialize messaging
broker = MessageBroker(
    broker_type=BrokerType.REDIS,
    connection_string="redis://localhost:6379"
)
await broker.connect()

publisher = EventPublisher(broker)

# Publish events
@app.post("/users")
async def create_user(user_data: dict):
    # Create user logic here...

    # Publish event
    await publisher.publish(
        topic="user.events",
        event={
            "event_type": "user_created",
            "user_id": 123,
            "username": user_data["username"],
            "timestamp": datetime.utcnow().isoformat()
        }
    )

    return {"message": "User created and event published"}
```

### Add Monitoring

```python
from maestro_monitoring import MonitoringManager

# Initialize monitoring
monitoring = MonitoringManager(
    service_name="my-first-service",
    prometheus_port=9090,
    enable_system_metrics=True
)
await monitoring.start()

# Business metrics
@app.post("/orders")
async def create_order(order_data: dict):
    # Order creation logic...

    # Record business metric
    monitoring.record_business_metric(
        "orders_created_total",
        1,
        {"order_type": order_data.get("type", "standard")}
    )

    return {"message": "Order created"}
```

## Common Patterns

### Request Context Logging

```python
from maestro_core_logging import request_context

@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    with request_context(
        request_id=request.headers.get("X-Request-ID"),
        user_id=request.headers.get("X-User-ID")
    ):
        response = await call_next(request)
        return response
```

### Error Handling

```python
from maestro_core_api import APIException

class UserNotFoundException(APIException):
    status_code = 404
    error_code = "USER_NOT_FOUND"
    message = "User not found"

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    user = await find_user(user_id)
    if not user:
        raise UserNotFoundException()
    return user
```

### Configuration Validation

```python
from maestro_core_config import BaseConfig
from pydantic import validator, Field

class ServiceConfig(BaseConfig):
    database_url: str = Field(..., description="Database URL")
    max_connections: int = Field(default=10, ge=1, le=100)

    @validator('database_url')
    def validate_database_url(cls, v):
        if not v.startswith(('postgresql://', 'mysql://', 'sqlite://')):
            raise ValueError('Invalid database URL')
        return v
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Make sure all required packages are installed
2. **Configuration Errors**: Check your `.env` file or configuration files
3. **Port Conflicts**: Ensure ports 8000 (API) and 9090 (metrics) are available
4. **JWT Secret**: Must be at least 32 characters long

### Debug Mode

Enable debug logging:

```python
configure_logging(
    service_name="my-service",
    log_level="DEBUG",
    log_format="console"  # Human-readable in development
)
```

### Health Checks

All services automatically include:
- `/health` - Basic health check
- `/metrics` - Prometheus metrics (on port 9090)
- `/docs` - API documentation (development only)

## Next Steps

1. **[Migration Guide](./migration-guide.md)** - Migrate existing services
2. **[Best Practices](./best-practices.md)** - Follow proven patterns
3. **[Examples](./examples/)** - See real-world examples
4. **[Library Docs](./libraries/)** - Deep dive into specific libraries

## Getting Help

- **Documentation**: Check the specific library documentation
- **Examples**: Look at the examples repository
- **Issues**: Open an issue on GitHub
- **Discussions**: Use GitHub Discussions for questions

---

**Congratulations!** You've created your first MAESTRO service. The shared libraries provide enterprise-grade features out of the box, so you can focus on your business logic.