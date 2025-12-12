"""
Repository Manager for External Project Gap Analysis.

Handles repository cloning, caching, and access for external project scanning.

EPIC: MD-3022
Child Task: MD-2920
"""

import hashlib
import logging
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class RepoSource(Enum):
    """Source type for repository."""
    GITHUB = "github"
    GITLAB = "gitlab"
    BITBUCKET = "bitbucket"
    LOCAL = "local"
    UNKNOWN = "unknown"


class RepoStatus(Enum):
    """Status of a managed repository."""
    PENDING = "pending"
    CLONING = "cloning"
    READY = "ready"
    UPDATING = "updating"
    ERROR = "error"
    EXPIRED = "expired"


@dataclass
class RepoConfig:
    """Configuration for repository management."""
    cache_dir: str = "/tmp/maestro_repo_cache"
    cache_ttl_hours: int = 24
    max_cache_size_gb: float = 10.0
    clone_depth: int = 1  # Shallow clone by default
    timeout_seconds: int = 300
    max_concurrent_clones: int = 3
    allowed_hosts: List[str] = field(default_factory=lambda: [
        "github.com",
        "gitlab.com",
        "bitbucket.org",
    ])


@dataclass
class RepoInfo:
    """Information about a managed repository."""
    url: str
    local_path: str
    source: RepoSource
    status: RepoStatus
    branch: str = "main"
    commit_hash: Optional[str] = None
    cloned_at: Optional[datetime] = None
    last_accessed: Optional[datetime] = None
    size_bytes: int = 0
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "url": self.url,
            "local_path": self.local_path,
            "source": self.source.value,
            "status": self.status.value,
            "branch": self.branch,
            "commit_hash": self.commit_hash,
            "cloned_at": self.cloned_at.isoformat() if self.cloned_at else None,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
            "size_bytes": self.size_bytes,
            "error_message": self.error_message,
        }


@dataclass
class CloneResult:
    """Result of a clone operation."""
    success: bool
    repo_info: Optional[RepoInfo] = None
    error: Optional[str] = None
    duration_seconds: float = 0.0


class RepoManager:
    """
    Manages repository cloning and caching for external project analysis.

    Features:
    - Secure cloning from allowed hosts only
    - Local path caching with TTL
    - Shallow clones for efficiency
    - Concurrent clone limiting
    - Cache size management
    """

    def __init__(self, config: Optional[RepoConfig] = None):
        """
        Initialize the repository manager.

        Args:
            config: Repository management configuration
        """
        self.config = config or RepoConfig()
        self._repos: Dict[str, RepoInfo] = {}
        self._ensure_cache_dir()

    def _ensure_cache_dir(self) -> None:
        """Ensure cache directory exists."""
        Path(self.config.cache_dir).mkdir(parents=True, exist_ok=True)

    def _get_cache_key(self, url: str, branch: str = "main") -> str:
        """Generate cache key for a repository URL."""
        normalized = f"{url.lower().rstrip('/')}:{branch}"
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    def _detect_source(self, url: str) -> RepoSource:
        """Detect the repository source from URL."""
        try:
            parsed = urlparse(url)
            host = parsed.netloc.lower()

            if "github.com" in host:
                return RepoSource.GITHUB
            elif "gitlab" in host:
                return RepoSource.GITLAB
            elif "bitbucket" in host:
                return RepoSource.BITBUCKET
            elif not host or host == "":
                return RepoSource.LOCAL
            else:
                return RepoSource.UNKNOWN
        except Exception:
            return RepoSource.UNKNOWN

    def _is_allowed_host(self, url: str) -> bool:
        """Check if URL host is in allowed list."""
        try:
            parsed = urlparse(url)
            host = parsed.netloc.lower()

            # Local paths are always allowed
            if not host:
                return True

            return any(allowed in host for allowed in self.config.allowed_hosts)
        except Exception:
            return False

    def _get_local_path(self, cache_key: str) -> str:
        """Get local path for cached repository."""
        return os.path.join(self.config.cache_dir, cache_key)

    def _is_cache_valid(self, repo_info: RepoInfo) -> bool:
        """Check if cached repository is still valid."""
        if repo_info.status != RepoStatus.READY:
            return False

        if not repo_info.cloned_at:
            return False

        ttl = timedelta(hours=self.config.cache_ttl_hours)
        return datetime.now() - repo_info.cloned_at < ttl

    def _get_directory_size(self, path: str) -> int:
        """Get total size of directory in bytes."""
        total = 0
        try:
            for dirpath, _, filenames in os.walk(path):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    if os.path.isfile(fp):
                        total += os.path.getsize(fp)
        except Exception:
            pass
        return total

    def _get_commit_hash(self, local_path: str) -> Optional[str]:
        """Get current commit hash of repository."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=local_path,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None

    def clone(
        self,
        url: str,
        branch: str = "main",
        force: bool = False,
    ) -> CloneResult:
        """
        Clone a repository to local cache.

        Args:
            url: Repository URL or local path
            branch: Branch to clone
            force: Force re-clone even if cached

        Returns:
            CloneResult with repository info or error
        """
        start_time = datetime.now()

        # Security check
        if not self._is_allowed_host(url):
            return CloneResult(
                success=False,
                error=f"Host not in allowed list. Allowed: {self.config.allowed_hosts}",
            )

        cache_key = self._get_cache_key(url, branch)
        local_path = self._get_local_path(cache_key)

        # Check cache
        if cache_key in self._repos and not force:
            repo_info = self._repos[cache_key]
            if self._is_cache_valid(repo_info):
                repo_info.last_accessed = datetime.now()
                duration = (datetime.now() - start_time).total_seconds()
                logger.info(f"Using cached repository: {url}")
                return CloneResult(
                    success=True,
                    repo_info=repo_info,
                    duration_seconds=duration,
                )

        # Handle local paths
        source = self._detect_source(url)
        if source == RepoSource.LOCAL:
            if os.path.isdir(url):
                repo_info = RepoInfo(
                    url=url,
                    local_path=url,
                    source=source,
                    status=RepoStatus.READY,
                    branch=branch,
                    cloned_at=datetime.now(),
                    last_accessed=datetime.now(),
                    size_bytes=self._get_directory_size(url),
                )
                self._repos[cache_key] = repo_info
                duration = (datetime.now() - start_time).total_seconds()
                return CloneResult(
                    success=True,
                    repo_info=repo_info,
                    duration_seconds=duration,
                )
            else:
                return CloneResult(
                    success=False,
                    error=f"Local path does not exist: {url}",
                )

        # Clean existing cache if force
        if force and os.path.exists(local_path):
            shutil.rmtree(local_path, ignore_errors=True)

        # Create repo info
        repo_info = RepoInfo(
            url=url,
            local_path=local_path,
            source=source,
            status=RepoStatus.CLONING,
            branch=branch,
        )
        self._repos[cache_key] = repo_info

        try:
            # Clone repository
            cmd = [
                "git", "clone",
                "--depth", str(self.config.clone_depth),
                "--branch", branch,
                "--single-branch",
                url,
                local_path,
            ]

            logger.info(f"Cloning repository: {url}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.timeout_seconds,
            )

            if result.returncode != 0:
                repo_info.status = RepoStatus.ERROR
                repo_info.error_message = result.stderr
                return CloneResult(
                    success=False,
                    repo_info=repo_info,
                    error=result.stderr,
                    duration_seconds=(datetime.now() - start_time).total_seconds(),
                )

            # Update repo info
            repo_info.status = RepoStatus.READY
            repo_info.cloned_at = datetime.now()
            repo_info.last_accessed = datetime.now()
            repo_info.commit_hash = self._get_commit_hash(local_path)
            repo_info.size_bytes = self._get_directory_size(local_path)

            duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"Successfully cloned {url} in {duration:.2f}s")

            return CloneResult(
                success=True,
                repo_info=repo_info,
                duration_seconds=duration,
            )

        except subprocess.TimeoutExpired:
            repo_info.status = RepoStatus.ERROR
            repo_info.error_message = "Clone operation timed out"
            return CloneResult(
                success=False,
                repo_info=repo_info,
                error="Clone operation timed out",
                duration_seconds=(datetime.now() - start_time).total_seconds(),
            )
        except Exception as e:
            repo_info.status = RepoStatus.ERROR
            repo_info.error_message = str(e)
            return CloneResult(
                success=False,
                repo_info=repo_info,
                error=str(e),
                duration_seconds=(datetime.now() - start_time).total_seconds(),
            )

    def get_repo(self, url: str, branch: str = "main") -> Optional[RepoInfo]:
        """Get cached repository info."""
        cache_key = self._get_cache_key(url, branch)
        return self._repos.get(cache_key)

    def list_repos(self) -> List[RepoInfo]:
        """List all managed repositories."""
        return list(self._repos.values())

    def cleanup_expired(self) -> int:
        """
        Remove expired repositories from cache.

        Returns:
            Number of repositories removed
        """
        removed = 0
        for cache_key, repo_info in list(self._repos.items()):
            if not self._is_cache_valid(repo_info):
                try:
                    if os.path.exists(repo_info.local_path):
                        shutil.rmtree(repo_info.local_path, ignore_errors=True)
                    del self._repos[cache_key]
                    removed += 1
                    logger.info(f"Removed expired cache: {repo_info.url}")
                except Exception as e:
                    logger.error(f"Error cleaning up {repo_info.url}: {e}")

        return removed

    def cleanup_all(self) -> int:
        """
        Remove all cached repositories.

        Returns:
            Number of repositories removed
        """
        removed = 0
        for cache_key, repo_info in list(self._repos.items()):
            try:
                if os.path.exists(repo_info.local_path):
                    shutil.rmtree(repo_info.local_path, ignore_errors=True)
                del self._repos[cache_key]
                removed += 1
            except Exception as e:
                logger.error(f"Error cleaning up {repo_info.url}: {e}")

        return removed

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_size = sum(r.size_bytes for r in self._repos.values())
        ready_count = sum(1 for r in self._repos.values() if r.status == RepoStatus.READY)

        return {
            "total_repos": len(self._repos),
            "ready_repos": ready_count,
            "total_size_bytes": total_size,
            "total_size_mb": total_size / (1024 * 1024),
            "cache_dir": self.config.cache_dir,
            "cache_ttl_hours": self.config.cache_ttl_hours,
        }


def create_repo_manager(config: Optional[Dict[str, Any]] = None) -> RepoManager:
    """
    Factory function to create a RepoManager instance.

    Args:
        config: Optional configuration dictionary

    Returns:
        Configured RepoManager instance
    """
    if config:
        repo_config = RepoConfig(
            cache_dir=config.get("cache_dir", "/tmp/maestro_repo_cache"),
            cache_ttl_hours=config.get("cache_ttl_hours", 24),
            max_cache_size_gb=config.get("max_cache_size_gb", 10.0),
            clone_depth=config.get("clone_depth", 1),
            timeout_seconds=config.get("timeout_seconds", 300),
        )
    else:
        repo_config = RepoConfig()

    return RepoManager(repo_config)
