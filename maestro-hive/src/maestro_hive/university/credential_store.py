"""
Credential Store (MD-3127)

Manages Verifiable Credentials (VCs) for agents.
Integrates with GovernancePersistence for storage and IdentityManager for signing.

AC-5: Upon passing (>80%), the agent receives a VC
AC-6: Credentials are signed using IdentityManager Ed25519 keys
AC-9: Credentials survive system restart (use GovernancePersistence)
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from maestro_hive.governance import IdentityManager, GovernancePersistence

logger = logging.getLogger(__name__)


class CredentialStatus(Enum):
    """Status of a credential."""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    SUSPENDED = "suspended"


@dataclass
class VerifiableCredential:
    """
    A Verifiable Credential issued by the University.

    Based on W3C VC Data Model (simplified).
    """
    credential_id: str
    agent_id: str
    credential_type: str  # e.g., "Python_Novice", "React_Expert"
    issuer: str = "PersonaUniversity"
    issued_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    status: CredentialStatus = CredentialStatus.ACTIVE

    # Exam context
    exam_id: Optional[str] = None
    exam_score: Optional[float] = None

    # Cryptographic proof
    signature: str = ""  # Ed25519 signature from IdentityManager

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_valid(self) -> bool:
        """Check if credential is currently valid."""
        if self.status != CredentialStatus.ACTIVE:
            return False
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "credential_id": self.credential_id,
            "agent_id": self.agent_id,
            "credential_type": self.credential_type,
            "issuer": self.issuer,
            "issued_at": self.issued_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "status": self.status.value,
            "exam_id": self.exam_id,
            "exam_score": self.exam_score,
            "signature": self.signature,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VerifiableCredential":
        """Deserialize from dictionary."""
        return cls(
            credential_id=data["credential_id"],
            agent_id=data["agent_id"],
            credential_type=data["credential_type"],
            issuer=data.get("issuer", "PersonaUniversity"),
            issued_at=datetime.fromisoformat(data["issued_at"]) if data.get("issued_at") else datetime.utcnow(),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
            status=CredentialStatus(data.get("status", "active")),
            exam_id=data.get("exam_id"),
            exam_score=data.get("exam_score"),
            signature=data.get("signature", ""),
            metadata=data.get("metadata", {}),
        )


class CredentialStore:
    """
    Manages Verifiable Credentials for agents.

    Features:
    - Issue credentials with Ed25519 signatures (AC-6)
    - Check credential validity (expiry, revocation)
    - Revoke/suspend credentials
    - Query agent credentials
    - Persist to GovernancePersistence (AC-9)
    """

    STORAGE_KEY_PREFIX = "credentials"
    REVOCATION_REGISTRY_KEY = "credentials:revoked"

    def __init__(
        self,
        identity_manager: Optional["IdentityManager"] = None,
        persistence: Optional["GovernancePersistence"] = None,
        default_validity_days: int = 365,
    ):
        """
        Initialize the credential store.

        Args:
            identity_manager: For signing credentials (AC-6)
            persistence: For storing credentials (AC-9)
            default_validity_days: Default credential validity
        """
        self._identity_manager = identity_manager
        self._persistence = persistence
        self._default_validity_days = default_validity_days
        self._revocation_registry: Set[str] = set()

        # In-memory store for when persistence is not available
        self._memory_store: Dict[str, VerifiableCredential] = {}

        # Load revocation registry if persistence available
        if self._persistence:
            self._load_revocation_registry()

        logger.info("CredentialStore initialized")

    def issue_credential(
        self,
        agent_id: str,
        credential_type: str,
        exam_id: Optional[str] = None,
        exam_score: Optional[float] = None,
        validity_days: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> VerifiableCredential:
        """
        Issue a new credential to an agent (AC-5).

        Args:
            agent_id: Agent receiving the credential
            credential_type: Type of credential (e.g., "Python_Novice")
            exam_id: Optional exam that earned this credential
            exam_score: Optional exam score
            validity_days: Days until expiry (default: 365)
            metadata: Additional metadata

        Returns:
            The issued VerifiableCredential
        """
        validity = validity_days or self._default_validity_days
        credential = VerifiableCredential(
            credential_id=f"vc_{uuid.uuid4().hex[:12]}",
            agent_id=agent_id,
            credential_type=credential_type,
            issued_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=validity),
            exam_id=exam_id,
            exam_score=exam_score,
            metadata=metadata or {},
        )

        # Sign with IdentityManager if available (AC-6)
        if self._identity_manager:
            signed_action = self._identity_manager.sign_action(
                agent_id="university_authority",
                action_type="credential_issued",
                payload=credential.to_dict(),
            )
            credential.signature = signed_action.signature
        else:
            # Fallback signature for testing
            credential.signature = f"unsigned:{credential.credential_id}"

        # Persist
        self._save_credential(credential)

        logger.info(f"Issued credential {credential.credential_id} ({credential_type}) to {agent_id}")
        return credential

    def verify_credential(self, credential: VerifiableCredential) -> bool:
        """
        Verify a credential is valid.

        Checks:
        - Status is ACTIVE
        - Not expired
        - Not in revocation registry
        """
        # Check status
        if credential.status != CredentialStatus.ACTIVE:
            logger.debug(f"Credential {credential.credential_id} status: {credential.status}")
            return False

        # Check expiry
        if credential.expires_at and datetime.utcnow() > credential.expires_at:
            logger.debug(f"Credential {credential.credential_id} expired")
            return False

        # Check revocation registry
        if credential.credential_id in self._revocation_registry:
            logger.debug(f"Credential {credential.credential_id} revoked")
            return False

        return True

    def revoke_credential(self, credential_id: str, reason: str = "") -> bool:
        """Revoke a credential."""
        credential = self.get_credential(credential_id)
        if not credential:
            return False

        credential.status = CredentialStatus.REVOKED
        credential.metadata["revoked_at"] = datetime.utcnow().isoformat()
        credential.metadata["revocation_reason"] = reason

        self._revocation_registry.add(credential_id)
        self._save_credential(credential)
        self._save_revocation_registry()

        logger.info(f"Revoked credential {credential_id}: {reason}")
        return True

    def get_credential(self, credential_id: str) -> Optional[VerifiableCredential]:
        """Get a credential by ID."""
        # Check memory store first
        if credential_id in self._memory_store:
            return self._memory_store[credential_id]

        # Check persistence
        if self._persistence:
            data = self._load_credential_from_persistence(credential_id)
            if data:
                cred = VerifiableCredential.from_dict(data)
                self._memory_store[credential_id] = cred
                return cred

        return None

    def get_agent_credentials(
        self,
        agent_id: str,
        valid_only: bool = True,
    ) -> List[VerifiableCredential]:
        """Get all credentials for an agent."""
        credentials = []

        # Get from memory store
        for cred in self._memory_store.values():
            if cred.agent_id == agent_id:
                if not valid_only or self.verify_credential(cred):
                    credentials.append(cred)

        return credentials

    def has_credential(self, agent_id: str, credential_type: str) -> bool:
        """Check if agent has a valid credential of given type (AC-2)."""
        credentials = self.get_agent_credentials(agent_id, valid_only=True)
        return any(c.credential_type == credential_type for c in credentials)

    def check_hiring_eligibility(self, agent_id: str, required_credential: str) -> bool:
        """
        Check if an agent is eligible for a role requiring specific credentials (AC-2).

        A "Fresh" agent cannot be hired for a "Senior" role without credentials.
        """
        return self.has_credential(agent_id, required_credential)

    def _save_credential(self, credential: VerifiableCredential) -> None:
        """Save credential to storage."""
        # Always save to memory
        self._memory_store[credential.credential_id] = credential

        # Save to persistence if available
        if self._persistence:
            key = f"{self.STORAGE_KEY_PREFIX}:{credential.credential_id}"
            # Use generic storage method
            if hasattr(self._persistence, '_backend'):
                self._persistence._backend.set(key, json.dumps(credential.to_dict()))

    def _load_credential_from_persistence(self, credential_id: str) -> Optional[Dict[str, Any]]:
        """Load credential from persistence."""
        if not self._persistence:
            return None

        key = f"{self.STORAGE_KEY_PREFIX}:{credential_id}"
        if hasattr(self._persistence, '_backend'):
            data = self._persistence._backend.get(key)
            if data:
                return json.loads(data)
        return None

    def _load_revocation_registry(self) -> None:
        """Load revocation registry from persistence."""
        if not self._persistence or not hasattr(self._persistence, '_backend'):
            return

        data = self._persistence._backend.get(self.REVOCATION_REGISTRY_KEY)
        if data:
            self._revocation_registry = set(json.loads(data))

    def _save_revocation_registry(self) -> None:
        """Save revocation registry to persistence."""
        if not self._persistence or not hasattr(self._persistence, '_backend'):
            return

        self._persistence._backend.set(
            self.REVOCATION_REGISTRY_KEY,
            json.dumps(list(self._revocation_registry))
        )
