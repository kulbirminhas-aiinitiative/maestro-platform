"""
Rollback Manager - Central coordinator for rollback operations

EPIC: MD-2527 - AC-2: Rollback execution on failure

Manages checkpoint creation, rollback execution, and coordination
between executor and notification components.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from .checkpoint import CheckpointStore, PhaseCheckpoint
from .executor import RollbackExecutor
from .notifications import RecoveryNotificationService, NotificationLevel

logger = logging.getLogger(__name__)


class RollbackResult(Enum):
    """Result of rollback operation."""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    NO_CHECKPOINT = "no_checkpoint"


@dataclass
class RollbackReport:
    """Report of rollback operation results."""
    result: RollbackResult
    execution_id: str
    checkpoint_id: Optional[str]
    phase_name: Optional[str]
    artifacts_cleaned: List[str]
    artifacts_failed: List[str]
    error_message: Optional[str] = None
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "result": self.result.value,
            "execution_id": self.execution_id,
            "checkpoint_id": self.checkpoint_id,
            "phase_name": self.phase_name,
            "artifacts_cleaned": self.artifacts_cleaned,
            "artifacts_failed": self.artifacts_failed,
            "error_message": self.error_message,
            "duration_ms": self.duration_ms,
        }


class RollbackManager:
    """
    Central manager for rollback operations.

    Coordinates:
    - Checkpoint creation before phases
    - Rollback execution on failure
    - Artifact cleanup
    - Recovery notifications
    """

    def __init__(
        self,
        checkpoint_dir: str = "/tmp/maestro/checkpoints",
        enable_notifications: bool = True,
        notification_webhook: Optional[str] = None,
    ):
        """
        Initialize rollback manager.

        Args:
            checkpoint_dir: Directory for checkpoint storage
            enable_notifications: Whether to send recovery notifications
            notification_webhook: Webhook URL for notifications
        """
        self.checkpoint_store = CheckpointStore(checkpoint_dir)
        self.executor = RollbackExecutor()
        self.notification_service = RecoveryNotificationService(
            webhook_url=notification_webhook,
            enabled=enable_notifications,
        )
        self._phase_handlers: Dict[str, Callable] = {}
        logger.info("RollbackManager initialized")

    def register_phase_handler(
        self,
        phase_name: str,
        handler: Callable[[PhaseCheckpoint], bool],
    ) -> None:
        """
        Register custom rollback handler for a phase.

        Args:
            phase_name: Name of the phase
            handler: Function to execute during rollback for this phase
        """
        self._phase_handlers[phase_name] = handler
        logger.debug(f"Registered rollback handler for phase: {phase_name}")

    def create_checkpoint(
        self,
        execution_id: str,
        phase_name: str,
        phase_index: int,
        state: Dict[str, Any],
        artifacts_created: Optional[List[str]] = None,
        confluence_pages: Optional[List[str]] = None,
        jira_comments: Optional[List[str]] = None,
        files_created: Optional[List[str]] = None,
    ) -> PhaseCheckpoint:
        """
        Create checkpoint before phase execution.

        Args:
            execution_id: Execution identifier
            phase_name: Name of the phase
            phase_index: Index of the phase (0-based)
            state: Current execution state
            artifacts_created: List of artifact paths created
            confluence_pages: List of Confluence page IDs created
            jira_comments: List of JIRA comment IDs added
            files_created: List of file paths created

        Returns:
            Created PhaseCheckpoint
        """
        checkpoint_id = f"ckpt-{phase_index:02d}-{uuid.uuid4().hex[:8]}"

        checkpoint = PhaseCheckpoint(
            checkpoint_id=checkpoint_id,
            execution_id=execution_id,
            phase_name=phase_name,
            phase_index=phase_index,
            timestamp=datetime.utcnow(),
            state=state,
            artifacts_created=artifacts_created or [],
            confluence_pages=confluence_pages or [],
            jira_comments=jira_comments or [],
            files_created=files_created or [],
        )

        self.checkpoint_store.save(checkpoint)
        logger.info(f"Created checkpoint {checkpoint_id} for phase {phase_name}")

        return checkpoint

    def rollback_to_checkpoint(
        self,
        execution_id: str,
        checkpoint_id: str,
        reason: Optional[str] = None,
    ) -> RollbackReport:
        """
        Rollback execution to a specific checkpoint.

        Args:
            execution_id: Execution identifier
            checkpoint_id: Checkpoint to rollback to
            reason: Reason for rollback

        Returns:
            RollbackReport with results
        """
        start_time = datetime.utcnow()
        logger.info(f"Starting rollback to checkpoint {checkpoint_id}")

        # Load target checkpoint
        checkpoint = self.checkpoint_store.load(execution_id, checkpoint_id)
        if not checkpoint:
            return RollbackReport(
                result=RollbackResult.NO_CHECKPOINT,
                execution_id=execution_id,
                checkpoint_id=checkpoint_id,
                phase_name=None,
                artifacts_cleaned=[],
                artifacts_failed=[],
                error_message="Checkpoint not found or corrupted",
            )

        # Get all checkpoints after this one
        all_checkpoints = self.checkpoint_store.list_checkpoints(execution_id)
        checkpoints_to_rollback = [
            c for c in all_checkpoints
            if c.phase_index > checkpoint.phase_index
        ]

        artifacts_cleaned = []
        artifacts_failed = []
        errors = []

        # Rollback in reverse order (newest first)
        for ckpt in reversed(checkpoints_to_rollback):
            try:
                # Execute custom handler if registered
                if ckpt.phase_name in self._phase_handlers:
                    handler = self._phase_handlers[ckpt.phase_name]
                    try:
                        handler(ckpt)
                    except Exception as e:
                        logger.warning(f"Phase handler failed for {ckpt.phase_name}: {e}")
                        errors.append(f"Handler {ckpt.phase_name}: {e}")

                # Clean up artifacts from this phase
                result = self.executor.cleanup_checkpoint_artifacts(ckpt)
                artifacts_cleaned.extend(result.get("cleaned", []))
                artifacts_failed.extend(result.get("failed", []))

                # Delete the checkpoint
                self.checkpoint_store.delete_checkpoint(execution_id, ckpt.checkpoint_id)

            except Exception as e:
                logger.error(f"Error rolling back checkpoint {ckpt.checkpoint_id}: {e}")
                errors.append(str(e))

        # Determine result
        if artifacts_failed or errors:
            result = RollbackResult.PARTIAL if artifacts_cleaned else RollbackResult.FAILED
        else:
            result = RollbackResult.SUCCESS

        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        report = RollbackReport(
            result=result,
            execution_id=execution_id,
            checkpoint_id=checkpoint_id,
            phase_name=checkpoint.phase_name,
            artifacts_cleaned=artifacts_cleaned,
            artifacts_failed=artifacts_failed,
            error_message="; ".join(errors) if errors else None,
            duration_ms=duration_ms,
        )

        # Send notification
        self._notify_rollback(report, reason)

        logger.info(f"Rollback completed: {result.value} ({duration_ms:.2f}ms)")
        return report

    def rollback_to_latest(
        self,
        execution_id: str,
        reason: Optional[str] = None,
    ) -> RollbackReport:
        """
        Rollback to the most recent checkpoint.

        Args:
            execution_id: Execution identifier
            reason: Reason for rollback

        Returns:
            RollbackReport with results
        """
        checkpoint = self.checkpoint_store.get_latest_checkpoint(execution_id)
        if not checkpoint:
            return RollbackReport(
                result=RollbackResult.NO_CHECKPOINT,
                execution_id=execution_id,
                checkpoint_id=None,
                phase_name=None,
                artifacts_cleaned=[],
                artifacts_failed=[],
                error_message="No checkpoints found for execution",
            )

        return self.rollback_to_checkpoint(
            execution_id,
            checkpoint.checkpoint_id,
            reason=reason,
        )

    def rollback_current_phase(
        self,
        execution_id: str,
        current_phase_index: int,
        reason: Optional[str] = None,
    ) -> RollbackReport:
        """
        Rollback only the current (failed) phase.

        Args:
            execution_id: Execution identifier
            current_phase_index: Index of the current/failed phase
            reason: Reason for rollback

        Returns:
            RollbackReport with results
        """
        # Find checkpoint for previous phase
        checkpoints = self.checkpoint_store.list_checkpoints(execution_id)
        target_checkpoint = None

        for ckpt in checkpoints:
            if ckpt.phase_index == current_phase_index - 1:
                target_checkpoint = ckpt
                break

        if not target_checkpoint:
            # No previous checkpoint, rollback everything
            return self.rollback_to_latest(execution_id, reason)

        return self.rollback_to_checkpoint(
            execution_id,
            target_checkpoint.checkpoint_id,
            reason=reason,
        )

    def get_recovery_state(
        self,
        execution_id: str,
        checkpoint_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get state from a checkpoint for recovery.

        Args:
            execution_id: Execution identifier
            checkpoint_id: Specific checkpoint or None for latest

        Returns:
            State dictionary or None
        """
        if checkpoint_id:
            checkpoint = self.checkpoint_store.load(execution_id, checkpoint_id)
        else:
            checkpoint = self.checkpoint_store.get_latest_checkpoint(execution_id)

        if checkpoint:
            return checkpoint.state
        return None

    def cleanup_execution(self, execution_id: str) -> int:
        """
        Clean up all checkpoints for an execution.

        Args:
            execution_id: Execution identifier

        Returns:
            Number of checkpoints cleaned
        """
        count = self.checkpoint_store.cleanup_execution(execution_id)
        logger.info(f"Cleaned up {count} checkpoints for execution {execution_id}")
        return count

    def _notify_rollback(
        self,
        report: RollbackReport,
        reason: Optional[str],
    ) -> None:
        """Send rollback notification."""
        level = (
            NotificationLevel.WARNING
            if report.result == RollbackResult.SUCCESS
            else NotificationLevel.ERROR
        )

        message = f"Rollback {report.result.value}: {report.execution_id}"
        if reason:
            message += f" - {reason}"

        self.notification_service.notify(
            level=level,
            title=f"Rollback {report.result.value.upper()}",
            message=message,
            details=report.to_dict(),
        )
