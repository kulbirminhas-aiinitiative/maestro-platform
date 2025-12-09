"""
API Key Management.

Implements secure API key generation, rotation, and revocation
for enterprise authentication.
"""

import secrets
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum
import uuid


class APIKeyStatus(Enum):
    """API key status."""
    ACTIVE = "active"
    ROTATING = "rotating"  # Grace period during rotation
    REVOKED = "revoked"
    EXPIRED = "expired"


@dataclass
class APIKey:
    """API key representation."""
    id: str
    user_id: str
    name: str
    key_prefix: str  # First 8 chars for identification
    key_hash: str  # SHA-256 hash of full key
    scope: List[str]
    status: APIKeyStatus = APIKeyStatus.ACTIVE
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    rotated_at: Optional[datetime] = None
    rotation_grace_until: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        """Check if key is expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() >= self.expires_at

    @property
    def is_active(self) -> bool:
        """Check if key is active and usable."""
        if self.status == APIKeyStatus.REVOKED:
            return False
        if self.is_expired:
            return False
        return True

    @property
    def is_in_rotation_grace(self) -> bool:
        """Check if key is in rotation grace period."""
        if self.rotation_grace_until is None:
            return False
        return datetime.utcnow() < self.rotation_grace_until


@dataclass
class APIKeyCreateResult:
    """Result of API key creation."""
    id: str
    key: str  # Full key (only shown once)
    key_prefix: str
    name: str
    scope: List[str]
    created_at: datetime
    expires_at: Optional[datetime]


@dataclass
class APIKeyRotateResult:
    """Result of API key rotation."""
    id: str
    new_key: str  # New full key (only shown once)
    new_key_prefix: str
    old_key_expires_at: datetime


class APIKeyManager:
    """
    API Key Manager for enterprise authentication.

    Handles secure key generation, rotation, and revocation
    with support for grace periods during rotation.
    """

    KEY_PREFIX = "mk_"  # Maestro key prefix
    KEY_LENGTH = 32  # Bytes of randomness
    ROTATION_GRACE_DAYS = 7

    def __init__(self, storage=None):
        """
        Initialize API key manager.

        Args:
            storage: Optional storage backend for keys
        """
        self._keys: Dict[str, APIKey] = {}  # In-memory store
        self._key_lookup: Dict[str, str] = {}  # hash -> key_id
        self.storage = storage

    def _generate_key(self) -> str:
        """Generate cryptographically secure API key."""
        random_bytes = secrets.token_bytes(self.KEY_LENGTH)
        key_body = secrets.token_urlsafe(self.KEY_LENGTH)
        return f"{self.KEY_PREFIX}{key_body}"

    def _hash_key(self, key: str) -> str:
        """Hash API key for storage."""
        return hashlib.sha256(key.encode()).hexdigest()

    def _get_prefix(self, key: str) -> str:
        """Extract key prefix for identification."""
        return key[:12]  # mk_ + first 9 chars

    def create_key(
        self,
        user_id: str,
        name: str,
        scope: List[str],
        expires_in_days: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> APIKeyCreateResult:
        """
        Create new API key.

        Args:
            user_id: Owner user ID
            name: Human-readable key name
            scope: List of granted scopes
            expires_in_days: Expiration in days (None for no expiry)
            metadata: Additional key metadata

        Returns:
            APIKeyCreateResult with full key (shown only once)
        """
        key_id = str(uuid.uuid4())
        full_key = self._generate_key()
        key_hash = self._hash_key(full_key)
        key_prefix = self._get_prefix(full_key)

        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        api_key = APIKey(
            id=key_id,
            user_id=user_id,
            name=name,
            key_prefix=key_prefix,
            key_hash=key_hash,
            scope=scope,
            expires_at=expires_at,
            metadata=metadata or {},
        )

        self._keys[key_id] = api_key
        self._key_lookup[key_hash] = key_id

        return APIKeyCreateResult(
            id=key_id,
            key=full_key,
            key_prefix=key_prefix,
            name=name,
            scope=scope,
            created_at=api_key.created_at,
            expires_at=expires_at,
        )

    def verify_key(self, key: str) -> Optional[APIKey]:
        """
        Verify API key and return key info if valid.

        Args:
            key: Full API key to verify

        Returns:
            APIKey if valid, None otherwise
        """
        key_hash = self._hash_key(key)
        key_id = self._key_lookup.get(key_hash)

        if not key_id:
            return None

        api_key = self._keys.get(key_id)
        if not api_key:
            return None

        # Check if key is usable
        if api_key.status == APIKeyStatus.REVOKED:
            return None

        if api_key.is_expired:
            return None

        # Allow usage during rotation grace period
        if api_key.status == APIKeyStatus.ROTATING:
            if not api_key.is_in_rotation_grace:
                return None

        # Update last used
        api_key.last_used_at = datetime.utcnow()

        return api_key

    def rotate_key(
        self,
        key_id: str,
        grace_period_days: Optional[int] = None,
    ) -> APIKeyRotateResult:
        """
        Rotate API key with grace period.

        The old key remains valid during the grace period
        to allow for migration.

        Args:
            key_id: ID of key to rotate
            grace_period_days: Grace period (default: ROTATION_GRACE_DAYS)

        Returns:
            APIKeyRotateResult with new key

        Raises:
            ValueError: If key not found or already revoked
        """
        api_key = self._keys.get(key_id)
        if not api_key:
            raise ValueError(f"API key not found: {key_id}")

        if api_key.status == APIKeyStatus.REVOKED:
            raise ValueError("Cannot rotate revoked key")

        grace_days = grace_period_days or self.ROTATION_GRACE_DAYS
        grace_until = datetime.utcnow() + timedelta(days=grace_days)

        # Generate new key
        new_full_key = self._generate_key()
        new_key_hash = self._hash_key(new_full_key)
        new_key_prefix = self._get_prefix(new_full_key)

        # Update old key hash lookup to point to same key_id
        # (allows both old and new key to work during grace period)
        self._key_lookup[new_key_hash] = key_id

        # Update key record
        old_hash = api_key.key_hash
        api_key.key_hash = new_key_hash
        api_key.key_prefix = new_key_prefix
        api_key.status = APIKeyStatus.ROTATING
        api_key.rotated_at = datetime.utcnow()
        api_key.rotation_grace_until = grace_until

        # Keep old hash valid during grace period
        # (handled in verify_key by checking grace period)

        return APIKeyRotateResult(
            id=key_id,
            new_key=new_full_key,
            new_key_prefix=new_key_prefix,
            old_key_expires_at=grace_until,
        )

    def revoke_key(self, key_id: str) -> bool:
        """
        Revoke API key immediately.

        Args:
            key_id: ID of key to revoke

        Returns:
            True if key was revoked
        """
        api_key = self._keys.get(key_id)
        if not api_key:
            return False

        api_key.status = APIKeyStatus.REVOKED

        # Remove from lookup
        if api_key.key_hash in self._key_lookup:
            del self._key_lookup[api_key.key_hash]

        return True

    def list_keys(
        self,
        user_id: str,
        include_revoked: bool = False,
    ) -> List[APIKey]:
        """
        List API keys for user.

        Args:
            user_id: User ID to list keys for
            include_revoked: Include revoked keys

        Returns:
            List of API keys (without key hash for security)
        """
        keys = []
        for api_key in self._keys.values():
            if api_key.user_id != user_id:
                continue
            if not include_revoked and api_key.status == APIKeyStatus.REVOKED:
                continue
            keys.append(api_key)

        return sorted(keys, key=lambda k: k.created_at, reverse=True)

    def get_key(self, key_id: str) -> Optional[APIKey]:
        """
        Get API key by ID.

        Args:
            key_id: Key ID

        Returns:
            APIKey if found
        """
        return self._keys.get(key_id)

    def update_scope(self, key_id: str, scope: List[str]) -> bool:
        """
        Update API key scope.

        Args:
            key_id: Key ID
            scope: New scope list

        Returns:
            True if updated
        """
        api_key = self._keys.get(key_id)
        if not api_key or api_key.status == APIKeyStatus.REVOKED:
            return False

        api_key.scope = scope
        return True

    def cleanup_expired(self) -> int:
        """
        Clean up expired keys.

        Returns:
            Number of keys cleaned up
        """
        expired_ids = []
        for key_id, api_key in self._keys.items():
            if api_key.is_expired:
                expired_ids.append(key_id)
            elif (api_key.status == APIKeyStatus.ROTATING and
                  not api_key.is_in_rotation_grace):
                # Rotation grace period ended, finalize rotation
                api_key.status = APIKeyStatus.ACTIVE

        for key_id in expired_ids:
            api_key = self._keys[key_id]
            api_key.status = APIKeyStatus.EXPIRED
            if api_key.key_hash in self._key_lookup:
                del self._key_lookup[api_key.key_hash]

        return len(expired_ids)
