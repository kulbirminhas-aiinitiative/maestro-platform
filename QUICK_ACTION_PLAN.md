# Quick Action Plan: Multi-repo Migration

**TL;DR**: Step-by-step guide to split maestro-platform into independent repositories

## Overview

**Goal**: Transform current monolithic structure into 7 independent repositories with clean API boundaries

**Timeline**: 4-6 weeks

**Approach**: Incremental, low-risk migration

## Prerequisites

- [ ] Stakeholder approval for multi-repo approach
- [ ] Package registry decision made (GitHub Packages / devpi / CodeArtifact)
- [ ] Git hosting ready (GitHub / GitLab)
- [ ] Team availability confirmed

## Week 1: Setup Foundation

### Day 1-2: Create Package Registry

#### If using GitHub Packages:
```bash
# 1. Configure Poetry
poetry config repositories.maestro https://github.com/YOUR_ORG/maestro-shared

# 2. Add to each package's pyproject.toml
[tool.poetry]
repository = "https://github.com/YOUR_ORG/maestro-shared"
```

#### If using self-hosted devpi:
```bash
# 1. Run devpi server
docker run -d --name devpi \
  -p 3141:3141 \
  -v /data/devpi:/data \
  muccg/devpi

# 2. Setup user and index
devpi use http://localhost:3141
devpi user -c maestro password=YOUR_PASSWORD
devpi index -c maestro/prod bases=root/pypi
```

### Day 3-4: Create maestro-shared Repository

```bash
# 1. Create new repository
mkdir maestro-shared
cd maestro-shared

# 2. Copy shared packages
cp -r ../maestro-platform/shared/packages .
mv packages/* .
rmdir packages

# 3. Create root pyproject.toml
cat > pyproject.toml << 'EOF'
[build-system]
requires = ["poetry-core>=1.0.0"]
build-backend = "poetry.core.masonry.api"

[project]
name = "maestro-shared"
version = "1.0.0"
description = "Shared libraries for Maestro ecosystem"
EOF

# 4. Initialize git
git init
git add .
git commit -m "Initial commit: Shared libraries"

# 5. Push to remote
git remote add origin git@github.com:YOUR_ORG/maestro-shared.git
git push -u origin main
```

### Day 5: Publish Initial Versions

```bash
#!/bin/bash
# publish_shared.sh

PACKAGES=(
    "core-api"
    "core-auth"
    "core-config"
    "core-logging"
    "core-db"
    "core-messaging"
    "monitoring"
)

for pkg in "${PACKAGES[@]}"; do
    echo "Publishing $pkg..."
    cd $pkg

    # Update package metadata
    poetry version 0.1.0

    # Build and publish
    poetry build
    poetry publish --repository maestro

    cd ..
done

echo "✅ All shared packages published!"
```

## Week 2: Extract quality-fabric (TAAS)

### Day 1: Create quality-fabric Repository

```bash
# 1. Create new repository
mkdir quality-fabric
cd quality-fabric

# 2. Copy code (exclude maestro dependencies)
rsync -av --exclude='__pycache__' \
  ../maestro-platform/quality-fabric/ ./

# 3. Initialize git
git init
git add .
git commit -m "Initial commit: Quality Fabric TAAS Platform"
git remote add origin git@github.com:YOUR_ORG/quality-fabric.git
git push -u origin main
```

### Day 2-3: Remove Maestro Coupling

```bash
# 1. Update pyproject.toml
# Remove path dependencies to maestro packages

# BEFORE:
# maestro-core-api = {path = "../shared/packages/core-api"}

# AFTER (if needed at all - probably not):
# maestro-core-api = "^0.1.0"

# 2. Remove any direct imports of maestro code

# 3. Make testing configuration-driven
cat > config/test_targets.yml << 'EOF'
targets:
  - name: maestro-platform
    api_base: http://localhost:8000
    frontend_url: http://localhost:4200
    test_suites: [api, frontend, e2e]

  - name: custom-app
    api_base: https://custom-app.com/api
    frontend_url: https://custom-app.com
    test_suites: [api, frontend]
EOF
```

### Day 4: Test Independence

```bash
# 1. Clean install (should work without maestro-platform)
cd quality-fabric
poetry install

# 2. Run unit tests (no external dependencies)
poetry run pytest tests/unit/

# 3. Run integration tests against Maestro via API
export TEST_TARGET=http://localhost:8000
poetry run pytest tests/integration/

# 4. Verify can test other applications
export TEST_TARGET=https://example.com/api
poetry run pytest tests/integration/
```

## Week 3: Extract Frontend and Backend

### Day 1-2: Create maestro-frontend Repository

```bash
# 1. Create repository
mkdir maestro-frontend
cd maestro-frontend

# 2. Copy frontend code
rsync -av --exclude='node_modules' \
  --exclude='__pycache__' \
  ../maestro-platform/maestro-frontend/ ./

# 3. Update environment configuration
cat > .env.example << 'EOF'
# Backend API URL (configurable)
VITE_API_BASE=http://localhost:8000

# Can point to any backend implementing the API contract
# VITE_API_BASE=http://custom-backend.com/api
# VITE_API_BASE=http://production.maestro.com/api
EOF

# 4. Document API contract expectations
cat > API_CONTRACT.md << 'EOF'
# Backend API Contract

Maestro Frontend expects backends to implement:

## Endpoints

### Workflows
- POST /api/workflows - Create workflow
- GET /api/workflows/:id - Get workflow
- GET /api/workflows - List workflows

### WebSocket
- WS /ws - Real-time updates

See OpenAPI spec: ./openapi.yml
EOF

# 5. Initialize git
git init
git add .
git commit -m "Initial commit: Maestro Frontend"
git push -u origin main
```

### Day 3-4: Create maestro-engine Repository

```bash
# 1. Create repository
mkdir maestro-engine
cd maestro-engine

# 2. Copy backend code
rsync -av --exclude='__pycache__' \
  ../maestro-platform/maestro-engine/ ./

# 3. Update dependencies to use published packages
# Edit pyproject.toml:
cat >> pyproject.toml << 'EOF'

[tool.poetry.dependencies]
python = "^3.11"

# Published shared packages
maestro-core-api = "^0.1.0"
maestro-core-auth = "^0.1.0"
maestro-core-logging = "^0.1.0"
maestro-core-config = "^0.1.0"
# ... others as needed

[[tool.poetry.source]]
name = "maestro"
url = "YOUR_REGISTRY_URL"
priority = "supplemental"
EOF

# 4. Generate OpenAPI spec
cat > scripts/generate_openapi.py << 'EOF'
from fastapi.openapi.utils import get_openapi
from src.main import app
import json

openapi_schema = get_openapi(
    title="Maestro Engine API",
    version="1.0.0",
    routes=app.routes,
)

with open("openapi.json", "w") as f:
    json.dump(openapi_schema, f, indent=2)

print("✅ OpenAPI spec generated: openapi.json")
EOF

# 5. Initialize git
git init
git add .
git commit -m "Initial commit: Maestro Engine"
git push -u origin main
```

### Day 5: Verify Independence

```bash
# Test frontend with custom backend URL
cd maestro-frontend
VITE_API_BASE=http://test-backend.com npm run dev

# Test backend standalone
cd maestro-engine
poetry install
poetry run uvicorn src.main:app --reload

# Verify frontend can connect to backend via API only
curl http://localhost:8000/api/health
```

## Week 4: Extract Remaining Components

### maestro-hive

```bash
mkdir maestro-hive
rsync -av ../maestro-platform/maestro-hive/ maestro-hive/
cd maestro-hive

# Fix dependencies
# Update pyproject.toml to use published packages

git init
git add .
git commit -m "Initial commit: Maestro Hive SDLC Engine"
git push -u origin main
```

### maestro-ml-platform (synth)

```bash
mkdir maestro-ml-platform
rsync -av ../maestro-platform/synth/ maestro-ml-platform/
cd maestro-ml-platform

# Rename internal references
find . -type f -name "*.py" -exec sed -i 's/synth/maestro_ml/g' {} +

git init
git add .
git commit -m "Initial commit: Maestro ML Platform"
git push -u origin main
```

### maestro-templates

```bash
mkdir maestro-templates
rsync -av ../maestro-platform/maestro-templates/ maestro-templates/
cd maestro-templates

git init
git add .
git commit -m "Initial commit: Maestro Templates v1.0.0"
git tag v1.0.0
git push -u origin main --tags
```

## Week 5: Integration and Testing

### Create Integration Test Suite

```bash
# Create maestro-integration-tests repository
mkdir maestro-integration-tests
cd maestro-integration-tests

cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  maestro-engine:
    image: maestro-engine:latest
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/maestro

  maestro-frontend:
    image: maestro-frontend:latest
    ports:
      - "4200:4200"
    environment:
      - VITE_API_BASE=http://maestro-engine:8000

  quality-fabric:
    image: quality-fabric:latest
    environment:
      - TEST_TARGET=http://maestro-engine:8000
    depends_on:
      - maestro-engine
    command: pytest tests/integration/

  db:
    image: postgres:14
    environment:
      - POSTGRES_PASSWORD=postgres
EOF

# Test full stack
docker-compose up
```

### Verify API Contracts

```bash
# 1. Validate backend produces correct OpenAPI spec
cd maestro-engine
poetry run python scripts/generate_openapi.py

# 2. Validate frontend expects correct contract
cd maestro-frontend
# Check TypeScript types match API contract

# 3. Use tools to validate
npm install -g @openapitools/openapi-generator-cli

openapi-generator-cli validate -i ../maestro-engine/openapi.json
```

## Week 6: Documentation and Cleanup

### Create Documentation Site

```bash
mkdir maestro-docs
cd maestro-docs

cat > README.md << 'EOF'
# Maestro Platform Documentation

## Architecture

Maestro is a modular platform with swappable components:

### Repositories
- **maestro-engine**: Backend API ([repo](https://github.com/org/maestro-engine))
- **maestro-frontend**: React UI ([repo](https://github.com/org/maestro-frontend))
- **maestro-hive**: SDLC Engine ([repo](https://github.com/org/maestro-hive))
- **maestro-shared**: Shared libraries ([repo](https://github.com/org/maestro-shared))
- **quality-fabric**: TAAS Platform ([repo](https://github.com/org/quality-fabric))
- **maestro-ml-platform**: ML Ops ([repo](https://github.com/org/maestro-ml-platform))
- **maestro-templates**: Code templates ([repo](https://github.com/org/maestro-templates))

### Integration Patterns

#### Use Maestro Frontend with Custom Backend
Your backend just needs to implement the API contract.

#### Use Custom Frontend with Maestro Backend
Point your frontend to Maestro Engine API.

#### Use Quality Fabric to Test Anything
Configure test target in config.

See [Integration Guide](./integration.md)
EOF
```

### Archive Old Monorepo

```bash
cd maestro-platform

# Add README explaining migration
cat > README.md << 'EOF'
# ⚠️ This repository has been archived

The Maestro platform has been split into independent repositories:

- [maestro-engine](https://github.com/org/maestro-engine)
- [maestro-frontend](https://github.com/org/maestro-frontend)
- [maestro-hive](https://github.com/org/maestro-hive)
- [maestro-shared](https://github.com/org/maestro-shared)
- [quality-fabric](https://github.com/org/quality-fabric)
- [maestro-ml-platform](https://github.com/org/maestro-ml-platform)
- [maestro-templates](https://github.com/org/maestro-templates)

This repository is kept for historical reference only.

**Migration Date**: 2025-10-XX
**Last Active Version**: See git tags
EOF

git add README.md
git commit -m "Archive repository - migrated to multi-repo structure"
git tag archived-$(date +%Y%m%d)
git push --tags
```

## Verification Checklist

After completing all steps, verify:

### Shared Packages
- [ ] All 7 packages published to registry
- [ ] Version 0.1.0 available
- [ ] Can install via `pip install maestro-core-api`
- [ ] Documentation published

### Quality Fabric
- [ ] Repository created and independent
- [ ] No code dependencies on Maestro
- [ ] Can test Maestro via API configuration
- [ ] Can test non-Maestro applications
- [ ] CI/CD pipeline working

### Maestro Frontend
- [ ] Repository created
- [ ] Can configure backend URL via env var
- [ ] Works with maestro-engine
- [ ] Documents API contract expectations
- [ ] CI/CD pipeline working

### Maestro Engine
- [ ] Repository created
- [ ] Uses published shared packages
- [ ] OpenAPI spec generated
- [ ] Works with maestro-frontend
- [ ] CI/CD pipeline working

### Integration
- [ ] Frontend + Backend work together
- [ ] Quality Fabric can test the stack
- [ ] Docker Compose works
- [ ] All tests passing

### Documentation
- [ ] Each repo has README
- [ ] API contracts documented
- [ ] Integration patterns documented
- [ ] Migration guide available
- [ ] Team trained

## Rollback Plan

If issues arise:

```bash
# Emergency rollback
git clone maestro-platform-backup
cd maestro-platform-backup
git checkout PRE_MIGRATION_TAG
# Continue with old structure
```

## Success Metrics

After migration:
- [ ] All components independently deployable
- [ ] Frontend can swap backends
- [ ] Backend can swap frontends
- [ ] Quality Fabric tests multiple solutions
- [ ] Clear product boundaries
- [ ] Independent release cycles
- [ ] Team productivity maintained or improved

## Common Issues

### Import Errors
```bash
# Clear Python cache
find . -type d -name __pycache__ -exec rm -r {} +
find . -type f -name "*.pyc" -delete
poetry install --no-cache
```

### Registry Authentication
```bash
# Regenerate tokens
poetry config http-basic.maestro YOUR_USER YOUR_TOKEN
```

### Docker Build Failures
```bash
# Clear Docker cache
docker system prune -a
docker-compose build --no-cache
```

## Next Steps

1. **Review** this plan with team
2. **Decide** on package registry
3. **Start** Week 1 tasks
4. **Track** progress weekly
5. **Adjust** plan as needed

---

**Remember**: This is a phased migration. You can pause, adjust, and iterate at any point. Don't rush - do it right.
