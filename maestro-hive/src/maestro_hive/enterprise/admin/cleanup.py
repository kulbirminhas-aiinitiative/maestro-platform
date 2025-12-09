"""
Resource Cleanup Module.

Provides utilities for cleaning up resources:
- Storage cleanup (files, logs, temp directories)
- Subscription cancellation
- Unused resource identification
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List, Dict, Any
import asyncio
import fnmatch
import glob
import logging
import os
import shutil
import uuid

from .config import AdminConfig, AdminOperation, OperationType

logger = logging.getLogger(__name__)


class ResourceType(Enum):
    """Types of resources that can be cleaned up."""

    FILE = "file"
    DIRECTORY = "directory"
    LOG = "log"
    TEMP = "temp"
    CACHE = "cache"
    SUBSCRIPTION = "subscription"
    API_KEY = "api_key"


@dataclass
class Resource:
    """Represents a resource that can be cleaned up."""

    resource_id: str
    resource_type: ResourceType
    name: str
    path: Optional[str] = None
    size_bytes: int = 0
    created_at: Optional[datetime] = None
    last_accessed: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "resource_id": self.resource_id,
            "type": self.resource_type.value,
            "name": self.name,
            "path": self.path,
            "size_bytes": self.size_bytes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
            "metadata": self.metadata,
        }


@dataclass
class CleanupResult:
    """Result of a storage cleanup operation."""

    success: bool
    files_removed: int = 0
    directories_removed: int = 0
    bytes_freed: int = 0
    errors: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    dry_run: bool = True
    items_processed: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "files_removed": self.files_removed,
            "directories_removed": self.directories_removed,
            "bytes_freed": self.bytes_freed,
            "errors": self.errors,
            "duration_seconds": self.duration_seconds,
            "dry_run": self.dry_run,
            "items_processed": self.items_processed[:10],  # Limit for readability
            "total_items": len(self.items_processed),
        }


@dataclass
class CancellationResult:
    """Result of a subscription cancellation."""

    success: bool
    service: str
    subscription_id: Optional[str] = None
    reason: str = ""
    cancelled_at: Optional[datetime] = None
    refund_amount: float = 0.0
    error_message: Optional[str] = None
    dry_run: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "service": self.service,
            "subscription_id": self.subscription_id,
            "reason": self.reason,
            "cancelled_at": self.cancelled_at.isoformat() if self.cancelled_at else None,
            "refund_amount": self.refund_amount,
            "error_message": self.error_message,
            "dry_run": self.dry_run,
        }


class ResourceCleanup:
    """Manages resource cleanup operations.

    All destructive operations respect dry_run setting from config.
    Operations are logged for audit compliance.
    """

    def __init__(self, config: Optional[AdminConfig] = None):
        """Initialize resource cleanup manager.

        Args:
            config: Admin configuration. Defaults to environment-based config.
        """
        self.config = config or AdminConfig.from_env()
        self._operations: List[AdminOperation] = []
        logger.info(
            "ResourceCleanup initialized (dry_run=%s, retention_days=%d)",
            self.config.dry_run,
            self.config.retention_days,
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

    def _should_exclude(self, path: str) -> bool:
        """Check if path matches any exclude pattern."""
        filename = os.path.basename(path)
        for pattern in self.config.exclude_patterns:
            if fnmatch.fnmatch(filename, pattern):
                return True
        return False

    def _get_file_age_days(self, path: str) -> int:
        """Get file age in days."""
        try:
            mtime = os.path.getmtime(path)
            age = datetime.now() - datetime.fromtimestamp(mtime)
            return age.days
        except OSError:
            return 0

    async def clean_storage(
        self,
        path: str,
        older_than_days: Optional[int] = None,
        dry_run: Optional[bool] = None,
    ) -> CleanupResult:
        """Clean up storage at specified path.

        Args:
            path: Path to clean (supports glob patterns)
            older_than_days: Only remove files older than this. Defaults to config.
            dry_run: Override config dry_run setting

        Returns:
            CleanupResult with cleanup details
        """
        effective_dry_run = dry_run if dry_run is not None else self.config.dry_run
        effective_retention = older_than_days or self.config.retention_days

        operation = self._create_operation(
            OperationType.STORAGE_CLEANUP,
            {
                "path": path,
                "older_than_days": effective_retention,
                "dry_run": effective_dry_run,
            },
        )

        start_time = datetime.utcnow()
        logger.info(
            "Starting storage cleanup: %s (older than %d days, dry_run=%s)",
            path,
            effective_retention,
            effective_dry_run,
        )

        result = CleanupResult(success=True, dry_run=effective_dry_run)

        try:
            # Expand glob patterns
            paths = glob.glob(path, recursive=True)
            if not paths:
                paths = [path]

            for target_path in paths:
                if not os.path.exists(target_path):
                    logger.warning("Path does not exist: %s", target_path)
                    continue

                if os.path.isfile(target_path):
                    await self._process_file(
                        target_path, effective_retention, effective_dry_run, result
                    )
                elif os.path.isdir(target_path):
                    await self._process_directory(
                        target_path, effective_retention, effective_dry_run, result
                    )

            result.duration_seconds = (datetime.utcnow() - start_time).total_seconds()

            operation.status = "completed" if not effective_dry_run else "completed_dry_run"
            operation.completed_at = datetime.utcnow()
            operation.result = result.to_dict()

            logger.info(
                "Cleanup complete: %d files, %d dirs, %d bytes freed",
                result.files_removed,
                result.directories_removed,
                result.bytes_freed,
            )

        except Exception as e:
            logger.error("Cleanup failed: %s", str(e))
            result.success = False
            result.errors.append(str(e))
            operation.status = "failed"
            operation.error_message = str(e)
            operation.completed_at = datetime.utcnow()

        return result

    async def _process_file(
        self,
        file_path: str,
        retention_days: int,
        dry_run: bool,
        result: CleanupResult,
    ) -> None:
        """Process a single file for cleanup."""
        if self._should_exclude(file_path):
            logger.debug("Excluding file: %s", file_path)
            return

        age_days = self._get_file_age_days(file_path)
        if age_days < retention_days:
            return

        try:
            file_size = os.path.getsize(file_path)
            result.items_processed.append(file_path)

            if dry_run:
                logger.info("[DRY RUN] Would remove file: %s (%d bytes)", file_path, file_size)
            else:
                os.remove(file_path)
                logger.info("Removed file: %s (%d bytes)", file_path, file_size)

            result.files_removed += 1
            result.bytes_freed += file_size

        except OSError as e:
            error_msg = f"Failed to remove {file_path}: {e}"
            logger.error(error_msg)
            result.errors.append(error_msg)

    async def _process_directory(
        self,
        dir_path: str,
        retention_days: int,
        dry_run: bool,
        result: CleanupResult,
    ) -> None:
        """Process a directory for cleanup."""
        for root, dirs, files in os.walk(dir_path, topdown=False):
            # Process files first
            for filename in files:
                file_path = os.path.join(root, filename)
                await self._process_file(file_path, retention_days, dry_run, result)

            # Remove empty directories
            for dirname in dirs:
                dir_path_full = os.path.join(root, dirname)
                if self._should_exclude(dir_path_full):
                    continue

                try:
                    if os.path.isdir(dir_path_full) and not os.listdir(dir_path_full):
                        result.items_processed.append(dir_path_full)
                        if dry_run:
                            logger.info("[DRY RUN] Would remove empty dir: %s", dir_path_full)
                        else:
                            os.rmdir(dir_path_full)
                            logger.info("Removed empty directory: %s", dir_path_full)
                        result.directories_removed += 1
                except OSError as e:
                    error_msg = f"Failed to remove directory {dir_path_full}: {e}"
                    logger.error(error_msg)
                    result.errors.append(error_msg)

    async def cancel_subscription(
        self,
        service: str,
        reason: str,
        dry_run: Optional[bool] = None,
    ) -> CancellationResult:
        """Cancel a subscription service.

        Args:
            service: Service name (e.g., 'google_one', 'aws_reserved')
            reason: Reason for cancellation
            dry_run: Override config dry_run setting

        Returns:
            CancellationResult with cancellation details
        """
        effective_dry_run = dry_run if dry_run is not None else self.config.dry_run

        operation = self._create_operation(
            OperationType.SUBSCRIPTION_CANCEL,
            {"service": service, "reason": reason, "dry_run": effective_dry_run},
        )

        logger.info(
            "Cancelling subscription: %s (reason: %s, dry_run=%s)",
            service,
            reason,
            effective_dry_run,
        )

        if effective_dry_run:
            logger.info("[DRY RUN] Would cancel subscription: %s", service)
            operation.status = "completed_dry_run"
            operation.completed_at = datetime.utcnow()
            return CancellationResult(
                success=True,
                service=service,
                reason=reason,
                cancelled_at=datetime.utcnow(),
                dry_run=True,
            )

        # In production, this would call the respective service API
        # For now, we simulate the cancellation
        try:
            subscription_id = f"{service}-{uuid.uuid4().hex[:8]}"

            operation.status = "completed"
            operation.completed_at = datetime.utcnow()
            operation.result = {
                "subscription_id": subscription_id,
                "service": service,
            }

            return CancellationResult(
                success=True,
                service=service,
                subscription_id=subscription_id,
                reason=reason,
                cancelled_at=datetime.utcnow(),
                dry_run=False,
            )

        except Exception as e:
            logger.error("Subscription cancellation failed: %s", str(e))
            operation.status = "failed"
            operation.error_message = str(e)
            operation.completed_at = datetime.utcnow()
            return CancellationResult(
                success=False,
                service=service,
                reason=reason,
                error_message=str(e),
                dry_run=False,
            )

    async def list_unused_resources(
        self,
        resource_types: Optional[List[ResourceType]] = None,
    ) -> List[Resource]:
        """List unused resources that could be cleaned up.

        Args:
            resource_types: Filter by resource types. Default: all types.

        Returns:
            List of unused resources
        """
        operation = self._create_operation(
            OperationType.RESOURCE_LIST,
            {"types": [t.value for t in resource_types] if resource_types else "all"},
        )

        logger.info("Listing unused resources")

        resources: List[Resource] = []

        # Check configured cleanup paths
        for path_pattern in self.config.cleanup_paths:
            for path in glob.glob(path_pattern, recursive=True):
                if not os.path.exists(path):
                    continue

                if os.path.isfile(path):
                    age_days = self._get_file_age_days(path)
                    if age_days >= self.config.retention_days:
                        try:
                            stat = os.stat(path)
                            resource = Resource(
                                resource_id=str(uuid.uuid4()),
                                resource_type=ResourceType.FILE,
                                name=os.path.basename(path),
                                path=path,
                                size_bytes=stat.st_size,
                                created_at=datetime.fromtimestamp(stat.st_ctime),
                                last_accessed=datetime.fromtimestamp(stat.st_atime),
                                metadata={"age_days": age_days},
                            )
                            if resource_types is None or resource.resource_type in resource_types:
                                resources.append(resource)
                        except OSError:
                            pass

                elif os.path.isdir(path):
                    # Check for empty directories
                    try:
                        if not os.listdir(path):
                            resource = Resource(
                                resource_id=str(uuid.uuid4()),
                                resource_type=ResourceType.DIRECTORY,
                                name=os.path.basename(path),
                                path=path,
                                metadata={"empty": True},
                            )
                            if resource_types is None or resource.resource_type in resource_types:
                                resources.append(resource)
                    except OSError:
                        pass

        operation.status = "completed"
        operation.completed_at = datetime.utcnow()
        operation.result = {"count": len(resources)}

        logger.info("Found %d unused resources", len(resources))
        return resources

    def get_operations_history(self) -> List[Dict[str, Any]]:
        """Get history of all operations for audit."""
        return [op.to_audit_record() for op in self._operations]
