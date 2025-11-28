"""
Git Manager Service
Handles Git operations for template cloning, archiving, and version management
"""

import asyncio
import hashlib
import os
import shutil
import tarfile
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime

import git
import structlog
import yaml
from git.exc import GitCommandError

from .models.manifest import TemplateManifest

logger = structlog.get_logger(__name__)


class GitManagerError(Exception):
    """Base exception for Git manager errors"""
    pass


class GitCloneError(GitManagerError):
    """Error during Git clone operation"""
    pass


class GitArchiveError(GitManagerError):
    """Error during archive creation"""
    pass


class ManifestNotFoundError(GitManagerError):
    """Manifest file not found in repository"""
    pass


class GitManager:
    """
    Manages Git operations for template repositories

    Features:
    - Shallow cloning for efficiency
    - Archive creation (tar.gz, zip)
    - Manifest extraction and validation
    - Automatic cleanup
    """

    def __init__(
        self,
        temp_dir: str = "/tmp/maestro_templates",
        timeout_seconds: int = 300,
        clone_depth: int = 1
    ):
        """
        Initialize Git Manager

        Args:
            temp_dir: Base directory for temporary Git operations
            timeout_seconds: Timeout for Git operations
            clone_depth: Depth for shallow clones (1 = only latest commit)
        """
        self.temp_dir = Path(temp_dir)
        self.timeout_seconds = timeout_seconds
        self.clone_depth = clone_depth

        # Ensure temp directory exists
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            "git_manager_initialized",
            temp_dir=str(self.temp_dir),
            timeout=timeout_seconds,
            clone_depth=clone_depth
        )

    async def clone_repository(
        self,
        git_url: str,
        branch: str = "main",
        commit_hash: Optional[str] = None
    ) -> Tuple[Path, str, int]:
        """
        Clone a Git repository

        Args:
            git_url: Repository URL
            branch: Branch to clone
            commit_hash: Specific commit hash (optional)

        Returns:
            Tuple of (clone_path, actual_commit_hash, duration_ms)

        Raises:
            GitCloneError: If cloning fails
        """
        start_time = time.time()
        clone_dir = None

        try:
            # Create unique temporary directory
            clone_dir = self.temp_dir / f"clone_{int(time.time())}_{os.getpid()}"
            clone_dir.mkdir(parents=True, exist_ok=True)

            logger.info(
                "cloning_repository",
                git_url=git_url,
                branch=branch,
                commit_hash=commit_hash,
                clone_dir=str(clone_dir)
            )

            # Perform shallow clone
            await asyncio.get_event_loop().run_in_executor(
                None,
                self._sync_clone,
                git_url,
                clone_dir,
                branch
            )

            # Get actual commit hash
            repo = git.Repo(clone_dir)
            actual_commit = repo.head.commit.hexsha

            # Checkout specific commit if provided
            if commit_hash and commit_hash != actual_commit:
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    repo.git.checkout,
                    commit_hash
                )
                actual_commit = commit_hash

            duration_ms = int((time.time() - start_time) * 1000)

            logger.info(
                "repository_cloned",
                git_url=git_url,
                commit=actual_commit[:8],
                duration_ms=duration_ms
            )

            return clone_dir, actual_commit, duration_ms

        except GitCommandError as e:
            if clone_dir and clone_dir.exists():
                shutil.rmtree(clone_dir, ignore_errors=True)
            logger.error(
                "clone_failed",
                git_url=git_url,
                error=str(e)
            )
            raise GitCloneError(f"Failed to clone {git_url}: {e}")

        except Exception as e:
            if clone_dir and clone_dir.exists():
                shutil.rmtree(clone_dir, ignore_errors=True)
            logger.error(
                "clone_unexpected_error",
                git_url=git_url,
                error=str(e)
            )
            raise GitCloneError(f"Unexpected error cloning {git_url}: {e}")

    def _sync_clone(self, git_url: str, clone_dir: Path, branch: str):
        """Synchronous Git clone operation (runs in executor)"""
        git.Repo.clone_from(
            git_url,
            clone_dir,
            branch=branch,
            depth=self.clone_depth,
            single_branch=True
        )

    async def create_archive(
        self,
        source_dir: Path,
        output_path: Path,
        format: str = "tar.gz"
    ) -> Tuple[int, str, int]:
        """
        Create archive from directory

        Args:
            source_dir: Directory to archive
            output_path: Output archive path
            format: Archive format (tar.gz or zip)

        Returns:
            Tuple of (file_size_bytes, checksum_sha256, duration_ms)

        Raises:
            GitArchiveError: If archive creation fails
        """
        start_time = time.time()

        try:
            logger.info(
                "creating_archive",
                source_dir=str(source_dir),
                output_path=str(output_path),
                format=format
            )

            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Create archive in executor to avoid blocking
            await asyncio.get_event_loop().run_in_executor(
                None,
                self._sync_create_archive,
                source_dir,
                output_path,
                format
            )

            # Calculate file size and checksum
            file_size = output_path.stat().st_size
            checksum = await self._calculate_checksum(output_path)

            duration_ms = int((time.time() - start_time) * 1000)

            logger.info(
                "archive_created",
                output_path=str(output_path),
                size_bytes=file_size,
                checksum=checksum[:16],
                duration_ms=duration_ms
            )

            return file_size, checksum, duration_ms

        except Exception as e:
            logger.error(
                "archive_creation_failed",
                source_dir=str(source_dir),
                error=str(e)
            )
            raise GitArchiveError(f"Failed to create archive: {e}")

    def _sync_create_archive(self, source_dir: Path, output_path: Path, format: str):
        """Synchronous archive creation (runs in executor)"""
        if format == "tar.gz":
            with tarfile.open(output_path, "w:gz") as tar:
                tar.add(source_dir, arcname=source_dir.name)
        elif format == "zip":
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(source_dir):
                    for file in files:
                        file_path = Path(root) / file
                        arcname = file_path.relative_to(source_dir.parent)
                        zipf.write(file_path, arcname)
        else:
            raise ValueError(f"Unsupported archive format: {format}")

    async def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of file"""
        sha256_hash = hashlib.sha256()

        def _sync_hash():
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()

        return await asyncio.get_event_loop().run_in_executor(None, _sync_hash)

    async def extract_manifest(
        self,
        clone_dir: Path
    ) -> TemplateManifest:
        """
        Extract and validate manifest.yaml from cloned repository

        Args:
            clone_dir: Directory containing cloned repository

        Returns:
            Validated TemplateManifest object

        Raises:
            ManifestNotFoundError: If manifest.yaml not found
            ValueError: If manifest is invalid
        """
        manifest_path = clone_dir / "manifest.yaml"

        if not manifest_path.exists():
            # Try alternate names
            for alt_name in ["manifest.yml", ".manifest.yaml", "template.yaml"]:
                alt_path = clone_dir / alt_name
                if alt_path.exists():
                    manifest_path = alt_path
                    break
            else:
                raise ManifestNotFoundError(
                    f"manifest.yaml not found in {clone_dir}"
                )

        logger.info(
            "extracting_manifest",
            manifest_path=str(manifest_path)
        )

        try:
            # Load YAML
            with open(manifest_path, 'r') as f:
                manifest_data = yaml.safe_load(f)

            # Validate with Pydantic
            manifest = TemplateManifest(**manifest_data)

            logger.info(
                "manifest_extracted",
                name=manifest.name,
                version=manifest.version,
                engine=manifest.engine
            )

            return manifest

        except yaml.YAMLError as e:
            logger.error("manifest_yaml_error", error=str(e))
            raise ValueError(f"Invalid YAML in manifest: {e}")

        except Exception as e:
            logger.error("manifest_validation_error", error=str(e))
            raise ValueError(f"Manifest validation failed: {e}")

    async def cleanup_clone(self, clone_dir: Path):
        """
        Clean up cloned repository directory

        Args:
            clone_dir: Directory to remove
        """
        try:
            if clone_dir.exists():
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    shutil.rmtree,
                    clone_dir,
                    True  # ignore_errors
                )
                logger.info("clone_cleanup_complete", clone_dir=str(clone_dir))
        except Exception as e:
            logger.warning(
                "clone_cleanup_failed",
                clone_dir=str(clone_dir),
                error=str(e)
            )

    async def get_repository_info(self, git_url: str, branch: str = "main") -> dict:
        """
        Get repository information without full clone

        Args:
            git_url: Repository URL
            branch: Branch name

        Returns:
            Dict with repository info (latest commit, etc.)
        """
        try:
            clone_dir, commit_hash, _ = await self.clone_repository(git_url, branch)

            try:
                repo = git.Repo(clone_dir)
                info = {
                    "url": git_url,
                    "branch": branch,
                    "latest_commit": commit_hash,
                    "commit_date": datetime.fromtimestamp(repo.head.commit.committed_date).isoformat(),
                    "author": repo.head.commit.author.name,
                    "message": repo.head.commit.message.strip()
                }
                return info
            finally:
                await self.cleanup_clone(clone_dir)

        except Exception as e:
            logger.error("get_repo_info_failed", git_url=git_url, error=str(e))
            raise

    async def list_versions(self, git_url: str) -> list:
        """
        List available versions (branches and tags) in repository

        Args:
            git_url: Repository URL

        Returns:
            List of version strings
        """
        clone_dir = None
        try:
            clone_dir, _, _ = await self.clone_repository(git_url, "main")

            repo = git.Repo(clone_dir)

            # Get branches
            branches = [ref.name.replace('origin/', '') for ref in repo.remote().refs]

            # Get tags
            tags = [tag.name for tag in repo.tags]

            versions = list(set(branches + tags))
            versions.sort()

            logger.info(
                "versions_listed",
                git_url=git_url,
                count=len(versions)
            )

            return versions

        except Exception as e:
            logger.error("list_versions_failed", git_url=git_url, error=str(e))
            raise

        finally:
            if clone_dir:
                await self.cleanup_clone(clone_dir)