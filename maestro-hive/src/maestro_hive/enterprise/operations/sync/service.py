"""
Environment Synchronization Service.

EPIC: MD-2790 - [Ops] Environment Synchronization
Main orchestrator for synchronizing Demo, Sandbox, and Dev environments.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from .schema_sync import SchemaSyncManager, SchemaSyncResult, EnvironmentDBConfig
from .git_sync import GitSyncManager, GitSyncResult, VersionInfo
from .data_sync import DataSyncManager, DataSyncResult, TableSyncConfig

logger = logging.getLogger(__name__)


class SyncOperationType(str, Enum):
    """Type of synchronization operation."""
    FULL = "full"  # All sync types
    SCHEMA = "schema"  # Schema only
    GIT = "git"  # Git commits only
    DATA = "data"  # Data only


class FullSyncStatus(str, Enum):
    """Status of full sync operation."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


@dataclass
class FullSyncResult:
    """Result of a full environment sync operation."""
    sync_id: str
    operation_type: SyncOperationType
    source_env: str
    target_envs: list[str]
    status: FullSyncStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    schema_result: Optional[SchemaSyncResult] = None
    git_result: Optional[GitSyncResult] = None
    data_result: Optional[DataSyncResult] = None
    errors: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "sync_id": self.sync_id,
            "operation_type": self.operation_type.value,
            "source_environment": self.source_env,
            "target_environments": self.target_envs,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "schema_sync": self.schema_result.to_dict() if self.schema_result else None,
            "git_sync": self.git_result.to_dict() if self.git_result else None,
            "data_sync": self.data_result.to_dict() if self.data_result else None,
            "errors": self.errors,
            "details": self.details
        }


class EnvironmentSyncService:
    """
    Main orchestrator for environment synchronization.

    Coordinates schema, git, and data synchronization across environments.

    EPIC: MD-2790 - [Ops] Environment Synchronization

    Features:
    - Full environment sync (schema + git + data)
    - Selective sync (schema only, git only, data only)
    - Environment comparison and validation
    - Version tracking and reporting
    """

    SUPPORTED_ENVIRONMENTS = ["sandbox", "demo", "dev", "production"]

    def __init__(
        self,
        schema_manager: Optional[SchemaSyncManager] = None,
        git_manager: Optional[GitSyncManager] = None,
        data_manager: Optional[DataSyncManager] = None
    ):
        self.schema_manager = schema_manager or SchemaSyncManager()
        self.git_manager = git_manager or GitSyncManager()
        self.data_manager = data_manager or DataSyncManager()
        self._sync_history: list[FullSyncResult] = []

    def validate_environments(self, environments: list[str]) -> list[str]:
        """Validate environment names and return errors."""
        errors = []
        for env in environments:
            if env not in self.SUPPORTED_ENVIRONMENTS:
                errors.append(f"Unknown environment: {env}")
        return errors

    async def sync_full(
        self,
        source: str,
        targets: list[str],
        run_schema_sync: bool = True,
        run_git_sync: bool = True,
        run_data_sync: bool = True,
        run_seed: bool = False
    ) -> FullSyncResult:
        """
        Perform full environment synchronization.

        This is the main entry point for synchronizing environments.
        Coordinates schema, git, and data sync in the correct order.
        """
        sync_id = str(uuid.uuid4())
        result = FullSyncResult(
            sync_id=sync_id,
            operation_type=SyncOperationType.FULL,
            source_env=source,
            target_envs=targets,
            status=FullSyncStatus.IN_PROGRESS,
            started_at=datetime.utcnow()
        )

        # Validate environments
        validation_errors = self.validate_environments([source] + targets)
        if validation_errors:
            result.errors.extend(validation_errors)
            result.status = FullSyncStatus.FAILED
            result.completed_at = datetime.utcnow()
            self._sync_history.append(result)
            return result

        try:
            success_count = 0
            total_operations = sum([run_schema_sync, run_git_sync, run_data_sync])

            # 1. Git Sync (first to ensure correct codebase)
            if run_git_sync:
                logger.info(f"Starting git sync from {source} to {targets}")
                try:
                    source_commit = self.git_manager.get_current_commit(source)
                    if source_commit:
                        git_result = await self.git_manager.sync_to_commit(
                            targets,
                            source_commit
                        )
                        result.git_result = git_result
                        if git_result.status.value == "completed":
                            success_count += 1
                        else:
                            result.errors.append(f"Git sync failed: {git_result.error}")
                    else:
                        result.errors.append(f"Could not get commit from {source}")
                except Exception as e:
                    result.errors.append(f"Git sync error: {e}")

            # 2. Schema Sync (second to apply migrations)
            if run_schema_sync:
                logger.info(f"Starting schema sync from {source} to {targets}")
                try:
                    schema_result = await self.schema_manager.sync_schema(
                        source,
                        targets,
                        run_generate=True,
                        run_seed=run_seed
                    )
                    result.schema_result = schema_result
                    if schema_result.status.value == "completed":
                        success_count += 1
                    else:
                        result.errors.append(f"Schema sync failed: {schema_result.error}")
                except Exception as e:
                    result.errors.append(f"Schema sync error: {e}")

            # 3. Data Sync (last to sync data)
            if run_data_sync:
                logger.info(f"Starting data sync from {source} to {targets}")
                try:
                    for target in targets:
                        data_result = await self.data_manager.sync_data(
                            source,
                            target
                        )
                        result.data_result = data_result
                        if data_result.status.value == "completed":
                            success_count += 1
                        else:
                            result.errors.append(
                                f"Data sync to {target} failed: {data_result.error}"
                            )
                except Exception as e:
                    result.errors.append(f"Data sync error: {e}")

            # Determine final status
            if success_count == total_operations:
                result.status = FullSyncStatus.COMPLETED
            elif success_count > 0:
                result.status = FullSyncStatus.PARTIAL
            else:
                result.status = FullSyncStatus.FAILED

            result.completed_at = datetime.utcnow()

        except Exception as e:
            result.status = FullSyncStatus.FAILED
            result.errors.append(f"Unexpected error: {e}")
            result.completed_at = datetime.utcnow()
            logger.error(f"Full sync failed: {e}")

        self._sync_history.append(result)
        return result

    async def sync_schema(
        self,
        source: str,
        targets: list[str],
        run_seed: bool = False
    ) -> SchemaSyncResult:
        """Perform schema-only synchronization."""
        return await self.schema_manager.sync_schema(
            source,
            targets,
            run_generate=True,
            run_seed=run_seed
        )

    async def sync_git(
        self,
        source: str,
        targets: list[str]
    ) -> GitSyncResult:
        """Perform git-only synchronization."""
        source_commit = self.git_manager.get_current_commit(source)
        if not source_commit:
            raise ValueError(f"Could not get commit from {source}")
        return await self.git_manager.sync_to_commit(targets, source_commit)

    async def sync_data(
        self,
        source: str,
        target: str,
        tables: Optional[list[TableSyncConfig]] = None
    ) -> DataSyncResult:
        """Perform data-only synchronization."""
        return await self.data_manager.sync_data(source, target, tables)

    def get_environment_status(self, environment: str) -> dict[str, Any]:
        """Get comprehensive status for an environment."""
        status = {
            "environment": environment,
            "checked_at": datetime.utcnow().isoformat()
        }

        # Git status
        try:
            status["git"] = {
                "has_git": self.git_manager.has_git_directory(environment),
                "commit": self.git_manager.get_short_commit(environment),
                "branch": self.git_manager.get_current_branch(environment),
                "remote": self.git_manager.get_remote_url(environment)
            }
        except Exception as e:
            status["git"] = {"error": str(e)}

        # Schema status
        try:
            status["schema"] = {
                "version": self.schema_manager.get_schema_version(environment)
            }
        except Exception as e:
            status["schema"] = {"error": str(e)}

        # Data status
        try:
            tables = ["users", "ai_agents", "team_blueprints"]
            status["data"] = {
                table: self.data_manager.get_table_count(environment, table)
                for table in tables
            }
        except Exception as e:
            status["data"] = {"error": str(e)}

        return status

    def compare_environments(
        self,
        source: str,
        targets: list[str]
    ) -> dict[str, Any]:
        """Compare source environment with multiple targets."""
        comparison = {
            "source_environment": source,
            "target_environments": targets,
            "compared_at": datetime.utcnow().isoformat(),
            "targets": {}
        }

        # Get source status
        source_status = self.get_environment_status(source)

        for target in targets:
            target_status = self.get_environment_status(target)

            target_comparison = {
                "git_matches": (
                    source_status.get("git", {}).get("commit") ==
                    target_status.get("git", {}).get("commit")
                ),
                "schema_matches": (
                    source_status.get("schema", {}).get("version") ==
                    target_status.get("schema", {}).get("version")
                ),
                "source_status": source_status,
                "target_status": target_status
            }

            comparison["targets"][target] = target_comparison

        return comparison

    def generate_version_info(
        self,
        environment: str,
        version: str = "1.0.0"
    ) -> VersionInfo:
        """Generate and save VERSION.json for environment."""
        return self.git_manager.create_version_json(environment, version)

    def get_sync_history(self, limit: int = 50) -> list[FullSyncResult]:
        """Get recent sync history."""
        return self._sync_history[-limit:]

    def generate_sync_report(
        self,
        source: str,
        targets: list[str]
    ) -> dict[str, Any]:
        """
        Generate comprehensive sync recommendation report.

        This report can be used to plan sync operations.
        """
        comparison = self.compare_environments(source, targets)

        report = {
            "title": "Environment Sync Report",
            "epic": "MD-2790",
            "generated_at": datetime.utcnow().isoformat(),
            "source": source,
            "targets": targets,
            "recommendations": [],
            "environment_comparison": comparison
        }

        for target, data in comparison.get("targets", {}).items():
            if not data.get("git_matches"):
                report["recommendations"].append({
                    "target": target,
                    "type": "git_sync",
                    "reason": f"Git commit differs from {source}"
                })

            if not data.get("schema_matches"):
                report["recommendations"].append({
                    "target": target,
                    "type": "schema_sync",
                    "reason": f"Schema version differs from {source}"
                })

        # Add data comparison
        try:
            for target in targets:
                data_comparison = self.data_manager.compare_table_counts(source, target)
                if not data_comparison.get("all_match"):
                    for table, info in data_comparison.get("tables", {}).items():
                        if not info.get("matches"):
                            report["recommendations"].append({
                                "target": target,
                                "type": "data_sync",
                                "table": table,
                                "reason": f"Table {table} has {info.get('difference', 0)} record difference"
                            })
        except Exception as e:
            report["recommendations"].append({
                "type": "error",
                "reason": f"Could not compare data: {e}"
            })

        return report

    def verify_acceptance_criteria(
        self,
        environments: list[str] = None
    ) -> dict[str, Any]:
        """
        Verify all acceptance criteria for MD-2790.

        Returns verification status for each AC.
        """
        if environments is None:
            environments = ["sandbox", "demo", "dev"]

        verification = {
            "epic": "MD-2790",
            "verified_at": datetime.utcnow().isoformat(),
            "acceptance_criteria": {}
        }

        # AC-1: Same Prisma schema
        try:
            schema_versions = {
                env: self.schema_manager.get_schema_version(env)
                for env in environments
            }
            unique_versions = set(schema_versions.values())
            verification["acceptance_criteria"]["AC-1"] = {
                "description": "Demo and Dev have same Prisma schema as Sandbox",
                "verified": len(unique_versions) == 1,
                "details": schema_versions
            }
        except Exception as e:
            verification["acceptance_criteria"]["AC-1"] = {
                "verified": False,
                "error": str(e)
            }

        # AC-2: Demo user exists
        try:
            demo_user_status = {
                env: self.schema_manager.verify_demo_user_exists(env)
                for env in environments
            }
            all_exist = all(s.get("exists") for s in demo_user_status.values())
            verification["acceptance_criteria"]["AC-2"] = {
                "description": "demo@fifth-9.com user exists on all environments",
                "verified": all_exist,
                "details": demo_user_status
            }
        except Exception as e:
            verification["acceptance_criteria"]["AC-2"] = {
                "verified": False,
                "error": str(e)
            }

        # AC-3: AI Agents count matches
        try:
            agent_counts = {
                env: self.schema_manager.count_ai_agents(env)
                for env in environments
            }
            counts = [c.get("count", 0) for c in agent_counts.values()]
            verification["acceptance_criteria"]["AC-3"] = {
                "description": "AI Agents count matches across all environments",
                "verified": len(set(counts)) == 1,
                "details": agent_counts
            }
        except Exception as e:
            verification["acceptance_criteria"]["AC-3"] = {
                "verified": False,
                "error": str(e)
            }

        # AC-4: Teams configuration matches
        try:
            team_counts = {
                env: self.schema_manager.count_teams(env)
                for env in environments
            }
            counts = [c.get("count", 0) for c in team_counts.values()]
            verification["acceptance_criteria"]["AC-4"] = {
                "description": "Teams configuration matches across all environments",
                "verified": len(set(counts)) == 1,
                "details": team_counts
            }
        except Exception as e:
            verification["acceptance_criteria"]["AC-4"] = {
                "verified": False,
                "error": str(e)
            }

        # AC-5: Git directory exists
        try:
            git_status = {
                env: self.git_manager.has_git_directory(env)
                for env in environments
            }
            verification["acceptance_criteria"]["AC-5"] = {
                "description": "All environments have .git directory",
                "verified": all(git_status.values()),
                "details": git_status
            }
        except Exception as e:
            verification["acceptance_criteria"]["AC-5"] = {
                "verified": False,
                "error": str(e)
            }

        # AC-6: Same git commit
        try:
            commits = {
                env: self.git_manager.get_short_commit(env)
                for env in environments
            }
            unique_commits = set(commits.values())
            verification["acceptance_criteria"]["AC-6"] = {
                "description": "All environments show same commit",
                "verified": len(unique_commits) == 1,
                "details": commits
            }
        except Exception as e:
            verification["acceptance_criteria"]["AC-6"] = {
                "verified": False,
                "error": str(e)
            }

        # Summary
        verified_count = sum(
            1 for ac in verification["acceptance_criteria"].values()
            if ac.get("verified")
        )
        total_count = len(verification["acceptance_criteria"])
        verification["summary"] = {
            "total": total_count,
            "verified": verified_count,
            "pending": total_count - verified_count,
            "compliance_percentage": round(verified_count / total_count * 100, 2)
        }

        return verification
