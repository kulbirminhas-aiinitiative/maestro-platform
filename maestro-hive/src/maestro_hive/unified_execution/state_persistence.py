#!/usr/bin/env python3
"""
State Persistence Module - AC-1 & AC-2 Implementation

EPIC: MD-3091 - Unified Execution Foundation
AC-1: State persists to /var/maestro/state by default
AC-2: Process restart auto-resumes from checkpoint

This module integrates with existing StateManager and CheckpointManager
to provide persistent state management for the unified execution module.
"""

import asyncio
import logging
import os
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TypeVar

from .config import ExecutionConfig, StateConfig, get_execution_config

logger = logging.getLogger(__name__)

# AC-1: Default state path changed from /tmp to /var/maestro/state
DEFAULT_STATE_PATH = "/var/maestro/state"
DEFAULT_CHECKPOINT_PATH = "/var/maestro/checkpoints"

T = TypeVar("T")


@dataclass
class ExecutionState:
    """
    Represents the complete execution state at a point in time.

    This state can be serialized to disk and restored on process restart.
    """

    workflow_id: str
    phase: str = "initializing"
    step: int = 0
    status: str = "pending"
    persona_states: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    retry_counts: Dict[str, int] = field(default_factory=dict)
    completed_tasks: List[str] = field(default_factory=list)
    pending_tasks: List[str] = field(default_factory=list)
    artifacts: Dict[str, str] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    checksum: str = ""

    def update(self) -> None:
        """Update the timestamp on modification."""
        self.updated_at = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutionState":
        """Reconstruct from dictionary."""
        return cls(**data)


class StateCorruptionError(Exception):
    """Raised when state data fails integrity checks."""
    pass


class StatePersistence:
    """
    Manages persistent state for workflow executions.

    Integrates with:
    - StateManager: Thread-safe in-memory state with notifications
    - CheckpointManager: Atomic disk persistence with SHA-256 verification

    Features:
    - AC-1: Persists to /var/maestro/state by default
    - AC-2: Auto-restore from latest checkpoint on startup
    - Thread-safe operations
    - Atomic writes (temp file + rename)
    - Auto-checkpoint at configurable intervals
    """

    def __init__(
        self,
        config: Optional[ExecutionConfig] = None,
        workflow_id: Optional[str] = None,
        auto_restore: bool = True,
    ):
        """
        Initialize state persistence.

        Args:
            config: Execution configuration (uses default if None)
            workflow_id: Optional workflow ID (auto-generated if None)
            auto_restore: Whether to auto-restore from checkpoint on startup
        """
        self.config = config or get_execution_config()
        self.state_config = self.config.state

        # Ensure state directory exists (AC-1)
        self._state_dir = Path(self.state_config.state_dir)
        self._checkpoint_dir = Path(self.state_config.checkpoint_dir)
        self._ensure_directories()

        # Initialize state
        self._workflow_id = workflow_id or self._generate_workflow_id()
        self._state: Optional[ExecutionState] = None
        self._lock = threading.RLock()
        self._checkpoint_timer: Optional[threading.Timer] = None

        # Try to integrate with existing infrastructure
        self._state_manager = self._get_state_manager()
        self._checkpoint_manager = self._get_checkpoint_manager()

        # Auto-restore from checkpoint (AC-2)
        if auto_restore and self._workflow_id:
            restored = self.restore_latest()
            if restored:
                logger.info(f"Restored state for workflow {self._workflow_id}")

        # Initialize new state if not restored
        if self._state is None:
            self._state = ExecutionState(workflow_id=self._workflow_id)

        # Start auto-checkpoint if enabled
        if self.state_config.enable_persistence:
            self._start_auto_checkpoint()

        logger.info(
            f"StatePersistence initialized: workflow={self._workflow_id}, "
            f"state_dir={self._state_dir}"
        )

    def _ensure_directories(self) -> None:
        """Ensure state and checkpoint directories exist."""
        try:
            self._state_dir.mkdir(parents=True, exist_ok=True)
            self._checkpoint_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            # Fall back to user directory if /var not writable
            fallback_base = Path.home() / ".maestro"
            self._state_dir = fallback_base / "state"
            self._checkpoint_dir = fallback_base / "checkpoints"
            self._state_dir.mkdir(parents=True, exist_ok=True)
            self._checkpoint_dir.mkdir(parents=True, exist_ok=True)
            logger.warning(
                f"Using fallback state directory: {self._state_dir} "
                "(no write access to /var/maestro)"
            )

    def _generate_workflow_id(self) -> str:
        """Generate a unique workflow ID."""
        import uuid
        return f"wf_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"

    def _get_state_manager(self) -> Optional[Any]:
        """Get StateManager singleton if available."""
        try:
            from maestro_hive.core.state_manager import StateManager
            return StateManager(
                persistence_dir=str(self._state_dir),
                auto_persist=self.state_config.enable_persistence,
                persist_interval_seconds=self.state_config.auto_checkpoint_interval_seconds,
            )
        except ImportError:
            logger.debug("StateManager not available, using standalone persistence")
            return None

    def _get_checkpoint_manager(self) -> Optional[Any]:
        """Get CheckpointManager if available."""
        try:
            from maestro_hive.maestro.state.checkpoint import CheckpointManager
            return CheckpointManager(
                storage_path=str(self._checkpoint_dir),
                default_ttl=timedelta(days=7),
                max_checkpoints=self.state_config.max_checkpoints_per_workflow,
                verify_on_read=self.state_config.verify_checksum_on_load,
            )
        except ImportError:
            logger.debug("CheckpointManager not available, using file-based persistence")
            return None

    @property
    def workflow_id(self) -> str:
        """Get current workflow ID."""
        return self._workflow_id

    @property
    def state(self) -> ExecutionState:
        """Get current execution state."""
        with self._lock:
            if self._state is None:
                self._state = ExecutionState(workflow_id=self._workflow_id)
            return self._state

    def get_state_path(self) -> Path:
        """Get path to state file for current workflow."""
        return self._state_dir / f"{self._workflow_id}.state.json"

    def update_state(
        self,
        phase: Optional[str] = None,
        step: Optional[int] = None,
        status: Optional[str] = None,
        **kwargs,
    ) -> ExecutionState:
        """
        Update execution state.

        Args:
            phase: Current phase name
            step: Current step number
            status: Current status
            **kwargs: Additional state fields to update

        Returns:
            Updated ExecutionState
        """
        with self._lock:
            if phase is not None:
                self._state.phase = phase
            if step is not None:
                self._state.step = step
            if status is not None:
                self._state.status = status

            # Update arbitrary fields
            for key, value in kwargs.items():
                if hasattr(self._state, key):
                    setattr(self._state, key, value)

            self._state.update()

            # Persist if using StateManager
            if self._state_manager:
                self._state_manager.set_state(
                    key=self._workflow_id,
                    value=self._state.to_dict(),
                    namespace="workflows",
                )

            return self._state

    def mark_task_completed(self, task_id: str, artifacts: Optional[Dict[str, str]] = None) -> None:
        """
        Mark a task as completed.

        Args:
            task_id: Identifier of completed task
            artifacts: Optional dictionary of artifact paths
        """
        with self._lock:
            if task_id in self._state.pending_tasks:
                self._state.pending_tasks.remove(task_id)
            if task_id not in self._state.completed_tasks:
                self._state.completed_tasks.append(task_id)
            if artifacts:
                self._state.artifacts.update(artifacts)
            self._state.update()

    def mark_task_pending(self, task_id: str) -> None:
        """Add a task to pending queue."""
        with self._lock:
            if task_id not in self._state.pending_tasks:
                self._state.pending_tasks.append(task_id)
            self._state.update()

    def increment_retry(self, persona_id: str) -> int:
        """
        Increment retry counter for a persona.

        Args:
            persona_id: Persona identifier

        Returns:
            New retry count
        """
        with self._lock:
            current = self._state.retry_counts.get(persona_id, 0)
            self._state.retry_counts[persona_id] = current + 1
            self._state.update()
            return current + 1

    def get_retry_count(self, persona_id: str) -> int:
        """Get current retry count for a persona."""
        with self._lock:
            return self._state.retry_counts.get(persona_id, 0)

    def update_persona_state(self, persona_id: str, state: Dict[str, Any]) -> None:
        """Update state for a specific persona."""
        with self._lock:
            self._state.persona_states[persona_id] = state
            self._state.update()

    def get_persona_state(self, persona_id: str) -> Optional[Dict[str, Any]]:
        """Get state for a specific persona."""
        with self._lock:
            return self._state.persona_states.get(persona_id)

    def checkpoint(self, checkpoint_id: Optional[str] = None) -> str:
        """
        Create a checkpoint of current state.

        Args:
            checkpoint_id: Optional checkpoint ID (auto-generated if None)

        Returns:
            Checkpoint ID
        """
        import hashlib
        import json

        with self._lock:
            # Generate checkpoint ID
            cp_id = checkpoint_id or f"cp_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

            # Compute checksum
            state_bytes = json.dumps(self._state.to_dict(), sort_keys=True).encode()
            self._state.checksum = hashlib.sha256(state_bytes).hexdigest()

            if self._checkpoint_manager:
                # Use CheckpointManager for atomic writes
                try:
                    from maestro_hive.maestro.state.checkpoint import WorkflowState, StateMetadata

                    workflow_state = WorkflowState(
                        workflow_id=self._workflow_id,
                        phase=self._state.phase,
                        step=self._state.step,
                        data=self._state.to_dict(),
                        metadata=StateMetadata(executor_version="2.1"),
                        checksum=self._state.checksum,
                    )

                    cp = self._checkpoint_manager.create_checkpoint(
                        workflow_id=self._workflow_id,
                        state=workflow_state,
                    )
                    logger.info(f"Checkpoint created via CheckpointManager: {cp.checkpoint_id}")
                    return cp.checkpoint_id
                except Exception as e:
                    logger.warning(f"CheckpointManager failed, using fallback: {e}")

            # Fallback: Direct file write
            cp_path = self._checkpoint_dir / f"{self._workflow_id}_{cp_id}.json"
            self._atomic_write(cp_path, state_bytes)
            logger.info(f"Checkpoint created: {cp_path}")
            return cp_id

    def _atomic_write(self, path: Path, data: bytes) -> None:
        """Atomically write data to file."""
        import tempfile

        # Write to temp file, then rename
        temp_fd, temp_path = tempfile.mkstemp(
            suffix=".tmp",
            dir=path.parent,
        )

        try:
            with os.fdopen(temp_fd, "wb") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            os.rename(temp_path, path)
        except Exception:
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            raise

    def restore(self, checkpoint_id: str) -> bool:
        """
        Restore state from a specific checkpoint.

        Args:
            checkpoint_id: Checkpoint to restore

        Returns:
            True if restoration successful
        """
        import json

        with self._lock:
            if self._checkpoint_manager:
                try:
                    cp = self._checkpoint_manager.get_checkpoint(
                        checkpoint_id,
                        workflow_id=self._workflow_id,
                        validate=self.state_config.verify_checksum_on_load,
                    )
                    self._state = ExecutionState.from_dict(cp.state.data)
                    logger.info(f"State restored from checkpoint: {checkpoint_id}")
                    return True
                except Exception as e:
                    logger.warning(f"CheckpointManager restore failed: {e}")

            # Fallback: Try loading from file
            cp_pattern = self._checkpoint_dir / f"{self._workflow_id}_{checkpoint_id}.json"
            if cp_pattern.exists():
                with open(cp_pattern, "rb") as f:
                    data = json.loads(f.read().decode())
                    self._state = ExecutionState.from_dict(data)
                    logger.info(f"State restored from file: {cp_pattern}")
                    return True

            return False

    def restore_latest(self) -> bool:
        """
        Restore state from the most recent checkpoint (AC-2).

        Returns:
            True if restoration successful
        """
        import json

        with self._lock:
            if self._checkpoint_manager:
                try:
                    latest = self._checkpoint_manager.get_latest_checkpoint(
                        self._workflow_id,
                        validate=self.state_config.verify_checksum_on_load,
                    )
                    if latest:
                        self._state = ExecutionState.from_dict(latest.state.data)
                        logger.info(f"State restored from latest checkpoint: {latest.checkpoint_id}")
                        return True
                except Exception as e:
                    logger.debug(f"No checkpoint found via manager: {e}")

            # Fallback: Find newest checkpoint file
            checkpoint_files = list(self._checkpoint_dir.glob(f"{self._workflow_id}_*.json"))
            if checkpoint_files:
                # Sort by modification time, newest first
                checkpoint_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
                try:
                    with open(checkpoint_files[0], "rb") as f:
                        data = json.loads(f.read().decode())
                        self._state = ExecutionState.from_dict(data)
                        logger.info(f"State restored from file: {checkpoint_files[0]}")
                        return True
                except Exception as e:
                    logger.warning(f"Failed to restore from file: {e}")

            return False

    def list_checkpoints(self) -> List[Dict[str, Any]]:
        """List all available checkpoints for this workflow."""
        checkpoints = []

        if self._checkpoint_manager:
            try:
                cps = self._checkpoint_manager.list_checkpoints(self._workflow_id)
                for cp in cps:
                    checkpoints.append({
                        "checkpoint_id": cp.checkpoint_id,
                        "version": cp.version,
                        "created_at": cp.created_at.isoformat() if hasattr(cp.created_at, 'isoformat') else str(cp.created_at),
                    })
            except Exception:
                pass

        # Also check for file-based checkpoints
        for cp_file in self._checkpoint_dir.glob(f"{self._workflow_id}_*.json"):
            cp_id = cp_file.stem.replace(f"{self._workflow_id}_", "")
            if not any(c["checkpoint_id"] == cp_id for c in checkpoints):
                checkpoints.append({
                    "checkpoint_id": cp_id,
                    "version": 0,
                    "created_at": datetime.fromtimestamp(cp_file.stat().st_mtime).isoformat(),
                })

        return sorted(checkpoints, key=lambda c: c["created_at"], reverse=True)

    def _start_auto_checkpoint(self) -> None:
        """Start automatic checkpointing at configured interval."""
        interval = self.state_config.auto_checkpoint_interval_seconds

        def checkpoint_task():
            try:
                self.checkpoint()
            except Exception as e:
                logger.warning(f"Auto-checkpoint failed: {e}")
            finally:
                if self.state_config.enable_persistence:
                    self._checkpoint_timer = threading.Timer(interval, checkpoint_task)
                    self._checkpoint_timer.daemon = True
                    self._checkpoint_timer.start()

        self._checkpoint_timer = threading.Timer(interval, checkpoint_task)
        self._checkpoint_timer.daemon = True
        self._checkpoint_timer.start()
        logger.debug(f"Auto-checkpoint started: interval={interval}s")

    def shutdown(self) -> None:
        """Gracefully shutdown state persistence."""
        if self._checkpoint_timer:
            self._checkpoint_timer.cancel()

        # Final checkpoint before shutdown
        try:
            self.checkpoint("shutdown")
        except Exception as e:
            logger.warning(f"Shutdown checkpoint failed: {e}")

        if self._state_manager:
            try:
                self._state_manager.shutdown()
            except Exception:
                pass

        logger.info(f"StatePersistence shutdown: workflow={self._workflow_id}")

    def __enter__(self) -> "StatePersistence":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.shutdown()


def get_state_persistence(
    workflow_id: Optional[str] = None,
    auto_restore: bool = True,
) -> StatePersistence:
    """
    Convenience function to get a StatePersistence instance.

    Args:
        workflow_id: Optional workflow ID
        auto_restore: Whether to auto-restore from checkpoint

    Returns:
        StatePersistence instance
    """
    return StatePersistence(workflow_id=workflow_id, auto_restore=auto_restore)


# AC-1 Convenience functions: save_state() and load_state()
def save_state(
    state: ExecutionState,
    workflow_id: Optional[str] = None,
    checkpoint: bool = True,
) -> str:
    """
    Save execution state to disk.

    AC-1: Create state_persistence.py with save_state() function.

    Args:
        state: ExecutionState to save
        workflow_id: Optional workflow ID (uses state.workflow_id if not provided)
        checkpoint: Whether to create a checkpoint (default True)

    Returns:
        Checkpoint ID if checkpoint=True, else workflow_id
    """
    wf_id = workflow_id or state.workflow_id
    persistence = StatePersistence(workflow_id=wf_id, auto_restore=False)
    persistence._state = state
    persistence._state.update()

    if checkpoint:
        return persistence.checkpoint()

    # Just update in-memory state manager if available
    if persistence._state_manager:
        persistence._state_manager.set_state(
            key=wf_id,
            value=state.to_dict(),
            namespace="workflows",
        )
    return wf_id


def load_state(workflow_id: str) -> Optional[ExecutionState]:
    """
    Load execution state from disk.

    AC-1: Create state_persistence.py with load_state() function.

    Args:
        workflow_id: Workflow ID to load state for

    Returns:
        ExecutionState if found, None otherwise
    """
    persistence = StatePersistence(workflow_id=workflow_id, auto_restore=True)
    if persistence._state and persistence._state.workflow_id == workflow_id:
        return persistence._state
    return None
