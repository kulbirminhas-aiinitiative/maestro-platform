#!/usr/bin/env python3
"""
Port Registry Manager
Manages dynamic port allocation for deployments to avoid conflicts
Shared across all projects on this server
"""

import json
import socket
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import uuid
import os


class PortRegistryManager:
    """Manages port allocation and registry for services"""

    def __init__(self, registry_path: str = None):
        # Default to shared location
        if registry_path is None:
            registry_path = "/home/ec2-user/projects/shared/services_registry.json"

        self.registry_path = Path(registry_path)
        # Ensure directory exists
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        self.registry = self._load_registry()

    def _load_registry(self) -> Dict:
        """Load existing registry or create new one"""
        if self.registry_path.exists():
            try:
                with open(self.registry_path, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print(f"Warning: Corrupted registry file, creating new one")
                return self._create_empty_registry()
        return self._create_empty_registry()

    def _create_empty_registry(self) -> Dict:
        """Create empty registry structure"""
        return {
            "services": {},
            "port_allocations": {},
            "metadata": {
                "last_updated": datetime.now().isoformat(),
                "registry_version": "2.0"
            }
        }

    def _save_registry(self):
        """Save registry to disk"""
        # Ensure metadata exists
        if "metadata" not in self.registry:
            self.registry["metadata"] = {}
        self.registry["metadata"]["last_updated"] = datetime.now().isoformat()

        # Atomic write
        temp_path = self.registry_path.with_suffix('.tmp')
        with open(temp_path, 'w') as f:
            json.dump(self.registry, f, indent=2)
        temp_path.replace(self.registry_path)

    def _is_port_available(self, port: int) -> bool:
        """Check if port is available for binding"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(('0.0.0.0', port))
                return True
        except OSError:
            return False

    def _get_used_ports(self) -> List[int]:
        """Get list of currently used ports from system"""
        try:
            # Try ss first (more modern)
            result = subprocess.run(['ss', '-tuln'], capture_output=True, text=True)
            if result.returncode != 0:
                # Fallback to netstat
                result = subprocess.run(['netstat', '-tuln'], capture_output=True, text=True)

            used_ports = []
            for line in result.stdout.split('\n'):
                if ':' in line and ('LISTEN' in line or 'State' not in line):
                    try:
                        # Handle both netstat and ss formats
                        parts = line.split()
                        for part in parts:
                            if ':' in part:
                                port_str = part.split(':')[-1]
                                # Remove trailing characters
                                port_str = ''.join(c for c in port_str if c.isdigit())
                                if port_str:
                                    port = int(port_str)
                                    if 1 <= port <= 65535:
                                        used_ports.append(port)
                                        break
                    except (ValueError, IndexError):
                        continue
            return list(set(used_ports))  # Remove duplicates
        except Exception as e:
            print(f"Warning: Could not get used ports: {e}")
            return []

    def get_allocated_ports(self) -> List[int]:
        """Get all ports currently allocated in registry"""
        allocated_ports = []

        # From services
        for service in self.registry.get("services", {}).values():
            if "port" in service:
                allocated_ports.append(service["port"])

        # From direct port allocations
        for port_info in self.registry.get("port_allocations", {}).values():
            if "allocated_ports" in port_info:
                allocated_ports.extend(port_info["allocated_ports"])

        return allocated_ports

    def find_available_ports(self, count: int = 1, start_range: int = 3100, end_range: int = 9999) -> List[int]:
        """Find available ports in the specified range"""
        used_ports = set(self._get_used_ports())
        allocated_ports = set(self.get_allocated_ports())
        unavailable_ports = used_ports | allocated_ports

        available_ports = []
        for port in range(start_range, end_range + 1):
            if port not in unavailable_ports:
                if self._is_port_available(port):
                    available_ports.append(port)
                    if len(available_ports) >= count:
                        break

        return available_ports

    def allocate_ports(self, service_name: str, project_path: str, count: int = 1,
                      start_range: int = 3100, end_range: int = 9999) -> List[int]:
        """Allocate ports for a service and register them"""
        available_ports = self.find_available_ports(count, start_range, end_range)

        if len(available_ports) < count:
            raise ValueError(f"Could not find {count} available ports in range {start_range}-{end_range}. "
                           f"Only found {len(available_ports)} available ports.")

        allocated_ports = available_ports[:count]

        # Register the allocation
        service_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()

        if "port_allocations" not in self.registry:
            self.registry["port_allocations"] = {}

        self.registry["port_allocations"][service_id] = {
            "service_id": service_id,
            "service_name": service_name,
            "project_path": project_path,
            "allocated_ports": allocated_ports,
            "allocated_at": timestamp,
            "status": "allocated"
        }

        self._save_registry()
        return allocated_ports

    def register_service(self, service_name: str, service_type: str, port: int,
                        project_path: str, health_endpoint: str = "/health",
                        namespace: str = None) -> str:
        """Register a deployed service"""
        service_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()

        if "services" not in self.registry:
            self.registry["services"] = {}

        self.registry["services"][service_id] = {
            "service_id": service_id,
            "name": service_name,
            "type": service_type,
            "url": f"http://localhost:{port}",
            "port": port,
            "health_endpoint": f"http://localhost:{port}{health_endpoint}",
            "status": "registered",
            "project_path": project_path,
            "namespace": namespace,
            "created_at": timestamp,
            "last_health_check": "",
            "metadata": {}
        }

        self._save_registry()
        return service_id

    def get_service_ports(self, project_path: str = None) -> Dict[str, int]:
        """Get allocated ports for a specific project or all projects"""
        ports = {}

        # Check services
        for service in self.registry.get("services", {}).values():
            if project_path is None or service.get("project_path") == project_path:
                key = f"{service['name']} ({service.get('project_path', 'unknown')})"
                ports[key] = service["port"]

        # Check port allocations
        for allocation in self.registry.get("port_allocations", {}).values():
            if project_path is None or allocation.get("project_path") == project_path:
                for i, port in enumerate(allocation["allocated_ports"]):
                    key = f"{allocation['service_name']}_port_{i} ({allocation.get('project_path', 'unknown')})"
                    ports[key] = port

        return ports

    def release_ports(self, project_path: str):
        """Release all ports allocated to a project"""
        # Remove from services
        services_to_remove = []
        for service_id, service in self.registry.get("services", {}).items():
            if service.get("project_path") == project_path:
                services_to_remove.append(service_id)

        for service_id in services_to_remove:
            del self.registry["services"][service_id]

        # Remove from port allocations
        allocations_to_remove = []
        for alloc_id, allocation in self.registry.get("port_allocations", {}).items():
            if allocation.get("project_path") == project_path:
                allocations_to_remove.append(alloc_id)

        for alloc_id in allocations_to_remove:
            del self.registry["port_allocations"][alloc_id]

        self._save_registry()
        print(f"Released {len(services_to_remove)} services and {len(allocations_to_remove)} port allocations")

    def generate_deployment_config(self, service_name: str, project_path: str,
                                 services_config: List[Dict]) -> Dict:
        """Generate deployment configuration with auto-allocated ports"""
        allocated_ports = self.allocate_ports(
            service_name=service_name,
            project_path=project_path,
            count=len(services_config)
        )

        deployment_config = {
            "project_name": service_name,
            "project_path": project_path,
            "services": []
        }

        for i, service_config in enumerate(services_config):
            port = allocated_ports[i]
            service_info = {
                "name": service_config.get("name", f"{service_name}-{i}"),
                "type": service_config.get("type", "web"),
                "port": port,
                "internal_port": service_config.get("internal_port", 80),
                "health_endpoint": service_config.get("health_endpoint", "/health"),
                "docker_service": service_config.get("docker_service", service_config.get("name")),
                "namespace": service_config.get("namespace")
            }
            deployment_config["services"].append(service_info)

            # Register the service
            self.register_service(
                service_name=service_info["name"],
                service_type=service_info["type"],
                port=port,
                project_path=project_path,
                health_endpoint=service_info["health_endpoint"],
                namespace=service_info["namespace"]
            )

        return deployment_config

    def list_all_services(self) -> Dict:
        """List all registered services grouped by project"""
        projects = {}

        for service in self.registry.get("services", {}).values():
            project = service.get("project_path", "unknown")
            if project not in projects:
                projects[project] = []
            projects[project].append({
                "name": service["name"],
                "type": service["type"],
                "port": service["port"],
                "status": service["status"],
                "created_at": service.get("created_at", "unknown")
            })

        return projects


def main():
    """CLI interface for port registry management"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Port Registry Manager - Shared across all projects"
    )
    parser.add_argument(
        "command",
        choices=["allocate", "release", "status", "available", "list"],
        help="Command to execute"
    )
    parser.add_argument("--service-name", help="Service name")
    parser.add_argument("--project-path", help="Project path")
    parser.add_argument("--count", type=int, default=1, help="Number of ports to allocate")
    parser.add_argument("--start-range", type=int, default=3100, help="Start of port range")
    parser.add_argument("--end-range", type=int, default=9999, help="End of port range")
    parser.add_argument("--registry-path", help="Custom registry path")

    args = parser.parse_args()

    manager = PortRegistryManager(registry_path=args.registry_path)

    if args.command == "allocate":
        if not args.service_name or not args.project_path:
            print("Error: --service-name and --project-path required for allocate")
            return 1

        try:
            ports = manager.allocate_ports(
                args.service_name,
                args.project_path,
                args.count,
                args.start_range,
                args.end_range
            )
            print(f"✓ Allocated ports for '{args.service_name}': {ports}")
            return 0
        except ValueError as e:
            print(f"✗ Error: {e}")
            return 1

    elif args.command == "release":
        if not args.project_path:
            print("Error: --project-path required for release")
            return 1

        manager.release_ports(args.project_path)
        print(f"✓ Released all ports for project: {args.project_path}")
        return 0

    elif args.command == "status":
        allocated = manager.get_allocated_ports()
        print(f"\n=== Port Registry Status ===")
        print(f"Total allocated ports: {len(allocated)}")
        print(f"Port range: {min(allocated) if allocated else 'N/A'} - {max(allocated) if allocated else 'N/A'}")

        if args.project_path:
            print(f"\n=== Ports for {args.project_path} ===")
            project_ports = manager.get_service_ports(args.project_path)
            if project_ports:
                for service, port in sorted(project_ports.items(), key=lambda x: x[1]):
                    print(f"  {port}: {service}")
            else:
                print(f"  No ports allocated for this project")
        else:
            print(f"\n=== All Allocated Ports ===")
            all_ports = manager.get_service_ports()
            if all_ports:
                for service, port in sorted(all_ports.items(), key=lambda x: x[1]):
                    print(f"  {port}: {service}")
        return 0

    elif args.command == "available":
        available = manager.find_available_ports(
            args.count, args.start_range, args.end_range
        )
        if available:
            print(f"✓ Found {len(available)} available ports in range {args.start_range}-{args.end_range}")
            print(f"First {min(10, len(available))} available: {available[:10]}")
        else:
            print(f"✗ No available ports found in range {args.start_range}-{args.end_range}")
        return 0

    elif args.command == "list":
        projects = manager.list_all_services()
        print("\n=== All Registered Services ===")
        for project, services in sorted(projects.items()):
            print(f"\n{project}:")
            for service in sorted(services, key=lambda x: x['port']):
                print(f"  - {service['name']:30} port={service['port']:5} type={service['type']:10} status={service['status']}")
        return 0


if __name__ == "__main__":
    exit(main() or 0)
