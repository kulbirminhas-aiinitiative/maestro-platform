"""
Phase Checkpoint - State Capture for Rollback

EPIC: MD-2527 - AC-1: State checkpoint before each phase

Captures execution state before each phase to enable rollback on failure.
"""

import json
import logging
import os
import shutil
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class PhaseCheckpoint:
    """
    Checkpoint capturing execution state before a phase.

    Stores:
    - Phase information
    - Execution state
    - Artifacts created up to this point
    - Timestamp for ordering
    """
    checkpoint_id: str
    execution_id: str
    phase_name: str
    phase_index: int
    timestamp: datetime
    state: Dict[str, Any]
    artifacts_created: List[str] = field(default_factory=list)
    confluence_pages: List[str] = field(default_factory=list)
    jira_comments: List[str] = field(default_factory=list)
    files_created: List[str] = field(default_factory=list)
    checksum: Optional[str] = None

    def __post_init__(self):
        """Calculate checksum after initialization."""
        if self.checksum is None:
            self.checksum = self._calculate_checksum()

    def _calculate_checksum(self) -> str:
        """Calculate SHA-256 checksum of checkpoint data for integrity verification."""
        data = {
            "execution_id": self.execution_id,
            "phase_name": self.phase_name,
            "phase_index": self.phase_index,
            "state": self.state,
            "artifacts_created": self.artifacts_created,
        }
        content = json.dumps(data, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()

    def verify_integrity(self) -> bool:
        """Verify checkpoint integrity using checksum."""
        expected = self._calculate_checksum()
        return self.checksum == expected

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "checkpoint_id": self.checkpoint_id,
            "execution_id": self.execution_id,
            "phase_name": self.phase_name,
            "phase_index": self.phase_index,
            "timestamp": self.timestamp.isoformat(),
            "state": self.state,
            "artifacts_created": self.artifacts_created,
            "confluence_pages": self.confluence_pages,
            "jira_comments": self.jira_comments,
            "files_created": self.files_created,
            "checksum": self.checksum,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PhaseCheckpoint":
        """Create checkpoint from dictionary."""
        return cls(
            checkpoint_id=data["checkpoint_id"],
            execution_id=data["execution_id"],
            phase_name=data["phase_name"],
            phase_index=data["phase_index"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            state=data["state"],
            artifacts_created=data.get("artifacts_created", []),
            confluence_pages=data.get("confluence_pages", []),
            jira_comments=data.get("jira_comments", []),
            files_created=data.get("files_created", []),
            checksum=data.get("checksum"),
        )


class CheckpointStore:
    """
    Persistent storage for phase checkpoints.

    Stores checkpoints on disk with integrity verification.
    Supports retrieval, listing, and cleanup operations.
    """

    def __init__(self, checkpoint_dir: str = "/tmp/maestro/checkpoints"):
        """
        Initialize checkpoint store.

        Args:
            checkpoint_dir: Directory to store checkpoint files
        """
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"CheckpointStore initialized at {self.checkpoint_dir}")

    def _get_execution_dir(self, execution_id: str) -> Path:
        """Get directory for execution's checkpoints."""
        exec_dir = self.checkpoint_dir / execution_id
        exec_dir.mkdir(parents=True, exist_ok=True)
        return exec_dir

    def _get_checkpoint_path(self, execution_id: str, checkpoint_id: str) -> Path:
        """Get path for checkpoint file."""
        return self._get_execution_dir(execution_id) / f"{checkpoint_id}.json"

    def save(self, checkpoint: PhaseCheckpoint) -> str:
        """
        Save checkpoint to disk.

        Args:
            checkpoint: Checkpoint to save

        Returns:
            Path to saved checkpoint file
        """
        path = self._get_checkpoint_path(checkpoint.execution_id, checkpoint.checkpoint_id)

        with open(path, "w") as f:
            json.dump(checkpoint.to_dict(), f, indent=2)

        logger.info(f"Checkpoint saved: {checkpoint.checkpoint_id} (phase={checkpoint.phase_name})")
        return str(path)

    def load(self, execution_id: str, checkpoint_id: str) -> Optional[PhaseCheckpoint]:
        """
        Load checkpoint from disk.

        Args:
            execution_id: Execution identifier
            checkpoint_id: Checkpoint identifier

        Returns:
            PhaseCheckpoint or None if not found
        """
        path = self._get_checkpoint_path(execution_id, checkpoint_id)

        if not path.exists():
            logger.warning(f"Checkpoint not found: {checkpoint_id}")
            return None

        try:
            with open(path, "r") as f:
                data = json.load(f)

            checkpoint = PhaseCheckpoint.from_dict(data)

            if not checkpoint.verify_integrity():
                logger.error(f"Checkpoint integrity check failed: {checkpoint_id}")
                return None

            return checkpoint
        except Exception as e:
            logger.error(f"Failed to load checkpoint {checkpoint_id}: {e}")
            return None

    def list_checkpoints(self, execution_id: str) -> List[PhaseCheckpoint]:
        """
        List all checkpoints for an execution.

        Args:
            execution_id: Execution identifier

        Returns:
            List of checkpoints ordered by phase index
        """
        exec_dir = self._get_execution_dir(execution_id)
        checkpoints = []

        for path in exec_dir.glob("*.json"):
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                checkpoint = PhaseCheckpoint.from_dict(data)
                if checkpoint.verify_integrity():
                    checkpoints.append(checkpoint)
            except Exception as e:
                logger.warning(f"Skipping invalid checkpoint {path}: {e}")

        # Sort by phase index
        checkpoints.sort(key=lambda c: c.phase_index)
        return checkpoints

    def get_latest_checkpoint(self, execution_id: str) -> Optional[PhaseCheckpoint]:
        """
        Get the most recent checkpoint for an execution.

        Args:
            execution_id: Execution identifier

        Returns:
            Most recent PhaseCheckpoint or None
        """
        checkpoints = self.list_checkpoints(execution_id)
        return checkpoints[-1] if checkpoints else None

    def delete_checkpoint(self, execution_id: str, checkpoint_id: str) -> bool:
        """
        Delete a checkpoint.

        Args:
            execution_id: Execution identifier
            checkpoint_id: Checkpoint identifier

        Returns:
            True if deleted, False otherwise
        """
        path = self._get_checkpoint_path(execution_id, checkpoint_id)

        if path.exists():
            path.unlink()
            logger.info(f"Checkpoint deleted: {checkpoint_id}")
            return True
        return False

    def cleanup_execution(self, execution_id: str) -> int:
        """
        Remove all checkpoints for an execution.

        Args:
            execution_id: Execution identifier

        Returns:
            Number of checkpoints deleted
        """
        exec_dir = self._get_execution_dir(execution_id)

        if exec_dir.exists():
            count = len(list(exec_dir.glob("*.json")))
            shutil.rmtree(exec_dir)
            logger.info(f"Cleaned up {count} checkpoints for execution {execution_id}")
            return count
        return 0

    def prune_old_checkpoints(self, max_age_hours: int = 24) -> int:
        """
        Remove checkpoints older than specified age.

        Args:
            max_age_hours: Maximum age in hours

        Returns:
            Number of checkpoints pruned
        """
        cutoff = datetime.utcnow()
        pruned = 0

        for exec_dir in self.checkpoint_dir.iterdir():
            if not exec_dir.is_dir():
                continue

            for path in exec_dir.glob("*.json"):
                try:
                    with open(path, "r") as f:
                        data = json.load(f)
                    timestamp = datetime.fromisoformat(data["timestamp"])
                    age_hours = (cutoff - timestamp).total_seconds() / 3600

                    if age_hours > max_age_hours:
                        path.unlink()
                        pruned += 1
                except Exception:
                    pass

        logger.info(f"Pruned {pruned} old checkpoints")
        return pruned
