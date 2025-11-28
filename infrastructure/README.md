# Maestro Platform - Centralized Infrastructure

**Single shared infrastructure for ALL Maestro services**

## Architecture

```
maestro-platform/infrastructure/
├── docker-compose.infrastructure.yml    ← Start this FIRST
├── .env.infrastructure                  ← Configure passwords here
├── databases/
│   ├── postgres/
│   │   └── init-scripts/
│   │       └── 01-create-databases.sql  ← Creates: quality_fabric, maestro_v2, maestro_frontend
│   └── redis/
│       └── redis.conf
└── monitoring/
    ├── prometheus/
    │   └── prometheus.yml               ← Scrapes all services
    └── grafana/
        ├── provisioning/
        │   ├── datasources/             ← Auto-configured datasources
        │   └── dashboards/              ← Dashboard provisioning
        └── dashboards/
            ├── platform/                ← Platform-wide dashboards
            ├── quality-fabric/          ← Service-specific dashboards
            ├── maestro-v2/
            └── maestro-frontend/
```

## Services Provided

### Core Infrastructure

| Service | Port | Purpose | Users |
|---------|------|---------|-------|
| **PostgreSQL** | 25432 | Database (5 databases) | All services |
| **Redis** | 27379 | Cache/Sessions | All services |
| **Prometheus** | 29090 | Metrics collection | Monitoring |
| **Grafana** | 23000 | Visualization + RBAC | All teams |
| **Jaeger** | 26686 | Distributed tracing | All services |

### Artifact Management (NEW)

| Service | Port | Purpose | Users |
|---------|------|---------|-------|
| **MinIO** | 29000, 29001 | S3-compatible storage | All ML/Data services |
| **Harbor** | 28080 | Container registry + security | All dev teams |
| **Nexus OSS** | 28081-28084 | Universal artifact repo | All dev teams |
| **MLflow** | 25000 | ML experiment tracking | ML engineers |

**Full Artifact Management Guide**: [ARTIFACT_MANAGEMENT_GUIDE.md](./docs/ARTIFACT_MANAGEMENT_GUIDE.md)

## Quick Start

### 1. Configure Environment

```bash
cd /home/ec2-user/projects/maestro-platform/infrastructure

# Edit .env.infrastructure (SET PASSWORDS!)
nano .env.infrastructure

# Required variables:
# - MAESTRO_POSTGRES_ADMIN_PASSWORD
# - MAESTRO_REDIS_PASSWORD
# - MAESTRO_GRAFANA_ADMIN_PASSWORD
```

### 2. Start Infrastructure

```bash
# Start all infrastructure services
docker-compose -f docker-compose.infrastructure.yml up -d

# Watch logs
docker-compose -f docker-compose.infrastructure.yml logs -f

# Check health
docker-compose -f docker-compose.infrastructure.yml ps
```

### 3. Verify Services

```bash
# PostgreSQL
docker exec maestro-postgres psql -U maestro_admin -c "\l"
# Should show: quality_fabric, maestro_v2, maestro_frontend

# Redis
docker exec maestro-redis redis-cli -a ${MAESTRO_REDIS_PASSWORD} ping
# Should return: PONG

# Prometheus
curl http://localhost:9090/-/healthy
# Should return: Prometheus is Healthy.

# Grafana
curl http://localhost:3000/api/health
# Should return: {"commit":"...","database":"ok","version":"..."}

# Jaeger
curl http://localhost:16686/
# Should return HTML
```

### 4. Access UIs

- **Grafana**: http://localhost:3000
  - Username: `admin`
  - Password: (from .env.infrastructure)

- **Prometheus**: http://localhost:29090
  - Targets: http://localhost:29090/targets

- **Jaeger**: http://localhost:26686
  - Search traces by service

- **Harbor**: http://localhost:28080
  - Username: `admin`
  - Password: (from .env.infrastructure)

- **Nexus OSS**: http://localhost:28081
  - Username: `admin`
  - Password: `admin123` (change on first login)

- **MinIO Console**: http://localhost:29001
  - Username: (from .env.infrastructure MINIO_ROOT_USER)
  - Password: (from .env.infrastructure MINIO_ROOT_PASSWORD)

- **MLflow**: http://localhost:25000
  - No authentication (dev mode)

## Database Configuration

### Multi-Database Setup

Single PostgreSQL instance with 3 isolated databases:

```sql
-- Database per service
quality_fabric     (user: quality_fabric)
maestro_v2         (user: maestro_v2)
maestro_frontend   (user: maestro_frontend)

-- Security: Each user can ONLY access their own database
```

### Connection Strings

Services use these connection strings:

```bash
# Quality Fabric
postgresql://quality_fabric:${QF_DB_PASSWORD}@maestro-postgres:5432/quality_fabric

# Maestro V2
postgresql://maestro_v2:${MV2_DB_PASSWORD}@maestro-postgres:5432/maestro_v2

# Maestro Frontend
postgresql://maestro_frontend:${MFE_DB_PASSWORD}@maestro-postgres:5432/maestro_frontend
```

## Redis Configuration

### Multi-Namespace Setup

Single Redis instance with database separation:

```bash
# Database 0: Quality Fabric
QUALITY_FABRIC_REDIS_DB=0

# Database 1: Maestro V2
MAESTRO_V2_REDIS_DB=1

# Database 2: Maestro Frontend
MAESTRO_FRONTEND_REDIS_DB=2
```

### Connection Strings

```bash
# Quality Fabric
redis://:${MAESTRO_REDIS_PASSWORD}@maestro-redis:6379/0

# Maestro V2
redis://:${MAESTRO_REDIS_PASSWORD}@maestro-redis:6379/1

# Maestro Frontend
redis://:${MAESTRO_REDIS_PASSWORD}@maestro-redis:6379/2
```

## Grafana RBAC

### Organizations (Workspaces)

| Org ID | Name | Purpose | Dashboards |
|--------|------|---------|------------|
| 1 | Maestro Platform | Platform admins | Platform overview |
| 2 | Quality Fabric | QF team | QF metrics |
| 3 | Maestro V2 | Backend team | MV2 metrics |
| 4 | Maestro Frontend | Frontend team | MFE metrics |

### Creating Users

```bash
# Login to Grafana as admin
# Settings → Users → Invite User

# Assign to organization:
# - Quality Fabric team → Org 2 (Quality Fabric)
# - Backend team → Org 3 (Maestro V2)
# - Frontend team → Org 4 (Maestro Frontend)
```

## Prometheus Service Discovery

Prometheus automatically scrapes metrics from:

- `quality-fabric:8000/metrics`
- `maestro-v2:3000/metrics`
- `maestro-frontend:3001/metrics`

Each service is labeled:

```yaml
labels:
  service: "quality-fabric"
  team: "quality"
  layer: "application"
```

Query by service:
```promql
# Quality Fabric requests
http_requests_total{service="quality-fabric"}

# All application layer metrics
http_requests_total{layer="application"}

# Specific team metrics
http_requests_total{team="quality"}
```

## Connecting Services

### Quality Fabric Example

```yaml
# quality-fabric/docker-compose.yml
version: '3.8'

services:
  quality-fabric:
    build: .
    environment:
      # Database
      - MAESTRO_POSTGRES_URL=postgresql://quality_fabric:${QUALITY_FABRIC_DB_PASSWORD}@maestro-postgres:5432/quality_fabric

      # Cache
      - MAESTRO_CACHE_URL=redis://:${MAESTRO_REDIS_PASSWORD}@maestro-redis:6379/0

      # Monitoring
      - MAESTRO_METRICS_ENDPOINT=http://maestro-prometheus:9090
      - MAESTRO_TRACING_ENDPOINT=http://maestro-jaeger:14268/api/traces

    networks:
      - maestro-network  # Join shared network

networks:
  maestro-network:
    external: true  # Use existing network from infrastructure
```

## Maintenance

### Backup PostgreSQL

```bash
# Backup all databases
docker exec maestro-postgres pg_dumpall -U maestro_admin > maestro_backup_$(date +%Y%m%d).sql

# Backup specific database
docker exec maestro-postgres pg_dump -U maestro_admin quality_fabric > qf_backup_$(date +%Y%m%d).sql
```

### Backup Redis

```bash
# Trigger RDB snapshot
docker exec maestro-redis redis-cli -a ${MAESTRO_REDIS_PASSWORD} BGSAVE

# Copy snapshot
docker cp maestro-redis:/data/dump.rdb ./redis_backup_$(date +%Y%m%d).rdb
```

### Upgrade Services

```bash
# Pull latest images
docker-compose -f docker-compose.infrastructure.yml pull

# Recreate with new images
docker-compose -f docker-compose.infrastructure.yml up -d

# Check status
docker-compose -f docker-compose.infrastructure.yml ps
```

### Scale Redis (Add Replica)

```yaml
# Add to docker-compose.infrastructure.yml
maestro-redis-replica:
  image: redis:7-alpine
  command: redis-server --replicaof maestro-redis 6379
  depends_on:
    - maestro-redis
  networks:
    - maestro-network
```

## Troubleshooting

### PostgreSQL Connection Issues

```bash
# Check PostgreSQL is running
docker-compose -f docker-compose.infrastructure.yml ps maestro-postgres

# Check logs
docker-compose -f docker-compose.infrastructure.yml logs maestro-postgres

# Test connection
docker exec maestro-postgres psql -U maestro_admin -c "SELECT 1;"
```

### Redis Connection Issues

```bash
# Check Redis is running
docker-compose -f docker-compose.infrastructure.yml ps maestro-redis

# Test authentication
docker exec maestro-redis redis-cli -a ${MAESTRO_REDIS_PASSWORD} ping

# Check memory usage
docker exec maestro-redis redis-cli -a ${MAESTRO_REDIS_PASSWORD} INFO memory
```

### Grafana Access Issues

```bash
# Reset admin password
docker exec maestro-grafana grafana-cli admin reset-admin-password newpassword

# Check logs
docker-compose -f docker-compose.infrastructure.yml logs maestro-grafana
```

## Production Deployment

For Kubernetes production deployment, see:
- `/maestro-platform/infrastructure/kubernetes/README.md`

For AWS ECS deployment, see:
- `/maestro-platform/infrastructure/ecs/README.md`

## Architecture Principles

1. **Single Source of Truth**: One infrastructure for all services
2. **Isolation**: Services cannot access each other's data
3. **RBAC**: Grafana organizations control dashboard access
4. **Observability**: Unified metrics, logs, and traces
5. **Scalability**: Easy to add new services or replicas

## Cost Analysis

**Before** (Per-service infrastructure):
- 3x PostgreSQL = 3 instances
- 3x Redis = 3 instances
- 3x Prometheus = 3 instances
- 3x Grafana = 3 instances
- **Total**: 12 infrastructure services

**After** (Centralized):
- 1x PostgreSQL (multi-database)
- 1x Redis (multi-namespace)
- 1x Prometheus (service discovery)
- 1x Grafana (RBAC organizations)
- **Total**: 4 infrastructure services

**Savings**: 67% infrastructure cost reduction

## License

Proprietary - Maestro Platform
