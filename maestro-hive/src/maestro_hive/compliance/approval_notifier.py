#!/usr/bin/env python3
"""
Approval Notifier: Notification system for approval workflows.

Sends notifications via multiple channels (email, slack, webhook).
"""

import json
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable
from enum import Enum
from .approval_engine import ApprovalRequest, ApprovalEngine

logger = logging.getLogger(__name__)


class NotificationChannel(Enum):
    """Notification channels."""
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    IN_APP = "in_app"


@dataclass
class Notification:
    """A notification to be sent."""
    id: str
    channel: NotificationChannel
    recipient: str
    subject: str
    body: str
    request_id: str
    sent: bool = False
    sent_at: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['channel'] = self.channel.value
        return data


class ApprovalNotifier:
    """Sends notifications for approval workflows."""

    def __init__(
        self,
        email_sender: Optional[Callable[[str, str, str], bool]] = None,
        slack_sender: Optional[Callable[[str, str], bool]] = None,
        webhook_sender: Optional[Callable[[str, Dict], bool]] = None
    ):
        self.email_sender = email_sender
        self.slack_sender = slack_sender
        self.webhook_sender = webhook_sender
        self._notifications: List[Notification] = []
        self._notification_counter = 0

    def notify_approval_request(
        self,
        request: ApprovalRequest,
        approver_id: str,
        channels: Optional[List[NotificationChannel]] = None
    ) -> List[Notification]:
        """Send notifications for a new approval request."""
        channels = channels or [NotificationChannel.EMAIL]
        notifications = []

        subject = f"Approval Required: {request.resource}/{request.action}"
        body = self._format_request_body(request)

        for channel in channels:
            notification = self._create_notification(
                channel=channel,
                recipient=approver_id,
                subject=subject,
                body=body,
                request_id=request.id
            )
            self._send_notification(notification)
            notifications.append(notification)

        return notifications

    def notify_decision(
        self,
        request: ApprovalRequest,
        decision: str,
        decider: str
    ) -> List[Notification]:
        """Notify requester of decision."""
        subject = f"Approval {decision.title()}: {request.resource}/{request.action}"
        body = f"Your request {request.id} has been {decision} by {decider}."

        notification = self._create_notification(
            channel=NotificationChannel.EMAIL,
            recipient=request.requester_id,
            subject=subject,
            body=body,
            request_id=request.id
        )
        self._send_notification(notification)

        return [notification]

    def notify_expiring(
        self,
        request: ApprovalRequest,
        hours_remaining: int
    ) -> List[Notification]:
        """Notify about expiring request."""
        subject = f"Approval Expiring: {request.resource}/{request.action}"
        body = f"Request {request.id} will expire in {hours_remaining} hours."

        notifications = []
        for approver_id in request.required_approvers:
            notification = self._create_notification(
                channel=NotificationChannel.EMAIL,
                recipient=approver_id,
                subject=subject,
                body=body,
                request_id=request.id
            )
            self._send_notification(notification)
            notifications.append(notification)

        return notifications

    def _create_notification(
        self,
        channel: NotificationChannel,
        recipient: str,
        subject: str,
        body: str,
        request_id: str
    ) -> Notification:
        """Create a notification."""
        self._notification_counter += 1
        notification_id = f"NOT-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{self._notification_counter:04d}"

        notification = Notification(
            id=notification_id,
            channel=channel,
            recipient=recipient,
            subject=subject,
            body=body,
            request_id=request_id
        )

        self._notifications.append(notification)
        return notification

    def _send_notification(self, notification: Notification) -> bool:
        """Send a notification via appropriate channel."""
        try:
            if notification.channel == NotificationChannel.EMAIL and self.email_sender:
                success = self.email_sender(
                    notification.recipient,
                    notification.subject,
                    notification.body
                )
            elif notification.channel == NotificationChannel.SLACK and self.slack_sender:
                success = self.slack_sender(notification.recipient, notification.body)
            elif notification.channel == NotificationChannel.WEBHOOK and self.webhook_sender:
                success = self.webhook_sender(
                    notification.recipient,
                    notification.to_dict()
                )
            else:
                # Default: log only
                logger.info(f"Notification: {notification.subject} -> {notification.recipient}")
                success = True

            notification.sent = success
            if success:
                notification.sent_at = datetime.utcnow().isoformat()

            return success

        except Exception as e:
            notification.error = str(e)
            logger.error(f"Failed to send notification: {e}")
            return False

    def _format_request_body(self, request: ApprovalRequest) -> str:
        """Format request for notification body."""
        return f"""
Approval Request: {request.id}

Resource: {request.resource}
Action: {request.action}
Requester: {request.requester_id}
Created: {request.created_at}
Expires: {request.expires_at}

Please review and approve/reject this request.
"""


def get_approval_notifier(**kwargs) -> ApprovalNotifier:
    """Get approval notifier instance."""
    return ApprovalNotifier(**kwargs)
