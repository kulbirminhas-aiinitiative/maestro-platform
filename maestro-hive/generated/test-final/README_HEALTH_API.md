# Health Check API Documentation

**Author:** Marcus (Backend Developer)
**Version:** 1.0.0

## Overview

A production-ready health check API for monitoring service availability, readiness, and liveness. Built with FastAPI and follows best practices for microservice health monitoring.

## Endpoints

### GET /health
Basic health check for load balancer and monitoring systems.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00.000000",
  "service": "health-check-api",
  "version": "1.0.0"
}
```

### GET /health/detailed
Detailed health information with system metrics.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00.000000",
  "service": "health-check-api",
  "version": "1.0.0",
  "uptime_seconds": 3600.50,
  "system": {
    "platform": "Linux",
    "python_version": "3.11.0",
    "hostname": "server-01",
    "processor": "x86_64",
    "pid": 12345
  }
}
```

### GET /ready
Kubernetes-style readiness probe.

**Response:**
```json
{
  "ready": true
}
```

### GET /live
Kubernetes-style liveness probe.

**Response:**
```json
{
  "alive": true
}
```

## Configuration

Environment variables:
- `SERVICE_NAME` - Service identifier (default: "health-check-api")
- `SERVICE_VERSION` - API version (default: "1.0.0")
- `HOST` - Bind host (default: "0.0.0.0")
- `PORT` - Bind port (default: "8000")

## Running the API

```bash
# Install dependencies
pip install fastapi uvicorn pydantic

# Run the server
python health_api.py

# Or with uvicorn directly
uvicorn health_api:app --host 0.0.0.0 --port 8000
```

## Running Tests

```bash
pip install pytest httpx
pytest test_health_api.py -v
```

## Interactive Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json

## Kubernetes Integration

```yaml
livenessProbe:
  httpGet:
    path: /live
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /ready
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 10
```

## Error Handling

All endpoints include proper error handling with structured error responses:

```json
{
  "error": "InternalError",
  "message": "Error description",
  "timestamp": "2024-01-15T10:30:00.000000"
}
```
