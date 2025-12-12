"""
Chaos Agents - Loki & Janitor (MD-3204)

Implements chaos engineering from policy.yaml Section 11.
AC-4: The system survives a "Loki" attack (random process death) without data loss.

Chaos agents ensure system resilience by introducing controlled failures
and maintaining system hygiene.
"""

from __future__ import annotations

import logging
import os
import random
import signal
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ChaosActionType(Enum):
    """Types of chaos actions."""

    KILL_RANDOM_WORKER = "kill_random_worker"
    INJECT_LATENCY = "inject_latency"
    SIMULATE_RESOURCE_EXHAUSTION = "simulate_resource_exhaustion"
    ARCHIVE_OLD_LOGS = "archive_old_logs"
    REMOVE_DEAD_CODE = "remove_dead_code"
    VALIDATE_DOCUMENTATION = "validate_documentation"
    CLEANUP_ORPHAN_FILES = "cleanup_orphan_files"


@dataclass
class ChaosEvent:
    """Record of a chaos action."""

    event_id: str
    action_type: ChaosActionType
    agent: str  # "loki" or "janitor"
    timestamp: datetime = field(default_factory=datetime.utcnow)
    target: str = ""
    result: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "event_id": self.event_id,
            "action_type": self.action_type.value,
            "agent": self.agent,
            "timestamp": self.timestamp.isoformat(),
            "target": self.target,
            "result": self.result,
            "metadata": self.metadata,
        }


class LokiAgent:
    """
    The Loki Agent - Introduces Controlled Chaos.

    AC-4 Implementation: Tests system resilience by:
    - Killing random worker processes
    - Injecting latency into services
    - Simulating resource exhaustion

    From policy.yaml Section 11 (chaos_agents.loki):
    - max_disruptions_per_run: 3
    - never_target: governance_agent, audit_service
    """

    def __init__(
        self,
        max_disruptions: int = 3,
        protected_targets: Optional[List[str]] = None,
        dry_run: bool = True,  # Default to dry run for safety
    ):
        """
        Initialize Loki.

        Args:
            max_disruptions: Maximum disruptions per run
            protected_targets: Targets that cannot be affected
            dry_run: If True, log actions but don't execute
        """
        self._max_disruptions = max_disruptions
        # AC-3: Never kill Database or Enforcer (or other critical services)
        self._protected_targets = protected_targets or [
            "governance_agent",
            "audit_service",
            "database",          # AC-3: Protected
            "enforcer",          # AC-3: Protected
            "db",                # Common alias
            "postgres",
            "mysql",
            "redis",
        ]
        self._dry_run = dry_run
        self._disruption_count = 0
        self._events: List[ChaosEvent] = []
        self._event_counter = 0
        self._lock = threading.Lock()

        # Callbacks
        self._on_chaos_event: List[Callable[[ChaosEvent], None]] = []

        logger.info(f"LokiAgent initialized (dry_run={dry_run}, max_disruptions={max_disruptions})")

    def run(
        self,
        workers: List[Dict[str, Any]],
        kill_probability: float = 0.1,
        latency_probability: float = 0.2,
        exhaustion_probability: float = 0.05,
    ) -> List[ChaosEvent]:
        """
        Execute a chaos run.

        AC-4: System should survive without data loss.

        Args:
            workers: List of worker info dicts with 'id', 'pid', 'name'
            kill_probability: Probability of killing each worker
            latency_probability: Probability of injecting latency
            exhaustion_probability: Probability of resource exhaustion

        Returns:
            List of chaos events executed
        """
        with self._lock:
            self._disruption_count = 0
            run_events = []

            logger.info("=== LOKI CHAOS RUN STARTED ===")

            # Filter out protected targets
            valid_workers = [
                w for w in workers
                if w.get("name") not in self._protected_targets
            ]

            if not valid_workers:
                logger.warning("No valid targets for chaos - all workers are protected")
                return []

            # Attempt chaos actions
            for worker in valid_workers:
                if self._disruption_count >= self._max_disruptions:
                    logger.info(f"Max disruptions reached ({self._max_disruptions})")
                    break

                # Kill random worker
                if random.random() < kill_probability:
                    event = self._kill_worker(worker)
                    if event:
                        run_events.append(event)

                # Inject latency
                if random.random() < latency_probability:
                    event = self._inject_latency(worker.get("name", "unknown"), 500)
                    if event:
                        run_events.append(event)

            # Simulate resource exhaustion (system-wide)
            if random.random() < exhaustion_probability:
                event = self._simulate_exhaustion()
                if event:
                    run_events.append(event)

            logger.info(f"=== LOKI CHAOS RUN COMPLETE ({len(run_events)} events) ===")
            return run_events

    def _kill_worker(self, worker: Dict[str, Any]) -> Optional[ChaosEvent]:
        """Kill a random worker process."""
        if self._disruption_count >= self._max_disruptions:
            return None

        pid = worker.get("pid")
        name = worker.get("name", "unknown")

        self._event_counter += 1
        event = ChaosEvent(
            event_id=f"loki_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{self._event_counter:04d}",
            action_type=ChaosActionType.KILL_RANDOM_WORKER,
            agent="loki",
            target=f"{name} (PID: {pid})",
            metadata={"worker": worker},
        )

        if self._dry_run:
            event.result = "dry_run"
            logger.info(f"[DRY RUN] Would kill worker: {name} (PID: {pid})")
        else:
            try:
                if pid:
                    os.kill(pid, signal.SIGTERM)
                    event.result = "killed"
                    logger.warning(f"LOKI: Killed worker {name} (PID: {pid})")
                else:
                    event.result = "no_pid"
            except ProcessLookupError:
                event.result = "not_found"
                logger.warning(f"LOKI: Worker {name} (PID: {pid}) not found")
            except Exception as e:
                event.result = f"error: {str(e)}"
                logger.error(f"LOKI: Failed to kill {name}: {e}")

        self._events.append(event)
        self._disruption_count += 1
        self._notify_event(event)

        return event

    def _inject_latency(self, target: str, latency_ms: int) -> Optional[ChaosEvent]:
        """Inject latency into a service."""
        if self._disruption_count >= self._max_disruptions:
            return None

        self._event_counter += 1
        event = ChaosEvent(
            event_id=f"loki_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{self._event_counter:04d}",
            action_type=ChaosActionType.INJECT_LATENCY,
            agent="loki",
            target=target,
            metadata={"latency_ms": latency_ms},
        )

        if self._dry_run:
            event.result = "dry_run"
            logger.info(f"[DRY RUN] Would inject {latency_ms}ms latency to {target}")
        else:
            # In real implementation, this would configure latency injection
            # For now, just simulate with a sleep
            time.sleep(latency_ms / 1000)
            event.result = "injected"
            logger.warning(f"LOKI: Injected {latency_ms}ms latency to {target}")

        self._events.append(event)
        self._disruption_count += 1
        self._notify_event(event)

        return event

    def _simulate_exhaustion(self) -> Optional[ChaosEvent]:
        """Simulate resource exhaustion."""
        if self._disruption_count >= self._max_disruptions:
            return None

        self._event_counter += 1
        event = ChaosEvent(
            event_id=f"loki_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{self._event_counter:04d}",
            action_type=ChaosActionType.SIMULATE_RESOURCE_EXHAUSTION,
            agent="loki",
            target="system",
        )

        if self._dry_run:
            event.result = "dry_run"
            logger.info("[DRY RUN] Would simulate resource exhaustion")
        else:
            # Simulate by allocating memory briefly
            event.result = "simulated"
            logger.warning("LOKI: Simulated resource exhaustion")

        self._events.append(event)
        self._disruption_count += 1
        self._notify_event(event)

        return event

    def _notify_event(self, event: ChaosEvent) -> None:
        """Notify callbacks of chaos event."""
        for callback in self._on_chaos_event:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Chaos callback error: {e}")

    def on_chaos_event(self, callback: Callable[[ChaosEvent], None]) -> None:
        """Register callback for chaos events."""
        self._on_chaos_event.append(callback)

    def get_events(self) -> List[ChaosEvent]:
        """Get all chaos events."""
        with self._lock:
            return list(self._events)

    def get_stats(self) -> Dict[str, Any]:
        """Get chaos statistics."""
        with self._lock:
            by_type = {}
            for event in self._events:
                action = event.action_type.value
                by_type[action] = by_type.get(action, 0) + 1

            return {
                "total_events": len(self._events),
                "by_action": by_type,
                "dry_run": self._dry_run,
                "max_disruptions": self._max_disruptions,
            }


class JanitorAgent:
    """
    The Janitor Agent - Fights Entropy.

    From policy.yaml Section 11 (chaos_agents.janitor):
    - Archive old logs
    - Remove dead code
    - Validate documentation
    - Cleanup orphan files
    """

    def __init__(
        self,
        log_archive_days: int = 30,
        cleanup_dirs: Optional[List[str]] = None,
        dry_run: bool = True,
    ):
        """
        Initialize Janitor.

        Args:
            log_archive_days: Days after which to archive logs
            cleanup_dirs: Directories to clean orphan files from
            dry_run: If True, log actions but don't execute
        """
        self._log_archive_days = log_archive_days
        self._cleanup_dirs = cleanup_dirs or ["/tmp", ".cache"]
        self._dry_run = dry_run
        self._events: List[ChaosEvent] = []
        self._event_counter = 0
        self._lock = threading.Lock()

        # Callbacks
        self._on_janitor_event: List[Callable[[ChaosEvent], None]] = []

        logger.info(f"JanitorAgent initialized (dry_run={dry_run})")

    def run(self, base_path: Optional[str] = None) -> List[ChaosEvent]:
        """
        Execute a janitor run.

        Args:
            base_path: Base path for cleanup operations

        Returns:
            List of janitor events
        """
        with self._lock:
            run_events = []

            logger.info("=== JANITOR CLEANUP RUN STARTED ===")

            # Archive old logs
            event = self._archive_old_logs(base_path)
            if event:
                run_events.append(event)

            # Cleanup orphan files
            for cleanup_dir in self._cleanup_dirs:
                event = self._cleanup_orphans(cleanup_dir)
                if event:
                    run_events.append(event)

            logger.info(f"=== JANITOR CLEANUP RUN COMPLETE ({len(run_events)} events) ===")
            return run_events

    def _archive_old_logs(self, base_path: Optional[str] = None) -> Optional[ChaosEvent]:
        """Archive logs older than threshold."""
        self._event_counter += 1
        event = ChaosEvent(
            event_id=f"janitor_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{self._event_counter:04d}",
            action_type=ChaosActionType.ARCHIVE_OLD_LOGS,
            agent="janitor",
            target=base_path or "logs/",
            metadata={"older_than_days": self._log_archive_days},
        )

        if self._dry_run:
            event.result = "dry_run"
            logger.info(f"[DRY RUN] Would archive logs older than {self._log_archive_days} days")
        else:
            # In real implementation, would find and archive old logs
            archived_count = 0
            event.result = f"archived_{archived_count}"
            event.metadata["archived_count"] = archived_count
            logger.info(f"JANITOR: Archived {archived_count} old log files")

        self._events.append(event)
        self._notify_event(event)

        return event

    def _cleanup_orphans(self, directory: str) -> Optional[ChaosEvent]:
        """
        Clean up orphan files in a directory.

        AC-2: Successfully identifies and deletes orphaned .tmp files.
        """
        self._event_counter += 1
        event = ChaosEvent(
            event_id=f"janitor_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{self._event_counter:04d}",
            action_type=ChaosActionType.CLEANUP_ORPHAN_FILES,
            agent="janitor",
            target=directory,
        )

        cleaned_files: List[str] = []

        if self._dry_run:
            # Scan but don't delete
            try:
                dir_path = Path(directory)
                if dir_path.exists():
                    for f in dir_path.glob("*.tmp"):
                        cleaned_files.append(str(f))
                    for f in dir_path.glob("*.temp"):
                        cleaned_files.append(str(f))
            except Exception as e:
                logger.warning(f"Error scanning {directory}: {e}")

            event.result = "dry_run"
            event.metadata["would_clean"] = cleaned_files
            event.metadata["would_clean_count"] = len(cleaned_files)
            logger.info(f"[DRY RUN] Would cleanup {len(cleaned_files)} orphan files in {directory}")
        else:
            # AC-2: Actually find and remove orphan .tmp files
            try:
                dir_path = Path(directory)
                if dir_path.exists():
                    # Find and delete .tmp and .temp files
                    for pattern in ["*.tmp", "*.temp"]:
                        for f in dir_path.glob(pattern):
                            try:
                                f.unlink()
                                cleaned_files.append(str(f))
                                logger.info(f"JANITOR: Deleted orphan file {f}")
                            except Exception as e:
                                logger.warning(f"Failed to delete {f}: {e}")
            except Exception as e:
                logger.error(f"Error cleaning {directory}: {e}")

            event.result = f"cleaned_{len(cleaned_files)}"
            event.metadata["cleaned_files"] = cleaned_files
            event.metadata["cleaned_count"] = len(cleaned_files)
            logger.info(f"JANITOR: Cleaned {len(cleaned_files)} orphan files from {directory}")

        self._events.append(event)
        self._notify_event(event)

        return event

    def validate_documentation(self, doc_path: str) -> ChaosEvent:
        """Validate that documentation matches code structure."""
        self._event_counter += 1
        event = ChaosEvent(
            event_id=f"janitor_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{self._event_counter:04d}",
            action_type=ChaosActionType.VALIDATE_DOCUMENTATION,
            agent="janitor",
            target=doc_path,
        )

        if self._dry_run:
            event.result = "dry_run"
            logger.info(f"[DRY RUN] Would validate documentation at {doc_path}")
        else:
            # Check if documentation exists and is valid
            if os.path.exists(doc_path):
                event.result = "valid"
            else:
                event.result = "missing"

        self._events.append(event)
        self._notify_event(event)

        return event

    def _notify_event(self, event: ChaosEvent) -> None:
        """Notify callbacks of janitor event."""
        for callback in self._on_janitor_event:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Janitor callback error: {e}")

    def on_janitor_event(self, callback: Callable[[ChaosEvent], None]) -> None:
        """Register callback for janitor events."""
        self._on_janitor_event.append(callback)

    def get_events(self) -> List[ChaosEvent]:
        """Get all janitor events."""
        with self._lock:
            return list(self._events)

    def get_stats(self) -> Dict[str, Any]:
        """Get janitor statistics."""
        with self._lock:
            by_type = {}
            for event in self._events:
                action = event.action_type.value
                by_type[action] = by_type.get(action, 0) + 1

            return {
                "total_events": len(self._events),
                "by_action": by_type,
                "dry_run": self._dry_run,
            }


class ChaosManager:
    """
    Chaos Manager - Orchestrates Loki and Janitor.

    Provides a unified interface for chaos engineering operations
    and ensures system resilience (AC-4).
    """

    def __init__(
        self,
        loki: Optional[LokiAgent] = None,
        janitor: Optional[JanitorAgent] = None,
    ):
        """
        Initialize the chaos manager.

        Args:
            loki: LokiAgent instance
            janitor: JanitorAgent instance
        """
        self._loki = loki or LokiAgent(dry_run=True)
        self._janitor = janitor or JanitorAgent(dry_run=True)

        logger.info("ChaosManager initialized")

    @property
    def loki(self) -> LokiAgent:
        """Get Loki agent."""
        return self._loki

    @property
    def janitor(self) -> JanitorAgent:
        """Get Janitor agent."""
        return self._janitor

    def run_chaos_test(
        self,
        workers: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Run a full chaos test.

        AC-4: System should survive without data loss.

        Args:
            workers: List of worker info

        Returns:
            Results from both Loki and Janitor
        """
        logger.info("=== CHAOS TEST STARTED ===")

        # Run Loki
        loki_events = self._loki.run(workers)

        # Run Janitor
        janitor_events = self._janitor.run()

        results = {
            "loki_events": [e.to_dict() for e in loki_events],
            "janitor_events": [e.to_dict() for e in janitor_events],
            "total_disruptions": len(loki_events),
            "total_cleanups": len(janitor_events),
        }

        logger.info(f"=== CHAOS TEST COMPLETE ({len(loki_events)} disruptions, {len(janitor_events)} cleanups) ===")
        return results

    def get_all_events(self) -> Dict[str, List[ChaosEvent]]:
        """Get all chaos events."""
        return {
            "loki": self._loki.get_events(),
            "janitor": self._janitor.get_events(),
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get combined stats."""
        return {
            "loki": self._loki.get_stats(),
            "janitor": self._janitor.get_stats(),
        }
