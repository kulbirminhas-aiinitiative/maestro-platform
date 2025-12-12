#!/usr/bin/env python3
"""
Checkpoint Management for Phased Execution

Handles checkpoint lifecycle including:
- Storage and retrieval
- Rotation and cleanup (configurable retention)
- Validation and recovery
- S3/Redis abstraction (future)

Addresses Gap G-006 from DESIGN_REVIEW_PHASED_EXECUTION.md:
"No checkpoint rotation/cleanup mechanism"
"""

import json
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class CheckpointInfo:
    """Information about a checkpoint file"""
    path: Path
    workflow_id: str
    phase: str
    created_at: datetime
    size_bytes: int
    is_synthetic: bool = False
    version: int = 1

    @property
    def age_hours(self) -> float:
        """Age of checkpoint in hours"""
        return (datetime.utcnow() - self.created_at).total_seconds() / 3600


class CheckpointManager:
    """
    Manages checkpoint storage, rotation, and cleanup.

    Environment Variables:
        MAESTRO_CHECKPOINT_DIR: Base directory for checkpoints
        MAESTRO_CHECKPOINT_RETENTION: Max checkpoints per workflow (default: 10)
        MAESTRO_CHECKPOINT_MAX_AGE_DAYS: Max age before cleanup (default: 30)
    """

    def __init__(
        self,
        checkpoint_dir: Optional[Path] = None,
        max_checkpoints_per_workflow: int = 10,
        max_age_days: int = 30
    ):
        """
        Initialize checkpoint manager.

        Args:
            checkpoint_dir: Base directory for checkpoints
            max_checkpoints_per_workflow: Max checkpoints to retain per workflow
            max_age_days: Max age in days before cleanup
        """
        if checkpoint_dir is not None:
            self.checkpoint_dir = Path(checkpoint_dir) if isinstance(checkpoint_dir, str) else checkpoint_dir
        else:
            self.checkpoint_dir = Path(os.environ.get("MAESTRO_CHECKPOINT_DIR", "./maestro_workflows.db"))

        self.max_checkpoints = int(
            os.environ.get("MAESTRO_CHECKPOINT_RETENTION", max_checkpoints_per_workflow)
        )
        self.max_age_days = int(
            os.environ.get("MAESTRO_CHECKPOINT_MAX_AGE_DAYS", max_age_days)
        )

        if self.checkpoint_dir.exists() and not self.checkpoint_dir.is_dir():
            # File exists with same name, use alternative path
            self.checkpoint_dir = Path(str(self.checkpoint_dir) + "_checkpoints")
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"CheckpointManager initialized: {self.checkpoint_dir}")

    def list_workflows(self) -> List[str]:
        """List all workflow IDs with checkpoints"""
        if not self.checkpoint_dir.exists():
            return []

        return [
            d.name for d in self.checkpoint_dir.iterdir()
            if d.is_dir() and d.name.startswith("wf-")
        ]

    def list_checkpoints(self, workflow_id: str) -> List[CheckpointInfo]:
        """
        List all checkpoints for a workflow.

        Args:
            workflow_id: Workflow ID

        Returns:
            List of CheckpointInfo sorted by creation time (newest first)
        """
        workflow_dir = self.checkpoint_dir / workflow_id
        if not workflow_dir.exists():
            return []

        checkpoints = []
        for f in workflow_dir.glob("checkpoint_*.json"):
            try:
                info = self._parse_checkpoint(f, workflow_id)
                if info:
                    checkpoints.append(info)
            except Exception as e:
                logger.warning(f"Failed to parse checkpoint {f}: {e}")

        return sorted(checkpoints, key=lambda c: c.created_at, reverse=True)

    def _parse_checkpoint(self, path: Path, workflow_id: str) -> Optional[CheckpointInfo]:
        """Parse checkpoint file to extract metadata"""
        try:
            stat = path.stat()
            with open(path) as f:
                data = json.load(f)

            # Extract phase from filename (checkpoint_<phase>.json)
            phase = path.stem.replace("checkpoint_", "").replace("_synthetic", "")

            # Get creation time from file or content
            created_at = data.get("checkpoint_metadata", {}).get("created_at")
            if created_at:
                if isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                else:
                    created_at = datetime.utcnow()
            else:
                created_at = datetime.fromtimestamp(stat.st_mtime)

            return CheckpointInfo(
                path=path,
                workflow_id=workflow_id,
                phase=phase,
                created_at=created_at,
                size_bytes=stat.st_size,
                is_synthetic=data.get("synthetic", False) or "_synthetic" in path.stem,
                version=data.get("checkpoint_metadata", {}).get("version", 1)
            )
        except Exception as e:
            logger.warning(f"Error parsing checkpoint {path}: {e}")
            return None

    def get_latest_checkpoint(self, workflow_id: str) -> Optional[CheckpointInfo]:
        """
        Get the most recent checkpoint for a workflow.

        Args:
            workflow_id: Workflow ID

        Returns:
            Latest checkpoint info or None
        """
        checkpoints = self.list_checkpoints(workflow_id)
        return checkpoints[0] if checkpoints else None

    def get_checkpoint_for_phase(
        self,
        workflow_id: str,
        phase: str
    ) -> Optional[CheckpointInfo]:
        """
        Get checkpoint for a specific phase.

        Args:
            workflow_id: Workflow ID
            phase: Phase name

        Returns:
            Checkpoint info or None
        """
        checkpoints = self.list_checkpoints(workflow_id)
        for cp in checkpoints:
            if cp.phase == phase:
                return cp
        return None

    def rotate_checkpoints(self, workflow_id: str) -> int:
        """
        Rotate checkpoints for a workflow, keeping only the most recent.

        Args:
            workflow_id: Workflow ID

        Returns:
            Number of checkpoints deleted
        """
        checkpoints = self.list_checkpoints(workflow_id)

        if len(checkpoints) <= self.max_checkpoints:
            return 0

        # Keep the most recent, delete the rest
        to_delete = checkpoints[self.max_checkpoints:]
        deleted = 0

        for cp in to_delete:
            try:
                cp.path.unlink()
                logger.info(f"Rotated checkpoint: {cp.path}")
                deleted += 1
            except Exception as e:
                logger.warning(f"Failed to delete checkpoint {cp.path}: {e}")

        return deleted

    def cleanup_old_checkpoints(self) -> Tuple[int, int]:
        """
        Clean up old checkpoints across all workflows.

        Returns:
            Tuple of (workflows cleaned, checkpoints deleted)
        """
        cutoff = datetime.utcnow() - timedelta(days=self.max_age_days)
        workflows_cleaned = 0
        total_deleted = 0

        for workflow_id in self.list_workflows():
            checkpoints = self.list_checkpoints(workflow_id)
            deleted = 0

            for cp in checkpoints:
                if cp.created_at < cutoff:
                    try:
                        cp.path.unlink()
                        deleted += 1
                        logger.info(f"Cleaned old checkpoint: {cp.path}")
                    except Exception as e:
                        logger.warning(f"Failed to clean checkpoint {cp.path}: {e}")

            if deleted > 0:
                workflows_cleaned += 1
                total_deleted += deleted

            # Also apply rotation
            total_deleted += self.rotate_checkpoints(workflow_id)

        return workflows_cleaned, total_deleted

    def archive_workflow(
        self,
        workflow_id: str,
        archive_dir: Optional[Path] = None
    ) -> Optional[Path]:
        """
        Archive all checkpoints for a workflow.

        Args:
            workflow_id: Workflow ID
            archive_dir: Optional archive directory

        Returns:
            Path to archive or None if failed
        """
        workflow_dir = self.checkpoint_dir / workflow_id
        if not workflow_dir.exists():
            return None

        archive_dir = archive_dir or self.checkpoint_dir / "archive"
        archive_dir.mkdir(parents=True, exist_ok=True)

        archive_name = f"{workflow_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        archive_path = archive_dir / archive_name

        try:
            shutil.make_archive(str(archive_path), "zip", workflow_dir)
            logger.info(f"Archived workflow {workflow_id} to {archive_path}.zip")
            return Path(f"{archive_path}.zip")
        except Exception as e:
            logger.error(f"Failed to archive workflow {workflow_id}: {e}")
            return None

    def delete_workflow_checkpoints(self, workflow_id: str) -> bool:
        """
        Delete all checkpoints for a workflow.

        Args:
            workflow_id: Workflow ID

        Returns:
            True if successful
        """
        workflow_dir = self.checkpoint_dir / workflow_id
        if not workflow_dir.exists():
            return True

        try:
            shutil.rmtree(workflow_dir)
            logger.info(f"Deleted all checkpoints for {workflow_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete checkpoints for {workflow_id}: {e}")
            return False

    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics for checkpoints.

        Returns:
            Dictionary with storage statistics
        """
        total_size = 0
        total_checkpoints = 0
        workflows = self.list_workflows()

        for workflow_id in workflows:
            checkpoints = self.list_checkpoints(workflow_id)
            for cp in checkpoints:
                total_size += cp.size_bytes
                total_checkpoints += 1

        return {
            "total_workflows": len(workflows),
            "total_checkpoints": total_checkpoints,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "checkpoint_dir": str(self.checkpoint_dir),
            "max_checkpoints_per_workflow": self.max_checkpoints,
            "max_age_days": self.max_age_days
        }

    def validate_checkpoint(self, path: Path) -> Tuple[bool, Optional[str]]:
        """
        Validate a checkpoint file.

        Args:
            path: Path to checkpoint

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not path.exists():
            return False, "File does not exist"

        try:
            with open(path) as f:
                data = json.load(f)

            # Check required fields
            if "workflow_id" not in data and "workflow" not in data:
                return False, "Missing workflow_id"

            # Check for corruption indicators
            if data.get("checkpoint_metadata", {}).get("version", 0) < 1:
                return False, "Invalid version"

            return True, None

        except json.JSONDecodeError as e:
            return False, f"Invalid JSON: {e}"
        except Exception as e:
            return False, f"Validation error: {e}"


def run_checkpoint_cleanup():
    """
    CLI helper to run checkpoint cleanup.

    Can be scheduled via cron or systemd timer.
    """
    import argparse

    parser = argparse.ArgumentParser(description="Checkpoint cleanup utility")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted")
    parser.add_argument("--stats", action="store_true", help="Show storage statistics")
    args = parser.parse_args()

    manager = CheckpointManager()

    if args.stats:
        stats = manager.get_storage_stats()
        print("\nCheckpoint Storage Statistics:")
        print(f"  Directory: {stats['checkpoint_dir']}")
        print(f"  Workflows: {stats['total_workflows']}")
        print(f"  Checkpoints: {stats['total_checkpoints']}")
        print(f"  Total Size: {stats['total_size_mb']} MB")
        print(f"  Retention: {stats['max_checkpoints_per_workflow']} per workflow")
        print(f"  Max Age: {stats['max_age_days']} days")
        return

    if args.dry_run:
        print("\nDry run - would clean:")
        for workflow_id in manager.list_workflows():
            checkpoints = manager.list_checkpoints(workflow_id)
            if len(checkpoints) > manager.max_checkpoints:
                excess = len(checkpoints) - manager.max_checkpoints
                print(f"  {workflow_id}: {excess} excess checkpoints")
        return

    workflows, deleted = manager.cleanup_old_checkpoints()
    print(f"\nCleanup complete:")
    print(f"  Workflows processed: {workflows}")
    print(f"  Checkpoints deleted: {deleted}")


__all__ = [
    "CheckpointManager",
    "CheckpointInfo",
    "run_checkpoint_cleanup"
]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_checkpoint_cleanup()
