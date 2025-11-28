#!/usr/bin/env python3
"""
Docker Registry Manager for Maestro Services

Handles:
- Building and tagging Docker images
- Pushing to registry (ECR/Docker Hub)
- Image versioning with git commit hashes
- Rollback to previous image versions
"""

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class ImageTag:
    """Docker image tag information"""

    registry: str
    repository: str
    tag: str
    full_name: str


class DockerRegistryManager:
    """Manages Docker images and registry operations"""

    def __init__(
        self,
        project_root: Path,
        environment: str,
        registry: Optional[str] = None,
    ):
        self.project_root = project_root
        self.environment = environment
        self.registry = registry or os.getenv("DOCKER_REGISTRY", "localhost:5000")
        self.registry_path = project_root / "maestro_services_registry.json"
        self.deployment_history_path = (
            project_root / ".deployment_history" / f"{environment}.json"
        )
        self.registry_data = self._load_registry()

        # Ensure deployment history directory exists
        self.deployment_history_path.parent.mkdir(parents=True, exist_ok=True)

    def _load_registry(self) -> dict:
        """Load service registry"""
        with open(self.registry_path) as f:
            return json.load(f)

    def get_git_commit_hash(self) -> str:
        """Get current git commit hash"""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.stdout.strip() if result.returncode == 0 else "unknown"
        except Exception:
            return "unknown"

    def get_image_tag(self, service: dict, use_commit_hash: bool = True) -> ImageTag:
        """
        Generate image tag for a service

        Args:
            service: Service configuration
            use_commit_hash: If True, use git commit hash in tag

        Returns:
            ImageTag object
        """
        repository = f"maestro-{service['id']}"

        if use_commit_hash:
            commit_hash = self.get_git_commit_hash()
            tag = f"{self.environment}-{commit_hash}"
        else:
            tag = f"{self.environment}-latest"

        full_name = f"{self.registry}/{repository}:{tag}"

        return ImageTag(
            registry=self.registry, repository=repository, tag=tag, full_name=full_name
        )

    def build_image(self, service: dict, no_cache: bool = False) -> bool:
        """
        Build Docker image for a service

        Args:
            service: Service configuration
            no_cache: If True, build without cache

        Returns:
            True if build successful
        """
        service_name = service["name"]
        service_path = self.project_root / service["source_path"]
        image_tag = self.get_image_tag(service)

        print(f"🔨 Building {service_name}")
        print(f"   Image: {image_tag.full_name}")

        try:
            cmd = [
                "docker",
                "build",
                "-t",
                image_tag.full_name,
                "-f",
                service.get("dockerfile", "Dockerfile"),
            ]

            if no_cache:
                cmd.append("--no-cache")

            cmd.append(".")

            result = subprocess.run(
                cmd,
                cwd=service_path,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minutes
            )

            if result.returncode == 0:
                print(f"   ✅ Build successful")
                return True
            else:
                print(f"   ❌ Build failed")
                print(f"      {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            print(f"   ❌ Build timed out (> 10 minutes)")
            return False
        except Exception as e:
            print(f"   ❌ Build error: {e}")
            return False

    def tag_image(self, service: dict, additional_tags: List[str] = None) -> bool:
        """
        Tag image with additional tags

        Args:
            service: Service configuration
            additional_tags: List of additional tags (e.g., ['latest', 'stable'])

        Returns:
            True if tagging successful
        """
        base_tag = self.get_image_tag(service)

        if not additional_tags:
            additional_tags = [f"{self.environment}-latest"]

        print(f"🏷️  Tagging {service['name']}")

        try:
            for tag in additional_tags:
                new_tag = f"{self.registry}/maestro-{service['id']}:{tag}"
                result = subprocess.run(
                    ["docker", "tag", base_tag.full_name, new_tag],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                if result.returncode == 0:
                    print(f"   ✅ Tagged as {tag}")
                else:
                    print(f"   ❌ Failed to tag as {tag}")
                    return False

            return True

        except Exception as e:
            print(f"   ❌ Tagging error: {e}")
            return False

    def push_image(self, service: dict) -> bool:
        """
        Push Docker image to registry

        Args:
            service: Service configuration

        Returns:
            True if push successful
        """
        service_name = service["name"]
        image_tag = self.get_image_tag(service)

        print(f"📤 Pushing {service_name} to registry")
        print(f"   Image: {image_tag.full_name}")

        try:
            # Push main tag
            result = subprocess.run(
                ["docker", "push", image_tag.full_name],
                capture_output=True,
                text=True,
                timeout=600,  # 10 minutes
            )

            if result.returncode != 0:
                print(f"   ❌ Push failed: {result.stderr}")
                return False

            # Push latest tag
            latest_tag = f"{self.registry}/maestro-{service['id']}:{self.environment}-latest"
            subprocess.run(
                ["docker", "push", latest_tag],
                capture_output=True,
                text=True,
                timeout=600,
            )

            print(f"   ✅ Push successful")
            return True

        except subprocess.TimeoutExpired:
            print(f"   ❌ Push timed out (> 10 minutes)")
            return False
        except Exception as e:
            print(f"   ❌ Push error: {e}")
            return False

    def pull_image(self, service: dict, tag: Optional[str] = None) -> bool:
        """
        Pull Docker image from registry

        Args:
            service: Service configuration
            tag: Specific tag to pull (defaults to current environment tag)

        Returns:
            True if pull successful
        """
        service_name = service["name"]

        if tag:
            full_image = f"{self.registry}/maestro-{service['id']}:{tag}"
        else:
            image_tag = self.get_image_tag(service)
            full_image = image_tag.full_name

        print(f"📥 Pulling {service_name} from registry")
        print(f"   Image: {full_image}")

        try:
            result = subprocess.run(
                ["docker", "pull", full_image],
                capture_output=True,
                text=True,
                timeout=600,
            )

            if result.returncode == 0:
                print(f"   ✅ Pull successful")
                return True
            else:
                print(f"   ❌ Pull failed: {result.stderr}")
                return False

        except Exception as e:
            print(f"   ❌ Pull error: {e}")
            return False

    def save_deployment_history(self, services: List[dict]) -> None:
        """Save deployment history for rollback capability"""
        deployment_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "environment": self.environment,
            "commit_hash": self.get_git_commit_hash(),
            "services": {},
        }

        for service in services:
            image_tag = self.get_image_tag(service)
            deployment_record["services"][service["id"]] = {
                "name": service["name"],
                "image": image_tag.full_name,
                "tag": image_tag.tag,
            }

        # Load existing history
        history = []
        if self.deployment_history_path.exists():
            with open(self.deployment_history_path) as f:
                history = json.load(f)

        # Add new deployment
        history.append(deployment_record)

        # Keep only last 10 deployments
        history = history[-10:]

        # Save
        with open(self.deployment_history_path, "w") as f:
            json.dump(history, f, indent=2)

        print(f"✅ Deployment history saved")

    def get_deployment_history(self, limit: int = 5) -> List[dict]:
        """Get deployment history"""
        if not self.deployment_history_path.exists():
            return []

        with open(self.deployment_history_path) as f:
            history = json.load(f)

        return history[-limit:]

    def rollback_to_previous(self) -> bool:
        """
        Rollback to previous deployment

        Returns:
            True if rollback successful
        """
        history = self.get_deployment_history(limit=2)

        if len(history) < 2:
            print("❌ No previous deployment found for rollback")
            return False

        previous = history[-2]

        print(f"🔄 Rolling back to deployment from {previous['timestamp']}")
        print(f"   Commit: {previous['commit_hash']}")
        print()

        # Pull previous images
        all_success = True
        for service_id, service_info in previous["services"].items():
            service = next(
                (s for s in self.registry_data["services"] if s["id"] == service_id),
                None,
            )

            if service:
                tag = service_info["tag"]
                success = self.pull_image(service, tag=tag)
                all_success = all_success and success

        if all_success:
            print("\n✅ Rollback images pulled successfully")
            print("   Run deployment to activate rolled-back images")
        else:
            print("\n❌ Rollback failed")

        return all_success

    def build_and_push_all(self, no_cache: bool = False) -> bool:
        """
        Build and push all active services

        Args:
            no_cache: If True, build without cache

        Returns:
            True if all builds and pushes successful
        """
        services = [
            s for s in self.registry_data["services"] if s["status"] == "active"
        ]

        print(f"\n{'='*60}")
        print(f"Building and Pushing Images - {self.environment}")
        print(f"Registry: {self.registry}")
        print(f"{'='*60}\n")

        all_success = True

        for service in services:
            # Build
            build_success = self.build_image(service, no_cache=no_cache)
            if not build_success:
                all_success = False
                continue

            # Tag
            tag_success = self.tag_image(service)
            if not tag_success:
                all_success = False
                continue

            # Push
            push_success = self.push_image(service)
            if not push_success:
                all_success = False

            print()

        if all_success:
            # Save deployment history
            self.save_deployment_history(services)
            print("\n✅ All images built and pushed successfully")
        else:
            print("\n❌ Some images failed to build or push")

        return all_success


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Docker Registry Manager for Maestro Services"
    )
    parser.add_argument(
        "action",
        choices=["build", "push", "pull", "build-push", "rollback", "history"],
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
        "--service", "-s", help="Specific service (optional, defaults to all)"
    )
    parser.add_argument(
        "--registry",
        "-r",
        help="Docker registry URL (defaults to DOCKER_REGISTRY env var or localhost:5000)",
    )
    parser.add_argument("--no-cache", action="store_true", help="Build without cache")
    parser.add_argument("--tag", "-t", help="Specific tag for pull operation")

    args = parser.parse_args()

    # Get project root
    project_root = Path(__file__).parent.parent.parent

    # Create registry manager
    manager = DockerRegistryManager(project_root, args.environment, args.registry)

    # Execute action
    if args.action == "build-push":
        success = manager.build_and_push_all(no_cache=args.no_cache)
        sys.exit(0 if success else 1)

    elif args.action == "rollback":
        success = manager.rollback_to_previous()
        sys.exit(0 if success else 1)

    elif args.action == "history":
        history = manager.get_deployment_history(limit=10)
        print(f"\nDeployment History - {args.environment}\n" + "=" * 60)
        for i, deployment in enumerate(reversed(history), 1):
            print(f"{i}. {deployment['timestamp']}")
            print(f"   Commit: {deployment['commit_hash']}")
            print(f"   Services: {len(deployment['services'])}")
            print()

    else:
        print(f"Action {args.action} not yet implemented in standalone mode")
        print("Use 'build-push', 'rollback', or 'history'")


if __name__ == "__main__":
    main()
