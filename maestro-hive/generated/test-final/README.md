# Health Check API

A simple health check API endpoint for service monitoring.

## Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Basic health check |
| `/health/detailed` | GET | Detailed health with system info |
| `/ready` | GET | Kubernetes readiness probe |
| `/live` | GET | Kubernetes liveness probe |

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python health_api.py
```

The API will be available at `http://localhost:8000`.

## API Documentation

Once running, access interactive docs at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Example Response

```json
{
  "status": "healthy",
  "timestamp": "2025-11-22T12:00:00.000000",
  "service": "health-check-api",
  "version": "1.0.0"
}
```
