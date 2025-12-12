"""
Agent Identity Module (MD-3118/MD-3203)

Implements cryptographic identity for agents using Ed25519 signatures.
Every agent has a cryptographic signature for their actions, ensuring
non-repudiation and verifiable attribution.

From policy.yaml:
- Each agent has Ed25519 keypair for signing actions
- All governance actions are cryptographically signed
- Signatures are verified for audit and accountability
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Try to import cryptography library for Ed25519
try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ed25519
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    logger.warning("cryptography library not available. Using fallback identity implementation.")


@dataclass
class AgentIdentity:
    """
    Cryptographic identity for an agent.

    Attributes:
        agent_id: Unique identifier for the agent
        public_key: Ed25519 public key (base64 encoded)
        created_at: When the identity was created
        fingerprint: SHA256 fingerprint of public key
    """

    agent_id: str
    public_key: str  # Base64 encoded
    created_at: datetime = field(default_factory=datetime.utcnow)
    fingerprint: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.fingerprint and self.public_key:
            # Calculate fingerprint from public key
            key_bytes = base64.b64decode(self.public_key)
            self.fingerprint = hashlib.sha256(key_bytes).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "agent_id": self.agent_id,
            "public_key": self.public_key,
            "created_at": self.created_at.isoformat(),
            "fingerprint": self.fingerprint,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentIdentity":
        """Deserialize from dictionary."""
        return cls(
            agent_id=data["agent_id"],
            public_key=data["public_key"],
            created_at=datetime.fromisoformat(data["created_at"]) if isinstance(data.get("created_at"), str) else datetime.utcnow(),
            fingerprint=data.get("fingerprint", ""),
            metadata=data.get("metadata", {}),
        )


@dataclass
class SignedAction:
    """
    A cryptographically signed action by an agent.

    Attributes:
        action_id: Unique identifier for the action
        agent_id: Agent performing the action
        action_type: Type of action (tool call, etc.)
        payload: Action details
        timestamp: When the action occurred
        signature: Ed25519 signature (base64 encoded)
    """

    action_id: str
    agent_id: str
    action_type: str
    payload: Dict[str, Any]
    timestamp: datetime
    signature: str  # Base64 encoded

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "action_id": self.action_id,
            "agent_id": self.agent_id,
            "action_type": self.action_type,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
            "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SignedAction":
        """Deserialize from dictionary."""
        return cls(
            action_id=data["action_id"],
            agent_id=data["agent_id"],
            action_type=data["action_type"],
            payload=data["payload"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            signature=data["signature"],
        )

    def get_signing_payload(self) -> bytes:
        """Get the canonical bytes to sign/verify."""
        canonical = {
            "action_id": self.action_id,
            "agent_id": self.agent_id,
            "action_type": self.action_type,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
        }
        return json.dumps(canonical, sort_keys=True).encode("utf-8")


class IdentityManager:
    """
    Identity Manager - Manages Agent Cryptographic Identities.

    MD-3118 Implementation: Ensures every agent has a cryptographic
    signature (Ed25519) for their actions.

    Features:
    - Ed25519 keypair generation per agent
    - Action signing and verification
    - Persistent identity storage
    - Key rotation support
    """

    def __init__(
        self,
        storage_path: Optional[str] = None,
        auto_persist: bool = True,
    ):
        """
        Initialize the identity manager.

        Args:
            storage_path: Path for persistent storage
            auto_persist: Whether to auto-save on changes
        """
        self._storage_path = storage_path or "/tmp/agent_identities.json"
        self._auto_persist = auto_persist
        self._lock = threading.RLock()

        # Identity storage: agent_id -> (identity, private_key_bytes)
        self._identities: Dict[str, AgentIdentity] = {}
        self._private_keys: Dict[str, bytes] = {}  # In production, use HSM/Vault

        # Load existing identities
        self._load_from_storage()

        logger.info(f"IdentityManager initialized (crypto={CRYPTO_AVAILABLE}, storage={self._storage_path})")

    def create_identity(self, agent_id: str, metadata: Optional[Dict[str, Any]] = None) -> AgentIdentity:
        """
        Create a new cryptographic identity for an agent.

        Args:
            agent_id: Unique identifier for the agent
            metadata: Optional metadata to attach

        Returns:
            The created AgentIdentity
        """
        with self._lock:
            # Check if already exists
            if agent_id in self._identities:
                logger.debug(f"Identity already exists for {agent_id}")
                return self._identities[agent_id]

            # Generate Ed25519 keypair
            if CRYPTO_AVAILABLE:
                private_key = ed25519.Ed25519PrivateKey.generate()
                public_key = private_key.public_key()

                # Serialize keys
                private_bytes = private_key.private_bytes(
                    encoding=serialization.Encoding.Raw,
                    format=serialization.PrivateFormat.Raw,
                    encryption_algorithm=serialization.NoEncryption(),
                )
                public_bytes = public_key.public_bytes(
                    encoding=serialization.Encoding.Raw,
                    format=serialization.PublicFormat.Raw,
                )
            else:
                # Fallback: Generate random bytes as placeholder
                private_bytes = os.urandom(32)
                public_bytes = os.urandom(32)

            # Create identity
            identity = AgentIdentity(
                agent_id=agent_id,
                public_key=base64.b64encode(public_bytes).decode("utf-8"),
                metadata=metadata or {},
            )

            # Store
            self._identities[agent_id] = identity
            self._private_keys[agent_id] = private_bytes

            # Persist
            if self._auto_persist:
                self._save_to_storage()

            logger.info(f"Created identity for {agent_id} (fingerprint: {identity.fingerprint})")
            return identity

    def get_identity(self, agent_id: str) -> Optional[AgentIdentity]:
        """Get an agent's identity."""
        with self._lock:
            return self._identities.get(agent_id)

    def sign_action(
        self,
        agent_id: str,
        action_type: str,
        payload: Dict[str, Any],
    ) -> SignedAction:
        """
        Sign an action with the agent's private key.

        Args:
            agent_id: Agent performing the action
            action_type: Type of action
            payload: Action details

        Returns:
            SignedAction with cryptographic signature

        Raises:
            ValueError: If agent has no identity
        """
        with self._lock:
            if agent_id not in self._identities:
                # Auto-create identity if doesn't exist
                self.create_identity(agent_id)

            private_bytes = self._private_keys[agent_id]

            # Create action
            action = SignedAction(
                action_id=self._generate_action_id(),
                agent_id=agent_id,
                action_type=action_type,
                payload=payload,
                timestamp=datetime.utcnow(),
                signature="",  # Will be filled below
            )

            # Sign
            signing_payload = action.get_signing_payload()

            if CRYPTO_AVAILABLE:
                private_key = ed25519.Ed25519PrivateKey.from_private_bytes(private_bytes)
                signature = private_key.sign(signing_payload)
            else:
                # Fallback: HMAC-SHA256 with private key as secret
                import hmac
                signature = hmac.new(private_bytes, signing_payload, hashlib.sha256).digest()

            action.signature = base64.b64encode(signature).decode("utf-8")

            logger.debug(f"Signed action {action.action_id} for {agent_id}")
            return action

    def verify_action(self, action: SignedAction) -> bool:
        """
        Verify an action's signature.

        Args:
            action: The signed action to verify

        Returns:
            True if signature is valid
        """
        with self._lock:
            identity = self._identities.get(action.agent_id)
            if identity is None:
                logger.warning(f"No identity found for {action.agent_id}")
                return False

            public_bytes = base64.b64decode(identity.public_key)
            signature = base64.b64decode(action.signature)
            signing_payload = action.get_signing_payload()

            if CRYPTO_AVAILABLE:
                try:
                    public_key = ed25519.Ed25519PublicKey.from_public_bytes(public_bytes)
                    public_key.verify(signature, signing_payload)
                    return True
                except Exception as e:
                    logger.warning(f"Signature verification failed: {e}")
                    return False
            else:
                # Fallback verification
                private_bytes = self._private_keys.get(action.agent_id)
                if private_bytes is None:
                    return False
                import hmac
                expected = hmac.new(private_bytes, signing_payload, hashlib.sha256).digest()
                return hmac.compare_digest(signature, expected)

    def rotate_key(self, agent_id: str) -> AgentIdentity:
        """
        Rotate an agent's keypair.

        Args:
            agent_id: Agent to rotate key for

        Returns:
            New identity with fresh keypair
        """
        with self._lock:
            old_identity = self._identities.pop(agent_id, None)
            self._private_keys.pop(agent_id, None)

            new_identity = self.create_identity(
                agent_id,
                metadata={
                    "rotated_from": old_identity.fingerprint if old_identity else None,
                    "rotation_time": datetime.utcnow().isoformat(),
                },
            )

            logger.info(f"Rotated key for {agent_id}")
            return new_identity

    def get_all_identities(self) -> List[AgentIdentity]:
        """Get all registered identities."""
        with self._lock:
            return list(self._identities.values())

    def _generate_action_id(self) -> str:
        """Generate a unique action ID."""
        import uuid
        return f"action_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"

    def _save_to_storage(self) -> None:
        """Save identities to persistent storage."""
        try:
            data = {
                "identities": {
                    agent_id: identity.to_dict()
                    for agent_id, identity in self._identities.items()
                },
                "private_keys": {
                    agent_id: base64.b64encode(key).decode("utf-8")
                    for agent_id, key in self._private_keys.items()
                },
                "saved_at": datetime.utcnow().isoformat(),
            }

            # Ensure directory exists
            Path(self._storage_path).parent.mkdir(parents=True, exist_ok=True)

            with open(self._storage_path, "w") as f:
                json.dump(data, f, indent=2)

            logger.debug(f"Saved {len(self._identities)} identities to {self._storage_path}")
        except Exception as e:
            logger.error(f"Failed to save identities: {e}")

    def _load_from_storage(self) -> None:
        """Load identities from persistent storage."""
        if not os.path.exists(self._storage_path):
            return

        try:
            with open(self._storage_path, "r") as f:
                data = json.load(f)

            for agent_id, identity_data in data.get("identities", {}).items():
                self._identities[agent_id] = AgentIdentity.from_dict(identity_data)

            for agent_id, key_b64 in data.get("private_keys", {}).items():
                self._private_keys[agent_id] = base64.b64decode(key_b64)

            logger.info(f"Loaded {len(self._identities)} identities from {self._storage_path}")
        except Exception as e:
            logger.error(f"Failed to load identities: {e}")

    def export_public_keys(self) -> Dict[str, str]:
        """Export all public keys for verification."""
        with self._lock:
            return {
                agent_id: identity.public_key
                for agent_id, identity in self._identities.items()
            }

    def get_stats(self) -> Dict[str, Any]:
        """Get identity manager statistics."""
        with self._lock:
            return {
                "total_identities": len(self._identities),
                "crypto_available": CRYPTO_AVAILABLE,
                "storage_path": self._storage_path,
                "identities": [
                    {
                        "agent_id": identity.agent_id,
                        "fingerprint": identity.fingerprint,
                        "created_at": identity.created_at.isoformat(),
                    }
                    for identity in self._identities.values()
                ],
            }
