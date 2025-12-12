"""
File Locker - Concurrency Control (AC-3)

Implements pessimistic file locking as defined in policy.yaml Section 3.
AC-3: Two agents trying to edit main.py simultaneously do not corrupt the file.

This component ensures that only one agent can modify a file at a time,
preventing race conditions and data corruption.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class LockStatus(Enum):
    """Status of a lock request."""

    ACQUIRED = "acquired"
    WAITING = "waiting"
    DENIED = "denied"
    EXPIRED = "expired"
    RELEASED = "released"


@dataclass
class FileLock:
    """
    A file lock held by an agent.

    Attributes:
        path: The locked file path
        agent_id: Agent holding the lock
        acquired_at: When the lock was acquired
        expires_at: When the lock automatically expires
        purpose: Optional description of why the lock is held
    """

    path: str
    agent_id: str
    acquired_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    purpose: str = ""

    @property
    def is_expired(self) -> bool:
        """Check if the lock has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    @property
    def time_remaining_seconds(self) -> float:
        """Get seconds remaining before expiry."""
        if self.expires_at is None:
            return float("inf")
        remaining = (self.expires_at - datetime.utcnow()).total_seconds()
        return max(0, remaining)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "path": self.path,
            "agent_id": self.agent_id,
            "acquired_at": self.acquired_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "purpose": self.purpose,
            "is_expired": self.is_expired,
            "time_remaining_seconds": self.time_remaining_seconds,
        }


@dataclass
class LockRequest:
    """A pending lock request from an agent."""

    path: str
    agent_id: str
    requested_at: datetime = field(default_factory=datetime.utcnow)
    callback: Optional[Callable[[], None]] = None


class FileLocker:
    """
    File Locker - Pessimistic Locking for Concurrency Control.

    AC-3 Implementation: Ensures only one agent can edit a file at a time.

    From policy.yaml Section 3 (concurrency_control):
    - strategy: pessimistic_locking
    - max_lock_duration_seconds: 300 (5 minutes)
    - max_locks_per_agent: 3
    - queue_max_waiters: 5

    Features:
    - Automatic lock expiry
    - Wait queue for contended files
    - Lock hoarding prevention
    """

    def __init__(
        self,
        max_lock_duration_seconds: int = 300,
        max_locks_per_agent: int = 3,
        queue_max_waiters: int = 5,
    ):
        """
        Initialize the file locker.

        Args:
            max_lock_duration_seconds: Maximum time a lock can be held
            max_locks_per_agent: Maximum locks an agent can hold
            queue_max_waiters: Maximum waiters per file
        """
        self._locks: Dict[str, FileLock] = {}
        self._wait_queues: Dict[str, List[LockRequest]] = {}
        self._lock = threading.RLock()

        # Configuration from policy.yaml
        self._max_duration = timedelta(seconds=max_lock_duration_seconds)
        self._max_locks_per_agent = max_locks_per_agent
        self._queue_max_waiters = queue_max_waiters

        # Callbacks
        self._on_lock_acquired: List[Callable[[FileLock], None]] = []
        self._on_lock_released: List[Callable[[FileLock], None]] = []
        self._on_lock_expired: List[Callable[[FileLock], None]] = []

        logger.info(
            f"FileLocker initialized (max_duration={max_lock_duration_seconds}s, "
            f"max_per_agent={max_locks_per_agent})"
        )

    def acquire(
        self,
        path: str,
        agent_id: str,
        purpose: str = "",
        wait: bool = True,
        timeout_seconds: float = 30.0,
    ) -> tuple[LockStatus, Optional[FileLock]]:
        """
        Acquire a lock on a file.

        AC-3: If another agent holds the lock, caller waits (or returns DENIED).

        Args:
            path: Path to lock
            agent_id: Agent requesting the lock
            purpose: Description of why lock is needed
            wait: Whether to wait if lock is held
            timeout_seconds: How long to wait for lock

        Returns:
            Tuple of (status, lock if acquired)
        """
        with self._lock:
            # Clean up expired locks first
            self._cleanup_expired()

            # Check if agent has too many locks
            agent_lock_count = sum(
                1 for lock in self._locks.values()
                if lock.agent_id == agent_id
            )
            if agent_lock_count >= self._max_locks_per_agent:
                logger.warning(
                    f"Agent {agent_id} at lock limit ({self._max_locks_per_agent})"
                )
                return LockStatus.DENIED, None

            # Check if file is already locked
            existing = self._locks.get(path)
            if existing:
                if existing.agent_id == agent_id:
                    # Same agent already holds lock - extend it
                    existing.expires_at = datetime.utcnow() + self._max_duration
                    logger.debug(f"Lock extended for {path} by {agent_id}")
                    return LockStatus.ACQUIRED, existing

                if not wait:
                    logger.debug(f"Lock denied for {path} - held by {existing.agent_id}")
                    return LockStatus.DENIED, None

                # Add to wait queue
                return self._wait_for_lock(path, agent_id, purpose, timeout_seconds)

            # Acquire new lock
            lock = FileLock(
                path=path,
                agent_id=agent_id,
                expires_at=datetime.utcnow() + self._max_duration,
                purpose=purpose,
            )
            self._locks[path] = lock

            logger.info(f"Lock acquired: {path} by {agent_id}")

            # Notify callbacks
            for callback in self._on_lock_acquired:
                try:
                    callback(lock)
                except Exception as e:
                    logger.error(f"Lock acquired callback error: {e}")

            return LockStatus.ACQUIRED, lock

    def release(self, path: str, agent_id: str) -> LockStatus:
        """
        Release a lock.

        Args:
            path: Path to unlock
            agent_id: Agent releasing the lock

        Returns:
            LockStatus indicating result
        """
        with self._lock:
            lock = self._locks.get(path)

            if lock is None:
                return LockStatus.RELEASED  # Already released

            if lock.agent_id != agent_id:
                logger.warning(
                    f"Agent {agent_id} tried to release lock held by {lock.agent_id}"
                )
                return LockStatus.DENIED

            del self._locks[path]
            logger.info(f"Lock released: {path} by {agent_id}")

            # Notify callbacks
            for callback in self._on_lock_released:
                try:
                    callback(lock)
                except Exception as e:
                    logger.error(f"Lock released callback error: {e}")

            # Grant to next waiter
            self._grant_to_next_waiter(path)

            return LockStatus.RELEASED

    def get_lock_holder(self, path: str) -> Optional[str]:
        """Get the agent ID holding a lock on a path."""
        with self._lock:
            self._cleanup_expired()
            lock = self._locks.get(path)
            return lock.agent_id if lock else None

    def get_lock(self, path: str) -> Optional[FileLock]:
        """Get the lock object for a path."""
        with self._lock:
            self._cleanup_expired()
            return self._locks.get(path)

    def is_locked(self, path: str) -> bool:
        """Check if a path is locked."""
        with self._lock:
            self._cleanup_expired()
            return path in self._locks

    def get_agent_locks(self, agent_id: str) -> List[FileLock]:
        """Get all locks held by an agent."""
        with self._lock:
            self._cleanup_expired()
            return [
                lock for lock in self._locks.values()
                if lock.agent_id == agent_id
            ]

    def force_release(self, path: str, reason: str = "forced") -> bool:
        """
        Force release a lock (governance action).

        Args:
            path: Path to unlock
            reason: Reason for force release

        Returns:
            True if lock was released
        """
        with self._lock:
            lock = self._locks.get(path)
            if lock is None:
                return False

            logger.warning(f"Force releasing lock: {path} (held by {lock.agent_id}) - {reason}")

            del self._locks[path]

            for callback in self._on_lock_expired:
                try:
                    callback(lock)
                except Exception as e:
                    logger.error(f"Lock expired callback error: {e}")

            self._grant_to_next_waiter(path)
            return True

    def _wait_for_lock(
        self,
        path: str,
        agent_id: str,
        purpose: str,
        timeout_seconds: float,
    ) -> tuple[LockStatus, Optional[FileLock]]:
        """Wait for a lock to become available."""
        # Check queue size
        queue = self._wait_queues.get(path, [])
        if len(queue) >= self._queue_max_waiters:
            logger.warning(f"Wait queue full for {path}")
            return LockStatus.DENIED, None

        # Add to queue
        request = LockRequest(path=path, agent_id=agent_id)
        if path not in self._wait_queues:
            self._wait_queues[path] = []
        self._wait_queues[path].append(request)

        logger.debug(f"Agent {agent_id} waiting for lock on {path}")

        # Wait for lock (with timeout)
        start_time = time.time()
        while time.time() - start_time < timeout_seconds:
            # Release lock temporarily to allow other operations
            self._lock.release()
            time.sleep(0.1)
            self._lock.acquire()

            # Check if we got the lock
            lock = self._locks.get(path)
            if lock and lock.agent_id == agent_id:
                # Remove from queue
                if path in self._wait_queues:
                    self._wait_queues[path] = [
                        r for r in self._wait_queues[path]
                        if r.agent_id != agent_id
                    ]
                return LockStatus.ACQUIRED, lock

            # Check if lock is now available
            if lock is None or lock.is_expired:
                # Try to acquire
                self._cleanup_expired()
                if path not in self._locks:
                    # Acquire the lock
                    new_lock = FileLock(
                        path=path,
                        agent_id=agent_id,
                        expires_at=datetime.utcnow() + self._max_duration,
                        purpose=purpose,
                    )
                    self._locks[path] = new_lock

                    # Remove from queue
                    if path in self._wait_queues:
                        self._wait_queues[path] = [
                            r for r in self._wait_queues[path]
                            if r.agent_id != agent_id
                        ]

                    logger.info(f"Lock acquired after wait: {path} by {agent_id}")

                    for callback in self._on_lock_acquired:
                        try:
                            callback(new_lock)
                        except Exception as e:
                            logger.error(f"Lock acquired callback error: {e}")

                    return LockStatus.ACQUIRED, new_lock

        # Timeout - remove from queue
        if path in self._wait_queues:
            self._wait_queues[path] = [
                r for r in self._wait_queues[path]
                if r.agent_id != agent_id
            ]

        logger.warning(f"Lock wait timeout for {path} by {agent_id}")
        return LockStatus.DENIED, None

    def _grant_to_next_waiter(self, path: str) -> None:
        """Grant lock to the next waiting agent."""
        queue = self._wait_queues.get(path, [])
        if not queue:
            return

        next_request = queue.pop(0)
        new_lock = FileLock(
            path=path,
            agent_id=next_request.agent_id,
            expires_at=datetime.utcnow() + self._max_duration,
        )
        self._locks[path] = new_lock

        logger.info(f"Lock granted to waiter: {path} -> {next_request.agent_id}")

        if next_request.callback:
            try:
                next_request.callback()
            except Exception as e:
                logger.error(f"Wait callback error: {e}")

    def _cleanup_expired(self) -> None:
        """Clean up expired locks."""
        expired = [
            path for path, lock in self._locks.items()
            if lock.is_expired
        ]

        for path in expired:
            lock = self._locks.pop(path)
            logger.info(f"Lock expired: {path} (was held by {lock.agent_id})")

            for callback in self._on_lock_expired:
                try:
                    callback(lock)
                except Exception as e:
                    logger.error(f"Lock expired callback error: {e}")

            self._grant_to_next_waiter(path)

    def on_lock_acquired(self, callback: Callable[[FileLock], None]) -> None:
        """Register callback for lock acquisition."""
        self._on_lock_acquired.append(callback)

    def on_lock_released(self, callback: Callable[[FileLock], None]) -> None:
        """Register callback for lock release."""
        self._on_lock_released.append(callback)

    def on_lock_expired(self, callback: Callable[[FileLock], None]) -> None:
        """Register callback for lock expiry."""
        self._on_lock_expired.append(callback)

    def get_stats(self) -> Dict[str, Any]:
        """Get lock statistics."""
        with self._lock:
            self._cleanup_expired()
            return {
                "total_locks": len(self._locks),
                "locks_by_agent": {
                    agent: sum(1 for l in self._locks.values() if l.agent_id == agent)
                    for agent in set(l.agent_id for l in self._locks.values())
                },
                "total_waiters": sum(len(q) for q in self._wait_queues.values()),
                "files_with_waiters": len([q for q in self._wait_queues.values() if q]),
            }

    def get_all_locks(self) -> List[FileLock]:
        """Get all current locks."""
        with self._lock:
            self._cleanup_expired()
            return list(self._locks.values())
