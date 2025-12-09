#!/usr/bin/env python3
"""Tests for Audit Logger module."""

import pytest
import tempfile
from pathlib import Path
import json

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from maestro_hive.compliance.audit_logger import (
    AuditLogger,
    AuditEvent,
    AuditEventType,
    AuditSeverity,
    PIIMasker,
    get_audit_logger
)


class TestPIIMasker:
    """Tests for PIIMasker class."""

    def test_mask_email(self):
        """Test masking email addresses."""
        masker = PIIMasker()
        text = "Contact us at user@example.com for support."
        masked = masker.mask(text)
        assert "[EMAIL_MASKED]" in masked
        assert "user@example.com" not in masked

    def test_mask_phone(self):
        """Test masking phone numbers."""
        masker = PIIMasker()
        text = "Call 123-456-7890 for assistance."
        masked = masker.mask(text)
        assert "[PHONE_MASKED]" in masked

    def test_mask_ssn(self):
        """Test masking SSN."""
        masker = PIIMasker()
        text = "SSN: 123-45-6789"
        masked = masker.mask(text)
        assert "[SSN_MASKED]" in masked

    def test_mask_credit_card(self):
        """Test masking credit card numbers."""
        masker = PIIMasker()
        text = "Card: 4111-1111-1111-1111"
        masked = masker.mask(text)
        assert "[CC_MASKED]" in masked

    def test_mask_bearer_token(self):
        """Test masking bearer tokens."""
        masker = PIIMasker()
        text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        masked = masker.mask(text)
        assert "[TOKEN_MASKED]" in masked

    def test_mask_dict(self):
        """Test masking dictionary values."""
        masker = PIIMasker()
        data = {
            "email": "test@example.com",
            "nested": {"phone": "123-456-7890"},
            "list": ["user@test.com"]
        }
        masked = masker.mask_dict(data)
        assert "[EMAIL_MASKED]" in masked["email"]
        assert "[PHONE_MASKED]" in masked["nested"]["phone"]

    def test_custom_patterns(self):
        """Test custom masking patterns."""
        custom = {"custom": (r"SECRET_\w+", "[CUSTOM_MASKED]")}
        masker = PIIMasker(additional_patterns=custom)
        text = "Key: SECRET_ABC123"
        masked = masker.mask(text)
        assert "[CUSTOM_MASKED]" in masked


class TestAuditEvent:
    """Tests for AuditEvent dataclass."""

    def test_event_creation(self):
        """Test creating an AuditEvent."""
        event = AuditEvent(
            id="AUD-001",
            event_type=AuditEventType.USER_ACTION,
            severity=AuditSeverity.INFO,
            message="Test event"
        )

        assert event.id == "AUD-001"
        assert event.event_type == AuditEventType.USER_ACTION

    def test_to_json(self):
        """Test JSON serialization."""
        event = AuditEvent(
            id="AUD-002",
            event_type=AuditEventType.AI_DECISION,
            severity=AuditSeverity.INFO,
            message="Test"
        )

        json_str = event.to_json()
        parsed = json.loads(json_str)
        assert parsed["id"] == "AUD-002"
        assert parsed["event_type"] == "ai_decision"

    def test_from_dict(self):
        """Test creating from dictionary."""
        data = {
            "id": "AUD-003",
            "event_type": "data_access",
            "severity": "warning",
            "message": "Test",
            "timestamp": "2025-01-01T00:00:00"
        }
        event = AuditEvent.from_dict(data)

        assert event.event_type == AuditEventType.DATA_ACCESS
        assert event.severity == AuditSeverity.WARNING


class TestAuditLogger:
    """Tests for AuditLogger class."""

    def setup_method(self):
        """Reset singleton for each test."""
        AuditLogger._instance = None

    def test_singleton_pattern(self):
        """Test that AuditLogger is a singleton."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger1 = AuditLogger(log_dir=tmpdir)
            logger2 = AuditLogger()
            assert logger1 is logger2

    def test_log_event(self):
        """Test logging an event."""
        with tempfile.TemporaryDirectory() as tmpdir:
            AuditLogger._instance = None
            logger = AuditLogger(log_dir=tmpdir)

            event_id = logger.log(
                AuditEventType.USER_ACTION,
                "User performed action",
                actor="test_user"
            )

            assert event_id.startswith("AUD-")

    def test_log_ai_decision(self):
        """Test logging AI decision."""
        with tempfile.TemporaryDirectory() as tmpdir:
            AuditLogger._instance = None
            logger = AuditLogger(log_dir=tmpdir)

            event_id = logger.log_ai_decision(
                decision="Approve request",
                reasoning="All criteria met",
                model="test-model",
                inputs={"request": "test"},
                outputs={"result": "approved"},
                confidence=0.95
            )

            assert event_id.startswith("AUD-")

    def test_log_user_action(self):
        """Test logging user action."""
        with tempfile.TemporaryDirectory() as tmpdir:
            AuditLogger._instance = None
            logger = AuditLogger(log_dir=tmpdir)

            event_id = logger.log_user_action(
                user="test_user",
                action="login",
                resource="authentication",
                outcome="success"
            )

            assert event_id.startswith("AUD-")

    def test_log_data_access(self):
        """Test logging data access."""
        with tempfile.TemporaryDirectory() as tmpdir:
            AuditLogger._instance = None
            logger = AuditLogger(log_dir=tmpdir)

            event_id = logger.log_data_access(
                accessor="system",
                data_type="user_records",
                operation="read",
                record_count=10
            )

            assert event_id.startswith("AUD-")

    def test_pii_masking(self):
        """Test that PII is masked in logs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            AuditLogger._instance = None
            logger = AuditLogger(log_dir=tmpdir, pii_masking=True)

            logger.log(
                AuditEventType.USER_ACTION,
                "User email: test@example.com logged in"
            )

            # Check the log file
            log_file = Path(tmpdir) / "audit.jsonl"
            content = log_file.read_text()
            assert "[EMAIL_MASKED]" in content
            assert "test@example.com" not in content

    def test_query_events(self):
        """Test querying events."""
        with tempfile.TemporaryDirectory() as tmpdir:
            AuditLogger._instance = None
            logger = AuditLogger(log_dir=tmpdir)

            # Log some events
            logger.log(AuditEventType.USER_ACTION, "Action 1", actor="user1")
            logger.log(AuditEventType.USER_ACTION, "Action 2", actor="user2")
            logger.log(AuditEventType.AI_DECISION, "Decision 1", actor="ai")

            # Query all
            events = logger.query(limit=10)
            assert len(events) >= 3

            # Query by type
            user_events = logger.query(event_type=AuditEventType.USER_ACTION)
            assert all(e.event_type == AuditEventType.USER_ACTION for e in user_events)

    def test_export_json(self):
        """Test exporting to JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            AuditLogger._instance = None
            logger = AuditLogger(log_dir=tmpdir)

            logger.log(AuditEventType.USER_ACTION, "Test event")

            exported = logger.export(format="json")
            data = json.loads(exported.decode())
            assert len(data) >= 1

    def test_export_csv(self):
        """Test exporting to CSV."""
        with tempfile.TemporaryDirectory() as tmpdir:
            AuditLogger._instance = None
            logger = AuditLogger(log_dir=tmpdir)

            logger.log(AuditEventType.USER_ACTION, "Test event")

            exported = logger.export(format="csv")
            lines = exported.decode().split("\n")
            assert "id" in lines[0]  # Header

    def test_add_hook(self):
        """Test adding alert hooks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            AuditLogger._instance = None
            logger = AuditLogger(log_dir=tmpdir)

            hook_calls = []

            def hook(event):
                hook_calls.append(event)

            logger.add_hook(hook)
            logger.log(AuditEventType.USER_ACTION, "Test")

            assert len(hook_calls) == 1


class TestGetAuditLoggerFunction:
    """Tests for convenience function."""

    def setup_method(self):
        """Reset singleton."""
        AuditLogger._instance = None

    def test_get_audit_logger(self):
        """Test getting audit logger."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = get_audit_logger(log_dir=tmpdir)
            assert isinstance(logger, AuditLogger)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
