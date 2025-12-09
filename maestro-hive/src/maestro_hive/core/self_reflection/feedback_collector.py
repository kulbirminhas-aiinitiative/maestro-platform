#!/usr/bin/env python3
"""
FeedbackCollector: User Feedback Integration for Fix Approval

Part of MD-2533: Self-Healing Mechanism - Auto-Refactoring (AC-4)

This module provides comprehensive user feedback collection for:
1. Fix approval/rejection workflows
2. Learning from feedback to improve future fixes
3. Integration with external review systems (Slack, GitHub PRs, etc.)

The feedback loop enables the self-healing system to:
- Learn from human corrections
- Build confidence in fix patterns
- Route complex issues to appropriate reviewers
"""

import json
import logging
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable, Union
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from enum import Enum
from threading import Thread, Event
import queue

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class FeedbackType(Enum):
    """Types of user feedback on fixes."""
    APPROVE = "APPROVE"
    APPROVE_WITH_MODIFICATION = "APPROVE_WITH_MODIFICATION"
    REJECT = "REJECT"
    REJECT_BAD_FIX = "REJECT_BAD_FIX"
    REJECT_WRONG_ROOT_CAUSE = "REJECT_WRONG_ROOT_CAUSE"
    MODIFY = "MODIFY"
    DEFER = "DEFER"
    ESCALATE = "ESCALATE"


class ReviewerType(Enum):
    """Types of reviewers for fixes."""
    AUTO = "AUTO"
    HUMAN = "HUMAN"
    TEAM_LEAD = "TEAM_LEAD"
    SYSTEM = "SYSTEM"


@dataclass
class FeedbackRecord:
    """
    Record of feedback on a fix.

    Used for learning and improving future fix generation.
    """
    feedback_id: str
    fix_id: str
    failure_type: str
    fix_type: str
    original_confidence: float
    feedback_type: FeedbackType
    reviewer_type: ReviewerType
    reviewer_id: Optional[str] = None
    comments: str = ""
    modifications: Optional[str] = None  # Modified fix content if applicable
    target_file: str = ""
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['feedback_type'] = self.feedback_type.value
        d['reviewer_type'] = self.reviewer_type.value
        return d


@dataclass
class FeedbackStats:
    """Statistics for feedback analysis."""
    total_feedback: int = 0
    approvals: int = 0
    rejections: int = 0
    modifications: int = 0
    escalations: int = 0
    avg_confidence_approved: float = 0.0
    avg_confidence_rejected: float = 0.0
    approval_rate: float = 0.0
    by_fix_type: Dict[str, Dict[str, int]] = field(default_factory=dict)
    by_failure_type: Dict[str, Dict[str, int]] = field(default_factory=dict)


class FeedbackStore:
    """
    Persistent storage for feedback records.

    Supports:
    - JSON file storage
    - In-memory caching
    - Query by various criteria
    """

    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize FeedbackStore.

        Args:
            storage_path: Path to JSON storage file
        """
        self.storage_path = Path(storage_path) if storage_path else None
        self._records: List[FeedbackRecord] = []
        self._index_by_fix: Dict[str, List[FeedbackRecord]] = {}
        self._index_by_type: Dict[str, List[FeedbackRecord]] = {}

        if self.storage_path and self.storage_path.exists():
            self._load()

    def add(self, record: FeedbackRecord):
        """Add a feedback record."""
        self._records.append(record)

        # Update indexes
        if record.fix_id not in self._index_by_fix:
            self._index_by_fix[record.fix_id] = []
        self._index_by_fix[record.fix_id].append(record)

        if record.fix_type not in self._index_by_type:
            self._index_by_type[record.fix_type] = []
        self._index_by_type[record.fix_type].append(record)

        # Persist
        if self.storage_path:
            self._save()

    def get_by_fix_id(self, fix_id: str) -> List[FeedbackRecord]:
        """Get all feedback for a fix."""
        return self._index_by_fix.get(fix_id, [])

    def get_by_fix_type(self, fix_type: str) -> List[FeedbackRecord]:
        """Get all feedback for a fix type."""
        return self._index_by_type.get(fix_type, [])

    def get_recent(self, days: int = 30) -> List[FeedbackRecord]:
        """Get recent feedback records."""
        cutoff = datetime.now() - timedelta(days=days)
        return [
            r for r in self._records
            if datetime.fromisoformat(r.timestamp) > cutoff
        ]

    def calculate_stats(self) -> FeedbackStats:
        """Calculate statistics from feedback records."""
        stats = FeedbackStats()

        if not self._records:
            return stats

        stats.total_feedback = len(self._records)

        approved_conf = []
        rejected_conf = []

        for record in self._records:
            if record.feedback_type in (FeedbackType.APPROVE, FeedbackType.APPROVE_WITH_MODIFICATION):
                stats.approvals += 1
                approved_conf.append(record.original_confidence)
            elif record.feedback_type in (FeedbackType.REJECT, FeedbackType.REJECT_BAD_FIX, FeedbackType.REJECT_WRONG_ROOT_CAUSE):
                stats.rejections += 1
                rejected_conf.append(record.original_confidence)
            elif record.feedback_type == FeedbackType.MODIFY:
                stats.modifications += 1
            elif record.feedback_type == FeedbackType.ESCALATE:
                stats.escalations += 1

            # By fix type
            if record.fix_type not in stats.by_fix_type:
                stats.by_fix_type[record.fix_type] = {'approved': 0, 'rejected': 0}
            if record.feedback_type in (FeedbackType.APPROVE, FeedbackType.APPROVE_WITH_MODIFICATION):
                stats.by_fix_type[record.fix_type]['approved'] += 1
            elif record.feedback_type.value.startswith('REJECT'):
                stats.by_fix_type[record.fix_type]['rejected'] += 1

            # By failure type
            if record.failure_type not in stats.by_failure_type:
                stats.by_failure_type[record.failure_type] = {'approved': 0, 'rejected': 0}
            if record.feedback_type in (FeedbackType.APPROVE, FeedbackType.APPROVE_WITH_MODIFICATION):
                stats.by_failure_type[record.failure_type]['approved'] += 1
            elif record.feedback_type.value.startswith('REJECT'):
                stats.by_failure_type[record.failure_type]['rejected'] += 1

        if approved_conf:
            stats.avg_confidence_approved = sum(approved_conf) / len(approved_conf)
        if rejected_conf:
            stats.avg_confidence_rejected = sum(rejected_conf) / len(rejected_conf)

        if stats.total_feedback > 0:
            stats.approval_rate = stats.approvals / stats.total_feedback

        return stats

    def _load(self):
        """Load records from storage."""
        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)
                for item in data:
                    item['feedback_type'] = FeedbackType(item['feedback_type'])
                    item['reviewer_type'] = ReviewerType(item['reviewer_type'])
                    record = FeedbackRecord(**item)
                    self._records.append(record)
                    # Rebuild indexes
                    if record.fix_id not in self._index_by_fix:
                        self._index_by_fix[record.fix_id] = []
                    self._index_by_fix[record.fix_id].append(record)
                    if record.fix_type not in self._index_by_type:
                        self._index_by_type[record.fix_type] = []
                    self._index_by_type[record.fix_type].append(record)
        except Exception as e:
            logger.warning(f"Failed to load feedback store: {e}")

    def _save(self):
        """Save records to storage."""
        if not self.storage_path:
            return
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.storage_path, 'w') as f:
                json.dump([r.to_dict() for r in self._records], f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save feedback store: {e}")


class FeedbackChannel:
    """
    Base class for feedback channels.

    Channels provide different ways to collect feedback:
    - CLI: Interactive terminal prompts
    - Webhook: HTTP callbacks
    - Slack: Slack message integration
    - GitHub: PR review integration
    """

    def request_feedback(
        self,
        fix_id: str,
        fix_type: str,
        target_file: str,
        diff_content: str,
        confidence: float,
        failure_info: Dict[str, Any]
    ) -> Optional[FeedbackType]:
        """Request feedback through this channel."""
        raise NotImplementedError

    def is_async(self) -> bool:
        """Whether this channel provides feedback asynchronously."""
        return False


class CLIFeedbackChannel(FeedbackChannel):
    """Interactive CLI feedback channel."""

    def request_feedback(
        self,
        fix_id: str,
        fix_type: str,
        target_file: str,
        diff_content: str,
        confidence: float,
        failure_info: Dict[str, Any]
    ) -> Optional[FeedbackType]:
        """Prompt user for feedback in CLI."""
        print("\n" + "=" * 70)
        print("FIX REVIEW REQUEST")
        print("=" * 70)
        print(f"Fix ID: {fix_id}")
        print(f"Fix Type: {fix_type}")
        print(f"Target: {target_file}")
        print(f"Confidence: {confidence:.1%}")
        print("-" * 70)
        print(f"Failure: {failure_info.get('type', 'Unknown')}")
        print(f"Error: {failure_info.get('message', 'No message')[:100]}")
        print("-" * 70)
        print("Proposed Diff:")
        # Truncate long diffs
        if len(diff_content) > 1000:
            print(diff_content[:1000])
            print(f"... ({len(diff_content) - 1000} more characters)")
        else:
            print(diff_content)
        print("-" * 70)
        print("\nOptions:")
        print("  [A] Approve - Apply this fix")
        print("  [R] Reject - Do not apply")
        print("  [M] Modify - Make changes before applying")
        print("  [E] Escalate - Send to team lead")
        print("  [D] Defer - Decide later")
        print("")

        try:
            choice = input("Your choice: ").strip().upper()

            choice_map = {
                'A': FeedbackType.APPROVE,
                'R': FeedbackType.REJECT,
                'M': FeedbackType.MODIFY,
                'E': FeedbackType.ESCALATE,
                'D': FeedbackType.DEFER
            }

            return choice_map.get(choice, FeedbackType.DEFER)

        except (EOFError, KeyboardInterrupt):
            return FeedbackType.DEFER


class WebhookFeedbackChannel(FeedbackChannel):
    """Webhook-based async feedback channel."""

    def __init__(self, webhook_url: str, callback_url: Optional[str] = None):
        self.webhook_url = webhook_url
        self.callback_url = callback_url
        self._pending: Dict[str, Event] = {}
        self._results: Dict[str, FeedbackType] = {}

    def request_feedback(
        self,
        fix_id: str,
        fix_type: str,
        target_file: str,
        diff_content: str,
        confidence: float,
        failure_info: Dict[str, Any]
    ) -> Optional[FeedbackType]:
        """Send webhook request for feedback."""
        try:
            import requests

            payload = {
                'fix_id': fix_id,
                'fix_type': fix_type,
                'target_file': target_file,
                'diff_content': diff_content[:5000],  # Limit size
                'confidence': confidence,
                'failure_info': failure_info,
                'callback_url': self.callback_url,
                'timestamp': datetime.now().isoformat()
            }

            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )

            if response.status_code == 200:
                logger.info(f"Webhook sent for fix {fix_id}")
                return FeedbackType.DEFER  # Async - will receive callback
            else:
                logger.warning(f"Webhook failed: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Webhook error: {e}")
            return None

    def is_async(self) -> bool:
        return True

    def receive_callback(self, fix_id: str, feedback_type: str) -> bool:
        """Process callback from webhook."""
        try:
            ft = FeedbackType(feedback_type)
            self._results[fix_id] = ft
            if fix_id in self._pending:
                self._pending[fix_id].set()
            return True
        except ValueError:
            return False


class FeedbackCollector:
    """
    Main feedback collection coordinator.

    Manages multiple feedback channels and aggregates results.
    """

    def __init__(
        self,
        storage_path: Optional[str] = None,
        auto_approve_threshold: float = 0.95,
        auto_reject_threshold: float = 0.3,
        default_channel: str = 'cli'
    ):
        """
        Initialize FeedbackCollector.

        Args:
            storage_path: Path for feedback persistence
            auto_approve_threshold: Confidence for auto-approval
            auto_reject_threshold: Confidence below which to auto-reject
            default_channel: Default feedback channel ('cli', 'webhook')
        """
        self.store = FeedbackStore(storage_path)
        self.auto_approve_threshold = auto_approve_threshold
        self.auto_reject_threshold = auto_reject_threshold
        self.default_channel = default_channel

        self._channels: Dict[str, FeedbackChannel] = {
            'cli': CLIFeedbackChannel()
        }

        self._pending_requests: Dict[str, Dict[str, Any]] = {}
        self._feedback_queue: queue.Queue = queue.Queue()

    def add_channel(self, name: str, channel: FeedbackChannel):
        """Add a feedback channel."""
        self._channels[name] = channel

    def request_feedback(
        self,
        fix_id: str,
        fix_type: str,
        target_file: str,
        diff_content: str,
        confidence: float,
        failure_type: str,
        error_message: str,
        channel: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> FeedbackType:
        """
        Request feedback on a fix.

        Args:
            fix_id: Unique fix identifier
            fix_type: Type of fix (import, typo, etc.)
            target_file: File being fixed
            diff_content: Unified diff of the fix
            confidence: Confidence score of the fix
            failure_type: Type of failure being fixed
            error_message: Original error message
            channel: Specific channel to use
            tags: Tags for categorization

        Returns:
            FeedbackType indicating the decision
        """
        # Check for auto-approve
        if confidence >= self.auto_approve_threshold:
            logger.info(f"Auto-approving fix {fix_id} with confidence {confidence:.1%}")
            self._record_feedback(
                fix_id=fix_id,
                fix_type=fix_type,
                failure_type=failure_type,
                confidence=confidence,
                feedback_type=FeedbackType.APPROVE,
                reviewer_type=ReviewerType.AUTO,
                target_file=target_file,
                tags=tags or []
            )
            return FeedbackType.APPROVE

        # Check for auto-reject
        if confidence <= self.auto_reject_threshold:
            logger.info(f"Auto-rejecting fix {fix_id} with confidence {confidence:.1%}")
            self._record_feedback(
                fix_id=fix_id,
                fix_type=fix_type,
                failure_type=failure_type,
                confidence=confidence,
                feedback_type=FeedbackType.REJECT,
                reviewer_type=ReviewerType.AUTO,
                target_file=target_file,
                comments="Confidence below threshold",
                tags=tags or []
            )
            return FeedbackType.REJECT

        # Get feedback from channel
        channel_name = channel or self.default_channel
        feedback_channel = self._channels.get(channel_name, self._channels['cli'])

        failure_info = {
            'type': failure_type,
            'message': error_message
        }

        feedback = feedback_channel.request_feedback(
            fix_id=fix_id,
            fix_type=fix_type,
            target_file=target_file,
            diff_content=diff_content,
            confidence=confidence,
            failure_info=failure_info
        )

        if feedback and feedback != FeedbackType.DEFER:
            self._record_feedback(
                fix_id=fix_id,
                fix_type=fix_type,
                failure_type=failure_type,
                confidence=confidence,
                feedback_type=feedback,
                reviewer_type=ReviewerType.HUMAN,
                target_file=target_file,
                tags=tags or []
            )

        return feedback or FeedbackType.DEFER

    def receive_async_feedback(
        self,
        fix_id: str,
        feedback_type: Union[str, FeedbackType],
        reviewer_id: Optional[str] = None,
        comments: str = "",
        modifications: Optional[str] = None
    ) -> bool:
        """
        Process async feedback (e.g., from webhook callback).

        Args:
            fix_id: Fix identifier
            feedback_type: Type of feedback
            reviewer_id: ID of the reviewer
            comments: Review comments
            modifications: Modified fix content

        Returns:
            True if feedback was processed
        """
        if fix_id not in self._pending_requests:
            logger.warning(f"No pending request for fix {fix_id}")
            return False

        request = self._pending_requests.pop(fix_id)

        if isinstance(feedback_type, str):
            feedback_type = FeedbackType(feedback_type)

        self._record_feedback(
            fix_id=fix_id,
            fix_type=request.get('fix_type', 'unknown'),
            failure_type=request.get('failure_type', 'unknown'),
            confidence=request.get('confidence', 0.5),
            feedback_type=feedback_type,
            reviewer_type=ReviewerType.HUMAN,
            reviewer_id=reviewer_id,
            target_file=request.get('target_file', ''),
            comments=comments,
            modifications=modifications,
            tags=request.get('tags', [])
        )

        return True

    def _record_feedback(
        self,
        fix_id: str,
        fix_type: str,
        failure_type: str,
        confidence: float,
        feedback_type: FeedbackType,
        reviewer_type: ReviewerType,
        target_file: str,
        reviewer_id: Optional[str] = None,
        comments: str = "",
        modifications: Optional[str] = None,
        tags: Optional[List[str]] = None
    ):
        """Record feedback to store."""
        record = FeedbackRecord(
            feedback_id=f"fb_{hashlib.md5(f'{fix_id}_{datetime.now().isoformat()}'.encode()).hexdigest()[:8]}",
            fix_id=fix_id,
            failure_type=failure_type,
            fix_type=fix_type,
            original_confidence=confidence,
            feedback_type=feedback_type,
            reviewer_type=reviewer_type,
            reviewer_id=reviewer_id,
            comments=comments,
            modifications=modifications,
            target_file=target_file,
            tags=tags or []
        )

        self.store.add(record)
        logger.info(f"Recorded feedback: {record.feedback_type.value} for {fix_id}")

    def get_confidence_adjustment(self, fix_type: str) -> float:
        """
        Calculate confidence adjustment based on historical feedback.

        Args:
            fix_type: Type of fix

        Returns:
            Adjustment factor (-0.2 to +0.2)
        """
        records = self.store.get_by_fix_type(fix_type)
        if len(records) < 5:
            return 0.0  # Not enough data

        approved = sum(
            1 for r in records
            if r.feedback_type in (FeedbackType.APPROVE, FeedbackType.APPROVE_WITH_MODIFICATION)
        )
        rejected = sum(
            1 for r in records
            if r.feedback_type.value.startswith('REJECT')
        )

        if approved + rejected == 0:
            return 0.0

        approval_rate = approved / (approved + rejected)

        # Map approval rate to adjustment
        # 0% -> -0.2, 50% -> 0, 100% -> +0.2
        return (approval_rate - 0.5) * 0.4

    def get_stats(self) -> FeedbackStats:
        """Get feedback statistics."""
        return self.store.calculate_stats()

    def generate_report(self) -> str:
        """Generate a feedback report."""
        stats = self.get_stats()

        lines = [
            "# Feedback Report",
            "",
            f"Total Feedback: {stats.total_feedback}",
            f"Approval Rate: {stats.approval_rate:.1%}",
            "",
            "## By Decision",
            f"- Approved: {stats.approvals}",
            f"- Rejected: {stats.rejections}",
            f"- Modifications: {stats.modifications}",
            f"- Escalations: {stats.escalations}",
            "",
            "## Confidence Analysis",
            f"- Avg Confidence (Approved): {stats.avg_confidence_approved:.1%}",
            f"- Avg Confidence (Rejected): {stats.avg_confidence_rejected:.1%}",
            ""
        ]

        if stats.by_fix_type:
            lines.append("## By Fix Type")
            for fix_type, counts in stats.by_fix_type.items():
                total = counts['approved'] + counts['rejected']
                rate = counts['approved'] / total if total > 0 else 0
                lines.append(f"- {fix_type}: {rate:.1%} approval ({total} total)")

        return "\n".join(lines)


if __name__ == "__main__":
    # Demo usage
    collector = FeedbackCollector(
        storage_path="/tmp/feedback_store.json",
        auto_approve_threshold=0.95
    )

    # Simulate feedback request
    result = collector.request_feedback(
        fix_id="test_fix_001",
        fix_type="import",
        target_file="test_module.py",
        diff_content="--- a/test_module.py\n+++ b/test_module.py\n@@ -1,2 +1,3 @@\n+import os\n import sys",
        confidence=0.75,
        failure_type="IMPORT_ERROR",
        error_message="No module named 'os'"
    )

    print(f"Feedback result: {result.value}")
    print("\n" + collector.generate_report())
