"""
Release Manager Implementation.

Provides release workflow management with semantic versioning,
changelog generation, and rollback capabilities.
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ReleaseType(Enum):
    """Types of releases."""

    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"
    PRERELEASE = "prerelease"


class BumpType(Enum):
    """Version bump types."""

    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"


class ReleaseStatus(Enum):
    """Release status states."""

    DRAFT = "draft"
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DEPLOYED = "deployed"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


@dataclass
class Release:
    """Release information."""

    version: str
    release_type: ReleaseType
    changelog: str
    status: ReleaseStatus = ReleaseStatus.DRAFT
    tag: Optional[str] = None
    commit_sha: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    deployed_at: Optional[datetime] = None
    deployed_to: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert release to dictionary."""
        return {
            "version": self.version,
            "release_type": self.release_type.value,
            "changelog": self.changelog,
            "status": self.status.value,
            "tag": self.tag,
            "commit_sha": self.commit_sha,
            "created_at": self.created_at.isoformat(),
            "deployed_at": self.deployed_at.isoformat() if self.deployed_at else None,
            "deployed_to": self.deployed_to,
            "metadata": self.metadata,
        }


@dataclass
class RollbackResult:
    """Result of a rollback operation."""

    success: bool
    environment: str
    from_version: str
    to_version: str
    reason: str
    executed_at: datetime = field(default_factory=datetime.utcnow)
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "success": self.success,
            "environment": self.environment,
            "from_version": self.from_version,
            "to_version": self.to_version,
            "reason": self.reason,
            "executed_at": self.executed_at.isoformat(),
            "error_message": self.error_message,
        }


class ReleaseManager:
    """Release workflow and versioning management."""

    VERSION_PATTERN = re.compile(
        r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
        r"(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
        r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
        r"(?:\+(?P<buildmetadata>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
    )

    def __init__(
        self,
        version_prefix: str = "v",
        changelog_enabled: bool = True,
    ):
        """
        Initialize release manager.

        Args:
            version_prefix: Prefix for version tags (e.g., 'v')
            changelog_enabled: Whether to generate changelogs
        """
        self.version_prefix = version_prefix
        self.changelog_enabled = changelog_enabled
        self._releases: Dict[str, Release] = {}
        self._current_version: Optional[str] = None
        self._rollback_history: List[RollbackResult] = []

        logger.info("ReleaseManager initialized")

    def create_release(
        self,
        version: str,
        release_type: ReleaseType,
        changelog: str,
        commit_sha: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Release:
        """
        Create new release.

        Args:
            version: Semantic version string
            release_type: Type of release
            changelog: Changelog description
            commit_sha: Git commit SHA
            metadata: Additional metadata

        Returns:
            Created release

        Raises:
            ValueError: If version is invalid or already exists
        """
        # Validate version format
        if not self._validate_version(version):
            raise ValueError(f"Invalid version format: {version}")

        if version in self._releases:
            raise ValueError(f"Release {version} already exists")

        tag = f"{self.version_prefix}{version}"

        release = Release(
            version=version,
            release_type=release_type,
            changelog=changelog,
            tag=tag,
            commit_sha=commit_sha,
            metadata=metadata or {},
        )

        self._releases[version] = release
        self._current_version = version

        logger.info(f"Release created: {version} ({release_type.value})")
        return release

    def get_release(self, version: str) -> Optional[Release]:
        """
        Get release by version.

        Args:
            version: Version string

        Returns:
            Release or None if not found
        """
        return self._releases.get(version)

    def list_releases(self, status: Optional[ReleaseStatus] = None) -> List[Release]:
        """
        List releases, optionally filtered by status.

        Args:
            status: Optional status filter

        Returns:
            List of releases
        """
        releases = list(self._releases.values())
        if status:
            releases = [r for r in releases if r.status == status]
        return sorted(releases, key=lambda r: r.created_at, reverse=True)

    def get_current_version(self) -> Optional[str]:
        """
        Get current release version.

        Returns:
            Current version string or None
        """
        return self._current_version

    def set_current_version(self, version: str) -> None:
        """
        Set current version.

        Args:
            version: Version to set as current

        Raises:
            ValueError: If version doesn't exist
        """
        if version not in self._releases:
            raise ValueError(f"Release {version} not found")
        self._current_version = version
        logger.info(f"Current version set to: {version}")

    def bump_version(self, bump_type: BumpType) -> str:
        """
        Bump version based on type.

        Args:
            bump_type: Type of version bump

        Returns:
            New version string

        Raises:
            ValueError: If no current version set
        """
        if not self._current_version:
            raise ValueError("No current version set")

        match = self.VERSION_PATTERN.match(self._current_version)
        if not match:
            raise ValueError(f"Current version is invalid: {self._current_version}")

        major = int(match.group("major"))
        minor = int(match.group("minor"))
        patch = int(match.group("patch"))

        if bump_type == BumpType.MAJOR:
            major += 1
            minor = 0
            patch = 0
        elif bump_type == BumpType.MINOR:
            minor += 1
            patch = 0
        elif bump_type == BumpType.PATCH:
            patch += 1

        new_version = f"{major}.{minor}.{patch}"
        logger.info(f"Version bumped: {self._current_version} -> {new_version}")
        return new_version

    def update_release_status(
        self,
        version: str,
        status: ReleaseStatus,
        environment: Optional[str] = None,
    ) -> Release:
        """
        Update release status.

        Args:
            version: Version to update
            status: New status
            environment: Environment being deployed to

        Returns:
            Updated release

        Raises:
            ValueError: If release not found
        """
        release = self._releases.get(version)
        if not release:
            raise ValueError(f"Release {version} not found")

        release.status = status

        if status == ReleaseStatus.DEPLOYED and environment:
            release.deployed_at = datetime.utcnow()
            if environment not in release.deployed_to:
                release.deployed_to.append(environment)

        logger.info(f"Release {version} status updated to: {status.value}")
        return release

    def rollback(
        self,
        environment: str,
        target_version: str,
        reason: str,
    ) -> RollbackResult:
        """
        Rollback to previous version.

        Args:
            environment: Environment to rollback
            target_version: Version to rollback to
            reason: Reason for rollback

        Returns:
            Rollback result
        """
        current = self._current_version or "unknown"

        # Validate target version exists
        if target_version not in self._releases:
            result = RollbackResult(
                success=False,
                environment=environment,
                from_version=current,
                to_version=target_version,
                reason=reason,
                error_message=f"Target version {target_version} not found",
            )
            self._rollback_history.append(result)
            logger.error(f"Rollback failed: {result.error_message}")
            return result

        # Execute rollback
        target_release = self._releases[target_version]
        target_release.status = ReleaseStatus.DEPLOYED
        if environment not in target_release.deployed_to:
            target_release.deployed_to.append(environment)

        # Mark current as rolled back if it exists
        if current in self._releases:
            self._releases[current].status = ReleaseStatus.ROLLED_BACK

        self._current_version = target_version

        result = RollbackResult(
            success=True,
            environment=environment,
            from_version=current,
            to_version=target_version,
            reason=reason,
        )

        self._rollback_history.append(result)
        logger.info(f"Rollback executed: {current} -> {target_version} ({environment})")
        return result

    def get_rollback_history(self) -> List[RollbackResult]:
        """
        Get rollback history.

        Returns:
            List of rollback results
        """
        return self._rollback_history.copy()

    def _validate_version(self, version: str) -> bool:
        """Validate semantic version format."""
        return bool(self.VERSION_PATTERN.match(version))

    def generate_changelog(
        self,
        from_version: Optional[str] = None,
        to_version: Optional[str] = None,
    ) -> str:
        """
        Generate changelog between versions.

        Args:
            from_version: Starting version (exclusive)
            to_version: Ending version (inclusive)

        Returns:
            Generated changelog text
        """
        releases = self.list_releases()

        if to_version:
            releases = [r for r in releases if r.version == to_version]

        if not releases:
            return "No releases found."

        changelog_parts = ["# Changelog\n"]

        for release in releases:
            changelog_parts.append(
                f"\n## {self.version_prefix}{release.version} "
                f"({release.created_at.strftime('%Y-%m-%d')})\n"
            )
            changelog_parts.append(f"\n{release.changelog}\n")

        return "".join(changelog_parts)

    def to_dict(self) -> Dict[str, Any]:
        """Convert manager state to dictionary."""
        return {
            "current_version": self._current_version,
            "version_prefix": self.version_prefix,
            "releases": {v: r.to_dict() for v, r in self._releases.items()},
            "rollback_history": [r.to_dict() for r in self._rollback_history],
        }
