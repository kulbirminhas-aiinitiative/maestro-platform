#!/usr/bin/env python3
"""
Maestro Platform - Automated CI/CD Deployment Service

This service automates deployment of all Maestro services to:
- Development environment (~/deployment)
- Demo server (18.134.157.225)
- Production environment

NO MANUAL FILE COPYING - Fully automated deployment pipeline.
"""

import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import requests


@dataclass
class DeploymentConfig:
    """Deployment configuration"""

    environment: str  # development, demo, production
    deployment_path: Path
    port_offset: int
    quality_gates_enabled: bool
    auto_deploy: bool


class MaestroDeploymentService:
    """Automated deployment service for Maestro Platform"""

    def __init__(self, project_root: Path, environment: str = "development"):
        self.project_root = project_root
        self.environment = environment
        self.registry_path = project_root / "maestro_services_registry.json"
        self.registry = self._load_registry()
        self.deployment_config = self._get_deployment_config()

    def _load_registry(self) -> dict:
        """Load service registry"""
        if not self.registry_path.exists():
            raise FileNotFoundError(f"Service registry not found: {self.registry_path}")

        with open(self.registry_path) as f:
            return json.load(f)

    def _get_deployment_config(self) -> DeploymentConfig:
        """Get deployment configuration for environment"""
        env_config = self.registry["environments"][self.environment]

        return DeploymentConfig(
            environment=self.environment,
            deployment_path=Path(env_config["location"]),
            port_offset=env_config.get("port_offset", 0),
            quality_gates_enabled=env_config.get("quality_gates", False),
            auto_deploy=env_config.get("auto_deploy", False),
        )

    def deploy_all_services(self, skip_tests: bool = False):
        """Deploy all active services"""
        print(f"🚀 Maestro Platform Deployment")
        print(f"Environment: {self.environment}")
        print(f"Target: {self.deployment_config.deployment_path}")
        print("=" * 60)

        # Get active services sorted by deploy_order
        services = [s for s in self.registry["services"] if s["status"] == "active"]
        services.sort(key=lambda s: s.get("deploy_order", 999))

        # Ensure deployment directory exists
        self._prepare_deployment_directory()

        # Build and deploy each service
        results = []
        for service in services:
            print(f"\n📦 Processing: {service['name']}")
            result = self._deploy_service(service, skip_tests=skip_tests)
            results.append(result)

        # Summary
        self._print_deployment_summary(results)

        # Health checks
        if all(r["success"] for r in results):
            print("\n🏥 Running health checks...")
            self._run_health_checks(services)

        return all(r["success"] for r in results)

    def _prepare_deployment_directory(self):
        """Prepare deployment directory"""
        deployment_path = self.deployment_config.deployment_path

        if not deployment_path.exists():
            print(f"📁 Creating deployment directory: {deployment_path}")
            deployment_path.mkdir(parents=True, exist_ok=True)

        # Create docker-compose orchestration
        self._create_deployment_compose()

    def _create_deployment_compose(self):
        """Create main docker-compose.yml for all services"""
        compose_content = {
            "version": "3.8",
            "services": {},
            "networks": {"maestro-network": {"driver": "bridge"}},
            "volumes": {
                "maestro_redis_data": {},
                "maestro_postgres_data": {},
            },
        }

        # Add infrastructure services
        compose_content["services"]["redis"] = {
            "image": "redis:7-alpine",
            "container_name": "maestro-redis",
            "ports": ["6379:6379"],
            "volumes": ["maestro_redis_data:/data"],
            "networks": ["maestro-network"],
            "healthcheck": {
                "test": ["CMD", "redis-cli", "ping"],
                "interval": "10s",
                "timeout": "5s",
                "retries": 5,
            },
        }

        compose_content["services"]["postgres"] = {
            "image": "postgres:15-alpine",
            "container_name": "maestro-postgres",
            "environment": {
                "POSTGRES_USER": "maestro",
                "POSTGRES_PASSWORD": "maestro_dev",
                "POSTGRES_DB": "maestro",
            },
            "ports": ["5432:5432"],
            "volumes": ["maestro_postgres_data:/var/lib/postgresql/data"],
            "networks": ["maestro-network"],
            "healthcheck": {
                "test": ["CMD-SHELL", "pg_isready -U maestro"],
                "interval": "10s",
                "timeout": "5s",
                "retries": 5,
            },
        }

        # Add each active service
        for service in self.registry["services"]:
            if service["status"] != "active":
                continue

            service_id = service["id"]
            source_path = self.project_root / service["source_path"]
            port = service["ports"][self.environment]

            compose_content["services"][service_id] = {
                "build": {
                    "context": str(source_path),
                    "dockerfile": service["dockerfile"],
                },
                "container_name": f"maestro-{service_id}",
                "ports": [f"{port}:{service['ports']['production']}"],
                "environment": {
                    "ENVIRONMENT": self.environment,
                    "SERVICE_PORT": str(service["ports"]["production"]),
                },
                "networks": ["maestro-network"],
                "depends_on": service.get("dependencies", []),
                "restart": "unless-stopped",
            }

        # Write docker-compose.yml
        compose_path = self.deployment_config.deployment_path / "docker-compose.yml"
        import yaml

        with open(compose_path, "w") as f:
            yaml.dump(compose_content, f, default_flow_style=False, sort_keys=False)

        print(f"✅ Created deployment compose: {compose_path}")

    def _deploy_service(self, service: dict, skip_tests: bool = False) -> dict:
        """Deploy a single service"""
        service_id = service["id"]
        service_name = service["name"]
        source_path = self.project_root / service["source_path"]

        result = {
            "service_id": service_id,
            "service_name": service_name,
            "success": False,
            "steps": {},
        }

        try:
            # Step 1: Build Docker image
            print(f"  🔨 Building Docker image...")
            build_success = self._build_service(service, source_path)
            result["steps"]["build"] = build_success

            if not build_success:
                print(f"  ❌ Build failed for {service_name}")
                return result

            # Step 2: Run tests (if not skipped and test command exists)
            if not skip_tests and service.get("test_command"):
                print(f"  🧪 Running tests...")
                test_success = self._test_service(service, source_path)
                result["steps"]["test"] = test_success

                if not test_success and self.deployment_config.quality_gates_enabled:
                    print(f"  ❌ Tests failed for {service_name}")
                    return result

            # Step 3: Deploy service
            print(f"  🚀 Deploying service...")
            deploy_success = self._start_service(service)
            result["steps"]["deploy"] = deploy_success

            if not deploy_success:
                print(f"  ❌ Deployment failed for {service_name}")
                return result

            result["success"] = True
            print(f"  ✅ {service_name} deployed successfully")

        except Exception as e:
            print(f"  ❌ Error deploying {service_name}: {e}")
            result["error"] = str(e)

        return result

    def _build_service(self, service: dict, source_path: Path) -> bool:
        """Build Docker image for service"""
        try:
            cmd = ["docker-compose", "build", "--no-cache"]

            if service.get("docker_compose") != "docker-compose.yml":
                cmd.extend(["-f", service["docker_compose"]])

            result = subprocess.run(
                cmd,
                cwd=source_path,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minutes
            )

            return result.returncode == 0

        except Exception as e:
            print(f"    Build error: {e}")
            return False

    def _test_service(self, service: dict, source_path: Path) -> bool:
        """Run tests for service"""
        test_cmd = service.get("test_command")
        if not test_cmd:
            return True  # No tests defined

        try:
            result = subprocess.run(
                test_cmd.split(),
                cwd=source_path,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutes
            )

            return result.returncode == 0

        except Exception as e:
            print(f"    Test error: {e}")
            return False

    def _start_service(self, service: dict) -> bool:
        """Start service using docker-compose"""
        try:
            cmd = [
                "docker-compose",
                "up",
                "-d",
                service["id"],
            ]

            result = subprocess.run(
                cmd,
                cwd=self.deployment_config.deployment_path,
                capture_output=True,
                text=True,
                timeout=120,
            )

            return result.returncode == 0

        except Exception as e:
            print(f"    Start error: {e}")
            return False

    def _run_health_checks(self, services: List[dict]):
        """Run health checks on all deployed services"""
        print("\n" + "=" * 60)
        print("Health Check Results:")
        print("=" * 60)

        all_healthy = True

        for service in services:
            service_name = service["name"]
            health_endpoint = service.get("health_check")
            port = service["ports"][self.environment]

            if not health_endpoint:
                print(f"  ⚠️  {service_name}: No health check defined")
                continue

            # Wait a bit for service to start
            time.sleep(2)

            # Check health
            url = f"http://localhost:{port}{health_endpoint}"
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    print(f"  ✅ {service_name}: HEALTHY (port {port})")
                else:
                    print(
                        f"  ❌ {service_name}: UNHEALTHY - Status {response.status_code}"
                    )
                    all_healthy = False
            except Exception as e:
                print(f"  ❌ {service_name}: UNREACHABLE - {e}")
                all_healthy = False

        return all_healthy

    def _print_deployment_summary(self, results: List[dict]):
        """Print deployment summary"""
        print("\n" + "=" * 60)
        print("Deployment Summary:")
        print("=" * 60)

        success_count = sum(1 for r in results if r["success"])
        total_count = len(results)

        for result in results:
            status = "✅ SUCCESS" if result["success"] else "❌ FAILED"
            print(f"  {status}: {result['service_name']}")

        print(f"\nTotal: {success_count}/{total_count} services deployed successfully")

        if success_count == total_count:
            print("\n🎉 All services deployed successfully!")
        else:
            print("\n⚠️  Some services failed to deploy")

    def stop_all_services(self):
        """Stop all deployed services"""
        print("🛑 Stopping all services...")

        cmd = ["docker-compose", "down"]

        result = subprocess.run(
            cmd,
            cwd=self.deployment_config.deployment_path,
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            print("✅ All services stopped")
        else:
            print("❌ Error stopping services")

        return result.returncode == 0


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Maestro Platform Automated Deployment Service"
    )
    parser.add_argument(
        "action",
        choices=["deploy", "stop", "health"],
        help="Action to perform",
    )
    parser.add_argument(
        "--environment",
        "-e",
        choices=["development", "demo", "production"],
        default="development",
        help="Target environment",
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip running tests",
    )

    args = parser.parse_args()

    # Get project root
    project_root = Path(__file__).parent.parent.parent
    print(f"Project root: {project_root}")

    # Create deployment service
    deployer = MaestroDeploymentService(project_root, args.environment)

    # Execute action
    if args.action == "deploy":
        success = deployer.deploy_all_services(skip_tests=args.skip_tests)
        sys.exit(0 if success else 1)

    elif args.action == "stop":
        success = deployer.stop_all_services()
        sys.exit(0 if success else 1)

    elif args.action == "health":
        services = [
            s for s in deployer.registry["services"] if s["status"] == "active"
        ]
        success = deployer._run_health_checks(services)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
