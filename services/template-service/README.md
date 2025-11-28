# Maestro Template Service

**Strategic Template Engine & Registry for Maestro Platform**

Version: 1.0.0
Port: 8005
Status: ✅ Production Ready

---

## 📋 Overview

The **Maestro Template Service** is the unified, strategic template engine for the Maestro Platform. It provides centralized template management, git-based versioning, quality validation, and multi-tenancy support for all platform templates.

### Key Features

- ✅ **Template CRUD Operations** - Full lifecycle management
- ✅ **Git-Based Versioning** - Track changes with GitPython
- ✅ **Template Search & Filtering** - Powerful query capabilities
- ✅ **Workflow Management** - Template-driven workflows
- ✅ **Quality Validation** - Automated quality gates
- ✅ **Multi-Tenancy Support** - Isolated tenant environments
- ✅ **RBAC Security** - Role-based access control
- ✅ **PostgreSQL + Redis** - Robust storage layer
- ✅ **Event-Driven Architecture** - Redis Streams integration
- ✅ **REST API** - FastAPI-powered endpoints

---

## 🏗️ Architecture

### Components

```
template-service/
├── src/template_service/
│   ├── app.py                    # Main FastAPI application
│   ├── models/                   # Data models
│   │   ├── manifest.py           # Template manifest model
│   │   ├── template.py           # Template model
│   │   ├── workflow.py           # Workflow model
│   │   └── package.py            # Package model
│   ├── routers/                  # API routes
│   │   ├── templates.py          # Template CRUD endpoints
│   │   ├── workflow.py           # Workflow management
│   │   ├── quality.py            # Quality gate endpoints
│   │   ├── admin.py              # Admin operations
│   │   ├── auth.py               # Authentication
│   │   └── health.py             # Health checks
│   ├── git_manager.py            # Git integration
│   ├── cache_manager.py          # Redis caching
│   ├── security.py               # Security middleware
│   ├── dependencies.py           # FastAPI dependencies
│   ├── message_handler.py        # Redis Streams consumer
│   └── seeder.py                 # Database seeding
├── templates_storage/            # 483 template files
│   ├── ai_ml_engineer/
│   ├── backend_developer/
│   ├── database_specialist/
│   ├── devops_engineer/
│   ├── frontend_developer/
│   ├── qa_engineer/
│   ├── security_specialist/
│   └── ... (15 categories total)
├── tests/                        # Test suite
├── pyproject.toml                # Dependencies
├── Dockerfile                    # Container config
├── docker-compose.yml            # Deployment config
└── .env.example                  # Environment template
```

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **API Framework** | FastAPI | High-performance async API |
| **Database** | PostgreSQL 15 | Template metadata storage |
| **Cache** | Redis 7 | Caching + message streaming |
| **ORM** | SQLAlchemy 2.0 | Database operations |
| **Validation** | Pydantic 2.0 | Data validation |
| **Versioning** | GitPython | Git integration |
| **Event Bus** | Redis Streams | Async messaging |

---

## 📦 Template Inventory

### 483 Templates Across 15 Categories

| Category | Count | Purpose |
|----------|-------|---------|
| ai_ml_engineer | ~30 | AI/ML workflows & models |
| backend_developer | ~35 | Backend services & APIs |
| database_specialist | ~25 | Database schemas & migrations |
| devops_engineer | ~40 | CI/CD & infrastructure |
| frontend_developer | ~50 | UI components & pages |
| integration_tester | ~30 | Integration test suites |
| maestro-curated | ~45 | Platform-curated templates |
| qa_engineer | ~40 | Test plans & strategies |
| requirement_analyst | ~25 | Requirements documentation |
| sdlc-templates | ~35 | SDLC workflows |
| security_specialist | ~30 | Security policies & tests |
| solution_architect | ~40 | Architecture patterns |
| technical_writer | ~28 | Documentation templates |
| ui_ux_designer | ~30 | Design systems |
| frontend-templates | ~20 | Additional frontend |

**Total: 483 production-ready templates**

---

## 🚀 Getting Started

### Prerequisites

- Docker & Docker Compose
- PostgreSQL 15+
- Redis 7+
- Python 3.11+ (for local development)

### Quick Start

1. **Clone and Navigate**
   ```bash
   cd /home/ec2-user/projects/maestro-platform/services/template-service
   ```

2. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start Services**
   ```bash
   docker-compose up -d
   ```

4. **Verify Health**
   ```bash
   curl http://localhost:8005/health
   ```

5. **Access API Documentation**
   ```
   http://localhost:8005/docs
   ```

### Local Development

```bash
# Install dependencies
poetry install

# Run database migrations
poetry run alembic upgrade head

# Seed initial templates
poetry run python src/template_service/seeder.py

# Start development server
poetry run uvicorn template_service.app:app --reload --port 8005
```

---

## 🔌 API Endpoints

### Template Operations

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/templates` | GET | List all templates |
| `/api/v1/templates` | POST | Create new template |
| `/api/v1/templates/{id}` | GET | Get template by ID |
| `/api/v1/templates/{id}` | PUT | Update template |
| `/api/v1/templates/{id}` | DELETE | Delete template |
| `/api/v1/templates/search` | POST | Search templates |
| `/api/v1/templates/{id}/versions` | GET | Get version history |

### Workflow Operations

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/workflows` | GET | List workflows |
| `/api/v1/workflows` | POST | Create workflow |
| `/api/v1/workflows/{id}` | GET | Get workflow |
| `/api/v1/workflows/{id}/execute` | POST | Execute workflow |

### Quality Operations

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/quality/validate` | POST | Validate template |
| `/api/v1/quality/score` | POST | Score template quality |
| `/api/v1/quality/report` | GET | Quality report |

### Admin Operations

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/admin/stats` | GET | Service statistics |
| `/api/v1/admin/cache/clear` | POST | Clear cache |
| `/api/v1/admin/git/sync` | POST | Sync git repository |

---

## 📊 Redis Streams Integration

### Streams

```python
STREAMS = {
    "template:requests": "maestro:streams:templates:requests",
    "template:results": "maestro:streams:templates:results",
    "template:usage": "maestro:streams:templates:usage"
}
```

### Message Format

**Template Request**:
```json
{
  "template_id": "uuid",
  "operation": "retrieve|create|update|delete",
  "tenant_id": "tenant-123",
  "user_id": "user-456",
  "parameters": {},
  "timestamp": "2025-10-26T12:00:00Z"
}
```

**Template Result**:
```json
{
  "request_id": "req-uuid",
  "template_id": "uuid",
  "status": "success|error",
  "result": {},
  "error": null,
  "duration_ms": 150
}
```

---

## 🔐 Security

### Authentication

- JWT-based authentication
- Token expiration: 30 minutes (configurable)
- Refresh token support

### Authorization

- Role-Based Access Control (RBAC)
- Roles: admin, editor, viewer
- Tenant isolation enforced

### API Security

```python
# Protected endpoint example
@router.get("/templates", dependencies=[Depends(verify_token)])
async def list_templates(
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_tenant)
):
    # Only returns templates for user's tenant
    pass
```

---

## 📈 Quality Gates

### Validation Rules

Templates must meet the following criteria:

| Criteria | Requirement | Weight |
|----------|-------------|--------|
| **Documentation** | README.md present | 30% |
| **Examples** | Usage examples included | 20% |
| **Metadata** | Complete manifest | 20% |
| **Structure** | Valid file structure | 15% |
| **Dependencies** | Dependencies declared | 15% |

**Minimum Score**: 70/100 to pass

### Quality Scoring

```python
# Example quality check
{
  "template_id": "backend-api-template",
  "quality_score": 85,
  "checks": {
    "documentation": "pass",
    "examples": "pass",
    "metadata": "pass",
    "structure": "pass",
    "dependencies": "warning"
  },
  "recommendations": [
    "Add more usage examples",
    "Update dependency versions"
  ]
}
```

---

## 🔄 Git Integration

### Version Control

All templates are version-controlled with Git:

```bash
# Automatic versioning on template update
template.update() → git commit -m "Update template: backend-api"

# View version history
GET /api/v1/templates/{id}/versions
```

### Git Operations

| Operation | Trigger | Action |
|-----------|---------|--------|
| Create | Template created | `git add` + `git commit` |
| Update | Template modified | `git commit` |
| Delete | Template deleted | `git rm` + `git commit` |
| Sync | Manual/scheduled | `git pull` + `git push` |

---

## 🧪 Testing

### Run Tests

```bash
# All tests
poetry run pytest

# With coverage
poetry run pytest --cov=template_service --cov-report=html

# Specific test file
poetry run pytest tests/test_templates.py

# Integration tests
poetry run pytest tests/integration/
```

### Test Structure

```
tests/
├── unit/
│   ├── test_models.py
│   ├── test_git_manager.py
│   └── test_cache_manager.py
├── integration/
│   ├── test_api_endpoints.py
│   ├── test_database.py
│   └── test_redis_streams.py
└── e2e/
    ├── test_template_lifecycle.py
    └── test_workflow_execution.py
```

---

## 📊 Monitoring

### Health Endpoint

```bash
curl http://localhost:8005/health

# Response
{
  "status": "healthy",
  "service": "template-service",
  "version": "1.0.0",
  "database": "connected",
  "redis": "connected",
  "templates_count": 483
}
```

### Metrics

Available metrics:
- Total templates
- Templates by category
- API request rate
- Response times
- Error rates
- Cache hit ratio
- Git sync status

---

## 🐳 Docker Deployment

### Build Image

```bash
docker build -t maestro-template-service:1.0.0 .
```

### Run Container

```bash
docker run -d \
  --name template-service \
  -p 8005:8005 \
  -e DATABASE_URL=postgresql://maestro:pass@postgres:5432/maestro_templates \
  -e REDIS_URL=redis://redis:6379/0 \
  -v ./templates_storage:/app/templates_storage \
  maestro-template-service:1.0.0
```

### Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f template-service

# Stop services
docker-compose down

# Rebuild
docker-compose build --no-cache
```

---

## 🔧 Configuration

### Environment Variables

Key configuration options (see `.env.example` for full list):

```bash
# Service
SERVICE_PORT=8005

# Database
DATABASE_URL=postgresql://maestro:pass@postgres:5432/maestro_templates

# Redis
REDIS_URL=redis://redis:6379/0

# Storage
TEMPLATES_STORAGE_PATH=/app/templates_storage

# Security
SECRET_KEY=your-secret-key
ENABLE_RBAC=true

# Features
ENABLE_QUALITY_GATES=true
ENABLE_PERFORMANCE_MONITORING=true
MIN_TEMPLATE_QUALITY_SCORE=70
```

---

## 📚 Template Management

### Template Structure

```yaml
# manifest.yaml
name: backend-api-template
version: 1.0.0
description: REST API backend template
category: backend_developer
author: Maestro Team
tags: [api, rest, fastapi, postgresql]

dependencies:
  - fastapi: "^0.104.0"
  - sqlalchemy: "^2.0.0"

files:
  - src/main.py
  - src/models.py
  - src/routes.py
  - README.md
  - tests/

quality_score: 85
```

### Using Templates

```python
# Python SDK example
from template_service_client import TemplateClient

client = TemplateClient(base_url="http://localhost:8005")

# Search templates
templates = await client.search(
    category="backend_developer",
    tags=["api", "fastapi"]
)

# Get template
template = await client.get_template("backend-api-template")

# Create from template
project = await template.instantiate(
    project_name="my-api",
    parameters={"database": "postgresql"}
)
```

---

## 🚀 Production Deployment

### Pre-Deployment Checklist

- [ ] Database migrations applied
- [ ] Redis cluster configured
- [ ] Environment variables set
- [ ] SSL certificates installed
- [ ] Monitoring configured
- [ ] Backup strategy defined
- [ ] Git repository initialized
- [ ] Quality gates configured

### Deployment Steps

1. **Database Setup**
   ```bash
   # Run migrations
   poetry run alembic upgrade head
   ```

2. **Seed Templates**
   ```bash
   # Import existing templates
   poetry run python src/template_service/seeder.py
   ```

3. **Start Service**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

4. **Verify**
   ```bash
   curl https://template-service.maestro.com/health
   ```

---

## 🔍 Troubleshooting

### Common Issues

**Issue: Database connection failed**
```bash
# Check PostgreSQL is running
docker ps | grep postgres

# Check DATABASE_URL in .env
cat .env | grep DATABASE_URL
```

**Issue: Templates not loading**
```bash
# Check templates directory
ls -la templates_storage/

# Check permissions
chmod -R 755 templates_storage/
```

**Issue: Redis connection failed**
```bash
# Check Redis is running
docker ps | grep redis

# Test Redis connection
redis-cli -h maestro-redis ping
```

---

## 📖 Additional Resources

- [API Documentation](http://localhost:8005/docs) - Interactive Swagger UI
- [Roadmap](../../ROADMAP_100_PERCENT_COMPLETE.md) - Complete platform roadmap
- [Architecture](../../STRATEGIC_TEMPLATE_CONSOLIDATION_PLAN.md) - Consolidation plan
- [Integration Guide](../../INTEGRATION_GUIDE.md) - Integration patterns

---

## 🤝 Contributing

### Adding New Templates

1. Create template directory in `templates_storage/{category}/`
2. Add `manifest.yaml` with metadata
3. Include README.md with usage instructions
4. Add example files
5. Run quality validation
6. Submit for review

### Development Workflow

```bash
# Create feature branch
git checkout -b feature/new-template-category

# Make changes
# ... add templates ...

# Run tests
poetry run pytest

# Commit changes
git commit -m "Add new template category"

# Push and create PR
git push origin feature/new-template-category
```

---

## 📄 License

Copyright © 2025 Maestro Platform Team

---

**Template Service** | Version 1.0.0 | Port 8005 | ✅ Production Ready

*Strategic Template Engine for Maestro Platform*
*Powering 483 production templates across 15 categories*
*Complete template lifecycle management with quality assurance* 🚀✨
