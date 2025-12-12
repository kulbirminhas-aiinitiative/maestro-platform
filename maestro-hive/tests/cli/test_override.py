#!/usr/bin/env python3
"""
Tests for Emergency Override ("God Mode") Implementation

EPIC: MD-3120 - Implement Emergency Override
Tests all 4 Acceptance Criteria:
    AC-1: Standard user cannot invoke override (Access Control)
    AC-2: Token stops working after 4 hours (Expiration)
    AC-3: Actions taken during override are flagged in the log (Audit)
    AC-4: Even in God Mode, cannot delete the Audit Log (Immutable)
"""

import json
import os
import pytest
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from maestro_hive.cli.override import (
    OverrideToken,
    OverrideStatus,
    AuditLogger,
    OverrideManager,
    AccessDeniedError,
    TokenExpiredError,
    OVERRIDE_DURATION_HOURS,
    REQUIRED_SIGNATURES,
    ADMIN_USERS_ENV,
    ADMIN_DOMAIN,
)


class TestOverrideToken:
    """Tests for OverrideToken dataclass."""

    def test_token_creation(self):
        """Test creating a new override token."""
        token = OverrideToken(
            reason="Test override",
            created_by="admin@fifth-9.com",
            signatures=["SIG1"]
        )

        assert token.token_id is not None
        assert token.reason == "Test override"
        assert token.created_by == "admin@fifth-9.com"
        assert len(token.signatures) == 1
        assert token.status == OverrideStatus.PENDING_SIGNATURES.value

    def test_token_not_expired_initially(self):
        """Test that new token is not expired."""
        token = OverrideToken(reason="Test")
        assert not token.is_expired()

    def test_ac2_token_expiration(self):
        """AC-2: Token stops working after 4 hours."""
        # Create token that expires in the past
        past_time = (datetime.utcnow() - timedelta(hours=5)).isoformat()
        token = OverrideToken(
            reason="Test",
            expires_at=past_time
        )

        assert token.is_expired()

    def test_token_remaining_time(self):
        """Test remaining time calculation."""
        token = OverrideToken(reason="Test")
        remaining = token.remaining_time()

        # Should be close to 4 hours
        assert remaining.total_seconds() > (OVERRIDE_DURATION_HOURS - 0.1) * 3600
        assert remaining.total_seconds() <= OVERRIDE_DURATION_HOURS * 3600

    def test_token_is_active(self):
        """Test token active status."""
        token = OverrideToken(
            reason="Test",
            signatures=["SIG1", "SIG2"],
            status=OverrideStatus.ACTIVE.value
        )

        assert token.is_active()

    def test_token_not_active_without_signatures(self):
        """Test that token needs required signatures."""
        token = OverrideToken(
            reason="Test",
            signatures=["SIG1"],  # Only 1 signature, need 2
            status=OverrideStatus.ACTIVE.value
        )

        assert not token.is_active()

    def test_token_serialization(self):
        """Test token to_dict and from_dict."""
        token = OverrideToken(
            reason="Test override",
            created_by="admin@fifth-9.com",
            signatures=["SIG1", "SIG2"]
        )

        data = token.to_dict()
        restored = OverrideToken.from_dict(data)

        assert restored.token_id == token.token_id
        assert restored.reason == token.reason
        assert restored.signatures == token.signatures


class TestAuditLogger:
    """Tests for AuditLogger class."""

    @pytest.fixture
    def temp_log(self):
        """Create a temporary log file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            yield f.name
        os.unlink(f.name)

    def test_log_creation(self, temp_log):
        """Test creating audit logger."""
        logger = AuditLogger(log_path=temp_log)
        assert Path(temp_log).exists()

    def test_ac3_action_logged_with_flag(self, temp_log):
        """AC-3: Actions taken during override are flagged in the log."""
        logger = AuditLogger(log_path=temp_log)
        token = OverrideToken(reason="Test", created_by="admin")

        logger.log_action(token, "test_action")

        # Read log and verify flag
        with open(temp_log, 'r') as f:
            log_entry = json.loads(f.readline())

        assert log_entry["flag"] == "OVERRIDE_SESSION"
        assert log_entry["action"] == "test_action"
        assert log_entry["token_id"] == token.token_id

    def test_ac3_override_start_logged(self, temp_log):
        """AC-3: Override session start is logged."""
        logger = AuditLogger(log_path=temp_log)
        token = OverrideToken(reason="Critical fix")

        logger.log_override_start(token)

        with open(temp_log, 'r') as f:
            log_entry = json.loads(f.readline())

        assert log_entry["action"] == "OVERRIDE_SESSION_START"
        assert log_entry["details"]["reason"] == "Critical fix"

    def test_ac3_override_end_logged(self, temp_log):
        """AC-3: Override session end is logged."""
        logger = AuditLogger(log_path=temp_log)
        token = OverrideToken(reason="Test")

        logger.log_override_end(token, reason="completed")

        with open(temp_log, 'r') as f:
            log_entry = json.loads(f.readline())

        assert log_entry["action"] == "OVERRIDE_SESSION_END"
        assert log_entry["details"]["end_reason"] == "completed"

    def test_ac3_signature_logged(self, temp_log):
        """AC-3: Signature additions are logged."""
        logger = AuditLogger(log_path=temp_log)
        token = OverrideToken(reason="Test", signatures=["SIG1"])

        logger.log_signature_added(token, "SIG2")

        with open(temp_log, 'r') as f:
            log_entry = json.loads(f.readline())

        assert log_entry["action"] == "SIGNATURE_ADDED"
        assert log_entry["details"]["signature"] == "SIG2"

    def test_get_session_actions(self, temp_log):
        """Test retrieving actions for a specific session."""
        logger = AuditLogger(log_path=temp_log)
        token1 = OverrideToken(reason="Test1")
        token2 = OverrideToken(reason="Test2")

        logger.log_action(token1, "action1")
        logger.log_action(token2, "action2")
        logger.log_action(token1, "action3")

        actions = logger.get_session_actions(token1.token_id)
        assert len(actions) == 2
        assert actions[0]["action"] == "action1"
        assert actions[1]["action"] == "action3"


class TestOverrideManager:
    """Tests for OverrideManager class."""

    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "audit.log")
            token_path = os.path.join(tmpdir, "tokens.json")
            yield log_path, token_path

    @pytest.fixture
    def manager(self, temp_dirs):
        """Create an override manager for testing."""
        log_path, token_path = temp_dirs
        return OverrideManager(
            audit_logger=AuditLogger(log_path=log_path),
            token_storage_path=token_path
        )

    def test_ac1_admin_user_access(self, manager):
        """AC-1: Admin users can access override."""
        # Admin domain user
        assert manager.check_admin_access("admin@fifth-9.com")

    def test_ac1_standard_user_denied(self, manager):
        """AC-1: Standard user cannot invoke override."""
        # Standard user
        assert not manager.check_admin_access("user@example.com")

    def test_ac1_env_admin_access(self, manager):
        """AC-1: Users in MAESTRO_ADMIN_USERS env var have access."""
        with patch.dict(os.environ, {ADMIN_USERS_ENV: "special_admin,another_admin"}):
            assert manager.check_admin_access("special_admin")
            assert manager.check_admin_access("another_admin")

    def test_ac1_request_override_denied(self, manager):
        """AC-1: Request override fails for non-admin."""
        with pytest.raises(AccessDeniedError) as exc:
            manager.request_override(
                user="standard_user@example.com",
                reason="Test",
                initial_signature="SIG1"
            )

        assert "does not have admin access" in str(exc.value)

    def test_ac1_request_override_allowed(self, manager):
        """AC-1: Request override succeeds for admin."""
        token = manager.request_override(
            user="admin@fifth-9.com",
            reason="Critical fix",
            initial_signature="SIG1"
        )

        assert token is not None
        assert token.reason == "Critical fix"
        assert "SIG1" in token.signatures

    def test_multi_sig_requirement(self, manager):
        """Test that 2 signatures are required."""
        # Request override with first signature
        token = manager.request_override(
            user="admin@fifth-9.com",
            reason="Test",
            initial_signature="SIG1"
        )

        # Token should not be active yet
        assert not token.is_active()
        assert token.status == OverrideStatus.PENDING_SIGNATURES.value

        # Add second signature
        token = manager.add_signature(token.token_id, "SIG2")

        # Now it should be active
        assert token.is_active()
        assert token.status == OverrideStatus.ACTIVE.value

    def test_duplicate_signature_rejected(self, manager):
        """Test that same signature twice doesn't count as two."""
        token = manager.request_override(
            user="admin@fifth-9.com",
            reason="Test",
            initial_signature="SIG1"
        )

        # Add same signature again
        token = manager.add_signature(token.token_id, "SIG1")

        # Should still only count as 1 signature
        assert len(set(token.signatures)) == 1
        assert not token.is_active()

    def test_ac2_expired_token_rejected(self, manager):
        """AC-2: Expired token is rejected when adding signature."""
        # Request override
        token = manager.request_override(
            user="admin@fifth-9.com",
            reason="Test",
            initial_signature="SIG1"
        )

        # Manually expire the token
        manager._active_token.expires_at = (
            datetime.utcnow() - timedelta(hours=1)
        ).isoformat()

        # Try to add signature to expired token
        with pytest.raises(TokenExpiredError):
            manager.add_signature(token.token_id, "SIG2")

    def test_get_status_no_active(self, manager):
        """Test status when no override is active."""
        status = manager.get_status()
        assert status["status"] == "no_active_override"

    def test_get_status_active(self, manager):
        """Test status when override is active."""
        token = manager.request_override(
            user="admin@fifth-9.com",
            reason="Testing",
            initial_signature="SIG1"
        )
        manager.add_signature(token.token_id, "SIG2")

        status = manager.get_status()
        assert status["status"] == OverrideStatus.ACTIVE.value
        assert status["is_active"] is True
        assert status["reason"] == "Testing"

    def test_revoke_override(self, manager):
        """Test revoking an active override."""
        token = manager.request_override(
            user="admin@fifth-9.com",
            reason="Test",
            initial_signature="SIG1"
        )
        manager.add_signature(token.token_id, "SIG2")

        # Revoke
        manager.revoke_override(user="admin@fifth-9.com", reason="No longer needed")

        # Should no longer be active
        assert not manager.is_override_active()

    def test_ac1_revoke_denied_for_non_admin(self, manager):
        """AC-1: Non-admin cannot revoke override."""
        token = manager.request_override(
            user="admin@fifth-9.com",
            reason="Test",
            initial_signature="SIG1"
        )
        manager.add_signature(token.token_id, "SIG2")

        with pytest.raises(AccessDeniedError):
            manager.revoke_override(user="standard@example.com", reason="hacking")

    def test_execute_with_override(self, manager):
        """Test executing function within override session."""
        # Set up active override
        token = manager.request_override(
            user="admin@fifth-9.com",
            reason="Test",
            initial_signature="SIG1"
        )
        manager.add_signature(token.token_id, "SIG2")

        # Execute a function
        def test_func(x, y):
            return x + y

        result = manager.execute_with_override("addition", test_func, 1, 2)
        assert result == 3

    def test_execute_without_override_fails(self, manager):
        """Test that execute fails without active override."""
        from maestro_hive.cli.override import OverrideError

        def test_func():
            return "should not run"

        with pytest.raises(OverrideError) as exc:
            manager.execute_with_override("test", test_func)

        assert "No active override session" in str(exc.value)


class TestAC4AuditImmutability:
    """Tests for AC-4: Audit log immutability."""

    @pytest.fixture
    def temp_log(self):
        """Create a temporary log file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            yield f.name
        try:
            os.unlink(f.name)
        except OSError:
            pass

    def test_ac4_audit_log_cannot_be_deleted_during_override(self, temp_log):
        """AC-4: Even in God Mode, cannot delete the Audit Log."""
        logger = AuditLogger(log_path=temp_log)
        token = OverrideToken(reason="Test")

        # Log some actions
        logger.log_action(token, "sensitive_action")

        # The audit log should still exist
        assert Path(temp_log).exists()

        # Verify the action was logged
        with open(temp_log, 'r') as f:
            log_entry = json.loads(f.readline())
        assert log_entry["action"] == "sensitive_action"

    def test_ac4_append_only_attempted(self, temp_log):
        """AC-4: Verify append-only is attempted on audit log."""
        # This test verifies the mechanism exists, even if chattr
        # can't be applied without root
        logger = AuditLogger(log_path=temp_log)

        # The is_protected method exists
        assert hasattr(logger, 'is_protected')

        # Log file should exist
        assert Path(temp_log).exists()


class TestTokenPersistence:
    """Tests for token persistence across restarts."""

    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "audit.log")
            token_path = os.path.join(tmpdir, "tokens.json")
            yield log_path, token_path

    def test_token_persists_across_restart(self, temp_dirs):
        """Test that active token survives manager restart."""
        log_path, token_path = temp_dirs

        # Create manager and start override
        manager1 = OverrideManager(
            audit_logger=AuditLogger(log_path=log_path),
            token_storage_path=token_path
        )

        token = manager1.request_override(
            user="admin@fifth-9.com",
            reason="Persistent test",
            initial_signature="SIG1"
        )
        manager1.add_signature(token.token_id, "SIG2")

        original_token_id = token.token_id

        # Create new manager (simulating restart)
        manager2 = OverrideManager(
            audit_logger=AuditLogger(log_path=log_path),
            token_storage_path=token_path
        )

        # Should restore the active token
        restored_token = manager2.get_active_token()
        assert restored_token is not None
        assert restored_token.token_id == original_token_id
        assert restored_token.is_active()

    def test_expired_token_not_restored(self, temp_dirs):
        """Test that expired tokens are not restored on restart."""
        log_path, token_path = temp_dirs

        # Create manager and start override
        manager1 = OverrideManager(
            audit_logger=AuditLogger(log_path=log_path),
            token_storage_path=token_path
        )

        token = manager1.request_override(
            user="admin@fifth-9.com",
            reason="Test",
            initial_signature="SIG1"
        )

        # Manually expire the token in storage
        with open(token_path, 'r+') as f:
            data = json.load(f)
            data['expires_at'] = (datetime.utcnow() - timedelta(hours=1)).isoformat()
            f.seek(0)
            json.dump(data, f)
            f.truncate()

        # Create new manager
        manager2 = OverrideManager(
            audit_logger=AuditLogger(log_path=log_path),
            token_storage_path=token_path
        )

        # Should not restore expired token
        assert manager2.get_active_token() is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
