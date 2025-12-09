"""
Secret Management for Environments.

Handles secure storage and rotation of secrets.
"""

import hashlib
import uuid
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional


class SecretType(str, Enum):
    """Types of secrets."""
    API_KEY = "api_key"
    DATABASE = "database"
    CERTIFICATE = "certificate"
    SSH_KEY = "ssh_key"
    TOKEN = "token"
    PASSWORD = "password"
    GENERIC = "generic"


class RotationStatus(str, Enum):
    """Secret rotation status."""
    ACTIVE = "active"
    ROTATING = "rotating"
    ROTATED = "rotated"
    EXPIRED = "expired"
    REVOKED = "revoked"


@dataclass
class Secret:
    """Secure secret representation."""
    id: str
    name: str
    secret_type: SecretType
    environment: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    last_rotated: Optional[datetime] = None
    version: int = 1
    status: RotationStatus = RotationStatus.ACTIVE
    metadata: dict[str, Any] = field(default_factory=dict)
    _value: str = field(default="", repr=False)

    @property
    def value(self) -> str:
        """Get secret value."""
        return self._value

    @value.setter
    def value(self, new_value: str) -> None:
        """Set secret value."""
        self._value = new_value
        self.version += 1

    def is_expired(self) -> bool:
        """Check if secret is expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def hash(self) -> str:
        """Get hash of secret value for comparison."""
        return hashlib.sha256(self._value.encode()).hexdigest()

    def to_dict(self, include_value: bool = False) -> dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "id": self.id,
            "name": self.name,
            "type": self.secret_type.value,
            "environment": self.environment,
            "version": self.version,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_rotated": self.last_rotated.isoformat() if self.last_rotated else None
        }
        if include_value:
            result["value_hash"] = self.hash()
        return result


@dataclass
class SecretRotation:
    """Secret rotation schedule and policy."""
    secret_id: str
    interval_days: int
    auto_rotate: bool = False
    rotation_function: Optional[str] = None
    notify_before_days: int = 7

    def next_rotation(self, last_rotated: Optional[datetime] = None) -> datetime:
        """Calculate next rotation date."""
        base = last_rotated or datetime.utcnow()
        return base + timedelta(days=self.interval_days)

    def should_notify(self, last_rotated: Optional[datetime] = None) -> bool:
        """Check if rotation notification should be sent."""
        next_rot = self.next_rotation(last_rotated)
        notify_date = next_rot - timedelta(days=self.notify_before_days)
        return datetime.utcnow() >= notify_date


class SecretManager:
    """Manages secrets for environments."""

    def __init__(self, encryption_key: Optional[str] = None):
        self._secrets: dict[str, Secret] = {}
        self._rotations: dict[str, SecretRotation] = {}
        self._rotation_functions: dict[str, Callable] = {}
        self._encryption_key = encryption_key or "default-key"

    async def create(
        self,
        name: str,
        value: str,
        secret_type: SecretType,
        environment: str,
        expires_in_days: Optional[int] = None
    ) -> Secret:
        """Create a new secret."""
        secret = Secret(
            id=str(uuid.uuid4()),
            name=name,
            secret_type=secret_type,
            environment=environment,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=expires_in_days) if expires_in_days else None
        )
        secret._value = self._encrypt(value)
        self._secrets[secret.id] = secret
        return secret

    async def get(self, secret_id: str) -> Optional[Secret]:
        """Get secret by ID."""
        return self._secrets.get(secret_id)

    async def get_by_name(self, name: str, environment: str) -> Optional[Secret]:
        """Get secret by name and environment."""
        for secret in self._secrets.values():
            if secret.name == name and secret.environment == environment:
                return secret
        return None

    async def get_value(self, secret_id: str) -> Optional[str]:
        """Get decrypted secret value."""
        secret = self._secrets.get(secret_id)
        if secret:
            return self._decrypt(secret._value)
        return None

    async def update(self, secret_id: str, new_value: str) -> Optional[Secret]:
        """Update secret value."""
        secret = self._secrets.get(secret_id)
        if secret:
            secret._value = self._encrypt(new_value)
            secret.version += 1
            return secret
        return None

    async def delete(self, secret_id: str) -> bool:
        """Delete secret."""
        if secret_id in self._secrets:
            del self._secrets[secret_id]
            self._rotations.pop(secret_id, None)
            return True
        return False

    async def rotate(self, secret_id: str, new_value: Optional[str] = None) -> Optional[Secret]:
        """Rotate secret to new value."""
        secret = self._secrets.get(secret_id)
        if not secret:
            return None

        secret.status = RotationStatus.ROTATING

        if new_value is None:
            rotation = self._rotations.get(secret_id)
            if rotation and rotation.rotation_function:
                func = self._rotation_functions.get(rotation.rotation_function)
                if func:
                    new_value = await func(secret)

        if new_value:
            secret._value = self._encrypt(new_value)
            secret.version += 1
            secret.last_rotated = datetime.utcnow()
            secret.status = RotationStatus.ACTIVE
        else:
            secret.status = RotationStatus.ACTIVE

        return secret

    def set_rotation_policy(self, secret_id: str, policy: SecretRotation) -> None:
        """Set rotation policy for secret."""
        self._rotations[secret_id] = policy

    def register_rotation_function(self, name: str, func: Callable) -> None:
        """Register custom rotation function."""
        self._rotation_functions[name] = func

    async def check_expirations(self) -> list[Secret]:
        """Check for expiring secrets."""
        expiring = []
        for secret in self._secrets.values():
            if secret.is_expired():
                secret.status = RotationStatus.EXPIRED
                expiring.append(secret)
            elif secret.expires_at:
                days_until = (secret.expires_at - datetime.utcnow()).days
                if days_until <= 7:
                    expiring.append(secret)
        return expiring

    async def list(self, environment: Optional[str] = None) -> list[Secret]:
        """List all secrets, optionally filtered by environment."""
        if environment:
            return [s for s in self._secrets.values() if s.environment == environment]
        return list(self._secrets.values())

    def _encrypt(self, value: str) -> str:
        """Encrypt value (simplified - use proper encryption in production)."""
        return value

    def _decrypt(self, value: str) -> str:
        """Decrypt value (simplified - use proper encryption in production)."""
        return value

    async def revoke(self, secret_id: str) -> Optional[Secret]:
        """Revoke a secret."""
        secret = self._secrets.get(secret_id)
        if secret:
            secret.status = RotationStatus.REVOKED
            secret._value = ""
            return secret
        return None
