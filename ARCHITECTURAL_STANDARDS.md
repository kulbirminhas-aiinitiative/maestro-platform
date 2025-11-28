# Maestro Platform - Architectural Standards & Deployment Guide

**Date**: 2025-10-25
**Status**: ARCHITECTURE DEFINED ✅
**Compliance**: ALL SERVICES MUST FOLLOW THIS PATTERN

---

## 🎯 Architecture Overview

### **The Golden Rule: Infrastructure First, Services Second**

```
┌─────────────────────────────────────────────────────────────┐
│  INFRASTRUCTURE LAYER (Start First)                         │
│  cd infrastructure && docker-compose -f                     │
│      docker-compose.infrastructure.yml up -d                │
├─────────────────────────────────────────────────────────────┤
│  ├── maestro-postgres:25432    (all databases)             │
│  ├── maestro-redis:27379        (all caches)               │
│  ├── maestro-prometheus:29090  (monitoring)                │
│  └── maestro-grafana:23000     (dashboards)                │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  APPLICATION LAYER (Start After Infrastructure)            │
├─────────────────────────────────────────────────────────────┤
│  quality-fabric     → maestro-postgres + maestro-redis     │
│  maestro-templates  → maestro-postgres + maestro-redis     │
│  maestro-gateway    → maestro-postgres + maestro-redis     │
│  conductor          → maestro-postgres + maestro-redis     │
└─────────────────────────────────────────────────────────────┘
```

---

## 📁 File Structure Standard

### **Every Service MUST Have:**

```
service-name/
├── docker-compose.yml           # Uses shared infrastructure
├── .env.shared                  # Service-specific config
├── Dockerfile                   # Standard build
├── Dockerfile.nexus             # Nexus-optimized build (optional)
└── README.md                    # Deployment instructions
```

---

## 📋 Docker Compose Template (MANDATORY)

### **Correct Pattern:**

```yaml
# Service Name - Uses Shared Infrastructure
# IMPORTANT: Start infrastructure first:
#   cd ../infrastructure && docker-compose -f docker-compose.infrastructure.yml up -d
#
# Then start this service:
#   docker-compose up -d

version: '3.8'

services:
  service-name:
    build: .
    container_name: service-name
    ports:
      - "${SERVICE_PORT:-8000}:8000"
    environment:
      # Use shared PostgreSQL
      - DATABASE_URL=postgresql://${SERVICE_DB_USER}:${SERVICE_DB_PASSWORD}@maestro-postgres:5432/${SERVICE_DB_NAME}
      # Use shared Redis (each service gets its own DB number)
      - REDIS_URL=redis://:${MAESTRO_REDIS_PASSWORD}@maestro-redis:6379/${SERVICE_REDIS_DB}
    networks:
      - maestro-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    labels:
      - "maestro.service=service-name"
      - "maestro.layer=application"

networks:
  maestro-network:
    external: true
    name: maestro-network
```

### **❌ ANTI-PATTERN (DO NOT DO THIS):**

```yaml
# WRONG: Creating own postgres/redis
services:
  service-postgres:    # ❌ NO! Use maestro-postgres
    image: postgres:15
  
  service-redis:       # ❌ NO! Use maestro-redis
    image: redis:7

  service-app:
    depends_on:
      - service-postgres  # ❌ Should depend on infrastructure, not service DB
      - service-redis
```

---

## 🔧 Environment Configuration Standard

### **infrastructure/.env (Shared Secrets)**

```bash
# Infrastructure-level configuration
MAESTRO_POSTGRES_ADMIN_USER=maestro_admin
MAESTRO_POSTGRES_ADMIN_PASSWORD=secure_password_here
MAESTRO_REDIS_PASSWORD=secure_redis_password_here

# Service DB passwords (referenced by services)
QUALITY_FABRIC_DB_PASSWORD=qf_db_secure_2025
MAESTRO_V2_DB_PASSWORD=mv2_db_secure_2025
MAESTRO_FRONTEND_DB_PASSWORD=mfe_db_secure_2025
```

### **service/.env.shared (Service Config)**

```bash
# Application settings
SERVICE_PORT=8000
LOG_LEVEL=info

# Database config (connects to maestro-postgres)
SERVICE_DB_NAME=service_db
SERVICE_DB_USER=service_user
SERVICE_DB_PASSWORD=from_infrastructure_env

# Redis config (connects to maestro-redis)
SERVICE_REDIS_DB=0  # Each service uses different DB number
MAESTRO_REDIS_PASSWORD=from_infrastructure_env
```

---

## 🚀 Deployment Process

### **Step 1: Infrastructure Setup**

```bash
cd /home/ec2-user/projects/maestro-platform/infrastructure

# Start shared infrastructure
docker-compose -f docker-compose.infrastructure.yml up -d

# Verify infrastructure health
docker ps | grep maestro-
docker exec maestro-postgres pg_isready
docker exec maestro-redis redis-cli ping
```

### **Step 2: Create Service Databases**

```bash
# For each service, create its database
docker exec -it maestro-postgres psql -U maestro_admin << EOF
CREATE DATABASE quality_fabric;
CREATE USER quality_fabric WITH PASSWORD 'qf_db_secure_2025';
GRANT ALL PRIVILEGES ON DATABASE quality_fabric TO quality_fabric;

CREATE DATABASE maestro_templates;
CREATE USER maestro_template_user WITH PASSWORD 'changeme_secure_password';
GRANT ALL PRIVILEGES ON DATABASE maestro_templates TO maestro_template_user;
EOF
```

### **Step 3: Deploy Services**

```bash
# Deploy Quality Fabric
cd /home/ec2-user/projects/maestro-platform/quality-fabric
docker-compose up -d

# Deploy Templates
cd /home/ec2-user/projects/maestro-platform/maestro-templates
docker-compose up -d

# Verify services
curl http://localhost:8000/api/health
curl http://localhost:9600/health
```

---

## 📊 Service-to-Infrastructure Mapping

| Service | Port | PostgreSQL DB | Redis DB | Network |
|---------|------|--------------|----------|---------|
| Quality Fabric | 8000 | `quality_fabric` | 0 | maestro-network |
| Maestro Templates | 9600 | `maestro_templates` | 1 | maestro-network |
| Maestro Gateway | 8080 | `maestro_gateway` | 2 | maestro-network |
| Conductor | 8003 | `conductor` | 3 | maestro-network |

**Infrastructure Services:**
- PostgreSQL: `maestro-postgres:25432` (external), `5432` (internal)
- Redis: `maestro-redis:27379` (external), `6379` (internal)
- Prometheus: `maestro-prometheus:29090`
- Grafana: `maestro-grafana:23000`

---

## ✅ Compliance Checklist

Before deploying any service, verify:

- [ ] Service `docker-compose.yml` does NOT create postgres/redis containers
- [ ] Service uses `networks: maestro-network: external: true`
- [ ] Service connects to `maestro-postgres:5432` (internal port)
- [ ] Service connects to `maestro-redis:6379` (internal port)
- [ ] Service has unique Redis DB number (0-15)
- [ ] Service has `.env.shared` with proper configuration
- [ ] Service has health check endpoint
- [ ] Service has `maestro.service` and `maestro.layer` labels

---

## 🔍 Troubleshooting

### **Service can't connect to PostgreSQL**

```bash
# 1. Check infrastructure is running
docker ps | grep maestro-postgres

# 2. Check network connectivity
docker exec service-name ping maestro-postgres

# 3. Check DATABASE_URL env var
docker exec service-name env | grep DATABASE_URL

# 4. Test PostgreSQL connection
docker exec service-name pg_isready -h maestro-postgres -p 5432
```

### **Service can't connect to Redis**

```bash
# 1. Check infrastructure is running
docker ps | grep maestro-redis

# 2. Check network connectivity
docker exec service-name ping maestro-redis

# 3. Test Redis connection
docker exec service-name redis-cli -h maestro-redis -p 6379 -a 'password' ping
```

### **Service not on maestro-network**

```bash
# 1. Check service network
docker inspect service-name | grep -A 10 Networks

# 2. Connect service to network manually
docker network connect maestro-network service-name

# 3. Recreate service with correct network
docker-compose down
docker-compose up -d
```

---

## 📚 Reference Files

### **Correctly Configured:**
✅ `/infrastructure/docker-compose.infrastructure.yml`
✅ `/quality-fabric/docker-compose.yml`
✅ `/quality-fabric/.env.shared`
✅ `/maestro-templates/docker-compose.yml`
✅ `/maestro-templates/.env.shared`

### **Deployment Scripts:**
✅ `/infrastructure/deploy-to-demo-enhanced.sh` (standard pattern)
✅ `/home/ec2-user/deployment/deploy-dev-github.sh` (GitHub-based)

### **Deprecated:**
❌ `/quality-fabric/docker-compose.shared.yml` (old pattern)
❌ Individual service postgres/redis containers

---

## 🎓 Key Principles

1. **Single Source of Truth**: Infrastructure layer owns all shared resources
2. **Network Isolation**: All services communicate via `maestro-network`
3. **Port Mapping**: External ports (25432, 27379) for admin, internal (5432, 6379) for services
4. **Database Isolation**: One PostgreSQL instance, multiple databases
5. **Cache Isolation**: One Redis instance, multiple DB numbers
6. **Configuration Hierarchy**: Infrastructure → Service → Container

---

## 🚨 Common Mistakes to Avoid

1. ❌ Creating service-specific postgres/redis containers
2. ❌ Using `depends_on` for infrastructure services
3. ❌ Hardcoding infrastructure hostnames (use env vars)
4. ❌ Using external ports (25432, 27379) from containers
5. ❌ Sharing Redis DB numbers between services
6. ❌ Forgetting to create service network as external
7. ❌ Not creating database in postgres before starting service

---

**END OF ARCHITECTURAL STANDARDS**

**Compliance**: MANDATORY for all Maestro Platform services
**Last Updated**: 2025-10-25
**Approved By**: Platform Architecture Team
