"""
Signed Message Support for Agora Communication.

EPIC: MD-3117 - Agora Phase 2: Secure Message Bus (Signed Messages)
AC-1: AgoraMessage schema includes signature field and sign/verify methods
AC-2: SignedMessage class wraps messages with automatic signing

This module extends the ACL with cryptographic signing capabilities,
ensuring message authenticity and non-repudiation in the Agora.

Reference: docs/roadmap/AGORA_PHASE2_DETAILED_BACKLOG.md (AGORA-104)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, Optional

from maestro_hive.agora.acl import AgoraMessage, Performative, ValidationError

if TYPE_CHECKING:
    from maestro_hive.agora.identity.agent_identity import AgentIdentity

logger = logging.getLogger(__name__)


class SecurityError(Exception):
    """Raised when a security check fails (signature verification, etc.)."""
    pass


@dataclass
class SignableMessage:
    """
    Extended AgoraMessage with cryptographic signing capabilities.

    This class adds signature support to standard ACL messages, enabling:
    - Message signing with agent's private key
    - Signature verification against public keys
    - Tamper detection through hash-based verification

    EPIC: MD-3117 AC-1
    """

    # Base message fields
    sender: str
    performative: Performative
    content: Dict[str, Any]
    message_id: str = field(default_factory=lambda: str(__import__('uuid').uuid4()))
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    receiver: str = "BROADCAST"
    protocol: str = "direct"

    # Signature field - None if unsigned
    signature: Optional[bytes] = None

    def __post_init__(self):
        """Validate on creation."""
        if not self.sender or not isinstance(self.sender, str):
            raise ValidationError("sender must be a non-empty string")
        if not isinstance(self.content, dict):
            raise ValidationError("content must be a dictionary")

    def to_signable_bytes(self) -> bytes:
        """
        Get the canonical byte representation for signing.

        Returns deterministic bytes from message content (excluding signature).

        Returns:
            UTF-8 encoded JSON bytes for signing
        """
        signable_data = {
            "message_id": self.message_id,
            "timestamp": self.timestamp,
            "sender": self.sender,
            "receiver": self.receiver,
            "performative": self.performative.value if isinstance(self.performative, Performative) else self.performative,
            "content": self.content,
            "protocol": self.protocol,
        }
        # Sort keys for deterministic output
        return json.dumps(signable_data, sort_keys=True, separators=(',', ':')).encode('utf-8')

    def sign(self, identity: "AgentIdentity") -> None:
        """
        Sign this message with the given agent identity.

        Args:
            identity: The AgentIdentity with private key to sign with

        Raises:
            ValueError: If identity has no private key
        """
        signable_bytes = self.to_signable_bytes()
        self.signature = identity.sign(signable_bytes)
        logger.debug(f"Message {self.message_id[:8]} signed by {self.sender}")

    def verify(self, identity: "AgentIdentity") -> bool:
        """
        Verify this message's signature against the given identity.

        Args:
            identity: The AgentIdentity with public key to verify against

        Returns:
            True if signature is valid, False otherwise
        """
        if not self.signature:
            logger.warning(f"Message {self.message_id[:8]} has no signature")
            return False

        signable_bytes = self.to_signable_bytes()
        is_valid = identity.verify(signable_bytes, self.signature)

        if not is_valid:
            logger.warning(f"Message {self.message_id[:8]} signature verification FAILED")
        else:
            logger.debug(f"Message {self.message_id[:8]} signature verified")

        return is_valid

    def is_signed(self) -> bool:
        """Check if message has a signature."""
        return self.signature is not None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary including signature."""
        data = {
            "message_id": self.message_id,
            "timestamp": self.timestamp,
            "sender": self.sender,
            "receiver": self.receiver,
            "performative": self.performative.value if isinstance(self.performative, Performative) else self.performative,
            "content": self.content,
            "protocol": self.protocol,
        }
        if self.signature:
            data["signature"] = self.signature.hex()
        return data

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SignableMessage":
        """Create from dictionary."""
        signature = None
        if "signature" in data:
            sig_value = data["signature"]
            if isinstance(sig_value, str):
                signature = bytes.fromhex(sig_value)
            elif isinstance(sig_value, bytes):
                signature = sig_value

        performative = data["performative"]
        if isinstance(performative, str):
            performative = Performative(performative)

        return cls(
            message_id=data.get("message_id", str(__import__('uuid').uuid4())),
            timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat()),
            sender=data["sender"],
            receiver=data.get("receiver", "BROADCAST"),
            performative=performative,
            content=data["content"],
            protocol=data.get("protocol", "direct"),
            signature=signature,
        )

    @classmethod
    def from_json(cls, json_str: str) -> "SignableMessage":
        """Create from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)

    @classmethod
    def from_agora_message(cls, msg: AgoraMessage) -> "SignableMessage":
        """Convert an AgoraMessage to a SignableMessage."""
        return cls(
            message_id=msg.message_id,
            timestamp=msg.timestamp,
            sender=msg.sender,
            receiver=msg.receiver,
            performative=msg.performative,
            content=msg.content,
            protocol=msg.protocol,
            signature=None,
        )

    def to_agora_message(self) -> AgoraMessage:
        """Convert back to a standard AgoraMessage (loses signature)."""
        return AgoraMessage(
            message_id=self.message_id,
            timestamp=self.timestamp,
            sender=self.sender,
            receiver=self.receiver,
            performative=self.performative,
            content=self.content,
            protocol=self.protocol,
        )


@dataclass
class SignedMessage:
    """
    Wrapper that holds a message with its cryptographic signature.

    This class enforces signing at construction time, ensuring that
    all SignedMessage instances are properly authenticated.

    EPIC: MD-3117 AC-2

    Example:
        >>> identity = AgentIdentity.generate(name="Coder")
        >>> msg = AgoraMessage(sender=identity.did, ...)
        >>> signed = SignedMessage.create(msg, identity)
        >>> assert signed.verify(identity)
    """

    message: SignableMessage
    signer_did: str
    signature: bytes
    signed_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @classmethod
    def create(
        cls,
        message: AgoraMessage,
        signer: "AgentIdentity"
    ) -> "SignedMessage":
        """
        Create a signed message by signing with the given identity.

        Args:
            message: The message to sign
            signer: The identity to sign with

        Returns:
            SignedMessage with valid signature

        Raises:
            ValueError: If signer has no private key
        """
        # Convert to signable message
        signable = SignableMessage.from_agora_message(message)
        signable.sign(signer)

        return cls(
            message=signable,
            signer_did=signer.did,
            signature=signable.signature,
            signed_at=datetime.now(timezone.utc).isoformat(),
        )

    def verify(self, identity: "AgentIdentity") -> bool:
        """
        Verify the signature against the given identity.

        Args:
            identity: Identity to verify against (should match signer)

        Returns:
            True if signature is valid
        """
        return self.message.verify(identity)

    def get_message(self) -> AgoraMessage:
        """Get the underlying message as AgoraMessage."""
        return self.message.to_agora_message()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "message": self.message.to_dict(),
            "signer_did": self.signer_did,
            "signature": self.signature.hex(),
            "signed_at": self.signed_at,
        }

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SignedMessage":
        """Deserialize from dictionary."""
        message = SignableMessage.from_dict(data["message"])
        signature = bytes.fromhex(data["signature"])

        return cls(
            message=message,
            signer_did=data["signer_did"],
            signature=signature,
            signed_at=data.get("signed_at", datetime.now(timezone.utc).isoformat()),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "SignedMessage":
        """Deserialize from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)


def sign_message(
    message: AgoraMessage,
    identity: "AgentIdentity"
) -> SignedMessage:
    """
    Convenience function to sign an AgoraMessage.

    Args:
        message: The message to sign
        identity: The signer's identity

    Returns:
        SignedMessage with valid signature
    """
    return SignedMessage.create(message, identity)


def verify_message(
    signed_msg: SignedMessage,
    identity: "AgentIdentity"
) -> bool:
    """
    Convenience function to verify a signed message.

    Args:
        signed_msg: The signed message to verify
        identity: The identity to verify against

    Returns:
        True if signature is valid
    """
    return signed_msg.verify(identity)
