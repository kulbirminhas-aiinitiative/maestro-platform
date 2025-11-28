# Week 5: Automation Service (CARS) - Extraction Analysis

**Date**: October 26, 2025
**Status**: 📋 Analysis Complete
**Phase**: Week 5 of 6-week roadmap
**Service**: Continuous Auto-Repair Service (CARS)
**Estimated Effort**: 5-7 days

---

## 🎯 Executive Summary

The Continuous Auto-Repair Service (CARS) is ready for extraction from Quality Fabric into a standalone microservice. This 1,514-line autonomous system detects, analyzes, and heals software errors automatically.

**Key Facts**:
- **Size**: 1,514 lines of Python code
- **Files**: 6 Python modules + comprehensive documentation
- **Status**: Production-ready (Phase 1 complete)
- **Infrastructure**: ✅ Ready (Redis Streams configured in Week 3)
- **Dependencies**: Minimal external dependencies

---

## 📊 Current State Analysis

### Code Inventory

| File | Lines | Purpose |
|------|-------|---------|
| `error_monitor.py` | 445 | Continuous error detection (4 error types) |
| `repair_orchestrator.py` | 453 | Repair workflow management |
| `api_endpoints.py` | 334 | RESTful API (8 endpoints) |
| `validation_engine.py` | 174 | Multi-stage validation |
| `notification_service.py` | 85 | Multi-channel alerts |
| `__init__.py` | 23 | Package exports |
| **Total** | **1,514** | **Complete system** |

### Current Location
```
quality-fabric/
└── services/
    └── automation/
        ├── __init__.py
        ├── error_monitor.py
        ├── repair_orchestrator.py
        ├── api_endpoints.py
        ├── validation_engine.py
        ├── notification_service.py
        └── README.md (10.7KB)
```

---

## 🔗 Dependency Analysis

### Python Dependencies

#### Required Dependencies
```python
# Web Framework
fastapi >= 0.104.0
pydantic >= 2.0.0
uvicorn >= 0.24.0

# Async & Utilities
asyncio (stdlib)
aiofiles >= 23.0.0

# Quality Fabric Integration
maestro-core-logging >= 1.0.0  # Shared package
```

#### Internal Dependencies
```python
# From Quality Fabric
from ..ai.autonomous_test_healer import AutonomousTestHealer, HealingResult
from ..core.validation_engine import ValidationEngine  # If not local

# Standard Library
import asyncio
import logging
import json
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime
import uuid
```

**Key Finding**: The service has a critical dependency on `AutonomousTestHealer` from Quality Fabric's AI service. This needs to be:
1. Extracted as a shared package first, OR
2. Accessed via API from Quality Fabric

---

## 🏗️ Target Architecture

### Microservice Structure

```
maestro-platform/
├── services/
│   └── automation-service/
│       ├── src/
│       │   └── automation_service/
│       │       ├── __init__.py
│       │       ├── main.py                    # FastAPI app
│       │       ├── error_monitor.py           # Copied from QF
│       │       ├── repair_orchestrator.py     # Copied from QF
│       │       ├── validation_engine.py       # Copied from QF
│       │       ├── notification_service.py    # Copied from QF
│       │       ├── message_handler.py         # NEW: Redis Streams integration
│       │       └── config.py                  # NEW: Configuration
│       ├── tests/
│       │   ├── test_error_monitor.py
│       │   ├── test_repair_orchestrator.py
│       │   └── test_message_handler.py
│       ├── Dockerfile
│       ├── docker-compose.yml
│       ├── pyproject.toml
│       ├── README.md
│       └── .env.example
└── shared/
    └── packages/
        └── test-healer/                       # NEW: Extract AutonomousTestHealer
            └── maestro_test_healer/
                └── autonomous_test_healer.py
```

---

## 🔄 Message-Based Architecture Design

### Redis Streams Integration

The CARS service will use Redis Streams (configured in Week 3) for:
1. Job queue management
2. Event-driven healing
3. Status updates
4. Result reporting

#### Stream Configuration

```python
# Stream names (from infrastructure/redis-streams-config.md)
STREAMS = {
    "automation_jobs": "maestro:streams:automation:jobs",
    "test_healing": "maestro:streams:automation:healing",
    "error_monitoring": "maestro:streams:automation:errors",
    "validation": "maestro:streams:automation:validation",
    "results": "maestro:streams:automation:results"
}

# Consumer groups
CONSUMER_GROUPS = {
    "automation_workers": "maestro-automation-workers",
    "healing_workers": "maestro-healing-workers",
    "monitoring_workers": "maestro-monitoring-workers"
}
```

#### Message Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    CARS Message Flow                         │
└─────────────────────────────────────────────────────────────┘

1. Error Detection:
   ErrorMonitor → [automation:errors] → RepairOrchestrator

2. Healing Request:
   API/Stream → [automation:jobs] → RepairOrchestrator

3. Healing Execution:
   RepairOrchestrator → TestHealer → ValidationEngine

4. Result Publishing:
   RepairOrchestrator → [automation:results] → Subscribers

5. Status Updates:
   RepairOrchestrator → [automation:healing] → Dashboard
```

#### Message Schema

```json
// Job Message
{
  "job_id": "uuid",
  "type": "heal_test_failure",
  "priority": "high|medium|low",
  "payload": {
    "project_path": "/path/to/project",
    "error_type": "test_failure",
    "file_path": "tests/test_auth.py",
    "error_details": {...},
    "config": {
      "auto_fix": true,
      "confidence_threshold": 0.75
    }
  },
  "timestamp": "2025-10-26T10:00:00Z"
}

// Result Message
{
  "job_id": "uuid",
  "repair_id": "uuid",
  "status": "success|failed|skipped",
  "result": {
    "fix_applied": true,
    "confidence_score": 0.85,
    "validation_passed": true,
    "execution_time": 12.5,
    "changes": [...]
  },
  "timestamp": "2025-10-26T10:00:15Z"
}

// Status Update
{
  "orchestrator_id": "uuid",
  "status": "running|idle|error",
  "active_repairs": 3,
  "queue_size": 12,
  "statistics": {
    "total_errors_detected": 50,
    "successful_repairs": 45,
    "success_rate": "90%"
  },
  "timestamp": "2025-10-26T10:00:00Z"
}
```

---

## 🐳 Docker Configuration

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY pyproject.toml ./
RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-dev

# Copy application
COPY src/ ./src/

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8003/health || exit 1

# Run service
CMD ["uvicorn", "automation_service.main:app", "--host", "0.0.0.0", "--port", "8003"]
```

### docker-compose.yml Integration

```yaml
services:
  automation-service:
    build: ./services/automation-service
    container_name: maestro-automation-service
    ports:
      - "8003:8003"
    environment:
      - REDIS_HOST=maestro-redis
      - REDIS_PORT=6379
      - POSTGRES_HOST=maestro-postgres
      - POSTGRES_DB=maestro_automation
      - LOG_LEVEL=INFO
      - PYPI_INDEX_URL=http://maestro-nexus:8081/repository/pypi-group/simple
    volumes:
      - ./logs/automation:/app/logs
      - /var/run/docker.sock:/var/run/docker.sock  # For Docker-based testing
    depends_on:
      - redis
      - postgres
      - nexus
    networks:
      - maestro-network
    restart: unless-stopped
```

---

## 🔌 API Design

### RESTful Endpoints (Existing)

```
POST   /api/automation/start          # Start continuous monitoring
POST   /api/automation/stop           # Stop monitoring
GET    /api/automation/status         # Get orchestrator status
GET    /api/automation/history        # Get repair history
GET    /api/automation/statistics     # Get statistics
POST   /api/automation/heal           # Manual heal request
GET    /api/automation/active-orchestrators
GET    /api/automation/health         # Health check
```

### New Message-Based API

```
# Message Consumers (Redis Streams)
XREADGROUP automation_workers job_worker maestro:streams:automation:jobs
XREADGROUP healing_workers heal_worker maestro:streams:automation:healing

# Message Publishers
XADD maestro:streams:automation:errors * {error_event}
XADD maestro:streams:automation:results * {repair_result}
XADD maestro:streams:automation:healing * {status_update}
```

---

## 📋 Extraction Plan

### Phase 1: Dependency Extraction (Day 1-2)

**Task 1.1: Extract AutonomousTestHealer as Shared Package**
```bash
# Create package structure
mkdir -p shared/packages/test-healer/maestro_test_healer

# Copy source
cp quality-fabric/services/ai/autonomous_test_healer.py \
   shared/packages/test-healer/maestro_test_healer/

# Create pyproject.toml
cat > shared/packages/test-healer/pyproject.toml <<EOF
[tool.poetry]
name = "maestro-test-healer"
version = "1.0.0"
description = "Maestro Platform - Autonomous Test Healing with 7 Strategies"

[tool.poetry.dependencies]
python = "^3.11"
maestro-core-logging = "^1.0.0"
EOF

# Build and publish
cd shared/packages/test-healer
poetry build
curl -u "admin:admin123" \
  -F "pypi.asset=@dist/maestro_test_healer-1.0.0-py3-none-any.whl" \
  "http://localhost:28081/service/rest/v1/components?repository=pypi-hosted"
```

**Task 1.2: Update CARS Dependencies**
```python
# Before
from ..ai.autonomous_test_healer import AutonomousTestHealer

# After
from maestro_test_healer import AutonomousTestHealer
```

### Phase 2: Service Extraction (Day 2-3)

**Task 2.1: Create Service Structure**
```bash
mkdir -p services/automation-service/src/automation_service
mkdir -p services/automation-service/tests
```

**Task 2.2: Copy and Adapt Code**
```bash
# Copy automation service files
cp quality-fabric/services/automation/*.py \
   services/automation-service/src/automation_service/

# Copy README
cp quality-fabric/services/automation/README.md \
   services/automation-service/
```

**Task 2.3: Create Main Application**
Create `services/automation-service/src/automation_service/main.py`:
```python
from fastapi import FastAPI
from automation_service.api_endpoints import router
from automation_service.message_handler import MessageHandler
import logging

app = FastAPI(
    title="Maestro Automation Service (CARS)",
    description="Continuous Auto-Repair Service",
    version="1.0.0"
)

# Include REST API
app.include_router(router)

# Start message handler
message_handler = MessageHandler()

@app.on_event("startup")
async def startup():
    await message_handler.start()
    logging.info("CARS started successfully")

@app.on_event("shutdown")
async def shutdown():
    await message_handler.stop()
    logging.info("CARS shutdown complete")

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "automation"}
```

### Phase 3: Redis Streams Integration (Day 3-4)

**Task 3.1: Create Message Handler**
Create `services/automation-service/src/automation_service/message_handler.py`:
```python
import asyncio
import json
import logging
from typing import Dict, Any
import redis.asyncio as redis

logger = logging.getLogger(__name__)

class MessageHandler:
    def __init__(self):
        self.redis = None
        self.is_running = False

    async def start(self):
        """Start consuming messages from Redis Streams"""
        self.redis = await redis.from_url("redis://maestro-redis:6379")
        self.is_running = True

        # Start consumer tasks
        asyncio.create_task(self.consume_jobs())
        asyncio.create_task(self.consume_healing_requests())

    async def consume_jobs(self):
        """Consume jobs from automation:jobs stream"""
        while self.is_running:
            try:
                messages = await self.redis.xreadgroup(
                    groupname="maestro-automation-workers",
                    consumername="worker-1",
                    streams={"maestro:streams:automation:jobs": ">"},
                    count=10,
                    block=5000
                )

                for stream, messages_list in messages:
                    for message_id, data in messages_list:
                        await self.process_job(message_id, data)
                        await self.redis.xack(
                            stream,
                            "maestro-automation-workers",
                            message_id
                        )
            except Exception as e:
                logger.error(f"Error consuming jobs: {e}")
                await asyncio.sleep(5)

    async def process_job(self, message_id: str, data: Dict[str, Any]):
        """Process a job message"""
        logger.info(f"Processing job: {message_id}")
        # Implement job processing logic

    async def publish_result(self, result: Dict[str, Any]):
        """Publish result to results stream"""
        await self.redis.xadd(
            "maestro:streams:automation:results",
            result
        )
```

### Phase 4: Configuration & Environment (Day 4)

**Task 4.1: Create Configuration**
Create `services/automation-service/src/automation_service/config.py`:
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Service
    service_name: str = "automation-service"
    service_port: int = 8003

    # Redis
    redis_host: str = "maestro-redis"
    redis_port: int = 6379

    # PostgreSQL
    postgres_host: str = "maestro-postgres"
    postgres_port: int = 5432
    postgres_db: str = "maestro_automation"
    postgres_user: str = "maestro"
    postgres_password: str

    # Healing Configuration
    default_confidence_threshold: float = 0.75
    max_concurrent_repairs: int = 3

    # Monitoring
    log_level: str = "INFO"

    class Config:
        env_file = ".env"

settings = Settings()
```

**Task 4.2: Create .env.example**
```bash
# Service
SERVICE_PORT=8003

# Redis
REDIS_HOST=maestro-redis
REDIS_PORT=6379

# PostgreSQL
POSTGRES_HOST=maestro-postgres
POSTGRES_PORT=5432
POSTGRES_DB=maestro_automation
POSTGRES_USER=maestro
POSTGRES_PASSWORD=change_me

# Healing
DEFAULT_CONFIDENCE_THRESHOLD=0.75
MAX_CONCURRENT_REPAIRS=3

# Monitoring
LOG_LEVEL=INFO
```

### Phase 5: Docker & Deployment (Day 5)

**Task 5.1: Create Dockerfile** (see Docker Configuration section above)

**Task 5.2: Update Main docker-compose.yml**
Add automation-service to `/home/ec2-user/projects/maestro-platform/docker-compose.yml`

**Task 5.3: Database Setup**
```sql
-- Create database
CREATE DATABASE maestro_automation;

-- Create tables
CREATE TABLE repair_history (
    id SERIAL PRIMARY KEY,
    repair_id UUID NOT NULL,
    orchestrator_id UUID NOT NULL,
    error_type VARCHAR(50),
    status VARCHAR(20),
    confidence_score FLOAT,
    execution_time FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_repair_orchestrator ON repair_history(orchestrator_id);
CREATE INDEX idx_repair_created ON repair_history(created_at);
```

### Phase 6: Testing & Validation (Day 6-7)

**Task 6.1: Unit Tests**
```bash
pytest services/automation-service/tests/
```

**Task 6.2: Integration Tests**
```bash
# Start service
docker-compose up automation-service

# Test REST API
curl http://localhost:8003/health
curl -X POST http://localhost:8003/api/automation/start \
  -H "Content-Type: application/json" \
  -d '{"project_path": "/test/project"}'

# Test Redis Streams
redis-cli XADD maestro:streams:automation:jobs * \
  job_id "test-1" \
  type "heal_test_failure" \
  project_path "/test"
```

**Task 6.3: End-to-End Test**
```python
# Test complete workflow
1. Publish job to Redis Stream
2. Verify job is consumed
3. Check orchestrator starts
4. Monitor healing progress
5. Verify result published
6. Check database persistence
```

---

## 🎯 Success Criteria

| Criteria | Target | Validation Method |
|----------|--------|-------------------|
| Service Extraction | Complete | Files in services/automation-service/ |
| Dependencies | Resolved | pip install succeeds |
| REST API | Functional | All 8 endpoints return 200 |
| Redis Integration | Working | Messages consumed from streams |
| Docker Build | Success | docker build completes |
| Health Check | Passing | /health returns 200 |
| Database Connection | Active | Can read/write repair history |
| Test Coverage | >80% | pytest --cov |
| Documentation | Complete | README.md comprehensive |
| Production Ready | Yes | Runs for 24h without errors |

---

## 📊 Impact Analysis

### Before Extraction
- **Location**: quality-fabric/services/automation/
- **Coupling**: Tightly coupled to Quality Fabric
- **Scalability**: Limited by Quality Fabric monolith
- **Deployment**: Must redeploy entire Quality Fabric
- **Monitoring**: Mixed with QF logs

### After Extraction
- **Location**: services/automation-service/
- **Coupling**: Loose coupling via Redis Streams + REST API
- **Scalability**: Independent horizontal scaling
- **Deployment**: Deploy CARS independently
- **Monitoring**: Dedicated logs, metrics, traces

### Benefits
1. **Independent Deployment**: Update CARS without touching Quality Fabric
2. **Scalability**: Scale healing workers independently
3. **Resilience**: CARS failure doesn't affect Quality Fabric
4. **Multi-tenancy**: Support multiple projects simultaneously
5. **Message-Based**: Async, non-blocking architecture

---

## 🚨 Risks & Mitigation

### Risk 1: AutonomousTestHealer Dependency
**Impact**: High
**Probability**: Medium
**Mitigation**:
1. Extract test healer as shared package first
2. Verify no circular dependencies
3. Create adapter layer if needed

### Risk 2: Message Queue Complexity
**Impact**: Medium
**Probability**: Low
**Mitigation**:
1. Comprehensive Redis Streams testing
2. Fallback to REST API if streams fail
3. Dead letter queue for failed messages

### Risk 3: State Management
**Impact**: Medium
**Probability**: Medium
**Mitigation**:
1. Use PostgreSQL for persistent state
2. Redis for ephemeral state
3. Implement state recovery mechanism

### Risk 4: Performance
**Impact**: Low
**Probability**: Low
**Mitigation**:
1. Load testing before production
2. Implement rate limiting
3. Circuit breaker for external calls

---

## 📈 Timeline

```
Day 1-2:  Extract AutonomousTestHealer package
Day 2-3:  Extract CARS service files
Day 3-4:  Implement Redis Streams integration
Day 4:    Configuration & environment setup
Day 5:    Docker configuration & deployment
Day 6-7:  Testing & validation

Total: 7 days
```

---

## 🎓 Integration Points

### Upstream Dependencies
- **Redis Streams**: Job queue, events, results
- **PostgreSQL**: Repair history, configuration
- **Nexus**: Package dependencies
- **AutonomousTestHealer**: Core healing logic (shared package)

### Downstream Consumers
- **Quality Fabric**: Can still use CARS via REST API
- **Maestro Engine**: Workflow integration via Redis
- **Dashboard**: Real-time status via Redis Streams
- **CI/CD**: Automated healing in pipelines

### API Gateway Integration
```yaml
# Add to API Gateway routes
/automation/*:
  service: automation-service
  port: 8003
  health_check: /health
  circuit_breaker: true
  timeout: 30s
```

---

## 📚 Documentation Deliverables

1. **README.md**: Service overview, setup, usage
2. **API.md**: Complete API reference
3. **ARCHITECTURE.md**: System design, message flows
4. **DEPLOYMENT.md**: Docker, K8s deployment guides
5. **TROUBLESHOOTING.md**: Common issues, solutions
6. **MIGRATION.md**: Migrating from Quality Fabric integration

---

## ✅ Next Actions

1. **Immediate**: Approve this analysis
2. **Day 1**: Begin AutonomousTestHealer extraction
3. **Day 2**: Start CARS service extraction
4. **Week completion**: CARS deployed and tested

---

## 🎯 Success Metrics

After completion, we should have:
- ✅ 1 new microservice (CARS)
- ✅ 1 new shared package (test-healer)
- ✅ Total packages: 17 → 18
- ✅ Redis Streams integration working
- ✅ Independent scalability for healing
- ✅ 24/7 autonomous error healing

---

**Status**: 📋 **ANALYSIS COMPLETE - READY FOR EXECUTION**
**Next Step**: Begin Phase 1 - Extract AutonomousTestHealer package
**Infrastructure**: ✅ Ready (Redis Streams configured)
**Estimated Timeline**: 7 days
**Confidence Level**: ⭐⭐⭐⭐⭐ (Very High)

---

*Week 5 Automation Service Analysis*
*Generated: October 26, 2025*
*Maestro Platform - Microservice Extraction Initiative*
*Part of 6-week modernization roadmap*
