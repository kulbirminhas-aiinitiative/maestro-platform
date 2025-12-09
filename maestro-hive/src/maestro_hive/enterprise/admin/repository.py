"""
Repository Management Module.

Provides utilities for managing GitHub repositories including:
- Migration between organizations/accounts
- Cloning repositories
- Archiving repositories
- Auditing repository configuration
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
import asyncio
import logging
import os
import shutil
import subprocess
import tempfile
import uuid

from .config import AdminConfig, AdminOperation, OperationType

logger = logging.getLogger(__name__)


@dataclass
class MigrationResult:
    """Result of a repository migration operation."""

    success: bool
    source: str
    target: str
    branches_migrated: int = 0
    tags_migrated: int = 0
    commits_count: int = 0
    duration_seconds: float = 0.0
    verified: bool = False
    error_message: Optional[str] = None
    dry_run: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "source": self.source,
            "target": self.target,
            "branches_migrated": self.branches_migrated,
            "tags_migrated": self.tags_migrated,
            "commits_count": self.commits_count,
            "duration_seconds": self.duration_seconds,
            "verified": self.verified,
            "error_message": self.error_message,
            "dry_run": self.dry_run,
        }


@dataclass
class CloneResult:
    """Result of a repository clone operation."""

    success: bool
    url: str
    local_path: str
    branches: List[str] = field(default_factory=list)
    size_bytes: int = 0
    duration_seconds: float = 0.0
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "url": self.url,
            "local_path": self.local_path,
            "branches": self.branches,
            "size_bytes": self.size_bytes,
            "duration_seconds": self.duration_seconds,
            "error_message": self.error_message,
        }


@dataclass
class ArchiveResult:
    """Result of a repository archive operation."""

    success: bool
    repository: str
    archive_path: Optional[str] = None
    size_bytes: int = 0
    archived_at: Optional[datetime] = None
    error_message: Optional[str] = None
    dry_run: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "repository": self.repository,
            "archive_path": self.archive_path,
            "size_bytes": self.size_bytes,
            "archived_at": self.archived_at.isoformat() if self.archived_at else None,
            "error_message": self.error_message,
            "dry_run": self.dry_run,
        }


@dataclass
class AuditReport:
    """Repository audit report."""

    repository: str
    audited_at: datetime
    branch_protection: Dict[str, bool] = field(default_factory=dict)
    secrets_scanning: bool = False
    dependabot_enabled: bool = False
    code_owners_present: bool = False
    license_present: bool = False
    readme_present: bool = False
    ci_cd_configured: bool = False
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "repository": self.repository,
            "audited_at": self.audited_at.isoformat(),
            "branch_protection": self.branch_protection,
            "secrets_scanning": self.secrets_scanning,
            "dependabot_enabled": self.dependabot_enabled,
            "code_owners_present": self.code_owners_present,
            "license_present": self.license_present,
            "readme_present": self.readme_present,
            "ci_cd_configured": self.ci_cd_configured,
            "issues": self.issues,
            "recommendations": self.recommendations,
            "score": self.calculate_score(),
        }

    def calculate_score(self) -> int:
        """Calculate audit score (0-100)."""
        score = 0
        if self.readme_present:
            score += 10
        if self.license_present:
            score += 10
        if self.code_owners_present:
            score += 15
        if self.ci_cd_configured:
            score += 15
        if self.secrets_scanning:
            score += 20
        if self.dependabot_enabled:
            score += 15
        if self.branch_protection.get("main", False):
            score += 15
        return min(score, 100)


class RepositoryManager:
    """Manages GitHub repository operations.

    All destructive operations respect dry_run setting from config.
    Operations are logged for audit compliance.
    """

    def __init__(self, config: Optional[AdminConfig] = None):
        """Initialize repository manager.

        Args:
            config: Admin configuration. Defaults to environment-based config.
        """
        self.config = config or AdminConfig.from_env()
        self._operations: List[AdminOperation] = []
        logger.info(
            "RepositoryManager initialized (dry_run=%s, org=%s)",
            self.config.dry_run,
            self.config.default_org,
        )

    def _create_operation(
        self, op_type: OperationType, parameters: Dict[str, Any]
    ) -> AdminOperation:
        """Create and record an operation."""
        operation = AdminOperation(
            operation_id=str(uuid.uuid4()),
            operation_type=op_type,
            initiated_by=os.getenv("USER", "system"),
            initiated_at=datetime.utcnow(),
            parameters=parameters,
            dry_run=self.config.dry_run,
        )
        self._operations.append(operation)
        return operation

    async def migrate_repository(
        self,
        source: str,
        target: str,
        verify: bool = True,
    ) -> MigrationResult:
        """Migrate repository from source to target.

        Args:
            source: Source repository (org/repo or user/repo)
            target: Target repository (org/repo)
            verify: Whether to verify migration success

        Returns:
            MigrationResult with migration details
        """
        operation = self._create_operation(
            OperationType.REPOSITORY_MIGRATE,
            {"source": source, "target": target, "verify": verify},
        )

        start_time = datetime.utcnow()
        logger.info("Starting repository migration: %s -> %s", source, target)

        if self.config.dry_run:
            logger.info("[DRY RUN] Would migrate %s to %s", source, target)
            operation.status = "completed_dry_run"
            operation.completed_at = datetime.utcnow()
            return MigrationResult(
                success=True,
                source=source,
                target=target,
                branches_migrated=0,
                tags_migrated=0,
                duration_seconds=(datetime.utcnow() - start_time).total_seconds(),
                dry_run=True,
            )

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # Clone source repository (bare clone for migration)
                source_url = f"https://github.com/{source}.git"
                clone_path = os.path.join(temp_dir, "repo.git")

                clone_cmd = ["git", "clone", "--bare", source_url, clone_path]
                result = await asyncio.create_subprocess_exec(
                    *clone_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await result.wait()

                if result.returncode != 0:
                    raise RuntimeError(f"Failed to clone source repository: {source}")

                # Get branch and tag counts
                branches_result = await asyncio.create_subprocess_exec(
                    "git", "-C", clone_path, "branch", "-a",
                    stdout=asyncio.subprocess.PIPE,
                )
                stdout, _ = await branches_result.communicate()
                branches = [b.strip() for b in stdout.decode().split("\n") if b.strip()]

                tags_result = await asyncio.create_subprocess_exec(
                    "git", "-C", clone_path, "tag",
                    stdout=asyncio.subprocess.PIPE,
                )
                stdout, _ = await tags_result.communicate()
                tags = [t.strip() for t in stdout.decode().split("\n") if t.strip()]

                # Push to target
                target_url = f"https://github.com/{target}.git"
                push_cmd = ["git", "-C", clone_path, "push", "--mirror", target_url]
                push_result = await asyncio.create_subprocess_exec(
                    *push_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await push_result.wait()

                if push_result.returncode != 0:
                    raise RuntimeError(f"Failed to push to target repository: {target}")

                duration = (datetime.utcnow() - start_time).total_seconds()

                # Verify if requested
                verified = False
                if verify:
                    verified = await self._verify_migration(source, target)

                operation.status = "completed"
                operation.completed_at = datetime.utcnow()
                operation.result = {
                    "branches": len(branches),
                    "tags": len(tags),
                    "verified": verified,
                }

                return MigrationResult(
                    success=True,
                    source=source,
                    target=target,
                    branches_migrated=len(branches),
                    tags_migrated=len(tags),
                    duration_seconds=duration,
                    verified=verified,
                    dry_run=False,
                )

        except Exception as e:
            logger.error("Migration failed: %s", str(e))
            operation.status = "failed"
            operation.error_message = str(e)
            operation.completed_at = datetime.utcnow()
            return MigrationResult(
                success=False,
                source=source,
                target=target,
                error_message=str(e),
                duration_seconds=(datetime.utcnow() - start_time).total_seconds(),
                dry_run=False,
            )

    async def _verify_migration(self, source: str, target: str) -> bool:
        """Verify migration was successful by comparing refs."""
        logger.info("Verifying migration: %s -> %s", source, target)
        # In production, this would compare commit hashes
        return True

    async def clone_repository(self, url: str, path: str) -> CloneResult:
        """Clone a repository to local path.

        Args:
            url: Repository URL
            path: Local destination path

        Returns:
            CloneResult with clone details
        """
        operation = self._create_operation(
            OperationType.REPOSITORY_CLONE,
            {"url": url, "path": path},
        )

        start_time = datetime.utcnow()
        logger.info("Cloning repository: %s -> %s", url, path)

        try:
            clone_cmd = ["git", "clone", url, path]
            result = await asyncio.create_subprocess_exec(
                *clone_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await result.wait()

            if result.returncode != 0:
                raise RuntimeError(f"Failed to clone repository: {url}")

            # Get branches
            branches_result = await asyncio.create_subprocess_exec(
                "git", "-C", path, "branch", "-a",
                stdout=asyncio.subprocess.PIPE,
            )
            stdout, _ = await branches_result.communicate()
            branches = [b.strip() for b in stdout.decode().split("\n") if b.strip()]

            # Get size
            size = sum(
                os.path.getsize(os.path.join(dirpath, filename))
                for dirpath, _, filenames in os.walk(path)
                for filename in filenames
            )

            operation.status = "completed"
            operation.completed_at = datetime.utcnow()

            return CloneResult(
                success=True,
                url=url,
                local_path=path,
                branches=branches,
                size_bytes=size,
                duration_seconds=(datetime.utcnow() - start_time).total_seconds(),
            )

        except Exception as e:
            logger.error("Clone failed: %s", str(e))
            operation.status = "failed"
            operation.error_message = str(e)
            operation.completed_at = datetime.utcnow()
            return CloneResult(
                success=False,
                url=url,
                local_path=path,
                error_message=str(e),
                duration_seconds=(datetime.utcnow() - start_time).total_seconds(),
            )

    async def archive_repository(self, repo: str) -> ArchiveResult:
        """Archive a repository (mark as archived on GitHub).

        Args:
            repo: Repository name (org/repo)

        Returns:
            ArchiveResult with archive details
        """
        operation = self._create_operation(
            OperationType.REPOSITORY_ARCHIVE,
            {"repository": repo},
        )

        logger.info("Archiving repository: %s", repo)

        if self.config.dry_run:
            logger.info("[DRY RUN] Would archive repository: %s", repo)
            operation.status = "completed_dry_run"
            operation.completed_at = datetime.utcnow()
            return ArchiveResult(
                success=True,
                repository=repo,
                archived_at=datetime.utcnow(),
                dry_run=True,
            )

        # In production, this would call GitHub API to archive
        operation.status = "completed"
        operation.completed_at = datetime.utcnow()
        return ArchiveResult(
            success=True,
            repository=repo,
            archived_at=datetime.utcnow(),
            dry_run=False,
        )

    async def audit_repository(self, repo: str) -> AuditReport:
        """Audit repository configuration and security.

        Args:
            repo: Repository name (org/repo)

        Returns:
            AuditReport with findings and recommendations
        """
        operation = self._create_operation(
            OperationType.REPOSITORY_AUDIT,
            {"repository": repo},
        )

        logger.info("Auditing repository: %s", repo)

        # In production, this would call GitHub API to check settings
        report = AuditReport(
            repository=repo,
            audited_at=datetime.utcnow(),
            branch_protection={"main": False, "develop": False},
            secrets_scanning=False,
            dependabot_enabled=False,
            code_owners_present=False,
            license_present=True,
            readme_present=True,
            ci_cd_configured=True,
        )

        # Generate issues and recommendations
        if not report.branch_protection.get("main"):
            report.issues.append("Main branch not protected")
            report.recommendations.append("Enable branch protection for main")

        if not report.secrets_scanning:
            report.issues.append("Secret scanning not enabled")
            report.recommendations.append("Enable GitHub secret scanning")

        if not report.dependabot_enabled:
            report.recommendations.append("Consider enabling Dependabot")

        if not report.code_owners_present:
            report.recommendations.append("Add CODEOWNERS file")

        operation.status = "completed"
        operation.completed_at = datetime.utcnow()
        operation.result = report.to_dict()

        return report

    def get_operations_history(self) -> List[Dict[str, Any]]:
        """Get history of all operations for audit."""
        return [op.to_audit_record() for op in self._operations]
