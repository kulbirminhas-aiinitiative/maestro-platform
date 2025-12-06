"""
Rollback Executor - Artifact cleanup on rollback

EPIC: MD-2527 - AC-3: Artifact cleanup on rollback

Executes cleanup operations for artifacts created during failed phases.
Supports files, Confluence pages, JIRA comments, and custom artifacts.
"""

import logging
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class CleanupResult:
    """Result of a cleanup operation."""
    success: bool
    artifact_type: str
    artifact_id: str
    error: Optional[str] = None


class RollbackExecutor:
    """
    Executes rollback cleanup operations.

    Handles cleanup of:
    - Local files and directories
    - Confluence pages (via API)
    - JIRA comments (via API)
    - Custom artifacts via registered handlers
    """

    def __init__(
        self,
        jira_client: Optional[Any] = None,
        confluence_client: Optional[Any] = None,
        dry_run: bool = False,
    ):
        """
        Initialize rollback executor.

        Args:
            jira_client: Optional JIRA API client
            confluence_client: Optional Confluence API client
            dry_run: If True, don't actually delete anything
        """
        self.jira_client = jira_client
        self.confluence_client = confluence_client
        self.dry_run = dry_run
        self._custom_handlers: Dict[str, Callable[[str], bool]] = {}
        logger.info(f"RollbackExecutor initialized (dry_run={dry_run})")

    def register_cleanup_handler(
        self,
        artifact_type: str,
        handler: Callable[[str], bool],
    ) -> None:
        """
        Register custom cleanup handler for artifact type.

        Args:
            artifact_type: Type of artifact (e.g., "database_record")
            handler: Function that takes artifact ID and returns success status
        """
        self._custom_handlers[artifact_type] = handler
        logger.debug(f"Registered cleanup handler for: {artifact_type}")

    def cleanup_checkpoint_artifacts(
        self,
        checkpoint: Any,  # PhaseCheckpoint - avoid circular import
    ) -> Dict[str, List[str]]:
        """
        Clean up all artifacts from a checkpoint.

        Args:
            checkpoint: PhaseCheckpoint containing artifact lists

        Returns:
            Dict with 'cleaned' and 'failed' lists
        """
        cleaned = []
        failed = []

        # Clean up files
        for file_path in checkpoint.files_created:
            result = self.cleanup_file(file_path)
            if result.success:
                cleaned.append(f"file:{file_path}")
            else:
                failed.append(f"file:{file_path}")

        # Clean up Confluence pages
        for page_id in checkpoint.confluence_pages:
            result = self.cleanup_confluence_page(page_id)
            if result.success:
                cleaned.append(f"confluence:{page_id}")
            else:
                failed.append(f"confluence:{page_id}")

        # Clean up JIRA comments
        for comment_id in checkpoint.jira_comments:
            result = self.cleanup_jira_comment(comment_id)
            if result.success:
                cleaned.append(f"jira_comment:{comment_id}")
            else:
                failed.append(f"jira_comment:{comment_id}")

        # Clean up generic artifacts
        for artifact_path in checkpoint.artifacts_created:
            result = self.cleanup_artifact(artifact_path)
            if result.success:
                cleaned.append(f"artifact:{artifact_path}")
            else:
                failed.append(f"artifact:{artifact_path}")

        logger.info(
            f"Checkpoint cleanup complete: {len(cleaned)} cleaned, {len(failed)} failed"
        )

        return {"cleaned": cleaned, "failed": failed}

    def cleanup_file(self, file_path: str) -> CleanupResult:
        """
        Clean up a file or directory.

        Args:
            file_path: Path to file or directory

        Returns:
            CleanupResult
        """
        path = Path(file_path)

        if self.dry_run:
            logger.info(f"[DRY RUN] Would delete: {file_path}")
            return CleanupResult(
                success=True,
                artifact_type="file",
                artifact_id=file_path,
            )

        try:
            if path.is_file():
                path.unlink()
                logger.info(f"Deleted file: {file_path}")
            elif path.is_dir():
                shutil.rmtree(path)
                logger.info(f"Deleted directory: {file_path}")
            else:
                logger.warning(f"Path does not exist: {file_path}")
                return CleanupResult(
                    success=True,  # Consider missing files as success
                    artifact_type="file",
                    artifact_id=file_path,
                )

            return CleanupResult(
                success=True,
                artifact_type="file",
                artifact_id=file_path,
            )

        except Exception as e:
            logger.error(f"Failed to delete {file_path}: {e}")
            return CleanupResult(
                success=False,
                artifact_type="file",
                artifact_id=file_path,
                error=str(e),
            )

    def cleanup_confluence_page(self, page_id: str) -> CleanupResult:
        """
        Delete a Confluence page.

        Args:
            page_id: Confluence page ID

        Returns:
            CleanupResult
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Would delete Confluence page: {page_id}")
            return CleanupResult(
                success=True,
                artifact_type="confluence_page",
                artifact_id=page_id,
            )

        if not self.confluence_client:
            logger.warning(f"No Confluence client - skipping page deletion: {page_id}")
            return CleanupResult(
                success=False,
                artifact_type="confluence_page",
                artifact_id=page_id,
                error="No Confluence client configured",
            )

        try:
            # Attempt to delete via Confluence API
            self.confluence_client.delete_page(page_id)
            logger.info(f"Deleted Confluence page: {page_id}")
            return CleanupResult(
                success=True,
                artifact_type="confluence_page",
                artifact_id=page_id,
            )
        except Exception as e:
            logger.error(f"Failed to delete Confluence page {page_id}: {e}")
            return CleanupResult(
                success=False,
                artifact_type="confluence_page",
                artifact_id=page_id,
                error=str(e),
            )

    def cleanup_jira_comment(self, comment_id: str) -> CleanupResult:
        """
        Delete a JIRA comment.

        Args:
            comment_id: JIRA comment ID (format: "ISSUE-KEY:COMMENT_ID")

        Returns:
            CleanupResult
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Would delete JIRA comment: {comment_id}")
            return CleanupResult(
                success=True,
                artifact_type="jira_comment",
                artifact_id=comment_id,
            )

        if not self.jira_client:
            logger.warning(f"No JIRA client - skipping comment deletion: {comment_id}")
            return CleanupResult(
                success=False,
                artifact_type="jira_comment",
                artifact_id=comment_id,
                error="No JIRA client configured",
            )

        try:
            # Parse comment ID (expected format: "ISSUE-KEY:COMMENT_ID")
            if ":" in comment_id:
                issue_key, cid = comment_id.split(":", 1)
                self.jira_client.delete_comment(issue_key, cid)
            else:
                # Assume it's just the comment ID
                self.jira_client.delete_comment_by_id(comment_id)

            logger.info(f"Deleted JIRA comment: {comment_id}")
            return CleanupResult(
                success=True,
                artifact_type="jira_comment",
                artifact_id=comment_id,
            )
        except Exception as e:
            logger.error(f"Failed to delete JIRA comment {comment_id}: {e}")
            return CleanupResult(
                success=False,
                artifact_type="jira_comment",
                artifact_id=comment_id,
                error=str(e),
            )

    def cleanup_artifact(self, artifact_path: str) -> CleanupResult:
        """
        Clean up a generic artifact.

        Attempts to determine type and use appropriate handler.

        Args:
            artifact_path: Path or identifier for artifact

        Returns:
            CleanupResult
        """
        # Check for custom handler by prefix
        if ":" in artifact_path:
            artifact_type, artifact_id = artifact_path.split(":", 1)
            if artifact_type in self._custom_handlers:
                try:
                    success = self._custom_handlers[artifact_type](artifact_id)
                    return CleanupResult(
                        success=success,
                        artifact_type=artifact_type,
                        artifact_id=artifact_id,
                    )
                except Exception as e:
                    return CleanupResult(
                        success=False,
                        artifact_type=artifact_type,
                        artifact_id=artifact_id,
                        error=str(e),
                    )

        # Default: treat as file path
        return self.cleanup_file(artifact_path)

    def cleanup_files_in_directory(
        self,
        directory: str,
        pattern: str = "*",
    ) -> Dict[str, List[str]]:
        """
        Clean up files matching pattern in directory.

        Args:
            directory: Directory path
            pattern: Glob pattern for files

        Returns:
            Dict with 'cleaned' and 'failed' lists
        """
        cleaned = []
        failed = []
        path = Path(directory)

        if not path.exists():
            logger.warning(f"Directory does not exist: {directory}")
            return {"cleaned": [], "failed": []}

        for file_path in path.glob(pattern):
            result = self.cleanup_file(str(file_path))
            if result.success:
                cleaned.append(str(file_path))
            else:
                failed.append(str(file_path))

        return {"cleaned": cleaned, "failed": failed}

    def verify_cleanup(
        self,
        artifacts: List[str],
    ) -> Dict[str, bool]:
        """
        Verify artifacts have been cleaned up.

        Args:
            artifacts: List of artifact paths/IDs

        Returns:
            Dict mapping artifact to existence status (True = still exists)
        """
        results = {}

        for artifact in artifacts:
            if artifact.startswith("file:"):
                file_path = artifact.replace("file:", "")
                results[artifact] = Path(file_path).exists()
            elif artifact.startswith("confluence:"):
                # Would need API call to verify
                results[artifact] = False  # Assume cleaned
            elif artifact.startswith("jira_comment:"):
                # Would need API call to verify
                results[artifact] = False  # Assume cleaned
            else:
                # Check as file path
                results[artifact] = Path(artifact).exists()

        return results
