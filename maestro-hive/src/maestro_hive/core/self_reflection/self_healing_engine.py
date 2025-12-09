#!/usr/bin/env python3
"""
SelfHealingEngine: Complete Feedback Loop Integration

Part of MD-2533: Self-Healing Mechanism - Auto-Refactoring

This module orchestrates the complete self-healing loop:
1. Detect failures (FailureDetector)
2. Generate fixes (RefactoringEngine)
3. Apply and test fixes
4. Collect user feedback (FeedbackCollector)
5. Fall back to JIRA if auto-fix fails

Target: Enable Self-Reflection capability (15% -> 80%)

Architecture:
    ┌─────────────────────────────────────────────────────────────┐
    │                    SelfHealingEngine                        │
    │                                                             │
    │  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
    │  │FailureDetector│───▶│RefactoringEng│───▶│FixApplicator │  │
    │  └──────────────┘    └──────────────┘    └──────────────┘  │
    │         │                   │                   │          │
    │         ▼                   ▼                   ▼          │
    │  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
    │  │ExecutionHist │    │  RAG + LLM   │    │ TestRunner   │  │
    │  └──────────────┘    └──────────────┘    └──────────────┘  │
    │                                                │            │
    │                           ┌────────────────────┘            │
    │                           ▼                                 │
    │                    ┌──────────────┐                        │
    │                    │FeedbackCollect│                        │
    │                    └──────────────┘                        │
    │                           │                                 │
    │              ┌────────────┴────────────┐                   │
    │              ▼                         ▼                   │
    │       ┌──────────────┐         ┌──────────────┐           │
    │       │  Commit Fix  │         │ Gap-to-JIRA  │           │
    │       └──────────────┘         └──────────────┘           │
    └─────────────────────────────────────────────────────────────┘
"""

import json
import logging
import subprocess
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum

from .failure_detector import FailureDetector, Failure, Severity, FailureType
from .refactoring_engine import RefactoringEngine, Fix, FixStatus

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class HealingStatus(Enum):
    """Status of a healing attempt."""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    FIXED = "FIXED"
    AWAITING_REVIEW = "AWAITING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    JIRA_CREATED = "JIRA_CREATED"
    FAILED = "FAILED"


class FeedbackType(Enum):
    """Types of user feedback on fixes."""
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    MODIFY = "MODIFY"
    DEFER = "DEFER"


@dataclass
class HealingResult:
    """Result of a healing attempt."""
    failure: Failure
    fix: Optional[Fix]
    status: HealingStatus
    jira_ticket: Optional[str] = None
    feedback: Optional[Dict[str, Any]] = None
    duration_ms: int = 0
    attempts: int = 1
    error_message: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'failure': self.failure.to_dict(),
            'fix': self.fix.to_dict() if self.fix else None,
            'status': self.status.value,
            'jira_ticket': self.jira_ticket,
            'feedback': self.feedback,
            'duration_ms': self.duration_ms,
            'attempts': self.attempts,
            'error_message': self.error_message,
            'timestamp': self.timestamp
        }


@dataclass
class FeedbackRequest:
    """Request for user feedback on a fix."""
    fix: Fix
    failure: Failure
    preview_url: Optional[str] = None
    diff_content: str = ""
    auto_approve_deadline: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'fix_id': self.fix.fix_id,
            'failure_type': self.failure.failure_type.value,
            'target_file': self.fix.target_file,
            'confidence_score': self.fix.confidence_score,
            'diff_content': self.diff_content,
            'preview_url': self.preview_url,
            'auto_approve_deadline': self.auto_approve_deadline
        }


class FeedbackCollector:
    """
    Collects and processes user feedback on generated fixes.

    Supports:
    - Interactive CLI approval
    - Webhook-based async approval
    - Auto-approval for high-confidence fixes
    """

    def __init__(
        self,
        auto_approve_threshold: float = 0.95,
        webhook_url: Optional[str] = None
    ):
        """
        Initialize FeedbackCollector.

        Args:
            auto_approve_threshold: Confidence score for auto-approval
            webhook_url: URL for async feedback notifications
        """
        self.auto_approve_threshold = auto_approve_threshold
        self.webhook_url = webhook_url
        self.pending_requests: Dict[str, FeedbackRequest] = {}
        self.feedback_history: List[Dict[str, Any]] = []

    def request_feedback(
        self,
        fix: Fix,
        failure: Failure,
        callback: Optional[Callable[[FeedbackType, Dict], None]] = None
    ) -> FeedbackType:
        """
        Request user feedback on a fix.

        Args:
            fix: The generated fix
            failure: The original failure
            callback: Optional callback for async feedback

        Returns:
            FeedbackType indicating user decision
        """
        # Auto-approve if above threshold
        if fix.confidence_score >= self.auto_approve_threshold:
            logger.info(f"Auto-approving fix with confidence {fix.confidence_score}")
            self._record_feedback(fix, FeedbackType.APPROVE, {'auto': True})
            return FeedbackType.APPROVE

        # Create feedback request
        request = FeedbackRequest(
            fix=fix,
            failure=failure,
            diff_content=fix.get_unified_diff()
        )
        self.pending_requests[fix.fix_id] = request

        # If webhook configured, send async notification
        if self.webhook_url:
            self._send_webhook(request)
            return FeedbackType.DEFER

        # Interactive mode (CLI)
        return self._interactive_prompt(request)

    def process_feedback(
        self,
        fix_id: str,
        feedback_type: FeedbackType,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Process received feedback for a fix.

        Args:
            fix_id: ID of the fix
            feedback_type: Type of feedback
            metadata: Additional feedback data

        Returns:
            True if feedback was processed successfully
        """
        if fix_id not in self.pending_requests:
            logger.warning(f"No pending request for fix {fix_id}")
            return False

        request = self.pending_requests.pop(fix_id)
        self._record_feedback(request.fix, feedback_type, metadata or {})

        return True

    def _interactive_prompt(self, request: FeedbackRequest) -> FeedbackType:
        """Prompt user for feedback in CLI mode."""
        print("\n" + "=" * 60)
        print("FIX REVIEW REQUEST")
        print("=" * 60)
        print(f"File: {request.fix.target_file}")
        print(f"Failure: {request.failure.failure_type.value}")
        print(f"Error: {request.failure.error_message[:100]}")
        print(f"Confidence: {request.fix.confidence_score:.2%}")
        print("\nDiff:")
        print(request.diff_content[:500])
        print("..." if len(request.diff_content) > 500 else "")
        print("\n" + "-" * 60)

        try:
            choice = input("Approve this fix? [Y]es/[N]o/[M]odify/[D]efer: ").strip().upper()

            feedback_map = {
                'Y': FeedbackType.APPROVE,
                'YES': FeedbackType.APPROVE,
                'N': FeedbackType.REJECT,
                'NO': FeedbackType.REJECT,
                'M': FeedbackType.MODIFY,
                'D': FeedbackType.DEFER
            }

            feedback = feedback_map.get(choice, FeedbackType.DEFER)
            self._record_feedback(request.fix, feedback, {'interactive': True})
            return feedback

        except (EOFError, KeyboardInterrupt):
            # Non-interactive mode - defer
            return FeedbackType.DEFER

    def _send_webhook(self, request: FeedbackRequest):
        """Send webhook notification for async feedback."""
        if not self.webhook_url:
            return

        try:
            import requests
            requests.post(
                self.webhook_url,
                json=request.to_dict(),
                timeout=5
            )
        except Exception as e:
            logger.warning(f"Failed to send webhook: {e}")

    def _record_feedback(
        self,
        fix: Fix,
        feedback_type: FeedbackType,
        metadata: Dict[str, Any]
    ):
        """Record feedback for learning."""
        self.feedback_history.append({
            'fix_id': fix.fix_id,
            'fix_type': fix.fix_type,
            'confidence_score': fix.confidence_score,
            'feedback_type': feedback_type.value,
            'metadata': metadata,
            'timestamp': datetime.now().isoformat()
        })

    def get_approval_stats(self) -> Dict[str, Any]:
        """Get statistics on fix approvals."""
        total = len(self.feedback_history)
        if total == 0:
            return {'total': 0, 'approval_rate': 0.0}

        approved = sum(
            1 for f in self.feedback_history
            if f['feedback_type'] == FeedbackType.APPROVE.value
        )

        return {
            'total': total,
            'approved': approved,
            'rejected': sum(1 for f in self.feedback_history if f['feedback_type'] == FeedbackType.REJECT.value),
            'approval_rate': approved / total
        }


class SelfHealingEngine:
    """
    Main orchestrator for the self-healing feedback loop.

    Coordinates:
    - FailureDetector for finding failures
    - RefactoringEngine for generating fixes
    - FeedbackCollector for user approval
    - Gap-to-JIRA fallback for unfixable issues
    """

    def __init__(
        self,
        workspace_root: Optional[str] = None,
        auto_apply: bool = False,
        auto_approve_threshold: float = 0.95,
        max_retries: int = 3,
        jira_fallback: bool = True
    ):
        """
        Initialize SelfHealingEngine.

        Args:
            workspace_root: Root directory for operations
            auto_apply: Whether to auto-apply fixes without review
            auto_approve_threshold: Confidence for auto-approval
            max_retries: Maximum fix attempts per failure
            jira_fallback: Whether to create JIRA tickets for unfixable issues
        """
        self.workspace_root = Path(workspace_root) if workspace_root else Path.cwd()
        self.auto_apply = auto_apply
        self.max_retries = max_retries
        self.jira_fallback = jira_fallback

        # Initialize components
        self.detector = FailureDetector(str(self.workspace_root))
        self.refactorer = RefactoringEngine(str(self.workspace_root))
        self.feedback = FeedbackCollector(auto_approve_threshold=auto_approve_threshold)

        # Results tracking
        self.results: List[HealingResult] = []
        self.stats = {
            'failures_detected': 0,
            'fixes_generated': 0,
            'fixes_applied': 0,
            'fixes_verified': 0,
            'jira_created': 0,
            'total_runs': 0
        }

    def heal(
        self,
        pytest_output: Optional[str] = None,
        log_path: Optional[str] = None,
        execution_history: Optional[str] = None
    ) -> List[HealingResult]:
        """
        Run the complete self-healing loop.

        Args:
            pytest_output: Path to pytest output file
            log_path: Path to application logs
            execution_history: Path to execution history JSON

        Returns:
            List of HealingResult for each failure processed
        """
        start_time = datetime.now()
        self.stats['total_runs'] += 1

        logger.info("Starting self-healing loop...")

        # Phase 1: Detect failures
        failures = self._detect_failures(pytest_output, log_path, execution_history)
        self.stats['failures_detected'] += len(failures)

        if not failures:
            logger.info("No failures detected. System is healthy!")
            return []

        logger.info(f"Detected {len(failures)} failures")

        # Phase 2: Process each failure
        results = []
        for failure in failures:
            result = self.heal_single(failure)
            results.append(result)
            self.results.append(result)

        # Log summary
        self._log_summary(results, start_time)

        return results

    def heal_single(self, failure: Failure) -> HealingResult:
        """
        Attempt to heal a single failure.

        Args:
            failure: The failure to heal

        Returns:
            HealingResult indicating outcome
        """
        start_time = datetime.now()
        logger.info(f"Processing failure: {failure.failure_type.value} - {failure.error_message[:50]}")

        result = HealingResult(
            failure=failure,
            fix=None,
            status=HealingStatus.IN_PROGRESS
        )

        # Try to generate fix
        for attempt in range(self.max_retries):
            result.attempts = attempt + 1

            try:
                fix = self.refactorer.generate_fix(failure)

                if not fix:
                    logger.warning(f"Attempt {attempt + 1}: Failed to generate fix")
                    continue

                self.stats['fixes_generated'] += 1
                result.fix = fix

                # Get feedback (or auto-approve)
                if not self.auto_apply:
                    feedback = self.feedback.request_feedback(fix, failure)

                    if feedback == FeedbackType.REJECT:
                        result.status = HealingStatus.REJECTED
                        logger.info("Fix rejected by user")
                        break

                    if feedback == FeedbackType.DEFER:
                        result.status = HealingStatus.AWAITING_REVIEW
                        logger.info("Fix deferred for review")
                        break

                    if feedback == FeedbackType.MODIFY:
                        # User wants to modify - continue to next attempt
                        continue

                # Apply fix
                if self.refactorer.apply_fix(fix):
                    self.stats['fixes_applied'] += 1

                    # Test fix
                    if self.refactorer.test_fix(fix):
                        self.stats['fixes_verified'] += 1
                        result.status = HealingStatus.FIXED

                        # Record success for RAG learning
                        self.refactorer.rag.add_fix_to_history(failure, fix)

                        logger.info(f"Successfully fixed: {failure.file_path}")
                        break
                    else:
                        # Test failed - rollback
                        logger.warning("Fix failed tests, rolling back")
                        self.refactorer.rollback_fix(fix)
                else:
                    logger.warning("Failed to apply fix")

            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed with error: {e}")
                result.error_message = str(e)

        # Fall back to JIRA if not fixed
        if result.status not in (HealingStatus.FIXED, HealingStatus.AWAITING_REVIEW):
            if self.jira_fallback:
                jira_key = self._create_jira_ticket(failure)
                if jira_key:
                    result.status = HealingStatus.JIRA_CREATED
                    result.jira_ticket = jira_key
                    self.stats['jira_created'] += 1
                else:
                    result.status = HealingStatus.FAILED
            else:
                result.status = HealingStatus.FAILED

        # Calculate duration
        result.duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        return result

    def _detect_failures(
        self,
        pytest_output: Optional[str],
        log_path: Optional[str],
        execution_history: Optional[str]
    ) -> List[Failure]:
        """Detect failures from various sources."""
        failures = []

        if pytest_output:
            if pytest_output.endswith('.json'):
                failures.extend(self.detector.scan_pytest_json(pytest_output))
            else:
                failures.extend(self.detector.scan_pytest(pytest_output))

        if log_path:
            failures.extend(self.detector.scan_logs(log_path))

        if execution_history:
            failures.extend(self.detector.scan_execution_history(execution_history))

        # Sort by severity (CRITICAL first)
        severity_order = {
            Severity.CRITICAL: 0,
            Severity.HIGH: 1,
            Severity.MEDIUM: 2,
            Severity.LOW: 3
        }
        failures.sort(key=lambda f: severity_order.get(f.severity, 99))

        return failures

    def _create_jira_ticket(self, failure: Failure) -> Optional[str]:
        """Create a JIRA ticket for an unfixable failure."""
        try:
            # Import Gap-to-JIRA
            from .gap_to_jira import GapToJira, JiraConfig
            from .gap_detector import Gap

            config = JiraConfig.from_env()
            gap_to_jira = GapToJira(config)

            # Convert Failure to Gap format
            gap = Gap(
                block_id=f"auto_heal_{failure.failure_id}",
                block_name=f"Self-Healing: {failure.failure_type.value}",
                gap_type="RUNTIME_FAILURE",
                description=f"Auto-healing failed for:\n{failure.error_message}\n\nStack trace:\n{failure.stack_trace[:500]}",
                severity=failure.severity.value,
                remediation="Manual investigation required. Auto-fix attempts exhausted.",
                metadata={
                    'file_path': failure.file_path,
                    'line_number': failure.line_number,
                    'failure_type': failure.failure_type.value
                }
            )

            ticket_key = gap_to_jira.create_ticket(gap, prefix="[AUTO-HEAL-FAIL] ")
            logger.info(f"Created JIRA ticket: {ticket_key}")
            return ticket_key

        except Exception as e:
            logger.error(f"Failed to create JIRA ticket: {e}")
            return None

    def _log_summary(self, results: List[HealingResult], start_time: datetime):
        """Log summary of healing run."""
        duration = (datetime.now() - start_time).total_seconds()

        fixed = sum(1 for r in results if r.status == HealingStatus.FIXED)
        jira = sum(1 for r in results if r.status == HealingStatus.JIRA_CREATED)
        failed = sum(1 for r in results if r.status == HealingStatus.FAILED)

        logger.info("\n" + "=" * 60)
        logger.info("SELF-HEALING SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total failures: {len(results)}")
        logger.info(f"Fixed automatically: {fixed}")
        logger.info(f"JIRA tickets created: {jira}")
        logger.info(f"Failed: {failed}")
        logger.info(f"Duration: {duration:.2f}s")
        logger.info(f"Fix rate: {fixed / len(results) * 100:.1f}%")
        logger.info("=" * 60)

    def get_stats(self) -> Dict[str, Any]:
        """Get cumulative statistics."""
        fix_rate = 0.0
        if self.stats['failures_detected'] > 0:
            fix_rate = self.stats['fixes_verified'] / self.stats['failures_detected']

        return {
            **self.stats,
            'fix_rate': fix_rate,
            'feedback_stats': self.feedback.get_approval_stats()
        }

    def generate_report(self, output_format: str = 'text') -> str:
        """Generate a report of all healing results."""
        if output_format == 'json':
            return json.dumps({
                'stats': self.get_stats(),
                'results': [r.to_dict() for r in self.results]
            }, indent=2)

        # Text report
        lines = ["# Self-Healing Report", ""]

        stats = self.get_stats()
        lines.append(f"Total Runs: {stats['total_runs']}")
        lines.append(f"Failures Detected: {stats['failures_detected']}")
        lines.append(f"Fixes Generated: {stats['fixes_generated']}")
        lines.append(f"Fixes Applied: {stats['fixes_applied']}")
        lines.append(f"Fixes Verified: {stats['fixes_verified']}")
        lines.append(f"JIRA Created: {stats['jira_created']}")
        lines.append(f"Fix Rate: {stats['fix_rate']:.1%}")
        lines.append("")

        if self.results:
            lines.append("## Recent Results")
            for r in self.results[-10:]:
                status_emoji = {
                    HealingStatus.FIXED: "OK",
                    HealingStatus.JIRA_CREATED: "JIRA",
                    HealingStatus.FAILED: "FAIL",
                    HealingStatus.AWAITING_REVIEW: "PENDING"
                }.get(r.status, "?")

                lines.append(f"- [{status_emoji}] {r.failure.failure_type.value}: {r.failure.error_message[:50]}")

        return "\n".join(lines)


def main():
    """CLI entry point for self-healing."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Self-Healing Engine: Automatic failure detection and fixing"
    )
    parser.add_argument(
        '--pytest-output',
        help='Path to pytest output file'
    )
    parser.add_argument(
        '--log-path',
        help='Path to application log file'
    )
    parser.add_argument(
        '--execution-history',
        help='Path to execution history JSON'
    )
    parser.add_argument(
        '--auto-apply',
        action='store_true',
        help='Auto-apply fixes without review'
    )
    parser.add_argument(
        '--no-jira',
        action='store_true',
        help='Disable JIRA ticket creation for unfixable issues'
    )
    parser.add_argument(
        '--workspace',
        default=str(Path.cwd()),
        help='Workspace root directory'
    )
    parser.add_argument(
        '--report',
        choices=['text', 'json'],
        default='text',
        help='Output report format'
    )

    args = parser.parse_args()

    engine = SelfHealingEngine(
        workspace_root=args.workspace,
        auto_apply=args.auto_apply,
        jira_fallback=not args.no_jira
    )

    results = engine.heal(
        pytest_output=args.pytest_output,
        log_path=args.log_path,
        execution_history=args.execution_history
    )

    print(engine.generate_report(args.report))


if __name__ == "__main__":
    main()
