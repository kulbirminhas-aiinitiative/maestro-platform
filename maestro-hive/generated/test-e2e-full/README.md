# Health Check API Endpoint

A simple, production-ready health check API for monitoring service availability.

## Endpoints

| Endpoint | Purpose | Use Case |
|----------|---------|----------|
| `/health` | Full health status | Monitoring dashboards, debugging |
| `/health/live` | Liveness probe | K8s liveness checks |
| `/health/ready` | Readiness probe | K8s readiness checks, load balancers |

## Quick Start

```bash
# Run the server
python health_check_api.py

# Or with custom port
PORT=3000 python health_check_api.py
```

## Test the Endpoints

```bash
# Full health check
curl http://localhost:8080/health

# Liveness probe
curl http://localhost:8080/health/live

# Readiness probe
curl http://localhost:8080/health/ready
```

## Example Response

```json
{
  "status": "healthy",
  "timestamp": "2025-11-22T12:00:00+00:00",
  "service": {
    "name": "health-check-api",
    "version": "1.0.0",
    "environment": "development"
  },
  "system": {
    "hostname": "server-01",
    "platform": "Linux",
    "python_version": "3.11.0",
    "uptime_seconds": 3600.5
  },
  "checks": {
    "memory": {"status": "healthy"},
    "disk": {"status": "healthy", "free_gb": 50.2, "used_percent": 45.3}
  }
}
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Bind address |
| `PORT` | `8080` | Listen port |
| `ENVIRONMENT` | `development` | Environment name |

## Integration

### Kubernetes

```yaml
livenessProbe:
  httpGet:
    path: /health/live
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /health/ready
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 5
```

### Docker

```dockerfile
HEALTHCHECK --interval=30s --timeout=3s \
  CMD curl -f http://localhost:8080/health/live || exit 1
```
