"""Tests for resource cleanup module."""

import os
import tempfile
import pytest
from datetime import datetime, timedelta

from maestro_hive.enterprise.admin.config import AdminConfig
from maestro_hive.enterprise.admin.cleanup import (
    ResourceCleanup,
    CleanupResult,
    CancellationResult,
    Resource,
    ResourceType,
)


class TestResourceType:
    """Tests for ResourceType enum."""

    def test_resource_types_exist(self):
        """Test all resource types are defined."""
        assert ResourceType.FILE.value == "file"
        assert ResourceType.DIRECTORY.value == "directory"
        assert ResourceType.LOG.value == "log"
        assert ResourceType.TEMP.value == "temp"
        assert ResourceType.CACHE.value == "cache"
        assert ResourceType.SUBSCRIPTION.value == "subscription"


class TestResource:
    """Tests for Resource dataclass."""

    def test_create_resource(self):
        """Test creating a resource."""
        resource = Resource(
            resource_id="res-123",
            resource_type=ResourceType.FILE,
            name="test.log",
            path="/var/log/test.log",
            size_bytes=1024,
        )

        assert resource.resource_id == "res-123"
        assert resource.resource_type == ResourceType.FILE
        assert resource.name == "test.log"
        assert resource.size_bytes == 1024

    def test_resource_to_dict(self):
        """Test converting resource to dict."""
        resource = Resource(
            resource_id="res-123",
            resource_type=ResourceType.FILE,
            name="test.log",
            path="/var/log/test.log",
        )

        data = resource.to_dict()

        assert data["resource_id"] == "res-123"
        assert data["type"] == "file"
        assert data["name"] == "test.log"


class TestCleanupResult:
    """Tests for CleanupResult dataclass."""

    def test_create_cleanup_result(self):
        """Test creating a cleanup result."""
        result = CleanupResult(
            success=True,
            files_removed=10,
            directories_removed=2,
            bytes_freed=102400,
            dry_run=True,
        )

        assert result.success is True
        assert result.files_removed == 10
        assert result.directories_removed == 2
        assert result.bytes_freed == 102400

    def test_cleanup_result_to_dict(self):
        """Test converting cleanup result to dict."""
        result = CleanupResult(
            success=True,
            files_removed=10,
            bytes_freed=102400,
            items_processed=["file1", "file2"],
            dry_run=True,
        )

        data = result.to_dict()

        assert data["success"] is True
        assert data["files_removed"] == 10
        assert data["total_items"] == 2


class TestCancellationResult:
    """Tests for CancellationResult dataclass."""

    def test_create_cancellation_result(self):
        """Test creating a cancellation result."""
        result = CancellationResult(
            success=True,
            service="google_one",
            reason="Cost optimization",
            dry_run=True,
        )

        assert result.success is True
        assert result.service == "google_one"
        assert result.reason == "Cost optimization"

    def test_cancellation_result_to_dict(self):
        """Test converting cancellation result to dict."""
        result = CancellationResult(
            success=True,
            service="aws_reserved",
            subscription_id="sub-123",
            cancelled_at=datetime.utcnow(),
            dry_run=False,
        )

        data = result.to_dict()

        assert data["success"] is True
        assert data["service"] == "aws_reserved"
        assert data["subscription_id"] == "sub-123"


class TestResourceCleanup:
    """Tests for ResourceCleanup class."""

    def test_init_default_config(self):
        """Test initialization with default config."""
        cleanup = ResourceCleanup()
        assert cleanup.config.dry_run is True
        assert cleanup.config.retention_days == 30

    def test_init_custom_config(self):
        """Test initialization with custom config."""
        config = AdminConfig(
            retention_days=60,
            dry_run=True,
        )
        cleanup = ResourceCleanup(config)
        assert cleanup.config.retention_days == 60

    @pytest.mark.asyncio
    async def test_clean_storage_dry_run(self):
        """Test storage cleanup in dry run mode."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a test file
            test_file = os.path.join(temp_dir, "test.log")
            with open(test_file, "w") as f:
                f.write("test content")

            # Set file modification time to old
            old_time = (datetime.now() - timedelta(days=60)).timestamp()
            os.utime(test_file, (old_time, old_time))

            config = AdminConfig(
                dry_run=True,
                retention_days=30,
            )
            cleanup = ResourceCleanup(config)

            result = await cleanup.clean_storage(temp_dir)

            assert result.success is True
            assert result.dry_run is True
            # File should still exist in dry run
            assert os.path.exists(test_file)

    @pytest.mark.asyncio
    async def test_clean_storage_exclude_patterns(self):
        """Test storage cleanup respects exclude patterns."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create files
            keep_file = os.path.join(temp_dir, "important.keep")
            with open(keep_file, "w") as f:
                f.write("keep me")

            config = AdminConfig(
                dry_run=False,
                retention_days=1,  # Short retention
                exclude_patterns=["*.keep"],
            )
            cleanup = ResourceCleanup(config)

            result = await cleanup.clean_storage(temp_dir)

            # .keep file should be excluded
            assert os.path.exists(keep_file)

    @pytest.mark.asyncio
    async def test_cancel_subscription_dry_run(self):
        """Test subscription cancellation in dry run mode."""
        config = AdminConfig(dry_run=True)
        cleanup = ResourceCleanup(config)

        result = await cleanup.cancel_subscription(
            service="google_one",
            reason="Cost optimization",
        )

        assert result.success is True
        assert result.dry_run is True
        assert result.service == "google_one"
        assert result.reason == "Cost optimization"

    @pytest.mark.asyncio
    async def test_cancel_subscription_execute(self):
        """Test subscription cancellation execution."""
        config = AdminConfig(dry_run=False)
        cleanup = ResourceCleanup(config)

        result = await cleanup.cancel_subscription(
            service="aws_reserved",
            reason="No longer needed",
        )

        assert result.success is True
        assert result.dry_run is False
        assert result.subscription_id is not None

    @pytest.mark.asyncio
    async def test_list_unused_resources(self):
        """Test listing unused resources."""
        cleanup = ResourceCleanup()
        resources = await cleanup.list_unused_resources()

        assert isinstance(resources, list)

    @pytest.mark.asyncio
    async def test_list_unused_resources_filtered(self):
        """Test listing unused resources with type filter."""
        cleanup = ResourceCleanup()
        resources = await cleanup.list_unused_resources(
            resource_types=[ResourceType.FILE]
        )

        for resource in resources:
            assert resource.resource_type == ResourceType.FILE

    def test_get_operations_history(self):
        """Test getting operations history."""
        cleanup = ResourceCleanup()
        history = cleanup.get_operations_history()
        assert isinstance(history, list)
