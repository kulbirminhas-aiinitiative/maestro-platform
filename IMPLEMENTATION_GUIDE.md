# Maestro Platform: Step-by-Step Implementation Guide

**Practical guide for executing the monorepo migration**

## Prerequisites

Before starting, ensure you have:
- [ ] Read MONOREPO_STRATEGY.md
- [ ] Reviewed DECISION_MATRIX.md
- [ ] Made key decisions (package registry, tooling)
- [ ] Team buy-in and availability
- [ ] Backup of current repository

## Implementation Path

We'll follow a **6-week phased approach** with clear milestones.

---

## Week 1: Setup Infrastructure

### Day 1-2: Package Registry Setup

#### Option A: GitHub Packages (Easiest)

```bash
# 1. Create GitHub Personal Access Token with package permissions
# Go to: GitHub Settings → Developer Settings → Personal Access Tokens

# 2. Configure Poetry to use GitHub Packages
poetry config repositories.maestro https://github.com/YOUR_ORG/maestro-platform

# 3. Configure authentication
poetry config http-basic.maestro YOUR_USERNAME YOUR_TOKEN

# 4. Test publish (use a test package first)
cd shared/packages/core-logging
poetry build
poetry publish --repository maestro
```

#### Option B: Self-hosted devpi

```bash
# 1. Install devpi
pip install devpi-server devpi-web devpi-client

# 2. Initialize devpi server
devpi-init

# 3. Start server
devpi-server --start --host=0.0.0.0 --port=3141

# 4. Create user and index
devpi use http://localhost:3141
devpi user -c maestro password=secret
devpi login maestro --password=secret
devpi index -c maestro/prod bases=root/pypi

# 5. Configure Poetry
poetry config repositories.maestro http://localhost:3141/maestro/prod/

# 6. Test publish
cd shared/packages/core-logging
poetry build
poetry publish --repository maestro
```

#### Option C: AWS CodeArtifact

```bash
# 1. Create CodeArtifact repository
aws codeartifact create-repository \
  --domain maestro \
  --repository maestro-shared \
  --region us-east-1

# 2. Get authentication token
export CODEARTIFACT_TOKEN=$(aws codeartifact get-authorization-token \
  --domain maestro \
  --query authorizationToken \
  --output text)

# 3. Configure Poetry
REPO_URL=$(aws codeartifact get-repository-endpoint \
  --domain maestro \
  --repository maestro-shared \
  --format pypi \
  --query repositoryEndpoint \
  --output text)

poetry config repositories.maestro $REPO_URL
poetry config http-basic.maestro aws $CODEARTIFACT_TOKEN

# 4. Test publish
cd shared/packages/core-logging
poetry build
poetry publish --repository maestro
```

### Day 3-4: Monorepo Tooling Setup

#### Setup Nx (Recommended)

```bash
# 1. Initialize Nx workspace
cd /home/ec2-user/projects/maestro-platform

# Create package.json if doesn't exist
cat > package.json << 'EOF'
{
  "name": "maestro-platform",
  "version": "2.0.0",
  "private": true,
  "workspaces": [
    "apps/*",
    "packages/*"
  ]
}
EOF

# 2. Install Nx
npm install -D nx @nrwl/workspace

# 3. Install Python plugin
npm install -D @nxlv/python

# 4. Create nx.json configuration
cat > nx.json << 'EOF'
{
  "$schema": "./node_modules/nx/schemas/nx-schema.json",
  "npmScope": "maestro",
  "affected": {
    "defaultBase": "main"
  },
  "tasksRunnerOptions": {
    "default": {
      "runner": "nx/tasks-runners/default",
      "options": {
        "cacheableOperations": [
          "build",
          "test",
          "lint"
        ]
      }
    }
  },
  "targetDefaults": {
    "build": {
      "dependsOn": ["^build"],
      "outputs": ["{projectRoot}/dist"]
    },
    "test": {
      "dependsOn": ["build"]
    }
  },
  "workspaceLayout": {
    "appsDir": "apps",
    "libsDir": "packages"
  }
}
EOF

# 5. Test Nx
npx nx graph  # Visualize project graph
```

### Day 5: CI/CD Pipeline Template

#### GitHub Actions Workflow

```bash
# Create .github/workflows/ci.yml
mkdir -p .github/workflows

cat > .github/workflows/ci.yml << 'EOF'
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  setup:
    runs-on: ubuntu-latest
    outputs:
      affected-apps: ${{ steps.affected.outputs.apps }}
      affected-libs: ${{ steps.affected.outputs.libs }}
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0

      - name: Setup Node
        uses: actions/setup-node@v3
        with:
          node-version: '18'

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install Nx
        run: npm install -g nx

      - name: Find affected projects
        id: affected
        run: |
          AFFECTED=$(nx affected:apps --base=origin/main --plain)
          echo "apps=$AFFECTED" >> $GITHUB_OUTPUT

          AFFECTED_LIBS=$(nx affected:libs --base=origin/main --plain)
          echo "libs=$AFFECTED_LIBS" >> $GITHUB_OUTPUT

  test:
    needs: setup
    runs-on: ubuntu-latest
    if: ${{ needs.setup.outputs.affected-apps != '' || needs.setup.outputs.affected-libs != '' }}
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0

      - name: Setup environment
        uses: ./.github/actions/setup-env

      - name: Run affected tests
        run: nx affected --target=test --base=origin/main

      - name: Upload coverage
        uses: codecov/codecov-action@v3

  build:
    needs: test
    runs-on: ubuntu-latest
    if: ${{ needs.setup.outputs.affected-apps != '' }}
    steps:
      - uses: actions/checkout@v3

      - name: Setup environment
        uses: ./.github/actions/setup-env

      - name: Build affected apps
        run: nx affected --target=build --base=origin/main

      - name: Upload artifacts
        uses: actions/upload-artifact@v3
        with:
          name: build-artifacts
          path: dist/

  publish-packages:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main' && needs.setup.outputs.affected-libs != ''
    steps:
      - uses: actions/checkout@v3

      - name: Setup environment
        uses: ./.github/actions/setup-env

      - name: Publish affected packages
        run: |
          for lib in ${{ needs.setup.outputs.affected-libs }}; do
            cd packages/$lib
            poetry version patch
            poetry build
            poetry publish --repository maestro --username ${{ secrets.REPO_USERNAME }} --password ${{ secrets.REPO_PASSWORD }}
            cd ../..
          done
EOF
```

---

## Week 2: Restructure Monorepo

### Day 1: Create New Structure

```bash
# 1. Create apps and packages directories
cd /home/ec2-user/projects/maestro-platform
mkdir -p apps packages

# 2. Move components to apps/
# Note: Do this one at a time to avoid issues

# Move maestro-engine
git mv maestro-engine apps/

# Move maestro-frontend
git mv maestro-frontend apps/

# Move maestro-hive
git mv maestro-hive apps/

# 3. Move shared packages to packages/
cd shared/packages

# Move each package
for pkg in core-api core-auth core-config core-logging core-db core-messaging monitoring; do
    git mv $pkg ../../packages/
done

# 4. Update package names in pyproject.toml files
# Each package should have a unique name like maestro-core-api
```

### Day 2-3: Update Import Paths

#### Script to find all imports

```bash
# Create a script to find imports
cat > scripts/find_imports.sh << 'EOF'
#!/bin/bash
# Find all Python imports from shared packages

echo "Finding imports in apps..."
for app in apps/*; do
    echo "Checking $app:"
    grep -r "from shared" $app/src || true
    grep -r "import shared" $app/src || true
done
EOF

chmod +x scripts/find_imports.sh
./scripts/find_imports.sh
```

#### Update imports in each app

```python
# Before (in maestro-engine):
from shared.packages.core_api import BaseAPI
from shared.packages.core_logging import setup_logging

# After:
from maestro_core_api import BaseAPI
from maestro_core_logging import setup_logging
```

### Day 4-5: Fix Dependencies

#### Update maestro-engine dependencies

```toml
# apps/maestro-engine/pyproject.toml

[tool.poetry.dependencies]
python = "^3.11"
# ... other dependencies ...

# Add shared packages as dependencies
maestro-core-api = {path = "../../packages/core-api", develop = true}
maestro-core-logging = {path = "../../packages/core-logging", develop = true}
maestro-core-config = {path = "../../packages/core-config", develop = true}
# ... other shared packages as needed
```

#### Update maestro-frontend dependencies

```toml
# apps/maestro-frontend/pyproject.toml

[tool.poetry.dependencies]
python = "^3.11"
# ... other dependencies ...

# Add only what's needed (frontend might need less)
maestro-core-api = {path = "../../packages/core-api", develop = true}
```

#### Fix maestro-hive dependencies

```toml
# apps/maestro-hive/pyproject.toml

[tool.poetry.dependencies]
python = "^3.11"
# ... other dependencies ...

# Replace broken paths:
# OLD: claude_team_sdk = {path = "../../", develop = true}
# OLD: maestro_core_api = {path = "../../../packages/core-api", develop = true}

# NEW:
claude-team-sdk = {path = "../../shared/claude_team_sdk", develop = true}
maestro-core-api = {path = "../../packages/core-api", develop = true}
```

### Day 6: Test and Validate

```bash
# 1. Test each app builds
cd apps/maestro-engine
poetry install
poetry run pytest

cd ../maestro-frontend
npm install
npm run build

cd ../maestro-hive
poetry install
poetry run pytest

# 2. Test cross-package imports work
python << 'EOF'
import sys
sys.path.insert(0, '/home/ec2-user/projects/maestro-platform/apps/maestro-engine')
from maestro_core_api import BaseAPI
print("✅ Import successful")
EOF

# 3. Run Nx graph to verify dependencies
npx nx graph
```

---

## Week 3: Publish Shared Packages

### Day 1: Prepare Packages for Publishing

For each package in `packages/`:

```bash
cd packages/core-api

# 1. Update pyproject.toml with publishing info
cat >> pyproject.toml << 'EOF'

[tool.poetry]
name = "maestro-core-api"
version = "0.1.0"
description = "Core API framework for Maestro platform"
authors = ["Maestro Team <team@maestro.ai>"]
readme = "README.md"
repository = "https://github.com/maestro/maestro-platform"
keywords = ["maestro", "api", "framework"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "Programming Language :: Python :: 3.11",
]
packages = [{include = "maestro_core_api"}]
EOF

# 2. Create README.md
cat > README.md << 'EOF'
# Maestro Core API

Core API framework for the Maestro platform.

## Installation

```bash
pip install maestro-core-api
```

## Usage

```python
from maestro_core_api import BaseAPI

api = BaseAPI()
```

## Development

This is part of the Maestro platform monorepo.
See [maestro-platform](https://github.com/maestro/maestro-platform) for details.
EOF

# 3. Repeat for all packages
```

### Day 2-3: Publish First Versions

```bash
# Create script to publish all packages
cat > scripts/publish_all_packages.sh << 'EOF'
#!/bin/bash

set -e

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
    cd packages/$pkg

    # Version 0.1.0
    poetry version 0.1.0

    # Build
    poetry build

    # Publish to registry
    poetry publish --repository maestro

    cd ../..

    echo "✅ Published $pkg version 0.1.0"
done

echo "🎉 All packages published!"
EOF

chmod +x scripts/publish_all_packages.sh
./scripts/publish_all_packages.sh
```

### Day 4-5: Update Apps to Use Published Packages

```bash
# For development, apps still use path dependencies
# But we can test installing from registry:

# Create virtual environment
python -m venv test_env
source test_env/bin/activate

# Test installing from registry
pip install maestro-core-api==0.1.0 --index-url YOUR_REGISTRY_URL

# Verify
python -c "from maestro_core_api import BaseAPI; print('✅ Works')"

deactivate
rm -rf test_env
```

---

## Week 4: Extract quality-fabric

### Day 1-2: Create New Repository

```bash
# 1. Create new repository on GitHub/GitLab
# Name: quality-fabric

# 2. Clone new repo
cd /home/ec2-user/projects
git clone git@github.com:yourorg/quality-fabric.git quality-fabric-new

# 3. Copy quality-fabric code
cd /home/ec2-user/projects/maestro-platform
cp -r quality-fabric/* /home/ec2-user/projects/quality-fabric-new/

# 4. Initialize new repo
cd /home/ec2-user/projects/quality-fabric-new
git add .
git commit -m "Initial commit: Extract quality-fabric from maestro-platform"
git push origin main
```

### Day 3-4: Update Dependencies to Use Registry

```toml
# /home/ec2-user/projects/quality-fabric-new/pyproject.toml

[tool.poetry.dependencies]
python = "^3.11"

# Replace path dependencies with registry versions
# OLD:
# maestro-core-api = {path = "../shared/packages/core-api"}
# maestro-core-auth = {path = "../shared/packages/core-auth"}

# NEW:
maestro-core-api = "^0.1.0"
maestro-core-auth = "^0.1.0"
maestro-core-logging = "^0.1.0"
maestro-core-config = "^0.1.0"
maestro-core-db = "^0.1.0"
maestro-monitoring = "^0.1.0"

[[tool.poetry.source]]
name = "maestro"
url = "YOUR_REGISTRY_URL"
priority = "supplemental"
```

### Day 5: Test Independent Operation

```bash
cd /home/ec2-user/projects/quality-fabric-new

# 1. Install dependencies (will fetch from registry)
poetry install

# 2. Run tests
poetry run pytest

# 3. Build
poetry build

# 4. Run service
poetry run python main.py

# 5. Verify all features work
curl http://localhost:8000/api/health
```

---

## Week 5: Extract synth/ML Platform

### Day 1-2: Create maestro-ml-platform Repository

```bash
# 1. Create new repository
cd /home/ec2-user/projects
git clone git@github.com:yourorg/maestro-ml-platform.git

# 2. Copy synth code
cd /home/ec2-user/projects/maestro-platform
cp -r synth/* /home/ec2-user/projects/maestro-ml-platform/

# 3. Rename internal references
cd /home/ec2-user/projects/maestro-ml-platform
find . -type f -name "*.py" -exec sed -i 's/synth/maestro_ml/g' {} +

# 4. Update pyproject.toml
# Change name from "maestro-ml" to "maestro-ml-platform"
```

### Day 3-4: Setup and Test

```bash
cd /home/ec2-user/projects/maestro-ml-platform

# 1. Install dependencies
poetry install

# 2. Run tests
poetry run pytest

# 3. Verify startup
poetry run python maestro_ml/api/main.py
```

### Day 5: Handle maestro-templates

#### Option A: Git Submodule (Recommended)

```bash
# 1. Create maestro-templates repository
cd /home/ec2-user/projects
git clone git@github.com:yourorg/maestro-templates.git maestro-templates-new

# 2. Copy template data
cd /home/ec2-user/projects/maestro-platform
cp -r maestro-templates/* /home/ec2-user/projects/maestro-templates-new/

# 3. Version and push
cd /home/ec2-user/projects/maestro-templates-new
git add .
git commit -m "Initial templates v1.0.0"
git tag v1.0.0
git push origin main --tags

# 4. Add as submodule to maestro-platform
cd /home/ec2-user/projects/maestro-platform
git submodule add git@github.com:yourorg/maestro-templates.git templates
git submodule update --init --recursive

# 5. Update references in code
sed -i 's|maestro-templates/|templates/|g' apps/maestro-engine/src/**/*.py
```

---

## Week 6: Documentation & Finalization

### Day 1-2: Update All Documentation

```bash
# 1. Update main README
cat > /home/ec2-user/projects/maestro-platform/README.md << 'EOF'
# Maestro Platform

Enterprise AI-powered SDLC orchestration platform.

## Repository Structure

This is a monorepo containing:

### Applications (`apps/`)
- **maestro-engine**: Backend orchestration engine
- **maestro-frontend**: React/TypeScript dashboard
- **maestro-hive**: Autonomous SDLC engine

### Shared Libraries (`packages/`)
- **core-api**: Core API framework
- **core-auth**: Authentication & authorization
- **core-config**: Configuration management
- **core-logging**: Structured logging
- **core-db**: Database abstraction
- **core-messaging**: Event messaging
- **monitoring**: Observability & metrics

### Related Projects
- [quality-fabric](https://github.com/yourorg/quality-fabric): Testing as a Service platform
- [maestro-ml-platform](https://github.com/yourorg/maestro-ml-platform): ML operations platform
- [maestro-templates](https://github.com/yourorg/maestro-templates): Code templates (submodule)

## Quick Start

See [QUICK_START.md](./QUICK_START.md)

## Development

See [CONTRIBUTING.md](./CONTRIBUTING.md)
EOF

# 2. Create developer guide
cat > /home/ec2-user/projects/maestro-platform/CONTRIBUTING.md << 'EOF'
# Contributing to Maestro Platform

## Development Setup

1. Clone repository:
```bash
git clone --recursive git@github.com:yourorg/maestro-platform.git
cd maestro-platform
```

2. Install dependencies:
```bash
# Install Nx globally
npm install -g nx

# Install Python dependencies for all apps
cd apps/maestro-engine && poetry install && cd ../..
cd apps/maestro-hive && poetry install && cd ../..
```

3. Run tests:
```bash
# Test everything
nx run-many --target=test --all

# Test only affected projects
nx affected --target=test
```

## Working with Shared Packages

Shared packages are in `packages/` and published to our private registry.

### Using in Development

Apps use path dependencies for fast iteration:
```toml
maestro-core-api = {path = "../../packages/core-api", develop = true}
```

### Publishing New Version

```bash
cd packages/core-api
poetry version patch  # or minor, or major
poetry build
poetry publish --repository maestro
```

## Monorepo Commands

```bash
# See project graph
nx graph

# Run specific target for specific project
nx run maestro-engine:test

# Run target for all affected projects
nx affected --target=test

# Clear cache
nx reset
```
EOF
```

### Day 3-4: Create Release Process Documentation

```markdown
# Release Process

## Shared Packages

1. Make changes in `packages/`
2. Update version: `poetry version patch`
3. Update CHANGELOG.md
4. Run tests: `nx run package-name:test`
5. Build: `poetry build`
6. Publish: `poetry publish --repository maestro`
7. Tag: `git tag package-name-v0.1.1`
8. Push: `git push --tags`

## Applications

1. Update app version in pyproject.toml
2. Update dependencies if needed
3. Run tests: `nx run app-name:test`
4. Build: `nx run app-name:build`
5. Tag: `git tag app-name-v1.0.1`
6. Push: `git push --tags`
7. Deploy via CI/CD

## Quality Fabric (Separate Repo)

1. Update version
2. Run tests
3. Create release on GitHub
4. CI/CD handles deployment
```

### Day 5-6: Team Training & Handoff

#### Training Checklist

- [ ] Walk through new repository structure
- [ ] Demonstrate Nx commands
- [ ] Show how to work with shared packages
- [ ] Explain versioning strategy
- [ ] Practice release process
- [ ] Review CI/CD pipelines
- [ ] Q&A session

---

## Validation Checklist

After completing all weeks, verify:

### Repository Structure
- [ ] Monorepo has apps/ and packages/ structure
- [ ] All imports updated and working
- [ ] No broken path dependencies
- [ ] Nx graph shows correct dependencies

### Published Packages
- [ ] All 7 shared packages published to registry
- [ ] Version 0.1.0 available
- [ ] Can install from registry
- [ ] README and metadata correct

### Separated Repositories
- [ ] quality-fabric repository created and working
- [ ] maestro-ml-platform repository created and working
- [ ] maestro-templates repository created
- [ ] Submodule linked correctly (if applicable)

### CI/CD
- [ ] Affected-based testing working
- [ ] Build pipeline working
- [ ] Publish pipeline working for shared packages
- [ ] All apps can be built and deployed

### Documentation
- [ ] README.md updated
- [ ] CONTRIBUTING.md created
- [ ] Release process documented
- [ ] Architecture decision records created

### Team Readiness
- [ ] Team trained on new structure
- [ ] Developer workflow documented
- [ ] Everyone can run and test locally
- [ ] Questions answered

## Troubleshooting

### Common Issues

#### Import Errors After Moving Packages
```bash
# Clear Python cache
find . -type d -name __pycache__ -exec rm -r {} +
find . -type f -name "*.pyc" -delete

# Reinstall dependencies
poetry install --no-cache
```

#### Nx Not Finding Projects
```bash
# Verify project.json or package.json exists in each project
# Regenerate Nx cache
nx reset
```

#### Poetry Can't Find Registry
```bash
# Verify registry configuration
poetry config repositories.maestro

# Test authentication
poetry search --source maestro test
```

#### CI/CD Not Running Affected Tests
```bash
# Verify fetch-depth in GitHub Actions
# Should be: fetch-depth: 0

# Check base branch configuration in nx.json
```

## Rollback Plan

If migration encounters critical issues:

1. **Immediate Rollback**:
   ```bash
   git reset --hard PRE_MIGRATION_TAG
   ```

2. **Partial Rollback**:
   - Revert specific commits
   - Keep infrastructure (registry, Nx)
   - Retry migration in smaller steps

3. **Keep Progress, Fix Forward**:
   - Isolate broken component
   - Fix in feature branch
   - Merge when working

## Success Metrics

Track these metrics to measure migration success:

- **Build Time**: Should decrease with caching
- **Test Time**: Should decrease with affected detection
- **Deploy Frequency**: Should increase
- **Developer Satisfaction**: Survey team
- **Onboarding Time**: Time for new developer to contribute
- **Dependency Conflicts**: Should decrease

## Next Steps After Migration

1. **Optimize CI/CD**: Add caching, parallel execution
2. **Documentation**: Expand developer guides
3. **Tooling**: Add custom Nx generators for scaffolding
4. **Monitoring**: Set up workspace analytics
5. **Process**: Establish release cadence and communication

---

**Remember**: Migration is a process, not an event. Be patient, communicate often, and iterate based on feedback.
