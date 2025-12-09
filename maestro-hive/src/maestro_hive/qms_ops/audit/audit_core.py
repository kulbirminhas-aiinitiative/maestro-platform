"""
Audit Core Module
=================

Provides core audit scheduling, execution, and logging capabilities.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time


class AuditStatus(Enum):
    """Status of an audit execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AuditTarget:
    """Target system or data to be audited."""
    id: str
    name: str
    type: str  # 'system', 'document', 'process'
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AuditResult:
    """Result of an audit execution."""
    audit_id: str
    target: AuditTarget
    status: AuditStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    findings: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration_seconds(self) -> float:
        """Calculate audit duration in seconds."""
        if self.completed_at and self.started_at:
            return (self.completed_at - self.started_at).total_seconds()
        return 0.0

    @property
    def is_successful(self) -> bool:
        """Check if audit completed without errors."""
        return self.status == AuditStatus.COMPLETED and len(self.errors) == 0


class AuditLogger:
    """Centralized audit logging with structured output."""

    def __init__(self, name: str = "qms-audit"):
        self.logger = logging.getLogger(name)
        self._configure_logger()

    def _configure_logger(self) -> None:
        """Configure logger with appropriate handlers."""
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def audit_start(self, audit_id: str, target: AuditTarget) -> None:
        """Log audit start event."""
        self.logger.info(
            f"AUDIT_START | audit_id={audit_id} | target={target.name} | type={target.type}"
        )

    def audit_complete(self, result: AuditResult) -> None:
        """Log audit completion event."""
        finding_count = len(result.findings)
        error_count = len(result.errors)
        self.logger.info(
            f"AUDIT_COMPLETE | audit_id={result.audit_id} | "
            f"status={result.status.value} | findings={finding_count} | "
            f"errors={error_count} | duration={result.duration_seconds:.2f}s"
        )

    def audit_error(self, audit_id: str, error: str) -> None:
        """Log audit error."""
        self.logger.error(f"AUDIT_ERROR | audit_id={audit_id} | error={error}")

    def finding_recorded(self, audit_id: str, severity: str, rule_id: str) -> None:
        """Log finding recorded event."""
        self.logger.info(
            f"FINDING | audit_id={audit_id} | severity={severity} | rule={rule_id}"
        )


class AuditExecutor:
    """Executes audit rules against targets."""

    def __init__(
        self,
        rule_engine: Any,  # RuleEngine type
        max_workers: int = 4,
        timeout_seconds: int = 300
    ):
        self.rule_engine = rule_engine
        self.max_workers = max_workers
        self.timeout_seconds = timeout_seconds
        self.logger = AuditLogger()
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    def execute(
        self,
        target: AuditTarget,
        rule_ids: Optional[List[str]] = None
    ) -> AuditResult:
        """
        Execute audit against a target.

        Args:
            target: The target to audit
            rule_ids: Optional list of specific rules to run

        Returns:
            AuditResult with findings and status
        """
        audit_id = str(uuid.uuid4())
        self.logger.audit_start(audit_id, target)

        result = AuditResult(
            audit_id=audit_id,
            target=target,
            status=AuditStatus.RUNNING,
            started_at=datetime.utcnow()
        )

        try:
            # Get rules to execute
            rules = self.rule_engine.get_rules(rule_ids)

            # Execute rules in parallel
            futures = {}
            for rule in rules:
                future = self._executor.submit(
                    self._evaluate_rule, rule, target
                )
                futures[future] = rule

            # Collect results with timeout
            for future in as_completed(futures, timeout=self.timeout_seconds):
                rule = futures[future]
                try:
                    rule_result = future.result()
                    if rule_result and not rule_result.passed:
                        finding = {
                            "rule_id": rule.id,
                            "rule_name": rule.name,
                            "severity": rule.severity.value,
                            "description": rule_result.message,
                            "evidence": rule_result.evidence,
                            "remediation": rule.remediation,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                        result.findings.append(finding)
                        self.logger.finding_recorded(
                            audit_id, rule.severity.value, rule.id
                        )
                except Exception as e:
                    error_msg = f"Rule {rule.id} failed: {str(e)}"
                    result.errors.append(error_msg)
                    self.logger.audit_error(audit_id, error_msg)

            result.status = AuditStatus.COMPLETED
            result.completed_at = datetime.utcnow()

        except Exception as e:
            result.status = AuditStatus.FAILED
            result.errors.append(str(e))
            result.completed_at = datetime.utcnow()
            self.logger.audit_error(audit_id, str(e))

        self.logger.audit_complete(result)
        return result

    def _evaluate_rule(self, rule: Any, target: AuditTarget) -> Any:
        """Evaluate a single rule against a target."""
        return self.rule_engine.evaluate(rule, target.metadata)

    def shutdown(self) -> None:
        """Shutdown the executor."""
        self._executor.shutdown(wait=True)


class AuditScheduler:
    """Schedules and manages recurring audits."""

    def __init__(self, executor: AuditExecutor):
        self.executor = executor
        self.scheduled_audits: Dict[str, Dict] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self.logger = AuditLogger()

    def schedule(
        self,
        target: AuditTarget,
        interval_seconds: int,
        rule_ids: Optional[List[str]] = None,
        callback: Optional[Callable[[AuditResult], None]] = None
    ) -> str:
        """
        Schedule a recurring audit.

        Args:
            target: Target to audit
            interval_seconds: Interval between audits
            rule_ids: Optional specific rules to run
            callback: Optional callback on audit completion

        Returns:
            Schedule ID
        """
        schedule_id = str(uuid.uuid4())
        self.scheduled_audits[schedule_id] = {
            "target": target,
            "interval": interval_seconds,
            "rule_ids": rule_ids,
            "callback": callback,
            "last_run": None,
            "next_run": datetime.utcnow()
        }
        self.logger.logger.info(
            f"SCHEDULE_CREATED | schedule_id={schedule_id} | "
            f"target={target.name} | interval={interval_seconds}s"
        )
        return schedule_id

    def unschedule(self, schedule_id: str) -> bool:
        """Remove a scheduled audit."""
        if schedule_id in self.scheduled_audits:
            del self.scheduled_audits[schedule_id]
            self.logger.logger.info(f"SCHEDULE_REMOVED | schedule_id={schedule_id}")
            return True
        return False

    def start(self) -> None:
        """Start the scheduler background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self.logger.logger.info("SCHEDULER_STARTED")

    def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        self.logger.logger.info("SCHEDULER_STOPPED")

    def _run_loop(self) -> None:
        """Main scheduler loop."""
        while self._running:
            now = datetime.utcnow()
            for schedule_id, config in list(self.scheduled_audits.items()):
                if config["next_run"] <= now:
                    try:
                        result = self.executor.execute(
                            config["target"],
                            config["rule_ids"]
                        )
                        config["last_run"] = now
                        config["next_run"] = datetime.utcnow() + \
                            __import__('datetime').timedelta(seconds=config["interval"])

                        if config["callback"]:
                            config["callback"](result)

                    except Exception as e:
                        self.logger.audit_error(schedule_id, str(e))

            time.sleep(1)  # Check every second


class AuditCore:
    """
    Main entry point for the audit system.

    Provides unified access to audit execution, scheduling, and management.
    """

    def __init__(
        self,
        rule_engine: Any,
        max_workers: int = 4,
        timeout_seconds: int = 300
    ):
        self.executor = AuditExecutor(
            rule_engine=rule_engine,
            max_workers=max_workers,
            timeout_seconds=timeout_seconds
        )
        self.scheduler = AuditScheduler(self.executor)
        self.logger = AuditLogger()

    def run_audit(
        self,
        target: AuditTarget,
        rule_ids: Optional[List[str]] = None
    ) -> AuditResult:
        """Run a one-time audit."""
        return self.executor.execute(target, rule_ids)

    def schedule_audit(
        self,
        target: AuditTarget,
        interval_seconds: int,
        rule_ids: Optional[List[str]] = None,
        callback: Optional[Callable[[AuditResult], None]] = None
    ) -> str:
        """Schedule a recurring audit."""
        return self.scheduler.schedule(target, interval_seconds, rule_ids, callback)

    def start_scheduler(self) -> None:
        """Start the audit scheduler."""
        self.scheduler.start()

    def stop_scheduler(self) -> None:
        """Stop the audit scheduler."""
        self.scheduler.stop()

    def shutdown(self) -> None:
        """Shutdown all audit components."""
        self.scheduler.stop()
        self.executor.shutdown()
