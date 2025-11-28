# Environment-Agnostic Deployment Architecture

**Date**: October 26, 2025
**Status**: ✅ Production Ready
**Version**: 2.0

---

## 🎯 Problem Solved

**Before**: Hardcoded paths in docker-compose.yml broke environment portability
```yaml
# ❌ WRONG: Hardcoded paths
build:
  context: /home/ec2-user/projects/maestro-platform/quality-fabric
```

**After**: Registry-driven dynamic generation
```bash
# ✅ CORRECT: Same command, different environments
python3 deploy_v2.py --environment development  # Dev paths
python3 deploy_v2.py --environment demo         # Demo paths
python3 deploy_v2.py --environment production   # Prod paths
```

---

## 🏗️ Architecture

### Central Configuration: `maestro_services_registry.json`

Single source of truth for ALL environments:

```json
{
  "services": [
    {
      "id": "quality-fabric",
      "source_path": "quality-fabric",
      "dockerfile": "Dockerfile",
      "ports": {
        "development": 9000,
        "demo": 8000,
        "production": 8000
      }
    }
  ],
  "environments": {
    "development": {
      "project_root": "/home/ec2-user/projects/maestro-platform",
      "nexus_url": "http://localhost:28081",
      "port_offset": 1000
    },
    "demo": {
      "project_root": "/home/ubuntu/maestro-platform",
      "nexus_url": "http://demo-nexus:8081",
      "port_offset": 0
    },
    "production": {
      "project_root": "/opt/maestro/source",
      "nexus_url": "http://prod-nexus:8081",
      "port_offset": 0
    }
  }
}
```

### Dynamic Generation Flow

```
┌─────────────────────────────────────────┐
│ maestro_services_registry.json          │
│ (Single Source of Truth)                │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│ compose_generator.py                    │
│ --environment development               │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│ docker-compose.yml (GENERATED)          │
│ ✅ Correct paths for environment        │
│ ✅ Correct Nexus URL                    │
│ ✅ Correct port mappings                │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│ docker-compose build && up              │
└─────────────────────────────────────────┘
```

---

## 📋 Files

### 1. `maestro_services_registry.json`
**Location**: `/home/ec2-user/projects/maestro-platform/`
**Purpose**: Central configuration for ALL environments

### 2. `compose_generator.py`
**Location**: `/home/ec2-user/projects/cicd-infrastructure/scripts/`
**Purpose**: Generate environment-specific docker-compose.yml

### 3. `deploy_v2.py`
**Location**: `/home/ec2-user/projects/cicd-infrastructure/scripts/`
**Purpose**: Full deployment orchestrator (uses compose_generator)

---

## 🚀 Usage

### Standalone Generation

```bash
# Generate docker-compose.yml for any environment
python3 /home/ec2-user/projects/cicd-infrastructure/scripts/compose_generator.py \
  --environment development \
  --output /home/ec2-user/deployment/docker-compose.yml

# Development
python3 compose_generator.py --environment development --output docker-compose.dev.yml

# Demo
python3 compose_generator.py --environment demo --output docker-compose.demo.yml

# Production
python3 compose_generator.py --environment production --output docker-compose.prod.yml
```

### Full Deployment (Recommended)

```bash
# Deploy to development
python3 /home/ec2-user/projects/cicd-infrastructure/scripts/deploy_v2.py \
  --environment development

# Deploy to demo
python3 /home/ec2-user/projects/cicd-infrastructure/scripts/deploy_v2.py \
  --environment demo

# Deploy to production
python3 /home/ec2-user/projects/cicd-infrastructure/scripts/deploy_v2.py \
  --environment production
```

**The script automatically**:
1. Generates docker-compose.yml from registry
2. Builds images with Nexus access
3. Runs database migrations
4. Deploys services
5. Runs health checks

---

## 🔧 Adding New Environment

1. **Update Registry**:
```json
"environments": {
  "uat": {
    "project_root": "/home/uat/maestro-platform",
    "nexus_url": "http://uat-nexus:8081",
    "port_offset": 0,
    "auto_deploy": false,
    "quality_gates": true
  }
}
```

2. **Deploy**:
```bash
python3 deploy_v2.py --environment uat
```

**NO CODE CHANGES NEEDED!**

---

## 🔄 Environment Differences

|                  | Development                                    | Demo                            | Production                |
|------------------|------------------------------------------------|---------------------------------|---------------------------|
| **Project Root** | `/home/ec2-user/projects/maestro-platform`     | `/home/ubuntu/maestro-platform` | `/opt/maestro/source`     |
| **Nexus URL**    | `http://localhost:28081`                       | `http://demo-nexus:8081`        | `http://prod-nexus:8081`  |
| **Port Offset**  | +1000 (10000, 10003, etc.)                     | +0 (8000, 8003, etc.)           | +0                        |
| **Auto Deploy**  | ✅ Yes                                          | ❌ Manual                        | ❌ Manual + Gates         |

---

## 📊 Generated docker-compose.yml Example

**Development**:
```yaml
services:
  quality-fabric:
    build:
      context: /home/ec2-user/projects/maestro-platform/quality-fabric
      dockerfile: Dockerfile
      network: host
      args:
        NEXUS_URL: http://localhost:28081
    ports:
      - 10000:9000  # Port offset +1000
```

**Demo**:
```yaml
services:
  quality-fabric:
    build:
      context: /home/ubuntu/maestro-platform/quality-fabric
      dockerfile: Dockerfile
      network: host
      args:
        NEXUS_URL: http://demo-nexus:8081
    ports:
      - 8000:8000  # Port offset +0
```

**ALL GENERATED FROM SAME REGISTRY!**

---

## ✅ Benefits

1. **No Hardcoded Paths**: Everything from registry
2. **Environment Portability**: Same script, different environments
3. **Central Configuration**: One file to rule them all
4. **Version Control Friendly**: Generated files are temporary
5. **CI/CD Ready**: Automated deployments across environments
6. **Scalable**: Add new environments without code changes

---

## 🔒 Best Practices

### 1. Registry is Source of Truth
- Never manually edit docker-compose.yml
- Always update registry first
- docker-compose.yml is a generated artifact

### 2. Environment Separation
- Each environment has its own config in registry
- No environment-specific code
- No conditional logic in deployment scripts

### 3. Deployment Workflow
```bash
# 1. Update registry
vim maestro_services_registry.json

# 2. Commit to git
git add maestro_services_registry.json
git commit -m "Add UAT environment"

# 3. Deploy
python3 deploy_v2.py --environment uat
```

### 4. CI/CD Integration
```yaml
# GitHub Actions example
- name: Deploy to Demo
  run: |
    python3 /cicd-infrastructure/scripts/deploy_v2.py \
      --environment demo
```

---

## 🆘 Troubleshooting

### Issue: Paths don't match
**Solution**: Check `project_root` in registry for environment

### Issue: Nexus packages not found
**Solution**: Check `nexus_url` in registry for environment

### Issue: Port conflicts
**Solution**: Adjust `port_offset` in registry for environment

### Issue: Service-specific config needed
**Solution**: Add to service definition in registry:
```json
{
  "id": "my-service",
  "environment_overrides": {
    "production": {
      "replicas": 3,
      "resources": {"memory": "2G"}
    }
  }
}
```

---

## 📝 Summary

**Before**: ❌ Hardcoded paths, manual edits, environment-specific scripts
**After**: ✅ Registry-driven, dynamic generation, environment-agnostic deployment

**One Command to Deploy Them All**:
```bash
python3 deploy_v2.py --environment <env>
```

---

**Architecture**: Registry → Generator → docker-compose.yml → Deployment
**Maintainability**: Update registry once, deploy anywhere
**Scalability**: Add environments without code changes

🚀 **Production Ready!**
