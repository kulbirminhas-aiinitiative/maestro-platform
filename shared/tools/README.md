# Shared Tools

Centralized tools available to all projects on this server.

## Port Registry Manager

**Location**: `/home/ec2-user/projects/shared/tools/port_registry_manager.py`

**Purpose**: Manages dynamic port allocation across all projects to avoid conflicts.

### Usage

```bash
# Check available ports
python3 /home/ec2-user/projects/shared/tools/port_registry_manager.py available --count 5

# Allocate ports for a service
python3 /home/ec2-user/projects/shared/tools/port_registry_manager.py allocate \
  --service-name "maestro-ml-platform" \
  --project-path "/home/ec2-user/projects/shared/claude_team_sdk/examples/sdlc_team/maestro_ml" \
  --count 3

# Check status of all allocations
python3 /home/ec2-user/projects/shared/tools/port_registry_manager.py status

# Check status for specific project
python3 /home/ec2-user/projects/shared/tools/port_registry_manager.py status \
  --project-path "/home/ec2-user/projects/shared/claude_team_sdk/examples/sdlc_team/maestro_ml"

# List all registered services
python3 /home/ec2-user/projects/shared/tools/port_registry_manager.py list

# Release ports for a project
python3 /home/ec2-user/projects/shared/tools/port_registry_manager.py release \
  --project-path "/home/ec2-user/projects/shared/claude_team_sdk/examples/sdlc_team/maestro_ml"
```

### Registry Location

**File**: `/home/ec2-user/projects/shared/services_registry.json`

This file tracks all port allocations across all projects.

### Port Ranges

- **Default range**: 3100-9999
- **System ports**: 0-1023 (avoided)
- **Common services**: 1024-3099 (avoided)
- **Available for allocation**: 3100-9999

### Python API

```python
from port_registry_manager import PortRegistryManager

# Initialize manager
manager = PortRegistryManager()

# Allocate ports
ports = manager.allocate_ports(
    service_name="my-service",
    project_path="/path/to/project",
    count=3
)
print(f"Allocated ports: {ports}")

# Register a service
service_id = manager.register_service(
    service_name="web-server",
    service_type="http",
    port=ports[0],
    project_path="/path/to/project",
    health_endpoint="/health"
)

# Get ports for a project
project_ports = manager.get_service_ports("/path/to/project")

# Release ports when done
manager.release_ports("/path/to/project")
```

### Integration with CI/CD

Add to your deployment scripts:

```bash
#!/bin/bash
# Allocate ports dynamically
PROJECT_PATH=$(pwd)
SERVICE_NAME=$(basename $PROJECT_PATH)

# Allocate 3 ports for this project
PORTS=$(python3 /home/ec2-user/projects/shared/tools/port_registry_manager.py allocate \
  --service-name "$SERVICE_NAME" \
  --project-path "$PROJECT_PATH" \
  --count 3)

echo "Allocated ports: $PORTS"

# Use these ports in your docker-compose or k8s manifests
# ...

# On teardown, release ports
trap "python3 /home/ec2-user/projects/shared/tools/port_registry_manager.py release --project-path '$PROJECT_PATH'" EXIT
```

## Adding New Tools

To add a new shared tool:

1. Place it in `/home/ec2-user/projects/shared/tools/`
2. Make it executable: `chmod +x tool_name.py`
3. Document it in this README
4. Update projects to reference the shared location

---

**Last Updated**: 2025-10-04
**Maintainer**: ML Platform Team
