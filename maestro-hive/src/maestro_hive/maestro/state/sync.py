"""
State Synchronization - Component state coordination

EPIC: MD-2528 - AC-2: State synchronization between components

Handles state synchronization across distributed components.
"""

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from .store import StateEntry, StateStore

logger = logging.getLogger(__name__)


class SyncStatus(Enum):
    """Synchronization status."""
    IDLE = "idle"
    SYNCING = "syncing"
    SYNCED = "synced"
    CONFLICT = "conflict"
    ERROR = "error"


@dataclass
class SyncEvent:
    """Event from state synchronization."""
    event_type: str  # "update", "delete", "conflict"
    key: str
    version: int
    component_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    details: Dict[str, Any] = field(default_factory=dict)


class StateSync:
    """
    State synchronization service.

    Coordinates state updates across components with:
    - Change detection
    - Conflict resolution
    - Event broadcasting
    """

    def __init__(
        self,
        store: StateStore,
        component_id: str,
        sync_interval: float = 5.0,
    ):
        """
        Initialize state sync.

        Args:
            store: State store backend
            component_id: Unique ID for this component
            sync_interval: Seconds between sync checks
        """
        self.store = store
        self.component_id = component_id
        self.sync_interval = sync_interval

        self._status = SyncStatus.IDLE
        self._subscriptions: Dict[str, Set[Callable]] = {}
        self._version_cache: Dict[str, int] = {}
        self._sync_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

        logger.info(f"StateSync initialized for component {component_id}")

    @property
    def status(self) -> SyncStatus:
        """Current sync status."""
        return self._status

    def subscribe(
        self,
        key_pattern: str,
        callback: Callable[[SyncEvent], None],
    ) -> None:
        """
        Subscribe to state changes.

        Args:
            key_pattern: Key pattern to watch (supports * wildcard)
            callback: Function to call on changes
        """
        with self._lock:
            if key_pattern not in self._subscriptions:
                self._subscriptions[key_pattern] = set()
            self._subscriptions[key_pattern].add(callback)
        logger.debug(f"Subscribed to {key_pattern}")

    def unsubscribe(
        self,
        key_pattern: str,
        callback: Callable[[SyncEvent], None],
    ) -> None:
        """
        Unsubscribe from state changes.

        Args:
            key_pattern: Key pattern to unwatch
            callback: Callback to remove
        """
        with self._lock:
            if key_pattern in self._subscriptions:
                self._subscriptions[key_pattern].discard(callback)
        logger.debug(f"Unsubscribed from {key_pattern}")

    def start(self) -> None:
        """Start background sync thread."""
        if self._sync_thread and self._sync_thread.is_alive():
            logger.warning("Sync thread already running")
            return

        self._stop_event.clear()
        self._sync_thread = threading.Thread(
            target=self._sync_loop,
            daemon=True,
            name=f"StateSync-{self.component_id}",
        )
        self._sync_thread.start()
        logger.info("State sync started")

    def stop(self) -> None:
        """Stop background sync thread."""
        self._stop_event.set()
        if self._sync_thread:
            self._sync_thread.join(timeout=5.0)
        self._status = SyncStatus.IDLE
        logger.info("State sync stopped")

    def sync_now(self) -> List[SyncEvent]:
        """
        Perform immediate synchronization.

        Returns:
            List of sync events detected
        """
        self._status = SyncStatus.SYNCING
        events = []

        try:
            # Get all keys
            keys = self.store.list_keys()

            for key in keys:
                entry = self.store.load(key)
                if not entry:
                    continue

                cached_version = self._version_cache.get(key, 0)

                if entry.version > cached_version:
                    # State was updated
                    event = SyncEvent(
                        event_type="update",
                        key=key,
                        version=entry.version,
                        component_id=entry.component_id or "unknown",
                        details={"previous_version": cached_version},
                    )
                    events.append(event)
                    self._notify_subscribers(event)
                    self._version_cache[key] = entry.version

            # Check for deletions
            cached_keys = set(self._version_cache.keys())
            current_keys = set(keys)
            deleted_keys = cached_keys - current_keys

            for key in deleted_keys:
                event = SyncEvent(
                    event_type="delete",
                    key=key,
                    version=0,
                    component_id=self.component_id,
                )
                events.append(event)
                self._notify_subscribers(event)
                del self._version_cache[key]

            self._status = SyncStatus.SYNCED

        except Exception as e:
            logger.error(f"Sync error: {e}")
            self._status = SyncStatus.ERROR

        return events

    def publish_update(
        self,
        key: str,
        value: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> StateEntry:
        """
        Update state and notify subscribers.

        Args:
            key: State key
            value: New value
            metadata: Optional metadata

        Returns:
            Created StateEntry
        """
        entry = self.store.save(
            key=key,
            value=value,
            component_id=self.component_id,
            metadata=metadata,
        )

        # Update cache
        self._version_cache[key] = entry.version

        # Notify local subscribers
        event = SyncEvent(
            event_type="update",
            key=key,
            version=entry.version,
            component_id=self.component_id,
        )
        self._notify_subscribers(event)

        return entry

    def resolve_conflict(
        self,
        key: str,
        local_value: Dict[str, Any],
        remote_value: Dict[str, Any],
        strategy: str = "remote_wins",
    ) -> StateEntry:
        """
        Resolve state conflict between local and remote.

        Args:
            key: State key
            local_value: Local state value
            remote_value: Remote state value
            strategy: Resolution strategy (remote_wins, local_wins, merge)

        Returns:
            Resolved StateEntry
        """
        if strategy == "remote_wins":
            resolved_value = remote_value
        elif strategy == "local_wins":
            resolved_value = local_value
        elif strategy == "merge":
            # Simple merge - remote values override local
            resolved_value = {**local_value, **remote_value}
        else:
            raise ValueError(f"Unknown conflict resolution strategy: {strategy}")

        return self.publish_update(
            key=key,
            value=resolved_value,
            metadata={"conflict_resolved": True, "strategy": strategy},
        )

    def _sync_loop(self) -> None:
        """Background sync loop."""
        while not self._stop_event.is_set():
            try:
                self.sync_now()
            except Exception as e:
                logger.error(f"Sync loop error: {e}")
                self._status = SyncStatus.ERROR

            self._stop_event.wait(self.sync_interval)

    def _notify_subscribers(self, event: SyncEvent) -> None:
        """Notify matching subscribers of event."""
        with self._lock:
            for pattern, callbacks in self._subscriptions.items():
                if self._matches_pattern(event.key, pattern):
                    for callback in callbacks:
                        try:
                            callback(event)
                        except Exception as e:
                            logger.error(f"Subscriber callback error: {e}")

    def _matches_pattern(self, key: str, pattern: str) -> bool:
        """Check if key matches pattern (supports * wildcard)."""
        if pattern == "*":
            return True
        if "*" not in pattern:
            return key == pattern

        # Simple wildcard matching
        parts = pattern.split("*")
        if len(parts) == 2:
            prefix, suffix = parts
            return key.startswith(prefix) and key.endswith(suffix)

        return False

    def get_sync_stats(self) -> Dict[str, Any]:
        """Get synchronization statistics."""
        return {
            "component_id": self.component_id,
            "status": self._status.value,
            "cached_keys": len(self._version_cache),
            "subscriptions": len(self._subscriptions),
            "sync_interval": self.sync_interval,
        }
