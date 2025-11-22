#!/usr/bin/env python3
"""
Validate service port allocations.

Checks:
1. No port conflicts
2. Ports within allocated ranges
3. All services defined in registry

Usage:
    python scripts/validate_port_allocation.py
"""

import sys
import yaml
from pathlib import Path
from collections import defaultdict
from typing import Dict, List


def load_port_registry() -> dict:
    """Load service port registry."""
    registry_path = Path("config/service_ports.yaml")

    if not registry_path.exists():
        print("⚠️  Port registry not found: config/service_ports.yaml")
        print("   Creating template registry...")
        create_template_registry()
        return load_port_registry()

    with open(registry_path) as f:
        return yaml.safe_load(f)


def create_template_registry():
    """Create template port registry."""
    template = {
        "metadata": {
            "project": "claude_team_sdk",
            "version": "1.0.0",
            "port_range_min": 3000,
            "port_range_max": 9999
        },
        "services": [
            {
                "name": "example-frontend",
                "port": 3000,
                "category": "examples",
                "public": True,
                "health_endpoint": "/health"
            },
            {
                "name": "example-api",
                "port": 4000,
                "category": "examples",
                "public": False,
                "health_endpoint": "/api/health"
            },
            {
                "name": "postgres",
                "port": 5432,
                "category": "infrastructure",
                "public": False,
                "health_endpoint": "tcp"
            },
            {
                "name": "redis",
                "port": 6379,
                "category": "infrastructure",
                "public": False,
                "health_endpoint": "tcp"
            }
        ],
        "port_ranges": {
            "examples": [3000, 3999],
            "services": [4000, 4999],
            "infrastructure": [5432, 6379]
        }
    }

    Path("config").mkdir(exist_ok=True)
    with open("config/service_ports.yaml", "w") as f:
        yaml.dump(template, f, default_flow_style=False, sort_keys=False)

    print(f"✅ Created template registry: config/service_ports.yaml\n")


def find_port_conflicts(registry: dict) -> Dict[int, List[str]]:
    """Find duplicate port assignments."""
    port_usage = defaultdict(list)

    for service in registry["services"]:
        port_usage[service["port"]].append(service["name"])

    return {
        port: services
        for port, services in port_usage.items()
        if len(services) > 1
    }


def validate_port_ranges(registry: dict) -> List[dict]:
    """Validate ports are within allocated ranges."""
    violations = []

    for service in registry["services"]:
        port = service["port"]
        category = service.get("category", "unknown")

        # Get expected range for category
        if category in registry.get("port_ranges", {}):
            min_port, max_port = registry["port_ranges"][category]
            if not (min_port <= port <= max_port):
                violations.append({
                    "service": service["name"],
                    "port": port,
                    "category": category,
                    "expected_range": f"{min_port}-{max_port}"
                })

    return violations


def main():
    """Run all port allocation validations."""
    print("🔍 Validating port allocations...\n")

    registry = load_port_registry()

    # Check for conflicts
    conflicts = find_port_conflicts(registry)
    if conflicts:
        print("❌ PORT CONFLICTS DETECTED:")
        for port, services in conflicts.items():
            print(f"   Port {port}: {', '.join(services)}")
        print()

    # Check range violations
    violations = validate_port_ranges(registry)
    if violations:
        print("⚠️  PORT RANGE VIOLATIONS:")
        for v in violations:
            print(f"   {v['service']}: port {v['port']} not in {v['expected_range']}")
        print()

    # Summary
    if conflicts or violations:
        print(f"❌ Validation failed: {len(conflicts)} conflict(s), {len(violations)} violation(s)")
        sys.exit(1)
    else:
        print("✅ All port allocations valid!")
        print(f"   Total services: {len(registry['services'])}")
        min_port = registry['metadata']['port_range_min']
        max_port = registry['metadata']['port_range_max']
        print(f"   Port range: {min_port}-{max_port}")


if __name__ == "__main__":
    main()
