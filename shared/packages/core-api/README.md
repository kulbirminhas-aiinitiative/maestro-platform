# MAESTRO Core API

Enterprise-grade FastAPI framework with built-in security, monitoring, rate limiting, and standardized patterns.

## Features

- 🔒 **Security**: JWT/API Key authentication, CORS, security headers
- 📊 **Monitoring**: Prometheus metrics, OpenTelemetry tracing, structured logging
- 🚦 **Rate Limiting**: Redis-backed rate limiting with per-endpoint controls
- 🛡️ **Middleware**: Request logging, security headers, compression, timeouts
- 🏥 **Health Checks**: Built-in health and readiness endpoints
- 📝 **Documentation**: Auto-generated OpenAPI docs with examples
- ⚙️ **Configuration**: Environment-based config with validation

## Quick Start

```python
from maestro_core_api import MaestroAPI, APIConfig, SecurityConfig

# Configure your API
config = APIConfig(
    title="My Service API",
    service_name="my-service",
    version="1.0.0",
    security=SecurityConfig(
        jwt_secret_key="your-super-secret-key-min-32-chars"
    )
)

# Create application
app = MaestroAPI(config)

# Add routes
@app.get("/users/{user_id}")
async def get_user(user_id: int):
    return {"user_id": user_id, "name": "John Doe"}

# Run the server
if __name__ == "__main__":
    app.run()
```

## Configuration

Use environment variables with `MAESTRO_API_` prefix:

```bash
export MAESTRO_API_TITLE="My API"
export MAESTRO_API_SERVICE_NAME="my-service"
export MAESTRO_API_SECURITY__JWT_SECRET_KEY="your-secret-key"
export MAESTRO_API_DEBUG=true
```

## Enterprise Features

### Authentication & Authorization

```python
from maestro_core_api import require_auth, require_role

@app.get("/protected")
@require_auth
async def protected_endpoint(current_user: User = Depends(get_current_user)):
    return {"message": f"Hello {current_user.username}"}

@app.get("/admin")
@require_role("admin")
async def admin_endpoint():
    return {"message": "Admin only"}
```

### Rate Limiting

```python
from slowapi import Limiter

@app.get("/limited")
@limiter.limit("5/minute")
async def limited_endpoint(request: Request):
    return {"message": "Rate limited endpoint"}
```

### Monitoring & Metrics

Built-in metrics at `/metrics`:
- Request duration histograms
- Request count by status code
- Active request gauge
- Custom business metrics

### Structured Logging

```python
from maestro_core_logging import get_logger

logger = get_logger(__name__)

@app.get("/example")
async def example():
    logger.info("Processing request", user_id=123, action="fetch_data")
    return {"result": "success"}
```

## Testing

```python
from fastapi.testclient import TestClient

def test_health_check():
    client = TestClient(app.app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
```

## Production Deployment

```dockerfile
FROM python:3.11-slim

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . /app
WORKDIR /app

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Best Practices

1. **Environment Configuration**: Use environment variables for all config
2. **Error Handling**: Use custom exceptions with proper HTTP status codes
3. **Validation**: Leverage Pydantic models for request/response validation
4. **Documentation**: Add docstrings and examples to all endpoints
5. **Testing**: Write comprehensive tests for all endpoints
6. **Monitoring**: Use structured logging and monitor key metrics

---
*Part of the MAESTRO Enterprise Ecosystem*