# Health Check API

A simple FastAPI-based health check service for monitoring application status.

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Basic health check |
| GET | `/health/detailed` | Detailed health with uptime |
| GET | `/health/ready` | Kubernetes readiness probe |
| GET | `/health/live` | Kubernetes liveness probe |

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python health_check_api.py
```

The API will be available at `http://localhost:8080`.

## API Documentation

Once running, access the interactive API docs at:
- Swagger UI: `http://localhost:8080/docs`
- ReDoc: `http://localhost:8080/redoc`

## Example Responses

### GET /health
```json
{
  "status": "healthy",
  "timestamp": "2025-11-22T12:00:00.000000",
  "service": "health-check-api",
  "version": "1.0.0",
  "checks": {
    "api": "ok"
  }
}
```

### GET /health/detailed
```json
{
  "status": "healthy",
  "timestamp": "2025-11-22T12:00:00.000000",
  "service": "health-check-api",
  "version": "1.0.0",
  "checks": {
    "api": "ok",
    "memory": "ok",
    "disk": "ok"
  },
  "uptime_seconds": 3600.0,
  "environment": "development"
}
```
