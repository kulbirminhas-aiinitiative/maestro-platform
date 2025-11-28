# Strategic Template Service Consolidation & Migration Plan

**Date**: October 26, 2025
**Status**: 🎯 STRATEGIC PLAN
**Priority**: CRITICAL (Completes 100% of roadmap)
**Strategic Focus**: maestro-templates/central_registry as foundation

---

## 🎯 EXECUTIVE SUMMARY

**Strategic Decision**: **maestro-templates is our strategic template engine**

We will:
1. **Extract** central_registry as standalone "template-service" microservice
2. **Enhance** with select enterprise features from maestro-engine
3. **Migrate** templates and data seamlessly
4. **Deprecate** maestro-engine/enterprise_template_repository gradually

**Timeline**: 2-3 days (parallel execution)
**Complexity**: Medium
**Impact**: Completes 100% of 6-week roadmap

---

## 📊 CURRENT STATE ANALYSIS

### Inventory

| Component | Location | Lines | Templates | Status |
|-----------|----------|-------|-----------|--------|
| **Central Registry** | maestro-templates/services/central_registry | 6,458 | 483 | ✅ Operational |
| **Enterprise Template Repo** | maestro-engine/src/templates/enterprise_template_repository | 7,814 | ? | ✅ Operational |
| **Template Storage** | maestro-templates/storage/templates | - | 483 files | ✅ Organized |

### Template Categories (483 total)

```
maestro-templates/storage/templates/
├── ai_ml_engineer/          (persona templates)
├── backend_developer/       (backend templates)
├── database_specialist/     (database templates)
├── devops_engineer/         (DevOps templates)
├── frontend-templates/      (frontend templates)
├── frontend_developer/      (more frontend)
├── integration_tester/      (testing templates)
├── maestro-curated/         (curated collection)
├── qa_engineer/             (QA templates)
├── requirement_analyst/     (requirements templates)
├── sdlc-templates/          (SDLC workflows)
├── security_specialist/     (security templates)
├── solution_architect/      (architecture templates)
├── technical_writer/        (documentation)
└── ui_ux_designer/          (design templates)
```

### Central Registry Service Features

**Current Capabilities**:
- ✅ Template CRUD operations
- ✅ Git-based versioning
- ✅ Template search & filtering
- ✅ Workflow management
- ✅ Quality validation
- ✅ Multi-tenancy support
- ✅ RBAC security
- ✅ PostgreSQL + Redis storage
- ✅ REST API (FastAPI)

**Files**:
```
services/central_registry/
├── app.py                      (Main FastAPI app)
├── models/
│   ├── manifest.py             (Template manifest model)
│   ├── template.py             (Template model)
│   ├── workflow.py             (Workflow model)
│   └── package.py              (Package model)
├── routers/
│   ├── templates.py            (Template CRUD)
│   ├── workflow.py             (Workflow management)
│   ├── quality.py              (Quality gates)
│   ├── admin.py                (Admin operations)
│   ├── auth.py                 (Authentication)
│   └── health.py               (Health checks)
├── git_manager.py              (Git integration)
├── cache_manager.py            (Redis caching)
├── security.py                 (Security middleware)
├── dependencies.py             (FastAPI dependencies)
└── seeder.py                   (Database seeding)
```

---

## 🎯 STRATEGIC CONSOLIDATION PLAN

### Phase 1: Extract Central Registry as Microservice (Day 1 - Morning)

**Objective**: Create standalone template-service microservice

**Actions**:
```bash
# 1. Create service structure
mkdir -p services/template-service/src/template_service
mkdir -p services/template-service/templates_storage

# 2. Copy central registry source
cp -r maestro-templates/services/central_registry/* \
      services/template-service/src/template_service/

# 3. Copy template storage
cp -r maestro-templates/storage/templates/* \
      services/template-service/templates_storage/

# 4. Create configuration
# - pyproject.toml with dependencies
# - Docker configuration
# - .env.example
```

**Deliverables**:
- ✅ template-service microservice structure
- ✅ All 483 templates included
- ✅ 6,458 lines of service code
- ✅ Docker-ready configuration

**Duration**: 2 hours

### Phase 2: Enhance with Enterprise Features (Day 1 - Afternoon)

**Objective**: Integrate best features from Enterprise Template Repository

**Features to Integrate**:

1. **Semantic Search** (from Enterprise)
   - AI-powered template search
   - Better discovery experience
   - File: `semantic_search.py` (28KB)

2. **Performance Monitoring** (from Enterprise)
   - Track template usage
   - Performance metrics
   - File: `performance_monitor.py` (44KB)

3. **Governance Dashboard** (from Enterprise)
   - Template governance
   - Compliance tracking
   - File: `governance_dashboard.py` (38KB)

**Implementation**:
```python
# Add to template-service
services/template-service/src/template_service/
├── features/
│   ├── semantic_search.py     (NEW from Enterprise)
│   ├── performance_monitor.py (NEW from Enterprise)
│   └── governance.py          (NEW from Enterprise)
```

**Deliverables**:
- ✅ Semantic search integrated
- ✅ Performance monitoring added
- ✅ Governance capabilities enhanced

**Duration**: 3 hours

### Phase 3: Database Migration & Schema Merge (Day 2 - Morning)

**Objective**: Merge database schemas from both services

**Current Databases**:
- Central Registry: PostgreSQL + Redis
- Enterprise: PostgreSQL only

**Merged Schema**:
```sql
-- Core tables from Central Registry
CREATE TABLE templates (
    id UUID PRIMARY KEY,
    name VARCHAR(255),
    category VARCHAR(100),
    version VARCHAR(50),
    manifest JSONB,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE workflows (
    id UUID PRIMARY KEY,
    template_id UUID REFERENCES templates(id),
    definition JSONB,
    status VARCHAR(50)
);

-- Add from Enterprise Template Repo
CREATE TABLE template_metrics (
    id UUID PRIMARY KEY,
    template_id UUID REFERENCES templates(id),
    usage_count INTEGER,
    performance_score FLOAT,
    last_used TIMESTAMP
);

CREATE TABLE governance_rules (
    id UUID PRIMARY KEY,
    rule_type VARCHAR(100),
    rule_definition JSONB,
    active BOOLEAN
);
```

**Migration Script**:
```python
# services/template-service/migrations/merge_schemas.py
async def migrate_enterprise_data():
    """Migrate data from Enterprise Template Repo"""
    # 1. Export data from Enterprise DB
    # 2. Transform to Central Registry schema
    # 3. Import into template-service DB
    pass
```

**Deliverables**:
- ✅ Unified database schema
- ✅ Migration scripts
- ✅ Data migration complete

**Duration**: 2 hours

### Phase 4: Redis Streams Integration (Day 2 - Afternoon)

**Objective**: Add event-driven capabilities

**Streams to Add**:
```python
STREAMS = {
    "template:requests": "maestro:streams:templates:requests",
    "template:results": "maestro:streams:templates:results",
    "template:usage": "maestro:streams:templates:usage"
}
```

**Message Handler**:
```python
# services/template-service/src/template_service/message_handler.py
class TemplateMessageHandler:
    async def consume_template_requests(self):
        """Handle template requests via Redis Streams"""
        pass

    async def publish_template_usage(self):
        """Publish template usage events"""
        pass
```

**Deliverables**:
- ✅ Redis Streams integration
- ✅ Event-driven template operations
- ✅ Usage tracking events

**Duration**: 2 hours

### Phase 5: Docker & Deployment (Day 3 - Morning)

**Objective**: Production-ready deployment configuration

**Dockerfile**:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install poetry
COPY pyproject.toml ./
RUN poetry config virtualenvs.create false && \
    poetry install --no-dev

# Copy application
COPY src/ ./src/
COPY templates_storage/ ./templates_storage/

EXPOSE 8005

CMD ["uvicorn", "template_service.app:app", "--host", "0.0.0.0", "--port", "8005"]
```

**docker-compose.yml**:
```yaml
services:
  template-service:
    build: .
    ports:
      - "8005:8005"
    environment:
      DATABASE_URL: postgresql://maestro:pass@postgres:5432/maestro_templates
      REDIS_URL: redis://maestro-redis:6379/0
    volumes:
      - ./templates_storage:/app/templates_storage
    depends_on:
      - postgres
      - redis
```

**Deliverables**:
- ✅ Dockerfile
- ✅ docker-compose.yml
- ✅ .env.example
- ✅ Deployment ready

**Duration**: 1 hour

### Phase 6: Testing & Validation (Day 3 - Afternoon)

**Test Plan**:

1. **Unit Tests**
   - Template CRUD operations
   - Git integration
   - Search functionality

2. **Integration Tests**
   - Database operations
   - Redis caching
   - API endpoints

3. **End-to-End Tests**
   - Template creation workflow
   - Template usage tracking
   - Semantic search

4. **Performance Tests**
   - Template retrieval speed
   - Search performance
   - Concurrent access

**Deliverables**:
- ✅ Test suite complete
- ✅ All tests passing
- ✅ Performance validated

**Duration**: 2 hours

---

## 📋 DETAILED MIGRATION STEPS

### Step 1: Service Extraction (Parallel Track 1)

```bash
# Terminal 1: Service extraction
cd /home/ec2-user/projects/maestro-platform

# Create structure
mkdir -p services/template-service/src/template_service
mkdir -p services/template-service/templates_storage
mkdir -p services/template-service/tests

# Copy source
cp -r maestro-templates/services/central_registry/* \
      services/template-service/src/template_service/

# Copy templates
cp -r maestro-templates/storage/templates/* \
      services/template-service/templates_storage/

# Verify
ls -la services/template-service/
```

### Step 2: Enterprise Feature Integration (Parallel Track 2)

```bash
# Terminal 2: Feature integration
cd /home/ec2-user/projects/maestro-platform

# Create features directory
mkdir -p services/template-service/src/template_service/features

# Copy enterprise features
cp maestro-engine/src/templates/enterprise_template_repository/semantic_search.py \
   services/template-service/src/template_service/features/

cp maestro-engine/src/templates/enterprise_template_repository/performance_monitor.py \
   services/template-service/src/template_service/features/

cp maestro-engine/src/templates/enterprise_template_repository/governance_dashboard.py \
   services/template-service/src/template_service/features/

# Update imports
# (manual step to adjust import paths)
```

### Step 3: Configuration Files (Parallel Track 3)

**pyproject.toml**:
```toml
[tool.poetry]
name = "maestro-template-service"
version = "1.0.0"
description = "Maestro Platform - Strategic Template Engine"

[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.104.0"
uvicorn = "^0.24.0"
sqlalchemy = "^2.0.0"
asyncpg = "^0.29.0"
redis = "^5.0.0"
pydantic = "^2.0.0"
pydantic-settings = "^2.0.0"
gitpython = "^3.1.40"
pyyaml = "^6.0"
```

**.env.example**:
```bash
# Service
SERVICE_NAME=template-service
SERVICE_PORT=8005

# Database
DATABASE_URL=postgresql://maestro:password@localhost:5432/maestro_templates

# Redis
REDIS_URL=redis://localhost:6379/0

# Templates
TEMPLATES_STORAGE_PATH=/app/templates_storage

# Features
ENABLE_SEMANTIC_SEARCH=true
ENABLE_PERFORMANCE_MONITORING=true
ENABLE_GOVERNANCE=true
```

### Step 4: Main Application Update

**src/template_service/main.py**:
```python
from fastapi import FastAPI
from template_service.routers import templates, workflow, quality, admin
from template_service.features import semantic_search, performance_monitor
from template_service.message_handler import TemplateMessageHandler

app = FastAPI(
    title="Maestro Template Service",
    description="Strategic Template Engine for Maestro Platform",
    version="1.0.0"
)

# Include routers
app.include_router(templates.router)
app.include_router(workflow.router)
app.include_router(quality.router)
app.include_router(admin.router)

# Include enterprise features
app.include_router(semantic_search.router)
app.include_router(performance_monitor.router)

# Initialize message handler
message_handler = TemplateMessageHandler()

@app.on_event("startup")
async def startup():
    await message_handler.start()

@app.on_event("shutdown")
async def shutdown():
    await message_handler.stop()
```

---

## 📊 IMPACT ANALYSIS

### Before Consolidation

| Aspect | Status |
|--------|--------|
| Services | 2 separate template services |
| Maintenance | Duplicate effort |
| Features | Scattered across 2 codebases |
| Users | Confused about which to use |
| Deployment | 2 separate deployments |

### After Consolidation

| Aspect | Status |
|--------|--------|
| Services | 1 unified template service ✅ |
| Maintenance | Single codebase ✅ |
| Features | All in one place ✅ |
| Users | Clear single service ✅ |
| Deployment | 1 microservice ✅ |

### Benefits

1. **Single Source of Truth**: One template service for all templates
2. **Best of Both Worlds**: Combines git integration + enterprise features
3. **Reduced Complexity**: One codebase to maintain
4. **Better UX**: Users know where to go
5. **Scalability**: Independent microservice deployment
6. **Event-Driven**: Redis Streams for async operations

---

## 🎯 SUCCESS CRITERIA

| Criterion | Target | Validation |
|-----------|--------|------------|
| Service Extracted | Yes | template-service/ exists |
| Templates Migrated | 483 | All files in templates_storage/ |
| Code Migrated | 6,458+ lines | Source files copied |
| Enterprise Features | 3 added | semantic_search, performance_monitor, governance |
| Docker Config | Complete | Builds successfully |
| Database Schema | Merged | Migration complete |
| Redis Streams | Integrated | Message handler working |
| Tests | Passing | All tests green |
| Documentation | Complete | README comprehensive |

---

## 📚 DELIVERABLES

### Code Deliverables

1. **template-service/** - Complete microservice
2. **templates_storage/** - 483 template files
3. **Dockerfile** - Container configuration
4. **docker-compose.yml** - Deployment config
5. **pyproject.toml** - Dependencies
6. **migrations/** - Database migrations
7. **tests/** - Test suite

### Documentation Deliverables

1. **README.md** - Service documentation
2. **MIGRATION_GUIDE.md** - Migration instructions
3. **API_REFERENCE.md** - API documentation
4. **TEMPLATE_GUIDE.md** - Template usage guide

---

## 🚀 EXECUTION TIMELINE

```
Day 1 Morning (2h):   Extract service + copy templates
Day 1 Afternoon (3h): Integrate enterprise features
Day 2 Morning (2h):   Database migration
Day 2 Afternoon (2h): Redis Streams integration
Day 3 Morning (1h):   Docker & deployment config
Day 3 Afternoon (2h): Testing & validation
──────────────────────────────────────────────
Total: 12 hours (1.5 days at 8h/day)
```

### Parallel Execution Optimization

**Can run in parallel**:
- Track 1: Service extraction
- Track 2: Enterprise feature copying
- Track 3: Configuration file creation

**Must run sequentially**:
- Database migration (after service extraction)
- Redis integration (after migration)
- Testing (after all code complete)

**Optimized Timeline**: 8 hours (1 day with parallel execution)

---

## 🚨 RISKS & MITIGATION

### Risk 1: Template File Migration
**Impact**: High
**Mitigation**: Simple file copy, low risk

### Risk 2: Database Schema Conflicts
**Impact**: Medium
**Mitigation**: Create migration scripts, test thoroughly

### Risk 3: Import Path Changes
**Impact**: Low
**Mitigation**: Update imports systematically

### Risk 4: Enterprise Feature Integration
**Impact**: Medium
**Mitigation**: Copy as optional features, disable if needed

---

## ✅ IMMEDIATE NEXT STEPS

1. **Begin Service Extraction** (Track 1)
   ```bash
   mkdir -p services/template-service
   cp -r maestro-templates/services/central_registry/* services/template-service/
   ```

2. **Copy Templates** (Track 1)
   ```bash
   cp -r maestro-templates/storage/templates services/template-service/templates_storage
   ```

3. **Copy Enterprise Features** (Track 2)
   ```bash
   mkdir -p services/template-service/features
   cp maestro-engine/.../semantic_search.py services/template-service/features/
   ```

4. **Create Config Files** (Track 3)
   - pyproject.toml
   - Dockerfile
   - docker-compose.yml
   - .env.example

---

**Status**: 🎯 **READY FOR EXECUTION**

**Next Action**: Begin parallel extraction tracks

**Estimated Completion**: 8 hours (with parallel execution)

**Impact**: Completes 100% of 6-week roadmap

---

*Strategic Template Consolidation Plan*
*Generated: October 26, 2025*
*Maestro Platform - Template Service Unification*
*Final Milestone: 100% Roadmap Completion* 🎯✨
