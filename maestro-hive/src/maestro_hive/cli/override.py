#!/usr/bin/env python3
"""
Emergency Override ("God Mode") Implementation

EPIC: MD-3120 - Implement Emergency Override
Implements all 4 Acceptance Criteria:
    AC-1: Standard user cannot invoke override (Access Control)
    AC-2: Token stops working after 4 hours (Expiration)
    AC-3: Actions taken during override are flagged in the log (Audit)
    AC-4: Even in God Mode, cannot delete the Audit Log (Immutable)

Usage:
    maestro-cli override --reason "Fixing critical bug"
    maestro-cli override --add-signature SIG2 --token <token_id>
    maestro-cli override --status
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import subprocess
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Configuration
OVERRIDE_DURATION_HOURS = 4
REQUIRED_SIGNATURES = 2
ADMIN_USERS_ENV = "MAESTRO_ADMIN_USERS"
ADMIN_DOMAIN = "@fifth-9.com"
AUDIT_LOG_PATH = "/var/log/maestro/override_audit.log"
FALLBACK_AUDIT_LOG_PATH = os.path.expanduser("~/.maestro/override_audit.log")
TOKEN_STORAGE_PATH = os.path.expanduser("~/.maestro/override_tokens.json")


class OverrideStatus(Enum):
    """Status of an override session."""
    PENDING_SIGNATURES = "pending_signatures"
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"


class OverrideError(Exception):
    """Base exception for override errors."""
    pass


class AccessDeniedError(OverrideError):
    """AC-1: User does not have admin access."""
    pass


class TokenExpiredError(OverrideError):
    """AC-2: Override token has expired."""
    pass


class InsufficientSignaturesError(OverrideError):
    """Multi-sig requirement not met."""
    pass


class AuditLogProtectedError(OverrideError):
    """AC-4: Cannot modify/delete audit log."""
    pass


@dataclass
class OverrideToken:
    """
    Represents an override session token.

    Implements:
        - AC-2: Time-limited expiration (4 hours)
        - Multi-sig: Requires 2 unique signatures
    """
    token_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    reason: str = ""
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    expires_at: str = field(default_factory=lambda: (datetime.utcnow() + timedelta(hours=OVERRIDE_DURATION_HOURS)).isoformat())
    signatures: List[str] = field(default_factory=list)
    created_by: str = ""
    status: str = OverrideStatus.PENDING_SIGNATURES.value

    def is_expired(self) -> bool:
        """
        AC-2: Check if token has expired.

        Returns:
            True if current time is past expiration.
        """
        expires = datetime.fromisoformat(self.expires_at)
        return datetime.utcnow() > expires

    def is_active(self) -> bool:
        """Check if token is currently active."""
        return (
            self.status == OverrideStatus.ACTIVE.value
            and not self.is_expired()
            and len(set(self.signatures)) >= REQUIRED_SIGNATURES
        )

    def remaining_time(self) -> timedelta:
        """Get remaining time before expiration."""
        expires = datetime.fromisoformat(self.expires_at)
        remaining = expires - datetime.utcnow()
        return remaining if remaining.total_seconds() > 0 else timedelta(0)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OverrideToken":
        """Reconstruct from dictionary."""
        return cls(**data)


class AuditLogger:
    """
    Immutable audit logger for override sessions.

    Implements:
        AC-3: Log all actions during override
        AC-4: Audit log cannot be deleted
    """

    def __init__(self, log_path: Optional[str] = None):
        """
        Initialize the audit logger.

        Args:
            log_path: Path to audit log file (uses default if None)
        """
        self._log_path = Path(log_path) if log_path else self._get_log_path()
        self._ensure_log_exists()

    def _get_log_path(self) -> Path:
        """Get the appropriate log path."""
        primary = Path(AUDIT_LOG_PATH)
        if primary.parent.exists() and os.access(primary.parent, os.W_OK):
            return primary
        # Fallback to user directory
        fallback = Path(FALLBACK_AUDIT_LOG_PATH)
        fallback.parent.mkdir(parents=True, exist_ok=True)
        return fallback

    def _ensure_log_exists(self) -> None:
        """Ensure log file exists and is protected."""
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        if not self._log_path.exists():
            self._log_path.touch()
        self._set_append_only()

    def _set_append_only(self) -> None:
        """
        AC-4: Set append-only attribute to prevent deletion.

        Uses chattr +a on Linux to make file append-only.
        """
        try:
            # Only attempt on Linux with root access
            if os.name == "posix" and os.geteuid() == 0:
                subprocess.run(
                    ["chattr", "+a", str(self._log_path)],
                    capture_output=True,
                    check=False
                )
                logger.info(f"Set append-only attribute on {self._log_path}")
        except Exception as e:
            logger.warning(f"Could not set append-only attribute: {e}")

    def log_action(
        self,
        token: OverrideToken,
        action: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        AC-3: Log an action taken during override session.

        All actions are flagged with OVERRIDE_SESSION marker.

        Args:
            token: The active override token
            action: Description of the action taken
            details: Optional additional details
        """
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "token_id": token.token_id,
            "action": action,
            "flag": "OVERRIDE_SESSION",
            "user": token.created_by,
            "signatures": token.signatures,
            "details": details or {}
        }

        self._append_entry(entry)
        logger.info(f"Audit logged: {action} (token={token.token_id[:8]})")

    def log_override_start(self, token: OverrideToken) -> None:
        """Log the start of an override session."""
        self.log_action(token, "OVERRIDE_SESSION_START", {
            "reason": token.reason,
            "expires_at": token.expires_at
        })

    def log_override_end(self, token: OverrideToken, reason: str = "normal") -> None:
        """Log the end of an override session."""
        self.log_action(token, "OVERRIDE_SESSION_END", {
            "end_reason": reason,
            "duration_seconds": (
                datetime.utcnow() - datetime.fromisoformat(token.created_at)
            ).total_seconds()
        })

    def log_signature_added(self, token: OverrideToken, signature: str) -> None:
        """Log when a signature is added."""
        self.log_action(token, "SIGNATURE_ADDED", {
            "signature": signature,
            "total_signatures": len(token.signatures)
        })

    def _append_entry(self, entry: Dict[str, Any]) -> None:
        """Append an entry to the audit log."""
        try:
            with open(self._log_path, "a") as f:
                f.write(json.dumps(entry) + "\n")
                f.flush()
                os.fsync(f.fileno())
        except IOError as e:
            logger.error(f"Failed to write audit log: {e}")
            raise AuditLogProtectedError(f"Cannot write to audit log: {e}")

    def get_session_actions(self, token_id: str) -> List[Dict[str, Any]]:
        """Get all actions for a specific override session."""
        actions = []
        try:
            with open(self._log_path, "r") as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        if entry.get("token_id") == token_id:
                            actions.append(entry)
                    except json.JSONDecodeError:
                        continue
        except IOError:
            pass
        return actions

    def is_protected(self) -> bool:
        """
        AC-4: Check if audit log has immutability protection.

        Returns:
            True if log file has append-only attribute set.
        """
        try:
            if os.name == "posix":
                result = subprocess.run(
                    ["lsattr", str(self._log_path)],
                    capture_output=True,
                    text=True,
                    check=False
                )
                return "a" in result.stdout.split()[0] if result.stdout else False
        except Exception:
            pass
        return False


class OverrideManager:
    """
    Manages emergency override sessions.

    Coordinates access control, token lifecycle, and audit logging.
    """

    def __init__(
        self,
        audit_logger: Optional[AuditLogger] = None,
        token_storage_path: Optional[str] = None
    ):
        """
        Initialize the override manager.

        Args:
            audit_logger: Optional custom audit logger
            token_storage_path: Path to store active tokens
        """
        self._audit = audit_logger or AuditLogger()
        self._token_path = Path(token_storage_path or TOKEN_STORAGE_PATH)
        self._token_path.parent.mkdir(parents=True, exist_ok=True)
        self._active_token: Optional[OverrideToken] = None
        self._load_active_token()

    def _load_active_token(self) -> None:
        """Load any existing active token from storage."""
        if self._token_path.exists():
            try:
                with open(self._token_path, "r") as f:
                    data = json.load(f)
                    token = OverrideToken.from_dict(data)
                    if not token.is_expired():
                        self._active_token = token
                    else:
                        # Token expired, clean up
                        self._token_path.unlink(missing_ok=True)
            except (json.JSONDecodeError, IOError):
                pass

    def _save_token(self, token: OverrideToken) -> None:
        """Save token to persistent storage."""
        with open(self._token_path, "w") as f:
            json.dump(token.to_dict(), f, indent=2)

    def check_admin_access(self, user: str) -> bool:
        """
        AC-1: Check if user has admin access for override.

        Args:
            user: Username or email to check

        Returns:
            True if user is an admin
        """
        # Check environment variable for admin users
        admin_users = os.environ.get(ADMIN_USERS_ENV, "").split(",")
        admin_users = [u.strip() for u in admin_users if u.strip()]

        # Check if user is in admin list
        if user in admin_users:
            return True

        # Check if user has admin domain
        if user.endswith(ADMIN_DOMAIN):
            return True

        return False

    def request_override(
        self,
        user: str,
        reason: str,
        initial_signature: str
    ) -> OverrideToken:
        """
        Request a new override session.

        AC-1: Only admin users can request override.

        Args:
            user: Username requesting override
            reason: Reason for override
            initial_signature: First signature for multi-sig

        Returns:
            New OverrideToken (pending signatures)

        Raises:
            AccessDeniedError: If user is not admin
        """
        # AC-1: Check admin access
        if not self.check_admin_access(user):
            logger.warning(f"Access denied for user: {user}")
            raise AccessDeniedError(
                f"User '{user}' does not have admin access. "
                f"Set {ADMIN_USERS_ENV} or use an {ADMIN_DOMAIN} email."
            )

        # Create new token
        token = OverrideToken(
            reason=reason,
            created_by=user,
            signatures=[initial_signature]
        )

        # Save token
        self._save_token(token)
        self._active_token = token

        # Log override request
        self._audit.log_action(token, "OVERRIDE_REQUESTED", {
            "reason": reason,
            "initial_signature": initial_signature
        })

        logger.info(f"Override requested by {user}: {token.token_id[:8]}")
        return token

    def add_signature(self, token_id: str, signature: str) -> OverrideToken:
        """
        Add a signature to an override token.

        Args:
            token_id: Token to add signature to
            signature: New signature to add

        Returns:
            Updated token

        Raises:
            OverrideError: If token not found or expired
        """
        if not self._active_token or self._active_token.token_id != token_id:
            raise OverrideError(f"Token not found: {token_id}")

        # AC-2: Check expiration
        if self._active_token.is_expired():
            self._audit.log_override_end(self._active_token, "expired")
            raise TokenExpiredError("Override token has expired")

        # Add signature if unique
        if signature not in self._active_token.signatures:
            self._active_token.signatures.append(signature)
            self._audit.log_signature_added(self._active_token, signature)

        # Check if we have enough signatures
        if len(set(self._active_token.signatures)) >= REQUIRED_SIGNATURES:
            self._active_token.status = OverrideStatus.ACTIVE.value
            self._audit.log_override_start(self._active_token)

        # Save updated token
        self._save_token(self._active_token)

        return self._active_token

    def get_active_token(self) -> Optional[OverrideToken]:
        """Get the currently active override token."""
        if self._active_token:
            # AC-2: Check expiration
            if self._active_token.is_expired():
                self._audit.log_override_end(self._active_token, "expired")
                self._active_token.status = OverrideStatus.EXPIRED.value
                self._save_token(self._active_token)
                return None
        return self._active_token

    def is_override_active(self) -> bool:
        """Check if there's an active override session."""
        token = self.get_active_token()
        return token is not None and token.is_active()

    def revoke_override(self, user: str, reason: str = "manual") -> None:
        """
        Revoke the active override session.

        Args:
            user: User performing revocation
            reason: Reason for revocation
        """
        if not self._active_token:
            return

        # AC-1: Check admin access
        if not self.check_admin_access(user):
            raise AccessDeniedError(f"User '{user}' cannot revoke override")

        self._active_token.status = OverrideStatus.REVOKED.value
        self._audit.log_override_end(self._active_token, reason)
        self._save_token(self._active_token)

        logger.info(f"Override revoked by {user}: {reason}")

    def execute_with_override(
        self,
        action: str,
        func: callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute a function within an override session.

        AC-3: All actions are logged.
        AC-4: Cannot delete audit log.

        Args:
            action: Description of the action
            func: Function to execute
            *args, **kwargs: Arguments for the function

        Returns:
            Result of the function

        Raises:
            OverrideError: If no active override session
        """
        if not self.is_override_active():
            raise OverrideError("No active override session")

        # AC-3: Log action before execution
        self._audit.log_action(self._active_token, f"EXECUTE: {action}")

        try:
            result = func(*args, **kwargs)
            self._audit.log_action(self._active_token, f"SUCCESS: {action}")
            return result
        except Exception as e:
            self._audit.log_action(
                self._active_token,
                f"FAILED: {action}",
                {"error": str(e)}
            )
            raise

    def get_status(self) -> Dict[str, Any]:
        """Get current override status."""
        token = self.get_active_token()

        if not token:
            return {
                "status": "no_active_override",
                "message": "No override session is currently active"
            }

        return {
            "status": token.status,
            "token_id": token.token_id,
            "created_at": token.created_at,
            "expires_at": token.expires_at,
            "remaining_time": str(token.remaining_time()),
            "signatures": len(set(token.signatures)),
            "required_signatures": REQUIRED_SIGNATURES,
            "reason": token.reason,
            "is_active": token.is_active()
        }


# CLI Interface Functions
def handle_override_command(args: argparse.Namespace) -> int:
    """
    Handle the maestro-cli override command.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success)
    """
    manager = OverrideManager()

    if args.status:
        status = manager.get_status()
        print(json.dumps(status, indent=2))
        return 0

    if args.revoke:
        user = os.environ.get("USER", "unknown")
        try:
            manager.revoke_override(user, args.revoke)
            print("Override session revoked")
            return 0
        except AccessDeniedError as e:
            print(f"Error: {e}")
            return 1

    if args.add_signature:
        if not args.token:
            print("Error: --token required when adding signature")
            return 1
        try:
            token = manager.add_signature(args.token, args.add_signature)
            print(f"Signature added. Status: {token.status}")
            if token.is_active():
                print(f"Override session is now ACTIVE (expires: {token.expires_at})")
            else:
                sigs = len(set(token.signatures))
                print(f"Waiting for {REQUIRED_SIGNATURES - sigs} more signature(s)")
            return 0
        except OverrideError as e:
            print(f"Error: {e}")
            return 1

    if args.reason:
        user = os.environ.get("USER", "unknown")
        signature = args.signature or f"SIG_{user}_{int(time.time())}"
        try:
            token = manager.request_override(user, args.reason, signature)
            print(f"Override requested. Token ID: {token.token_id}")
            print(f"Initial signature: {signature}")
            print(f"Waiting for {REQUIRED_SIGNATURES - 1} more signature(s)")
            print(f"\nNext approver should run:")
            print(f"  maestro-cli override --add-signature <SIG> --token {token.token_id}")
            return 0
        except AccessDeniedError as e:
            print(f"Error: {e}")
            return 1

    print("Usage: maestro-cli override --reason 'description' [--signature SIG]")
    print("       maestro-cli override --add-signature SIG --token TOKEN_ID")
    print("       maestro-cli override --status")
    print("       maestro-cli override --revoke 'reason'")
    return 1


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for override command."""
    parser = argparse.ArgumentParser(
        description="Emergency Override (God Mode) for Maestro",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Request override:
    maestro-cli override --reason "Fixing critical policy bug"

  Add second signature:
    maestro-cli override --add-signature SIG2 --token <token_id>

  Check status:
    maestro-cli override --status

  Revoke override:
    maestro-cli override --revoke "No longer needed"
        """
    )

    parser.add_argument(
        "--reason",
        help="Reason for requesting override"
    )
    parser.add_argument(
        "--signature",
        help="Custom signature for this approval"
    )
    parser.add_argument(
        "--add-signature",
        help="Add a signature to existing token"
    )
    parser.add_argument(
        "--token",
        help="Token ID when adding signature"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show current override status"
    )
    parser.add_argument(
        "--revoke",
        metavar="REASON",
        help="Revoke active override session"
    )

    return parser


def main() -> int:
    """Main entry point for override command."""
    parser = create_parser()
    args = parser.parse_args()
    return handle_override_command(args)


if __name__ == "__main__":
    exit(main())
