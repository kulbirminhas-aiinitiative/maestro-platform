"""
Auditor Service - Asynchronous Governance (MD-3117)

Implements asynchronous auditing for the governance layer:
- AC-1: Coverage verification (no reputation if test doesn't increase coverage)
- AC-2: Async processing (non-blocking agent execution)
- AC-3: Sybil detection (flag concurrent file edits within 100ms)
- AC-4: Immutable audit logging (all decisions logged)
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


class AuditDecision(Enum):
    """Types of audit decisions."""
    APPROVED = "approved"
    REJECTED = "rejected"
    FLAGGED = "flagged"
    PENDING = "pending"


class AuditReason(Enum):
    """Reasons for audit decisions."""
    COVERAGE_INCREASED = "coverage_increased"
    COVERAGE_NOT_INCREASED = "coverage_not_increased"
    SYBIL_DETECTED = "sybil_detected"
    CONCURRENT_EDIT = "concurrent_edit"
    VALID_CONTRIBUTION = "valid_contribution"
    INVALID_CONTRIBUTION = "invalid_contribution"


@dataclass
class CoverageReport:
    """Coverage analysis result."""
    before: float
    after: float
    delta: float
    files_covered: int
    lines_covered: int
    lines_total: int

    @property
    def increased(self) -> bool:
        """Check if coverage increased."""
        return self.delta > 0


@dataclass
class FileEditEvent:
    """Record of a file edit by an agent."""
    agent_id: str
    file_path: str
    timestamp_ms: float
    edit_hash: str

    @classmethod
    def create(cls, agent_id: str, file_path: str, content_hash: str) -> "FileEditEvent":
        """Create a new file edit event with current timestamp."""
        return cls(
            agent_id=agent_id,
            file_path=file_path,
            timestamp_ms=time.time() * 1000,
            edit_hash=content_hash
        )


@dataclass
class AuditLogEntry:
    """Immutable audit log entry."""
    entry_id: str
    timestamp: datetime
    agent_id: str
    action: str
    decision: AuditDecision
    reason: AuditReason
    metadata: Dict[str, Any]
    previous_hash: str
    entry_hash: str = field(default="")

    def __post_init__(self):
        """Compute hash after initialization."""
        if not self.entry_hash:
            self.entry_hash = self._compute_hash()

    def _compute_hash(self) -> str:
        """Compute SHA-256 hash of entry for immutability."""
        content = json.dumps({
            "entry_id": self.entry_id,
            "timestamp": self.timestamp.isoformat(),
            "agent_id": self.agent_id,
            "action": self.action,
            "decision": self.decision.value,
            "reason": self.reason.value,
            "metadata": self.metadata,
            "previous_hash": self.previous_hash
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "entry_id": self.entry_id,
            "timestamp": self.timestamp.isoformat(),
            "agent_id": self.agent_id,
            "action": self.action,
            "decision": self.decision.value,
            "reason": self.reason.value,
            "metadata": self.metadata,
            "previous_hash": self.previous_hash,
            "entry_hash": self.entry_hash
        }


class ImmutableAuditLog:
    """
    Immutable audit log with hash chain (AC-4).

    Each entry includes hash of previous entry, creating
    a tamper-evident chain similar to blockchain.
    """

    GENESIS_HASH = "0" * 64  # Genesis block hash

    def __init__(self, persist_path: Optional[Path] = None):
        """
        Initialize audit log.

        Args:
            persist_path: Optional path to persist log to disk
        """
        self._entries: List[AuditLogEntry] = []
        self._persist_path = persist_path
        self._entry_counter = 0
        self._lock = asyncio.Lock()

        logger.info("ImmutableAuditLog initialized")

    async def append(
        self,
        agent_id: str,
        action: str,
        decision: AuditDecision,
        reason: AuditReason,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditLogEntry:
        """
        Append entry to audit log (thread-safe).

        Args:
            agent_id: ID of agent being audited
            action: Action being audited
            decision: Audit decision
            reason: Reason for decision
            metadata: Additional metadata

        Returns:
            The created audit log entry
        """
        async with self._lock:
            self._entry_counter += 1

            # Get previous hash (genesis if first entry)
            previous_hash = self.GENESIS_HASH
            if self._entries:
                previous_hash = self._entries[-1].entry_hash

            entry = AuditLogEntry(
                entry_id=f"audit_{self._entry_counter:08d}",
                timestamp=datetime.utcnow(),
                agent_id=agent_id,
                action=action,
                decision=decision,
                reason=reason,
                metadata=metadata or {},
                previous_hash=previous_hash
            )

            self._entries.append(entry)

            # Persist if path configured
            if self._persist_path:
                await self._persist_entry(entry)

            logger.info(f"Audit log entry: {entry.entry_id} - {agent_id} - {decision.value}")
            return entry

    async def _persist_entry(self, entry: AuditLogEntry) -> None:
        """Persist entry to disk."""
        if not self._persist_path:
            return

        self._persist_path.parent.mkdir(parents=True, exist_ok=True)

        # Append to JSONL file
        async with asyncio.Lock():
            with open(self._persist_path, "a") as f:
                f.write(json.dumps(entry.to_dict()) + "\n")

    def verify_chain(self) -> bool:
        """
        Verify integrity of the hash chain.

        Returns:
            True if chain is valid, False if tampered
        """
        if not self._entries:
            return True

        # Verify first entry links to genesis
        if self._entries[0].previous_hash != self.GENESIS_HASH:
            logger.warning("Chain verification failed: First entry doesn't link to genesis")
            return False

        # Verify each entry's hash and chain linkage
        for i, entry in enumerate(self._entries):
            # Recompute hash
            expected_hash = entry._compute_hash()
            if entry.entry_hash != expected_hash:
                logger.warning(f"Chain verification failed: Entry {entry.entry_id} hash mismatch")
                return False

            # Verify chain linkage (except first)
            if i > 0:
                if entry.previous_hash != self._entries[i-1].entry_hash:
                    logger.warning(f"Chain verification failed: Entry {entry.entry_id} chain break")
                    return False

        return True

    def get_entries(
        self,
        agent_id: Optional[str] = None,
        decision: Optional[AuditDecision] = None,
        limit: int = 100
    ) -> List[AuditLogEntry]:
        """Get filtered audit entries."""
        entries = self._entries

        if agent_id:
            entries = [e for e in entries if e.agent_id == agent_id]
        if decision:
            entries = [e for e in entries if e.decision == decision]

        return entries[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Get audit log statistics."""
        by_decision = defaultdict(int)
        by_reason = defaultdict(int)

        for entry in self._entries:
            by_decision[entry.decision.value] += 1
            by_reason[entry.reason.value] += 1

        return {
            "total_entries": len(self._entries),
            "by_decision": dict(by_decision),
            "by_reason": dict(by_reason),
            "chain_valid": self.verify_chain()
        }


class SybilDetector:
    """
    Sybil attack detection (AC-3).

    Detects when multiple agents try to edit the same file
    within a short time window (100ms), which may indicate
    coordinated attack or bot activity.
    """

    DETECTION_WINDOW_MS = 100  # 100ms window per AC-3

    def __init__(self):
        """Initialize sybil detector."""
        self._edit_history: Dict[str, List[FileEditEvent]] = defaultdict(list)
        self._flagged_events: List[tuple] = []
        self._lock = asyncio.Lock()

        logger.info(f"SybilDetector initialized (window={self.DETECTION_WINDOW_MS}ms)")

    async def record_edit(self, event: FileEditEvent) -> bool:
        """
        Record a file edit and check for sybil activity.

        Args:
            event: File edit event

        Returns:
            True if sybil activity detected, False otherwise
        """
        async with self._lock:
            file_path = event.file_path
            current_time = event.timestamp_ms

            # Get recent edits to this file
            recent_edits = [
                e for e in self._edit_history[file_path]
                if current_time - e.timestamp_ms <= self.DETECTION_WINDOW_MS
                and e.agent_id != event.agent_id  # Different agent
            ]

            # Record this edit
            self._edit_history[file_path].append(event)

            # Cleanup old entries (keep last 1000 per file)
            if len(self._edit_history[file_path]) > 1000:
                self._edit_history[file_path] = self._edit_history[file_path][-500:]

            # Check for sybil: 2+ agents editing same file within window
            if recent_edits:
                conflicting_agents = {e.agent_id for e in recent_edits}
                conflicting_agents.add(event.agent_id)

                self._flagged_events.append((
                    file_path,
                    list(conflicting_agents),
                    current_time,
                    len(conflicting_agents)
                ))

                logger.warning(
                    f"SYBIL DETECTED: {len(conflicting_agents)} agents editing "
                    f"{file_path} within {self.DETECTION_WINDOW_MS}ms: {conflicting_agents}"
                )
                return True

            return False

    def get_flagged_events(self) -> List[Dict[str, Any]]:
        """Get all flagged sybil events."""
        return [
            {
                "file_path": fp,
                "agents": agents,
                "timestamp_ms": ts,
                "agent_count": count
            }
            for fp, agents, ts, count in self._flagged_events
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get sybil detection statistics."""
        return {
            "files_monitored": len(self._edit_history),
            "total_edits_tracked": sum(len(v) for v in self._edit_history.values()),
            "sybil_events_flagged": len(self._flagged_events),
            "detection_window_ms": self.DETECTION_WINDOW_MS
        }


class CoverageVerifier:
    """
    Coverage verification service (AC-1).

    Verifies that test contributions actually increase
    code coverage before awarding reputation.
    """

    def __init__(self):
        """Initialize coverage verifier."""
        self._coverage_history: Dict[str, List[CoverageReport]] = defaultdict(list)
        logger.info("CoverageVerifier initialized")

    async def verify_coverage_increase(
        self,
        agent_id: str,
        test_file: str,
        coverage_before: float,
        coverage_after: float,
        files_covered: int = 0,
        lines_covered: int = 0,
        lines_total: int = 0
    ) -> tuple[bool, CoverageReport]:
        """
        Verify if a test contribution increased coverage.

        Args:
            agent_id: Agent who contributed the test
            test_file: Path to test file
            coverage_before: Coverage % before adding test
            coverage_after: Coverage % after adding test
            files_covered: Number of files with coverage
            lines_covered: Lines covered
            lines_total: Total lines

        Returns:
            Tuple of (coverage_increased, coverage_report)
        """
        delta = coverage_after - coverage_before

        report = CoverageReport(
            before=coverage_before,
            after=coverage_after,
            delta=delta,
            files_covered=files_covered,
            lines_covered=lines_covered,
            lines_total=lines_total
        )

        # Record history
        self._coverage_history[agent_id].append(report)

        if report.increased:
            logger.info(
                f"Coverage INCREASED by {delta:.2f}% for {agent_id} "
                f"({coverage_before:.2f}% -> {coverage_after:.2f}%)"
            )
        else:
            logger.warning(
                f"Coverage NOT increased for {agent_id}: "
                f"delta={delta:.2f}% (before={coverage_before:.2f}%, after={coverage_after:.2f}%)"
            )

        return report.increased, report

    def get_agent_coverage_history(self, agent_id: str) -> List[CoverageReport]:
        """Get coverage history for an agent."""
        return self._coverage_history.get(agent_id, [])

    def get_stats(self) -> Dict[str, Any]:
        """Get coverage verification statistics."""
        total_verifications = sum(len(v) for v in self._coverage_history.values())
        increases = sum(
            1 for reports in self._coverage_history.values()
            for r in reports if r.increased
        )

        return {
            "agents_tracked": len(self._coverage_history),
            "total_verifications": total_verifications,
            "coverage_increases": increases,
            "coverage_failures": total_verifications - increases,
            "success_rate": increases / total_verifications if total_verifications > 0 else 0
        }


class AuditorService:
    """
    Main Auditor Service - Asynchronous Governance (MD-3117).

    Provides non-blocking auditing for agent contributions:
    - AC-1: Coverage verification
    - AC-2: Async processing (doesn't block main loop)
    - AC-3: Sybil detection
    - AC-4: Immutable audit logging
    """

    def __init__(
        self,
        audit_log_path: Optional[Path] = None,
        reputation_callback: Optional[Callable[[str, int], None]] = None
    ):
        """
        Initialize Auditor Service.

        Args:
            audit_log_path: Path to persist audit log
            reputation_callback: Callback to award/revoke reputation
        """
        self._audit_log = ImmutableAuditLog(persist_path=audit_log_path)
        self._sybil_detector = SybilDetector()
        self._coverage_verifier = CoverageVerifier()
        self._reputation_callback = reputation_callback

        # Task queue for async processing
        self._task_queue: asyncio.Queue = asyncio.Queue()
        self._processing = False
        self._processor_task: Optional[asyncio.Task] = None

        logger.info("AuditorService initialized")

    async def start(self) -> None:
        """Start the async audit processor (AC-2)."""
        if self._processing:
            return

        self._processing = True
        self._processor_task = asyncio.create_task(self._process_queue())
        logger.info("AuditorService processor started")

    async def stop(self) -> None:
        """Stop the async audit processor."""
        self._processing = False
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
        logger.info("AuditorService processor stopped")

    async def _process_queue(self) -> None:
        """
        Process audit tasks asynchronously (AC-2).

        This runs in background and doesn't block main agent execution.
        """
        while self._processing:
            try:
                # Non-blocking get with timeout
                task = await asyncio.wait_for(
                    self._task_queue.get(),
                    timeout=1.0
                )

                task_type = task.get("type")

                if task_type == "coverage_check":
                    await self._handle_coverage_check(task)
                elif task_type == "file_edit":
                    await self._handle_file_edit(task)
                elif task_type == "contribution":
                    await self._handle_contribution(task)

                self._task_queue.task_done()

            except asyncio.TimeoutError:
                # No tasks, continue loop
                continue
            except Exception as e:
                logger.error(f"Error processing audit task: {e}")

    async def submit_coverage_check(
        self,
        agent_id: str,
        test_file: str,
        coverage_before: float,
        coverage_after: float,
        files_covered: int = 0,
        lines_covered: int = 0,
        lines_total: int = 0
    ) -> None:
        """
        Submit a coverage check for async processing (AC-1 + AC-2).

        Non-blocking - returns immediately while audit happens in background.
        """
        await self._task_queue.put({
            "type": "coverage_check",
            "agent_id": agent_id,
            "test_file": test_file,
            "coverage_before": coverage_before,
            "coverage_after": coverage_after,
            "files_covered": files_covered,
            "lines_covered": lines_covered,
            "lines_total": lines_total
        })
        logger.debug(f"Coverage check queued for {agent_id}")

    async def submit_file_edit(
        self,
        agent_id: str,
        file_path: str,
        content_hash: str
    ) -> None:
        """
        Submit a file edit for sybil detection (AC-3 + AC-2).

        Non-blocking - returns immediately while check happens in background.
        """
        await self._task_queue.put({
            "type": "file_edit",
            "agent_id": agent_id,
            "file_path": file_path,
            "content_hash": content_hash
        })
        logger.debug(f"File edit queued for {agent_id}: {file_path}")

    async def _handle_coverage_check(self, task: Dict[str, Any]) -> None:
        """Handle coverage check task (AC-1)."""
        agent_id = task["agent_id"]

        increased, report = await self._coverage_verifier.verify_coverage_increase(
            agent_id=agent_id,
            test_file=task["test_file"],
            coverage_before=task["coverage_before"],
            coverage_after=task["coverage_after"],
            files_covered=task.get("files_covered", 0),
            lines_covered=task.get("lines_covered", 0),
            lines_total=task.get("lines_total", 0)
        )

        if increased:
            # Award reputation
            decision = AuditDecision.APPROVED
            reason = AuditReason.COVERAGE_INCREASED

            if self._reputation_callback:
                self._reputation_callback(agent_id, 10)  # Award 10 reputation
        else:
            # No reputation awarded (AC-1 requirement)
            decision = AuditDecision.REJECTED
            reason = AuditReason.COVERAGE_NOT_INCREASED

            logger.info(f"No reputation awarded to {agent_id} - coverage not increased")

        # Log to immutable audit log (AC-4)
        await self._audit_log.append(
            agent_id=agent_id,
            action="coverage_check",
            decision=decision,
            reason=reason,
            metadata={
                "test_file": task["test_file"],
                "coverage_before": task["coverage_before"],
                "coverage_after": task["coverage_after"],
                "delta": report.delta
            }
        )

    async def _handle_file_edit(self, task: Dict[str, Any]) -> None:
        """Handle file edit task for sybil detection (AC-3)."""
        agent_id = task["agent_id"]
        file_path = task["file_path"]

        event = FileEditEvent.create(
            agent_id=agent_id,
            file_path=file_path,
            content_hash=task["content_hash"]
        )

        sybil_detected = await self._sybil_detector.record_edit(event)

        if sybil_detected:
            decision = AuditDecision.FLAGGED
            reason = AuditReason.SYBIL_DETECTED
        else:
            decision = AuditDecision.APPROVED
            reason = AuditReason.VALID_CONTRIBUTION

        # Log to immutable audit log (AC-4)
        await self._audit_log.append(
            agent_id=agent_id,
            action="file_edit",
            decision=decision,
            reason=reason,
            metadata={
                "file_path": file_path,
                "content_hash": task["content_hash"],
                "sybil_detected": sybil_detected
            }
        )

    async def _handle_contribution(self, task: Dict[str, Any]) -> None:
        """Handle general contribution audit."""
        agent_id = task["agent_id"]

        # Log to immutable audit log (AC-4)
        await self._audit_log.append(
            agent_id=agent_id,
            action=task.get("action", "contribution"),
            decision=AuditDecision.APPROVED,
            reason=AuditReason.VALID_CONTRIBUTION,
            metadata=task.get("metadata", {})
        )

    # Synchronous convenience methods that queue async tasks

    def check_coverage(
        self,
        agent_id: str,
        test_file: str,
        coverage_before: float,
        coverage_after: float
    ) -> None:
        """
        Non-blocking coverage check (queues for async processing).

        Call this from main agent loop - it won't block (AC-2).
        """
        asyncio.create_task(self.submit_coverage_check(
            agent_id=agent_id,
            test_file=test_file,
            coverage_before=coverage_before,
            coverage_after=coverage_after
        ))

    def record_file_edit(
        self,
        agent_id: str,
        file_path: str,
        content: str
    ) -> None:
        """
        Non-blocking file edit recording (queues for async processing).

        Call this from main agent loop - it won't block (AC-2).
        """
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        asyncio.create_task(self.submit_file_edit(
            agent_id=agent_id,
            file_path=file_path,
            content_hash=content_hash
        ))

    # Direct audit methods (for testing or immediate auditing)

    async def audit_coverage_direct(
        self,
        agent_id: str,
        test_file: str,
        coverage_before: float,
        coverage_after: float
    ) -> tuple[bool, AuditLogEntry]:
        """
        Direct coverage audit (blocking, for testing).

        Returns:
            Tuple of (reputation_awarded, audit_entry)
        """
        increased, report = await self._coverage_verifier.verify_coverage_increase(
            agent_id=agent_id,
            test_file=test_file,
            coverage_before=coverage_before,
            coverage_after=coverage_after
        )

        decision = AuditDecision.APPROVED if increased else AuditDecision.REJECTED
        reason = AuditReason.COVERAGE_INCREASED if increased else AuditReason.COVERAGE_NOT_INCREASED

        entry = await self._audit_log.append(
            agent_id=agent_id,
            action="coverage_check",
            decision=decision,
            reason=reason,
            metadata={
                "test_file": test_file,
                "coverage_before": coverage_before,
                "coverage_after": coverage_after,
                "delta": report.delta
            }
        )

        return increased, entry

    async def check_sybil_direct(
        self,
        agent_id: str,
        file_path: str,
        content_hash: str
    ) -> tuple[bool, AuditLogEntry]:
        """
        Direct sybil check (blocking, for testing).

        Returns:
            Tuple of (sybil_detected, audit_entry)
        """
        event = FileEditEvent.create(
            agent_id=agent_id,
            file_path=file_path,
            content_hash=content_hash
        )

        sybil_detected = await self._sybil_detector.record_edit(event)

        decision = AuditDecision.FLAGGED if sybil_detected else AuditDecision.APPROVED
        reason = AuditReason.SYBIL_DETECTED if sybil_detected else AuditReason.VALID_CONTRIBUTION

        entry = await self._audit_log.append(
            agent_id=agent_id,
            action="file_edit",
            decision=decision,
            reason=reason,
            metadata={
                "file_path": file_path,
                "content_hash": content_hash,
                "sybil_detected": sybil_detected
            }
        )

        return sybil_detected, entry

    # Properties and stats

    @property
    def audit_log(self) -> ImmutableAuditLog:
        """Get the immutable audit log."""
        return self._audit_log

    @property
    def sybil_detector(self) -> SybilDetector:
        """Get the sybil detector."""
        return self._sybil_detector

    @property
    def coverage_verifier(self) -> CoverageVerifier:
        """Get the coverage verifier."""
        return self._coverage_verifier

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive auditor statistics."""
        return {
            "audit_log": self._audit_log.get_stats(),
            "sybil_detector": self._sybil_detector.get_stats(),
            "coverage_verifier": self._coverage_verifier.get_stats(),
            "queue_size": self._task_queue.qsize(),
            "processing": self._processing
        }


# Factory function
def create_auditor_service(
    audit_log_path: Optional[str] = None,
    reputation_callback: Optional[Callable[[str, int], None]] = None
) -> AuditorService:
    """
    Create an AuditorService instance.

    Args:
        audit_log_path: Optional path to persist audit log
        reputation_callback: Optional callback for reputation changes

    Returns:
        Configured AuditorService instance
    """
    path = Path(audit_log_path) if audit_log_path else None
    return AuditorService(
        audit_log_path=path,
        reputation_callback=reputation_callback
    )
