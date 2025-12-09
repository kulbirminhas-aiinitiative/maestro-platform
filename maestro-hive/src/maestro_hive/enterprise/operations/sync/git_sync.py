"""
Git Synchronization Manager.

EPIC: MD-2790 - AC-5, AC-6, AC-7, AC-8
Handles git-based deployment synchronization across environments.
"""

import logging
import subprocess
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class GitSyncStatus(str, Enum):
    """Git sync operation status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class GitSyncResult:
    """Result of a git sync operation."""
    sync_id: str
    target_env: str
    status: GitSyncStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    previous_commit: Optional[str] = None
    current_commit: Optional[str] = None
    branch: str = "main"
    error: Optional[str] = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "sync_id": self.sync_id,
            "target_environment": self.target_env,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "previous_commit": self.previous_commit,
            "current_commit": self.current_commit,
            "branch": self.branch,
            "error": self.error,
            "details": self.details
        }


@dataclass
class VersionInfo:
    """Version information for an environment."""
    version: str
    commit: str
    branch: str
    build_time: str
    environment: str
    deployed_at: Optional[str] = None
    deployed_by: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for VERSION.json."""
        return {
            "version": self.version,
            "commit": self.commit,
            "branch": self.branch,
            "build_time": self.build_time,
            "environment": self.environment,
            "deployed_at": self.deployed_at,
            "deployed_by": self.deployed_by
        }


@dataclass
class EnvironmentGitConfig:
    """Git configuration for an environment."""
    path: Path
    remote_url: str
    branch: str = "main"
    deploy_key_path: Optional[Path] = None


class GitSyncManager:
    """
    Manages git-based deployment synchronization.

    Implements:
    - AC-5: Demo has .git directory with same remote as Sandbox
    - AC-6: All 3 environments show same commit via git rev-parse HEAD
    - AC-7: Deployment script uses git pull instead of rsync
    - AC-8: /api/health/version endpoint works identically on all environments
    """

    # Default environment paths
    DEFAULT_CONFIGS = {
        "sandbox": EnvironmentGitConfig(
            path=Path("/home/ec2-user/projects/maestro-frontend-production"),
            remote_url="git@github.com:fifth-9/maestro-frontend.git",
            branch="main"
        ),
        "demo": EnvironmentGitConfig(
            path=Path("/home/ec2-user/maestro"),
            remote_url="git@github.com:fifth-9/maestro-frontend.git",
            branch="main"
        ),
        "dev": EnvironmentGitConfig(
            path=Path("/home/ec2-user/development/maestro-frontend"),
            remote_url="git@github.com:fifth-9/maestro-frontend.git",
            branch="main"
        )
    }

    def __init__(
        self,
        configs: Optional[dict[str, EnvironmentGitConfig]] = None
    ):
        self.configs = configs or self.DEFAULT_CONFIGS
        self._sync_history: list[GitSyncResult] = []

    def get_current_commit(self, environment: str) -> Optional[str]:
        """
        Get current git commit hash for an environment.

        AC-6: All 3 environments show same commit via git rev-parse HEAD.
        """
        if environment not in self.configs:
            raise ValueError(f"Unknown environment: {environment}")

        config = self.configs[environment]
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=str(config.path),
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except Exception as e:
            logger.error(f"Failed to get commit for {environment}: {e}")
            return None

    def get_short_commit(self, environment: str) -> Optional[str]:
        """Get short commit hash (8 chars)."""
        commit = self.get_current_commit(environment)
        return commit[:8] if commit else None

    def get_current_branch(self, environment: str) -> Optional[str]:
        """Get current git branch for an environment."""
        if environment not in self.configs:
            raise ValueError(f"Unknown environment: {environment}")

        config = self.configs[environment]
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=str(config.path),
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except Exception as e:
            logger.error(f"Failed to get branch for {environment}: {e}")
            return None

    def get_remote_url(self, environment: str) -> Optional[str]:
        """
        Get git remote URL for an environment.

        AC-5: Demo has .git directory with same remote as Sandbox.
        """
        if environment not in self.configs:
            raise ValueError(f"Unknown environment: {environment}")

        config = self.configs[environment]
        try:
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=str(config.path),
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except Exception as e:
            logger.error(f"Failed to get remote URL for {environment}: {e}")
            return None

    def has_git_directory(self, environment: str) -> bool:
        """
        Check if environment has .git directory.

        AC-5: Demo has .git directory with same remote as Sandbox.
        """
        if environment not in self.configs:
            raise ValueError(f"Unknown environment: {environment}")

        config = self.configs[environment]
        git_dir = config.path / ".git"
        return git_dir.exists() and git_dir.is_dir()

    def compare_environments(
        self,
        source: str,
        targets: list[str]
    ) -> dict[str, Any]:
        """
        Compare git state across environments.

        Verifies AC-5 and AC-6.
        """
        source_commit = self.get_current_commit(source)
        source_remote = self.get_remote_url(source)

        comparison = {
            "source_environment": source,
            "source_commit": source_commit,
            "source_remote": source_remote,
            "targets": {},
            "all_match": True,
            "checked_at": datetime.utcnow().isoformat()
        }

        for target in targets:
            target_commit = self.get_current_commit(target)
            target_remote = self.get_remote_url(target)
            has_git = self.has_git_directory(target)

            target_data = {
                "has_git_directory": has_git,
                "commit": target_commit,
                "remote": target_remote,
                "commit_matches": source_commit == target_commit,
                "remote_matches": source_remote == target_remote
            }
            comparison["targets"][target] = target_data

            if not target_data["commit_matches"]:
                comparison["all_match"] = False

        return comparison

    async def git_pull(self, environment: str) -> dict[str, Any]:
        """
        Run git pull on target environment.

        AC-7: Deployment script uses git pull instead of rsync.
        """
        if environment not in self.configs:
            raise ValueError(f"Unknown environment: {environment}")

        config = self.configs[environment]
        previous_commit = self.get_current_commit(environment)

        try:
            # Fetch first
            fetch_result = subprocess.run(
                ["git", "fetch", "origin", config.branch],
                cwd=str(config.path),
                capture_output=True,
                text=True,
                timeout=60
            )

            # Then pull
            pull_result = subprocess.run(
                ["git", "pull", "origin", config.branch],
                cwd=str(config.path),
                capture_output=True,
                text=True,
                timeout=120
            )

            new_commit = self.get_current_commit(environment)

            return {
                "status": "success" if pull_result.returncode == 0 else "failed",
                "environment": environment,
                "previous_commit": previous_commit,
                "current_commit": new_commit,
                "changed": previous_commit != new_commit,
                "returncode": pull_result.returncode,
                "stdout": pull_result.stdout,
                "stderr": pull_result.stderr
            }
        except subprocess.TimeoutExpired:
            return {
                "status": "timeout",
                "environment": environment,
                "error": "Git pull timed out"
            }
        except Exception as e:
            return {
                "status": "error",
                "environment": environment,
                "error": str(e)
            }

    async def setup_git_repository(
        self,
        environment: str,
        force: bool = False
    ) -> dict[str, Any]:
        """
        Set up git repository on environment that doesn't have one.

        AC-5: Demo has .git directory with same remote as Sandbox.
        """
        if environment not in self.configs:
            raise ValueError(f"Unknown environment: {environment}")

        config = self.configs[environment]

        if self.has_git_directory(environment) and not force:
            return {
                "status": "already_exists",
                "environment": environment,
                "path": str(config.path)
            }

        try:
            # Clone repository to temp location
            result = subprocess.run(
                ["git", "clone", "-b", config.branch, config.remote_url, str(config.path)],
                capture_output=True,
                text=True,
                timeout=300
            )

            return {
                "status": "success" if result.returncode == 0 else "failed",
                "environment": environment,
                "path": str(config.path),
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
        except Exception as e:
            return {
                "status": "error",
                "environment": environment,
                "error": str(e)
            }

    def create_version_json(
        self,
        environment: str,
        version: str = "1.0.0"
    ) -> VersionInfo:
        """
        Create VERSION.json for an environment.

        AC-8: Supports /api/health/version endpoint.
        AC-9: VERSION.json tracking for deployments.
        """
        commit = self.get_current_commit(environment) or "unknown"
        branch = self.get_current_branch(environment) or "main"

        version_info = VersionInfo(
            version=version,
            commit=commit[:8] if len(commit) > 8 else commit,
            branch=branch,
            build_time=datetime.utcnow().isoformat(),
            environment=environment,
            deployed_at=datetime.utcnow().isoformat(),
            deployed_by="system"
        )

        if environment in self.configs:
            config = self.configs[environment]
            version_file = config.path / "VERSION.json"
            try:
                with open(version_file, "w") as f:
                    json.dump(version_info.to_dict(), f, indent=2)
                logger.info(f"Created VERSION.json at {version_file}")
            except Exception as e:
                logger.error(f"Failed to create VERSION.json: {e}")

        return version_info

    def read_version_json(self, environment: str) -> Optional[VersionInfo]:
        """Read VERSION.json from environment."""
        if environment not in self.configs:
            raise ValueError(f"Unknown environment: {environment}")

        config = self.configs[environment]
        version_file = config.path / "VERSION.json"

        try:
            if version_file.exists():
                with open(version_file) as f:
                    data = json.load(f)
                return VersionInfo(**data)
            return None
        except Exception as e:
            logger.error(f"Failed to read VERSION.json: {e}")
            return None

    async def sync_to_commit(
        self,
        environments: list[str],
        target_commit: str
    ) -> GitSyncResult:
        """
        Sync all environments to specific commit.

        AC-6: All 3 environments show same commit via git rev-parse HEAD.
        """
        import uuid

        sync_id = str(uuid.uuid4())
        result = GitSyncResult(
            sync_id=sync_id,
            target_env=",".join(environments),
            status=GitSyncStatus.IN_PROGRESS,
            started_at=datetime.utcnow(),
            current_commit=target_commit
        )

        try:
            details: dict[str, Any] = {"environments": {}}

            for env in environments:
                if env not in self.configs:
                    details["environments"][env] = {"error": "Unknown environment"}
                    continue

                config = self.configs[env]
                result.previous_commit = self.get_current_commit(env)

                # Checkout specific commit
                checkout_result = subprocess.run(
                    ["git", "checkout", target_commit],
                    cwd=str(config.path),
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                new_commit = self.get_current_commit(env)
                details["environments"][env] = {
                    "status": "success" if checkout_result.returncode == 0 else "failed",
                    "previous_commit": result.previous_commit,
                    "current_commit": new_commit,
                    "matches_target": new_commit and new_commit.startswith(target_commit)
                }

            result.details = details
            result.status = GitSyncStatus.COMPLETED
            result.completed_at = datetime.utcnow()

        except Exception as e:
            result.status = GitSyncStatus.FAILED
            result.error = str(e)
            result.completed_at = datetime.utcnow()

        self._sync_history.append(result)
        return result

    def get_sync_history(self, limit: int = 50) -> list[GitSyncResult]:
        """Get recent sync history."""
        return self._sync_history[-limit:]

    def generate_deployment_script(self, environment: str) -> str:
        """
        Generate git-based deployment script.

        AC-7: Deployment script uses git pull instead of rsync.
        """
        if environment not in self.configs:
            raise ValueError(f"Unknown environment: {environment}")

        config = self.configs[environment]

        script = f'''#!/bin/bash
# Git-based deployment script for {environment}
# Generated by GitSyncManager - AC-7 implementation
# EPIC: MD-2790

set -e

DEPLOY_PATH="{config.path}"
BRANCH="{config.branch}"
REMOTE="origin"

echo "=== Starting git-based deployment to {environment} ==="
echo "Timestamp: $(date -Iseconds)"

# Navigate to deployment path
cd "$DEPLOY_PATH"

# Get current commit before pull
PREVIOUS_COMMIT=$(git rev-parse HEAD)
echo "Previous commit: $PREVIOUS_COMMIT"

# Fetch latest changes
echo "Fetching from $REMOTE/$BRANCH..."
git fetch "$REMOTE" "$BRANCH"

# Pull changes
echo "Pulling changes..."
git pull "$REMOTE" "$BRANCH"

# Get new commit
CURRENT_COMMIT=$(git rev-parse HEAD)
echo "Current commit: $CURRENT_COMMIT"

# Update VERSION.json
echo '{{"version": "1.0.0", "commit": "'${{CURRENT_COMMIT:0:8}}'", "branch": "'$BRANCH'", "environment": "{environment}", "deployed_at": "'$(date -Iseconds)'", "deployed_by": "system"}}' > VERSION.json
echo "Updated VERSION.json"

# Run Prisma migrations
echo "Running database migrations..."
npx prisma migrate deploy

# Generate Prisma client
echo "Generating Prisma client..."
npx prisma generate

# Install dependencies if needed
if [ "$PREVIOUS_COMMIT" != "$CURRENT_COMMIT" ]; then
    echo "Installing dependencies..."
    npm ci
fi

# Restart application (PM2)
echo "Restarting application..."
pm2 restart all || true

echo "=== Deployment complete ==="
echo "Deployed commit: $CURRENT_COMMIT"
'''
        return script
