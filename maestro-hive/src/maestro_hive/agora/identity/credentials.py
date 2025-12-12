"""
Agent Credentials Module - Verifiable Credentials for Agents

Implements verifiable credentials for attesting agent capabilities,
roles, and trust relationships.

EPIC: MD-3104 (Agora Phase 2: Identity & Trust)
AC-2: Create AgentCredential system for verifiable credentials
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from .agent_identity import AgentIdentity


class CredentialType(str, Enum):
    """Types of verifiable credentials."""
    CAPABILITY = "capability"
    ROLE = "role"
    CERTIFICATION = "certification"
    TRUST_DELEGATION = "trust_delegation"
    MEMBERSHIP = "membership"
    AUTHORIZATION = "authorization"


class CredentialStatus(str, Enum):
    """Status of a credential."""
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"
    SUSPENDED = "suspended"


@dataclass
class CredentialClaim:
    """A single claim within a credential."""
    claim_type: str
    value: Any
    evidence: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = {
            "type": self.claim_type,
            "value": self.value,
        }
        if self.evidence:
            data["evidence"] = self.evidence
        return data


@dataclass
class AgentCredential:
    """
    Verifiable Credential for an agent.

    Based on W3C Verifiable Credentials Data Model.

    Attributes:
        credential_id: Unique identifier for this credential
        issuer_did: DID of the credential issuer
        subject_did: DID of the credential subject
        credential_type: Type of credential
        claims: List of claims in this credential
        issued_at: When the credential was issued
        expires_at: When the credential expires
        signature: Cryptographic signature from issuer
        status: Current status of the credential
    """
    credential_id: str
    issuer_did: str
    subject_did: str
    credential_type: CredentialType
    claims: List[CredentialClaim] = field(default_factory=list)
    issued_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    signature: Optional[bytes] = None
    status: CredentialStatus = CredentialStatus.ACTIVE
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        issuer: "AgentIdentity",
        subject_did: str,
        credential_type: CredentialType,
        claims: Optional[Dict[str, Any]] = None,
        expires_in_days: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "AgentCredential":
        """
        Create and sign a new credential.

        Args:
            issuer: The identity issuing the credential
            subject_did: DID of the subject receiving the credential
            credential_type: Type of credential
            claims: Dictionary of claims
            expires_in_days: Days until expiration (None = no expiry)
            metadata: Additional metadata

        Returns:
            Signed AgentCredential
        """
        credential_id = f"vc:{uuid.uuid4()}"
        issued_at = datetime.now(timezone.utc)

        expires_at = None
        if expires_in_days:
            expires_at = issued_at + timedelta(days=expires_in_days)

        # Convert claims dict to CredentialClaim objects
        claim_objects = []
        if claims:
            for claim_type, value in claims.items():
                claim_objects.append(CredentialClaim(
                    claim_type=claim_type,
                    value=value,
                ))

        credential = cls(
            credential_id=credential_id,
            issuer_did=issuer.did,
            subject_did=subject_did,
            credential_type=credential_type,
            claims=claim_objects,
            issued_at=issued_at,
            expires_at=expires_at,
            metadata=metadata or {},
        )

        # Sign the credential
        credential._sign(issuer)

        return credential

    def _sign(self, issuer: "AgentIdentity") -> None:
        """Sign the credential with the issuer's private key."""
        payload = self._get_signing_payload()
        self.signature = issuer.sign(payload)

    def _get_signing_payload(self) -> bytes:
        """Get the payload to be signed."""
        data = {
            "credential_id": self.credential_id,
            "issuer_did": self.issuer_did,
            "subject_did": self.subject_did,
            "credential_type": self.credential_type.value,
            "claims": [c.to_dict() for c in self.claims],
            "issued_at": self.issued_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }
        return json.dumps(data, sort_keys=True).encode()

    def verify(self, issuer_public_key: bytes) -> bool:
        """
        Verify the credential's signature.

        Args:
            issuer_public_key: Public key bytes of the issuer

        Returns:
            True if signature is valid
        """
        if not self.signature:
            return False

        # Import here to avoid circular dependency
        from .agent_identity import AgentIdentity

        # Create a verification-only identity
        verifier = AgentIdentity.from_public_key(
            did=self.issuer_did,
            name="verifier",
            public_key_hex=issuer_public_key.hex(),
        )

        payload = self._get_signing_payload()
        return verifier.verify(payload, self.signature)

    def is_valid(self) -> bool:
        """
        Check if the credential is currently valid.

        Returns:
            True if active and not expired
        """
        if self.status != CredentialStatus.ACTIVE:
            return False

        if self.expires_at and datetime.now(timezone.utc) > self.expires_at:
            return False

        return True

    def revoke(self) -> None:
        """Revoke this credential."""
        self.status = CredentialStatus.REVOKED

    def suspend(self) -> None:
        """Suspend this credential."""
        self.status = CredentialStatus.SUSPENDED

    def reinstate(self) -> None:
        """Reinstate a suspended credential."""
        if self.status == CredentialStatus.SUSPENDED:
            self.status = CredentialStatus.ACTIVE

    def get_claim(self, claim_type: str) -> Optional[Any]:
        """Get the value of a specific claim."""
        for claim in self.claims:
            if claim.claim_type == claim_type:
                return claim.value
        return None

    def has_claim(self, claim_type: str, value: Any = None) -> bool:
        """
        Check if credential has a specific claim.

        Args:
            claim_type: Type of claim to check
            value: Optional value to match

        Returns:
            True if claim exists (and matches value if specified)
        """
        for claim in self.claims:
            if claim.claim_type == claim_type:
                if value is None:
                    return True
                return claim.value == value
        return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "@context": [
                "https://www.w3.org/2018/credentials/v1",
                "https://agora.maestro.ai/credentials/v1",
            ],
            "id": self.credential_id,
            "type": ["VerifiableCredential", f"Agora{self.credential_type.value.title()}Credential"],
            "issuer": self.issuer_did,
            "issuanceDate": self.issued_at.isoformat(),
            "expirationDate": self.expires_at.isoformat() if self.expires_at else None,
            "credentialSubject": {
                "id": self.subject_did,
                "claims": [c.to_dict() for c in self.claims],
            },
            "proof": {
                "type": "Ed25519Signature2020",
                "created": self.issued_at.isoformat(),
                "verificationMethod": f"{self.issuer_did}#key-1",
                "proofValue": self.signature.hex() if self.signature else None,
            },
            "credentialStatus": {
                "type": "CredentialStatusList2021",
                "status": self.status.value,
            },
            "metadata": self.metadata,
        }

    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentCredential":
        """Create from dictionary representation."""
        claims = []
        subject_data = data.get("credentialSubject", {})
        for claim_data in subject_data.get("claims", []):
            claims.append(CredentialClaim(
                claim_type=claim_data["type"],
                value=claim_data["value"],
                evidence=claim_data.get("evidence"),
            ))

        signature = None
        proof = data.get("proof", {})
        if proof.get("proofValue"):
            signature = bytes.fromhex(proof["proofValue"])

        credential_type_str = data.get("type", ["", "AgoraCapabilityCredential"])[1]
        credential_type_str = credential_type_str.replace("Agora", "").replace("Credential", "").lower()
        try:
            credential_type = CredentialType(credential_type_str)
        except ValueError:
            credential_type = CredentialType.CAPABILITY

        status_data = data.get("credentialStatus", {})
        try:
            status = CredentialStatus(status_data.get("status", "active"))
        except ValueError:
            status = CredentialStatus.ACTIVE

        expires_at = None
        if data.get("expirationDate"):
            expires_at = datetime.fromisoformat(data["expirationDate"])

        return cls(
            credential_id=data["id"],
            issuer_did=data["issuer"],
            subject_did=subject_data.get("id", ""),
            credential_type=credential_type,
            claims=claims,
            issued_at=datetime.fromisoformat(data["issuanceDate"]),
            expires_at=expires_at,
            signature=signature,
            status=status,
            metadata=data.get("metadata", {}),
        )

    def __repr__(self) -> str:
        return (
            f"AgentCredential(id={self.credential_id!r}, "
            f"type={self.credential_type.value}, "
            f"subject={self.subject_did!r})"
        )


class CredentialStore:
    """
    Storage for agent credentials.

    Provides credential lookup, validation, and management.
    """

    def __init__(self):
        """Initialize the credential store."""
        self._credentials: Dict[str, AgentCredential] = {}
        self._by_subject: Dict[str, List[str]] = {}
        self._by_issuer: Dict[str, List[str]] = {}

    def add(self, credential: AgentCredential) -> None:
        """Add a credential to the store."""
        self._credentials[credential.credential_id] = credential

        # Index by subject
        if credential.subject_did not in self._by_subject:
            self._by_subject[credential.subject_did] = []
        self._by_subject[credential.subject_did].append(credential.credential_id)

        # Index by issuer
        if credential.issuer_did not in self._by_issuer:
            self._by_issuer[credential.issuer_did] = []
        self._by_issuer[credential.issuer_did].append(credential.credential_id)

    def get(self, credential_id: str) -> Optional[AgentCredential]:
        """Get a credential by ID."""
        return self._credentials.get(credential_id)

    def get_by_subject(
        self,
        subject_did: str,
        credential_type: Optional[CredentialType] = None,
        only_valid: bool = True,
    ) -> List[AgentCredential]:
        """
        Get all credentials for a subject.

        Args:
            subject_did: DID of the subject
            credential_type: Optional filter by type
            only_valid: Only return valid credentials

        Returns:
            List of matching credentials
        """
        credential_ids = self._by_subject.get(subject_did, [])
        credentials = [self._credentials[cid] for cid in credential_ids]

        if credential_type:
            credentials = [c for c in credentials if c.credential_type == credential_type]

        if only_valid:
            credentials = [c for c in credentials if c.is_valid()]

        return credentials

    def get_by_issuer(self, issuer_did: str) -> List[AgentCredential]:
        """Get all credentials issued by an agent."""
        credential_ids = self._by_issuer.get(issuer_did, [])
        return [self._credentials[cid] for cid in credential_ids]

    def revoke(self, credential_id: str) -> bool:
        """Revoke a credential."""
        credential = self._credentials.get(credential_id)
        if credential:
            credential.revoke()
            return True
        return False

    def has_capability(
        self,
        subject_did: str,
        capability: str,
    ) -> bool:
        """
        Check if a subject has a specific capability credential.

        Args:
            subject_did: DID of the subject
            capability: Capability to check for

        Returns:
            True if subject has valid capability credential
        """
        credentials = self.get_by_subject(
            subject_did,
            credential_type=CredentialType.CAPABILITY,
            only_valid=True,
        )
        for cred in credentials:
            if cred.has_claim("capability", capability):
                return True
        return False

    def count(self) -> int:
        """Get total number of credentials."""
        return len(self._credentials)

    def clear(self) -> None:
        """Clear all credentials."""
        self._credentials.clear()
        self._by_subject.clear()
        self._by_issuer.clear()
