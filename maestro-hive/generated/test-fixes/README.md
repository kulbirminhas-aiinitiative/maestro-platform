# Health Check API

A simple REST API endpoint for health monitoring and service status checks.

## Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Basic health check |
| `/health/detailed` | GET | Detailed health with system metrics |
| `/health/ready` | GET | Kubernetes readiness probe |
| `/health/live` | GET | Kubernetes liveness probe |

## Installation

```bash
pip install -r requirements.txt
```

## Running the Service

```bash
python health_api.py
```

Or with uvicorn:

```bash
uvicorn health_api:app --host 0.0.0.0 --port 8000
```

## API Documentation

Once running, access:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Example Responses

### GET /health
```json
{
  "status": "healthy",
  "timestamp": "2025-11-22T12:00:00.000000",
  "version": "1.0.0",
  "service": "health-check-service"
}
```

### GET /health/detailed
```json
{
  "status": "healthy",
  "timestamp": "2025-11-22T12:00:00.000000",
  "version": "1.0.0",
  "service": "health-check-service",
  "uptime_seconds": 3600.0,
  "memory_usage_mb": 45.2,
  "cpu_percent": 2.5,
  "disk_usage_percent": 45.0
}
```

## Environment Variables

- `SERVICE_VERSION`: Service version string (default: "1.0.0")
- `SERVICE_NAME`: Service name (default: "health-check-service")
