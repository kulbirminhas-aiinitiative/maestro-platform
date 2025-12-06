"""
User Feedback Integrator for Self-Healing Mechanism.

Collects and processes user feedback to improve healing accuracy.

Implements AC-4: User feedback integration
"""

import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import uuid
import json

from .models import UserFeedback, HealingAction

logger = logging.getLogger(__name__)


@dataclass
class FeedbackStats:
    """Statistics for a healing action's feedback."""
    action_id: str
    total_feedback: int = 0
    helpful_count: int = 0
    not_helpful_count: int = 0
    average_rating: float = 0.0
    comments: List[str] = field(default_factory=list)
    suggested_fixes: List[str] = field(default_factory=list)

    @property
    def helpfulness_ratio(self) -> float:
        """Calculate the ratio of helpful feedback."""
        if self.total_feedback == 0:
            return 0.0
        return self.helpful_count / self.total_feedback


@dataclass
class LearningUpdate:
    """Represents an update to the healing model based on feedback."""
    pattern_id: str
    confidence_delta: float
    source: str  # "user_feedback", "automatic"
    reason: str
    timestamp: datetime = field(default_factory=datetime.utcnow)


class UserFeedbackIntegrator:
    """
    Integrates user feedback into the self-healing mechanism.

    This component:
    1. Collects feedback on healing actions
    2. Aggregates and analyzes feedback
    3. Updates pattern confidence scores
    4. Provides insights for model improvement
    """

    def __init__(
        self,
        min_feedback_for_update: int = 3,
        confidence_adjustment: float = 0.05,
        feedback_ttl_days: int = 90,
    ):
        """
        Initialize the feedback integrator.

        Args:
            min_feedback_for_update: Minimum feedback count before updating confidence
            confidence_adjustment: Base adjustment for confidence updates
            feedback_ttl_days: Days to retain feedback data
        """
        self.min_feedback_for_update = min_feedback_for_update
        self.confidence_adjustment = confidence_adjustment
        self.feedback_ttl_days = feedback_ttl_days

        # Feedback storage
        self._feedback: Dict[str, List[UserFeedback]] = defaultdict(list)
        self._action_stats: Dict[str, FeedbackStats] = {}
        self._learning_updates: List[LearningUpdate] = []

        # Pattern to action mapping
        self._pattern_actions: Dict[str, List[str]] = defaultdict(list)

    def submit_feedback(
        self,
        action_id: str,
        helpful: bool,
        comment: Optional[str] = None,
        suggested_fix: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> UserFeedback:
        """
        Submit user feedback for a healing action.

        Args:
            action_id: The action being rated
            helpful: Whether the action was helpful
            comment: Optional user comment
            suggested_fix: Optional suggested improvement
            user_id: Optional user identifier

        Returns:
            The created UserFeedback object
        """
        feedback = UserFeedback(
            feedback_id=f"fb-{uuid.uuid4().hex[:8]}",
            action_id=action_id,
            helpful=helpful,
            comment=comment,
            suggested_fix=suggested_fix,
            user_id=user_id,
        )

        self._feedback[action_id].append(feedback)
        self._update_stats(action_id, feedback)

        logger.info(
            f"Received feedback for action {action_id}: "
            f"helpful={helpful}, has_comment={bool(comment)}"
        )

        # Check if we should trigger a learning update
        self._check_learning_trigger(action_id)

        return feedback

    def _update_stats(self, action_id: str, feedback: UserFeedback) -> None:
        """Update statistics for an action based on new feedback."""
        if action_id not in self._action_stats:
            self._action_stats[action_id] = FeedbackStats(action_id=action_id)

        stats = self._action_stats[action_id]
        stats.total_feedback += 1

        if feedback.helpful:
            stats.helpful_count += 1
        else:
            stats.not_helpful_count += 1

        if feedback.comment:
            stats.comments.append(feedback.comment)

        if feedback.suggested_fix:
            stats.suggested_fixes.append(feedback.suggested_fix)

        # Recalculate average rating (treating helpful as 1.0, not helpful as 0.0)
        stats.average_rating = stats.helpfulness_ratio

    def _check_learning_trigger(self, action_id: str) -> None:
        """Check if feedback triggers a learning update."""
        if action_id not in self._action_stats:
            return

        stats = self._action_stats[action_id]

        if stats.total_feedback < self.min_feedback_for_update:
            return

        # Calculate confidence adjustment based on feedback
        if stats.helpfulness_ratio >= 0.8:
            delta = self.confidence_adjustment
            reason = "High user satisfaction"
        elif stats.helpfulness_ratio <= 0.3:
            delta = -self.confidence_adjustment * 2  # Larger penalty for bad fixes
            reason = "Low user satisfaction"
        else:
            return  # Neutral feedback, no update

        # Create learning update
        update = LearningUpdate(
            pattern_id=action_id,  # We'll need to map this to pattern
            confidence_delta=delta,
            source="user_feedback",
            reason=f"{reason} (ratio: {stats.helpfulness_ratio:.2f})",
        )

        self._learning_updates.append(update)
        logger.info(f"Learning update triggered: {update.reason}")

    def register_action(
        self,
        action: HealingAction,
    ) -> None:
        """
        Register a healing action for feedback tracking.

        Args:
            action: The healing action to track
        """
        self._pattern_actions[action.pattern_id].append(action.action_id)

        if action.action_id not in self._action_stats:
            self._action_stats[action.action_id] = FeedbackStats(
                action_id=action.action_id
            )

    def get_feedback_for_action(
        self,
        action_id: str,
    ) -> List[UserFeedback]:
        """Get all feedback for a specific action."""
        return self._feedback.get(action_id, [])

    def get_stats_for_action(
        self,
        action_id: str,
    ) -> Optional[FeedbackStats]:
        """Get statistics for a specific action."""
        return self._action_stats.get(action_id)

    def get_pattern_feedback(
        self,
        pattern_id: str,
    ) -> Dict[str, Any]:
        """
        Get aggregated feedback for all actions of a pattern.

        Returns:
            Aggregated feedback statistics for the pattern
        """
        action_ids = self._pattern_actions.get(pattern_id, [])

        if not action_ids:
            return {
                "pattern_id": pattern_id,
                "total_actions": 0,
                "total_feedback": 0,
                "overall_helpfulness": 0.0,
            }

        total_feedback = 0
        total_helpful = 0

        for action_id in action_ids:
            stats = self._action_stats.get(action_id)
            if stats:
                total_feedback += stats.total_feedback
                total_helpful += stats.helpful_count

        return {
            "pattern_id": pattern_id,
            "total_actions": len(action_ids),
            "total_feedback": total_feedback,
            "overall_helpfulness": (
                total_helpful / total_feedback if total_feedback > 0 else 0.0
            ),
        }

    def get_pending_updates(self) -> List[LearningUpdate]:
        """Get pending learning updates."""
        return self._learning_updates.copy()

    def apply_update(
        self,
        update: LearningUpdate,
    ) -> None:
        """
        Mark a learning update as applied.

        Args:
            update: The update that was applied
        """
        if update in self._learning_updates:
            self._learning_updates.remove(update)
            logger.debug(f"Applied learning update for pattern {update.pattern_id}")

    def get_improvement_suggestions(
        self,
        pattern_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get improvement suggestions based on user feedback.

        Args:
            pattern_id: Optional filter by pattern

        Returns:
            List of improvement suggestions
        """
        suggestions = []

        action_ids = (
            self._pattern_actions.get(pattern_id, [])
            if pattern_id
            else list(self._action_stats.keys())
        )

        for action_id in action_ids:
            stats = self._action_stats.get(action_id)
            if not stats:
                continue

            # Low helpfulness with suggested fixes
            if stats.helpfulness_ratio < 0.5 and stats.suggested_fixes:
                suggestions.append({
                    "action_id": action_id,
                    "type": "user_suggested_fix",
                    "priority": "high" if stats.total_feedback >= 5 else "medium",
                    "suggestions": stats.suggested_fixes,
                    "feedback_count": stats.total_feedback,
                    "helpfulness": stats.helpfulness_ratio,
                })

            # High feedback with mixed ratings
            if stats.total_feedback >= 10 and 0.4 <= stats.helpfulness_ratio <= 0.6:
                suggestions.append({
                    "action_id": action_id,
                    "type": "needs_investigation",
                    "priority": "medium",
                    "reason": "Mixed user feedback",
                    "comments": stats.comments[:5],  # Latest 5 comments
                    "helpfulness": stats.helpfulness_ratio,
                })

        return sorted(suggestions, key=lambda x: x.get("priority", "low") == "high", reverse=True)

    def cleanup_old_feedback(self) -> int:
        """
        Remove feedback older than TTL.

        Returns:
            Number of feedback entries removed
        """
        cutoff = datetime.utcnow() - timedelta(days=self.feedback_ttl_days)
        removed = 0

        for action_id in list(self._feedback.keys()):
            original_count = len(self._feedback[action_id])
            self._feedback[action_id] = [
                fb for fb in self._feedback[action_id]
                if fb.submitted_at > cutoff
            ]
            removed += original_count - len(self._feedback[action_id])

            # Clean up empty entries
            if not self._feedback[action_id]:
                del self._feedback[action_id]

        if removed > 0:
            logger.info(f"Cleaned up {removed} old feedback entries")

        return removed

    def get_statistics(self) -> Dict[str, Any]:
        """Get overall feedback statistics."""
        total_feedback = sum(len(fb) for fb in self._feedback.values())
        total_helpful = sum(
            stats.helpful_count
            for stats in self._action_stats.values()
        )

        return {
            "total_feedback": total_feedback,
            "total_helpful": total_helpful,
            "overall_helpfulness": (
                total_helpful / total_feedback if total_feedback > 0 else 0.0
            ),
            "actions_tracked": len(self._action_stats),
            "patterns_tracked": len(self._pattern_actions),
            "pending_updates": len(self._learning_updates),
        }

    def export_feedback(self) -> Dict[str, Any]:
        """Export all feedback data for persistence."""
        return {
            "feedback": {
                action_id: [fb.to_dict() for fb in feedbacks]
                for action_id, feedbacks in self._feedback.items()
            },
            "stats": {
                action_id: {
                    "action_id": stats.action_id,
                    "total_feedback": stats.total_feedback,
                    "helpful_count": stats.helpful_count,
                    "not_helpful_count": stats.not_helpful_count,
                    "comments": stats.comments,
                    "suggested_fixes": stats.suggested_fixes,
                }
                for action_id, stats in self._action_stats.items()
            },
            "pattern_actions": dict(self._pattern_actions),
        }

    def import_feedback(self, data: Dict[str, Any]) -> int:
        """
        Import feedback data from persistence.

        Returns:
            Number of feedback entries imported
        """
        count = 0

        # Import raw feedback
        for action_id, feedbacks in data.get("feedback", {}).items():
            for fb_data in feedbacks:
                fb = UserFeedback(
                    feedback_id=fb_data["feedback_id"],
                    action_id=fb_data["action_id"],
                    helpful=fb_data["helpful"],
                    comment=fb_data.get("comment"),
                    suggested_fix=fb_data.get("suggested_fix"),
                    submitted_at=datetime.fromisoformat(fb_data["submitted_at"]),
                    user_id=fb_data.get("user_id"),
                )
                self._feedback[action_id].append(fb)
                count += 1

        # Import stats
        for action_id, stats_data in data.get("stats", {}).items():
            self._action_stats[action_id] = FeedbackStats(
                action_id=stats_data["action_id"],
                total_feedback=stats_data["total_feedback"],
                helpful_count=stats_data["helpful_count"],
                not_helpful_count=stats_data["not_helpful_count"],
                comments=stats_data.get("comments", []),
                suggested_fixes=stats_data.get("suggested_fixes", []),
            )

        # Import pattern-action mapping
        for pattern_id, actions in data.get("pattern_actions", {}).items():
            self._pattern_actions[pattern_id].extend(actions)

        return count
