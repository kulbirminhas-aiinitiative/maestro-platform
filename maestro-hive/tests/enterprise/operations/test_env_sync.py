#!/usr/bin/env python3
"""
Tests for Environment Synchronization Service.

EPIC: MD-2790 - [Ops] Environment Synchronization
Tests SchemaSyncManager, GitSyncManager, DataSyncManager, and EnvironmentSyncService.
"""

import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import subprocess

# Import modules under test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from maestro_hive.enterprise.operations.sync import (
    EnvironmentSyncService,
    SchemaSyncManager,
    SchemaSyncResult,
    GitSyncManager,
    GitSyncResult,
    DataSyncManager,
    DataSyncResult,
    TableSyncConfig,
)
from maestro_hive.enterprise.operations.sync.schema_sync import (
    SchemaSyncStatus,
    EnvironmentDBConfig,
)
from maestro_hive.enterprise.operations.sync.git_sync import (
    GitSyncStatus,
    VersionInfo,
    EnvironmentGitConfig,
)
from maestro_hive.enterprise.operations.sync.data_sync import (
    DataSyncStatus,
    SyncMode,
)


# ==================== SchemaSyncManager Tests ====================

class TestSchemaSyncManager:
    """Tests for SchemaSyncManager."""

    @pytest.fixture
    def schema_manager(self):
        """Create schema sync manager with test configs."""
        return SchemaSyncManager(
            project_root=Path("/tmp/test_project"),
            configs={
                "test_source": EnvironmentDBConfig(
                    host="localhost",
                    port=5432,
                    database="test_db",
                    username="test_user"
                ),
                "test_target": EnvironmentDBConfig(
                    host="localhost",
                    port=5433,
                    database="test_db",
                    username="test_user"
                )
            }
        )

    def test_default_configs_exist(self, schema_manager):
        """Test that default configs are available."""
        manager = SchemaSyncManager()
        assert "sandbox" in manager.configs
        assert "demo" in manager.configs
        assert "dev" in manager.configs
        assert "production" in manager.configs

    def test_get_schema_version_unknown_env(self, schema_manager):
        """Test get_schema_version raises for unknown environment."""
        with pytest.raises(ValueError, match="Unknown environment"):
            schema_manager.get_schema_version("nonexistent")

    def test_compare_schemas(self, schema_manager):
        """Test schema comparison returns expected structure."""
        with patch.object(schema_manager, "get_schema_version") as mock_version:
            mock_version.return_value = "20240101_initial"

            result = schema_manager.compare_schemas("test_source", "test_target")

            assert "source_environment" in result
            assert "target_environment" in result
            assert "schemas_match" in result
            assert result["schemas_match"] is True

    @pytest.mark.asyncio
    async def test_run_migrate_deploy_dry_run(self, schema_manager):
        """Test migrate deploy in dry run mode."""
        result = await schema_manager.run_migrate_deploy("test_source", dry_run=True)

        assert result["status"] == "dry_run"
        assert result["environment"] == "test_source"
        assert "command" in result

    def test_verify_demo_user_unknown_env(self, schema_manager):
        """Test verify_demo_user raises for unknown environment."""
        with pytest.raises(ValueError, match="Unknown environment"):
            schema_manager.verify_demo_user_exists("nonexistent")

    def test_count_ai_agents_unknown_env(self, schema_manager):
        """Test count_ai_agents raises for unknown environment."""
        with pytest.raises(ValueError, match="Unknown environment"):
            schema_manager.count_ai_agents("nonexistent")


# ==================== GitSyncManager Tests ====================

class TestGitSyncManager:
    """Tests for GitSyncManager."""

    @pytest.fixture
    def git_manager(self):
        """Create git sync manager with test configs."""
        return GitSyncManager(
            configs={
                "test_source": EnvironmentGitConfig(
                    path=Path("/tmp/test_repo_source"),
                    remote_url="git@github.com:test/repo.git",
                    branch="main"
                ),
                "test_target": EnvironmentGitConfig(
                    path=Path("/tmp/test_repo_target"),
                    remote_url="git@github.com:test/repo.git",
                    branch="main"
                )
            }
        )

    def test_default_configs_exist(self, git_manager):
        """Test that default configs are available."""
        manager = GitSyncManager()
        assert "sandbox" in manager.configs
        assert "demo" in manager.configs
        assert "dev" in manager.configs

    def test_get_current_commit_unknown_env(self, git_manager):
        """Test get_current_commit raises for unknown environment."""
        with pytest.raises(ValueError, match="Unknown environment"):
            git_manager.get_current_commit("nonexistent")

    def test_has_git_directory_unknown_env(self, git_manager):
        """Test has_git_directory raises for unknown environment."""
        with pytest.raises(ValueError, match="Unknown environment"):
            git_manager.has_git_directory("nonexistent")

    def test_compare_environments(self, git_manager):
        """Test environment comparison returns expected structure."""
        with patch.object(git_manager, "get_current_commit") as mock_commit:
            with patch.object(git_manager, "get_remote_url") as mock_remote:
                with patch.object(git_manager, "has_git_directory") as mock_git:
                    mock_commit.return_value = "abc12345"
                    mock_remote.return_value = "git@github.com:test/repo.git"
                    mock_git.return_value = True

                    result = git_manager.compare_environments(
                        "test_source",
                        ["test_target"]
                    )

                    assert "source_environment" in result
                    assert "targets" in result
                    assert "all_match" in result

    def test_create_version_json(self, git_manager):
        """Test VERSION.json creation."""
        with patch.object(git_manager, "get_current_commit") as mock_commit:
            with patch.object(git_manager, "get_current_branch") as mock_branch:
                mock_commit.return_value = "abc12345678"
                mock_branch.return_value = "main"

                version_info = git_manager.create_version_json("test_source")

                assert version_info.commit == "abc12345"
                assert version_info.branch == "main"
                assert version_info.environment == "test_source"

    def test_generate_deployment_script(self, git_manager):
        """Test deployment script generation."""
        script = git_manager.generate_deployment_script("test_source")

        assert "#!/bin/bash" in script
        assert "git pull" in script
        assert "VERSION.json" in script
        assert "prisma migrate deploy" in script

    def test_generate_deployment_script_unknown_env(self, git_manager):
        """Test generate_deployment_script raises for unknown environment."""
        with pytest.raises(ValueError, match="Unknown environment"):
            git_manager.generate_deployment_script("nonexistent")


# ==================== DataSyncManager Tests ====================

class TestDataSyncManager:
    """Tests for DataSyncManager."""

    @pytest.fixture
    def data_manager(self):
        """Create data sync manager with test configs."""
        from maestro_hive.enterprise.operations.sync.data_sync import EnvironmentDBConfig as DataDBConfig
        return DataSyncManager(
            configs={
                "test_source": DataDBConfig(
                    host="localhost",
                    port=5432,
                    database="test_db",
                    username="test_user"
                ),
                "test_target": DataDBConfig(
                    host="localhost",
                    port=5433,
                    database="test_db",
                    username="test_user"
                )
            },
            export_dir=Path("/tmp/test_exports")
        )

    def test_default_configs_exist(self, data_manager):
        """Test that default configs are available."""
        manager = DataSyncManager()
        assert "production" in manager.configs
        assert "sandbox" in manager.configs
        assert "demo" in manager.configs

    def test_default_tables_exist(self, data_manager):
        """Test that default tables config exists."""
        manager = DataSyncManager()
        assert len(manager.DEFAULT_TABLES) > 0
        table_names = [t.table_name for t in manager.DEFAULT_TABLES]
        assert "users" in table_names
        assert "ai_agents" in table_names

    def test_get_table_count_unknown_env(self, data_manager):
        """Test get_table_count raises for unknown environment."""
        with pytest.raises(ValueError, match="Unknown environment"):
            data_manager.get_table_count("nonexistent", "users")

    def test_compare_table_counts(self, data_manager):
        """Test table count comparison returns expected structure."""
        with patch.object(data_manager, "get_table_count") as mock_count:
            mock_count.return_value = 10

            result = data_manager.compare_table_counts(
                "test_source",
                "test_target",
                ["users", "ai_agents"]
            )

            assert "source_environment" in result
            assert "target_environment" in result
            assert "tables" in result
            assert "total_difference" in result

    def test_table_sync_config_defaults(self):
        """Test TableSyncConfig has correct defaults."""
        config = TableSyncConfig(table_name="test_table")

        assert config.primary_key == "id"
        assert config.sync_mode == SyncMode.UPSERT
        assert config.exclude_columns == []
        assert config.where_clause is None

    def test_generate_comparison_report(self, data_manager):
        """Test comparison report generation."""
        with patch.object(data_manager, "compare_table_counts") as mock_compare:
            mock_compare.return_value = {
                "tables": {
                    "users": {"matches": True, "difference": 0},
                    "ai_agents": {"matches": False, "difference": 5}
                },
                "total_difference": 5,
                "all_match": False
            }

            report = data_manager.generate_comparison_report(
                "test_source",
                "test_target"
            )

            assert "title" in report
            assert "epic" in report
            assert report["epic"] == "MD-2790"
            assert "recommendations" in report


# ==================== EnvironmentSyncService Tests ====================

class TestEnvironmentSyncService:
    """Tests for EnvironmentSyncService."""

    @pytest.fixture
    def sync_service(self):
        """Create sync service with mocked managers."""
        schema_manager = Mock(spec=SchemaSyncManager)
        git_manager = Mock(spec=GitSyncManager)
        data_manager = Mock(spec=DataSyncManager)

        return EnvironmentSyncService(
            schema_manager=schema_manager,
            git_manager=git_manager,
            data_manager=data_manager
        )

    def test_supported_environments(self, sync_service):
        """Test supported environments list."""
        assert "sandbox" in sync_service.SUPPORTED_ENVIRONMENTS
        assert "demo" in sync_service.SUPPORTED_ENVIRONMENTS
        assert "dev" in sync_service.SUPPORTED_ENVIRONMENTS
        assert "production" in sync_service.SUPPORTED_ENVIRONMENTS

    def test_validate_environments_valid(self, sync_service):
        """Test environment validation with valid environments."""
        errors = sync_service.validate_environments(["sandbox", "demo"])
        assert errors == []

    def test_validate_environments_invalid(self, sync_service):
        """Test environment validation with invalid environments."""
        errors = sync_service.validate_environments(["sandbox", "invalid"])
        assert len(errors) == 1
        assert "invalid" in errors[0]

    def test_get_environment_status(self, sync_service):
        """Test environment status retrieval."""
        sync_service.git_manager.has_git_directory.return_value = True
        sync_service.git_manager.get_short_commit.return_value = "abc12345"
        sync_service.git_manager.get_current_branch.return_value = "main"
        sync_service.git_manager.get_remote_url.return_value = "git@github.com:test/repo.git"
        sync_service.schema_manager.get_schema_version.return_value = "20240101"
        sync_service.data_manager.get_table_count.return_value = 10

        status = sync_service.get_environment_status("sandbox")

        assert "environment" in status
        assert "git" in status
        assert "schema" in status
        assert status["environment"] == "sandbox"

    @pytest.mark.asyncio
    async def test_sync_full_invalid_environment(self, sync_service):
        """Test full sync with invalid environment."""
        result = await sync_service.sync_full(
            source="invalid_env",
            targets=["demo"]
        )

        assert result.status.value == "failed"
        assert len(result.errors) > 0

    def test_compare_environments(self, sync_service):
        """Test environment comparison."""
        sync_service.git_manager.has_git_directory.return_value = True
        sync_service.git_manager.get_short_commit.return_value = "abc12345"
        sync_service.git_manager.get_current_branch.return_value = "main"
        sync_service.git_manager.get_remote_url.return_value = "git@github.com:test/repo.git"
        sync_service.schema_manager.get_schema_version.return_value = "20240101"
        sync_service.data_manager.get_table_count.return_value = 10

        result = sync_service.compare_environments("sandbox", ["demo"])

        assert "source_environment" in result
        assert "targets" in result

    def test_generate_sync_report(self, sync_service):
        """Test sync report generation."""
        sync_service.git_manager.has_git_directory.return_value = True
        sync_service.git_manager.get_short_commit.return_value = "abc12345"
        sync_service.git_manager.get_current_branch.return_value = "main"
        sync_service.git_manager.get_remote_url.return_value = "git@github.com:test/repo.git"
        sync_service.schema_manager.get_schema_version.return_value = "20240101"
        sync_service.data_manager.get_table_count.return_value = 10
        sync_service.data_manager.compare_table_counts.return_value = {
            "all_match": True,
            "tables": {}
        }

        report = sync_service.generate_sync_report("sandbox", ["demo"])

        assert "title" in report
        assert "epic" in report
        assert report["epic"] == "MD-2790"
        assert "recommendations" in report


# ==================== Result Dataclass Tests ====================

class TestResultDataclasses:
    """Tests for result dataclasses."""

    def test_schema_sync_result_to_dict(self):
        """Test SchemaSyncResult.to_dict()."""
        result = SchemaSyncResult(
            sync_id="test-123",
            source_env="sandbox",
            target_env="demo",
            status=SchemaSyncStatus.COMPLETED,
            started_at=datetime(2024, 1, 1, 12, 0, 0),
            completed_at=datetime(2024, 1, 1, 12, 5, 0),
            migrations_applied=3
        )

        d = result.to_dict()

        assert d["sync_id"] == "test-123"
        assert d["status"] == "completed"
        assert d["migrations_applied"] == 3

    def test_git_sync_result_to_dict(self):
        """Test GitSyncResult.to_dict()."""
        result = GitSyncResult(
            sync_id="test-456",
            target_env="demo",
            status=GitSyncStatus.COMPLETED,
            started_at=datetime(2024, 1, 1, 12, 0, 0),
            current_commit="abc12345"
        )

        d = result.to_dict()

        assert d["sync_id"] == "test-456"
        assert d["status"] == "completed"
        assert d["current_commit"] == "abc12345"

    def test_data_sync_result_to_dict(self):
        """Test DataSyncResult.to_dict()."""
        result = DataSyncResult(
            sync_id="test-789",
            source_env="production",
            target_env="sandbox",
            status=DataSyncStatus.COMPLETED,
            started_at=datetime(2024, 1, 1, 12, 0, 0),
            tables_synced=["users", "ai_agents"],
            records_inserted=50
        )

        d = result.to_dict()

        assert d["sync_id"] == "test-789"
        assert d["status"] == "completed"
        assert d["records_inserted"] == 50
        assert "users" in d["tables_synced"]

    def test_version_info_to_dict(self):
        """Test VersionInfo.to_dict()."""
        info = VersionInfo(
            version="1.0.0",
            commit="abc12345",
            branch="main",
            build_time="2024-01-01T12:00:00",
            environment="sandbox"
        )

        d = info.to_dict()

        assert d["version"] == "1.0.0"
        assert d["commit"] == "abc12345"
        assert d["environment"] == "sandbox"


# ==================== Integration Tests ====================

class TestIntegration:
    """Integration tests for the sync service."""

    def test_full_service_initialization(self):
        """Test service initializes with all managers."""
        service = EnvironmentSyncService()

        assert service.schema_manager is not None
        assert service.git_manager is not None
        assert service.data_manager is not None

    def test_verify_acceptance_criteria_structure(self):
        """Test AC verification returns expected structure."""
        service = EnvironmentSyncService()

        # Mock all the methods that interact with external systems
        with patch.object(service.schema_manager, "get_schema_version") as mock_schema:
            with patch.object(service.schema_manager, "verify_demo_user_exists") as mock_user:
                with patch.object(service.schema_manager, "count_ai_agents") as mock_agents:
                    with patch.object(service.schema_manager, "count_teams") as mock_teams:
                        with patch.object(service.git_manager, "has_git_directory") as mock_git:
                            with patch.object(service.git_manager, "get_short_commit") as mock_commit:
                                mock_schema.return_value = "v1"
                                mock_user.return_value = {"exists": True}
                                mock_agents.return_value = {"count": 10}
                                mock_teams.return_value = {"count": 5}
                                mock_git.return_value = True
                                mock_commit.return_value = "abc123"

                                result = service.verify_acceptance_criteria(
                                    environments=["sandbox", "demo"]
                                )

                                assert "epic" in result
                                assert result["epic"] == "MD-2790"
                                assert "acceptance_criteria" in result
                                assert "summary" in result
                                assert "AC-1" in result["acceptance_criteria"]
                                assert "AC-2" in result["acceptance_criteria"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
