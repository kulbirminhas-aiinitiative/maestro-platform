"""Tests for repository management module."""

import pytest
from datetime import datetime

from maestro_hive.enterprise.admin.config import AdminConfig
from maestro_hive.enterprise.admin.repository import (
    RepositoryManager,
    MigrationResult,
    CloneResult,
    ArchiveResult,
    AuditReport,
)


class TestMigrationResult:
    """Tests for MigrationResult dataclass."""

    def test_create_migration_result(self):
        """Test creating a migration result."""
        result = MigrationResult(
            success=True,
            source="user/repo",
            target="org/repo",
            branches_migrated=5,
            tags_migrated=10,
            duration_seconds=30.5,
        )

        assert result.success is True
        assert result.source == "user/repo"
        assert result.target == "org/repo"
        assert result.branches_migrated == 5
        assert result.tags_migrated == 10

    def test_migration_result_to_dict(self):
        """Test converting migration result to dict."""
        result = MigrationResult(
            success=True,
            source="user/repo",
            target="org/repo",
            branches_migrated=5,
            tags_migrated=10,
            duration_seconds=30.5,
            verified=True,
        )

        data = result.to_dict()

        assert data["success"] is True
        assert data["source"] == "user/repo"
        assert data["verified"] is True


class TestCloneResult:
    """Tests for CloneResult dataclass."""

    def test_create_clone_result(self):
        """Test creating a clone result."""
        result = CloneResult(
            success=True,
            url="https://github.com/org/repo.git",
            local_path="/tmp/repo",
            branches=["main", "develop"],
            size_bytes=1024000,
        )

        assert result.success is True
        assert result.url == "https://github.com/org/repo.git"
        assert len(result.branches) == 2


class TestArchiveResult:
    """Tests for ArchiveResult dataclass."""

    def test_create_archive_result(self):
        """Test creating an archive result."""
        result = ArchiveResult(
            success=True,
            repository="org/repo",
            archived_at=datetime.utcnow(),
            dry_run=True,
        )

        assert result.success is True
        assert result.repository == "org/repo"
        assert result.dry_run is True


class TestAuditReport:
    """Tests for AuditReport dataclass."""

    def test_create_audit_report(self):
        """Test creating an audit report."""
        report = AuditReport(
            repository="org/repo",
            audited_at=datetime.utcnow(),
            secrets_scanning=True,
            readme_present=True,
        )

        assert report.repository == "org/repo"
        assert report.secrets_scanning is True

    def test_calculate_score_full(self):
        """Test score calculation with all checks passing."""
        report = AuditReport(
            repository="org/repo",
            audited_at=datetime.utcnow(),
            branch_protection={"main": True},
            secrets_scanning=True,
            dependabot_enabled=True,
            code_owners_present=True,
            license_present=True,
            readme_present=True,
            ci_cd_configured=True,
        )

        assert report.calculate_score() == 100

    def test_calculate_score_partial(self):
        """Test score calculation with partial checks."""
        report = AuditReport(
            repository="org/repo",
            audited_at=datetime.utcnow(),
            readme_present=True,  # 10 points
            license_present=True,  # 10 points
        )

        assert report.calculate_score() == 20

    def test_calculate_score_empty(self):
        """Test score calculation with no checks passing."""
        report = AuditReport(
            repository="org/repo",
            audited_at=datetime.utcnow(),
        )

        assert report.calculate_score() == 0


class TestRepositoryManager:
    """Tests for RepositoryManager class."""

    def test_init_default_config(self):
        """Test initialization with default config."""
        manager = RepositoryManager()
        assert manager.config.dry_run is True
        assert manager.config.default_org == "fifth-9"

    def test_init_custom_config(self):
        """Test initialization with custom config."""
        config = AdminConfig(
            default_org="test-org",
            dry_run=True,
        )
        manager = RepositoryManager(config)
        assert manager.config.default_org == "test-org"

    @pytest.mark.asyncio
    async def test_migrate_repository_dry_run(self):
        """Test repository migration in dry run mode."""
        config = AdminConfig(dry_run=True)
        manager = RepositoryManager(config)

        result = await manager.migrate_repository(
            source="user/repo",
            target="org/repo",
            verify=True,
        )

        assert result.success is True
        assert result.dry_run is True
        assert result.source == "user/repo"
        assert result.target == "org/repo"

    @pytest.mark.asyncio
    async def test_archive_repository_dry_run(self):
        """Test repository archival in dry run mode."""
        config = AdminConfig(dry_run=True)
        manager = RepositoryManager(config)

        result = await manager.archive_repository("org/repo")

        assert result.success is True
        assert result.dry_run is True
        assert result.repository == "org/repo"

    @pytest.mark.asyncio
    async def test_audit_repository(self):
        """Test repository audit."""
        config = AdminConfig(dry_run=True)
        manager = RepositoryManager(config)

        report = await manager.audit_repository("org/repo")

        assert report.repository == "org/repo"
        assert report.audited_at is not None
        assert len(report.recommendations) > 0

    def test_get_operations_history(self):
        """Test getting operations history."""
        manager = RepositoryManager()
        history = manager.get_operations_history()
        assert isinstance(history, list)
