"""
State Recovery - Automatic checkpoint detection and recovery

EPIC: MD-2514 - AC-3: State recovery with automatic checkpoint detection

Provides:
- Automatic latest checkpoint detection
- Checkpoint validation before recovery
- Recovery callbacks for state restoration
- Dry-run recovery capability
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from .checkpoint import (
    Checkpoint,
    CheckpointManager,
    CheckpointNotFoundError,
    ChecksumValidationError,
    WorkflowState,
)

logger = logging.getLogger(__name__)


class RecoveryError(Exception):
    """Base exception for recovery errors."""
    pass


class NoCheckpointAvailable(RecoveryError):
    """Raised when no valid checkpoint is available for recovery."""
    pass


class RecoveryValidationError(RecoveryError):
    """Raised when recovered state fails validation."""
    pass


@dataclass
class RecoveryResult:
    """
    Result of a recovery operation.

    Attributes:
        success: Whether recovery succeeded
        workflow_id: Recovered workflow ID
        checkpoint: Checkpoint used for recovery
        recovered_state: The recovered workflow state
        validation_passed: Whether state validation passed
        recovery_time_ms: Time taken for recovery in milliseconds
        message: Human-readable status message
    """
    success: bool
    workflow_id: str
    checkpoint: Optional[Checkpoint]
    recovered_state: Optional[WorkflowState]
    validation_passed: bool
    recovery_time_ms: float
    message: str


class StateRecovery:
    """
    Handles automatic state recovery from checkpoints.

    Features:
    - Automatic latest checkpoint detection
    - Checksum validation before recovery
    - Recovery callbacks for custom state restoration
    - Dry-run mode for testing
    """

    def __init__(
        self,
        checkpoint_manager: Optional[CheckpointManager] = None,
        storage_path: str = "/var/maestro/checkpoints",
        auto_validate: bool = True,
    ):
        """
        Initialize state recovery.

        Args:
            checkpoint_manager: CheckpointManager instance (creates default if None)
            storage_path: Storage path for checkpoints (if creating manager)
            auto_validate: Automatically validate checkpoints before recovery
        """
        self._checkpoint_manager = checkpoint_manager or CheckpointManager(
            storage_path=storage_path,
        )
        self._auto_validate = auto_validate
        self._recovery_callbacks: List[Callable[[WorkflowState], None]] = []
        self._validators: List[Callable[[WorkflowState], bool]] = []

    def register_callback(
        self,
        callback: Callable[[WorkflowState], None],
    ) -> None:
        """
        Register a callback to be called after successful recovery.

        Args:
            callback: Function that receives recovered state
        """
        self._recovery_callbacks.append(callback)

    def register_validator(
        self,
        validator: Callable[[WorkflowState], bool],
    ) -> None:
        """
        Register a validator for recovered states.

        Validators return True if state is valid, False otherwise.

        Args:
            validator: Validation function
        """
        self._validators.append(validator)

    def can_recover(self, workflow_id: str) -> bool:
        """
        Check if recovery is possible for a workflow.

        Args:
            workflow_id: Workflow identifier

        Returns:
            True if at least one valid checkpoint exists
        """
        try:
            checkpoint = self._checkpoint_manager.get_latest_checkpoint(
                workflow_id,
                validate=self._auto_validate,
            )
            return checkpoint is not None
        except (CheckpointNotFoundError, ChecksumValidationError):
            return False

    def find_recoverable_workflows(self) -> List[str]:
        """
        Find all workflows that have valid checkpoints.

        Returns:
            List of workflow IDs with recoverable checkpoints
        """
        recoverable = []
        storage_path = self._checkpoint_manager._storage_path

        for wf_dir in storage_path.iterdir():
            if wf_dir.is_dir():
                workflow_id = wf_dir.name
                if self.can_recover(workflow_id):
                    recoverable.append(workflow_id)

        return recoverable

    def _validate_state(self, state: WorkflowState) -> bool:
        """
        Run all validators on recovered state.

        Args:
            state: Recovered workflow state

        Returns:
            True if all validators pass
        """
        for validator in self._validators:
            try:
                if not validator(state):
                    return False
            except Exception as e:
                logger.warning(f"Validator raised exception: {e}")
                return False
        return True

    def _run_callbacks(self, state: WorkflowState) -> None:
        """
        Execute recovery callbacks.

        Args:
            state: Recovered workflow state
        """
        for callback in self._recovery_callbacks:
            try:
                callback(state)
            except Exception as e:
                logger.error(f"Recovery callback error: {e}")

    def recover(
        self,
        workflow_id: str,
        version: Optional[int] = None,
        dry_run: bool = False,
    ) -> RecoveryResult:
        """
        Recover workflow state from checkpoint.

        Args:
            workflow_id: Workflow to recover
            version: Specific version (None for latest)
            dry_run: If True, only validate without callbacks

        Returns:
            RecoveryResult with recovery details

        Raises:
            NoCheckpointAvailable: If no valid checkpoint found
            RecoveryValidationError: If state validation fails
        """
        start_time = datetime.utcnow()

        try:
            # Get checkpoint
            if version is not None:
                # Find specific version
                checkpoints = self._checkpoint_manager.list_checkpoints(
                    workflow_id
                )
                checkpoint = None
                for cp in checkpoints:
                    if cp.version == version:
                        checkpoint = self._checkpoint_manager.get_checkpoint(
                            cp.checkpoint_id,
                            workflow_id,
                            validate=self._auto_validate,
                        )
                        break

                if checkpoint is None:
                    raise NoCheckpointAvailable(
                        f"Version {version} not found for workflow {workflow_id}"
                    )
            else:
                # Get latest
                checkpoint = self._checkpoint_manager.get_latest_checkpoint(
                    workflow_id,
                    validate=self._auto_validate,
                )

                if checkpoint is None:
                    raise NoCheckpointAvailable(
                        f"No checkpoints found for workflow {workflow_id}"
                    )

            # Validate state
            validation_passed = self._validate_state(checkpoint.state)

            if not validation_passed:
                raise RecoveryValidationError(
                    f"State validation failed for workflow {workflow_id}"
                )

            # Run callbacks (unless dry run)
            if not dry_run:
                self._run_callbacks(checkpoint.state)

            end_time = datetime.utcnow()
            duration_ms = (end_time - start_time).total_seconds() * 1000

            logger.info(
                f"{'Dry-run r' if dry_run else 'R'}ecovered workflow "
                f"{workflow_id} from checkpoint v{checkpoint.version} "
                f"in {duration_ms:.1f}ms"
            )

            return RecoveryResult(
                success=True,
                workflow_id=workflow_id,
                checkpoint=checkpoint,
                recovered_state=checkpoint.state,
                validation_passed=validation_passed,
                recovery_time_ms=duration_ms,
                message=(
                    f"Successfully {'validated' if dry_run else 'recovered'} "
                    f"from checkpoint v{checkpoint.version}"
                ),
            )

        except (CheckpointNotFoundError, NoCheckpointAvailable) as e:
            end_time = datetime.utcnow()
            duration_ms = (end_time - start_time).total_seconds() * 1000

            logger.warning(f"Recovery failed for {workflow_id}: {e}")

            return RecoveryResult(
                success=False,
                workflow_id=workflow_id,
                checkpoint=None,
                recovered_state=None,
                validation_passed=False,
                recovery_time_ms=duration_ms,
                message=str(e),
            )

        except ChecksumValidationError as e:
            end_time = datetime.utcnow()
            duration_ms = (end_time - start_time).total_seconds() * 1000

            logger.error(f"Checksum validation failed for {workflow_id}: {e}")

            return RecoveryResult(
                success=False,
                workflow_id=workflow_id,
                checkpoint=None,
                recovered_state=None,
                validation_passed=False,
                recovery_time_ms=duration_ms,
                message=f"Checksum validation failed: {e}",
            )

        except RecoveryValidationError as e:
            end_time = datetime.utcnow()
            duration_ms = (end_time - start_time).total_seconds() * 1000

            logger.error(f"State validation failed for {workflow_id}: {e}")

            return RecoveryResult(
                success=False,
                workflow_id=workflow_id,
                checkpoint=checkpoint if 'checkpoint' in locals() else None,
                recovered_state=None,
                validation_passed=False,
                recovery_time_ms=duration_ms,
                message=str(e),
            )

    def recover_all(
        self,
        dry_run: bool = False,
    ) -> Dict[str, RecoveryResult]:
        """
        Recover all workflows with valid checkpoints.

        Args:
            dry_run: If True, only validate without callbacks

        Returns:
            Dict mapping workflow IDs to RecoveryResult
        """
        results = {}
        workflow_ids = self.find_recoverable_workflows()

        for workflow_id in workflow_ids:
            results[workflow_id] = self.recover(workflow_id, dry_run=dry_run)

        successful = sum(1 for r in results.values() if r.success)
        logger.info(
            f"Recovered {successful}/{len(results)} workflows "
            f"{'(dry run)' if dry_run else ''}"
        )

        return results

    def get_recovery_info(
        self,
        workflow_id: str,
    ) -> Dict[str, Any]:
        """
        Get information about recovery options for a workflow.

        Args:
            workflow_id: Workflow identifier

        Returns:
            Dict with recovery information
        """
        checkpoints = self._checkpoint_manager.list_checkpoints(workflow_id)

        if not checkpoints:
            return {
                "workflow_id": workflow_id,
                "recoverable": False,
                "checkpoints": [],
                "latest_version": None,
                "message": "No checkpoints available",
            }

        latest = max(checkpoints, key=lambda cp: cp.version)

        return {
            "workflow_id": workflow_id,
            "recoverable": True,
            "checkpoints": [
                {
                    "checkpoint_id": cp.checkpoint_id,
                    "version": cp.version,
                    "created_at": cp.created_at.isoformat(),
                    "phase": cp.state.phase,
                    "step": cp.state.step,
                    "expired": cp.is_expired(),
                }
                for cp in checkpoints
            ],
            "latest_version": latest.version,
            "latest_checkpoint_id": latest.checkpoint_id,
            "message": f"Can recover to v{latest.version}",
        }
