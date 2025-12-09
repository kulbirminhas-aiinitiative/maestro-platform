"""Tests for admin configuration module."""

import os
import pytest
from datetime import datetime

from maestro_hive.enterprise.admin.config import (
    AdminConfig,
    AdminOperation,
    OperationType,
)


class TestOperationType:
    """Tests for OperationType enum."""

    def test_operation_types_exist(self):
        """Test all operation types are defined."""
        assert OperationType.REPOSITORY_MIGRATE.value == "repository_migrate"
        assert OperationType.REPOSITORY_CLONE.value == "repository_clone"
        assert OperationType.REPOSITORY_ARCHIVE.value == "repository_archive"
        assert OperationType.REPOSITORY_AUDIT.value == "repository_audit"
        assert OperationType.STORAGE_CLEANUP.value == "storage_cleanup"
        assert OperationType.SUBSCRIPTION_CANCEL.value == "subscription_cancel"
        assert OperationType.RESOURCE_LIST.value == "resource_list"


class TestAdminOperation:
    """Tests for AdminOperation dataclass."""

    def test_create_operation(self):
        """Test creating an admin operation."""
        operation = AdminOperation(
            operation_id="test-123",
            operation_type=OperationType.STORAGE_CLEANUP,
            initiated_by="test_user",
            initiated_at=datetime.utcnow(),
            parameters={"path": "/tmp/test"},
            dry_run=True,
        )

        assert operation.operation_id == "test-123"
        assert operation.operation_type == OperationType.STORAGE_CLEANUP
        assert operation.initiated_by == "test_user"
        assert operation.dry_run is True
        assert operation.status == "pending"

    def test_to_audit_record(self):
        """Test converting operation to audit record."""
        now = datetime.utcnow()
        operation = AdminOperation(
            operation_id="test-123",
            operation_type=OperationType.STORAGE_CLEANUP,
            initiated_by="test_user",
            initiated_at=now,
            parameters={"path": "/tmp/test"},
            dry_run=True,
            status="completed",
        )

        record = operation.to_audit_record()

        assert record["operation_id"] == "test-123"
        assert record["type"] == "storage_cleanup"
        assert record["initiated_by"] == "test_user"
        assert record["dry_run"] is True
        assert record["status"] == "completed"


class TestAdminConfig:
    """Tests for AdminConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = AdminConfig()

        assert config.default_org == "fifth-9"
        assert config.retention_days == 30
        assert config.dry_run is True  # Safe default
        assert config.batch_size == 100
        assert config.timeout_seconds == 300
        assert config.verify_after is True
        assert config.keep_source is True

    def test_dry_run_default_true(self):
        """Test that dry_run defaults to True for safety."""
        config = AdminConfig()
        assert config.dry_run is True

    def test_config_validation_retention_days(self):
        """Test validation of retention_days."""
        with pytest.raises(ValueError, match="retention_days must be at least 1"):
            AdminConfig(retention_days=0)

    def test_config_validation_batch_size(self):
        """Test validation of batch_size."""
        with pytest.raises(ValueError, match="batch_size must be at least 1"):
            AdminConfig(batch_size=0)

    def test_config_validation_timeout(self):
        """Test validation of timeout_seconds."""
        with pytest.raises(ValueError, match="timeout_seconds must be at least 10"):
            AdminConfig(timeout_seconds=5)

    def test_from_dict(self):
        """Test creating config from dictionary."""
        data = {
            "default_org": "test-org",
            "retention_days": 60,
            "dry_run": False,
            "batch_size": 50,
        }

        config = AdminConfig.from_dict(data)

        assert config.default_org == "test-org"
        assert config.retention_days == 60
        assert config.dry_run is False
        assert config.batch_size == 50

    def test_to_dict_excludes_token(self):
        """Test that to_dict excludes sensitive data."""
        config = AdminConfig(github_token="secret-token")

        data = config.to_dict()

        assert "github_token" not in data
        assert data["has_github_token"] is True

    def test_validate_github_access_with_token(self):
        """Test GitHub access validation with token."""
        config = AdminConfig(github_token="ghp_test123")
        assert config.validate_github_access() is True

    def test_validate_github_access_without_token(self):
        """Test GitHub access validation without token."""
        config = AdminConfig(github_token=None)
        assert config.validate_github_access() is False

    def test_validate_github_access_empty_token(self):
        """Test GitHub access validation with empty token."""
        config = AdminConfig(github_token="")
        assert config.validate_github_access() is False

    def test_cleanup_paths_default(self):
        """Test default cleanup paths."""
        config = AdminConfig()
        assert "/var/log/maestro" in config.cleanup_paths
        assert "/tmp/maestro-*" in config.cleanup_paths

    def test_exclude_patterns_default(self):
        """Test default exclude patterns."""
        config = AdminConfig()
        assert "*.keep" in config.exclude_patterns
        assert "current" in config.exclude_patterns
