"""
Audit Log Models
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class AuditEventType(str, Enum):
    """Types of audit events"""

    # Authentication & Authorization
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    PERMISSION_DENIED = "permission_denied"

    # Data Access
    DATA_READ = "data_read"
    DATA_EXPORT = "data_export"
    DATA_DOWNLOAD = "data_download"

    # Data Modification
    DATA_CREATE = "data_create"
    DATA_UPDATE = "data_update"
    DATA_DELETE = "data_delete"

    # Model Operations
    MODEL_TRAIN = "model_train"
    MODEL_DEPLOY = "model_deploy"
    MODEL_DELETE = "model_delete"
    MODEL_PREDICT = "model_predict"

    # Experiment Operations
    EXPERIMENT_CREATE = "experiment_create"
    EXPERIMENT_UPDATE = "experiment_update"
    EXPERIMENT_DELETE = "experiment_delete"

    # Configuration Changes
    CONFIG_UPDATE = "config_update"
    PERMISSION_CHANGE = "permission_change"
    ROLE_CHANGE = "role_change"

    # System Events
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    ERROR = "error"
    WARNING = "warning"

    # Compliance
    DATA_RETENTION_POLICY_APPLIED = "data_retention_policy_applied"
    DATA_ANONYMIZED = "data_anonymized"
    GDPR_DATA_REQUEST = "gdpr_data_request"
    GDPR_DATA_DELETION = "gdpr_data_deletion"


class AuditSeverity(str, Enum):
    """Severity levels for audit events"""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditEvent(BaseModel):
    """
    Audit log event

    Captures who did what, when, where, and why for compliance and security.
    """

    # Event identification
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: AuditEventType
    severity: AuditSeverity = AuditSeverity.INFO

    # When
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Who
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    user_ip: Optional[str] = None
    user_agent: Optional[str] = None

    # Where
    service: str = Field(default="maestro_ml", description="Service/component name")
    endpoint: Optional[str] = None

    # What
    action: str = Field(..., description="Action performed")
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None

    # How
    status: str = Field(default="success", description="success, failure, partial")

    # Why / Context
    description: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    # Changes (for data modification events)
    changes: Optional[dict[str, Any]] = Field(
        None, description="Before/after values for updates"
    )

    # Compliance
    tenant_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None

    # Security
    requires_review: bool = Field(False, description="Flag for security team review")

    class Config:
        json_schema_extra = {
            "example": {
                "event_type": "model_deploy",
                "user_id": "user_123",
                "user_email": "alice@company.com",
                "action": "Deployed model to production",
                "resource_type": "model",
                "resource_id": "model_v2.0",
                "status": "success",
                "metadata": {"model_version": "2.0", "environment": "production"},
            }
        }


class ComplianceStandard(str, Enum):
    """Compliance standards"""

    GDPR = "gdpr"  # EU General Data Protection Regulation
    HIPAA = "hipaa"  # Health Insurance Portability and Accountability Act
    SOC2 = "soc2"  # Service Organization Control 2
    PCI_DSS = "pci_dss"  # Payment Card Industry Data Security Standard
    ISO_27001 = "iso_27001"  # Information Security Management
    CCPA = "ccpa"  # California Consumer Privacy Act


class ComplianceReport(BaseModel):
    """
    Compliance report

    Summary of audit events for compliance verification.
    """

    report_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    standard: ComplianceStandard

    # Time range
    start_time: datetime
    end_time: datetime

    # Summary statistics
    total_events: int
    events_by_type: dict[str, int] = Field(default_factory=dict)
    events_by_severity: dict[str, int] = Field(default_factory=dict)

    # Security metrics
    failed_logins: int = 0
    permission_denials: int = 0
    data_exports: int = 0
    sensitive_data_access: int = 0

    # Compliance-specific metrics
    gdpr_requests: Optional[int] = None
    data_retention_violations: int = 0
    encryption_failures: int = 0

    # Critical events requiring review
    critical_events: list[AuditEvent] = Field(default_factory=list)

    # Report metadata
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    generated_by: str = Field(default="system")

    # Compliance status
    compliant: bool = True
    violations: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class AuditQuery(BaseModel):
    """Query parameters for searching audit logs"""

    # Time range
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    # Filters
    event_types: Optional[list[AuditEventType]] = None
    severities: Optional[list[AuditSeverity]] = None
    user_ids: Optional[list[str]] = None
    resource_types: Optional[list[str]] = None
    resource_ids: Optional[list[str]] = None
    tenant_ids: Optional[list[str]] = None

    # Search
    search_text: Optional[str] = None

    # Pagination
    page: int = 1
    page_size: int = 100

    # Sorting
    sort_by: str = "timestamp"
    sort_order: str = "desc"  # or "asc"


class RetentionPolicy(BaseModel):
    """Data retention policy"""

    policy_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None

    # Retention period (days)
    retention_days: int = Field(..., ge=1)

    # What to retain
    event_types: Optional[list[AuditEventType]] = None  # None = all
    severities: Optional[list[AuditSeverity]] = None

    # Archive or delete
    archive_on_expiry: bool = True
    archive_location: Optional[str] = None

    # Exceptions (never delete)
    exclude_event_types: list[AuditEventType] = Field(default_factory=list)

    # Compliance
    compliance_standards: list[ComplianceStandard] = Field(default_factory=list)

    # Status
    active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class AuditLogSettings(BaseModel):
    """Audit logging configuration"""

    # Enable/disable
    enabled: bool = True

    # What to log
    log_reads: bool = False  # Can be very verbose
    log_writes: bool = True
    log_auth: bool = True
    log_errors: bool = True

    # Minimum severity to log
    min_severity: AuditSeverity = AuditSeverity.INFO

    # Storage
    storage_backend: str = "database"  # or "file", "s3", "elasticsearch"

    # Performance
    async_logging: bool = True
    batch_size: int = 100
    flush_interval_seconds: int = 5

    # Retention
    default_retention_days: int = 90

    # Alerts
    alert_on_critical: bool = True
    alert_on_multiple_failed_logins: bool = True
    failed_login_threshold: int = 5
