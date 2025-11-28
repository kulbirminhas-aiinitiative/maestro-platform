"""
ACC Security Tests: Data Retention Policies
Test IDs: ACC-435 to ACC-449

Tests for data retention and lifecycle management:
- Retention period enforcement
- Automatic data deletion
- Archive before delete
- Retention policy by data type
- Legal hold handling
- Compliance reporting

These tests ensure:
1. Data is retained for required periods
2. Old data is automatically deleted
3. Legal holds prevent deletion
4. Audit trails for retention actions
"""

import pytest
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum


class DataType(Enum):
    """Types of data with different retention requirements"""
    USER_DATA = "user_data"
    AUDIT_LOG = "audit_log"
    TRANSACTION = "transaction"
    SESSION = "session"
    TEMP_FILE = "temp_file"
    BACKUP = "backup"


class RetentionAction(Enum):
    """Actions taken on data"""
    ARCHIVED = "archived"
    DELETED = "deleted"
    RETAINED = "retained"


@dataclass
class DataRecord:
    """Data record with lifecycle metadata"""
    record_id: str
    data_type: DataType
    created_at: datetime
    data: Dict[str, Any] = field(default_factory=dict)
    archived_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    legal_hold: bool = False
    retention_days: Optional[int] = None  # Override default

    def age_days(self) -> int:
        """Get age of record in days"""
        return (datetime.now() - self.created_at).days

    def is_expired(self, retention_days: int) -> bool:
        """Check if record has exceeded retention period"""
        if self.legal_hold:
            return False  # Legal hold prevents expiration
        return self.age_days() > retention_days


@dataclass
class RetentionPolicyRule:
    """Retention policy rule for a data type"""
    data_type: DataType
    retention_days: int
    archive_before_delete: bool = False
    archive_days: Optional[int] = None  # Days before archiving (if applicable)


@dataclass
class RetentionActionLog:
    """Log of retention action"""
    record_id: str
    action: RetentionAction
    timestamp: datetime = field(default_factory=datetime.now)
    reason: str = ""


class RetentionPolicyEngine:
    """Manages data retention policies"""

    def __init__(self):
        # Default retention policies
        self.policies: Dict[DataType, RetentionPolicyRule] = {
            DataType.USER_DATA: RetentionPolicyRule(
                data_type=DataType.USER_DATA,
                retention_days=2555,  # 7 years
                archive_before_delete=True,
                archive_days=1825  # 5 years
            ),
            DataType.AUDIT_LOG: RetentionPolicyRule(
                data_type=DataType.AUDIT_LOG,
                retention_days=2555,  # 7 years
                archive_before_delete=True,
                archive_days=365  # 1 year
            ),
            DataType.TRANSACTION: RetentionPolicyRule(
                data_type=DataType.TRANSACTION,
                retention_days=2555,  # 7 years
                archive_before_delete=True,
                archive_days=1825  # 5 years
            ),
            DataType.SESSION: RetentionPolicyRule(
                data_type=DataType.SESSION,
                retention_days=90,  # 90 days
                archive_before_delete=False
            ),
            DataType.TEMP_FILE: RetentionPolicyRule(
                data_type=DataType.TEMP_FILE,
                retention_days=7,  # 7 days
                archive_before_delete=False
            ),
            DataType.BACKUP: RetentionPolicyRule(
                data_type=DataType.BACKUP,
                retention_days=90,  # 90 days
                archive_before_delete=False
            ),
        }

        self._records: Dict[str, DataRecord] = {}
        self._archived_records: Dict[str, DataRecord] = {}
        self._action_logs: List[RetentionActionLog] = []

    def add_record(self, record: DataRecord):
        """Add data record"""
        self._records[record.record_id] = record

    def get_policy(self, data_type: DataType) -> RetentionPolicyRule:
        """Get retention policy for data type"""
        return self.policies[data_type]

    def enforce_retention(self) -> Dict[str, Any]:
        """
        Enforce retention policies on all records.

        Returns statistics about actions taken.
        """
        stats = {
            "total_records": len(self._records),
            "archived": 0,
            "deleted": 0,
            "retained": 0,
            "legal_holds": 0
        }

        records_to_delete = []

        for record_id, record in self._records.items():
            # Skip records on legal hold
            if record.legal_hold:
                stats["legal_holds"] += 1
                continue

            # Get policy
            policy = self.policies[record.data_type]

            # Use record-specific retention if set
            retention_days = record.retention_days if record.retention_days else policy.retention_days

            # Check if record should be archived
            if (policy.archive_before_delete and
                policy.archive_days and
                not record.archived_at and
                record.age_days() > policy.archive_days):

                self._archive_record(record)
                stats["archived"] += 1

            # Check if record should be deleted
            if record.is_expired(retention_days):
                # If policy requires archiving, check if archived
                if policy.archive_before_delete and not record.archived_at:
                    # Must archive first
                    self._archive_record(record)
                    stats["archived"] += 1

                records_to_delete.append(record_id)
                stats["deleted"] += 1
            else:
                stats["retained"] += 1

        # Delete expired records
        for record_id in records_to_delete:
            self._delete_record(record_id)

        return stats

    def _archive_record(self, record: DataRecord):
        """Archive a record"""
        record.archived_at = datetime.now()
        self._archived_records[record.record_id] = record

        self._action_logs.append(RetentionActionLog(
            record_id=record.record_id,
            action=RetentionAction.ARCHIVED,
            reason=f"Archived after {record.age_days()} days"
        ))

    def _delete_record(self, record_id: str):
        """Delete a record"""
        record = self._records[record_id]
        record.deleted_at = datetime.now()

        self._action_logs.append(RetentionActionLog(
            record_id=record_id,
            action=RetentionAction.DELETED,
            reason=f"Deleted after {record.age_days()} days (retention period exceeded)"
        ))

        del self._records[record_id]

    def set_legal_hold(self, record_id: str, hold: bool = True):
        """Set or release legal hold on record"""
        if record_id in self._records:
            self._records[record_id].legal_hold = hold

    def get_action_logs(self, record_id: Optional[str] = None) -> List[RetentionActionLog]:
        """Get retention action logs"""
        if record_id:
            return [log for log in self._action_logs if log.record_id == record_id]
        return self._action_logs.copy()

    def get_records_for_review(self, data_type: Optional[DataType] = None) -> List[DataRecord]:
        """Get records approaching retention deadline"""
        policy = self.policies[data_type] if data_type else None
        approaching = []

        for record in self._records.values():
            if data_type and record.data_type != data_type:
                continue

            record_policy = self.policies[record.data_type]
            retention_days = record.retention_days if record.retention_days else record_policy.retention_days

            # Records within 30 days of deletion
            days_until_deletion = retention_days - record.age_days()
            if 0 < days_until_deletion <= 30:
                approaching.append(record)

        return approaching


@pytest.mark.acc
@pytest.mark.security
class TestRetentionPolicies:
    """Test suite for retention policy definitions"""

    @pytest.fixture
    def engine(self):
        return RetentionPolicyEngine()

    def test_acc_435_user_data_retention_7_years(self, engine):
        """ACC-435: User data retained for 7 years"""
        policy = engine.get_policy(DataType.USER_DATA)

        assert policy.retention_days == 2555  # ~7 years

    def test_acc_436_audit_log_retention_7_years(self, engine):
        """ACC-436: Audit logs retained for 7 years"""
        policy = engine.get_policy(DataType.AUDIT_LOG)

        assert policy.retention_days == 2555  # ~7 years

    def test_acc_437_session_data_retention_90_days(self, engine):
        """ACC-437: Session data retained for 90 days"""
        policy = engine.get_policy(DataType.SESSION)

        assert policy.retention_days == 90

    def test_acc_438_temp_file_retention_7_days(self, engine):
        """ACC-438: Temporary files retained for 7 days"""
        policy = engine.get_policy(DataType.TEMP_FILE)

        assert policy.retention_days == 7

    def test_acc_439_archive_before_delete_for_user_data(self, engine):
        """ACC-439: User data must be archived before deletion"""
        policy = engine.get_policy(DataType.USER_DATA)

        assert policy.archive_before_delete is True
        assert policy.archive_days is not None


@pytest.mark.acc
@pytest.mark.security
class TestRetentionEnforcement:
    """Test suite for retention enforcement"""

    @pytest.fixture
    def engine(self):
        return RetentionPolicyEngine()

    def test_acc_440_old_record_deleted_after_retention_period(self, engine):
        """ACC-440: Old records are deleted after retention period"""
        # Create record older than temp file retention (7 days)
        old_record = DataRecord(
            record_id="temp-1",
            data_type=DataType.TEMP_FILE,
            created_at=datetime.now() - timedelta(days=10),
            data={"content": "temporary data"}
        )

        engine.add_record(old_record)
        initial_count = len(engine._records)

        # Enforce retention
        stats = engine.enforce_retention()

        assert stats["deleted"] == 1
        assert len(engine._records) == initial_count - 1
        assert "temp-1" not in engine._records

    def test_acc_441_recent_record_retained(self, engine):
        """ACC-441: Recent records are retained"""
        recent_record = DataRecord(
            record_id="session-1",
            data_type=DataType.SESSION,
            created_at=datetime.now() - timedelta(days=30),  # 30 days old, retained for 90
            data={"session_data": "active"}
        )

        engine.add_record(recent_record)

        stats = engine.enforce_retention()

        assert stats["deleted"] == 0
        assert stats["retained"] >= 1
        assert "session-1" in engine._records

    def test_acc_442_record_archived_before_deletion(self, engine):
        """ACC-442: Records requiring archiving are archived before deletion"""
        # Audit log should be archived after 1 year, deleted after 7 years
        # Create record 8 years old (should be archived and deleted)
        old_audit = DataRecord(
            record_id="audit-1",
            data_type=DataType.AUDIT_LOG,
            created_at=datetime.now() - timedelta(days=2920),  # ~8 years
            data={"log": "old audit"}
        )

        engine.add_record(old_audit)

        stats = engine.enforce_retention()

        # Should be both archived and deleted
        assert stats["archived"] >= 1
        assert stats["deleted"] == 1

        # Check action logs
        logs = engine.get_action_logs("audit-1")
        actions = [log.action for log in logs]
        assert RetentionAction.ARCHIVED in actions
        assert RetentionAction.DELETED in actions

    def test_acc_443_legal_hold_prevents_deletion(self, engine):
        """ACC-443: Legal hold prevents record deletion"""
        old_record = DataRecord(
            record_id="legal-1",
            data_type=DataType.TEMP_FILE,
            created_at=datetime.now() - timedelta(days=30),  # Older than 7 day retention
            data={"content": "legal evidence"},
            legal_hold=True
        )

        engine.add_record(old_record)

        stats = engine.enforce_retention()

        # Should not be deleted due to legal hold
        assert stats["deleted"] == 0
        assert stats["legal_holds"] == 1
        assert "legal-1" in engine._records

    def test_acc_444_release_legal_hold_allows_deletion(self, engine):
        """ACC-444: Releasing legal hold allows deletion"""
        old_record = DataRecord(
            record_id="legal-2",
            data_type=DataType.TEMP_FILE,
            created_at=datetime.now() - timedelta(days=30),
            data={"content": "was under legal hold"},
            legal_hold=True
        )

        engine.add_record(old_record)

        # First enforcement - not deleted due to hold
        stats1 = engine.enforce_retention()
        assert stats1["deleted"] == 0

        # Release legal hold
        engine.set_legal_hold("legal-2", hold=False)

        # Second enforcement - now deleted
        stats2 = engine.enforce_retention()
        assert stats2["deleted"] == 1
        assert "legal-2" not in engine._records

    def test_acc_445_custom_retention_overrides_policy(self, engine):
        """ACC-445: Record-specific retention overrides policy default"""
        # Temp file with custom 30-day retention (policy is 7 days)
        record = DataRecord(
            record_id="custom-1",
            data_type=DataType.TEMP_FILE,
            created_at=datetime.now() - timedelta(days=10),  # Would be deleted under policy
            data={"content": "important temp file"},
            retention_days=30  # Custom retention
        )

        engine.add_record(record)

        stats = engine.enforce_retention()

        # Should be retained due to custom retention
        assert stats["deleted"] == 0
        assert "custom-1" in engine._records


@pytest.mark.acc
@pytest.mark.security
class TestRetentionReporting:
    """Test suite for retention compliance reporting"""

    @pytest.fixture
    def engine(self):
        engine = RetentionPolicyEngine()

        # Add various records
        engine.add_record(DataRecord(
            record_id="user-1",
            data_type=DataType.USER_DATA,
            created_at=datetime.now() - timedelta(days=2000),
            data={"name": "User 1"}
        ))
        engine.add_record(DataRecord(
            record_id="session-1",
            data_type=DataType.SESSION,
            created_at=datetime.now() - timedelta(days=70),  # Approaching deletion (90 day policy)
            data={"session": "data"}
        ))
        engine.add_record(DataRecord(
            record_id="temp-1",
            data_type=DataType.TEMP_FILE,
            created_at=datetime.now() - timedelta(days=1),
            data={"temp": "file"}
        ))

        return engine

    def test_acc_446_get_records_approaching_deletion(self, engine):
        """ACC-446: Can identify records approaching retention deadline"""
        approaching = engine.get_records_for_review(DataType.SESSION)

        # session-1 is 70 days old with 90 day policy (20 days remaining)
        assert len(approaching) >= 1
        assert any(r.record_id == "session-1" for r in approaching)

    def test_acc_447_retention_action_logs_created(self, engine):
        """ACC-447: Retention actions are logged"""
        engine.enforce_retention()

        logs = engine.get_action_logs()

        assert len(logs) > 0

    def test_acc_448_get_action_logs_for_specific_record(self, engine):
        """ACC-448: Can retrieve action logs for specific record"""
        engine.enforce_retention()

        # Get logs for a specific record that was processed
        all_logs = engine.get_action_logs()
        if all_logs:
            record_id = all_logs[0].record_id
            record_logs = engine.get_action_logs(record_id)

            assert len(record_logs) > 0
            assert all(log.record_id == record_id for log in record_logs)

    def test_acc_449_enforcement_returns_statistics(self, engine):
        """ACC-449: Enforcement returns detailed statistics"""
        stats = engine.enforce_retention()

        assert "total_records" in stats
        assert "archived" in stats
        assert "deleted" in stats
        assert "retained" in stats
        assert "legal_holds" in stats

        # Verify statistics are accurate
        assert stats["total_records"] > 0
        assert isinstance(stats["archived"], int)
        assert isinstance(stats["deleted"], int)
        assert isinstance(stats["retained"], int)
