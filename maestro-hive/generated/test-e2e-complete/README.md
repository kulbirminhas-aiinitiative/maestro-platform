# Health Check API

A simple REST API endpoint for health monitoring and system status checks.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Start the server

```bash
python health_check_api.py
```

Or with uvicorn directly:

```bash
uvicorn health_check_api:app --host 0.0.0.0 --port 8080
```

## Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Basic health check with status, timestamp, version |
| `/health/ready` | GET | Kubernetes readiness probe |
| `/health/live` | GET | Kubernetes liveness probe |
| `/health/detailed` | GET | Detailed health with system metrics |
| `/` | GET | Root endpoint |

## Example Response

### GET /health

```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00.000000Z",
  "version": "1.0.0",
  "uptime_seconds": 3600.5
}
```

### GET /health/detailed

```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00.000000Z",
  "version": "1.0.0",
  "system": {
    "platform": "Linux",
    "python_version": "3.11.0",
    "hostname": "server-01",
    "cpu_count": 4,
    "memory_percent": 45.2,
    "disk_percent": 32.1
  },
  "checks": {
    "api": "passing",
    "memory": "passing",
    "disk": "passing"
  }
}
```

## API Documentation

Interactive API docs available at:
- Swagger UI: `http://localhost:8080/docs`
- ReDoc: `http://localhost:8080/redoc`
