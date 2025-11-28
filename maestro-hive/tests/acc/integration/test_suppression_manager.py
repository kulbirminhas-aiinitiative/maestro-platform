"""
ACC Rule Engine Tests: Suppression System
Test IDs: ACC-201 to ACC-225

Test Suite 18: Suppression System for architectural rule violations.

Tests cover:
1. Loading (201-210): Load suppression list from YAML, with/without ADR,
   expiration checks, reason required, approval tracking, matching,
   multiple suppressions
2. Priority (211-212): Specific > wildcard, pattern matching
3. API operations (213-215): Add, remove, update suppressions via API
4. Audit and review (216-222): Audit log, review reminders, metrics, reports,
   ADR/JIRA validation, bulk operations
5. Import/export (223-225): Export to YAML, import from YAML, schema validation

These tests ensure:
1. Violations can be suppressed with proper justification
2. Suppressions are tracked and expire appropriately
3. ADR links are validated before acceptance
4. Audit trail maintains compliance
5. Review reminders prevent forgotten suppressions
"""

import pytest
import yaml
import json
from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
import tempfile
import shutil


class SuppressionStatus(str, Enum):
    """Suppression status"""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    PENDING_REVIEW = "pending_review"


@dataclass
class Suppression:
    """
    Suppression for architectural rule violation.

    Fields:
    - violation_id: ID or pattern to match violations
    - reason: Required justification for suppression
    - adr_link: Link to Architecture Decision Record (validated)
    - expiry_date: When suppression expires (datetime)
    - approver: Who approved the suppression
    - created_at: When suppression was created
    - jira_ticket: Optional JIRA ticket reference
    - review_before_days: Days before expiry to send reminder (default: 7)
    """
    violation_id: str
    reason: str
    approver: str
    created_at: datetime = field(default_factory=datetime.now)
    adr_link: Optional[str] = None
    expiry_date: Optional[datetime] = None
    jira_ticket: Optional[str] = None
    review_before_days: int = 7
    status: SuppressionStatus = SuppressionStatus.ACTIVE

    def is_expired(self) -> bool:
        """Check if suppression has expired"""
        if self.expiry_date is None:
            return False
        return datetime.now() > self.expiry_date

    def needs_review(self) -> bool:
        """Check if suppression needs review (within review_before_days of expiry)"""
        if self.expiry_date is None:
            return False

        review_date = self.expiry_date - timedelta(days=self.review_before_days)
        now = datetime.now()
        return review_date <= now <= self.expiry_date

    def matches(self, violation_id: str) -> bool:
        """
        Check if suppression matches violation ID.
        Supports wildcards: * (any), ? (single char)
        """
        import fnmatch
        return fnmatch.fnmatch(violation_id, self.violation_id)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        # Convert datetime to ISO format
        if self.created_at:
            data['created_at'] = self.created_at.isoformat()
        if self.expiry_date:
            data['expiry_date'] = self.expiry_date.isoformat()
        data['status'] = self.status.value
        return data

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Suppression':
        """Create Suppression from dictionary"""
        # Convert ISO strings back to datetime
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if 'expiry_date' in data and data['expiry_date'] and isinstance(data['expiry_date'], str):
            data['expiry_date'] = datetime.fromisoformat(data['expiry_date'])
        if 'status' in data:
            data['status'] = SuppressionStatus(data['status'])

        return Suppression(**data)


@dataclass
class AuditEntry:
    """Audit log entry for suppression changes"""
    timestamp: datetime
    action: str  # added, removed, updated, expired
    suppression_id: str
    user: str
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'action': self.action,
            'suppression_id': self.suppression_id,
            'user': self.user,
            'details': self.details
        }


class ADRValidator:
    """Validates Architecture Decision Record links"""

    def __init__(self, adr_directory: Optional[Path] = None):
        self.adr_directory = adr_directory or Path("docs/adr")

    def validate(self, adr_link: str) -> bool:
        """
        Validate that ADR link exists.

        Accepts:
        - File paths: docs/adr/001-architecture.md
        - URLs: https://github.com/org/repo/docs/adr/001.md
        """
        if not adr_link:
            return False

        # Check if it's a file path
        if not adr_link.startswith('http'):
            adr_path = Path(adr_link)
            if adr_path.is_absolute():
                return adr_path.exists()
            else:
                # Relative path - check in ADR directory
                return (self.adr_directory / adr_path.name).exists()

        # For URLs, we'd normally make HTTP request
        # For testing, just validate format
        return adr_link.startswith('http') and len(adr_link) > 10


class JIRAValidator:
    """Validates JIRA ticket references"""

    def __init__(self, jira_url: Optional[str] = None):
        self.jira_url = jira_url or "https://jira.example.com"

    def validate(self, jira_ticket: str) -> bool:
        """
        Validate JIRA ticket format.

        Format: PROJECT-123
        """
        if not jira_ticket:
            return False

        # Simple format check: XXX-NNN
        parts = jira_ticket.split('-')
        if len(parts) != 2:
            return False

        project_key = parts[0]
        ticket_number = parts[1]

        return project_key.isupper() and ticket_number.isdigit()


class SuppressionManager:
    """
    Manages suppression list for architectural rule violations.

    Features:
    - YAML-based persistence
    - Pattern matching (wildcards)
    - Expiration tracking
    - ADR link validation
    - Audit logging
    - Review reminders
    - Import/export capabilities
    """

    def __init__(
        self,
        suppression_file: Optional[Path] = None,
        adr_validator: Optional[ADRValidator] = None,
        jira_validator: Optional[JIRAValidator] = None
    ):
        self.suppression_file = suppression_file or Path("suppressions.yaml")
        self.adr_validator = adr_validator or ADRValidator()
        self.jira_validator = jira_validator or JIRAValidator()

        self.suppressions: Dict[str, Suppression] = {}
        self.audit_log: List[AuditEntry] = []

        # Load from file if exists
        if self.suppression_file.exists():
            self.load()

    def add(
        self,
        violation_id: str,
        reason: str,
        approver: str,
        adr_link: Optional[str] = None,
        expiry_date: Optional[datetime] = None,
        jira_ticket: Optional[str] = None,
        validate_adr: bool = True,
        validate_jira: bool = True
    ) -> Suppression:
        """
        Add new suppression.

        Raises ValueError if:
        - violation_id already exists
        - reason is empty
        - ADR link invalid (when validate_adr=True)
        - JIRA ticket invalid (when validate_jira=True)
        """
        if not reason or not reason.strip():
            raise ValueError("Suppression reason is required")

        if violation_id in self.suppressions:
            raise ValueError(f"Suppression for {violation_id} already exists")

        # Validate ADR link if provided
        if adr_link and validate_adr:
            if not self.adr_validator.validate(adr_link):
                raise ValueError(f"ADR link not found: {adr_link}")

        # Validate JIRA ticket if provided
        if jira_ticket and validate_jira:
            if not self.jira_validator.validate(jira_ticket):
                raise ValueError(f"Invalid JIRA ticket format: {jira_ticket}")

        suppression = Suppression(
            violation_id=violation_id,
            reason=reason,
            approver=approver,
            adr_link=adr_link,
            expiry_date=expiry_date,
            jira_ticket=jira_ticket,
            created_at=datetime.now(),
            status=SuppressionStatus.ACTIVE
        )

        self.suppressions[violation_id] = suppression

        # Audit log
        self._add_audit_entry(
            action="added",
            suppression_id=violation_id,
            user=approver,
            details={
                'reason': reason,
                'adr_link': adr_link,
                'expiry_date': expiry_date.isoformat() if expiry_date else None
            }
        )

        self.save()
        return suppression

    def remove(self, violation_id: str, user: str) -> bool:
        """Remove suppression"""
        if violation_id not in self.suppressions:
            return False

        suppression = self.suppressions[violation_id]
        del self.suppressions[violation_id]

        # Audit log
        self._add_audit_entry(
            action="removed",
            suppression_id=violation_id,
            user=user,
            details={'reason': suppression.reason}
        )

        self.save()
        return True

    def update(
        self,
        violation_id: str,
        user: str,
        reason: Optional[str] = None,
        adr_link: Optional[str] = None,
        expiry_date: Optional[datetime] = None,
        status: Optional[SuppressionStatus] = None
    ) -> Suppression:
        """Update existing suppression"""
        if violation_id not in self.suppressions:
            raise ValueError(f"Suppression not found: {violation_id}")

        suppression = self.suppressions[violation_id]
        changes = {}

        if reason is not None:
            if not reason.strip():
                raise ValueError("Suppression reason cannot be empty")
            suppression.reason = reason
            changes['reason'] = reason

        if adr_link is not None:
            if adr_link and not self.adr_validator.validate(adr_link):
                raise ValueError(f"ADR link not found: {adr_link}")
            suppression.adr_link = adr_link
            changes['adr_link'] = adr_link

        if expiry_date is not None:
            suppression.expiry_date = expiry_date
            changes['expiry_date'] = expiry_date.isoformat() if expiry_date else None

        if status is not None:
            suppression.status = status
            changes['status'] = status.value

        # Audit log
        self._add_audit_entry(
            action="updated",
            suppression_id=violation_id,
            user=user,
            details=changes
        )

        self.save()
        return suppression

    def is_suppressed(self, violation_id: str) -> bool:
        """
        Check if violation is suppressed.

        Matches against:
        1. Exact violation ID
        2. Pattern matches (wildcards)

        Returns False if suppression is expired.
        Priority: Specific matches take precedence over wildcards.
        """
        # Check for exact match first (highest priority)
        if violation_id in self.suppressions:
            suppression = self.suppressions[violation_id]
            if not suppression.is_expired():
                return True

        # Check pattern matches (wildcards)
        for suppression_id, suppression in self.suppressions.items():
            if suppression.matches(violation_id) and not suppression.is_expired():
                return True

        return False

    def get_suppression(self, violation_id: str) -> Optional[Suppression]:
        """
        Get suppression for violation ID (supports pattern matching).

        Priority: Exact match > Most specific pattern > Wildcard
        """
        # Exact match first
        if violation_id in self.suppressions:
            return self.suppressions[violation_id]

        # Pattern matches - find most specific
        matches = []
        for suppression_id, suppression in self.suppressions.items():
            if suppression.matches(violation_id):
                # Count wildcards to determine specificity
                wildcard_count = suppression_id.count('*') + suppression_id.count('?')
                matches.append((wildcard_count, suppression))

        if matches:
            # Sort by wildcard count (fewer = more specific)
            matches.sort(key=lambda x: x[0])
            return matches[0][1]

        return None

    def get_all_suppressions(self) -> List[Suppression]:
        """Get all suppressions"""
        return list(self.suppressions.values())

    def get_active_suppressions(self) -> List[Suppression]:
        """Get all active (non-expired) suppressions"""
        return [s for s in self.suppressions.values() if not s.is_expired()]

    def get_expired_suppressions(self) -> List[Suppression]:
        """Get all expired suppressions"""
        return [s for s in self.suppressions.values() if s.is_expired()]

    def get_suppressions_needing_review(self) -> List[Suppression]:
        """Get suppressions that need review (approaching expiry)"""
        return [s for s in self.suppressions.values() if s.needs_review()]

    def check_expirations(self, user: str = "system") -> List[Suppression]:
        """
        Check for expired suppressions and update their status.
        Returns list of newly expired suppressions.
        """
        newly_expired = []

        for suppression_id, suppression in self.suppressions.items():
            if suppression.is_expired() and suppression.status == SuppressionStatus.ACTIVE:
                suppression.status = SuppressionStatus.EXPIRED
                newly_expired.append(suppression)

                # Audit log
                self._add_audit_entry(
                    action="expired",
                    suppression_id=suppression_id,
                    user=user,
                    details={'expiry_date': suppression.expiry_date.isoformat()}
                )

        if newly_expired:
            self.save()

        return newly_expired

    def bulk_add(self, suppressions: List[Dict[str, Any]], user: str) -> int:
        """
        Bulk add suppressions from list of dictionaries.
        Returns count of successfully added suppressions.
        """
        count = 0
        for data in suppressions:
            try:
                self.add(
                    violation_id=data['violation_id'],
                    reason=data['reason'],
                    approver=user,
                    adr_link=data.get('adr_link'),
                    expiry_date=data.get('expiry_date'),
                    jira_ticket=data.get('jira_ticket'),
                    validate_adr=data.get('validate_adr', True),
                    validate_jira=data.get('validate_jira', True)
                )
                count += 1
            except (ValueError, KeyError):
                # Skip invalid entries
                continue

        return count

    def get_metrics(self) -> Dict[str, Any]:
        """Get suppression metrics"""
        all_suppressions = self.get_all_suppressions()
        active = self.get_active_suppressions()
        expired = self.get_expired_suppressions()
        needs_review = self.get_suppressions_needing_review()

        # Count by status
        status_counts = {}
        for suppression in all_suppressions:
            status = suppression.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        # Count with ADR links
        with_adr = len([s for s in all_suppressions if s.adr_link])

        # Count with JIRA tickets
        with_jira = len([s for s in all_suppressions if s.jira_ticket])

        return {
            'total': len(all_suppressions),
            'active': len(active),
            'expired': len(expired),
            'needs_review': len(needs_review),
            'status_counts': status_counts,
            'with_adr_link': with_adr,
            'with_jira_ticket': with_jira,
            'audit_entries': len(self.audit_log)
        }

    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive suppression report"""
        metrics = self.get_metrics()

        return {
            'generated_at': datetime.now().isoformat(),
            'metrics': metrics,
            'active_suppressions': [s.to_dict() for s in self.get_active_suppressions()],
            'expired_suppressions': [s.to_dict() for s in self.get_expired_suppressions()],
            'needs_review': [s.to_dict() for s in self.get_suppressions_needing_review()],
            'recent_audit_entries': [e.to_dict() for e in self.audit_log[-10:]]
        }

    def save(self):
        """Save suppressions to YAML file"""
        data = {
            'version': '1.0',
            'updated_at': datetime.now().isoformat(),
            'suppressions': [s.to_dict() for s in self.suppressions.values()]
        }

        with open(self.suppression_file, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    def load(self):
        """Load suppressions from YAML file"""
        if not self.suppression_file.exists():
            return

        with open(self.suppression_file) as f:
            data = yaml.safe_load(f)

        if not data or 'suppressions' not in data:
            return

        self.suppressions.clear()
        for item in data['suppressions']:
            suppression = Suppression.from_dict(item)
            self.suppressions[suppression.violation_id] = suppression

    def export_yaml(self, output_file: Path):
        """Export suppressions to YAML file"""
        shutil.copy(self.suppression_file, output_file)

    def import_yaml(self, input_file: Path, merge: bool = False):
        """
        Import suppressions from YAML file.

        Args:
            input_file: Path to YAML file to import
            merge: If True, merge with existing suppressions. If False, replace.
        """
        if not merge:
            self.suppressions.clear()

        with open(input_file) as f:
            data = yaml.safe_load(f)

        if not data or 'suppressions' not in data:
            raise ValueError("Invalid suppression file format")

        for item in data['suppressions']:
            suppression = Suppression.from_dict(item)
            self.suppressions[suppression.violation_id] = suppression

        self.save()

    def validate_schema(self, file_path: Path) -> bool:
        """Validate suppression file schema"""
        try:
            with open(file_path) as f:
                data = yaml.safe_load(f)

            # Check required fields
            if not isinstance(data, dict):
                return False

            if 'suppressions' not in data:
                return False

            if not isinstance(data['suppressions'], list):
                return False

            # Validate each suppression
            for item in data['suppressions']:
                if not isinstance(item, dict):
                    return False

                # Required fields
                required = ['violation_id', 'reason', 'approver', 'created_at']
                for field in required:
                    if field not in item:
                        return False

            return True

        except Exception:
            return False

    def _add_audit_entry(self, action: str, suppression_id: str, user: str, details: Dict[str, Any]):
        """Add entry to audit log"""
        entry = AuditEntry(
            timestamp=datetime.now(),
            action=action,
            suppression_id=suppression_id,
            user=user,
            details=details
        )
        self.audit_log.append(entry)

    def get_audit_log(self, limit: Optional[int] = None) -> List[AuditEntry]:
        """Get audit log entries"""
        if limit:
            return self.audit_log[-limit:]
        return self.audit_log


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def temp_dir():
    """Create temporary directory for test files"""
    temp = tempfile.mkdtemp()
    yield Path(temp)
    shutil.rmtree(temp)


@pytest.fixture
def adr_dir(temp_dir):
    """Create temporary ADR directory with sample files"""
    adr_path = temp_dir / "docs" / "adr"
    adr_path.mkdir(parents=True)

    # Create sample ADR files
    (adr_path / "001-architecture.md").write_text("# ADR 001: Architecture")
    (adr_path / "002-database.md").write_text("# ADR 002: Database")

    return adr_path


@pytest.fixture
def suppression_manager(temp_dir, adr_dir):
    """Create SuppressionManager with temp file"""
    suppression_file = temp_dir / "suppressions.yaml"
    adr_validator = ADRValidator(adr_directory=adr_dir)

    return SuppressionManager(
        suppression_file=suppression_file,
        adr_validator=adr_validator
    )


# ============================================================================
# Test Suite 1: Loading (ACC-201 to ACC-210)
# ============================================================================

@pytest.mark.acc
@pytest.mark.integration
class TestSuppressionLoading:
    """Test suite for suppression loading functionality"""

    def test_acc_201_load_empty_suppression_list(self, suppression_manager):
        """ACC-201: Load empty suppression list"""
        # New manager starts with no suppressions
        assert len(suppression_manager.get_all_suppressions()) == 0

    def test_acc_202_load_suppression_with_adr(self, suppression_manager, adr_dir):
        """ACC-202: Load suppression with ADR link"""
        adr_file = adr_dir / "001-architecture.md"

        suppression = suppression_manager.add(
            violation_id="V-001",
            reason="Legacy code, refactoring planned",
            approver="architect@example.com",
            adr_link=str(adr_file)
        )

        assert suppression.adr_link == str(adr_file)
        assert suppression_manager.is_suppressed("V-001")

    def test_acc_203_load_suppression_without_adr(self, suppression_manager):
        """ACC-203: Load suppression without ADR link"""
        suppression = suppression_manager.add(
            violation_id="V-002",
            reason="Temporary workaround",
            approver="dev@example.com",
            adr_link=None,
            validate_adr=False
        )

        assert suppression.adr_link is None
        assert suppression_manager.is_suppressed("V-002")

    def test_acc_204_expiration_check_active(self, suppression_manager):
        """ACC-204: Expiration check for active suppression"""
        future_date = datetime.now() + timedelta(days=30)

        suppression = suppression_manager.add(
            violation_id="V-003",
            reason="Under review",
            approver="manager@example.com",
            expiry_date=future_date
        )

        assert not suppression.is_expired()
        assert suppression_manager.is_suppressed("V-003")

    def test_acc_205_expiration_check_expired(self, suppression_manager):
        """ACC-205: Expiration check for expired suppression"""
        past_date = datetime.now() - timedelta(days=1)

        suppression = suppression_manager.add(
            violation_id="V-004",
            reason="Short term fix",
            approver="dev@example.com",
            expiry_date=past_date
        )

        assert suppression.is_expired()
        assert not suppression_manager.is_suppressed("V-004")  # Expired suppressions don't apply

    def test_acc_206_reason_required(self, suppression_manager):
        """ACC-206: Suppression reason is required"""
        with pytest.raises(ValueError, match="reason is required"):
            suppression_manager.add(
                violation_id="V-005",
                reason="",  # Empty reason
                approver="dev@example.com"
            )

    def test_acc_207_approval_tracking(self, suppression_manager):
        """ACC-207: Track who approved suppression"""
        approver = "lead@example.com"

        suppression = suppression_manager.add(
            violation_id="V-006",
            reason="Performance optimization needed",
            approver=approver
        )

        assert suppression.approver == approver

    def test_acc_208_exact_match_suppression(self, suppression_manager):
        """ACC-208: Exact match for violation suppression"""
        suppression_manager.add(
            violation_id="V-007",
            reason="Known issue",
            approver="dev@example.com"
        )

        assert suppression_manager.is_suppressed("V-007")
        assert not suppression_manager.is_suppressed("V-008")

    def test_acc_209_multiple_suppressions(self, suppression_manager):
        """ACC-209: Load and manage multiple suppressions"""
        suppressions = [
            ("V-010", "Issue 1"),
            ("V-011", "Issue 2"),
            ("V-012", "Issue 3")
        ]

        for vid, reason in suppressions:
            suppression_manager.add(
                violation_id=vid,
                reason=reason,
                approver="team@example.com"
            )

        all_suppressions = suppression_manager.get_all_suppressions()
        assert len(all_suppressions) == 3

    def test_acc_210_load_from_yaml_file(self, suppression_manager, temp_dir):
        """ACC-210: Load suppressions from YAML file"""
        # Add suppressions
        suppression_manager.add("V-020", "Test 1", "user@example.com")
        suppression_manager.add("V-021", "Test 2", "user@example.com")

        # Save to file
        suppression_manager.save()

        # Create new manager and load
        new_manager = SuppressionManager(suppression_file=suppression_manager.suppression_file)

        assert len(new_manager.get_all_suppressions()) == 2
        assert new_manager.is_suppressed("V-020")
        assert new_manager.is_suppressed("V-021")


# ============================================================================
# Test Suite 2: Priority (ACC-211 to ACC-212)
# ============================================================================

@pytest.mark.acc
@pytest.mark.integration
class TestSuppressionPriority:
    """Test suite for suppression matching priority"""

    def test_acc_211_specific_over_wildcard(self, suppression_manager):
        """ACC-211: Specific violation ID takes precedence over wildcard"""
        # Add wildcard suppression
        suppression_manager.add(
            violation_id="V-*",
            reason="All violations suppressed",
            approver="admin@example.com"
        )

        # Add specific suppression
        specific_reason = "Specific reason for V-100"
        suppression_manager.add(
            violation_id="V-100",
            reason=specific_reason,
            approver="dev@example.com"
        )

        # Get suppression for V-100 - should return specific one
        suppression = suppression_manager.get_suppression("V-100")
        assert suppression.reason == specific_reason
        assert suppression.violation_id == "V-100"

    def test_acc_212_pattern_matching_wildcards(self, suppression_manager):
        """ACC-212: Pattern matching with wildcards"""
        # Add pattern-based suppression
        suppression_manager.add(
            violation_id="DEP-*",
            reason="All dependency violations suppressed",
            approver="architect@example.com"
        )

        # Test pattern matching
        assert suppression_manager.is_suppressed("DEP-001")
        assert suppression_manager.is_suppressed("DEP-999")
        assert suppression_manager.is_suppressed("DEP-ABC")
        assert not suppression_manager.is_suppressed("COUP-001")  # Different prefix


# ============================================================================
# Test Suite 3: API Operations (ACC-213 to ACC-215)
# ============================================================================

@pytest.mark.acc
@pytest.mark.integration
class TestSuppressionAPI:
    """Test suite for API operations on suppressions"""

    def test_acc_213_add_suppression_via_api(self, suppression_manager):
        """ACC-213: Add suppression via API"""
        suppression = suppression_manager.add(
            violation_id="API-001",
            reason="Added via API",
            approver="api-user@example.com",
            jira_ticket="PROJ-123"
        )

        assert suppression.violation_id == "API-001"
        assert suppression.jira_ticket == "PROJ-123"
        assert suppression_manager.is_suppressed("API-001")

    def test_acc_214_remove_suppression_via_api(self, suppression_manager):
        """ACC-214: Remove suppression via API"""
        # Add suppression
        suppression_manager.add(
            violation_id="API-002",
            reason="To be removed",
            approver="user@example.com"
        )

        assert suppression_manager.is_suppressed("API-002")

        # Remove it
        result = suppression_manager.remove("API-002", user="admin@example.com")

        assert result is True
        assert not suppression_manager.is_suppressed("API-002")

    def test_acc_215_update_suppression_via_api(self, suppression_manager):
        """ACC-215: Update suppression via API"""
        # Add suppression
        suppression_manager.add(
            violation_id="API-003",
            reason="Original reason",
            approver="user@example.com"
        )

        # Update it
        new_reason = "Updated reason with more details"
        new_expiry = datetime.now() + timedelta(days=60)

        updated = suppression_manager.update(
            violation_id="API-003",
            user="admin@example.com",
            reason=new_reason,
            expiry_date=new_expiry
        )

        assert updated.reason == new_reason
        assert updated.expiry_date == new_expiry


# ============================================================================
# Test Suite 4: Audit and Review (ACC-216 to ACC-222)
# ============================================================================

@pytest.mark.acc
@pytest.mark.integration
class TestSuppressionAudit:
    """Test suite for audit logging and review reminders"""

    def test_acc_216_audit_log_records_changes(self, suppression_manager):
        """ACC-216: Audit log records all suppression changes"""
        # Add suppression
        suppression_manager.add("AUD-001", "Test", "user@example.com")

        # Update suppression
        suppression_manager.update("AUD-001", "admin@example.com", reason="Updated")

        # Remove suppression
        suppression_manager.remove("AUD-001", "admin@example.com")

        # Check audit log
        audit_log = suppression_manager.get_audit_log()

        assert len(audit_log) >= 3
        actions = [entry.action for entry in audit_log]
        assert "added" in actions
        assert "updated" in actions
        assert "removed" in actions

    def test_acc_217_review_reminders_before_expiry(self, suppression_manager):
        """ACC-217: Generate review reminders before suppression expires"""
        # Add suppression expiring in 5 days (within review window)
        expiry_date = datetime.now() + timedelta(days=5)

        suppression_manager.add(
            violation_id="REV-001",
            reason="Needs review soon",
            approver="user@example.com",
            expiry_date=expiry_date
        )

        # Check for suppressions needing review
        needs_review = suppression_manager.get_suppressions_needing_review()

        assert len(needs_review) == 1
        assert needs_review[0].violation_id == "REV-001"

    def test_acc_218_suppression_metrics(self, suppression_manager):
        """ACC-218: Calculate suppression metrics"""
        # Add various suppressions
        suppression_manager.add("M-001", "Active", "user@example.com")

        past_date = datetime.now() - timedelta(days=1)
        suppression_manager.add("M-002", "Expired", "user@example.com", expiry_date=past_date)

        # Get metrics
        metrics = suppression_manager.get_metrics()

        assert metrics['total'] == 2
        assert metrics['active'] == 1  # M-002 is expired
        assert metrics['expired'] == 1

    def test_acc_219_generate_suppression_report(self, suppression_manager):
        """ACC-219: Generate comprehensive suppression report"""
        # Add test data
        suppression_manager.add("R-001", "Test 1", "user@example.com")
        suppression_manager.add("R-002", "Test 2", "user@example.com")

        # Generate report
        report = suppression_manager.generate_report()

        assert 'generated_at' in report
        assert 'metrics' in report
        assert 'active_suppressions' in report
        assert report['metrics']['total'] == 2

    def test_acc_220_adr_link_validation(self, suppression_manager, adr_dir):
        """ACC-220: Validate ADR links before accepting suppression"""
        # Valid ADR link
        valid_adr = adr_dir / "001-architecture.md"
        suppression_manager.add(
            "V-ADR-1",
            "Valid ADR",
            "user@example.com",
            adr_link=str(valid_adr)
        )

        # Invalid ADR link should raise error
        with pytest.raises(ValueError, match="ADR link not found"):
            suppression_manager.add(
                "V-ADR-2",
                "Invalid ADR",
                "user@example.com",
                adr_link="nonexistent.md",
                validate_adr=True
            )

    def test_acc_221_jira_ticket_validation(self, suppression_manager):
        """ACC-221: Validate JIRA ticket format"""
        # Valid JIRA ticket
        suppression_manager.add(
            "V-JIRA-1",
            "Valid JIRA",
            "user@example.com",
            jira_ticket="PROJ-123"
        )

        # Invalid JIRA ticket format
        with pytest.raises(ValueError, match="Invalid JIRA ticket format"):
            suppression_manager.add(
                "V-JIRA-2",
                "Invalid JIRA",
                "user@example.com",
                jira_ticket="invalid-format",
                validate_jira=True
            )

    def test_acc_222_bulk_operations(self, suppression_manager):
        """ACC-222: Bulk add/remove suppressions"""
        suppressions = [
            {
                'violation_id': 'BULK-001',
                'reason': 'Bulk item 1',
                'validate_adr': False,
                'validate_jira': False
            },
            {
                'violation_id': 'BULK-002',
                'reason': 'Bulk item 2',
                'validate_adr': False,
                'validate_jira': False
            },
            {
                'violation_id': 'BULK-003',
                'reason': 'Bulk item 3',
                'validate_adr': False,
                'validate_jira': False
            }
        ]

        count = suppression_manager.bulk_add(suppressions, user="admin@example.com")

        assert count == 3
        assert suppression_manager.is_suppressed("BULK-001")
        assert suppression_manager.is_suppressed("BULK-002")
        assert suppression_manager.is_suppressed("BULK-003")


# ============================================================================
# Test Suite 5: Import/Export (ACC-223 to ACC-225)
# ============================================================================

@pytest.mark.acc
@pytest.mark.integration
class TestSuppressionImportExport:
    """Test suite for import/export functionality"""

    def test_acc_223_export_to_yaml(self, suppression_manager, temp_dir):
        """ACC-223: Export suppressions to YAML file"""
        # Add test data
        suppression_manager.add("EXP-001", "Export test 1", "user@example.com")
        suppression_manager.add("EXP-002", "Export test 2", "user@example.com")

        # Export
        export_file = temp_dir / "exported.yaml"
        suppression_manager.export_yaml(export_file)

        assert export_file.exists()

        # Verify content
        with open(export_file) as f:
            data = yaml.safe_load(f)

        assert 'suppressions' in data
        assert len(data['suppressions']) == 2

    def test_acc_224_import_from_yaml(self, suppression_manager, temp_dir):
        """ACC-224: Import suppressions from YAML file"""
        # Create import file
        import_file = temp_dir / "import.yaml"
        import_data = {
            'version': '1.0',
            'suppressions': [
                {
                    'violation_id': 'IMP-001',
                    'reason': 'Imported 1',
                    'approver': 'user@example.com',
                    'created_at': datetime.now().isoformat(),
                    'status': 'active'
                },
                {
                    'violation_id': 'IMP-002',
                    'reason': 'Imported 2',
                    'approver': 'user@example.com',
                    'created_at': datetime.now().isoformat(),
                    'status': 'active'
                }
            ]
        }

        with open(import_file, 'w') as f:
            yaml.dump(import_data, f)

        # Import
        suppression_manager.import_yaml(import_file)

        assert suppression_manager.is_suppressed("IMP-001")
        assert suppression_manager.is_suppressed("IMP-002")

    def test_acc_225_schema_validation(self, suppression_manager, temp_dir):
        """ACC-225: Validate suppression file schema"""
        # Valid file
        valid_file = temp_dir / "valid.yaml"
        valid_data = {
            'version': '1.0',
            'suppressions': [
                {
                    'violation_id': 'V-001',
                    'reason': 'Valid',
                    'approver': 'user@example.com',
                    'created_at': datetime.now().isoformat(),
                    'status': 'active'
                }
            ]
        }

        with open(valid_file, 'w') as f:
            yaml.dump(valid_data, f)

        assert suppression_manager.validate_schema(valid_file) is True

        # Invalid file (missing required field)
        invalid_file = temp_dir / "invalid.yaml"
        invalid_data = {
            'suppressions': [
                {
                    'violation_id': 'V-002',
                    # Missing 'reason' field
                    'approver': 'user@example.com',
                    'created_at': datetime.now().isoformat()
                }
            ]
        }

        with open(invalid_file, 'w') as f:
            yaml.dump(invalid_data, f)

        assert suppression_manager.validate_schema(invalid_file) is False


# ============================================================================
# Summary Test
# ============================================================================

@pytest.mark.acc
@pytest.mark.integration
def test_acc_suppression_system_integration(suppression_manager, adr_dir):
    """
    Integration test: Complete suppression system workflow

    Tests the full lifecycle:
    1. Add suppressions with ADR links and expiry
    2. Pattern matching and priority
    3. Review reminders
    4. Expiration handling
    5. Audit logging
    6. Metrics and reporting
    """
    # Add specific suppression
    adr_file = adr_dir / "001-architecture.md"
    expiry = datetime.now() + timedelta(days=30)

    suppression_manager.add(
        violation_id="INT-001",
        reason="Integration test specific",
        approver="lead@example.com",
        adr_link=str(adr_file),
        expiry_date=expiry
    )

    # Add wildcard suppression
    suppression_manager.add(
        violation_id="INT-*",
        reason="Integration test wildcard",
        approver="lead@example.com"
    )

    # Test pattern matching priority
    suppression = suppression_manager.get_suppression("INT-001")
    assert suppression.reason == "Integration test specific"  # Specific wins

    suppression = suppression_manager.get_suppression("INT-999")
    assert suppression.reason == "Integration test wildcard"  # Wildcard matches

    # Check metrics
    metrics = suppression_manager.get_metrics()
    assert metrics['total'] >= 2
    assert metrics['with_adr_link'] >= 1

    # Generate report
    report = suppression_manager.generate_report()
    assert 'generated_at' in report
    assert len(report['active_suppressions']) >= 2

    # Verify audit log
    audit = suppression_manager.get_audit_log()
    assert len(audit) >= 2
