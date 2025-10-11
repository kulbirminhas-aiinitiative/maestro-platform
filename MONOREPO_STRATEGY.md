# Maestro Platform: Monorepo vs Multi-repo Strategy

**Date**: 2025-10-08
**Status**: Planning Phase
**Decision**: Hybrid Approach

## Executive Summary

After analyzing the maestro-platform components, we recommend a **hybrid approach** combining:
- A monorepo for tightly coupled core components
- Separate repositories for independent products
- A private package registry for shared library distribution

## Current State Analysis

### Component Inventory

| Component | Type | Dependencies | Current State |
|-----------|------|--------------|---------------|
| maestro-engine | Service | None (local) | ✅ Standalone |
| maestro-frontend | UI | None (local) | ✅ Standalone |
| maestro-hive | Service | Broken shared refs | ⚠️ Needs fix |
| maestro-templates | Data | None | ✅ Standalone |
| quality-fabric | Product | 6 shared packages | ⚠️ Tightly coupled |
| synth | Product | None (local) | ✅ Standalone |
| shared | Libraries | N/A | 📦 Core dependency |

### Dependency Graph

```
quality-fabric
├── shared/packages/core-api
├── shared/packages/core-auth
├── shared/packages/core-logging
├── shared/packages/core-config
├── shared/packages/monitoring
└── shared/packages/core-db

maestro-hive (broken)
├── shared/claude_team_sdk (path: "../../")
└── shared/packages/core-api (path: "../../../packages/core-api")
```

## Recommended Structure

### Option 1: Monorepo for Core Platform (RECOMMENDED)

**Repository**: `maestro-platform` (keep current structure)

```
maestro-platform/
├── apps/
│   ├── maestro-engine/          # Backend orchestration
│   ├── maestro-frontend/        # React dashboard
│   └── maestro-hive/            # SDLC engine
├── packages/
│   ├── core-api/
│   ├── core-auth/
│   ├── core-config/
│   ├── core-logging/
│   ├── core-db/
│   ├── core-messaging/
│   └── monitoring/
├── tools/                        # Build and deployment tools
├── nx.json / pnpm-workspace.yaml # Monorepo config
└── pyproject.toml               # Root Python config
```

**Pros**:
- Atomic commits across related changes
- Shared tooling and CI/CD
- Simplified dependency management
- Better discoverability
- Single source of truth

**Cons**:
- Larger repository size
- Requires monorepo tooling
- All teams need access to full repo

### Option 2: Separate Independent Products

**New Repositories**:

1. **quality-fabric** → `quality-fabric` (separate repo)
   - Testing as a Service platform
   - Completely standalone product
   - Different release cycle
   - Can be marketed/sold independently

2. **synth** → `maestro-ml-platform` (separate repo)
   - ML operations platform
   - Different domain expertise required
   - Independent evolution path
   - Potential for separate product line

3. **maestro-templates** → `maestro-templates` OR Git submodule
   - Pure data/content repository
   - No code dependencies
   - Could be versioned separately
   - Alternative: Git submodule in main repo

## Version Management Strategy

### For Monorepo (maestro-platform)

#### Approach A: Unified Versioning
```toml
# Root pyproject.toml
[tool.poetry]
name = "maestro-platform"
version = "2.0.0"  # Single version for entire platform
```

**When to use**: Tight coupling, coordinated releases, small team

#### Approach B: Independent Package Versioning (RECOMMENDED)
```toml
# apps/maestro-engine/pyproject.toml
[tool.poetry]
name = "maestro-engine"
version = "1.5.0"

# apps/maestro-frontend/pyproject.toml
[tool.poetry]
name = "maestro-frontend"
version = "1.3.0"

# packages/core-api/pyproject.toml
[tool.poetry]
name = "maestro-core-api"
version = "0.8.0"
```

**When to use**: Different release cycles per component, larger team

### For Separated Repos

Each repo maintains independent semantic versioning:
- `quality-fabric`: v1.0.0, v1.1.0, etc.
- `maestro-ml-platform`: v0.1.0, v0.2.0, etc.
- `maestro-templates`: v2024.10.08 (date-based) or v1.0.0

## Shared Library Distribution

### Private Package Registry Options

#### Option 1: AWS CodeArtifact (Recommended for AWS environments)
```bash
# Setup
aws codeartifact create-repository \
  --domain maestro \
  --repository maestro-shared

# Publish
poetry publish --repository maestro-shared

# Install
pip install maestro-core-api==0.8.0 \
  --index-url https://maestro-shared.codeartifact.aws/pypi/
```

**Pros**: Managed, integrated with AWS, supports multiple package types
**Cons**: AWS-specific, costs money

#### Option 2: Self-hosted PyPI (devpi)
```bash
# Setup
docker run -d --name devpi \
  -p 3141:3141 \
  -v /data/devpi:/data \
  muccg/devpi

# Publish
poetry publish --repository http://localhost:3141/maestro/prod/

# Install
pip install maestro-core-api==0.8.0 \
  --index-url http://localhost:3141/maestro/prod/+simple/
```

**Pros**: Free, full control, simple setup
**Cons**: Need to manage infrastructure

#### Option 3: GitHub Packages
```bash
# Publish via GitHub Actions
poetry publish --repository github

# Install
pip install maestro-core-api==0.8.0 \
  --index-url https://ghcr.io/maestro-platform/
```

**Pros**: Integrated with GitHub, private packages free for private repos
**Cons**: GitHub-specific

#### Option 4: Artifactory / Nexus (Enterprise)
**Pros**: Enterprise features, multi-format support, HA
**Cons**: Complex setup, licensing costs

## Monorepo Tooling Options

### For Python Monorepos

#### Option 1: Nx with Python Plugin (RECOMMENDED)
```bash
# Install
npm install -g nx

# Initialize
npx create-nx-workspace@latest maestro-platform \
  --preset=empty

# Add Python plugin
npm install -D @nxlv/python

# Configure
nx.json:
{
  "affected": {
    "defaultBase": "main"
  }
}
```

**Features**:
- Affected-based testing (only test changed code)
- Computation caching
- Task orchestration
- Visualization tools

#### Option 2: Pants (Python-focused)
```toml
# pants.toml
[GLOBAL]
backend_packages = [
  "pants.backend.python",
  "pants.backend.python.lint.black",
]

# BUILD file
python_sources(name="lib")
```

**Features**:
- Purpose-built for Python
- Fine-grained caching
- Remote execution
- Excellent for large monorepos

#### Option 3: Poetry with Workspace Plugin
```toml
# pyproject.toml (root)
[tool.poetry]
name = "maestro-platform"
packages = [
  {include = "apps/*"},
  {include = "packages/*"}
]

[tool.poetry.workspace]
members = ["apps/*", "packages/*"]
```

**Features**:
- Native Poetry integration
- Simpler learning curve
- Good for smaller monorepos

### Recommended: Nx for Hybrid Workspace

**Why Nx**:
- Supports both Python and TypeScript (for maestro-frontend)
- Best-in-class caching and affected detection
- Excellent developer experience
- Active community and ecosystem

## Implementation Roadmap

### Phase 1: Setup Infrastructure (Week 1)

#### Tasks:
1. ✅ Analyze current structure (COMPLETE)
2. 🔲 Choose package registry (Decision needed)
3. 🔲 Setup private PyPI registry
4. 🔲 Configure monorepo tooling (Nx)
5. 🔲 Create CI/CD pipeline templates

**Deliverables**:
- Running package registry
- Nx workspace configured
- CI/CD templates ready

### Phase 2: Restructure Monorepo (Week 2)

#### Tasks:
1. 🔲 Create apps/ and packages/ structure
2. 🔲 Move maestro-engine to apps/maestro-engine
3. 🔲 Move maestro-frontend to apps/maestro-frontend
4. 🔲 Move maestro-hive to apps/maestro-hive
5. 🔲 Consolidate shared/ into packages/
6. 🔲 Update all import paths
7. 🔲 Fix maestro-hive dependencies

**Deliverables**:
- Restructured monorepo
- All tests passing
- Updated documentation

### Phase 3: Publish Shared Packages (Week 2-3)

#### Tasks:
1. 🔲 Version shared packages (start at 0.1.0)
2. 🔲 Add package metadata and README
3. 🔲 Publish to private registry
4. 🔲 Test installation from registry

**Deliverables**:
- All 7 shared packages published
- Version 0.1.0 available in registry

### Phase 4: Extract quality-fabric (Week 3-4)

#### Tasks:
1. 🔲 Create new `quality-fabric` repository
2. 🔲 Copy quality-fabric code
3. 🔲 Update dependencies to use registry versions
4. 🔲 Setup independent CI/CD
5. 🔲 Test standalone operation
6. 🔲 Archive old location (or remove)

**Deliverables**:
- Independent quality-fabric repo
- v1.0.0 released
- CI/CD working

### Phase 5: Extract synth/ML Platform (Week 4-5)

#### Tasks:
1. 🔲 Create new `maestro-ml-platform` repository
2. 🔲 Copy synth code
3. 🔲 Update dependencies (if any)
4. 🔲 Setup independent CI/CD
5. 🔲 Test standalone operation
6. 🔲 Archive old location

**Deliverables**:
- Independent ML platform repo
- v0.1.0 released
- CI/CD working

### Phase 6: Handle maestro-templates (Week 5)

#### Option A: Separate Repository
1. 🔲 Create `maestro-templates` repo
2. 🔲 Move templates
3. 🔲 Version as v1.0.0
4. 🔲 Reference from main repo

#### Option B: Git Submodule (RECOMMENDED)
1. 🔲 Create `maestro-templates` repo
2. 🔲 Add as submodule to maestro-platform
3. 🔲 Update references

**Deliverables**:
- Templates properly versioned
- Integration maintained

### Phase 7: Documentation & Training (Week 6)

#### Tasks:
1. 🔲 Update all README files
2. 🔲 Create developer onboarding guide
3. 🔲 Document version management process
4. 🔲 Create release process documentation
5. 🔲 Team training sessions

**Deliverables**:
- Complete documentation
- Team trained on new structure

## Configuration Examples

### Nx Workspace Configuration

```json
// nx.json
{
  "npmScope": "maestro",
  "affected": {
    "defaultBase": "main"
  },
  "tasksRunnerOptions": {
    "default": {
      "runner": "nx/tasks-runners/default",
      "options": {
        "cacheableOperations": ["build", "test", "lint"]
      }
    }
  },
  "targetDefaults": {
    "build": {
      "dependsOn": ["^build"]
    },
    "test": {
      "dependsOn": ["build"]
    }
  }
}
```

### Poetry Workspace Configuration

```toml
# Root pyproject.toml
[tool.poetry]
name = "maestro-platform"
version = "2.0.0"
description = "Maestro Platform Monorepo"

[tool.poetry.dependencies]
python = "^3.11"

[tool.poetry.workspace]
members = [
    "apps/maestro-engine",
    "apps/maestro-frontend",
    "apps/maestro-hive",
    "packages/core-api",
    "packages/core-auth",
    "packages/core-config",
    "packages/core-logging",
    "packages/core-db",
    "packages/core-messaging",
    "packages/monitoring"
]
```

### Individual Package Configuration

```toml
# packages/core-api/pyproject.toml
[tool.poetry]
name = "maestro-core-api"
version = "0.1.0"
description = "Core API framework for Maestro platform"
authors = ["Maestro Team"]
repository = "https://github.com/maestro/maestro-platform"
packages = [{include = "maestro_core_api"}]

[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.115.0"
pydantic = "^2.9.0"
maestro-core-logging = "^0.1.0"  # Internal dependency

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

### CI/CD Pipeline (GitHub Actions)

```yaml
# .github/workflows/ci.yml
name: CI

on:
  pull_request:
  push:
    branches: [main]

jobs:
  affected:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0

      - name: Setup Nx
        run: npm install -g nx

      - name: Run affected tests
        run: nx affected --target=test --base=origin/main

      - name: Run affected builds
        run: nx affected --target=build --base=origin/main

      - name: Run affected lints
        run: nx affected --target=lint --base=origin/main

  publish-shared:
    if: github.ref == 'refs/heads/main'
    needs: affected
    runs-on: ubuntu-latest
    steps:
      - name: Publish shared packages
        run: |
          for pkg in packages/*; do
            cd $pkg
            poetry publish --repository maestro-shared
            cd ../..
          done
```

## Migration Checklist

### Pre-Migration
- [ ] Backup current repository
- [ ] Document current dependency graph
- [ ] Freeze current versions
- [ ] Communicate changes to team
- [ ] Choose package registry
- [ ] Setup registry infrastructure

### During Migration
- [ ] Create new repository structure
- [ ] Move code to new locations
- [ ] Update all import paths
- [ ] Fix broken dependencies
- [ ] Publish shared packages
- [ ] Update consumer references
- [ ] Test all applications
- [ ] Update CI/CD pipelines

### Post-Migration
- [ ] Archive old structure
- [ ] Update documentation
- [ ] Train team on new workflow
- [ ] Monitor for issues
- [ ] Gather feedback
- [ ] Iterate on tooling

## Decision Points

### 1. Package Registry Choice
**Recommendation**: AWS CodeArtifact if using AWS, otherwise devpi (self-hosted)

**Decision Needed**: ❓ Which cloud provider / infrastructure?

### 2. Monorepo Tool
**Recommendation**: Nx (supports Python + TypeScript)

**Decision Needed**: ❓ Confirm or explore alternatives?

### 3. Versioning Strategy
**Recommendation**: Independent package versioning

**Decision Needed**: ❓ Unified vs independent?

### 4. maestro-templates Approach
**Recommendation**: Git submodule

**Decision Needed**: ❓ Submodule vs separate repo?

### 5. Migration Timeline
**Recommendation**: 6-week phased approach

**Decision Needed**: ❓ Timeline constraints?

## Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Breaking changes during migration | High | Medium | Phased approach, feature flags |
| Dependency conflicts | Medium | High | Lock versions, comprehensive testing |
| Team resistance to new structure | Medium | Medium | Training, documentation, early involvement |
| CI/CD pipeline failures | High | Low | Test in staging, rollback plan |
| Registry downtime | Medium | Low | Backup registry, local caching |
| Lost productivity during transition | Medium | High | Clear documentation, pair programming |

## Success Metrics

### Short-term (1-3 months)
- [ ] All shared packages published to registry
- [ ] quality-fabric operating independently
- [ ] synth/ML platform operating independently
- [ ] CI/CD pipelines working
- [ ] All tests passing
- [ ] Team comfortable with new structure

### Long-term (3-6 months)
- [ ] Reduced dependency conflicts
- [ ] Faster CI/CD times (via affected detection)
- [ ] Easier onboarding for new developers
- [ ] Improved release velocity
- [ ] Clear ownership boundaries
- [ ] Independent product evolution

## Conclusion

The hybrid approach balances the benefits of:
- **Monorepo** for tightly coupled core platform components
- **Multi-repo** for independent products with different lifecycles
- **Private registry** for clean dependency management

This structure allows:
- The core Maestro platform to evolve cohesively
- Quality Fabric to be marketed/sold as standalone product
- ML platform to evolve independently
- Clean separation of concerns
- Flexible versioning strategies

## Next Steps

1. **Decision Making** (Week 0)
   - Review this document with stakeholders
   - Make decisions on open questions
   - Get team buy-in

2. **Setup Phase** (Week 1)
   - Choose and setup package registry
   - Install monorepo tooling
   - Create pilot migration

3. **Execution Phase** (Weeks 2-5)
   - Follow implementation roadmap
   - Monitor and adjust as needed

4. **Stabilization Phase** (Week 6+)
   - Documentation
   - Training
   - Continuous improvement

## Appendix

### Glossary
- **Monorepo**: Single repository containing multiple projects
- **Multi-repo**: Multiple repositories, one per project
- **Affected Detection**: Testing only code affected by changes
- **Private Registry**: Internal package repository
- **Semantic Versioning**: MAJOR.MINOR.PATCH versioning scheme

### References
- Nx: https://nx.dev
- Pants: https://pantsbuild.org
- Poetry: https://python-poetry.org
- AWS CodeArtifact: https://aws.amazon.com/codeartifact/
- devpi: https://devpi.net/

### Contact
For questions about this strategy, contact the platform architecture team.
