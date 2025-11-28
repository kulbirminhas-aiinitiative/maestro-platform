#!/usr/bin/env python3
"""
Quality Fabric - Notification Service
Sends notifications about repair events
"""

import logging
from typing import Dict, List, Any
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class NotificationChannel(str, Enum):
    """Notification channels"""
    LOG = "log"
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    CONSOLE = "console"


@dataclass
class Notification:
    """Notification message"""
    title: str
    message: str
    severity: str
    details: Dict[str, Any]


class NotificationService:
    """Send notifications about repairs"""

    def __init__(self, channels: List[NotificationChannel] = None):
        self.channels = channels or [NotificationChannel.LOG]

    async def notify_repair_success(self, repair_result: Dict[str, Any]):
        """Notify about successful repair"""
        notification = Notification(
            title="✓ Auto-Repair Successful",
            message=f"Fixed {repair_result['error_event']['error_type']} in {repair_result['error_event']['file_path']}",
            severity="info",
            details=repair_result
        )
        await self._send_notification(notification)

    async def notify_repair_failure(self, repair_result: Dict[str, Any]):
        """Notify about failed repair"""
        notification = Notification(
            title="✗ Auto-Repair Failed",
            message=f"Failed to fix {repair_result['error_event']['error_type']} in {repair_result['error_event']['file_path']}",
            severity="warning",
            details=repair_result
        )
        await self._send_notification(notification)

    async def notify_error_detected(self, error: Dict[str, Any]):
        """Notify about detected error"""
        notification = Notification(
            title="🔍 Error Detected",
            message=f"{error['error_type']} in {error['file_path']}",
            severity="info",
            details=error
        )
        await self._send_notification(notification)

    async def _send_notification(self, notification: Notification):
        """Send notification to configured channels"""
        for channel in self.channels:
            if channel == NotificationChannel.LOG:
                await self._send_to_log(notification)
            elif channel == NotificationChannel.CONSOLE:
                await self._send_to_console(notification)
            # TODO: Implement email, slack, webhook

    async def _send_to_log(self, notification: Notification):
        """Send to log"""
        logger.info(f"{notification.title}: {notification.message}")

    async def _send_to_console(self, notification: Notification):
        """Send to console"""
        print(f"\n{notification.title}")
        print(f"{notification.message}")
        print(f"Severity: {notification.severity}\n")