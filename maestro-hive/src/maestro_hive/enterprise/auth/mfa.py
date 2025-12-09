"""
Multi-Factor Authentication Provider.

Implements TOTP-based MFA with backup codes for enterprise security.
"""

import secrets
import hashlib
import hmac
import struct
import time
import base64
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from enum import Enum


class MFAStatus(Enum):
    """MFA enrollment status."""
    DISABLED = "disabled"
    PENDING = "pending"
    ENABLED = "enabled"


@dataclass
class MFAConfig:
    """MFA configuration."""
    issuer: str = "Maestro"
    digits: int = 6
    interval: int = 30
    algorithm: str = "SHA1"
    backup_code_count: int = 10
    backup_code_length: int = 8


@dataclass
class MFASetupResult:
    """Result of MFA setup."""
    secret: str
    qr_code_uri: str
    backup_codes: List[str]
    status: MFAStatus = MFAStatus.PENDING


@dataclass
class MFAVerifyResult:
    """Result of MFA verification."""
    verified: bool
    method: str  # "totp" or "backup"
    remaining_backup_codes: Optional[int] = None


class MFAProvider:
    """
    Multi-Factor Authentication provider using TOTP.

    Implements RFC 6238 TOTP algorithm with support for
    backup codes and secure secret management.
    """

    def __init__(self, config: Optional[MFAConfig] = None):
        """Initialize MFA provider."""
        self.config = config or MFAConfig()
        self._used_backup_codes: dict = {}  # user_id -> set of used codes

    def generate_secret(self) -> str:
        """
        Generate cryptographically secure TOTP secret.

        Returns:
            Base32-encoded secret
        """
        # Generate 20 bytes (160 bits) of randomness
        random_bytes = secrets.token_bytes(20)
        return base64.b32encode(random_bytes).decode("utf-8").rstrip("=")

    def generate_backup_codes(self) -> List[str]:
        """
        Generate backup codes for account recovery.

        Returns:
            List of backup codes
        """
        codes = []
        for _ in range(self.config.backup_code_count):
            # Generate readable backup code (8 chars, alphanumeric)
            code = secrets.token_hex(self.config.backup_code_length // 2).upper()
            # Format as XXXX-XXXX for readability
            formatted = f"{code[:4]}-{code[4:]}"
            codes.append(formatted)
        return codes

    def generate_provisioning_uri(
        self,
        secret: str,
        account_name: str,
    ) -> str:
        """
        Generate otpauth:// URI for QR code.

        Args:
            secret: Base32-encoded secret
            account_name: User account identifier (email)

        Returns:
            otpauth:// URI for authenticator apps
        """
        issuer = self.config.issuer
        algorithm = self.config.algorithm
        digits = self.config.digits
        period = self.config.interval

        # URL encode the account name
        encoded_account = account_name.replace(" ", "%20").replace("@", "%40")
        encoded_issuer = issuer.replace(" ", "%20")

        uri = (
            f"otpauth://totp/{encoded_issuer}:{encoded_account}"
            f"?secret={secret}"
            f"&issuer={encoded_issuer}"
            f"&algorithm={algorithm}"
            f"&digits={digits}"
            f"&period={period}"
        )

        return uri

    def setup_mfa(self, account_name: str) -> MFASetupResult:
        """
        Setup MFA for a user account.

        Args:
            account_name: User account identifier

        Returns:
            MFASetupResult with secret, QR URI, and backup codes
        """
        secret = self.generate_secret()
        qr_uri = self.generate_provisioning_uri(secret, account_name)
        backup_codes = self.generate_backup_codes()

        return MFASetupResult(
            secret=secret,
            qr_code_uri=qr_uri,
            backup_codes=backup_codes,
            status=MFAStatus.PENDING,
        )

    def _generate_totp(
        self,
        secret: str,
        timestamp: Optional[int] = None,
    ) -> str:
        """
        Generate TOTP code for given timestamp.

        Args:
            secret: Base32-encoded secret
            timestamp: Unix timestamp (current time if not provided)

        Returns:
            TOTP code string
        """
        if timestamp is None:
            timestamp = int(time.time())

        # Calculate time counter
        counter = timestamp // self.config.interval

        # Decode secret (handle missing padding)
        secret_padded = secret + "=" * (8 - len(secret) % 8) if len(secret) % 8 else secret
        key = base64.b32decode(secret_padded.upper())

        # Generate HMAC-SHA1
        counter_bytes = struct.pack(">Q", counter)
        hmac_hash = hmac.new(key, counter_bytes, hashlib.sha1).digest()

        # Dynamic truncation (RFC 4226)
        offset = hmac_hash[-1] & 0x0F
        code = struct.unpack(">I", hmac_hash[offset:offset + 4])[0]
        code = code & 0x7FFFFFFF  # Remove sign bit
        code = code % (10 ** self.config.digits)

        return str(code).zfill(self.config.digits)

    def verify_totp(
        self,
        secret: str,
        code: str,
        window: int = 1,
    ) -> bool:
        """
        Verify TOTP code with time window tolerance.

        Args:
            secret: Base32-encoded secret
            code: User-provided code
            window: Number of intervals to check before/after current

        Returns:
            True if code is valid
        """
        current_time = int(time.time())

        # Check current and adjacent time windows
        for offset in range(-window, window + 1):
            timestamp = current_time + (offset * self.config.interval)
            expected_code = self._generate_totp(secret, timestamp)
            if hmac.compare_digest(code, expected_code):
                return True

        return False

    def verify_backup_code(
        self,
        user_id: str,
        code: str,
        valid_codes: List[str],
    ) -> Tuple[bool, List[str]]:
        """
        Verify and consume backup code.

        Args:
            user_id: User identifier
            code: User-provided backup code
            valid_codes: List of valid backup codes for user

        Returns:
            Tuple of (is_valid, remaining_codes)
        """
        # Normalize code format
        normalized = code.upper().replace("-", "")
        if len(normalized) == 8:
            normalized = f"{normalized[:4]}-{normalized[4:]}"

        # Check if code was already used
        used_codes = self._used_backup_codes.get(user_id, set())
        if normalized in used_codes:
            return False, valid_codes

        # Verify code
        for valid_code in valid_codes:
            if hmac.compare_digest(normalized, valid_code):
                # Mark code as used
                if user_id not in self._used_backup_codes:
                    self._used_backup_codes[user_id] = set()
                self._used_backup_codes[user_id].add(normalized)

                # Return remaining codes
                remaining = [c for c in valid_codes if c != valid_code]
                return True, remaining

        return False, valid_codes

    def verify(
        self,
        user_id: str,
        secret: str,
        code: str,
        backup_codes: Optional[List[str]] = None,
    ) -> MFAVerifyResult:
        """
        Verify MFA code (TOTP or backup).

        Args:
            user_id: User identifier
            secret: TOTP secret
            code: User-provided code
            backup_codes: Valid backup codes

        Returns:
            MFAVerifyResult with verification status
        """
        # Try TOTP first
        if self.verify_totp(secret, code):
            return MFAVerifyResult(
                verified=True,
                method="totp",
            )

        # Try backup code if available
        if backup_codes:
            is_valid, remaining = self.verify_backup_code(user_id, code, backup_codes)
            if is_valid:
                return MFAVerifyResult(
                    verified=True,
                    method="backup",
                    remaining_backup_codes=len(remaining),
                )

        return MFAVerifyResult(
            verified=False,
            method="none",
        )

    def regenerate_backup_codes(self, user_id: str) -> List[str]:
        """
        Regenerate backup codes for user.

        Args:
            user_id: User identifier

        Returns:
            New list of backup codes
        """
        # Clear used codes for user
        if user_id in self._used_backup_codes:
            del self._used_backup_codes[user_id]

        return self.generate_backup_codes()
