# Health Check API

A simple FastAPI service providing health check endpoints for container orchestration and monitoring.

## Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Basic health check with metadata |
| `/ready` | GET | Readiness probe endpoint |
| `/live` | GET | Liveness probe endpoint |

## Quick Start

### Local Development
```bash
pip install -r requirements.txt
uvicorn app:app --reload --port 8080
```

### Docker
```bash
docker build -t health-api .
docker run -p 8080:8080 health-api
```

### Docker Compose
```bash
docker-compose up -d
```

### Kubernetes
```bash
kubectl apply -f k8s/deployment.yaml
```

## API Documentation

Once running, access:
- Swagger UI: http://localhost:8080/docs
- ReDoc: http://localhost:8080/redoc

## Testing

```bash
curl http://localhost:8080/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00.000000",
  "version": "1.0.0",
  "service": "health-api"
}
```
