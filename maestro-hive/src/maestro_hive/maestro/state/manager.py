"""
State Manager - Central coordinator for state operations

EPIC: MD-2528 - AC-4: State recovery on restart

Unified state management with recovery capabilities.
"""

import logging
import os
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from .json_backend import JSONStateStore
from .postgres_backend import PostgreSQLStateStore
from .store import StateEntry, StateStore
from .sync import StateSync, SyncEvent
from .versioning import StateVersioning

logger = logging.getLogger(__name__)


class StateManager:
    """
    Central state management coordinator.

    Provides unified interface for:
    - State persistence (JSON or PostgreSQL)
    - State synchronization between components
    - Version history and rollback
    - Recovery on restart
    """

    def __init__(
        self,
        component_id: str,
        backend: str = "json",
        state_dir: str = "/tmp/maestro/state",
        db_connection: Optional[str] = None,
        enable_sync: bool = True,
        sync_interval: float = 5.0,
        max_versions: int = 100,
    ):
        """
        Initialize state manager.

        Args:
            component_id: Unique ID for this component
            backend: Storage backend (json, postgresql)
            state_dir: Directory for JSON state files
            db_connection: PostgreSQL connection string
            enable_sync: Enable background synchronization
            sync_interval: Sync interval in seconds
            max_versions: Maximum versions to retain
        """
        self.component_id = component_id
        self.backend_type = backend

        # Initialize store
        if backend == "postgresql" and db_connection:
            self.store: StateStore = PostgreSQLStateStore(
                connection_string=db_connection,
            )
            if not self.store.is_available():
                logger.warning("PostgreSQL not available, falling back to JSON")
                self.store = JSONStateStore(state_dir=state_dir)
                self.backend_type = "json"
        else:
            self.store = JSONStateStore(
                state_dir=state_dir,
                max_versions=max_versions,
            )

        # Initialize versioning
        self.versioning = StateVersioning(
            store=self.store,
            max_versions=max_versions,
        )

        # Initialize sync
        self.sync: Optional[StateSync] = None
        if enable_sync:
            self.sync = StateSync(
                store=self.store,
                component_id=component_id,
                sync_interval=sync_interval,
            )

        # Recovery state
        self._recovery_handlers: List[Callable[[str, StateEntry], None]] = []

        logger.info(
            f"StateManager initialized (component={component_id}, backend={self.backend_type})"
        )

    def start(self) -> None:
        """Start state manager (sync thread, etc.)."""
        if self.sync:
            self.sync.start()
        logger.info("StateManager started")

    def stop(self) -> None:
        """Stop state manager."""
        if self.sync:
            self.sync.stop()
        logger.info("StateManager stopped")

    # Core state operations

    def save(
        self,
        key: str,
        value: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> StateEntry:
        """
        Save state.

        Args:
            key: State key
            value: State data
            metadata: Optional metadata

        Returns:
            StateEntry with version
        """
        if self.sync:
            return self.sync.publish_update(key, value, metadata)
        else:
            return self.store.save(
                key=key,
                value=value,
                component_id=self.component_id,
                metadata=metadata,
            )

    def load(
        self,
        key: str,
        version: Optional[int] = None,
    ) -> Optional[StateEntry]:
        """
        Load state.

        Args:
            key: State key
            version: Specific version or None for latest

        Returns:
            StateEntry or None
        """
        return self.store.load(key, version)

    def get_value(
        self,
        key: str,
        default: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get state value only (convenience method).

        Args:
            key: State key
            default: Default value if not found

        Returns:
            State value dict or default
        """
        entry = self.store.load(key)
        return entry.value if entry else default

    def delete(self, key: str) -> bool:
        """Delete state."""
        return self.store.delete(key)

    def exists(self, key: str) -> bool:
        """Check if state exists."""
        return self.store.exists(key)

    def list_keys(self, prefix: Optional[str] = None) -> List[str]:
        """List state keys."""
        return self.store.list_keys(prefix)

    # Execution state convenience methods

    def save_execution_state(
        self,
        execution_id: str,
        state: Dict[str, Any],
    ) -> StateEntry:
        """
        Save execution state.

        Args:
            execution_id: Execution identifier
            state: Execution state data

        Returns:
            StateEntry
        """
        key = f"execution/{execution_id}"
        return self.save(
            key=key,
            value=state,
            metadata={"type": "execution_state"},
        )

    def load_execution_state(
        self,
        execution_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Load execution state.

        Args:
            execution_id: Execution identifier

        Returns:
            State dict or None
        """
        key = f"execution/{execution_id}"
        entry = self.load(key)
        return entry.value if entry else None

    def save_phase_state(
        self,
        execution_id: str,
        phase_name: str,
        state: Dict[str, Any],
    ) -> StateEntry:
        """
        Save phase state within execution.

        Args:
            execution_id: Execution identifier
            phase_name: Phase name
            state: Phase state data

        Returns:
            StateEntry
        """
        key = f"execution/{execution_id}/phase/{phase_name}"
        return self.save(
            key=key,
            value=state,
            metadata={"type": "phase_state", "phase": phase_name},
        )

    def load_phase_state(
        self,
        execution_id: str,
        phase_name: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Load phase state.

        Args:
            execution_id: Execution identifier
            phase_name: Phase name

        Returns:
            State dict or None
        """
        key = f"execution/{execution_id}/phase/{phase_name}"
        entry = self.load(key)
        return entry.value if entry else None

    # Versioning and history

    def get_history(
        self,
        key: str,
        limit: Optional[int] = None,
    ) -> List[StateEntry]:
        """Get version history."""
        return self.versioning.get_history(key, limit)

    def rollback(
        self,
        key: str,
        to_version: int,
    ) -> Optional[StateEntry]:
        """Rollback to previous version."""
        return self.versioning.rollback(
            key=key,
            to_version=to_version,
            component_id=self.component_id,
        )

    def compare_versions(
        self,
        key: str,
        from_version: int,
        to_version: int,
    ):
        """Compare two versions."""
        return self.versioning.compare_versions(key, from_version, to_version)

    # Recovery

    def register_recovery_handler(
        self,
        handler: Callable[[str, StateEntry], None],
    ) -> None:
        """
        Register handler for state recovery.

        Handler receives (execution_id, state_entry) on recovery.

        Args:
            handler: Recovery handler function
        """
        self._recovery_handlers.append(handler)

    def recover_state(
        self,
        execution_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Recover state for an execution.

        Args:
            execution_id: Execution identifier

        Returns:
            Recovered state or None
        """
        state = self.load_execution_state(execution_id)

        if state:
            entry = self.load(f"execution/{execution_id}")
            if entry:
                for handler in self._recovery_handlers:
                    try:
                        handler(execution_id, entry)
                    except Exception as e:
                        logger.error(f"Recovery handler error: {e}")

            logger.info(f"Recovered state for execution {execution_id}")

        return state

    def find_recoverable_executions(self) -> List[str]:
        """
        Find executions that can be recovered.

        Returns:
            List of execution IDs with saved state
        """
        keys = self.list_keys(prefix="execution/")
        execution_ids = set()

        for key in keys:
            # Extract execution ID from key
            parts = key.split("/")
            if len(parts) >= 2:
                execution_ids.add(parts[1])

        return list(execution_ids)

    def recover_all_active(self) -> Dict[str, Dict[str, Any]]:
        """
        Recover all active execution states.

        Returns:
            Dict mapping execution IDs to their states
        """
        recovered = {}
        execution_ids = self.find_recoverable_executions()

        for exec_id in execution_ids:
            state = self.recover_state(exec_id)
            if state:
                recovered[exec_id] = state

        logger.info(f"Recovered {len(recovered)} execution states")
        return recovered

    # Subscription

    def subscribe(
        self,
        key_pattern: str,
        callback: Callable[[SyncEvent], None],
    ) -> None:
        """Subscribe to state changes."""
        if self.sync:
            self.sync.subscribe(key_pattern, callback)
        else:
            logger.warning("Sync not enabled - subscription ignored")

    def unsubscribe(
        self,
        key_pattern: str,
        callback: Callable[[SyncEvent], None],
    ) -> None:
        """Unsubscribe from state changes."""
        if self.sync:
            self.sync.unsubscribe(key_pattern, callback)

    # Snapshot and export

    def create_snapshot(
        self,
        execution_id: Optional[str] = None,
    ) -> Dict[str, StateEntry]:
        """
        Create snapshot of state.

        Args:
            execution_id: Specific execution or None for all

        Returns:
            Snapshot dict
        """
        prefix = f"execution/{execution_id}" if execution_id else None
        return self.versioning.create_snapshot(prefix=prefix)

    def restore_snapshot(
        self,
        snapshot: Dict[str, StateEntry],
    ) -> int:
        """
        Restore from snapshot.

        Args:
            snapshot: Snapshot from create_snapshot

        Returns:
            Number of keys restored
        """
        return self.versioning.restore_snapshot(
            snapshot=snapshot,
            component_id=self.component_id,
        )

    # Statistics

    def get_stats(self) -> Dict[str, Any]:
        """Get state manager statistics."""
        stats = {
            "component_id": self.component_id,
            "backend": self.backend_type,
            "total_keys": len(self.list_keys()),
            "execution_count": len(self.find_recoverable_executions()),
        }

        if self.sync:
            stats["sync"] = self.sync.get_sync_stats()

        if hasattr(self.store, "get_stats"):
            stats["store"] = self.store.get_stats()

        return stats

    # Cleanup

    def cleanup_execution(
        self,
        execution_id: str,
    ) -> int:
        """
        Clean up all state for an execution.

        Args:
            execution_id: Execution identifier

        Returns:
            Number of keys deleted
        """
        prefix = f"execution/{execution_id}"
        keys = self.list_keys(prefix=prefix)
        count = 0

        for key in keys:
            if self.delete(key):
                count += 1

        logger.info(f"Cleaned up {count} state keys for execution {execution_id}")
        return count

    def prune_old_versions(self) -> int:
        """Remove old versions based on retention policy."""
        return self.versioning.prune_old_versions()
