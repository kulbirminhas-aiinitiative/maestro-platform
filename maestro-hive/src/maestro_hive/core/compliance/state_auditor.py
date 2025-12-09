"""
State Compliance Auditor: State checkpoint integrity validation.

EPIC: MD-2801 - Core Services & CLI Compliance (Batch 2)
AC-4: State Manager Compliance

Provides integrity validation for StateManager checkpoints,
ensuring state consistency and detecting tampering.
"""

import hashlib
import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import threading

logger = logging.getLogger(__name__)


class IntegrityStatus(Enum):
    """Checkpoint integrity status."""
    VALID = "valid"
    MODIFIED = "modified"
    CORRUPTED = "corrupted"
    MISSING = "missing"
    UNKNOWN = "unknown"


@dataclass
class AuditResult:
    """Result of a state audit."""
    checkpoint_id: str
    timestamp: str
    status: IntegrityStatus
    expected_hash: Optional[str] = None
    actual_hash: Optional[str] = None
    discrepancies: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = asdict(self)
        result["status"] = self.status.value
        return result


class StateComplianceAuditor:
    """
    State checkpoint integrity validation service.

    Provides:
    - Checkpoint hash verification
    - State consistency checks
    - Tamper detection
    - Compliance reporting for state operations

    Thread-safe implementation with checkpoint history tracking.
    """

    def __init__(
        self,
        hash_algorithm: str = "sha256",
        track_history: bool = True,
        max_history: int = 1000,
        enabled: bool = True
    ):
        """
        Initialize the state compliance auditor.

        Args:
            hash_algorithm: Hash algorithm for integrity checks
            track_history: Whether to track checkpoint history
            max_history: Maximum history entries to keep
            enabled: Whether auditing is active
        """
        self._hash_algorithm = hash_algorithm
        self._track_history = track_history
        self._max_history = max_history
        self._enabled = enabled
        self._lock = threading.RLock()
        self._checkpoint_hashes: Dict[str, str] = {}  # checkpoint_id -> hash
        self._audit_history: List[AuditResult] = []

        logger.info(f"StateComplianceAuditor initialized with {hash_algorithm}")

    def _compute_hash(self, data: Any) -> str:
        """Compute hash of data."""
        if isinstance(data, dict):
            # Sort keys for consistent hashing
            serialized = json.dumps(data, sort_keys=True, default=str)
        else:
            serialized = str(data)

        if self._hash_algorithm == "sha256":
            return hashlib.sha256(serialized.encode()).hexdigest()
        elif self._hash_algorithm == "sha512":
            return hashlib.sha512(serialized.encode()).hexdigest()
        elif self._hash_algorithm == "md5":
            return hashlib.md5(serialized.encode()).hexdigest()
        else:
            return hashlib.sha256(serialized.encode()).hexdigest()

    def register_checkpoint(
        self,
        checkpoint_id: str,
        state_snapshot: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Register a checkpoint and compute its integrity hash.

        Args:
            checkpoint_id: Unique checkpoint identifier
            state_snapshot: The state data to protect
            metadata: Optional additional metadata

        Returns:
            Computed hash for the checkpoint
        """
        if not self._enabled:
            return ""

        with self._lock:
            hash_value = self._compute_hash(state_snapshot)
            self._checkpoint_hashes[checkpoint_id] = hash_value

            logger.debug(f"Registered checkpoint {checkpoint_id}: {hash_value[:16]}...")
            return hash_value

    def audit_checkpoint(
        self,
        checkpoint_id: str,
        current_state: Dict[str, Any]
    ) -> AuditResult:
        """
        Audit a checkpoint for integrity.

        Args:
            checkpoint_id: Checkpoint to audit
            current_state: Current state to verify

        Returns:
            AuditResult with integrity status
        """
        if not self._enabled:
            return AuditResult(
                checkpoint_id=checkpoint_id,
                timestamp=datetime.utcnow().isoformat(),
                status=IntegrityStatus.UNKNOWN,
                metadata={"auditing_disabled": True}
            )

        with self._lock:
            expected_hash = self._checkpoint_hashes.get(checkpoint_id)

            if not expected_hash:
                result = AuditResult(
                    checkpoint_id=checkpoint_id,
                    timestamp=datetime.utcnow().isoformat(),
                    status=IntegrityStatus.MISSING,
                    recommendations=["Register checkpoint before auditing"]
                )
            else:
                actual_hash = self._compute_hash(current_state)
                
                if actual_hash == expected_hash:
                    status = IntegrityStatus.VALID
                    discrepancies = []
                    recommendations = []
                else:
                    status = IntegrityStatus.MODIFIED
                    discrepancies = ["State hash mismatch detected"]
                    recommendations = [
                        "Investigate state changes since checkpoint",
                        "Consider restoring from known-good checkpoint"
                    ]

                result = AuditResult(
                    checkpoint_id=checkpoint_id,
                    timestamp=datetime.utcnow().isoformat(),
                    status=status,
                    expected_hash=expected_hash,
                    actual_hash=actual_hash,
                    discrepancies=discrepancies,
                    recommendations=recommendations,
                )

            # Track history
            if self._track_history:
                self._audit_history.append(result)
                if len(self._audit_history) > self._max_history:
                    self._audit_history = self._audit_history[-self._max_history:]

            logger.info(
                f"Audit checkpoint {checkpoint_id}: status={result.status.value}"
            )
            return result

    def validate_integrity(self, state: Dict[str, Any]) -> bool:
        """
        Simple integrity check for state data.

        Args:
            state: State dictionary to validate

        Returns:
            True if state appears valid
        """
        if not self._enabled:
            return True

        try:
            # Check if state is valid JSON-serializable
            json.dumps(state, default=str)

            # Check for required structure
            if not isinstance(state, dict):
                return False

            # Check for suspicious patterns
            state_str = json.dumps(state, default=str)
            suspicious = [
                "__import__",
                "eval(",
                "exec(",
                "compile(",
                "open(",
            ]
            if any(s in state_str for s in suspicious):
                logger.warning("Suspicious pattern detected in state")
                return False

            return True

        except (TypeError, ValueError) as e:
            logger.warning(f"State validation failed: {e}")
            return False

    def generate_compliance_hash(self, state: Dict[str, Any]) -> str:
        """
        Generate a compliance hash for state.

        This creates a hash that includes metadata about the state
        for regulatory compliance purposes.

        Args:
            state: State to hash

        Returns:
            Compliance hash string
        """
        if not self._enabled:
            return ""

        compliance_data = {
            "state": state,
            "timestamp": datetime.utcnow().isoformat(),
            "algorithm": self._hash_algorithm,
            "version": "1.0",
        }

        return self._compute_hash(compliance_data)

    def get_audit_history(
        self,
        checkpoint_id: Optional[str] = None,
        status: Optional[IntegrityStatus] = None,
        limit: int = 100
    ) -> List[AuditResult]:
        """
        Get audit history with optional filtering.

        Args:
            checkpoint_id: Filter by checkpoint
            status: Filter by status
            limit: Maximum results

        Returns:
            List of audit results
        """
        with self._lock:
            results = self._audit_history.copy()

            if checkpoint_id:
                results = [r for r in results if r.checkpoint_id == checkpoint_id]

            if status:
                results = [r for r in results if r.status == status]

            return results[-limit:]

    def verify_checkpoint_chain(
        self,
        checkpoint_ids: List[str],
        states: List[Dict[str, Any]]
    ) -> Dict[str, AuditResult]:
        """
        Verify a chain of checkpoints.

        Args:
            checkpoint_ids: List of checkpoint IDs in order
            states: Corresponding states for each checkpoint

        Returns:
            Dictionary mapping checkpoint_id to AuditResult
        """
        if len(checkpoint_ids) != len(states):
            raise ValueError("checkpoint_ids and states must have same length")

        results = {}
        for cp_id, state in zip(checkpoint_ids, states):
            results[cp_id] = self.audit_checkpoint(cp_id, state)

        return results

    def get_statistics(self) -> Dict[str, Any]:
        """Get auditor statistics."""
        with self._lock:
            history = self._audit_history
            return {
                "total_checkpoints": len(self._checkpoint_hashes),
                "total_audits": len(history),
                "valid_count": sum(1 for r in history if r.status == IntegrityStatus.VALID),
                "modified_count": sum(1 for r in history if r.status == IntegrityStatus.MODIFIED),
                "missing_count": sum(1 for r in history if r.status == IntegrityStatus.MISSING),
                "hash_algorithm": self._hash_algorithm,
                "enabled": self._enabled,
            }

    def clear_checkpoint(self, checkpoint_id: str) -> bool:
        """Remove a checkpoint from tracking."""
        with self._lock:
            if checkpoint_id in self._checkpoint_hashes:
                del self._checkpoint_hashes[checkpoint_id]
                logger.debug(f"Cleared checkpoint: {checkpoint_id}")
                return True
            return False

    def enable(self) -> None:
        """Enable auditing."""
        self._enabled = True
        logger.info("State compliance auditing enabled")

    def disable(self) -> None:
        """Disable auditing."""
        self._enabled = False
        logger.info("State compliance auditing disabled")

    @property
    def is_enabled(self) -> bool:
        """Check if auditing is enabled."""
        return self._enabled


def get_state_auditor(**kwargs) -> StateComplianceAuditor:
    """Get a StateComplianceAuditor instance."""
    return StateComplianceAuditor(**kwargs)
