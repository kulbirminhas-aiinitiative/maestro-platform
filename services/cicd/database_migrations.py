#!/usr/bin/env python3
"""
Database Migration Manager for Maestro Services

Handles automated database migrations for all services with databases.
Integrates with Alembic for schema versioning.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional


class DatabaseMigrationManager:
    """Manages database migrations for Maestro services"""

    def __init__(self, project_root: Path, environment: str):
        self.project_root = project_root
        self.environment = environment
        self.registry_path = project_root / "maestro_services_registry.json"
        self.registry = self._load_registry()

    def _load_registry(self) -> dict:
        """Load service registry"""
        with open(self.registry_path) as f:
            return json.load(f)

    def get_services_with_migrations(self) -> List[dict]:
        """Get all services that require database migrations"""
        services = []
        for service in self.registry["services"]:
            if service.get("status") == "active" and "postgres" in service.get(
                "dependencies", []
            ):
                services.append(service)
        return services

    def run_migrations(self, service: dict, dry_run: bool = False) -> bool:
        """
        Run database migrations for a service

        Args:
            service: Service configuration
            dry_run: If True, only show what would be done

        Returns:
            True if migrations successful, False otherwise
        """
        service_name = service["name"]
        service_path = self.project_root / service["source_path"]

        print(f"📊 Running migrations for {service_name}")

        # Check if Alembic is configured
        alembic_ini = service_path / "alembic.ini"
        if not alembic_ini.exists():
            print(f"  ⚠️  No alembic.ini found - skipping migrations")
            return True

        if dry_run:
            print(f"  [DRY RUN] Would run: alembic upgrade head")
            return True

        try:
            # Run Alembic upgrade
            result = subprocess.run(
                ["alembic", "upgrade", "head"],
                cwd=service_path,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutes
            )

            if result.returncode == 0:
                print(f"  ✅ Migrations completed successfully")
                if result.stdout:
                    print(f"     {result.stdout.strip()}")
                return True
            else:
                print(f"  ❌ Migration failed")
                print(f"     Error: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            print(f"  ❌ Migration timed out (> 5 minutes)")
            return False
        except Exception as e:
            print(f"  ❌ Migration error: {e}")
            return False

    def rollback_migration(self, service: dict, steps: int = 1) -> bool:
        """
        Rollback database migrations

        Args:
            service: Service configuration
            steps: Number of migration steps to rollback

        Returns:
            True if rollback successful
        """
        service_name = service["name"]
        service_path = self.project_root / service["source_path"]

        print(f"🔄 Rolling back {steps} migration(s) for {service_name}")

        try:
            # Rollback using Alembic downgrade
            result = subprocess.run(
                ["alembic", "downgrade", f"-{steps}"],
                cwd=service_path,
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode == 0:
                print(f"  ✅ Rollback completed")
                return True
            else:
                print(f"  ❌ Rollback failed: {result.stderr}")
                return False

        except Exception as e:
            print(f"  ❌ Rollback error: {e}")
            return False

    def check_migration_status(self, service: dict) -> Dict[str, any]:
        """
        Check current migration status for a service

        Returns:
            Dict with current and head revisions
        """
        service_path = self.project_root / service["source_path"]

        try:
            # Get current revision
            result = subprocess.run(
                ["alembic", "current"],
                cwd=service_path,
                capture_output=True,
                text=True,
                timeout=30,
            )

            current_revision = result.stdout.strip() if result.returncode == 0 else None

            # Get head revision
            result = subprocess.run(
                ["alembic", "heads"],
                cwd=service_path,
                capture_output=True,
                text=True,
                timeout=30,
            )

            head_revision = result.stdout.strip() if result.returncode == 0 else None

            return {
                "current": current_revision,
                "head": head_revision,
                "needs_upgrade": current_revision != head_revision,
            }

        except Exception as e:
            print(f"  ⚠️  Could not check migration status: {e}")
            return {"current": None, "head": None, "needs_upgrade": False}

    def create_migration(self, service: dict, message: str) -> bool:
        """
        Create a new migration for a service

        Args:
            service: Service configuration
            message: Migration message/description

        Returns:
            True if migration created successfully
        """
        service_path = self.project_root / service["source_path"]

        print(f"📝 Creating migration for {service['name']}: {message}")

        try:
            result = subprocess.run(
                ["alembic", "revision", "--autogenerate", "-m", message],
                cwd=service_path,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                print(f"  ✅ Migration created")
                print(f"     {result.stdout.strip()}")
                return True
            else:
                print(f"  ❌ Failed to create migration: {result.stderr}")
                return False

        except Exception as e:
            print(f"  ❌ Error creating migration: {e}")
            return False

    def run_all_migrations(self, dry_run: bool = False) -> bool:
        """
        Run migrations for all services with databases

        Args:
            dry_run: If True, only show what would be done

        Returns:
            True if all migrations successful
        """
        services = self.get_services_with_migrations()

        if not services:
            print("No services require database migrations")
            return True

        print(f"\n{'='*60}")
        print(f"Running Database Migrations - {self.environment}")
        print(f"{'='*60}\n")

        all_success = True

        for service in services:
            # Check if migration is needed
            status = self.check_migration_status(service)

            if status.get("needs_upgrade"):
                print(
                    f"🔄 {service['name']}: Needs upgrade "
                    f"({status.get('current')} → {status.get('head')})"
                )
                success = self.run_migrations(service, dry_run=dry_run)
            else:
                print(f"✅ {service['name']}: Already up to date")
                success = True

            all_success = all_success and success
            print()

        if all_success:
            print("✅ All migrations completed successfully")
        else:
            print("❌ Some migrations failed")

        return all_success


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Database Migration Manager for Maestro Services"
    )
    parser.add_argument(
        "action",
        choices=["run", "status", "rollback", "create"],
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
        "--service",
        "-s",
        help="Specific service to migrate (optional, defaults to all)",
    )
    parser.add_argument(
        "--message", "-m", help="Migration message (for 'create' action)"
    )
    parser.add_argument(
        "--steps", type=int, default=1, help="Number of steps to rollback"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be done without doing it"
    )

    args = parser.parse_args()

    # Get project root
    project_root = Path(__file__).parent.parent.parent

    # Create migration manager
    manager = DatabaseMigrationManager(project_root, args.environment)

    # Execute action
    if args.action == "run":
        success = manager.run_all_migrations(dry_run=args.dry_run)
        sys.exit(0 if success else 1)

    elif args.action == "status":
        services = manager.get_services_with_migrations()
        print(f"\nMigration Status - {args.environment}\n" + "=" * 60)
        for service in services:
            status = manager.check_migration_status(service)
            needs = "⚠️  NEEDS UPGRADE" if status.get("needs_upgrade") else "✅ UP TO DATE"
            print(f"{service['name']}: {needs}")
            print(f"  Current: {status.get('current')}")
            print(f"  Head:    {status.get('head')}\n")

    elif args.action == "rollback":
        if not args.service:
            print("❌ --service required for rollback")
            sys.exit(1)

        # Find service
        service = next(
            (s for s in manager.registry["services"] if s["id"] == args.service), None
        )
        if not service:
            print(f"❌ Service not found: {args.service}")
            sys.exit(1)

        success = manager.rollback_migration(service, args.steps)
        sys.exit(0 if success else 1)

    elif args.action == "create":
        if not args.service or not args.message:
            print("❌ --service and --message required for create")
            sys.exit(1)

        # Find service
        service = next(
            (s for s in manager.registry["services"] if s["id"] == args.service), None
        )
        if not service:
            print(f"❌ Service not found: {args.service}")
            sys.exit(1)

        success = manager.create_migration(service, args.message)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
