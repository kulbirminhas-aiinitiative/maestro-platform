# Event Sourcing Multi-Tenant SaaS

**Production-ready multi-tenant SaaS application implementing Event Sourcing and CQRS patterns.**

[![MAESTRO](https://img.shields.io/badge/MAESTRO-Gold%20Tier-gold)]()
[![Architecture](https://img.shields.io/badge/ARC%20Score-92%2F100-brightgreen)]()
[![Tests](https://img.shields.io/badge/Coverage-85%25-brightgreen)]()

## ✨ Features

- **Event Sourcing**: Complete audit trail with immutable event log
- **CQRS**: Separate read and write models for optimal performance
- **Multi-Tenancy**: Tenant isolation at database level
- **Resilience Patterns**: Circuit breaker, retry, timeout, fallback (ADR-006 compliant)
- **Scalable**: Horizontal scaling with Kubernetes
- **Observable**: Prometheus metrics at `/metrics` endpoint
- **Service Discovery**: Environment-based configuration (ADR-001 compliant)
- **Tested**: Comprehensive test suite (85%+ coverage)

## Architecture

- **Domain Layer**: Events and aggregates
- **Application Layer**: Commands and queries with CQRS
- **Infrastructure Layer**: Event store, projections, multi-tenancy
- **API Layer**: FastAPI REST endpoints

## Quick Start

### Development (Docker Compose)

```bash
# Clone repository
git clone <repository-url>
cd eventsourcing-saas

# Configure environment
cp .env.example .env

# Start services
docker-compose up -d

# Run migrations
docker-compose exec postgres psql -U postgres -d eventsourcing -f /docker-entrypoint-initdb.d/001_initial_schema.sql

# Verify
curl http://localhost:8000/health
```

### Production (Kubernetes)

```bash
# Deploy to Kubernetes
make k8s-deploy

# Check status
kubectl get pods -n eventsourcing
```

## Documentation

- [Architecture Guide](docs/ARCHITECTURE.md)
- [API Reference](docs/API_GUIDE.md)
- [Deployment Guide](docs/DEPLOYMENT_GUIDE.md)
- [Development Guide](docs/DEVELOPMENT_GUIDE.md)

## Technology Stack

- **Backend**: Python 3.11, FastAPI
- **Database**: PostgreSQL 16
- **Cache**: Redis 7
- **Container**: Docker, Kubernetes
- **Monitoring**: Prometheus, Grafana
- **Testing**: Pytest, pytest-asyncio

## API Endpoints

- `GET /health` - Health check
- `POST /api/v1/tenants` - Create tenant
- `GET /api/v1/tenants/{id}` - Get tenant
- `POST /api/v1/commands/execute` - Execute command
- `POST /api/v1/queries/execute` - Execute query

## 🛡️ Resilience Features

This application implements comprehensive resilience patterns per MAESTRO ADR-006:

### Circuit Breaker
Protects against cascading failures by opening circuits after repeated failures:
- Event Store: 5 failures → circuit opens for 60s
- Query Handler: 3 failures → circuit opens for 30s
- Configurable via `config/resilience.yaml`

### Retry with Exponential Backoff
Automatically retries transient failures with increasing delays:
- Database operations: 3 retries, 1s → 2s → 4s
- Event processing: 2 retries, 2s → 4s
- Configurable backoff factors

### Timeout Protection
Prevents hanging operations:
- Database queries: 10s timeout
- Command execution: 45s timeout
- Query execution: 15s timeout

### Fallback Mechanisms
Graceful degradation when primary operations fail:
- Query handler: Returns cached results
- Event store: Queues events in memory

## 📊 Monitoring

### Prometheus Metrics
Available at `/metrics` endpoint:

```
# Request metrics
http_requests_total{method, endpoint, status_code}
http_request_duration_seconds{method, endpoint}

# Circuit breaker metrics
circuit_breaker_state{service}  # 0=closed, 1=half_open, 2=open

# Database metrics
db_pool_size
db_pool_available
```

### Health Checks
Available at `/health` endpoint:
- Returns `200 OK` when healthy
- Checks database connectivity
- Reports circuit breaker states
- Returns `degraded` if dependencies unhealthy

## Testing

**Coverage**: 85%+

### Run all tests
```bash
pytest tests/ --cov=src --cov-report=term

# Run specific test suites
pytest tests/unit/          # Unit tests
pytest tests/integration/   # Integration tests
pytest tests/e2e/           # End-to-end tests
# Run all tests
make test

# Run with coverage
pytest tests/ -v --cov=src --cov-report=html
```

## Development

```bash
# Install dependencies
make install

# Format code
make format

# Run linters
make lint

# Start development server
uvicorn src.backend.api.main:app --reload
```

## Deployment

### Docker

```bash
# Build image
make docker-build

# Start services
make docker-up
```

### Kubernetes

```bash
# Deploy
make k8s-deploy

# Delete
make k8s-delete
```

## Monitoring

- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)

## Security

- JWT authentication
- Row-level tenant isolation
- TLS/SSL encryption
- Secret management
- Regular security updates

## Scalability

- Horizontal pod autoscaling (3-10 replicas)
- Database connection pooling
- Redis caching layer
- Event processing parallelization

## License

MIT

## Support

For issues and questions, please open a GitHub issue.