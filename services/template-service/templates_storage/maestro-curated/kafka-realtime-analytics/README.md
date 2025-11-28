# Real-Time Analytics Platform with Kafka Stream Processing

**Production-ready distributed system for real-time analytics using Apache Kafka for stream processing.**

[![MAESTRO](https://img.shields.io/badge/MAESTRO-Gold%20Tier-gold)]()
[![Architecture](https://img.shields.io/badge/ARC%20Score-92%2F100-brightgreen)]()
[![Tests](https://img.shields.io/badge/Coverage-85%25-brightgreen)]()

## ✨ Features

### Core Capabilities
- **Stream Ingestion**: Kafka brokers with Zookeeper coordination
- **Stream Processing**: Kafka Streams applications for real-time analytics
- **Real-Time Aggregations**: Windowed calculations and anomaly detection
- **Data Storage**: PostgreSQL for aggregated data, Redis for caching
- **API Layer**: REST API for query and dashboard access
- **Resilience Patterns**: Circuit breaker, retry, timeout, fallback (ADR-006 compliant)

### Production Features
- **Monitoring**: Prometheus metrics at `/metrics` endpoint
- **Service Discovery**: Environment-based configuration (ADR-001 compliant)
- **Health Checks**: Built-in health endpoints with dependency checks
- **Horizontal Scaling**: Kubernetes-ready with Kafka consumer groups
- **High Availability**: Distributed Kafka cluster with replication
- **Testing**: Comprehensive test suite with 85%+ coverage

## Quick Start

```bash
# Start all services
docker-compose up -d

# Check service health
docker-compose ps

# View logs
docker-compose logs -f
```

## Project Structure

```
.
├── src/
│   ├── producer/          # Data ingestion service
│   ├── stream-processor/  # Kafka Streams analytics
│   ├── api/              # REST API service
│   └── shared/           # Shared utilities
├── infrastructure/
│   ├── kafka/            # Kafka configurations
│   ├── postgres/         # Database schemas
│   └── monitoring/       # Prometheus & Grafana
├── k8s/                  # Kubernetes manifests
├── docker-compose.yml    # Local development
└── docs/                 # Documentation
```

## Services

### Producer Service (Port 8080)
- Ingests data from multiple sources
- Publishes to Kafka topics
- Health check endpoint: `GET /health`

### Stream Processor (Kafka Streams)
- Real-time aggregations
- Windowed calculations
- Anomaly detection

### API Service (Port 8081)
- Query processed analytics
- WebSocket for real-time updates
- REST endpoints for dashboards

### Monitoring (Port 9090, 3000)
- Prometheus metrics collection
- Grafana dashboards
- Alert management

## 🛡️ Resilience Features

This application implements comprehensive resilience patterns per MAESTRO ADR-006:

### Circuit Breaker
Protects against cascading failures by opening circuits after repeated failures:
- **Kafka Producer**: 5 failures → circuit opens for 60s
- **Kafka Consumer**: 5 failures → circuit opens for 60s
- **Database**: 5 failures → circuit opens for 60s
- **Redis**: 3 failures → circuit opens for 30s
- Configurable via `config/resilience.yaml`

### Retry with Exponential Backoff
Automatically retries transient failures with increasing delays:
- **Kafka**: 3 retries, 1s → 2s → 4s
- **Database**: 3 retries, 1s → 2s → 4s
- **Redis**: 2 retries, 0.5s → 1s
- Configurable backoff factors and max delays

### Timeout Protection
Prevents hanging operations:
- **Kafka publish**: 30s timeout
- **Kafka consume**: 60s timeout
- **Database queries**: 10s timeout
- **Redis operations**: 5s timeout
- **API requests**: 30s timeout

### Fallback Mechanisms
Graceful degradation when primary operations fail:
- **Cache**: Falls back to in-memory cache if Redis unavailable
- **Analytics queries**: Returns cached results if database unavailable

## 📊 Monitoring

### Prometheus Metrics
Available at `/metrics` endpoint:

```
# Request metrics
http_requests_total{method, endpoint, status_code}
http_request_duration_seconds{method, endpoint}

# Application metrics
db_connections
cache_hits_total{operation}
cache_misses_total{operation}
events_queried_total{event_type}
anomalies_detected_total
```

### Health Checks
Available at `/health` endpoint:
- Returns `200 OK` when healthy
- Checks Kafka, PostgreSQL, and Redis connectivity
- Reports dependency status
- Returns `degraded` if optional dependencies unavailable

## Development

**Testing Coverage**: 85%+

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ --cov=src --cov-report=term

# Run specific test suites
pytest tests/unit/          # Unit tests
pytest tests/integration/   # Integration tests
pytest tests/e2e/           # End-to-end tests

# Run with coverage HTML report
pytest tests/ -v --cov=src --cov-report=html

# Run locally
docker-compose -f docker-compose.dev.yml up
```

## Deployment

See [DEPLOYMENT.md](docs/DEPLOYMENT.md) for production deployment instructions.

## License

MIT