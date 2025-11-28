# Health Check API

A production-ready health check API endpoint built with FastAPI.

## Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Root endpoint with service info |
| `/health` | GET | Basic health check |
| `/health/live` | GET | Kubernetes liveness probe |
| `/health/ready` | GET | Kubernetes readiness probe |
| `/health/detailed` | GET | Detailed health with component status |

## Installation

```bash
pip install -r requirements.txt
```

## Running

```bash
# Development
python health_api.py

# Production
uvicorn health_api:app --host 0.0.0.0 --port 8000
```

## API Response Examples

### Basic Health Check (`/health`)
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00.000000+00:00",
  "version": "1.0.0",
  "uptime_seconds": 3600.25,
  "hostname": "server-01",
  "service": "Health Check API"
}
```

### Liveness Probe (`/health/live`)
```json
{
  "status": "alive"
}
```

### Readiness Probe (`/health/ready`)
```json
{
  "status": "ready"
}
```

## Configuration

Environment variables:
- `PORT`: Server port (default: 8000)
- `HOST`: Server host (default: 0.0.0.0)
- `ENV`: Environment mode (default: development)

## API Documentation

Interactive docs available at `/docs` (Swagger UI) and `/redoc` (ReDoc).
