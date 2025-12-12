"""
Identity Verification Module - Challenge-Response Authentication

Implements identity verification workflows for agent-to-agent
authentication in the Agora architecture.

EPIC: MD-3104 (Agora Phase 2: Identity & Trust)
AC-5: Add identity verification workflow for agent communication
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from .agent_identity import AgentIdentity
    from .trust_registry import TrustRegistry


class VerificationStatus(str, Enum):
    """Status of a verification attempt."""
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    EXPIRED = "expired"


@dataclass
class Challenge:
    """
    A verification challenge for agent authentication.

    The challenge must be signed by the target agent's private key
    to prove identity ownership.
    """
    challenge_id: str
    verifier_did: str
    target_did: str
    nonce: str
    created_at: datetime
    expires_at: datetime
    status: VerificationStatus = VerificationStatus.PENDING
    response: Optional[bytes] = None
    verified_at: Optional[datetime] = None

    @property
    def is_expired(self) -> bool:
        """Check if the challenge has expired."""
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def challenge_data(self) -> bytes:
        """Get the data to be signed."""
        return f"{self.challenge_id}:{self.nonce}:{self.target_did}".encode()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "challenge_id": self.challenge_id,
            "verifier_did": self.verifier_did,
            "target_did": self.target_did,
            "nonce": self.nonce,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "status": self.status.value,
            "response": self.response.hex() if self.response else None,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
        }


@dataclass
class VerificationResult:
    """Result of a verification attempt."""
    success: bool
    challenge_id: str
    target_did: str
    verifier_did: str
    status: VerificationStatus
    message: str
    verified_at: Optional[datetime] = None
    trust_level: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "challenge_id": self.challenge_id,
            "target_did": self.target_did,
            "verifier_did": self.verifier_did,
            "status": self.status.value,
            "message": self.message,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "trust_level": self.trust_level,
        }


class IdentityVerifier:
    """
    Verifies agent identities using challenge-response protocol.

    Flow:
    1. Verifier creates a challenge for target agent
    2. Target agent signs the challenge with their private key
    3. Verifier validates the signature using target's public key
    4. If valid, trust can be established

    Example:
        >>> verifier = IdentityVerifier(registry)
        >>> challenge = verifier.create_challenge(target_did="did:agora:123")
        >>> response = target_identity.sign(challenge.challenge_data)
        >>> result = verifier.verify_response(challenge.challenge_id, response)
        >>> if result.success:
        ...     print("Identity verified!")
    """

    def __init__(
        self,
        registry: "TrustRegistry",
        challenge_ttl_seconds: int = 300,
        max_pending_challenges: int = 100,
    ):
        """
        Initialize the identity verifier.

        Args:
            registry: Trust registry for looking up agents
            challenge_ttl_seconds: Time-to-live for challenges
            max_pending_challenges: Maximum pending challenges to store
        """
        self._registry = registry
        self._challenge_ttl = challenge_ttl_seconds
        self._max_pending = max_pending_challenges
        self._pending_challenges: Dict[str, Challenge] = {}
        self._verifier_did: Optional[str] = None

    def set_verifier_identity(self, identity: "AgentIdentity") -> None:
        """Set the verifier's identity."""
        self._verifier_did = identity.did

    def create_challenge(
        self,
        target_did: str,
        verifier_did: Optional[str] = None,
    ) -> Challenge:
        """
        Create a new verification challenge.

        Args:
            target_did: DID of the agent to verify
            verifier_did: DID of the verifier (optional if set via set_verifier_identity)

        Returns:
            Challenge object to be signed by target

        Raises:
            ValueError: If verifier DID not set
            ValueError: If target not registered
        """
        verifier_did = verifier_did or self._verifier_did
        if not verifier_did:
            raise ValueError("Verifier DID not set")

        # Check target is registered
        target_record = self._registry.get(target_did)
        if not target_record:
            raise ValueError(f"Target agent not registered: {target_did}")

        # Clean up expired challenges
        self._cleanup_expired()

        # Check capacity
        if len(self._pending_challenges) >= self._max_pending:
            # Remove oldest challenge
            oldest_id = min(
                self._pending_challenges,
                key=lambda k: self._pending_challenges[k].created_at,
            )
            del self._pending_challenges[oldest_id]

        # Generate challenge
        challenge_id = f"challenge:{secrets.token_hex(16)}"
        nonce = secrets.token_hex(32)
        now = datetime.now(timezone.utc)

        challenge = Challenge(
            challenge_id=challenge_id,
            verifier_did=verifier_did,
            target_did=target_did,
            nonce=nonce,
            created_at=now,
            expires_at=now + timedelta(seconds=self._challenge_ttl),
        )

        self._pending_challenges[challenge_id] = challenge
        return challenge

    def verify_response(
        self,
        challenge_id: str,
        response: bytes,
    ) -> VerificationResult:
        """
        Verify a challenge response.

        Args:
            challenge_id: ID of the challenge
            response: Signature from target agent

        Returns:
            VerificationResult indicating success/failure
        """
        # Get the challenge
        challenge = self._pending_challenges.get(challenge_id)
        if not challenge:
            return VerificationResult(
                success=False,
                challenge_id=challenge_id,
                target_did="",
                verifier_did="",
                status=VerificationStatus.FAILED,
                message="Challenge not found or already used",
            )

        # Check expiration
        if challenge.is_expired:
            challenge.status = VerificationStatus.EXPIRED
            del self._pending_challenges[challenge_id]
            return VerificationResult(
                success=False,
                challenge_id=challenge_id,
                target_did=challenge.target_did,
                verifier_did=challenge.verifier_did,
                status=VerificationStatus.EXPIRED,
                message="Challenge has expired",
            )

        # Get target's public key from registry
        target_record = self._registry.get(challenge.target_did)
        if not target_record:
            return VerificationResult(
                success=False,
                challenge_id=challenge_id,
                target_did=challenge.target_did,
                verifier_did=challenge.verifier_did,
                status=VerificationStatus.FAILED,
                message="Target agent not found in registry",
            )

        # Verify signature
        from .agent_identity import AgentIdentity

        verifier_identity = AgentIdentity.from_public_key(
            did=target_record.did,
            name=target_record.name,
            public_key_hex=target_record.public_key_hex,
        )

        is_valid = verifier_identity.verify(challenge.challenge_data, response)

        # Update challenge
        challenge.response = response
        challenge.verified_at = datetime.now(timezone.utc)
        challenge.status = (
            VerificationStatus.SUCCESS if is_valid else VerificationStatus.FAILED
        )

        # Record interaction in registry
        self._registry.record_interaction(
            challenge.target_did,
            success=is_valid,
            details={"type": "verification", "challenge_id": challenge_id},
        )

        # Remove from pending
        del self._pending_challenges[challenge_id]

        return VerificationResult(
            success=is_valid,
            challenge_id=challenge_id,
            target_did=challenge.target_did,
            verifier_did=challenge.verifier_did,
            status=challenge.status,
            message="Identity verified" if is_valid else "Signature verification failed",
            verified_at=challenge.verified_at if is_valid else None,
            trust_level=target_record.trust_level.value if is_valid else None,
        )

    def _cleanup_expired(self) -> None:
        """Remove expired challenges."""
        now = datetime.now(timezone.utc)
        expired = [
            cid
            for cid, c in self._pending_challenges.items()
            if c.expires_at < now
        ]
        for cid in expired:
            del self._pending_challenges[cid]

    def get_pending_count(self) -> int:
        """Get number of pending challenges."""
        return len(self._pending_challenges)


class MutualVerification:
    """
    Implements mutual (bidirectional) identity verification.

    Both agents verify each other's identity before establishing
    a trust relationship.
    """

    def __init__(self, registry: "TrustRegistry"):
        """Initialize mutual verification."""
        self._registry = registry
        self._verifier = IdentityVerifier(registry)

    def initiate(
        self,
        initiator: "AgentIdentity",
        target_did: str,
    ) -> Tuple[Challenge, Challenge]:
        """
        Initiate mutual verification.

        Args:
            initiator: Identity of the initiating agent
            target_did: DID of the target agent

        Returns:
            Tuple of (outgoing_challenge, incoming_challenge)
        """
        self._verifier.set_verifier_identity(initiator)

        # Create challenge for target
        outgoing_challenge = self._verifier.create_challenge(target_did)

        # Create challenge for initiator (from target's perspective)
        incoming_challenge = self._verifier.create_challenge(
            target_did=initiator.did,
            verifier_did=target_did,
        )

        return outgoing_challenge, incoming_challenge

    def complete(
        self,
        initiator: "AgentIdentity",
        outgoing_challenge_id: str,
        outgoing_response: bytes,
        incoming_challenge_id: str,
    ) -> Tuple[VerificationResult, bytes]:
        """
        Complete mutual verification.

        Args:
            initiator: Identity of the initiating agent
            outgoing_challenge_id: ID of challenge sent to target
            outgoing_response: Target's response to our challenge
            incoming_challenge_id: ID of challenge from target

        Returns:
            Tuple of (verification_result, our_response)
        """
        # Verify target's response
        result = self._verifier.verify_response(
            outgoing_challenge_id,
            outgoing_response,
        )

        # Sign the incoming challenge
        incoming_challenge = self._verifier._pending_challenges.get(
            incoming_challenge_id
        )
        if incoming_challenge:
            our_response = initiator.sign(incoming_challenge.challenge_data)
        else:
            our_response = b""

        return result, our_response


class HandshakeProtocol:
    """
    High-level protocol for establishing verified connections.

    Combines identity verification with credential exchange.
    """

    def __init__(self, registry: "TrustRegistry"):
        """Initialize handshake protocol."""
        self._registry = registry
        self._mutual_verifier = MutualVerification(registry)

    def create_handshake_request(
        self,
        initiator: "AgentIdentity",
        target_did: str,
        requested_capabilities: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Create a handshake request.

        Args:
            initiator: Identity of the initiating agent
            target_did: DID of the target agent
            requested_capabilities: Capabilities to request from target

        Returns:
            Handshake request dictionary
        """
        outgoing, incoming = self._mutual_verifier.initiate(initiator, target_did)

        return {
            "type": "handshake_request",
            "version": "1.0",
            "initiator_did": initiator.did,
            "target_did": target_did,
            "outgoing_challenge": outgoing.to_dict(),
            "incoming_challenge_id": incoming.challenge_id,
            "requested_capabilities": requested_capabilities or [],
            "initiator_public_key": initiator.public_key_hex,
            "initiator_capabilities": initiator.capabilities,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def process_handshake_response(
        self,
        initiator: "AgentIdentity",
        response: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Process a handshake response.

        Args:
            initiator: Identity of the initiating agent
            response: Handshake response from target

        Returns:
            Handshake result dictionary
        """
        # Verify target's response to our challenge
        result, our_response = self._mutual_verifier.complete(
            initiator,
            response["outgoing_challenge_response"]["challenge_id"],
            bytes.fromhex(response["outgoing_challenge_response"]["signature"]),
            response["incoming_challenge_id"],
        )

        return {
            "type": "handshake_completion",
            "verification_result": result.to_dict(),
            "our_response": {
                "challenge_id": response["incoming_challenge_id"],
                "signature": our_response.hex(),
            },
            "connection_established": result.success,
            "trust_level": result.trust_level,
        }
