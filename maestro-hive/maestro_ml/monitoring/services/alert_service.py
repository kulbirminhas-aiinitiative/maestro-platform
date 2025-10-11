"""
Alert Management Service

Manages alert rules, triggers alerts, and handles notifications.
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import uuid

from ..models.alert_models import (
    AlertRule,
    Alert,
    AlertConfig,
    AlertSeverity,
    AlertStatus,
    AlertSummary,
    AlertNotification
)
from ..models.metrics_models import MetricType, MetricComparisonResult
from .degradation_detector import DegradationDetector


class AlertService:
    """
    Alert management and notification service

    Example:
        >>> service = AlertService(degradation_detector)

        >>> # Create alert rule
        >>> rule = service.create_rule(
        >>>     model_name="my_model",
        >>>     metric_type=MetricType.ACCURACY,
        >>>     threshold_value=0.90,
        >>>     comparison_operator="lt",
        >>>     severity=AlertSeverity.HIGH
        >>> )

        >>> # Check and trigger alerts
        >>> alerts = service.evaluate_model("my_model", "v1.0")
    """

    def __init__(
        self,
        degradation_detector: DegradationDetector,
        config: Optional[AlertConfig] = None
    ):
        """
        Initialize alert service

        Args:
            degradation_detector: DegradationDetector instance
            config: AlertConfig for global settings
        """
        self.detector = degradation_detector
        self.config = config or AlertConfig()

        # Storage
        self.rules: Dict[str, AlertRule] = {}
        self.alerts: Dict[str, Alert] = {}

        # Cooldown tracking: {rule_id: last_trigger_time}
        self.last_triggered: Dict[str, datetime] = {}

        # Rate limiting: {model_name: [trigger_times]}
        self.trigger_history: Dict[str, List[datetime]] = defaultdict(list)

    def create_rule(
        self,
        rule_name: str,
        model_name: str,
        metric_type: MetricType,
        threshold_value: float,
        comparison_operator: str,
        severity: AlertSeverity,
        model_version: Optional[str] = None,
        cooldown_minutes: int = 60,
        notify_channels: Optional[List[str]] = None,
        description: Optional[str] = None,
        created_by: str = "system"
    ) -> AlertRule:
        """
        Create a new alert rule

        Args:
            rule_name: Unique name for the rule
            model_name: Model to monitor
            metric_type: Metric to monitor
            threshold_value: Threshold for triggering
            comparison_operator: gt, lt, gte, lte, eq
            severity: Alert severity level
            model_version: Specific version (None = all versions)
            cooldown_minutes: Min time between alerts
            notify_channels: Notification channels
            description: Rule description
            created_by: Who created the rule

        Returns:
            AlertRule instance
        """
        rule_id = f"rule_{uuid.uuid4().hex[:12]}"

        rule = AlertRule(
            rule_id=rule_id,
            rule_name=rule_name,
            model_name=model_name,
            model_version=model_version,
            metric_type=metric_type,
            threshold_value=threshold_value,
            comparison_operator=comparison_operator,
            severity=severity,
            cooldown_minutes=cooldown_minutes,
            notify_channels=notify_channels or [],
            description=description,
            created_by=created_by
        )

        self.rules[rule_id] = rule
        return rule

    def create_degradation_rule(
        self,
        rule_name: str,
        model_name: str,
        metric_type: MetricType,
        max_degradation_percentage: float,
        severity: AlertSeverity,
        model_version: Optional[str] = None,
        baseline_window_hours: int = 24,
        cooldown_minutes: int = 60,
        notify_channels: Optional[List[str]] = None,
        created_by: str = "system"
    ) -> AlertRule:
        """
        Create degradation-based alert rule

        Args:
            rule_name: Unique name for the rule
            model_name: Model to monitor
            metric_type: Metric to monitor
            max_degradation_percentage: Max % degradation allowed
            severity: Alert severity
            model_version: Specific version (None = all)
            baseline_window_hours: Hours for baseline calculation
            cooldown_minutes: Min time between alerts
            notify_channels: Notification channels
            created_by: Who created the rule

        Returns:
            AlertRule instance
        """
        rule_id = f"rule_{uuid.uuid4().hex[:12]}"

        rule = AlertRule(
            rule_id=rule_id,
            rule_name=rule_name,
            model_name=model_name,
            model_version=model_version,
            metric_type=metric_type,
            threshold_value=0.0,  # Not used for degradation rules
            comparison_operator="degradation",
            use_degradation=True,
            max_degradation_percentage=max_degradation_percentage,
            baseline_window_hours=baseline_window_hours,
            severity=severity,
            cooldown_minutes=cooldown_minutes,
            notify_channels=notify_channels or [],
            created_by=created_by
        )

        self.rules[rule_id] = rule
        return rule

    def get_rule(self, rule_id: str) -> Optional[AlertRule]:
        """Get rule by ID"""
        return self.rules.get(rule_id)

    def list_rules(
        self,
        model_name: Optional[str] = None,
        enabled_only: bool = True
    ) -> List[AlertRule]:
        """
        List alert rules

        Args:
            model_name: Filter by model name
            enabled_only: Only return enabled rules

        Returns:
            List of AlertRule instances
        """
        rules = list(self.rules.values())

        if model_name:
            rules = [r for r in rules if r.model_name == model_name]

        if enabled_only:
            rules = [r for r in rules if r.enabled]

        return rules

    def update_rule(self, rule_id: str, **updates) -> Optional[AlertRule]:
        """Update an existing rule"""
        rule = self.rules.get(rule_id)
        if not rule:
            return None

        for key, value in updates.items():
            if hasattr(rule, key):
                setattr(rule, key, value)

        return rule

    def delete_rule(self, rule_id: str) -> bool:
        """Delete a rule"""
        if rule_id in self.rules:
            del self.rules[rule_id]
            return True
        return False

    def evaluate_model(
        self,
        model_name: str,
        model_version: str
    ) -> List[Alert]:
        """
        Evaluate all rules for a model and trigger alerts if needed

        Args:
            model_name: Model identifier
            model_version: Model version

        Returns:
            List of triggered Alert instances
        """
        if not self.config.enable_alerts:
            return []

        # Get applicable rules
        applicable_rules = [
            r for r in self.rules.values()
            if r.enabled
            and r.model_name == model_name
            and (r.model_version is None or r.model_version == model_version)
        ]

        triggered_alerts = []

        for rule in applicable_rules:
            # Check cooldown
            if not self._check_cooldown(rule):
                continue

            # Evaluate rule
            alert = self._evaluate_rule(rule, model_name, model_version)

            if alert:
                # Check rate limits
                if self._check_rate_limits(model_name):
                    triggered_alerts.append(alert)
                    self._record_trigger(rule, model_name)

        return triggered_alerts

    def _evaluate_rule(
        self,
        rule: AlertRule,
        model_name: str,
        model_version: str
    ) -> Optional[Alert]:
        """Evaluate a single rule and create alert if triggered"""

        if rule.use_degradation:
            # Degradation-based rule
            comparison = self.detector.check_degradation(
                model_name=model_name,
                model_version=model_version,
                metric_type=rule.metric_type,
                baseline_window_hours=rule.baseline_window_hours
            )

            if comparison.is_degraded:
                return self._create_alert_from_degradation(rule, model_version, comparison)

        else:
            # Threshold-based rule
            latest_snapshot = self.detector.collector.get_latest_metrics(
                model_name=model_name,
                model_version=model_version
            )

            if not latest_snapshot:
                return None

            metric_value = latest_snapshot.metrics.get(rule.metric_type.value)
            if metric_value is None:
                return None

            # Check threshold
            triggered = self._check_threshold(
                metric_value,
                rule.threshold_value,
                rule.comparison_operator
            )

            if triggered:
                return self._create_alert_from_threshold(rule, model_version, metric_value)

        return None

    def _check_threshold(
        self,
        value: float,
        threshold: float,
        operator: str
    ) -> bool:
        """Check if value crosses threshold"""
        if operator == "gt":
            return value > threshold
        elif operator == "lt":
            return value < threshold
        elif operator == "gte":
            return value >= threshold
        elif operator == "lte":
            return value <= threshold
        elif operator == "eq":
            return value == threshold
        return False

    def _create_alert_from_threshold(
        self,
        rule: AlertRule,
        model_version: str,
        metric_value: float
    ) -> Alert:
        """Create alert from threshold violation"""
        alert_id = f"alert_{uuid.uuid4().hex[:12]}"

        message = (
            f"{rule.severity.value.upper()}: {rule.metric_type.value} "
            f"({metric_value:.4f}) {rule.comparison_operator} "
            f"threshold ({rule.threshold_value:.4f}) "
            f"for model {rule.model_name} v{model_version}"
        )

        alert = Alert(
            alert_id=alert_id,
            rule_id=rule.rule_id,
            rule_name=rule.rule_name,
            model_name=rule.model_name,
            model_version=model_version,
            metric_type=rule.metric_type,
            metric_value=metric_value,
            threshold_value=rule.threshold_value,
            severity=rule.severity,
            message=message,
            context={
                "comparison_operator": rule.comparison_operator,
                "threshold": rule.threshold_value
            }
        )

        self.alerts[alert_id] = alert
        return alert

    def _create_alert_from_degradation(
        self,
        rule: AlertRule,
        model_version: str,
        comparison: MetricComparisonResult
    ) -> Alert:
        """Create alert from degradation detection"""
        alert_id = f"alert_{uuid.uuid4().hex[:12]}"

        message = (
            f"{comparison.severity.upper()}: Performance degradation detected "
            f"for {rule.model_name} v{model_version}. "
            f"{rule.metric_type.value} degraded by {abs(comparison.percentage_change):.1f}% "
            f"({comparison.baseline_value:.4f} → {comparison.current_value:.4f})"
        )

        alert = Alert(
            alert_id=alert_id,
            rule_id=rule.rule_id,
            rule_name=rule.rule_name,
            model_name=rule.model_name,
            model_version=model_version,
            metric_type=rule.metric_type,
            metric_value=comparison.current_value,
            baseline_value=comparison.baseline_value,
            degradation_percentage=comparison.percentage_change,
            severity=AlertSeverity(comparison.severity) if comparison.severity != "none" else rule.severity,
            message=message,
            context={
                "recommendation": comparison.recommendation,
                "absolute_change": comparison.absolute_change
            }
        )

        self.alerts[alert_id] = alert
        return alert

    def _check_cooldown(self, rule: AlertRule) -> bool:
        """Check if rule is in cooldown period"""
        if rule.rule_id not in self.last_triggered:
            return True

        last_trigger = self.last_triggered[rule.rule_id]
        cooldown_expires = last_trigger + timedelta(minutes=rule.cooldown_minutes)

        return datetime.utcnow() > cooldown_expires

    def _check_rate_limits(self, model_name: str) -> bool:
        """Check global and per-model rate limits"""
        now = datetime.utcnow()
        one_hour_ago = now - timedelta(hours=1)

        # Clean old triggers
        self.trigger_history[model_name] = [
            t for t in self.trigger_history[model_name]
            if t > one_hour_ago
        ]

        # Check limits
        model_triggers = len(self.trigger_history[model_name])

        if model_triggers >= self.config.max_alerts_per_model_per_hour:
            return False

        # Check global limit (sum across all models)
        total_triggers = sum(len(triggers) for triggers in self.trigger_history.values())
        if total_triggers >= self.config.max_alerts_per_hour:
            return False

        return True

    def _record_trigger(self, rule: AlertRule, model_name: str) -> None:
        """Record that a rule was triggered"""
        now = datetime.utcnow()
        self.last_triggered[rule.rule_id] = now
        self.trigger_history[model_name].append(now)

    def get_alert(self, alert_id: str) -> Optional[Alert]:
        """Get alert by ID"""
        return self.alerts.get(alert_id)

    def list_alerts(
        self,
        model_name: Optional[str] = None,
        status: Optional[AlertStatus] = None,
        severity: Optional[AlertSeverity] = None,
        hours: int = 24
    ) -> List[Alert]:
        """
        List alerts with filtering

        Args:
            model_name: Filter by model
            status: Filter by status
            severity: Filter by severity
            hours: Time window

        Returns:
            List of Alert instances
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        alerts = [a for a in self.alerts.values() if a.triggered_at > cutoff_time]

        if model_name:
            alerts = [a for a in alerts if a.model_name == model_name]

        if status:
            alerts = [a for a in alerts if a.status == status]

        if severity:
            alerts = [a for a in alerts if a.severity == severity]

        # Sort by triggered time (most recent first)
        alerts.sort(key=lambda a: a.triggered_at, reverse=True)

        return alerts

    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> Optional[Alert]:
        """Acknowledge an alert"""
        alert = self.alerts.get(alert_id)
        if not alert:
            return None

        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_at = datetime.utcnow()
        alert.acknowledged_by = acknowledged_by

        return alert

    def resolve_alert(
        self,
        alert_id: str,
        resolved_by: str,
        resolution_notes: Optional[str] = None
    ) -> Optional[Alert]:
        """Resolve an alert"""
        alert = self.alerts.get(alert_id)
        if not alert:
            return None

        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = datetime.utcnow()
        alert.resolved_by = resolved_by
        alert.resolution_notes = resolution_notes

        return alert

    def get_alert_summary(
        self,
        model_name: str,
        model_version: Optional[str] = None,
        hours: int = 24
    ) -> AlertSummary:
        """Get alert summary for a model"""
        alerts = self.list_alerts(model_name=model_name, hours=hours)

        if model_version:
            alerts = [a for a in alerts if a.model_version == model_version]

        summary = AlertSummary(
            model_name=model_name,
            model_version=model_version,
            time_range_hours=hours
        )

        # Count by status
        for alert in alerts:
            if alert.status == AlertStatus.ACTIVE:
                summary.active_count += 1
            elif alert.status == AlertStatus.ACKNOWLEDGED:
                summary.acknowledged_count += 1
            elif alert.status == AlertStatus.RESOLVED:
                summary.resolved_count += 1

            # Count by severity
            if alert.severity == AlertSeverity.CRITICAL:
                summary.critical_count += 1
            elif alert.severity == AlertSeverity.HIGH:
                summary.high_count += 1
            elif alert.severity == AlertSeverity.MEDIUM:
                summary.medium_count += 1
            elif alert.severity == AlertSeverity.LOW:
                summary.low_count += 1

        # Recent alerts (top 10)
        summary.recent_alerts = alerts[:10]

        return summary
