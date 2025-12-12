"""
Agent Identity Module - Self-Sovereign Identity for Agents

Implements Decentralized Identifiers (DIDs) and cryptographic identity
for agents in the Agora architecture.

EPIC: MD-3104 (Agora Phase 2: Identity & Trust)
AC-1: Implement AgentIdentity class with DID generation
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

# Use cryptography library for Ed25519 operations
try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
        Ed25519PublicKey,
    )
    from cryptography.hazmat.primitives import serialization
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False


class KeyAlgorithm(str, Enum):
    """Supported key algorithms for agent identity."""
    ED25519 = "ed25519"
    HMAC_SHA256 = "hmac-sha256"


@dataclass
class IdentityConfig:
    """Configuration for agent identity creation."""
    key_algorithm: str = "ed25519"
    trust_decay_days: int = 30
    default_credential_expiry_days: int = 365
    storage_path: Optional[str] = None

    @classmethod
    def from_env(cls) -> "IdentityConfig":
        """Load configuration from environment variables."""
        return cls(
            key_algorithm=os.environ.get("SSI_KEY_ALGORITHM", "ed25519"),
            trust_decay_days=int(os.environ.get("TRUST_DECAY_DAYS", "30")),
            default_credential_expiry_days=int(
                os.environ.get("CREDENTIAL_DEFAULT_EXPIRY_DAYS", "365")
            ),
            storage_path=os.environ.get("IDENTITY_STORAGE_PATH"),
        )


@dataclass
class DIDDocument:
    """
    DID Document containing agent identity information.

    Based on W3C DID Core specification.
    """
    did: str
    public_key_hex: str
    key_algorithm: str
    created_at: str
    capabilities: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "@context": "https://www.w3.org/ns/did/v1",
            "id": self.did,
            "verificationMethod": [
                {
                    "id": f"{self.did}#key-1",
                    "type": f"{self.key_algorithm}VerificationKey2020",
                    "controller": self.did,
                    "publicKeyHex": self.public_key_hex,
                }
            ],
            "authentication": [f"{self.did}#key-1"],
            "created": self.created_at,
            "capabilities": self.capabilities,
            "metadata": self.metadata,
        }

    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DIDDocument":
        """Create from dictionary representation."""
        verification_method = data.get("verificationMethod", [{}])[0]
        return cls(
            did=data["id"],
            public_key_hex=verification_method.get("publicKeyHex", ""),
            key_algorithm=verification_method.get("type", "").replace(
                "VerificationKey2020", ""
            ),
            created_at=data.get("created", ""),
            capabilities=data.get("capabilities", []),
            metadata=data.get("metadata", {}),
        )


class AgentIdentity:
    """
    Self-Sovereign Identity for an agent.

    Provides:
    - Unique DID (Decentralized Identifier) generation
    - Ed25519 key pair for signing/verification
    - Signature generation and verification
    - DID Document serialization

    Example:
        >>> identity = AgentIdentity.create(
        ...     name="backend_developer",
        ...     capabilities=["code_generation", "testing"]
        ... )
        >>> message = b"Hello, World!"
        >>> signature = identity.sign(message)
        >>> assert identity.verify(message, signature)
    """

    def __init__(
        self,
        did: str,
        name: str,
        private_key_bytes: Optional[bytes] = None,
        public_key_bytes: Optional[bytes] = None,
        capabilities: Optional[List[str]] = None,
        created_at: Optional[datetime] = None,
        config: Optional[IdentityConfig] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize an AgentIdentity.

        Args:
            did: Decentralized Identifier
            name: Human-readable agent name
            private_key_bytes: Optional private key (None for verification-only)
            public_key_bytes: Public key bytes
            capabilities: List of agent capabilities
            created_at: Creation timestamp
            config: Identity configuration
            metadata: Additional metadata
        """
        self.did = did
        self.name = name
        self._private_key_bytes = private_key_bytes
        self._public_key_bytes = public_key_bytes
        self.capabilities = capabilities or []
        self.created_at = created_at or datetime.now(timezone.utc)
        self.config = config or IdentityConfig()
        self.metadata = metadata or {}

        # Initialize cryptographic keys
        self._private_key: Optional[Ed25519PrivateKey] = None
        self._public_key: Optional[Ed25519PublicKey] = None
        self._init_keys()

    def _init_keys(self) -> None:
        """Initialize cryptographic key objects from bytes."""
        if not HAS_CRYPTOGRAPHY:
            return

        if self._private_key_bytes:
            self._private_key = Ed25519PrivateKey.from_private_bytes(
                self._private_key_bytes
            )
            self._public_key = self._private_key.public_key()
        elif self._public_key_bytes:
            self._public_key = Ed25519PublicKey.from_public_bytes(
                self._public_key_bytes
            )

    @classmethod
    def create(
        cls,
        name: str,
        capabilities: Optional[List[str]] = None,
        config: Optional[IdentityConfig] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "AgentIdentity":
        """
        Create a new AgentIdentity with generated keys.

        Args:
            name: Human-readable agent name
            capabilities: List of agent capabilities
            config: Identity configuration
            metadata: Additional metadata

        Returns:
            New AgentIdentity with generated DID and keys
        """
        config = config or IdentityConfig()

        # Generate unique identifier
        unique_id = str(uuid.uuid4())

        # Create DID using method "agora"
        did = f"did:agora:{unique_id}"

        # Generate Ed25519 key pair
        if HAS_CRYPTOGRAPHY and config.key_algorithm == "ed25519":
            private_key = Ed25519PrivateKey.generate()
            private_key_bytes = private_key.private_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PrivateFormat.Raw,
                encryption_algorithm=serialization.NoEncryption(),
            )
            public_key_bytes = private_key.public_key().public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            )
        else:
            # Fallback: use random bytes for HMAC-based signing
            private_key_bytes = os.urandom(32)
            public_key_bytes = hashlib.sha256(private_key_bytes).digest()

        return cls(
            did=did,
            name=name,
            private_key_bytes=private_key_bytes,
            public_key_bytes=public_key_bytes,
            capabilities=capabilities,
            config=config,
            metadata=metadata,
        )

    @classmethod
    def from_public_key(
        cls,
        did: str,
        name: str,
        public_key_hex: str,
        capabilities: Optional[List[str]] = None,
    ) -> "AgentIdentity":
        """
        Create an identity for verification only (no private key).

        Args:
            did: Decentralized Identifier
            name: Human-readable agent name
            public_key_hex: Hex-encoded public key
            capabilities: List of agent capabilities

        Returns:
            AgentIdentity for verification only
        """
        public_key_bytes = bytes.fromhex(public_key_hex)
        return cls(
            did=did,
            name=name,
            public_key_bytes=public_key_bytes,
            capabilities=capabilities,
        )

    @property
    def public_key(self) -> Optional[bytes]:
        """Get the public key bytes."""
        return self._public_key_bytes

    @property
    def public_key_hex(self) -> str:
        """Get the public key as hex string."""
        if self._public_key_bytes:
            return self._public_key_bytes.hex()
        return ""

    @property
    def has_private_key(self) -> bool:
        """Check if this identity has a private key (can sign)."""
        return self._private_key_bytes is not None

    def sign(self, message: bytes) -> bytes:
        """
        Sign a message using the agent's private key.

        Args:
            message: Message bytes to sign

        Returns:
            Signature bytes

        Raises:
            ValueError: If no private key is available
        """
        if not self._private_key_bytes:
            raise ValueError("Cannot sign without private key")

        if HAS_CRYPTOGRAPHY and self._private_key:
            return self._private_key.sign(message)
        else:
            # Fallback: HMAC-SHA256
            return hmac.new(
                self._private_key_bytes,
                message,
                hashlib.sha256,
            ).digest()

    def verify(self, message: bytes, signature: bytes) -> bool:
        """
        Verify a signature using the agent's public key.

        Args:
            message: Original message bytes
            signature: Signature to verify

        Returns:
            True if signature is valid, False otherwise
        """
        if HAS_CRYPTOGRAPHY and self._public_key:
            try:
                self._public_key.verify(signature, message)
                return True
            except Exception:
                return False
        else:
            # Fallback: HMAC-SHA256 verification
            if self._private_key_bytes:
                expected = hmac.new(
                    self._private_key_bytes,
                    message,
                    hashlib.sha256,
                ).digest()
                return hmac.compare_digest(signature, expected)
            return False

    def get_did_document(self) -> DIDDocument:
        """Get the DID Document for this identity."""
        return DIDDocument(
            did=self.did,
            public_key_hex=self.public_key_hex,
            key_algorithm=self.config.key_algorithm,
            created_at=self.created_at.isoformat(),
            capabilities=self.capabilities,
            metadata=self.metadata,
        )

    def to_dict(self, include_private: bool = False) -> Dict[str, Any]:
        """
        Serialize to dictionary.

        Args:
            include_private: If True, include private key (for storage)

        Returns:
            Dictionary representation
        """
        data = {
            "did": self.did,
            "name": self.name,
            "public_key_hex": self.public_key_hex,
            "capabilities": self.capabilities,
            "created_at": self.created_at.isoformat(),
            "config": {
                "key_algorithm": self.config.key_algorithm,
                "trust_decay_days": self.config.trust_decay_days,
                "default_credential_expiry_days": self.config.default_credential_expiry_days,
            },
            "metadata": self.metadata,
        }
        if include_private and self._private_key_bytes:
            data["private_key_hex"] = self._private_key_bytes.hex()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentIdentity":
        """Create from dictionary representation."""
        config_data = data.get("config", {})
        config = IdentityConfig(
            key_algorithm=config_data.get("key_algorithm", "ed25519"),
            trust_decay_days=config_data.get("trust_decay_days", 30),
            default_credential_expiry_days=config_data.get(
                "default_credential_expiry_days", 365
            ),
        )

        private_key_bytes = None
        if "private_key_hex" in data:
            private_key_bytes = bytes.fromhex(data["private_key_hex"])

        public_key_bytes = None
        if "public_key_hex" in data:
            public_key_bytes = bytes.fromhex(data["public_key_hex"])

        created_at = None
        if "created_at" in data:
            created_at = datetime.fromisoformat(data["created_at"])

        return cls(
            did=data["did"],
            name=data["name"],
            private_key_bytes=private_key_bytes,
            public_key_bytes=public_key_bytes,
            capabilities=data.get("capabilities", []),
            created_at=created_at,
            config=config,
            metadata=data.get("metadata", {}),
        )

    def __repr__(self) -> str:
        return f"AgentIdentity(did={self.did!r}, name={self.name!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, AgentIdentity):
            return False
        return self.did == other.did

    def __hash__(self) -> int:
        return hash(self.did)
