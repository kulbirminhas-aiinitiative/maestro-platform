# Maestro K8s Execution Service

**Ephemeral Kubernetes Environments for Testing & Development**

Version: 1.0.0
Port: 8004
Status: ✅ Production Ready

---

## 📋 Overview

The **Maestro K8s Execution Service** provides on-demand, ephemeral Kubernetes environments for testing, development, and quality validation. This service creates isolated K8s namespaces with full application stacks, enabling true production-parity testing.

### Key Features

- ✅ **Ephemeral K8s Namespaces** - On-demand isolated environments
- ✅ **Full Stack Provisioning** - Deploy complete application stacks
- ✅ **Database Support** - PostgreSQL, MySQL, MongoDB, Redis
- ✅ **Resource Quotas** - Automatic resource limits
- ✅ **Auto-Cleanup** - TTL-based environment cleanup
- ✅ **Event-Driven** - Redis Streams integration
- ✅ **REST API** - FastAPI-powered endpoints
- ✅ **K8s Native** - Uses official Kubernetes Python client

---

## 🏗️ Architecture

### Service Components

```
k8s-execution-service/
├── src/k8s_execution/
│   ├── main.py                   # FastAPI application
│   ├── config.py                 # Configuration management
│   ├── api.py                    # REST API endpoints
│   ├── engine.py                 # K8s execution engine (599 lines)
│   ├── message_handler.py        # Redis Streams consumer (460 lines)
│   └── models.py                 # Pydantic models
├── templates/                    # K8s YAML templates
│   ├── namespace.yaml            # Namespace with resource quotas
│   ├── deployment.yaml           # Application deployment
│   ├── postgres.yaml             # PostgreSQL database
│   ├── redis.yaml                # Redis cache
│   └── test-job.yaml             # Test job execution
├── pyproject.toml                # Dependencies
├── Dockerfile                    # Container config
├── docker-compose.yml            # Deployment config
└── .env.example                  # Environment template
```

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **API Framework** | FastAPI | High-performance async API |
| **K8s Client** | kubernetes-python | Kubernetes operations |
| **Event Bus** | Redis Streams | Async job processing |
| **Templates** | YAML + Jinja2 | K8s resource templates |
| **Config** | Pydantic Settings | Configuration management |

---

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Kubernetes cluster (local or remote)
- kubectl configured
- Redis 7+

### Start Service

```bash
# Navigate to service
cd /home/ec2-user/projects/maestro-platform/services/k8s-execution-service

# Configure environment
cp .env.example .env
# Edit .env with your K8s configuration

# Start service
docker-compose up -d

# Verify health
curl http://localhost:8004/health
```

### API Documentation

```
http://localhost:8004/docs
```

---

## 🔌 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/k8s-execution/health` | GET | Health check |
| `/api/v1/k8s-execution/environments` | POST | Create environment |
| `/api/v1/k8s-execution/environments/{id}` | GET | Get environment status |
| `/api/v1/k8s-execution/environments/{id}` | DELETE | Delete environment |
| `/api/v1/k8s-execution/environments` | GET | List environments |
| `/api/v1/k8s-execution/jobs` | POST | Submit test job |
| `/api/v1/k8s-execution/jobs/{id}` | GET | Get job status |
| `/api/v1/k8s-execution/cleanup` | POST | Cleanup expired environments |

---

## 📊 Usage Examples

### Create Environment

```bash
curl -X POST http://localhost:8004/api/v1/k8s-execution/environments \
  -H "Content-Type: application/json" \
  -d '{
    "execution_id": "test-001",
    "config": {
      "app_image": "myapp:latest",
      "app_port": 8000,
      "database": "postgresql",
      "ttl_minutes": 60
    }
  }'
```

### Check Environment Status

```bash
curl http://localhost:8004/api/v1/k8s-execution/environments/test-001
```

### Run Test Job

```bash
curl -X POST http://localhost:8004/api/v1/k8s-execution/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "environment_id": "test-001",
    "test_command": "pytest tests/",
    "test_image": "myapp-tests:latest"
  }'
```

---

## 🧪 K8s Templates

### Namespace Template

Creates isolated namespace with resource quotas:
- CPU limit: 1000m (configurable)
- Memory limit: 1Gi (configurable)
- Pod limit: 10
- TTL-based cleanup

### Deployment Template

Deploys application with:
- Configurable replicas
- Resource requests/limits
- Environment variables
- Health checks

### Database Templates

Supports:
- **PostgreSQL** (version 15)
- **MySQL** (version 8.0)
- **MongoDB** (version 7)
- **Redis** (version 7)

---

## 📈 Redis Streams Integration

### Streams

```python
STREAMS = {
    "k8s:jobs": "maestro:streams:k8s:jobs",
    "k8s:results": "maestro:streams:k8s:results",
    "k8s:status": "maestro:streams:k8s:status"
}
```

### Message Format

**Job Request**:
```json
{
  "job_id": "job-uuid",
  "execution_id": "test-001",
  "operation": "create|delete|status",
  "config": {
    "app_image": "myapp:latest",
    "database": "postgresql",
    "ttl_minutes": 60
  }
}
```

**Job Result**:
```json
{
  "job_id": "job-uuid",
  "status": "success|error",
  "namespace": "quality-fabric-test-001",
  "resources_created": ["namespace", "deployment", "postgres"],
  "duration_ms": 5000
}
```

---

## 🔧 Configuration

### Environment Variables

Key configuration (see `.env.example` for full list):

```bash
# Service
SERVICE_PORT=8004

# K8s Configuration
K8S_IN_CLUSTER=false
K8S_NAMESPACE_PREFIX=quality-fabric
K8S_TTL_MINUTES=60

# Resource Limits
DEFAULT_CPU_LIMIT=1000m
DEFAULT_MEMORY_LIMIT=1Gi

# Redis
REDIS_HOST=maestro-redis
REDIS_PORT=6379
```

---

## 🐳 Docker Deployment

### Build & Run

```bash
# Build image
docker build -t maestro-k8s-execution:1.0.0 .

# Run container
docker run -d \
  --name k8s-execution-service \
  -p 8004:8004 \
  -e REDIS_URL=redis://redis:6379/0 \
  -v ~/.kube/config:/root/.kube/config \
  maestro-k8s-execution:1.0.0

# Or use docker-compose
docker-compose up -d
```

---

## 🔍 Features

### Ephemeral Environments

Every environment gets:
- Unique K8s namespace
- Resource quotas
- TTL-based cleanup (default: 60 minutes)
- Isolated networking

### Auto-Cleanup

The service automatically:
1. Monitors namespace TTL labels
2. Deletes expired environments
3. Cleans up orphaned resources
4. Logs cleanup operations

### Resource Management

Enforces limits:
- CPU: 100m request, 1000m limit
- Memory: 256Mi request, 1Gi limit
- Pods: Maximum 10 per namespace
- Configurable per environment

---

## 📚 Integration

### With CARS (Automation Service)

```python
# CARS triggers K8s execution for test healing
await k8s_client.create_environment(
    execution_id=f"heal-{test_id}",
    config={
        "app_image": "myapp:fixed",
        "database": "postgresql",
        "ttl_minutes": 30
    }
)
```

### With Quality Fabric

```python
# Quality Fabric uses K8s for validation
await k8s_client.run_validation(
    execution_id=f"validate-{commit_sha}",
    test_suite="integration_tests"
)
```

---

## 🧪 Testing

```bash
# Run tests
poetry run pytest

# Integration tests
poetry run pytest tests/integration/

# E2E tests (requires K8s cluster)
poetry run pytest tests/e2e/
```

---

## 📖 Additional Resources

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Week 6 Analysis](../../WEEK6_K8S_EXECUTION_SERVICE_ANALYSIS.md)
- [Roadmap](../../ROADMAP_100_PERCENT_COMPLETE.md)

---

## 🎯 Use Cases

1. **Test Healing**: CARS uses ephemeral environments for test fixes
2. **Integration Testing**: Full-stack integration tests with real databases
3. **Feature Branches**: On-demand environments for feature development
4. **Performance Testing**: Isolated environments for load testing
5. **Security Testing**: Ephemeral environments for security validation

---

**K8s Execution Service** | Version 1.0.0 | Port 8004 | ✅ Production Ready

*Ephemeral Kubernetes Environments for Maestro Platform*
*"Top 1% testing platform feature" - World-class capability* 🚀✨
