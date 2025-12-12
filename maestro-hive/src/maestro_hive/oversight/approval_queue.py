#!/usr/bin/env python3
"""
approval_queue.py

Approval Queue Manager for pending human-in-the-loop decisions.
Provides queue management, prioritization, and statistics.

Related EPIC: MD-3023 - Human-in-the-Loop Approval System
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from threading import RLock
from typing import Any, Dict, List, Optional

from .approval_workflow import (
    ApprovalRequest,
    ApprovalStatus,
    ApprovalType,
    Priority,
    get_approval_workflow
)

logger = logging.getLogger(__name__)


@dataclass
class QueueStats:
    """Statistics about the approval queue."""
    total_pending: int
    by_priority: Dict[str, int]
    by_type: Dict[str, int]
    overdue_count: int
    average_wait_seconds: float
    oldest_request_age_seconds: int
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_pending": self.total_pending,
            "by_priority": self.by_priority,
            "by_type": self.by_type,
            "overdue_count": self.overdue_count,
            "average_wait_seconds": self.average_wait_seconds,
            "oldest_request_age_seconds": self.oldest_request_age_seconds,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class QueueEntry:
    """Entry in the approval queue with metadata."""
    request_id: str
    enqueued_at: datetime
    priority: Priority
    assigned_to: List[str]
    request_type: ApprovalType
    deadline: datetime


class ApprovalQueue:
    """
    Manages the queue of pending approval requests.

    Features:
    - Priority-based ordering
    - Per-approver filtering
    - Timeout tracking
    - Queue statistics
    - Batch operations
    """

    _instance: Optional['ApprovalQueue'] = None
    _lock = RLock()

    def __new__(cls) -> 'ApprovalQueue':
        """Singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the approval queue."""
        if self._initialized:
            return

        self._queue: Dict[str, QueueEntry] = {}
        self._approver_queues: Dict[str, List[str]] = {}  # approver_id -> request_ids
        self._workflow = get_approval_workflow()
        self._initialized = True

        logger.info("ApprovalQueue initialized")

    def enqueue(self, request: ApprovalRequest) -> bool:
        """
        Add a request to the queue.

        Args:
            request: The approval request to enqueue

        Returns:
            True if successfully enqueued
        """
        with self._lock:
            if request.id in self._queue:
                logger.warning(f"Request {request.id} already in queue")
                return False

            if request.status != ApprovalStatus.PENDING:
                logger.warning(f"Cannot enqueue non-pending request: {request.status}")
                return False

            entry = QueueEntry(
                request_id=request.id,
                enqueued_at=datetime.utcnow(),
                priority=request.priority,
                assigned_to=request.assigned_to,
                request_type=request.request_type,
                deadline=request.created_at + timedelta(seconds=request.timeout_seconds)
            )

            self._queue[request.id] = entry

            # Add to per-approver queues
            for approver_id in request.assigned_to:
                if approver_id not in self._approver_queues:
                    self._approver_queues[approver_id] = []
                self._approver_queues[approver_id].append(request.id)

            logger.info(f"Request {request.id} enqueued with priority {request.priority.name}")
            return True

    def dequeue(self, request_id: str) -> Optional[ApprovalRequest]:
        """
        Remove a request from the queue.

        Args:
            request_id: ID of the request to remove

        Returns:
            The removed request, or None if not found
        """
        with self._lock:
            if request_id not in self._queue:
                return None

            entry = self._queue[request_id]
            del self._queue[request_id]

            # Remove from per-approver queues
            for approver_id in entry.assigned_to:
                if approver_id in self._approver_queues:
                    if request_id in self._approver_queues[approver_id]:
                        self._approver_queues[approver_id].remove(request_id)

            logger.info(f"Request {request_id} dequeued")
            return self._workflow.get_request(request_id)

    def get_pending(
        self,
        approver_id: Optional[str] = None,
        limit: int = 50
    ) -> List[ApprovalRequest]:
        """
        Get pending requests, optionally filtered by approver.

        Args:
            approver_id: Optional approver ID to filter by
            limit: Maximum number of requests to return

        Returns:
            List of pending approval requests
        """
        with self._lock:
            if approver_id:
                request_ids = self._approver_queues.get(approver_id, [])
            else:
                request_ids = list(self._queue.keys())

            # Get actual requests
            requests = []
            for rid in request_ids:
                req = self._workflow.get_request(rid)
                if req and req.status == ApprovalStatus.PENDING:
                    requests.append(req)

            # Sort by priority (descending) then by creation time (ascending)
            requests.sort(
                key=lambda r: (-r.priority.value, r.created_at)
            )

            return requests[:limit]

    def get_by_priority(
        self,
        priority: Priority,
        limit: int = 50
    ) -> List[ApprovalRequest]:
        """
        Get requests of a specific priority.

        Args:
            priority: Priority level to filter by
            limit: Maximum number of requests to return

        Returns:
            List of matching approval requests
        """
        with self._lock:
            requests = []
            for entry in self._queue.values():
                if entry.priority == priority:
                    req = self._workflow.get_request(entry.request_id)
                    if req:
                        requests.append(req)

            requests.sort(key=lambda r: r.created_at)
            return requests[:limit]

    def get_by_type(
        self,
        request_type: ApprovalType,
        limit: int = 50
    ) -> List[ApprovalRequest]:
        """
        Get requests of a specific type.

        Args:
            request_type: Type to filter by
            limit: Maximum number of requests to return

        Returns:
            List of matching approval requests
        """
        with self._lock:
            requests = []
            for entry in self._queue.values():
                if entry.request_type == request_type:
                    req = self._workflow.get_request(entry.request_id)
                    if req:
                        requests.append(req)

            requests.sort(
                key=lambda r: (-r.priority.value, r.created_at)
            )
            return requests[:limit]

    def prioritize(
        self,
        request_id: str,
        new_priority: Priority
    ) -> bool:
        """
        Change the priority of a queued request.

        Args:
            request_id: ID of the request
            new_priority: New priority level

        Returns:
            True if successfully updated
        """
        with self._lock:
            if request_id not in self._queue:
                return False

            old_priority = self._queue[request_id].priority
            self._queue[request_id].priority = new_priority

            # Also update the actual request
            request = self._workflow.get_request(request_id)
            if request:
                request.priority = new_priority

            logger.info(
                f"Request {request_id} priority changed: "
                f"{old_priority.name} -> {new_priority.name}"
            )
            return True

    def get_overdue(self) -> List[ApprovalRequest]:
        """
        Get all overdue requests (past their deadline).

        Returns:
            List of overdue approval requests
        """
        with self._lock:
            now = datetime.utcnow()
            overdue = []

            for entry in self._queue.values():
                if entry.deadline < now:
                    req = self._workflow.get_request(entry.request_id)
                    if req and req.status == ApprovalStatus.PENDING:
                        overdue.append(req)

            overdue.sort(key=lambda r: r.created_at)
            return overdue

    def get_expiring_soon(
        self,
        within_seconds: int = 900
    ) -> List[ApprovalRequest]:
        """
        Get requests expiring within the specified time.

        Args:
            within_seconds: Time window in seconds (default 15 minutes)

        Returns:
            List of soon-to-expire requests
        """
        with self._lock:
            now = datetime.utcnow()
            threshold = now + timedelta(seconds=within_seconds)
            expiring = []

            for entry in self._queue.values():
                if now < entry.deadline < threshold:
                    req = self._workflow.get_request(entry.request_id)
                    if req and req.status == ApprovalStatus.PENDING:
                        expiring.append(req)

            expiring.sort(key=lambda r: r.created_at)
            return expiring

    def get_stats(self) -> QueueStats:
        """
        Get queue statistics.

        Returns:
            QueueStats with current queue state
        """
        with self._lock:
            pending_entries = list(self._queue.values())
            now = datetime.utcnow()

            # Count by priority
            by_priority = {p.name: 0 for p in Priority}
            for entry in pending_entries:
                by_priority[entry.priority.name] += 1

            # Count by type
            by_type = {t.value: 0 for t in ApprovalType}
            for entry in pending_entries:
                by_type[entry.request_type.value] += 1

            # Count overdue
            overdue_count = sum(1 for e in pending_entries if e.deadline < now)

            # Calculate average wait time
            if pending_entries:
                wait_times = [(now - e.enqueued_at).total_seconds() for e in pending_entries]
                avg_wait = sum(wait_times) / len(wait_times)
                oldest = max(wait_times) if wait_times else 0
            else:
                avg_wait = 0
                oldest = 0

            return QueueStats(
                total_pending=len(pending_entries),
                by_priority=by_priority,
                by_type=by_type,
                overdue_count=overdue_count,
                average_wait_seconds=avg_wait,
                oldest_request_age_seconds=int(oldest)
            )

    def get_approver_load(self) -> Dict[str, int]:
        """
        Get the number of pending requests per approver.

        Returns:
            Dictionary mapping approver ID to pending count
        """
        with self._lock:
            load = {}
            for approver_id, request_ids in self._approver_queues.items():
                # Count only requests still in queue
                active_count = sum(1 for rid in request_ids if rid in self._queue)
                if active_count > 0:
                    load[approver_id] = active_count
            return load

    def reassign(
        self,
        request_id: str,
        new_approvers: List[str]
    ) -> bool:
        """
        Reassign a request to different approvers.

        Args:
            request_id: ID of the request
            new_approvers: New list of approver IDs

        Returns:
            True if successfully reassigned
        """
        with self._lock:
            if request_id not in self._queue:
                return False

            entry = self._queue[request_id]
            old_approvers = entry.assigned_to

            # Remove from old approver queues
            for approver_id in old_approvers:
                if approver_id in self._approver_queues:
                    if request_id in self._approver_queues[approver_id]:
                        self._approver_queues[approver_id].remove(request_id)

            # Add to new approver queues
            for approver_id in new_approvers:
                if approver_id not in self._approver_queues:
                    self._approver_queues[approver_id] = []
                self._approver_queues[approver_id].append(request_id)

            entry.assigned_to = new_approvers

            # Update the actual request
            request = self._workflow.get_request(request_id)
            if request:
                request.assigned_to = new_approvers

            logger.info(
                f"Request {request_id} reassigned: "
                f"{old_approvers} -> {new_approvers}"
            )
            return True

    def clear_completed(self) -> int:
        """
        Remove all completed requests from the queue.

        Returns:
            Number of entries removed
        """
        with self._lock:
            to_remove = []
            for request_id in self._queue:
                req = self._workflow.get_request(request_id)
                if req and req.status != ApprovalStatus.PENDING:
                    to_remove.append(request_id)

            for request_id in to_remove:
                self.dequeue(request_id)

            logger.info(f"Cleared {len(to_remove)} completed requests from queue")
            return len(to_remove)


# Singleton accessor
_queue_instance: Optional[ApprovalQueue] = None


def get_approval_queue() -> ApprovalQueue:
    """Get the singleton ApprovalQueue instance."""
    global _queue_instance
    if _queue_instance is None:
        _queue_instance = ApprovalQueue()
    return _queue_instance
