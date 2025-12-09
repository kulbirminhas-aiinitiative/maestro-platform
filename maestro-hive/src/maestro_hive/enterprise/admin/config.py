"""
Admin Module Configuration.

Provides configuration management for administrative operations
with secure defaults and environment variable support.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
import os
import logging

logger = logging.getLogger(__name__)


class OperationType(Enum):
    """Types of administrative operations."""

    REPOSITORY_MIGRATE = "repository_migrate"
    REPOSITORY_CLONE = "repository_clone"
    REPOSITORY_ARCHIVE = "repository_archive"
    REPOSITORY_AUDIT = "repository_audit"
    STORAGE_CLEANUP = "storage_cleanup"
    SUBSCRIPTION_CANCEL = "subscription_cancel"
    RESOURCE_LIST = "resource_list"


@dataclass
class AdminOperation:
    """Record of an administrative operation for audit trail."""

    operation_id: str
    operation_type: OperationType
    initiated_by: str
    initiated_at: datetime
    parameters: Dict[str, Any]
    dry_run: bool = True
    status: str = "pending"
    result: Optional[Dict[str, Any]] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    def to_audit_record(self) -> Dict[str, Any]:
        """Convert to audit record format."""
        return {
            "operation_id": self.operation_id,
            "type": self.operation_type.value,
            "initiated_by": self.initiated_by,
            "initiated_at": self.initiated_at.isoformat(),
            "parameters": self.parameters,
            "dry_run": self.dry_run,
            "status": self.status,
            "result": self.result,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error_message,
        }


@dataclass
class AdminConfig:
    """Configuration for administrative operations.

    All destructive operations default to dry_run=True for safety.
    Credentials are loaded from environment variables.

    Attributes:
        github_token: GitHub API token (from GITHUB_TOKEN env var)
        default_org: Default GitHub organization
        retention_days: Days to retain files before cleanup
        dry_run: Whether to execute or simulate operations
        batch_size: Number of items to process per batch
        timeout_seconds: Operation timeout
        verify_after: Verify operations after completion
        keep_source: Keep source after migration
        log_level: Logging level for operations
        log_file: Path to operation log file
    """

    # GitHub Configuration
    github_token: Optional[str] = field(default_factory=lambda: os.getenv("GITHUB_TOKEN"))
    default_org: str = "fifth-9"
    github_api_url: str = "https://api.github.com"

    # Cleanup Configuration
    retention_days: int = 30
    dry_run: bool = True  # SAFE DEFAULT
    batch_size: int = 100

    # Migration Configuration
    verify_after: bool = True
    keep_source: bool = True
    timeout_seconds: int = 300

    # Logging Configuration
    log_level: str = "INFO"
    log_file: str = "/var/log/maestro/admin.log"

    # Cleanup Paths
    cleanup_paths: List[str] = field(default_factory=lambda: [
        "/var/log/maestro",
        "/tmp/maestro-*",
    ])

    # Exclude Patterns
    exclude_patterns: List[str] = field(default_factory=lambda: [
        "*.keep",
        "current",
        ".gitkeep",
    ])

    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.retention_days < 1:
            raise ValueError("retention_days must be at least 1")
        if self.batch_size < 1:
            raise ValueError("batch_size must be at least 1")
        if self.timeout_seconds < 10:
            raise ValueError("timeout_seconds must be at least 10")

        # Log warning if dry_run is disabled
        if not self.dry_run:
            logger.warning(
                "AdminConfig initialized with dry_run=False - "
                "destructive operations will be executed!"
            )

    @classmethod
    def from_env(cls) -> "AdminConfig":
        """Create configuration from environment variables."""
        return cls(
            github_token=os.getenv("GITHUB_TOKEN"),
            default_org=os.getenv("GITHUB_ORG", "fifth-9"),
            dry_run=os.getenv("ADMIN_DRY_RUN", "true").lower() == "true",
            retention_days=int(os.getenv("ADMIN_RETENTION_DAYS", "30")),
            batch_size=int(os.getenv("ADMIN_BATCH_SIZE", "100")),
            timeout_seconds=int(os.getenv("ADMIN_TIMEOUT", "300")),
            log_level=os.getenv("ADMIN_LOG_LEVEL", "INFO"),
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AdminConfig":
        """Create configuration from dictionary."""
        return cls(
            github_token=data.get("github_token") or os.getenv("GITHUB_TOKEN"),
            default_org=data.get("default_org", "fifth-9"),
            github_api_url=data.get("github_api_url", "https://api.github.com"),
            retention_days=data.get("retention_days", 30),
            dry_run=data.get("dry_run", True),
            batch_size=data.get("batch_size", 100),
            verify_after=data.get("verify_after", True),
            keep_source=data.get("keep_source", True),
            timeout_seconds=data.get("timeout_seconds", 300),
            log_level=data.get("log_level", "INFO"),
            log_file=data.get("log_file", "/var/log/maestro/admin.log"),
            cleanup_paths=data.get("cleanup_paths", ["/var/log/maestro", "/tmp/maestro-*"]),
            exclude_patterns=data.get("exclude_patterns", ["*.keep", "current"]),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary (excluding sensitive data)."""
        return {
            "default_org": self.default_org,
            "github_api_url": self.github_api_url,
            "retention_days": self.retention_days,
            "dry_run": self.dry_run,
            "batch_size": self.batch_size,
            "verify_after": self.verify_after,
            "keep_source": self.keep_source,
            "timeout_seconds": self.timeout_seconds,
            "log_level": self.log_level,
            "log_file": self.log_file,
            "cleanup_paths": self.cleanup_paths,
            "exclude_patterns": self.exclude_patterns,
            "has_github_token": self.github_token is not None,
        }

    def validate_github_access(self) -> bool:
        """Check if GitHub token is configured."""
        return self.github_token is not None and len(self.github_token) > 0
