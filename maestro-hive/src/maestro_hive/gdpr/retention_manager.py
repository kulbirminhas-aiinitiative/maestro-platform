"""
Retention Manager - Data retention policy and auto-deletion

Implements AC-4: Create data retention policy and implement auto-deletion.
Enforces GDPR Article 5(1)(e) storage limitation principle.

EPIC: MD-2156
Child Task: MD-2281 [Privacy-4]
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Optional
import json
import uuid


class DataCategory(Enum):
    """Categories of data with different retention requirements."""
    USER_CONTENT = "user_content"
    AI_PROMPTS = "ai_prompts"
    AI_RESPONSES = "ai_responses"
    AUDIT_LOGS = "audit_logs"
    CONSENT_RECORDS = "consent_records"
    SESSION_DATA = "session_data"
    ANALYTICS = "analytics"
    SYSTEM_LOGS = "system_logs"
    TRANSACTION_DATA = "transaction_data"
    BACKUP_DATA = "backup_data"


class RetentionAction(Enum):
    """Action to take when retention period expires."""
    DELETE = "delete"
    ANONYMIZE = "anonymize"
    ARCHIVE = "archive"
    NOTIFY = "notify"


class DeletionStatus(Enum):
    """Status of a deletion operation."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    VERIFIED = "verified"


@dataclass
class RetentionPolicy:
    """Defines retention policy for a data category."""
    policy_id: str
    category: DataCategory
    retention_days: int
    action: RetentionAction
    legal_basis: str
    description: str
    active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    notify_before_days: int = 7
    require_approval: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "policy_id": self.policy_id,
            "category": self.category.value,
            "retention_days": self.retention_days,
            "action": self.action.value,
            "legal_basis": self.legal_basis,
            "description": self.description,
            "active": self.active,
            "created_at": self.created_at.isoformat(),
            "notify_before_days": self.notify_before_days,
            "require_approval": self.require_approval,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RetentionPolicy":
        """Create from dictionary."""
        return cls(
            policy_id=data["policy_id"],
            category=DataCategory(data["category"]),
            retention_days=data["retention_days"],
            action=RetentionAction(data["action"]),
            legal_basis=data["legal_basis"],
            description=data["description"],
            active=data.get("active", True),
            created_at=datetime.fromisoformat(data["created_at"]),
            notify_before_days=data.get("notify_before_days", 7),
            require_approval=data.get("require_approval", False),
        )


@dataclass
class DataRecord:
    """Represents a data record subject to retention."""
    record_id: str
    category: DataCategory
    user_id: Optional[str]
    created_at: datetime
    expires_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)
    deletion_status: Optional[DeletionStatus] = None
    deleted_at: Optional[datetime] = None


@dataclass
class DeletionJob:
    """Represents a scheduled deletion job."""
    job_id: str
    policy_id: str
    category: DataCategory
    scheduled_at: datetime
    status: DeletionStatus
    records_count: int
    records_deleted: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "job_id": self.job_id,
            "policy_id": self.policy_id,
            "category": self.category.value,
            "scheduled_at": self.scheduled_at.isoformat(),
            "status": self.status.value,
            "records_count": self.records_count,
            "records_deleted": self.records_deleted,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
        }


class RetentionManager:
    """
    Manages data retention policies and auto-deletion.

    Implements GDPR Article 5(1)(e) - Storage Limitation:
    Personal data shall be kept in a form which permits identification
    of data subjects for no longer than is necessary.
    """

    # Default retention periods by category (in days)
    DEFAULT_RETENTION = {
        DataCategory.USER_CONTENT: 365,
        DataCategory.AI_PROMPTS: 90,
        DataCategory.AI_RESPONSES: 90,
        DataCategory.AUDIT_LOGS: 2555,  # 7 years for compliance
        DataCategory.CONSENT_RECORDS: 2555,  # 7 years
        DataCategory.SESSION_DATA: 30,
        DataCategory.ANALYTICS: 365,
        DataCategory.SYSTEM_LOGS: 90,
        DataCategory.TRANSACTION_DATA: 2555,
        DataCategory.BACKUP_DATA: 365,
    }

    def __init__(self):
        """Initialize Retention Manager."""
        self._policies: dict[str, RetentionPolicy] = {}
        self._records: dict[str, DataRecord] = {}
        self._jobs: dict[str, DeletionJob] = {}
        self._deletion_handlers: dict[DataCategory, Callable[[str], bool]] = {}
        self._initialize_default_policies()

    def _initialize_default_policies(self) -> None:
        """Create default retention policies."""
        for category, days in self.DEFAULT_RETENTION.items():
            self.create_policy(
                category=category,
                retention_days=days,
                action=RetentionAction.DELETE,
                legal_basis="GDPR Article 5(1)(e) - Storage Limitation",
                description=f"Default retention policy for {category.value}",
            )

    def create_policy(
        self,
        category: DataCategory,
        retention_days: int,
        action: RetentionAction,
        legal_basis: str,
        description: str,
        notify_before_days: int = 7,
        require_approval: bool = False,
    ) -> RetentionPolicy:
        """
        Create a retention policy.

        Args:
            category: Data category this policy applies to
            retention_days: Days to retain data
            action: Action when retention expires
            legal_basis: Legal basis for retention period
            description: Policy description
            notify_before_days: Days before expiry to notify
            require_approval: Whether deletion requires approval

        Returns:
            Created retention policy
        """
        policy_id = f"POLICY-{uuid.uuid4().hex[:8].upper()}"

        policy = RetentionPolicy(
            policy_id=policy_id,
            category=category,
            retention_days=retention_days,
            action=action,
            legal_basis=legal_basis,
            description=description,
            notify_before_days=notify_before_days,
            require_approval=require_approval,
        )

        self._policies[policy_id] = policy
        return policy

    def update_policy(
        self,
        policy_id: str,
        retention_days: Optional[int] = None,
        action: Optional[RetentionAction] = None,
        active: Optional[bool] = None,
    ) -> RetentionPolicy:
        """Update an existing retention policy."""
        if policy_id not in self._policies:
            raise ValueError(f"Policy not found: {policy_id}")

        policy = self._policies[policy_id]

        if retention_days is not None:
            policy.retention_days = retention_days
        if action is not None:
            policy.action = action
        if active is not None:
            policy.active = active

        return policy

    def get_policy(self, policy_id: str) -> Optional[RetentionPolicy]:
        """Get a policy by ID."""
        return self._policies.get(policy_id)

    def get_policy_for_category(self, category: DataCategory) -> Optional[RetentionPolicy]:
        """Get active policy for a data category."""
        for policy in self._policies.values():
            if policy.category == category and policy.active:
                return policy
        return None

    def list_policies(self, active_only: bool = True) -> list[RetentionPolicy]:
        """List all retention policies."""
        policies = list(self._policies.values())
        if active_only:
            policies = [p for p in policies if p.active]
        return policies

    def register_record(
        self,
        category: DataCategory,
        user_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> DataRecord:
        """
        Register a data record for retention tracking.

        Args:
            category: Category of the data
            user_id: Optional user ID associated with record
            metadata: Additional metadata

        Returns:
            Created data record
        """
        policy = self.get_policy_for_category(category)
        if not policy:
            raise ValueError(f"No active policy for category: {category.value}")

        record_id = f"REC-{uuid.uuid4().hex[:12].upper()}"
        now = datetime.utcnow()

        record = DataRecord(
            record_id=record_id,
            category=category,
            user_id=user_id,
            created_at=now,
            expires_at=now + timedelta(days=policy.retention_days),
            metadata=metadata or {},
        )

        self._records[record_id] = record
        return record

    def get_record(self, record_id: str) -> Optional[DataRecord]:
        """Get a data record by ID."""
        return self._records.get(record_id)

    def get_expired_records(
        self,
        category: Optional[DataCategory] = None,
    ) -> list[DataRecord]:
        """
        Get records that have exceeded their retention period.

        Args:
            category: Filter by category (None = all)

        Returns:
            List of expired records
        """
        now = datetime.utcnow()
        expired = []

        for record in self._records.values():
            if record.deletion_status is not None:
                continue
            if record.expires_at <= now:
                if category is None or record.category == category:
                    expired.append(record)

        return expired

    def get_expiring_records(
        self,
        days: int = 7,
        category: Optional[DataCategory] = None,
    ) -> list[DataRecord]:
        """
        Get records expiring within specified days.

        Args:
            days: Days until expiry
            category: Filter by category

        Returns:
            List of expiring records
        """
        threshold = datetime.utcnow() + timedelta(days=days)
        expiring = []

        for record in self._records.values():
            if record.deletion_status is not None:
                continue
            if record.expires_at <= threshold:
                if category is None or record.category == category:
                    expiring.append(record)

        return expiring

    def register_deletion_handler(
        self,
        category: DataCategory,
        handler: Callable[[str], bool],
    ) -> None:
        """
        Register a handler function for deleting data.

        Args:
            category: Category this handler handles
            handler: Function that takes record_id and returns success
        """
        self._deletion_handlers[category] = handler

    def schedule_deletion(
        self,
        category: Optional[DataCategory] = None,
        immediate: bool = False,
    ) -> DeletionJob:
        """
        Schedule deletion of expired records.

        Args:
            category: Category to process (None = all)
            immediate: Execute immediately

        Returns:
            Created deletion job
        """
        expired = self.get_expired_records(category)
        if not expired:
            raise ValueError("No expired records to delete")

        policy = None
        if category:
            policy = self.get_policy_for_category(category)

        job_id = f"JOB-{uuid.uuid4().hex[:8].upper()}"
        now = datetime.utcnow()

        job = DeletionJob(
            job_id=job_id,
            policy_id=policy.policy_id if policy else "MULTI",
            category=category or DataCategory.USER_CONTENT,
            scheduled_at=now if immediate else now + timedelta(hours=1),
            status=DeletionStatus.PENDING,
            records_count=len(expired),
        )

        self._jobs[job_id] = job

        if immediate:
            self.execute_deletion_job(job_id)

        return job

    def execute_deletion_job(self, job_id: str) -> DeletionJob:
        """
        Execute a scheduled deletion job.

        Args:
            job_id: Job to execute

        Returns:
            Updated job with results
        """
        if job_id not in self._jobs:
            raise ValueError(f"Job not found: {job_id}")

        job = self._jobs[job_id]
        job.status = DeletionStatus.IN_PROGRESS
        job.started_at = datetime.utcnow()

        expired = self.get_expired_records(job.category)
        deleted_count = 0

        for record in expired:
            try:
                # Use registered handler or mark as deleted
                handler = self._deletion_handlers.get(record.category)
                if handler:
                    success = handler(record.record_id)
                else:
                    success = True  # Default: just mark as deleted

                if success:
                    record.deletion_status = DeletionStatus.COMPLETED
                    record.deleted_at = datetime.utcnow()
                    deleted_count += 1
                else:
                    record.deletion_status = DeletionStatus.FAILED

            except Exception as e:
                record.deletion_status = DeletionStatus.FAILED
                job.error_message = str(e)

        job.records_deleted = deleted_count
        job.completed_at = datetime.utcnow()
        job.status = (
            DeletionStatus.COMPLETED
            if deleted_count == len(expired)
            else DeletionStatus.FAILED
        )

        return job

    def get_job(self, job_id: str) -> Optional[DeletionJob]:
        """Get a deletion job by ID."""
        return self._jobs.get(job_id)

    def list_jobs(
        self,
        status: Optional[DeletionStatus] = None,
    ) -> list[DeletionJob]:
        """List deletion jobs with optional status filter."""
        jobs = list(self._jobs.values())
        if status:
            jobs = [j for j in jobs if j.status == status]
        return jobs

    def get_retention_report(self) -> dict[str, Any]:
        """
        Generate retention status report.

        Returns:
            Dictionary with retention statistics
        """
        now = datetime.utcnow()
        report = {
            "generated_at": now.isoformat(),
            "policies": {},
            "records": {
                "total": len(self._records),
                "active": 0,
                "expired": 0,
                "deleted": 0,
            },
            "jobs": {
                "total": len(self._jobs),
                "pending": 0,
                "completed": 0,
                "failed": 0,
            },
        }

        # Policy summary
        for policy in self._policies.values():
            category_key = policy.category.value
            if category_key not in report["policies"]:
                report["policies"][category_key] = {
                    "retention_days": policy.retention_days,
                    "action": policy.action.value,
                    "active": policy.active,
                }

        # Record summary
        for record in self._records.values():
            if record.deletion_status == DeletionStatus.COMPLETED:
                report["records"]["deleted"] += 1
            elif record.expires_at <= now:
                report["records"]["expired"] += 1
            else:
                report["records"]["active"] += 1

        # Job summary
        for job in self._jobs.values():
            if job.status == DeletionStatus.PENDING:
                report["jobs"]["pending"] += 1
            elif job.status == DeletionStatus.COMPLETED:
                report["jobs"]["completed"] += 1
            elif job.status == DeletionStatus.FAILED:
                report["jobs"]["failed"] += 1

        return report

    def export_policies(self) -> str:
        """Export all policies as JSON."""
        return json.dumps(
            [p.to_dict() for p in self._policies.values()],
            indent=2,
        )

    def extend_retention(
        self,
        record_id: str,
        additional_days: int,
        reason: str,
    ) -> DataRecord:
        """
        Extend retention period for a specific record.

        Args:
            record_id: Record to extend
            additional_days: Days to add
            reason: Justification for extension

        Returns:
            Updated record
        """
        if record_id not in self._records:
            raise ValueError(f"Record not found: {record_id}")

        record = self._records[record_id]
        record.expires_at = record.expires_at + timedelta(days=additional_days)
        record.metadata["retention_extended"] = {
            "extended_at": datetime.utcnow().isoformat(),
            "additional_days": additional_days,
            "reason": reason,
        }

        return record
