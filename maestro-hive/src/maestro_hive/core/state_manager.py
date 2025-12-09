#!/usr/bin/env python3
"""
State Manager: Centralized state management for orchestration workflows.

This module provides thread-safe state storage with event-based notifications,
persistence layer for checkpoint/recovery, and namespace isolation for multi-tenant support.
"""

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, asdict, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class StateChange:
    """Represents a state change event."""
    key: str
    old_value: Any
    new_value: Any
    namespace: str
    timestamp: str
    change_type: str  # 'set', 'delete', 'clear'


@dataclass
class Checkpoint:
    """Represents a state checkpoint."""
    checkpoint_id: str
    timestamp: str
    state_snapshot: Dict[str, Dict[str, Any]]
    metadata: Dict[str, Any] = field(default_factory=dict)


class StateManager:
    """
    Thread-safe state management for orchestration workflows.

    Features:
    - Thread-safe dictionary storage with RLock
    - Event-based state change notifications
    - Persistence layer for checkpoint/recovery
    - Namespace isolation for multi-tenant support
    """

    _instance: Optional['StateManager'] = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """Singleton pattern for global state access."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        persistence_dir: Optional[str] = None,
        auto_persist: bool = False,
        persist_interval_seconds: int = 60
    ):
        """
        Initialize the state manager.

        Args:
            persistence_dir: Directory for state persistence files
            auto_persist: Enable automatic periodic persistence
            persist_interval_seconds: Interval for auto-persistence
        """
        if hasattr(self, '_initialized') and self._initialized:
            return

        self._state: Dict[str, Dict[str, Any]] = {'default': {}}
        self._state_lock = threading.RLock()
        self._subscribers: Dict[str, List[Callable[[StateChange], None]]] = {}
        self._checkpoints: Dict[str, Checkpoint] = {}
        self._persistence_dir = Path(persistence_dir) if persistence_dir else None
        self._auto_persist = auto_persist
        self._persist_interval = persist_interval_seconds
        self._persist_timer: Optional[threading.Timer] = None
        self._initialized = True

        if self._persistence_dir:
            self._persistence_dir.mkdir(parents=True, exist_ok=True)

        if self._auto_persist:
            self._start_auto_persist()

        logger.info("StateManager initialized")

    def get_state(self, key: str, namespace: str = 'default') -> Any:
        """
        Retrieve state value by key.

        Args:
            key: State key to retrieve
            namespace: Namespace for isolation (default: 'default')

        Returns:
            The state value or None if not found
        """
        with self._state_lock:
            ns = self._state.get(namespace, {})
            return ns.get(key)

    def set_state(
        self,
        key: str,
        value: Any,
        namespace: str = 'default',
        notify: bool = True
    ) -> None:
        """
        Set state value with optional namespace isolation.

        Args:
            key: State key to set
            value: Value to store
            namespace: Namespace for isolation
            notify: Whether to notify subscribers
        """
        with self._state_lock:
            if namespace not in self._state:
                self._state[namespace] = {}

            old_value = self._state[namespace].get(key)
            self._state[namespace][key] = value

            if notify:
                change = StateChange(
                    key=key,
                    old_value=old_value,
                    new_value=value,
                    namespace=namespace,
                    timestamp=datetime.utcnow().isoformat(),
                    change_type='set'
                )
                self._notify_subscribers(change)

        logger.debug(f"State set: {namespace}/{key}")

    def delete_state(self, key: str, namespace: str = 'default') -> bool:
        """
        Remove state entry.

        Args:
            key: State key to delete
            namespace: Namespace

        Returns:
            True if key existed and was deleted
        """
        with self._state_lock:
            if namespace in self._state and key in self._state[namespace]:
                old_value = self._state[namespace].pop(key)
                change = StateChange(
                    key=key,
                    old_value=old_value,
                    new_value=None,
                    namespace=namespace,
                    timestamp=datetime.utcnow().isoformat(),
                    change_type='delete'
                )
                self._notify_subscribers(change)
                logger.debug(f"State deleted: {namespace}/{key}")
                return True
            return False

    def get_all_state(self, namespace: Optional[str] = None) -> Dict[str, Any]:
        """
        Get all state entries.

        Args:
            namespace: If provided, get state only for this namespace

        Returns:
            Dictionary of all state entries
        """
        with self._state_lock:
            if namespace:
                return dict(self._state.get(namespace, {}))
            return {ns: dict(state) for ns, state in self._state.items()}

    def get_namespaces(self) -> List[str]:
        """Get list of all namespaces."""
        with self._state_lock:
            return list(self._state.keys())

    def clear(self, namespace: Optional[str] = None) -> None:
        """
        Clear all state entries.

        Args:
            namespace: If provided, clear only this namespace
        """
        with self._state_lock:
            if namespace:
                self._state[namespace] = {}
            else:
                self._state = {'default': {}}

            change = StateChange(
                key='*',
                old_value=None,
                new_value=None,
                namespace=namespace or '*',
                timestamp=datetime.utcnow().isoformat(),
                change_type='clear'
            )
            self._notify_subscribers(change)

        logger.info(f"State cleared: {namespace or 'all namespaces'}")

    def subscribe(
        self,
        callback: Callable[[StateChange], None],
        key_pattern: str = '*',
        namespace: str = '*'
    ) -> str:
        """
        Subscribe to state changes.

        Args:
            callback: Function to call on state change
            key_pattern: Key pattern to match (* for all)
            namespace: Namespace to watch (* for all)

        Returns:
            Subscription ID for unsubscribing
        """
        subscription_key = f"{namespace}:{key_pattern}"
        subscription_id = f"{subscription_key}:{id(callback)}"

        with self._state_lock:
            if subscription_key not in self._subscribers:
                self._subscribers[subscription_key] = []
            self._subscribers[subscription_key].append(callback)

        logger.debug(f"Subscription added: {subscription_id}")
        return subscription_id

    def unsubscribe(self, subscription_id: str) -> bool:
        """
        Remove a subscription.

        Args:
            subscription_id: ID returned from subscribe()

        Returns:
            True if subscription was found and removed
        """
        parts = subscription_id.rsplit(':', 1)
        if len(parts) != 2:
            return False

        subscription_key = parts[0]
        callback_id = int(parts[1])

        with self._state_lock:
            if subscription_key in self._subscribers:
                for i, cb in enumerate(self._subscribers[subscription_key]):
                    if id(cb) == callback_id:
                        self._subscribers[subscription_key].pop(i)
                        logger.debug(f"Subscription removed: {subscription_id}")
                        return True
        return False

    def _notify_subscribers(self, change: StateChange) -> None:
        """Notify all matching subscribers of a state change."""
        patterns_to_check = [
            f"{change.namespace}:{change.key}",
            f"{change.namespace}:*",
            f"*:{change.key}",
            "*:*"
        ]

        for pattern in patterns_to_check:
            callbacks = self._subscribers.get(pattern, [])
            for callback in callbacks:
                try:
                    callback(change)
                except Exception as e:
                    logger.error(f"Subscriber callback error: {e}")

    def checkpoint(self, checkpoint_id: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create named checkpoint of current state.

        Args:
            checkpoint_id: Unique identifier for checkpoint
            metadata: Optional metadata to store with checkpoint

        Returns:
            Checkpoint information
        """
        with self._state_lock:
            snapshot = {ns: dict(state) for ns, state in self._state.items()}

            cp = Checkpoint(
                checkpoint_id=checkpoint_id,
                timestamp=datetime.utcnow().isoformat(),
                state_snapshot=snapshot,
                metadata=metadata or {}
            )

            self._checkpoints[checkpoint_id] = cp

            # Persist if directory configured
            if self._persistence_dir:
                cp_file = self._persistence_dir / f"checkpoint_{checkpoint_id}.json"
                with open(cp_file, 'w') as f:
                    json.dump(asdict(cp), f, indent=2, default=str)

        logger.info(f"Checkpoint created: {checkpoint_id}")
        return asdict(cp)

    def restore(self, checkpoint_id: str) -> bool:
        """
        Restore state from checkpoint.

        Args:
            checkpoint_id: Checkpoint to restore

        Returns:
            True if checkpoint was found and restored
        """
        with self._state_lock:
            cp = self._checkpoints.get(checkpoint_id)

            # Try loading from disk if not in memory
            if not cp and self._persistence_dir:
                cp_file = self._persistence_dir / f"checkpoint_{checkpoint_id}.json"
                if cp_file.exists():
                    with open(cp_file, 'r') as f:
                        data = json.load(f)
                        cp = Checkpoint(**data)
                        self._checkpoints[checkpoint_id] = cp

            if cp:
                self._state = {ns: dict(state) for ns, state in cp.state_snapshot.items()}
                logger.info(f"State restored from checkpoint: {checkpoint_id}")
                return True

            logger.warning(f"Checkpoint not found: {checkpoint_id}")
            return False

    def list_checkpoints(self) -> List[Dict[str, Any]]:
        """List all available checkpoints."""
        checkpoints = []

        # In-memory checkpoints
        for cp in self._checkpoints.values():
            checkpoints.append({
                'checkpoint_id': cp.checkpoint_id,
                'timestamp': cp.timestamp,
                'metadata': cp.metadata
            })

        # Disk checkpoints not in memory
        if self._persistence_dir:
            for cp_file in self._persistence_dir.glob("checkpoint_*.json"):
                cp_id = cp_file.stem.replace("checkpoint_", "")
                if cp_id not in self._checkpoints:
                    with open(cp_file, 'r') as f:
                        data = json.load(f)
                        checkpoints.append({
                            'checkpoint_id': data['checkpoint_id'],
                            'timestamp': data['timestamp'],
                            'metadata': data.get('metadata', {})
                        })

        return sorted(checkpoints, key=lambda x: x['timestamp'], reverse=True)

    def _start_auto_persist(self) -> None:
        """Start automatic persistence timer."""
        def persist_task():
            if self._auto_persist:
                self.checkpoint(f"auto_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}")
                self._persist_timer = threading.Timer(self._persist_interval, persist_task)
                self._persist_timer.daemon = True
                self._persist_timer.start()

        self._persist_timer = threading.Timer(self._persist_interval, persist_task)
        self._persist_timer.daemon = True
        self._persist_timer.start()

    def shutdown(self) -> None:
        """Clean shutdown of state manager."""
        if self._persist_timer:
            self._persist_timer.cancel()

        # Final checkpoint
        if self._persistence_dir:
            self.checkpoint('shutdown')

        logger.info("StateManager shutdown complete")


# Convenience function to get singleton instance
def get_state_manager(**kwargs) -> StateManager:
    """Get the singleton StateManager instance."""
    return StateManager(**kwargs)
