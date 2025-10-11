"""
Alert Data Models

Alert configuration, rules, and triggered alerts.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

from .metrics_models import MetricType


class AlertSeverity(str, Enum):
    """Alert severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AlertStatus(str, Enum):
    """Alert lifecycle status"""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


class AlertRule(BaseModel):
    """Rule for triggering alerts"""
    rule_id: str
    rule_name: str

    # What to monitor
    model_name: str
    model_version: Optional[str] = None  # None = all versions
    metric_type: MetricType

    # Threshold conditions
    threshold_value: float
    comparison_operator: str = Field(..., description="gt, lt, gte, lte, eq")

    # Or degradation-based
    use_degradation: bool = False
    max_degradation_percentage: Optional[float] = None
    baseline_window_hours: int = Field(default=24, description="Hours to look back for baseline")

    # Alert configuration
    severity: AlertSeverity
    cooldown_minutes: int = Field(default=60, description="Min time between alerts for same rule")

    # Notification
    notify_channels: List[str] = Field(default_factory=list, description="email, slack, pagerduty")

    # Metadata
    enabled: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = "system"
    description: Optional[str] = None


class Alert(BaseModel):
    """Triggered alert instance"""
    alert_id: str
    rule_id: str
    rule_name: str

    # What triggered it
    model_name: str
    model_version: str
    metric_type: MetricType
    metric_value: float

    # Why it triggered
    threshold_value: Optional[float] = None
    baseline_value: Optional[float] = None
    degradation_percentage: Optional[float] = None

    # Alert properties
    severity: AlertSeverity
    status: AlertStatus = AlertStatus.ACTIVE
    message: str

    # Timestamps
    triggered_at: datetime = Field(default_factory=datetime.utcnow)
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    # Who handled it
    acknowledged_by: Optional[str] = None
    resolved_by: Optional[str] = None
    resolution_notes: Optional[str] = None

    # Additional context
    context: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)


class AlertConfig(BaseModel):
    """Global alert configuration"""
    # Notification settings
    email_enabled: bool = True
    email_recipients: List[str] = Field(default_factory=list)

    slack_enabled: bool = False
    slack_webhook_url: Optional[str] = None
    slack_channel: Optional[str] = None

    pagerduty_enabled: bool = False
    pagerduty_integration_key: Optional[str] = None

    # Global settings
    enable_alerts: bool = True
    min_severity_to_notify: AlertSeverity = AlertSeverity.MEDIUM

    # Rate limiting
    max_alerts_per_hour: int = 10
    max_alerts_per_model_per_hour: int = 5


class AlertSummary(BaseModel):
    """Summary of alerts for a model"""
    model_name: str
    model_version: Optional[str] = None

    # Counts by status
    active_count: int = 0
    acknowledged_count: int = 0
    resolved_count: int = 0

    # Counts by severity
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0

    # Recent alerts
    recent_alerts: List[Alert] = Field(default_factory=list)

    # Time range
    time_range_hours: int = 24


class AlertNotification(BaseModel):
    """Alert notification to be sent"""
    alert: Alert
    channels: List[str]  # email, slack, pagerduty

    notification_id: str
    sent_at: Optional[datetime] = None
    delivery_status: Dict[str, str] = Field(default_factory=dict)  # channel -> status

    retry_count: int = 0
    max_retries: int = 3
