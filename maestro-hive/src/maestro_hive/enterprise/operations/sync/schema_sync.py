"""
Schema Synchronization Manager.

EPIC: MD-2790 - AC-1, AC-2, AC-3, AC-4
Handles Prisma schema synchronization across environments.
"""

import logging
import subprocess
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class SchemaSyncStatus(str, Enum):
    """Schema sync operation status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class SchemaSyncResult:
    """Result of a schema sync operation."""
    sync_id: str
    source_env: str
    target_env: str
    status: SchemaSyncStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    migrations_applied: int = 0
    seed_run: bool = False
    error: Optional[str] = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "sync_id": self.sync_id,
            "source_environment": self.source_env,
            "target_environment": self.target_env,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "migrations_applied": self.migrations_applied,
            "seed_run": self.seed_run,
            "error": self.error,
            "details": self.details
        }


@dataclass
class EnvironmentDBConfig:
    """Database configuration for an environment."""
    host: str
    port: int
    database: str
    username: str
    password: str = ""

    @property
    def connection_string(self) -> str:
        """Generate PostgreSQL connection string."""
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"


class SchemaSyncManager:
    """
    Manages Prisma schema synchronization across environments.

    Implements:
    - AC-1: Demo and Dev have same Prisma schema as Sandbox
    - AC-2: demo@fifth-9.com user exists on all environments
    - AC-3: AI Agents count matches across all environments
    - AC-4: Teams configuration matches across all environments
    """

    # Default environment configurations
    DEFAULT_CONFIGS = {
        "sandbox": EnvironmentDBConfig(
            host="localhost",
            port=15432,
            database="maestro",
            username="postgres"
        ),
        "demo": EnvironmentDBConfig(
            host="localhost",
            port=5432,
            database="maestro",
            username="postgres"
        ),
        "dev": EnvironmentDBConfig(
            host="localhost",
            port=5432,
            database="maestro",
            username="postgres"
        ),
        "production": EnvironmentDBConfig(
            host="localhost",
            port=5435,
            database="maestro",
            username="postgres"
        )
    }

    def __init__(
        self,
        project_root: Optional[Path] = None,
        configs: Optional[dict[str, EnvironmentDBConfig]] = None
    ):
        self.project_root = project_root or Path("/home/ec2-user/projects/maestro-frontend")
        self.configs = configs or self.DEFAULT_CONFIGS
        self._sync_history: list[SchemaSyncResult] = []

    def get_schema_version(self, environment: str) -> Optional[str]:
        """Get current Prisma migration version for an environment."""
        if environment not in self.configs:
            raise ValueError(f"Unknown environment: {environment}")

        config = self.configs[environment]
        try:
            # Query _prisma_migrations table
            result = subprocess.run(
                [
                    "psql",
                    "-h", config.host,
                    "-p", str(config.port),
                    "-U", config.username,
                    "-d", config.database,
                    "-t", "-c",
                    "SELECT migration_name FROM _prisma_migrations ORDER BY finished_at DESC LIMIT 1"
                ],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except Exception as e:
            logger.error(f"Failed to get schema version for {environment}: {e}")
            return None

    def compare_schemas(
        self,
        source: str,
        target: str
    ) -> dict[str, Any]:
        """Compare Prisma schemas between environments."""
        source_version = self.get_schema_version(source)
        target_version = self.get_schema_version(target)

        return {
            "source_environment": source,
            "target_environment": target,
            "source_version": source_version,
            "target_version": target_version,
            "schemas_match": source_version == target_version,
            "checked_at": datetime.utcnow().isoformat()
        }

    async def run_migrate_deploy(
        self,
        environment: str,
        dry_run: bool = False
    ) -> dict[str, Any]:
        """
        Run prisma migrate deploy on target environment.

        AC-1: Ensures target has same schema as source.
        """
        if environment not in self.configs:
            raise ValueError(f"Unknown environment: {environment}")

        config = self.configs[environment]
        env_vars = {"DATABASE_URL": config.connection_string}

        if dry_run:
            return {
                "status": "dry_run",
                "environment": environment,
                "command": "npx prisma migrate deploy",
                "database_url": f"postgresql://***@{config.host}:{config.port}/{config.database}"
            }

        try:
            result = subprocess.run(
                ["npx", "prisma", "migrate", "deploy"],
                cwd=str(self.project_root),
                env={**dict(subprocess.os.environ), **env_vars},
                capture_output=True,
                text=True,
                timeout=120
            )

            return {
                "status": "success" if result.returncode == 0 else "failed",
                "environment": environment,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
        except subprocess.TimeoutExpired:
            return {
                "status": "timeout",
                "environment": environment,
                "error": "Migration timed out after 120 seconds"
            }
        except Exception as e:
            return {
                "status": "error",
                "environment": environment,
                "error": str(e)
            }

    async def run_prisma_generate(self, environment: str) -> dict[str, Any]:
        """Run prisma generate for Prisma client update."""
        if environment not in self.configs:
            raise ValueError(f"Unknown environment: {environment}")

        config = self.configs[environment]
        env_vars = {"DATABASE_URL": config.connection_string}

        try:
            result = subprocess.run(
                ["npx", "prisma", "generate"],
                cwd=str(self.project_root),
                env={**dict(subprocess.os.environ), **env_vars},
                capture_output=True,
                text=True,
                timeout=60
            )

            return {
                "status": "success" if result.returncode == 0 else "failed",
                "environment": environment,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
        except Exception as e:
            return {
                "status": "error",
                "environment": environment,
                "error": str(e)
            }

    async def run_db_seed(self, environment: str) -> dict[str, Any]:
        """
        Run prisma db seed on target environment.

        AC-2: Seeds demo user
        AC-3: Seeds AI Agents
        AC-4: Seeds Teams configuration
        """
        if environment not in self.configs:
            raise ValueError(f"Unknown environment: {environment}")

        config = self.configs[environment]
        env_vars = {"DATABASE_URL": config.connection_string}

        try:
            result = subprocess.run(
                ["npx", "prisma", "db", "seed"],
                cwd=str(self.project_root),
                env={**dict(subprocess.os.environ), **env_vars},
                capture_output=True,
                text=True,
                timeout=120
            )

            return {
                "status": "success" if result.returncode == 0 else "failed",
                "environment": environment,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
        except Exception as e:
            return {
                "status": "error",
                "environment": environment,
                "error": str(e)
            }

    async def sync_schema(
        self,
        source: str,
        targets: list[str],
        run_generate: bool = True,
        run_seed: bool = False
    ) -> SchemaSyncResult:
        """
        Synchronize schema from source to target environments.

        Full implementation of AC-1 through AC-4.
        """
        import uuid

        sync_id = str(uuid.uuid4())
        result = SchemaSyncResult(
            sync_id=sync_id,
            source_env=source,
            target_env=",".join(targets),
            status=SchemaSyncStatus.IN_PROGRESS,
            started_at=datetime.utcnow()
        )

        try:
            migrations_count = 0
            details: dict[str, Any] = {"targets": {}}

            for target in targets:
                target_details: dict[str, Any] = {}

                # Run migrate deploy
                migrate_result = await self.run_migrate_deploy(target)
                target_details["migrate"] = migrate_result
                if migrate_result["status"] == "success":
                    migrations_count += 1

                # Run generate if requested
                if run_generate:
                    generate_result = await self.run_prisma_generate(target)
                    target_details["generate"] = generate_result

                # Run seed if requested
                if run_seed:
                    seed_result = await self.run_db_seed(target)
                    target_details["seed"] = seed_result
                    result.seed_run = True

                details["targets"][target] = target_details

            result.migrations_applied = migrations_count
            result.details = details
            result.status = SchemaSyncStatus.COMPLETED
            result.completed_at = datetime.utcnow()

        except Exception as e:
            result.status = SchemaSyncStatus.FAILED
            result.error = str(e)
            result.completed_at = datetime.utcnow()
            logger.error(f"Schema sync failed: {e}")

        self._sync_history.append(result)
        return result

    def get_sync_history(self, limit: int = 50) -> list[SchemaSyncResult]:
        """Get recent sync history."""
        return self._sync_history[-limit:]

    def verify_demo_user_exists(self, environment: str) -> dict[str, Any]:
        """
        Verify demo@fifth-9.com user exists in environment.

        AC-2: demo@fifth-9.com user exists on all environments with same credentials.
        """
        if environment not in self.configs:
            raise ValueError(f"Unknown environment: {environment}")

        config = self.configs[environment]
        try:
            result = subprocess.run(
                [
                    "psql",
                    "-h", config.host,
                    "-p", str(config.port),
                    "-U", config.username,
                    "-d", config.database,
                    "-t", "-c",
                    "SELECT id, email, role FROM users WHERE email = 'demo@fifth-9.com'"
                ],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0 and result.stdout.strip():
                parts = result.stdout.strip().split("|")
                return {
                    "exists": True,
                    "environment": environment,
                    "user_id": parts[0].strip() if len(parts) > 0 else None,
                    "email": parts[1].strip() if len(parts) > 1 else None,
                    "role": parts[2].strip() if len(parts) > 2 else None
                }
            return {
                "exists": False,
                "environment": environment
            }
        except Exception as e:
            return {
                "exists": False,
                "environment": environment,
                "error": str(e)
            }

    def count_ai_agents(self, environment: str) -> dict[str, Any]:
        """
        Count AI Agents in environment.

        AC-3: AI Agents count matches across all environments.
        """
        if environment not in self.configs:
            raise ValueError(f"Unknown environment: {environment}")

        config = self.configs[environment]
        try:
            result = subprocess.run(
                [
                    "psql",
                    "-h", config.host,
                    "-p", str(config.port),
                    "-U", config.username,
                    "-d", config.database,
                    "-t", "-c",
                    "SELECT COUNT(*) FROM ai_agents"
                ],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                count = int(result.stdout.strip())
                return {
                    "environment": environment,
                    "count": count
                }
            return {
                "environment": environment,
                "count": 0,
                "error": result.stderr
            }
        except Exception as e:
            return {
                "environment": environment,
                "count": 0,
                "error": str(e)
            }

    def count_teams(self, environment: str) -> dict[str, Any]:
        """
        Count Teams in environment.

        AC-4: Teams configuration matches across all environments.
        """
        if environment not in self.configs:
            raise ValueError(f"Unknown environment: {environment}")

        config = self.configs[environment]
        try:
            result = subprocess.run(
                [
                    "psql",
                    "-h", config.host,
                    "-p", str(config.port),
                    "-U", config.username,
                    "-d", config.database,
                    "-t", "-c",
                    "SELECT COUNT(*) FROM team_blueprints"
                ],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                count = int(result.stdout.strip())
                return {
                    "environment": environment,
                    "count": count
                }
            return {
                "environment": environment,
                "count": 0,
                "error": result.stderr
            }
        except Exception as e:
            return {
                "environment": environment,
                "count": 0,
                "error": str(e)
            }
