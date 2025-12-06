"""
Recovery Notification Service - Alerts for rollback events

EPIC: MD-2527 - AC-4: Recovery notification system

Sends notifications when rollback events occur via multiple channels:
- Webhooks (Slack, Teams, custom)
- Logging
- Event system
"""

import json
import logging
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class NotificationLevel(Enum):
    """Notification severity level."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Notification:
    """Notification message."""
    level: NotificationLevel
    title: str
    message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    details: Optional[Dict[str, Any]] = None
    source: str = "RollbackManager"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "level": self.level.value,
            "title": self.title,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
            "source": self.source,
        }

    def to_slack_payload(self) -> Dict[str, Any]:
        """Convert to Slack webhook payload."""
        color_map = {
            NotificationLevel.INFO: "#36a64f",
            NotificationLevel.WARNING: "#ffcc00",
            NotificationLevel.ERROR: "#ff6600",
            NotificationLevel.CRITICAL: "#ff0000",
        }

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🔄 {self.title}",
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": self.message,
                }
            },
        ]

        if self.details:
            detail_text = "\n".join(
                f"• *{k}*: {v}" for k, v in self.details.items()
                if not isinstance(v, (list, dict))
            )
            if detail_text:
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": detail_text,
                    }
                })

        return {
            "attachments": [{
                "color": color_map.get(self.level, "#808080"),
                "blocks": blocks,
            }]
        }

    def to_teams_payload(self) -> Dict[str, Any]:
        """Convert to Microsoft Teams webhook payload."""
        color_map = {
            NotificationLevel.INFO: "00FF00",
            NotificationLevel.WARNING: "FFCC00",
            NotificationLevel.ERROR: "FF6600",
            NotificationLevel.CRITICAL: "FF0000",
        }

        facts = []
        if self.details:
            for k, v in self.details.items():
                if not isinstance(v, (list, dict)):
                    facts.append({"name": k, "value": str(v)})

        return {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": color_map.get(self.level, "808080"),
            "summary": self.title,
            "sections": [{
                "activityTitle": f"🔄 {self.title}",
                "facts": facts,
                "text": self.message,
            }]
        }


class RecoveryNotificationService:
    """
    Service for sending recovery/rollback notifications.

    Supports multiple notification channels and custom handlers.
    """

    def __init__(
        self,
        webhook_url: Optional[str] = None,
        webhook_type: str = "slack",
        enabled: bool = True,
        min_level: NotificationLevel = NotificationLevel.WARNING,
    ):
        """
        Initialize notification service.

        Args:
            webhook_url: URL for webhook notifications
            webhook_type: Type of webhook (slack, teams, custom)
            enabled: Whether notifications are enabled
            min_level: Minimum level to send notifications
        """
        self.webhook_url = webhook_url
        self.webhook_type = webhook_type
        self.enabled = enabled
        self.min_level = min_level
        self._handlers: List[Callable[[Notification], None]] = []
        self._notification_history: List[Notification] = []
        self._max_history = 100

        logger.info(
            f"RecoveryNotificationService initialized "
            f"(enabled={enabled}, webhook_type={webhook_type})"
        )

    def add_handler(self, handler: Callable[[Notification], None]) -> None:
        """
        Add custom notification handler.

        Args:
            handler: Function that receives Notification objects
        """
        self._handlers.append(handler)
        logger.debug(f"Added notification handler: {handler.__name__}")

    def notify(
        self,
        level: NotificationLevel,
        title: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Send a notification.

        Args:
            level: Notification severity level
            title: Notification title
            message: Notification message
            details: Additional details

        Returns:
            True if notification was sent successfully
        """
        notification = Notification(
            level=level,
            title=title,
            message=message,
            details=details,
        )

        # Add to history
        self._notification_history.append(notification)
        if len(self._notification_history) > self._max_history:
            self._notification_history = self._notification_history[-self._max_history:]

        # Log the notification
        log_method = getattr(logger, level.value, logger.info)
        log_method(f"[{title}] {message}")

        if not self.enabled:
            return True

        # Check minimum level
        level_order = [
            NotificationLevel.INFO,
            NotificationLevel.WARNING,
            NotificationLevel.ERROR,
            NotificationLevel.CRITICAL,
        ]
        if level_order.index(level) < level_order.index(self.min_level):
            return True

        success = True

        # Send to webhook
        if self.webhook_url:
            webhook_success = self._send_webhook(notification)
            success = success and webhook_success

        # Call custom handlers
        for handler in self._handlers:
            try:
                handler(notification)
            except Exception as e:
                logger.error(f"Notification handler failed: {e}")
                success = False

        return success

    def notify_rollback_started(
        self,
        execution_id: str,
        phase_name: str,
        reason: Optional[str] = None,
    ) -> bool:
        """
        Send notification when rollback starts.

        Args:
            execution_id: Execution identifier
            phase_name: Phase where rollback started
            reason: Reason for rollback

        Returns:
            True if notification sent
        """
        details = {
            "execution_id": execution_id,
            "phase": phase_name,
        }
        if reason:
            details["reason"] = reason

        return self.notify(
            level=NotificationLevel.WARNING,
            title="Rollback Started",
            message=f"Rolling back execution {execution_id} from phase {phase_name}",
            details=details,
        )

    def notify_rollback_completed(
        self,
        execution_id: str,
        success: bool,
        artifacts_cleaned: int,
        artifacts_failed: int,
        duration_ms: float,
    ) -> bool:
        """
        Send notification when rollback completes.

        Args:
            execution_id: Execution identifier
            success: Whether rollback was successful
            artifacts_cleaned: Number of artifacts cleaned
            artifacts_failed: Number of artifacts that failed cleanup
            duration_ms: Duration of rollback in milliseconds

        Returns:
            True if notification sent
        """
        level = NotificationLevel.INFO if success else NotificationLevel.ERROR
        status = "completed successfully" if success else "completed with errors"

        return self.notify(
            level=level,
            title="Rollback Completed",
            message=f"Rollback {status} for execution {execution_id}",
            details={
                "execution_id": execution_id,
                "success": success,
                "artifacts_cleaned": artifacts_cleaned,
                "artifacts_failed": artifacts_failed,
                "duration_ms": f"{duration_ms:.2f}",
            },
        )

    def notify_recovery_available(
        self,
        execution_id: str,
        checkpoint_id: str,
        phase_name: str,
    ) -> bool:
        """
        Send notification that recovery is available.

        Args:
            execution_id: Execution identifier
            checkpoint_id: Available checkpoint ID
            phase_name: Phase at checkpoint

        Returns:
            True if notification sent
        """
        return self.notify(
            level=NotificationLevel.INFO,
            title="Recovery Available",
            message=f"Execution {execution_id} can be recovered from phase {phase_name}",
            details={
                "execution_id": execution_id,
                "checkpoint_id": checkpoint_id,
                "phase": phase_name,
            },
        )

    def get_notification_history(
        self,
        level: Optional[NotificationLevel] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Get notification history.

        Args:
            level: Filter by level
            limit: Maximum notifications to return

        Returns:
            List of notification dictionaries
        """
        notifications = self._notification_history

        if level:
            notifications = [n for n in notifications if n.level == level]

        notifications = notifications[-limit:]

        return [n.to_dict() for n in reversed(notifications)]

    def _send_webhook(self, notification: Notification) -> bool:
        """
        Send notification to webhook.

        Args:
            notification: Notification to send

        Returns:
            True if successful
        """
        if not self.webhook_url:
            return True

        try:
            if self.webhook_type == "slack":
                payload = notification.to_slack_payload()
            elif self.webhook_type == "teams":
                payload = notification.to_teams_payload()
            else:
                payload = notification.to_dict()

            data = json.dumps(payload).encode("utf-8")
            request = urllib.request.Request(
                self.webhook_url,
                data=data,
                headers={"Content-Type": "application/json"},
            )

            with urllib.request.urlopen(request, timeout=10) as response:
                if response.status < 300:
                    logger.debug(f"Webhook notification sent successfully")
                    return True
                else:
                    logger.warning(f"Webhook returned status {response.status}")
                    return False

        except urllib.error.URLError as e:
            logger.error(f"Failed to send webhook notification: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending webhook: {e}")
            return False

    def test_connection(self) -> bool:
        """
        Test webhook connection with a test notification.

        Returns:
            True if test successful
        """
        if not self.webhook_url:
            logger.info("No webhook URL configured")
            return True

        return self.notify(
            level=NotificationLevel.INFO,
            title="Connection Test",
            message="Recovery notification service connection test",
            details={"test": True},
        )
