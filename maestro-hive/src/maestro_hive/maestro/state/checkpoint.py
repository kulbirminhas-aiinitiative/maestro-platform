"""
Checkpoint Manager - Atomic checkpoint creation and management

EPIC: MD-2514 - AC-2: Checkpoint creation with atomic writes and versioning

Provides:
- Atomic checkpoint writes (temp file + rename)
- Version-based checkpoint management
- Checkpoint validation with checksums
- Configurable retention policies
"""

import logging
import os
import shutil
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .serializer import StateSerializer

logger = logging.getLogger(__name__)


class CheckpointError(Exception):
    """Base exception for checkpoint errors."""
    pass


class CheckpointNotFoundError(CheckpointError):
    """Raised when checkpoint is not found."""
    pass


class ChecksumValidationError(CheckpointError):
    """Raised when checksum validation fails."""
    pass


class AtomicWriteError(CheckpointError):
    """Raised when atomic write fails."""
    pass


@dataclass
class StateMetadata:
    """
    Metadata about workflow state.

    Attributes:
        executor_version: Version of executor that created state
        serialization_format: Format used for serialization
        compression: Compression algorithm (if any)
        custom: Custom metadata fields
    """
    executor_version: str = "2.1"
    serialization_format: str = "json"
    compression: Optional[str] = None
    custom: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowState:
    """
    Complete workflow state for checkpointing.

    Attributes:
        workflow_id: Unique workflow identifier
        phase: Current workflow phase
        step: Current step within phase
        data: State data dictionary
        metadata: State metadata
        created_at: Timestamp of state creation
        checksum: SHA-256 checksum of serialized data
    """
    workflow_id: str
    phase: str
    step: int
    data: Dict[str, Any]
    metadata: StateMetadata = field(default_factory=StateMetadata)
    created_at: datetime = field(default_factory=datetime.utcnow)
    checksum: str = ""


@dataclass
class Checkpoint:
    """
    Checkpoint entry for a workflow.

    Attributes:
        checkpoint_id: Unique checkpoint identifier
        workflow_id: Associated workflow ID
        version: Version number of this checkpoint
        state: The checkpointed workflow state
        created_at: When checkpoint was created
        expires_at: When checkpoint should be deleted
    """
    checkpoint_id: str
    workflow_id: str
    version: int
    state: WorkflowState
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None

    def is_expired(self) -> bool:
        """Check if checkpoint has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Checkpoint":
        """Reconstruct Checkpoint from dict."""
        # Handle state
        state_data = data.get("state", {})
        if isinstance(state_data, dict):
            # Extract value if wrapped
            if "__value__" in state_data:
                state_data = state_data["__value__"]

            # Reconstruct metadata
            meta_data = state_data.get("metadata", {})
            if isinstance(meta_data, dict) and "__value__" in meta_data:
                meta_data = meta_data["__value__"]
            metadata = StateMetadata(
                executor_version=meta_data.get("executor_version", "2.1"),
                serialization_format=meta_data.get("serialization_format", "json"),
                compression=meta_data.get("compression"),
                custom=meta_data.get("custom", {}),
            )

            # Handle created_at
            created_at = state_data.get("created_at")
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at)
            elif isinstance(created_at, dict) and "__value__" in created_at:
                created_at = datetime.fromisoformat(created_at["__value__"])
            elif not isinstance(created_at, datetime):
                created_at = datetime.utcnow()

            state = WorkflowState(
                workflow_id=state_data.get("workflow_id", ""),
                phase=state_data.get("phase", ""),
                step=state_data.get("step", 0),
                data=state_data.get("data", {}),
                metadata=metadata,
                created_at=created_at,
                checksum=state_data.get("checksum", ""),
            )
        else:
            state = state_data

        # Handle checkpoint created_at
        cp_created_at = data.get("created_at")
        if isinstance(cp_created_at, str):
            cp_created_at = datetime.fromisoformat(cp_created_at)
        elif isinstance(cp_created_at, dict) and "__value__" in cp_created_at:
            cp_created_at = datetime.fromisoformat(cp_created_at["__value__"])
        elif not isinstance(cp_created_at, datetime):
            cp_created_at = datetime.utcnow()

        # Handle expires_at
        expires_at = data.get("expires_at")
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
        elif isinstance(expires_at, dict) and "__value__" in expires_at:
            expires_at = datetime.fromisoformat(expires_at["__value__"])
        elif expires_at is not None and not isinstance(expires_at, datetime):
            expires_at = None

        return cls(
            checkpoint_id=data.get("checkpoint_id", ""),
            workflow_id=data.get("workflow_id", ""),
            version=data.get("version", 1),
            state=state,
            created_at=cp_created_at,
            expires_at=expires_at,
        )


class CheckpointManager:
    """
    Manages checkpoint creation, storage, and retrieval.

    Features:
    - Atomic writes using temp file + rename pattern
    - SHA-256 checksum validation
    - Version-based checkpoint management
    - Configurable TTL and retention count
    """

    CHECKPOINT_EXTENSION = ".checkpoint"
    METADATA_FILE = "metadata.json"

    def __init__(
        self,
        storage_path: str = "/var/maestro/checkpoints",
        serializer: Optional[StateSerializer] = None,
        default_ttl: Optional[timedelta] = None,
        max_checkpoints: int = 10,
        verify_on_read: bool = True,
    ):
        """
        Initialize checkpoint manager.

        Args:
            storage_path: Directory for storing checkpoints
            serializer: Serializer instance (creates default if None)
            default_ttl: Default time-to-live for checkpoints
            max_checkpoints: Maximum checkpoints to keep per workflow
            verify_on_read: Whether to verify checksum on read
        """
        self._storage_path = Path(storage_path)
        self._storage_path.mkdir(parents=True, exist_ok=True)

        self._serializer = serializer or StateSerializer()
        self._default_ttl = default_ttl
        self._max_checkpoints = max_checkpoints
        self._verify_on_read = verify_on_read

        logger.info(f"CheckpointManager initialized at {storage_path}")

    def _get_workflow_dir(self, workflow_id: str) -> Path:
        """Get directory for workflow checkpoints."""
        workflow_dir = self._storage_path / workflow_id
        workflow_dir.mkdir(parents=True, exist_ok=True)
        return workflow_dir

    def _get_checkpoint_path(
        self,
        workflow_id: str,
        checkpoint_id: str,
    ) -> Path:
        """Get path for checkpoint file."""
        return (
            self._get_workflow_dir(workflow_id) /
            f"{checkpoint_id}{self.CHECKPOINT_EXTENSION}"
        )

    def _atomic_write(self, path: Path, data: bytes) -> None:
        """
        Atomically write data to file.

        Uses temp file + rename pattern to ensure atomicity.

        Args:
            path: Target file path
            data: Data to write

        Raises:
            AtomicWriteError: If write fails
        """
        # Create temp file in same directory for atomic rename
        temp_fd, temp_path = tempfile.mkstemp(
            suffix=".tmp",
            dir=path.parent,
        )

        try:
            # Write data to temp file
            with os.fdopen(temp_fd, "wb") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())

            # Atomic rename
            os.rename(temp_path, path)

        except Exception as e:
            # Clean up temp file on failure
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            raise AtomicWriteError(f"Atomic write failed: {e}") from e

    def _get_next_version(self, workflow_id: str) -> int:
        """Get next version number for workflow."""
        checkpoints = self.list_checkpoints(workflow_id)
        if not checkpoints:
            return 1
        return max(cp.version for cp in checkpoints) + 1

    def create_checkpoint(
        self,
        workflow_id: str,
        state: WorkflowState,
        ttl: Optional[timedelta] = None,
    ) -> Checkpoint:
        """
        Create a new checkpoint for a workflow.

        Args:
            workflow_id: Workflow identifier
            state: Workflow state to checkpoint
            ttl: Time-to-live (uses default if None)

        Returns:
            Created Checkpoint object

        Raises:
            CheckpointError: If checkpoint creation fails
        """
        checkpoint_id = str(uuid.uuid4())[:12]
        version = self._get_next_version(workflow_id)

        # Compute checksum on state.data only (stable across serialization)
        data_only_bytes = self._serializer.serialize(state.data)
        checksum = self._serializer.compute_checksum(data_only_bytes)
        state.checksum = checksum

        # Calculate expiration
        expires_at = None
        effective_ttl = ttl or self._default_ttl
        if effective_ttl:
            expires_at = datetime.utcnow() + effective_ttl

        # Create checkpoint object
        checkpoint = Checkpoint(
            checkpoint_id=checkpoint_id,
            workflow_id=workflow_id,
            version=version,
            state=state,
            created_at=datetime.utcnow(),
            expires_at=expires_at,
        )

        # Serialize checkpoint
        checkpoint_data = self._serializer.serialize(checkpoint)

        # Atomic write
        path = self._get_checkpoint_path(workflow_id, checkpoint_id)
        self._atomic_write(path, checkpoint_data)

        # Enforce retention policy
        self._enforce_retention(workflow_id)

        logger.info(
            f"Created checkpoint {checkpoint_id} v{version} "
            f"for workflow {workflow_id}"
        )

        return checkpoint

    def get_checkpoint(
        self,
        checkpoint_id: str,
        workflow_id: Optional[str] = None,
        validate: bool = True,
    ) -> Checkpoint:
        """
        Retrieve a specific checkpoint.

        Args:
            checkpoint_id: Checkpoint identifier
            workflow_id: Optional workflow ID (searches all if None)
            validate: Whether to verify checksum

        Returns:
            Checkpoint object

        Raises:
            CheckpointNotFoundError: If checkpoint not found
            ChecksumValidationError: If validation fails
        """
        # Find checkpoint file
        if workflow_id:
            path = self._get_checkpoint_path(workflow_id, checkpoint_id)
            if not path.exists():
                raise CheckpointNotFoundError(
                    f"Checkpoint {checkpoint_id} not found"
                )
        else:
            # Search all workflows
            path = None
            for wf_dir in self._storage_path.iterdir():
                if wf_dir.is_dir():
                    candidate = (
                        wf_dir /
                        f"{checkpoint_id}{self.CHECKPOINT_EXTENSION}"
                    )
                    if candidate.exists():
                        path = candidate
                        break

            if path is None:
                raise CheckpointNotFoundError(
                    f"Checkpoint {checkpoint_id} not found"
                )

        # Read and deserialize
        with open(path, "rb") as f:
            data = f.read()

        cp_dict = self._serializer.deserialize(data)

        # Reconstruct Checkpoint from dict
        if isinstance(cp_dict, dict):
            checkpoint = Checkpoint.from_dict(cp_dict)
        else:
            checkpoint = cp_dict

        # Validate checksum on state.data only (skip if checksum not set yet)
        if validate and self._verify_on_read and checkpoint.state.checksum:
            data_only_bytes = self._serializer.serialize(checkpoint.state.data)
            actual_checksum = self._serializer.compute_checksum(data_only_bytes)

            if actual_checksum != checkpoint.state.checksum:
                raise ChecksumValidationError(
                    f"Checksum mismatch for checkpoint {checkpoint_id}: "
                    f"expected {checkpoint.state.checksum}, "
                    f"got {actual_checksum}"
                )

        return checkpoint

    def get_latest_checkpoint(
        self,
        workflow_id: str,
        validate: bool = True,
    ) -> Optional[Checkpoint]:
        """
        Get the latest checkpoint for a workflow.

        Args:
            workflow_id: Workflow identifier
            validate: Whether to verify checksum

        Returns:
            Latest Checkpoint or None if no checkpoints exist
        """
        checkpoints = self.list_checkpoints(workflow_id)
        if not checkpoints:
            return None

        # Get latest by version
        latest = max(checkpoints, key=lambda cp: cp.version)

        # Re-fetch with full data
        return self.get_checkpoint(
            latest.checkpoint_id,
            workflow_id,
            validate,
        )

    def list_checkpoints(
        self,
        workflow_id: str,
        include_expired: bool = False,
    ) -> List[Checkpoint]:
        """
        List all checkpoints for a workflow.

        Args:
            workflow_id: Workflow identifier
            include_expired: Whether to include expired checkpoints

        Returns:
            List of Checkpoint objects (sorted by version)
        """
        workflow_dir = self._get_workflow_dir(workflow_id)
        checkpoints = []

        for path in workflow_dir.glob(f"*{self.CHECKPOINT_EXTENSION}"):
            try:
                with open(path, "rb") as f:
                    data = f.read()
                cp_dict = self._serializer.deserialize(data)

                # Reconstruct Checkpoint from dict
                if isinstance(cp_dict, dict):
                    checkpoint = Checkpoint.from_dict(cp_dict)
                else:
                    checkpoint = cp_dict

                if include_expired or not checkpoint.is_expired():
                    checkpoints.append(checkpoint)

            except Exception as e:
                logger.warning(f"Failed to read checkpoint {path}: {e}")

        return sorted(checkpoints, key=lambda cp: cp.version)

    def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """
        Delete a specific checkpoint.

        Args:
            checkpoint_id: Checkpoint identifier

        Returns:
            True if deleted, False if not found
        """
        # Search all workflows
        for wf_dir in self._storage_path.iterdir():
            if wf_dir.is_dir():
                path = wf_dir / f"{checkpoint_id}{self.CHECKPOINT_EXTENSION}"
                if path.exists():
                    path.unlink()
                    logger.info(f"Deleted checkpoint {checkpoint_id}")
                    return True

        return False

    def validate_checkpoint(self, checkpoint_id: str) -> bool:
        """
        Validate a checkpoint's integrity.

        Args:
            checkpoint_id: Checkpoint identifier

        Returns:
            True if valid

        Raises:
            CheckpointNotFoundError: If not found
            ChecksumValidationError: If invalid
        """
        checkpoint = self.get_checkpoint(checkpoint_id, validate=True)
        return True

    def _enforce_retention(self, workflow_id: str) -> int:
        """
        Enforce retention policy for workflow.

        Args:
            workflow_id: Workflow identifier

        Returns:
            Number of checkpoints deleted
        """
        checkpoints = self.list_checkpoints(workflow_id, include_expired=True)
        deleted = 0

        # Delete expired checkpoints
        for cp in checkpoints:
            if cp.is_expired():
                if self.delete_checkpoint(cp.checkpoint_id):
                    deleted += 1

        # Enforce max count
        remaining = [cp for cp in checkpoints if not cp.is_expired()]
        if len(remaining) > self._max_checkpoints:
            # Delete oldest checkpoints
            to_delete = sorted(remaining, key=lambda cp: cp.version)
            excess = len(remaining) - self._max_checkpoints

            for cp in to_delete[:excess]:
                if self.delete_checkpoint(cp.checkpoint_id):
                    deleted += 1

        if deleted > 0:
            logger.info(
                f"Retention policy: deleted {deleted} checkpoints "
                f"for workflow {workflow_id}"
            )

        return deleted

    def cleanup_expired(self) -> int:
        """
        Clean up all expired checkpoints.

        Returns:
            Number of checkpoints deleted
        """
        deleted = 0

        for wf_dir in self._storage_path.iterdir():
            if wf_dir.is_dir():
                workflow_id = wf_dir.name
                deleted += self._enforce_retention(workflow_id)

        return deleted

    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on checkpoint storage.

        Returns:
            Health status dictionary
        """
        total_checkpoints = 0
        total_size = 0
        errors = []

        for wf_dir in self._storage_path.iterdir():
            if wf_dir.is_dir():
                for path in wf_dir.glob(f"*{self.CHECKPOINT_EXTENSION}"):
                    total_checkpoints += 1
                    total_size += path.stat().st_size

                    try:
                        with open(path, "rb") as f:
                            data = f.read()
                        self._serializer.deserialize(data)
                    except Exception as e:
                        errors.append(f"{path.name}: {e}")

        return {
            "status": "healthy" if not errors else "degraded",
            "total_checkpoints": total_checkpoints,
            "total_size_bytes": total_size,
            "errors": errors,
        }
