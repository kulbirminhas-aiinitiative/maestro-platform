"""
Alerting System for Operations Monitoring - AC-4.

Manages alerting rules and notifications.
"""

import uuid
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

from .metrics import MetricsCollector, MetricQuery, MetricResult, Aggregation


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    """Alert status."""
    FIRING = "firing"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"
    SILENCED = "silenced"


class ComparisonOperator(str, Enum):
    """Comparison operators for alert rules."""
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN_OR_EQUAL = "gte"
    LESS_THAN_OR_EQUAL = "lte"


@dataclass
class AlertRule:
    """Rule for triggering alerts."""
    id: str
    name: str
    metric: str
    condition: ComparisonOperator
    threshold: float
    duration_seconds: int
    severity: AlertSeverity
    labels: dict[str, str] = field(default_factory=dict)
    annotations: dict[str, str] = field(default_factory=dict)
    notification_channels: list[str] = field(default_factory=list)
    enabled: bool = True

    def evaluate(self, value: float) -> bool:
        """Evaluate rule against value."""
        if self.condition == ComparisonOperator.GREATER_THAN:
            return value > self.threshold
        elif self.condition == ComparisonOperator.LESS_THAN:
            return value < self.threshold
        elif self.condition == ComparisonOperator.EQUALS:
            return value == self.threshold
        elif self.condition == ComparisonOperator.NOT_EQUALS:
            return value != self.threshold
        elif self.condition == ComparisonOperator.GREATER_THAN_OR_EQUAL:
            return value >= self.threshold
        elif self.condition == ComparisonOperator.LESS_THAN_OR_EQUAL:
            return value <= self.threshold
        return False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "metric": self.metric,
            "condition": self.condition.value,
            "threshold": self.threshold,
            "duration_seconds": self.duration_seconds,
            "severity": self.severity.value,
            "labels": self.labels,
            "notification_channels": self.notification_channels,
            "enabled": self.enabled
        }


@dataclass
class Alert:
    """Active alert instance."""
    id: str
    rule_id: str
    rule_name: str
    severity: AlertSeverity
    status: AlertStatus
    message: str
    metric_value: float
    threshold: float
    triggered_at: datetime
    resolved_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    labels: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "rule_id": self.rule_id,
            "rule": self.rule_name,
            "severity": self.severity.value,
            "status": self.status.value,
            "message": self.message,
            "metric_value": self.metric_value,
            "threshold": self.threshold,
            "triggered_at": self.triggered_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "acknowledged_by": self.acknowledged_by,
            "labels": self.labels
        }


@dataclass
class NotificationChannel:
    """Notification channel configuration."""
    id: str
    name: str
    channel_type: str  # slack, email, pagerduty, webhook
    config: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.channel_type,
            "enabled": self.enabled
        }


class AlertManager:
    """Manages alerting rules and notifications."""

    def __init__(self, metrics_collector: Optional[MetricsCollector] = None):
        self.metrics = metrics_collector or MetricsCollector()
        self._rules: dict[str, AlertRule] = {}
        self._alerts: dict[str, Alert] = {}
        self._channels: dict[str, NotificationChannel] = {}
        self._notifiers: dict[str, Callable] = {}
        self._firing_since: dict[str, datetime] = {}

    def add_rule(self, rule: AlertRule) -> None:
        """Add alerting rule."""
        self._rules[rule.id] = rule

    def remove_rule(self, rule_id: str) -> bool:
        """Remove alerting rule."""
        if rule_id in self._rules:
            del self._rules[rule_id]
            return True
        return False

    def add_channel(self, channel: NotificationChannel) -> None:
        """Add notification channel."""
        self._channels[channel.id] = channel

    def register_notifier(self, channel_type: str, notifier: Callable) -> None:
        """Register notifier function for channel type."""
        self._notifiers[channel_type] = notifier

    async def evaluate(self) -> list[Alert]:
        """Evaluate all rules against current metrics."""
        new_alerts = []

        for rule in self._rules.values():
            if not rule.enabled:
                continue

            value = await self.metrics.get_current(rule.metric, rule.labels)
            if value is None:
                continue

            firing = rule.evaluate(value)

            if firing:
                # Check duration
                if rule.id not in self._firing_since:
                    self._firing_since[rule.id] = datetime.utcnow()
                else:
                    duration = (datetime.utcnow() - self._firing_since[rule.id]).total_seconds()
                    if duration >= rule.duration_seconds:
                        # Check if alert already exists
                        existing = self._get_alert_for_rule(rule.id)
                        if not existing:
                            alert = await self._create_alert(rule, value)
                            new_alerts.append(alert)
            else:
                # Clear firing state
                self._firing_since.pop(rule.id, None)

                # Resolve existing alert
                existing = self._get_alert_for_rule(rule.id)
                if existing and existing.status == AlertStatus.FIRING:
                    existing.status = AlertStatus.RESOLVED
                    existing.resolved_at = datetime.utcnow()

        return new_alerts

    async def _create_alert(self, rule: AlertRule, value: float) -> Alert:
        """Create new alert from rule."""
        alert = Alert(
            id=str(uuid.uuid4()),
            rule_id=rule.id,
            rule_name=rule.name,
            severity=rule.severity,
            status=AlertStatus.FIRING,
            message=rule.annotations.get(
                "message",
                f"{rule.metric} {rule.condition.value} {rule.threshold}"
            ),
            metric_value=value,
            threshold=rule.threshold,
            triggered_at=datetime.utcnow(),
            labels=rule.labels
        )

        self._alerts[alert.id] = alert

        # Send notifications
        await self._notify(alert, rule.notification_channels)

        return alert

    def _get_alert_for_rule(self, rule_id: str) -> Optional[Alert]:
        """Get active alert for rule."""
        for alert in self._alerts.values():
            if alert.rule_id == rule_id and alert.status == AlertStatus.FIRING:
                return alert
        return None

    async def _notify(self, alert: Alert, channel_ids: list[str]) -> None:
        """Send notifications for alert."""
        for channel_id in channel_ids:
            channel = self._channels.get(channel_id)
            if not channel or not channel.enabled:
                continue

            notifier = self._notifiers.get(channel.channel_type)
            if notifier:
                try:
                    await notifier(alert, channel)
                except Exception:
                    pass  # Log error in production

    async def acknowledge(
        self,
        alert_id: str,
        acknowledged_by: str,
        comment: str = ""
    ) -> Optional[Alert]:
        """Acknowledge alert."""
        alert = self._alerts.get(alert_id)
        if alert:
            alert.status = AlertStatus.ACKNOWLEDGED
            alert.acknowledged_by = acknowledged_by
            alert.acknowledged_at = datetime.utcnow()
            return alert
        return None

    async def silence(self, alert_id: str) -> Optional[Alert]:
        """Silence alert."""
        alert = self._alerts.get(alert_id)
        if alert:
            alert.status = AlertStatus.SILENCED
            return alert
        return None

    def get_alerts(
        self,
        status: Optional[AlertStatus] = None,
        severity: Optional[AlertSeverity] = None
    ) -> list[Alert]:
        """Get alerts with optional filtering."""
        alerts = list(self._alerts.values())

        if status:
            alerts = [a for a in alerts if a.status == status]

        if severity:
            alerts = [a for a in alerts if a.severity == severity]

        return sorted(alerts, key=lambda a: a.triggered_at, reverse=True)

    def get_alert(self, alert_id: str) -> Optional[Alert]:
        """Get alert by ID."""
        return self._alerts.get(alert_id)

    def get_rules(self) -> list[AlertRule]:
        """Get all alerting rules."""
        return list(self._rules.values())
