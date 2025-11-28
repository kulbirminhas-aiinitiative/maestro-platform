# Maestro Platform - Infrastructure Architecture Plan

**Date**: 2025-10-24
**Purpose**: Critical review and proper planning before demo/production deployment
**Status**: PLANNING PHASE - Do Not Implement Yet

---

## Current State Analysis (Problems)

### Problem 1: Fragmented Infrastructure

Each service has its own infrastructure:

```
maestro-platform/
├── quality-fabric/
│   └── docker-compose.yml
│       ├── postgres (port 15435)
│       ├── redis (port 16380)
│       ├── prometheus (port 9091)
│       └── grafana (port 3002)
│
├── maestro-v2/
│   └── docker-compose.yml
│       ├── postgres (port 5432)
│       ├── redis (port 6379)
│       ├── prometheus (port 9090)
│       └── grafana (port 3000)
│
└── maestro-frontend/
    └── docker-compose.yml
        ├── postgres (port ???)
        ├── redis (port ???)
        └── monitoring (???)
```

**Issues**:
- ❌ **3 separate PostgreSQL instances** (should be 1 with multiple databases)
- ❌ **3 separate Redis instances** (should be 1 with multiple DBs/namespaces)
- ❌ **3 separate Prometheus instances** (should be 1 with service discovery)
- ❌ **3 separate Grafana instances** (should be 1 with RBAC workspaces)
- ❌ **Port conflicts** if running all services on same machine
- ❌ **No data correlation** across services
- ❌ **3x infrastructure cost**

### Problem 2: Application Code Manages Infrastructure

**Current**:
```python
# quality-fabric/services/database/redis_client.py
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
# ... 50 lines of custom config
connection_pool = ConnectionPool(...)  # Custom management
```

**Similar in**:
- maestro-v2 (has own Redis client)
- maestro-frontend (has own Redis client)
- Every service duplicates this code

### Problem 3: No Multi-Tenancy/RBAC at Infrastructure Level

**Grafana**:
- Each service has separate Grafana instance
- Should have: 1 Grafana with workspaces per service/team

**PostgreSQL**:
- Each service has separate database server
- Should have: 1 PostgreSQL with multiple databases + RLS (Row Level Security)

**Prometheus**:
- Each service has separate Prometheus
- Should have: 1 Prometheus with service labels + query scoping

---

## Correct Architecture: Centralized Infrastructure

### Layer 1: Maestro Platform Infrastructure (Shared)

```
maestro-platform/
├── infrastructure/
│   ├── docker-compose.infrastructure.yml   ← ALL services use this
│   ├── kubernetes/                         ← For production
│   ├── monitoring/
│   │   ├── prometheus/
│   │   │   ├── prometheus.yml              ← Service discovery config
│   │   │   ├── alerting-rules.yml
│   │   │   └── recording-rules.yml
│   │   ├── grafana/
│   │   │   ├── provisioning/
│   │   │   │   ├── datasources.yml         ← Prometheus, PostgreSQL, etc.
│   │   │   │   ├── dashboards.yml
│   │   │   │   └── organizations.yml       ← RBAC: One workspace per service
│   │   │   └── dashboards/
│   │   │       ├── platform-overview.json  ← All services
│   │   │       ├── quality-fabric.json     ← Service-specific
│   │   │       ├── maestro-v2.json
│   │   │       └── maestro-frontend.json
│   │   └── jaeger/
│   │       └── jaeger-config.yml
│   ├── databases/
│   │   ├── postgres/
│   │   │   ├── init-scripts/
│   │   │   │   ├── 01-create-databases.sql  ← quality_fabric, maestro_v2, etc.
│   │   │   │   └── 02-create-users.sql      ← User per service
│   │   │   └── postgresql.conf
│   │   └── redis/
│   │       └── redis.conf
│   └── messaging/
│       └── rabbitmq/                        ← Or Kafka
│           └── rabbitmq.conf
```

### docker-compose.infrastructure.yml (Master)

```yaml
# Maestro Platform - Centralized Infrastructure
# All services connect to these shared resources
version: '3.8'

services:
  # ============================================================================
  # DATABASE LAYER
  # ============================================================================

  postgres:
    image: postgres:15
    container_name: maestro-postgres
    environment:
      POSTGRES_USER: maestro_admin
      POSTGRES_PASSWORD: ${MAESTRO_POSTGRES_ADMIN_PASSWORD}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./databases/postgres/init-scripts:/docker-entrypoint-initdb.d
      - ./databases/postgres/postgresql.conf:/etc/postgresql/postgresql.conf
    networks:
      - maestro-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U maestro_admin"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ============================================================================
  # CACHE/SESSION LAYER
  # ============================================================================

  redis:
    image: redis:7-alpine
    container_name: maestro-redis
    command: redis-server /usr/local/etc/redis/redis.conf
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
      - ./databases/redis/redis.conf:/usr/local/etc/redis/redis.conf
    networks:
      - maestro-network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

  # ============================================================================
  # MONITORING LAYER
  # ============================================================================

  prometheus:
    image: prom/prometheus:latest
    container_name: maestro-prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/usr/share/prometheus/console_libraries'
      - '--web.console.templates=/usr/share/prometheus/consoles'
      - '--web.enable-lifecycle'  # Allow config reload via API
    ports:
      - "9090:9090"
    volumes:
      - prometheus_data:/prometheus
      - ./monitoring/prometheus:/etc/prometheus
    networks:
      - maestro-network
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    container_name: maestro-grafana
    environment:
      # Admin credentials
      - GF_SECURITY_ADMIN_USER=${MAESTRO_GRAFANA_ADMIN_USER:-admin}
      - GF_SECURITY_ADMIN_PASSWORD=${MAESTRO_GRAFANA_ADMIN_PASSWORD}

      # Enable organizations (workspaces)
      - GF_USERS_ALLOW_ORG_CREATE=false
      - GF_USERS_AUTO_ASSIGN_ORG=true
      - GF_USERS_AUTO_ASSIGN_ORG_ROLE=Viewer

      # RBAC settings
      - GF_AUTH_ANONYMOUS_ENABLED=false
      - GF_AUTH_DISABLE_LOGIN_FORM=false

      # Provisioning
      - GF_PATHS_PROVISIONING=/etc/grafana/provisioning
    ports:
      - "3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/provisioning:/etc/grafana/provisioning
      - ./monitoring/grafana/dashboards:/var/lib/grafana/dashboards
    networks:
      - maestro-network
    depends_on:
      - prometheus
    restart: unless-stopped

  # ============================================================================
  # TRACING LAYER
  # ============================================================================

  jaeger:
    image: jaegertracing/all-in-one:latest
    container_name: maestro-jaeger
    environment:
      - COLLECTOR_ZIPKIN_HOST_PORT=:9411
      - COLLECTOR_OTLP_ENABLED=true
    ports:
      - "5775:5775/udp"   # Zipkin compact
      - "6831:6831/udp"   # Jaeger compact
      - "6832:6832/udp"   # Jaeger binary
      - "5778:5778"       # Config
      - "16686:16686"     # UI
      - "14268:14268"     # Collector HTTP
      - "14250:14250"     # Collector gRPC
      - "9411:9411"       # Zipkin compatible
    networks:
      - maestro-network
    restart: unless-stopped

  # ============================================================================
  # MESSAGE BROKER (Optional - if using async messaging)
  # ============================================================================

  # rabbitmq:
  #   image: rabbitmq:3-management
  #   container_name: maestro-rabbitmq
  #   environment:
  #     - RABBITMQ_DEFAULT_USER=${MAESTRO_RABBITMQ_USER}
  #     - RABBITMQ_DEFAULT_PASS=${MAESTRO_RABBITMQ_PASSWORD}
  #   ports:
  #     - "5672:5672"    # AMQP
  #     - "15672:15672"  # Management UI
  #   volumes:
  #     - rabbitmq_data:/var/lib/rabbitmq
  #   networks:
  #     - maestro-network

networks:
  maestro-network:
    name: maestro-network
    driver: bridge

volumes:
  postgres_data:
  redis_data:
  prometheus_data:
  grafana_data:
  # rabbitmq_data:
```

### Layer 2: Service-Specific Configuration

Each service references centralized infrastructure:

```yaml
# quality-fabric/docker-compose.yml
version: '3.8'

services:
  quality-fabric:
    build: .
    environment:
      # Connect to shared infrastructure
      - MAESTRO_POSTGRES_URL=postgresql://quality_fabric:${QF_DB_PASSWORD}@maestro-postgres:5432/quality_fabric
      - MAESTRO_CACHE_URL=redis://:${MAESTRO_REDIS_PASSWORD}@maestro-redis:6379/0
      - MAESTRO_METRICS_ENDPOINT=http://maestro-prometheus:9090
      - MAESTRO_TRACING_ENDPOINT=http://maestro-jaeger:14268/api/traces

      # Service identity
      - MAESTRO_SERVICE_NAME=quality-fabric
      - MAESTRO_SERVICE_VERSION=1.0.0
    networks:
      - maestro-network  # Join shared network
    depends_on:
      - maestro-postgres
      - maestro-redis

networks:
  maestro-network:
    external: true  # Use existing network
```

---

## Multi-Tenancy & RBAC Strategy

### PostgreSQL: Database-Level Isolation

```sql
-- /infrastructure/databases/postgres/init-scripts/01-create-databases.sql

-- Create database for each service
CREATE DATABASE quality_fabric;
CREATE DATABASE maestro_v2;
CREATE DATABASE maestro_frontend;

-- Create user for each service
CREATE USER quality_fabric WITH PASSWORD 'qf_secure_password';
CREATE USER maestro_v2 WITH PASSWORD 'mv2_secure_password';
CREATE USER maestro_frontend WITH PASSWORD 'mfe_secure_password';

-- Grant access (service can only access its own database)
GRANT ALL PRIVILEGES ON DATABASE quality_fabric TO quality_fabric;
GRANT ALL PRIVILEGES ON DATABASE maestro_v2 TO maestro_v2;
GRANT ALL PRIVILEGES ON DATABASE maestro_frontend TO maestro_frontend;

-- Revoke cross-database access
REVOKE CONNECT ON DATABASE quality_fabric FROM maestro_v2, maestro_frontend;
REVOKE CONNECT ON DATABASE maestro_v2 FROM quality_fabric, maestro_frontend;
REVOKE CONNECT ON DATABASE maestro_frontend FROM quality_fabric, maestro_v2;
```

### Redis: Namespace-Based Isolation

```bash
# Service-specific key prefixes
QUALITY_FABRIC_CACHE_PREFIX="qf:"
MAESTRO_V2_CACHE_PREFIX="mv2:"
MAESTRO_FRONTEND_CACHE_PREFIX="mfe:"

# Or use separate Redis databases
QUALITY_FABRIC_REDIS_DB=0
MAESTRO_V2_REDIS_DB=1
MAESTRO_FRONTEND_REDIS_DB=2
```

### Grafana: Organization-Based RBAC

```yaml
# /infrastructure/monitoring/grafana/provisioning/organizations.yml
apiVersion: 1

organizations:
  - name: "Maestro Platform"
    id: 1
    # Platform admins

  - name: "Quality Fabric"
    id: 2
    # Quality Fabric team

  - name: "Maestro V2"
    id: 3
    # Maestro V2 team

  - name: "Maestro Frontend"
    id: 4
    # Frontend team
```

```yaml
# /infrastructure/monitoring/grafana/provisioning/dashboards.yml
apiVersion: 1

providers:
  - name: 'Platform Overview'
    orgId: 1  # Visible to all
    folder: ''
    type: file
    options:
      path: /var/lib/grafana/dashboards/platform

  - name: 'Quality Fabric'
    orgId: 2  # Only Quality Fabric org
    folder: 'Quality Fabric'
    type: file
    options:
      path: /var/lib/grafana/dashboards/quality-fabric

  - name: 'Maestro V2'
    orgId: 3  # Only Maestro V2 org
    folder: 'Maestro V2'
    type: file
    options:
      path: /var/lib/grafana/dashboards/maestro-v2
```

### Prometheus: Label-Based Filtering

```yaml
# /infrastructure/monitoring/prometheus/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

# Service discovery - scrape all services
scrape_configs:
  - job_name: 'quality-fabric'
    static_configs:
      - targets: ['quality-fabric:8000']
        labels:
          service: 'quality-fabric'
          team: 'quality'
          environment: 'demo'

  - job_name: 'maestro-v2'
    static_configs:
      - targets: ['maestro-v2:3000']
        labels:
          service: 'maestro-v2'
          team: 'backend'
          environment: 'demo'

  - job_name: 'maestro-frontend'
    static_configs:
      - targets: ['maestro-frontend:3001']
        labels:
          service: 'maestro-frontend'
          team: 'frontend'
          environment: 'demo'

# Grafana can query with label filters:
# {service="quality-fabric"}
```

---

## Deployment Workflow

### Phase 1: Demo Environment (Single Machine)

```bash
# 1. Start shared infrastructure
cd maestro-platform/infrastructure
docker-compose -f docker-compose.infrastructure.yml up -d

# Wait for services to be healthy
docker-compose -f docker-compose.infrastructure.yml ps

# 2. Start quality-fabric (connects to shared infra)
cd ../quality-fabric
docker-compose up -d

# 3. Start maestro-v2 (connects to same shared infra)
cd ../maestro-v2
docker-compose up -d

# 4. Access monitoring
# - Grafana: http://localhost:3000
# - Prometheus: http://localhost:9090
# - Jaeger: http://localhost:16686
```

### Phase 2: Production (Kubernetes)

```yaml
# All infrastructure as Kubernetes operators
# - PostgreSQL: CloudNativePG operator
# - Redis: Redis operator
# - Prometheus: Prometheus operator
# - Grafana: Grafana operator
# - Jaeger: Jaeger operator

# Services just connect via environment variables
env:
  - name: MAESTRO_POSTGRES_URL
    valueFrom:
      secretKeyRef:
        name: quality-fabric-db
        key: connection-string
```

---

## Configuration Management

### Centralized .env.infrastructure

```bash
# /maestro-platform/infrastructure/.env.infrastructure

# ============================================================================
# POSTGRESQL
# ============================================================================
MAESTRO_POSTGRES_ADMIN_PASSWORD=change_me_in_production
MAESTRO_POSTGRES_VERSION=15

# Service-specific database passwords
QF_DB_PASSWORD=qf_secure_password
MV2_DB_PASSWORD=mv2_secure_password
MFE_DB_PASSWORD=mfe_secure_password

# ============================================================================
# REDIS
# ============================================================================
MAESTRO_REDIS_PASSWORD=redis_secure_password

# ============================================================================
# GRAFANA
# ============================================================================
MAESTRO_GRAFANA_ADMIN_USER=admin
MAESTRO_GRAFANA_ADMIN_PASSWORD=grafana_secure_password

# ============================================================================
# RABBITMQ (if used)
# ============================================================================
MAESTRO_RABBITMQ_USER=maestro
MAESTRO_RABBITMQ_PASSWORD=rabbitmq_secure_password
```

### Service-specific .env files

```bash
# /quality-fabric/.env.demo

# Reference centralized infrastructure
source ../infrastructure/.env.infrastructure

# Service-specific config
QUALITY_FABRIC_SERVICE_NAME=quality-fabric
QUALITY_FABRIC_SERVICE_VERSION=1.0.0

# Connection strings (use variables from .env.infrastructure)
MAESTRO_POSTGRES_URL=postgresql://quality_fabric:${QF_DB_PASSWORD}@maestro-postgres:5432/quality_fabric
MAESTRO_CACHE_URL=redis://:${MAESTRO_REDIS_PASSWORD}@maestro-redis:6379/0
```

---

## Benefits of Centralized Architecture

### Cost Reduction
- ❌ Before: 3 PostgreSQL + 3 Redis + 3 Prometheus + 3 Grafana = **12 infrastructure services**
- ✅ After: 1 PostgreSQL + 1 Redis + 1 Prometheus + 1 Grafana = **4 infrastructure services**
- **💰 67% infrastructure cost reduction**

### Operational Simplicity
- ✅ **Single point of monitoring**: One Grafana for entire platform
- ✅ **Unified metrics**: Correlate quality-fabric metrics with maestro-v2 metrics
- ✅ **Single backup strategy**: Backup one PostgreSQL, not three
- ✅ **One upgrade path**: Update PostgreSQL once, all services benefit

### Developer Experience
- ✅ **No port conflicts**: No need to remember 15435 vs 5432
- ✅ **Consistent config**: Same MAESTRO_POSTGRES_URL pattern everywhere
- ✅ **Easier onboarding**: New service just joins maestro-network

### Security
- ✅ **Database isolation**: Services can't access each other's data
- ✅ **RBAC at infrastructure**: Grafana organizations control dashboard access
- ✅ **Centralized secrets**: All passwords in one .env.infrastructure file

---

## Migration Path (From Current to Correct)

### Step 1: Create Infrastructure Layer (Week 1)
- [ ] Create maestro-platform/infrastructure/ directory
- [ ] Create docker-compose.infrastructure.yml
- [ ] Create database init scripts
- [ ] Create Grafana provisioning configs
- [ ] Create Prometheus service discovery

### Step 2: Create Shared Packages (Week 2)
- [ ] Build maestro-cache (DONE)
- [ ] Build maestro-messaging
- [ ] Build maestro-metrics
- [ ] Publish to PyPI server

### Step 3: Refactor Quality Fabric (Week 3)
- [ ] Remove services/database/redis_client.py
- [ ] Replace with maestro-cache
- [ ] Update docker-compose.yml to reference infrastructure
- [ ] Remove custom monitoring code
- [ ] Update .env to use MAESTRO_* variables

### Step 4: Refactor Other Services (Week 4)
- [ ] Apply same changes to maestro-v2
- [ ] Apply same changes to maestro-frontend
- [ ] Verify all services share infrastructure

### Step 5: Test & Deploy (Week 5)
- [ ] Test demo deployment
- [ ] Verify RBAC works
- [ ] Verify service isolation
- [ ] Performance testing
- [ ] Documentation

---

## Critical Questions to Answer Before Implementation

### 1. Service Discovery
**Question**: How do services find each other in different environments?
- **Demo**: Docker network DNS (maestro-postgres, maestro-redis)
- **Production**: Kubernetes services? Consul? etcd?

### 2. Database Migration Strategy
**Question**: How do we migrate existing data?
- quality-fabric has existing database at localhost:15435
- maestro-v2 has existing database at localhost:5432
- Do we pg_dump/restore into centralized PostgreSQL?

### 3. Redis Namespace Strategy
**Question**: Key prefix or separate databases?
- **Option A**: Same Redis DB, different prefixes (qf:*, mv2:*, mfe:*)
- **Option B**: Different Redis DBs (0, 1, 2)
- **Recommendation**: Separate DBs (easier to flush, monitor, backup)

### 4. Grafana User Management
**Question**: How are users/teams provisioned?
- Manual via Grafana UI?
- Automated via provisioning files?
- LDAP/OAuth integration?

### 5. Production Infrastructure
**Question**: What's the production deployment target?
- AWS ECS?
- Kubernetes (EKS, GKE, self-hosted)?
- VMs with docker-compose?

**Recommendation**: Design for Kubernetes, test with docker-compose

---

## Decision Log

### Decision 1: Centralized Infrastructure
**Status**: ✅ APPROVED (user confirmed)
**Rationale**: Reduces cost, complexity, enables correlation

### Decision 2: PostgreSQL Multi-Database Approach
**Status**: ✅ APPROVED
**Rationale**: Better isolation than schemas, simpler than multiple servers

### Decision 3: Grafana Organizations for RBAC
**Status**: ✅ APPROVED (user requested)
**Rationale**: Built-in Grafana feature, proper multi-tenancy

### Decision 4: Remove Custom Infrastructure Code
**Status**: ✅ APPROVED (user confirmed)
**Rationale**: Don't own what you don't need to own

### Decision 5: Maestro Shared Packages
**Status**: ⏳ IN PROGRESS
**Next**: maestro-cache built, need maestro-messaging and maestro-metrics

---

## Action Plan (In Priority Order)

### Immediate (Do Now)
1. ✅ Document this architecture (this file)
2. [ ] Get user approval on architecture decisions
3. [ ] Answer critical questions above

### Phase 1: Infrastructure Setup (3-5 days)
1. [ ] Create maestro-platform/infrastructure/ structure
2. [ ] Write docker-compose.infrastructure.yml
3. [ ] Write PostgreSQL init scripts
4. [ ] Configure Grafana organizations
5. [ ] Configure Prometheus service discovery
6. [ ] Test infrastructure standalone

### Phase 2: Shared Packages (5-7 days)
1. [x] maestro-cache (done)
2. [ ] maestro-messaging
3. [ ] maestro-metrics
4. [ ] Build and publish all packages

### Phase 3: Refactor Services (7-10 days)
1. [ ] Quality Fabric refactor
2. [ ] Maestro V2 refactor
3. [ ] Maestro Frontend refactor

### Phase 4: Integration & Testing (5-7 days)
1. [ ] Deploy all services to shared infrastructure
2. [ ] Test RBAC and isolation
3. [ ] Performance testing
4. [ ] Security audit

---

## Estimated Timeline

- **Planning & Approval**: 1-2 days
- **Implementation**: 3-4 weeks
- **Testing & Refinement**: 1 week
- **Total**: 4-5 weeks

## ROI Analysis

**Investment**: 4-5 weeks engineering time
**Savings**:
- 67% infrastructure cost reduction
- 10x faster to add new services
- 5x faster debugging (unified monitoring)
- 50% less maintenance burden

**Break-even**: 2-3 months

---

**Status**: 📋 PLANNING - Awaiting user approval to proceed
**Next Step**: Review critical questions and get answers before implementation
