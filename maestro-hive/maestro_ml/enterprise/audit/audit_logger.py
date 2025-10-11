"""
Audit Logger

Comprehensive audit logging for compliance and security.
"""

import asyncio
import logging
from collections import defaultdict
from collections.abc import Callable
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Optional

from .models import (
    AuditEvent,
    AuditEventType,
    AuditLogSettings,
    AuditQuery,
    AuditSeverity,
    ComplianceReport,
    ComplianceStandard,
    RetentionPolicy,
)

logger = logging.getLogger(__name__)


class AuditLogger:
    """
    Enterprise audit logger

    Features:
    - Comprehensive event tracking
    - Async batching for performance
    - Compliance reporting (GDPR, SOC2, HIPAA)
    - Retention policies
    - Security alerts
    """

    def __init__(self, settings: Optional[AuditLogSettings] = None):
        """
        Initialize audit logger

        Args:
            settings: Audit logging configuration
        """
        self.settings = settings or AuditLogSettings()
        self.logger = logger

        # In-memory storage (in production, use database/Elasticsearch)
        self.events: list[AuditEvent] = []
        self.retention_policies: dict[str, RetentionPolicy] = {}

        # Batching
        self.event_buffer: list[AuditEvent] = []
        self.buffer_lock = asyncio.Lock()

        # Security tracking
        self.failed_login_tracker: dict[str, list[datetime]] = defaultdict(list)

        self.logger.info("AuditLogger initialized")

    def log_event(
        self,
        event_type: AuditEventType,
        action: str,
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        status: str = "success",
        severity: AuditSeverity = AuditSeverity.INFO,
        metadata: Optional[dict[str, Any]] = None,
        **kwargs,
    ) -> AuditEvent:
        """
        Log an audit event

        Args:
            event_type: Type of event
            action: Description of action
            user_id: User performing action
            user_email: User email
            resource_type: Type of resource affected
            resource_id: ID of resource
            status: success, failure, partial
            severity: Event severity
            metadata: Additional context
            **kwargs: Additional event fields

        Returns:
            Created audit event
        """
        if not self.settings.enabled:
            return None

        # Check severity threshold
        severity_order = {
            AuditSeverity.DEBUG: 0,
            AuditSeverity.INFO: 1,
            AuditSeverity.WARNING: 2,
            AuditSeverity.ERROR: 3,
            AuditSeverity.CRITICAL: 4,
        }

        if severity_order[severity] < severity_order[self.settings.min_severity]:
            return None

        # Create event
        event = AuditEvent(
            event_type=event_type,
            action=action,
            user_id=user_id,
            user_email=user_email,
            resource_type=resource_type,
            resource_id=resource_id,
            status=status,
            severity=severity,
            metadata=metadata or {},
            **kwargs,
        )

        # Store event
        if self.settings.async_logging:
            self.event_buffer.append(event)
            if len(self.event_buffer) >= self.settings.batch_size:
                self._flush_buffer()
        else:
            self.events.append(event)

        # Security checks
        self._check_security_alerts(event)

        # Log to standard logger
        log_level = self._severity_to_log_level(severity)
        self.logger.log(log_level, f"[AUDIT] {action} - {event.event_id}")

        return event

    def _flush_buffer(self):
        """Flush event buffer to storage"""
        if not self.event_buffer:
            return

        self.events.extend(self.event_buffer)
        self.event_buffer.clear()

        self.logger.debug(f"Flushed {len(self.event_buffer)} events to storage")

    def _check_security_alerts(self, event: AuditEvent):
        """Check for security issues and send alerts"""
        # Critical events
        if event.severity == AuditSeverity.CRITICAL and self.settings.alert_on_critical:
            self._send_alert(f"Critical event: {event.action}", event)

        # Failed login tracking
        if event.event_type == AuditEventType.LOGIN_FAILED:
            user_key = event.user_email or event.user_id or event.user_ip
            if user_key:
                self.failed_login_tracker[user_key].append(event.timestamp)

                # Clean old entries (last hour)
                cutoff = datetime.utcnow() - timedelta(hours=1)
                self.failed_login_tracker[user_key] = [
                    ts for ts in self.failed_login_tracker[user_key] if ts > cutoff
                ]

                # Check threshold
                if (
                    len(self.failed_login_tracker[user_key])
                    >= self.settings.failed_login_threshold
                ):
                    self._send_alert(f"Multiple failed logins for {user_key}", event)

    def _send_alert(self, message: str, event: AuditEvent):
        """Send security alert (email, Slack, PagerDuty, etc.)"""
        # In production, integrate with alerting system
        self.logger.warning(f"[SECURITY ALERT] {message}")
        event.requires_review = True

    def _severity_to_log_level(self, severity: AuditSeverity) -> int:
        """Convert audit severity to logging level"""
        mapping = {
            AuditSeverity.DEBUG: logging.DEBUG,
            AuditSeverity.INFO: logging.INFO,
            AuditSeverity.WARNING: logging.WARNING,
            AuditSeverity.ERROR: logging.ERROR,
            AuditSeverity.CRITICAL: logging.CRITICAL,
        }
        return mapping.get(severity, logging.INFO)

    def query_events(self, query: AuditQuery) -> list[AuditEvent]:
        """
        Query audit events

        Args:
            query: Query parameters

        Returns:
            Matching audit events
        """
        # Flush buffer first
        self._flush_buffer()

        # Filter events
        filtered = self.events

        # Time range
        if query.start_time:
            filtered = [e for e in filtered if e.timestamp >= query.start_time]
        if query.end_time:
            filtered = [e for e in filtered if e.timestamp <= query.end_time]

        # Event types
        if query.event_types:
            filtered = [e for e in filtered if e.event_type in query.event_types]

        # Severities
        if query.severities:
            filtered = [e for e in filtered if e.severity in query.severities]

        # Users
        if query.user_ids:
            filtered = [e for e in filtered if e.user_id in query.user_ids]

        # Resources
        if query.resource_types:
            filtered = [e for e in filtered if e.resource_type in query.resource_types]
        if query.resource_ids:
            filtered = [e for e in filtered if e.resource_id in query.resource_ids]

        # Tenants
        if query.tenant_ids:
            filtered = [e for e in filtered if e.tenant_id in query.tenant_ids]

        # Text search
        if query.search_text:
            search_lower = query.search_text.lower()
            filtered = [
                e
                for e in filtered
                if search_lower in (e.action or "").lower()
                or search_lower in (e.description or "").lower()
            ]

        # Sort
        reverse = query.sort_order == "desc"
        filtered.sort(
            key=lambda e: getattr(e, query.sort_by, e.timestamp), reverse=reverse
        )

        # Paginate
        start = (query.page - 1) * query.page_size
        end = start + query.page_size

        return filtered[start:end]

    def generate_compliance_report(
        self, standard: ComplianceStandard, start_time: datetime, end_time: datetime
    ) -> ComplianceReport:
        """
        Generate compliance report

        Args:
            standard: Compliance standard (GDPR, SOC2, etc.)
            start_time: Report start time
            end_time: Report end time

        Returns:
            Compliance report
        """
        # Query events in time range
        query = AuditQuery(start_time=start_time, end_time=end_time, page_size=999999)
        events = self.query_events(query)

        # Count by type
        events_by_type = defaultdict(int)
        for event in events:
            events_by_type[event.event_type.value] += 1

        # Count by severity
        events_by_severity = defaultdict(int)
        for event in events:
            events_by_severity[event.severity.value] += 1

        # Security metrics
        failed_logins = sum(
            1 for e in events if e.event_type == AuditEventType.LOGIN_FAILED
        )

        permission_denials = sum(
            1 for e in events if e.event_type == AuditEventType.PERMISSION_DENIED
        )

        data_exports = sum(
            1 for e in events if e.event_type == AuditEventType.DATA_EXPORT
        )

        # GDPR-specific
        gdpr_requests = None
        if standard == ComplianceStandard.GDPR:
            gdpr_requests = sum(
                1
                for e in events
                if e.event_type
                in [AuditEventType.GDPR_DATA_REQUEST, AuditEventType.GDPR_DATA_DELETION]
            )

        # Critical events
        critical_events = [
            e
            for e in events
            if e.severity == AuditSeverity.CRITICAL or e.requires_review
        ]

        # Compliance checks
        violations = []
        recommendations = []

        if failed_logins > 100:
            violations.append(f"High number of failed logins ({failed_logins})")
            recommendations.append("Implement stronger authentication controls")

        if data_exports > 50:
            recommendations.append("Review data export policies and access controls")

        compliant = len(violations) == 0

        return ComplianceReport(
            standard=standard,
            start_time=start_time,
            end_time=end_time,
            total_events=len(events),
            events_by_type=dict(events_by_type),
            events_by_severity=dict(events_by_severity),
            failed_logins=failed_logins,
            permission_denials=permission_denials,
            data_exports=data_exports,
            gdpr_requests=gdpr_requests,
            critical_events=critical_events[:100],  # Limit to 100
            compliant=compliant,
            violations=violations,
            recommendations=recommendations,
        )

    def add_retention_policy(self, policy: RetentionPolicy):
        """Add a data retention policy"""
        self.retention_policies[policy.policy_id] = policy
        self.logger.info(
            f"Added retention policy: {policy.name} ({policy.retention_days} days)"
        )

    def apply_retention_policies(self):
        """Apply retention policies and clean up old events"""
        cutoff_dates = {}

        for policy in self.retention_policies.values():
            if not policy.active:
                continue

            cutoff = datetime.utcnow() - timedelta(days=policy.retention_days)
            cutoff_dates[policy.policy_id] = cutoff

        # Find events to delete/archive
        events_to_remove = []
        events_to_archive = []

        for event in self.events:
            for policy_id, policy in self.retention_policies.items():
                cutoff = cutoff_dates[policy_id]

                # Check if policy applies to this event
                if policy.event_types and event.event_type not in policy.event_types:
                    continue

                # Check exclusions
                if event.event_type in policy.exclude_event_types:
                    continue

                # Check if expired
                if event.timestamp < cutoff:
                    if policy.archive_on_expiry:
                        events_to_archive.append((event, policy))
                    else:
                        events_to_remove.append(event)
                    break

        # Archive
        for event, policy in events_to_archive:
            self._archive_event(event, policy.archive_location)
            events_to_remove.append(event)

        # Remove
        for event in events_to_remove:
            self.events.remove(event)

        self.logger.info(
            f"Applied retention policies: "
            f"{len(events_to_archive)} archived, "
            f"{len(events_to_remove)} deleted"
        )

    def _archive_event(self, event: AuditEvent, location: Optional[str]):
        """Archive an event to cold storage"""
        # In production, write to S3, Glacier, etc.
        self.logger.debug(f"Archived event {event.event_id} to {location}")


# Decorator for automatic audit logging
def audit_log(
    event_type: AuditEventType,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
):
    """
    Decorator to automatically log function calls

    Usage:
        @audit_log(AuditEventType.MODEL_TRAIN, action="Train model")
        def train_model(user_id, model_name):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract user context
            user_id = kwargs.get("user_id") or (args[0] if args else None)

            # Determine action
            nonlocal action
            if action is None:
                action = f"{func.__name__} called"

            # Get global audit logger (would be injected in production)
            # For now, create a default one
            audit_logger = AuditLogger()

            try:
                # Execute function
                result = func(*args, **kwargs)

                # Log success
                audit_logger.log_event(
                    event_type=event_type,
                    action=action,
                    user_id=str(user_id) if user_id else None,
                    resource_type=resource_type,
                    status="success",
                    metadata={"function": func.__name__},
                )

                return result

            except Exception as e:
                # Log failure
                audit_logger.log_event(
                    event_type=event_type,
                    action=f"{action} (failed)",
                    user_id=str(user_id) if user_id else None,
                    resource_type=resource_type,
                    status="failure",
                    severity=AuditSeverity.ERROR,
                    metadata={"function": func.__name__, "error": str(e)},
                )
                raise

        return wrapper

    return decorator
