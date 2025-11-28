# Health Check API

A production-ready health check API endpoint for service monitoring and orchestration.

## Overview

| Endpoint | Purpose | Use Case |
|----------|---------|----------|
| `GET /health` | Basic health status | Load balancers, general monitoring |
| `GET /health/live` | Minimal liveness probe | Kubernetes liveness probes |
| `GET /health/ready` | Readiness with dependencies | Kubernetes readiness probes |

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
python health_check_api.py

# Or with uvicorn directly
uvicorn health_check_api:app --host 0.0.0.0 --port 8000
```

## API Documentation

Access interactive docs at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Endpoints

### Basic Health Check
```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2025-11-22T12:00:00Z",
  "service": "health-check-api",
  "version": "1.0.0",
  "uptime_seconds": 3600.5
}
```

### Liveness Probe
```bash
curl http://localhost:8000/health/live
```

### Readiness Check
```bash
curl http://localhost:8000/health/ready
```

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `SERVICE_NAME` | health-check-api | Service identifier |
| `SERVICE_VERSION` | 1.0.0 | Service version |
| `ENVIRONMENT` | development | Deployment environment |

## Kubernetes Integration

```yaml
livenessProbe:
  httpGet:
    path: /health/live
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /health/ready
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 5
```

## Quality Standards

- Type hints throughout
- Pydantic models for validation
- OpenAPI documentation
- Kubernetes probe compatibility
- Proper error handling (503 for degraded state)

## Author

Marcus - Backend Developer
