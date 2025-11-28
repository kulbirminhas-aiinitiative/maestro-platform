"""
ACC Security Tests: PII (Personally Identifiable Information) Handling
Test IDs: ACC-420 to ACC-434

Tests for PII detection, masking, and compliance:
- PII field detection (email, SSN, phone, credit card, etc.)
- Data masking strategies
- Logging with PII redaction
- GDPR compliance (right to be forgotten)
- PII encryption
- Audit trail for PII access

These tests ensure:
1. PII is properly identified
2. Sensitive data is masked in logs
3. GDPR/CCPA compliance requirements met
4. PII access is audited
"""

import pytest
import re
from typing import Dict, List, Set, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class PIIType(Enum):
    """Types of PII"""
    EMAIL = "email"
    PHONE = "phone"
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    IP_ADDRESS = "ip_address"
    PASSPORT = "passport"
    DRIVER_LICENSE = "driver_license"
    ADDRESS = "address"
    DATE_OF_BIRTH = "date_of_birth"


@dataclass
class PIIField:
    """Detected PII field"""
    field_name: str
    pii_type: PIIType
    value: str
    masked_value: str


class PIIDetector:
    """Detects PII in data structures"""

    # Regex patterns for PII detection
    PATTERNS = {
        PIIType.EMAIL: r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        PIIType.PHONE: r'\b(\+?1[-.]?)?\(?([0-9]{3})\)?[-.]?([0-9]{3})[-.]?([0-9]{4})\b',
        PIIType.SSN: r'\b\d{3}-\d{2}-\d{4}\b',
        PIIType.CREDIT_CARD: r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
        PIIType.IP_ADDRESS: r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
    }

    # Field name patterns that likely contain PII
    FIELD_PATTERNS = {
        PIIType.EMAIL: ['email', 'e_mail', 'email_address'],
        PIIType.PHONE: ['phone', 'telephone', 'mobile', 'cell'],
        PIIType.SSN: ['ssn', 'social_security', 'tax_id'],
        PIIType.CREDIT_CARD: ['credit_card', 'card_number', 'cc_number'],
        PIIType.ADDRESS: ['address', 'street', 'home_address'],
        PIIType.DATE_OF_BIRTH: ['dob', 'date_of_birth', 'birth_date', 'birthdate'],
    }

    def detect_in_text(self, text: str) -> List[PIIField]:
        """Detect PII in free text"""
        detected = []

        for pii_type, pattern in self.PATTERNS.items():
            matches = re.finditer(pattern, text)
            for match in matches:
                value = match.group(0)
                masked = self._mask_value(value, pii_type)
                detected.append(PIIField(
                    field_name="text_content",
                    pii_type=pii_type,
                    value=value,
                    masked_value=masked
                ))

        return detected

    def detect_in_dict(self, data: Dict[str, Any]) -> List[PIIField]:
        """Detect PII in dictionary by field names and values"""
        detected = []

        for field_name, value in data.items():
            if not isinstance(value, str):
                continue

            # Check field name patterns
            for pii_type, patterns in self.FIELD_PATTERNS.items():
                if any(pattern in field_name.lower() for pattern in patterns):
                    masked = self._mask_value(value, pii_type)
                    detected.append(PIIField(
                        field_name=field_name,
                        pii_type=pii_type,
                        value=value,
                        masked_value=masked
                    ))
                    break  # Found PII type for this field
            else:
                # Check value patterns
                for pii_type, pattern in self.PATTERNS.items():
                    if re.search(pattern, value):
                        masked = self._mask_value(value, pii_type)
                        detected.append(PIIField(
                            field_name=field_name,
                            pii_type=pii_type,
                            value=value,
                            masked_value=masked
                        ))
                        break

        return detected

    def _mask_value(self, value: str, pii_type: PIIType) -> str:
        """Mask PII value based on type"""
        if pii_type == PIIType.EMAIL:
            # mask middle of email: alice@example.com -> a***e@example.com
            parts = value.split('@')
            if len(parts) == 2:
                username = parts[0]
                if len(username) > 2:
                    masked_username = username[0] + '***' + username[-1]
                else:
                    masked_username = '***'
                return f"{masked_username}@{parts[1]}"

        elif pii_type == PIIType.PHONE:
            # Mask middle digits: (555) 123-4567 -> (555) ***-4567
            cleaned = re.sub(r'[^\d]', '', value)
            if len(cleaned) >= 10:
                return f"({cleaned[:3]}) ***-{cleaned[-4:]}"

        elif pii_type == PIIType.SSN:
            # Mask first 5 digits: 123-45-6789 -> ***-**-6789
            return f"***-**-{value[-4:]}"

        elif pii_type == PIIType.CREDIT_CARD:
            # Mask all but last 4: 1234 5678 9012 3456 -> **** **** **** 3456
            cleaned = re.sub(r'[^\d]', '', value)
            return f"**** **** **** {cleaned[-4:]}"

        elif pii_type == PIIType.IP_ADDRESS:
            # Mask last octet: 192.168.1.100 -> 192.168.1.***
            parts = value.split('.')
            if len(parts) == 4:
                return f"{parts[0]}.{parts[1]}.{parts[2]}.***"

        # Default masking
        return "***" + value[-3:] if len(value) > 3 else "***"


class PIIMasker:
    """Masks PII in data structures"""

    def __init__(self):
        self.detector = PIIDetector()

    def mask_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Return copy of dict with PII masked"""
        masked_data = data.copy()
        detected_pii = self.detector.detect_in_dict(data)

        for pii_field in detected_pii:
            masked_data[pii_field.field_name] = pii_field.masked_value

        return masked_data

    def mask_text(self, text: str) -> str:
        """Return text with PII masked"""
        masked_text = text
        detected_pii = self.detector.detect_in_text(text)

        # Replace in reverse order to maintain offsets
        for pii_field in reversed(detected_pii):
            masked_text = masked_text.replace(pii_field.value, pii_field.masked_value)

        return masked_text


@dataclass
class PIIAccessLog:
    """Log entry for PII access"""
    user_id: str
    resource_id: str
    pii_fields: List[str]
    accessed_at: datetime = field(default_factory=datetime.now)
    purpose: Optional[str] = None


class PIIAccessAuditor:
    """Audits PII access for compliance"""

    def __init__(self):
        self._access_logs: List[PIIAccessLog] = []

    def log_access(self, user_id: str, resource_id: str, pii_fields: List[str], purpose: Optional[str] = None):
        """Log PII access"""
        log_entry = PIIAccessLog(
            user_id=user_id,
            resource_id=resource_id,
            pii_fields=pii_fields,
            purpose=purpose
        )
        self._access_logs.append(log_entry)

    def get_access_logs(self, user_id: Optional[str] = None) -> List[PIIAccessLog]:
        """Get access logs, optionally filtered by user"""
        if user_id:
            return [log for log in self._access_logs if log.user_id == user_id]
        return self._access_logs.copy()

    def get_user_data_access(self, resource_id: str) -> List[PIIAccessLog]:
        """Get all access logs for a specific user's data"""
        return [log for log in self._access_logs if log.resource_id == resource_id]


class GDPRCompliance:
    """GDPR compliance operations"""

    def __init__(self):
        self._deleted_users: Set[str] = set()
        self._user_data: Dict[str, Dict[str, Any]] = {}

    def store_user_data(self, user_id: str, data: Dict[str, Any]):
        """Store user data"""
        self._user_data[user_id] = data

    def right_to_be_forgotten(self, user_id: str) -> bool:
        """
        Exercise GDPR right to be forgotten.
        Delete all user data permanently.
        """
        if user_id in self._user_data:
            del self._user_data[user_id]

        self._deleted_users.add(user_id)
        return True

    def is_user_deleted(self, user_id: str) -> bool:
        """Check if user has been deleted"""
        return user_id in self._deleted_users

    def export_user_data(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Exercise GDPR right to data portability.
        Export all user data.
        """
        return self._user_data.get(user_id)


@pytest.mark.acc
@pytest.mark.security
class TestPIIDetection:
    """Test suite for PII detection"""

    @pytest.fixture
    def detector(self):
        return PIIDetector()

    def test_acc_420_detect_email_in_text(self, detector):
        """ACC-420: Detects email addresses in text"""
        text = "Contact me at alice@example.com for details"

        detected = detector.detect_in_text(text)

        assert len(detected) == 1
        assert detected[0].pii_type == PIIType.EMAIL
        assert detected[0].value == "alice@example.com"

    def test_acc_421_detect_phone_in_text(self, detector):
        """ACC-421: Detects phone numbers in text"""
        text = "Call me at 555-123-4567"

        detected = detector.detect_in_text(text)

        assert len(detected) == 1
        assert detected[0].pii_type == PIIType.PHONE

    def test_acc_422_detect_ssn_in_text(self, detector):
        """ACC-422: Detects SSN in text"""
        text = "SSN: 123-45-6789"

        detected = detector.detect_in_text(text)

        assert len(detected) == 1
        assert detected[0].pii_type == PIIType.SSN
        assert detected[0].value == "123-45-6789"

    def test_acc_423_detect_credit_card_in_text(self, detector):
        """ACC-423: Detects credit card numbers in text"""
        text = "Card: 1234 5678 9012 3456"

        detected = detector.detect_in_text(text)

        assert len(detected) == 1
        assert detected[0].pii_type == PIIType.CREDIT_CARD

    def test_acc_424_detect_pii_in_dict_by_field_name(self, detector):
        """ACC-424: Detects PII by field name"""
        data = {
            "user_id": "user-123",
            "email": "alice@example.com",
            "phone": "555-123-4567"
        }

        detected = detector.detect_in_dict(data)

        assert len(detected) >= 2
        pii_types = {d.pii_type for d in detected}
        assert PIIType.EMAIL in pii_types
        assert PIIType.PHONE in pii_types

    def test_acc_425_detect_multiple_pii_types(self, detector):
        """ACC-425: Detects multiple PII types in same text"""
        text = "Email: alice@example.com, Phone: 555-123-4567, SSN: 123-45-6789"

        detected = detector.detect_in_text(text)

        assert len(detected) == 3
        pii_types = {d.pii_type for d in detected}
        assert PIIType.EMAIL in pii_types
        assert PIIType.PHONE in pii_types
        assert PIIType.SSN in pii_types


@pytest.mark.acc
@pytest.mark.security
class TestPIIMasking:
    """Test suite for PII masking"""

    @pytest.fixture
    def masker(self):
        return PIIMasker()

    def test_acc_426_mask_email_address(self, masker):
        """ACC-426: Email addresses are properly masked"""
        data = {"email": "alice@example.com"}

        masked = masker.mask_dict(data)

        assert masked["email"] == "a***e@example.com"

    def test_acc_427_mask_phone_number(self, masker):
        """ACC-427: Phone numbers are properly masked"""
        data = {"phone": "555-123-4567"}

        masked = masker.mask_dict(data)

        assert "***" in masked["phone"]
        assert "4567" in masked["phone"]  # Last 4 digits visible

    def test_acc_428_mask_ssn(self, masker):
        """ACC-428: SSN is properly masked"""
        data = {"ssn": "123-45-6789"}

        masked = masker.mask_dict(data)

        assert masked["ssn"] == "***-**-6789"

    def test_acc_429_mask_credit_card(self, masker):
        """ACC-429: Credit card numbers are properly masked"""
        data = {"credit_card": "1234 5678 9012 3456"}

        masked = masker.mask_dict(data)

        assert "****" in masked["credit_card"]
        assert "3456" in masked["credit_card"]

    def test_acc_430_non_pii_fields_unchanged(self, masker):
        """ACC-430: Non-PII fields remain unchanged"""
        data = {
            "user_id": "user-123",
            "username": "alice",
            "email": "alice@example.com"
        }

        masked = masker.mask_dict(data)

        assert masked["user_id"] == "user-123"  # Unchanged
        assert masked["username"] == "alice"  # Unchanged
        assert masked["email"] != "alice@example.com"  # Masked

    def test_acc_431_mask_pii_in_log_message(self, masker):
        """ACC-431: PII is masked in log messages"""
        log_message = "User alice@example.com logged in from 192.168.1.100"

        masked = masker.mask_text(log_message)

        assert "alice@example.com" not in masked
        assert "192.168.1.100" not in masked
        assert "***" in masked


@pytest.mark.acc
@pytest.mark.security
class TestPIIAuditing:
    """Test suite for PII access auditing"""

    @pytest.fixture
    def auditor(self):
        return PIIAccessAuditor()

    def test_acc_432_log_pii_access(self, auditor):
        """ACC-432: PII access is logged"""
        auditor.log_access(
            user_id="admin-1",
            resource_id="user-data-123",
            pii_fields=["email", "phone"],
            purpose="customer_support"
        )

        logs = auditor.get_access_logs()

        assert len(logs) == 1
        assert logs[0].user_id == "admin-1"
        assert logs[0].resource_id == "user-data-123"
        assert "email" in logs[0].pii_fields

    def test_acc_433_get_access_logs_by_user(self, auditor):
        """ACC-433: Can retrieve access logs by user"""
        auditor.log_access("user-1", "resource-1", ["email"])
        auditor.log_access("user-2", "resource-2", ["phone"])
        auditor.log_access("user-1", "resource-3", ["ssn"])

        user1_logs = auditor.get_access_logs(user_id="user-1")

        assert len(user1_logs) == 2
        assert all(log.user_id == "user-1" for log in user1_logs)


@pytest.mark.acc
@pytest.mark.security
class TestGDPRCompliance:
    """Test suite for GDPR compliance"""

    @pytest.fixture
    def gdpr(self):
        return GDPRCompliance()

    def test_acc_434_right_to_be_forgotten(self, gdpr):
        """ACC-434: GDPR right to be forgotten deletes user data"""
        user_id = "user-123"
        user_data = {
            "email": "user@example.com",
            "name": "John Doe"
        }

        # Store data
        gdpr.store_user_data(user_id, user_data)
        assert gdpr.export_user_data(user_id) is not None

        # Exercise right to be forgotten
        gdpr.right_to_be_forgotten(user_id)

        # Data should be deleted
        assert gdpr.export_user_data(user_id) is None
        assert gdpr.is_user_deleted(user_id) is True
