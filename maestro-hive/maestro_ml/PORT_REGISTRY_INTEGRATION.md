# Port Registry Integration Complete ✅

## Overview

The Maestro ML Platform now uses a centralized, server-wide port registry manager for dynamic port allocation. This prevents port conflicts across all projects on the server and enables proper CI/CD integration.

**Completion Date**: 2025-10-04

---

## What Changed

### Before (Hardcoded Ports)
```yaml
# infrastructure/kubernetes/deployment.yaml
containerPort: 8000  # Hardcoded, risk of conflicts

# infrastructure/minikube/mlflow.yaml
nodePort: 30500  # Hardcoded
```

### After (Registry-Managed Ports)
```yaml
# Ports allocated via shared registry
nodePort: 30500  # Allocated via port registry
nodePort: 30501  # Allocated via port registry
nodePort: 30502  # Allocated via port registry
```

---

## Implementation Details

### 1. Shared Port Registry Manager

**Location**: `/home/ec2-user/projects/shared/tools/port_registry_manager.py`

**Features**:
- Dynamic port allocation (3100-9999 range)
- Conflict detection with system ports
- Project-based port tracking
- Automatic registry persistence
- CLI and Python API

**Registry File**: `/home/ec2-user/projects/shared/services_registry.json`

### 2. Allocated Ports for ML Platform

| Service | NodePort | Purpose |
|---------|----------|---------|
| MLflow | 30500 | Experiment tracking UI |
| Feast | 30501 | Feature server |
| Airflow | 30502 | Workflow orchestration UI |
| Prometheus | 30503 | Metrics collection |
| Grafana | 30504 | Monitoring dashboards |
| MinIO Console | 30505 | Object storage UI |

### 3. Updated Files

**Infrastructure**:
- `infrastructure/minikube/feast.yaml` - NodePort updated to 30501
- `infrastructure/minikube/airflow.yaml` - NodePort updated to 30502
- `infrastructure/service-registry.yaml` - Service registry configuration

**Documentation**:
- `PORT_ALLOCATION.md` - Complete port allocation guide
- `PORT_REGISTRY_INTEGRATION.md` - This document

**Scripts**:
- `scripts/check-ports.sh` - Quick port status checker

**Shared Tools**:
- `/home/ec2-user/projects/shared/tools/port_registry_manager.py` - Registry manager
- `/home/ec2-user/projects/shared/tools/README.md` - Usage documentation

---

## Usage

### Check Port Allocation

```bash
# Quick check
./scripts/check-ports.sh

# Detailed status
python3 /home/ec2-user/projects/shared/tools/port_registry_manager.py status \
  --project-path "/home/ec2-user/projects/shared/claude_team_sdk/examples/sdlc_team/maestro_ml"
```

### Allocate New Ports

```bash
python3 /home/ec2-user/projects/shared/tools/port_registry_manager.py allocate \
  --service-name "my-service" \
  --project-path "$(pwd)" \
  --count 3
```

### Release Ports

```bash
python3 /home/ec2-user/projects/shared/tools/port_registry_manager.py release \
  --project-path "$(pwd)"
```

### List All Services

```bash
python3 /home/ec2-user/projects/shared/tools/port_registry_manager.py list
```

---

## Benefits

### ✅ Conflict Prevention
- No more port conflicts between projects
- Automatic detection of in-use ports
- Registry tracks all allocations

### ✅ CI/CD Integration
- Dynamic port allocation in deployment pipelines
- Automated cleanup on teardown
- Consistent across environments

### ✅ Multi-Project Support
- Single registry for entire server
- Project-based tracking
- Easy port discovery

### ✅ Developer Experience
- Simple CLI interface
- Python API for automation
- Clear documentation

---

## Migration Guide

### For New Projects

```bash
# 1. Allocate ports
python3 /home/ec2-user/projects/shared/tools/port_registry_manager.py allocate \
  --service-name "my-project" \
  --project-path "$(pwd)" \
  --count 5

# 2. Use allocated ports in manifests
# Edit your kubernetes/docker-compose files with the allocated ports

# 3. On teardown, release ports
python3 /home/ec2-user/projects/shared/tools/port_registry_manager.py release \
  --project-path "$(pwd)"
```

### For Existing Projects

```bash
# 1. Check current ports
python3 /home/ec2-user/projects/shared/tools/port_registry_manager.py status

# 2. Register existing services (if not conflicting)
python3 /home/ec2-user/projects/shared/tools/port_registry_manager.py allocate \
  --service-name "existing-service" \
  --project-path "/path/to/project" \
  --start-range 30500 \
  --end-range 30599 \
  --count 3

# 3. Update manifests with allocated ports
```

---

## Python API Example

```python
#!/usr/bin/env python3
import sys
sys.path.append('/home/ec2-user/projects/shared/tools')

from port_registry_manager import PortRegistryManager

# Initialize
manager = PortRegistryManager()

# Allocate ports
try:
    ports = manager.allocate_ports(
        service_name="ml-platform",
        project_path="/path/to/project",
        count=3,
        start_range=30000,
        end_range=31000
    )
    print(f"Allocated ports: {ports}")

    # Register services
    for i, port in enumerate(ports):
        manager.register_service(
            service_name=f"service-{i}",
            service_type="web",
            port=port,
            project_path="/path/to/project",
            health_endpoint="/health"
        )

except ValueError as e:
    print(f"Error: {e}")

# Check allocation
project_ports = manager.get_service_ports("/path/to/project")
print(f"Project ports: {project_ports}")

# Cleanup
# manager.release_ports("/path/to/project")
```

---

## CI/CD Integration Example

```yaml
# .github/workflows/deploy.yml
name: Deploy ML Platform

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: self-hosted
    steps:
      - uses: actions/checkout@v2

      - name: Allocate Ports
        id: ports
        run: |
          PROJECT_PATH=$(pwd)
          python3 /home/ec2-user/projects/shared/tools/port_registry_manager.py allocate \
            --service-name "ml-platform" \
            --project-path "$PROJECT_PATH" \
            --count 6 > ports.txt
          echo "::set-output name=allocated::$(cat ports.txt)"

      - name: Deploy to Minikube
        run: |
          ./scripts/setup-minikube-test.sh

      - name: Cleanup (on failure)
        if: failure()
        run: |
          PROJECT_PATH=$(pwd)
          python3 /home/ec2-user/projects/shared/tools/port_registry_manager.py release \
            --project-path "$PROJECT_PATH"
```

---

## Troubleshooting

### Port Already in Use

```bash
# Find what's using the port
sudo ss -tulpn | grep 30500

# Check registry
python3 /home/ec2-user/projects/shared/tools/port_registry_manager.py status

# Release if needed
python3 /home/ec2-user/projects/shared/tools/port_registry_manager.py release \
  --project-path "/path/to/project"
```

### Registry Corruption

```bash
# Backup current registry
cp /home/ec2-user/projects/shared/services_registry.json \
   /home/ec2-user/projects/shared/services_registry.json.backup

# Reset registry (WARNING: loses all allocations)
rm /home/ec2-user/projects/shared/services_registry.json

# Re-allocate
python3 /home/ec2-user/projects/shared/tools/port_registry_manager.py allocate \
  --service-name "ml-platform" \
  --project-path "$(pwd)" \
  --count 6
```

### Stale Allocations

```bash
# List all services
python3 /home/ec2-user/projects/shared/tools/port_registry_manager.py list

# Release stale projects
python3 /home/ec2-user/projects/shared/tools/port_registry_manager.py release \
  --project-path "/path/to/old/project"
```

---

## Future Enhancements

### Planned Features

1. **Automatic Port Range Assignment**
   - Assign port ranges per project type
   - ML projects: 30500-30599
   - Web projects: 30600-30699
   - Data projects: 30700-30799

2. **Health Check Integration**
   - Automatically verify services are using assigned ports
   - Alert on port mismatches
   - Periodic cleanup of unused allocations

3. **Kubernetes Integration**
   - Auto-generate K8s manifests with allocated ports
   - Update ConfigMaps with service endpoints
   - Dynamic service discovery

4. **Web UI**
   - Visual port allocation dashboard
   - Real-time port usage monitoring
   - Interactive port management

---

## Success Criteria

- [x] Shared port registry manager created
- [x] ML platform ports allocated (30500-30505)
- [x] Minikube manifests updated
- [x] Documentation complete
- [x] Helper scripts created
- [x] Testing verified
- [x] No port conflicts

**All criteria met ✅**

---

## Resources

- **Registry Manager**: `/home/ec2-user/projects/shared/tools/port_registry_manager.py`
- **Registry File**: `/home/ec2-user/projects/shared/services_registry.json`
- **Documentation**: `/home/ec2-user/projects/shared/tools/README.md`
- **ML Platform Ports**: `PORT_ALLOCATION.md`
- **Quick Check**: `./scripts/check-ports.sh`

---

**Last Updated**: 2025-10-04
**Version**: 2.0
**Status**: Production Ready ✅
