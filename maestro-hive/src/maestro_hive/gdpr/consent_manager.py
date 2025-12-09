"""
Consent Manager - User consent for AI processing

Implements AC-3: Add explicit consent for AI processing of user data.
Manages GDPR-compliant consent collection and tracking per Article 7.

EPIC: MD-2156
Child Task: MD-2280 [Privacy-3]
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional
import hashlib
import json
import uuid


class ConsentType(Enum):
    """Types of consent that can be collected."""
    AI_PROCESSING = "ai_processing"
    DATA_SHARING = "data_sharing"
    MARKETING = "marketing"
    PROFILING = "profiling"
    CROSS_BORDER_TRANSFER = "cross_border_transfer"
    THIRD_PARTY_AI = "third_party_ai"
    DATA_RETENTION = "data_retention"


class ConsentStatus(Enum):
    """Status of a consent record."""
    ACTIVE = "active"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"
    PENDING = "pending"


class LegalBasis(Enum):
    """GDPR legal basis for processing."""
    CONSENT = "consent"  # Article 6(1)(a)
    CONTRACT = "contract"  # Article 6(1)(b)
    LEGAL_OBLIGATION = "legal_obligation"  # Article 6(1)(c)
    VITAL_INTERESTS = "vital_interests"  # Article 6(1)(d)
    PUBLIC_TASK = "public_task"  # Article 6(1)(e)
    LEGITIMATE_INTERESTS = "legitimate_interests"  # Article 6(1)(f)


@dataclass
class ConsentPurpose:
    """Detailed purpose for consent."""
    purpose_id: str
    name: str
    description: str
    consent_type: ConsentType
    legal_basis: LegalBasis
    data_categories: list[str]
    retention_period_days: int
    third_parties: list[str] = field(default_factory=list)
    mandatory: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "purpose_id": self.purpose_id,
            "name": self.name,
            "description": self.description,
            "consent_type": self.consent_type.value,
            "legal_basis": self.legal_basis.value,
            "data_categories": self.data_categories,
            "retention_period_days": self.retention_period_days,
            "third_parties": self.third_parties,
            "mandatory": self.mandatory,
        }


@dataclass
class ConsentRecord:
    """Individual consent record for a user."""
    consent_id: str
    user_id: str
    purpose_id: str
    consent_type: ConsentType
    status: ConsentStatus
    given_at: datetime
    expires_at: Optional[datetime]
    withdrawn_at: Optional[datetime] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    consent_text: str = ""
    version: str = "1.0"
    proof_hash: Optional[str] = None

    def is_valid(self) -> bool:
        """Check if consent is currently valid."""
        if self.status != ConsentStatus.ACTIVE:
            return False
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        return True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "consent_id": self.consent_id,
            "user_id": self.user_id,
            "purpose_id": self.purpose_id,
            "consent_type": self.consent_type.value,
            "status": self.status.value,
            "given_at": self.given_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "withdrawn_at": self.withdrawn_at.isoformat() if self.withdrawn_at else None,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "consent_text": self.consent_text,
            "version": self.version,
            "proof_hash": self.proof_hash,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConsentRecord":
        """Create from dictionary."""
        return cls(
            consent_id=data["consent_id"],
            user_id=data["user_id"],
            purpose_id=data["purpose_id"],
            consent_type=ConsentType(data["consent_type"]),
            status=ConsentStatus(data["status"]),
            given_at=datetime.fromisoformat(data["given_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
            withdrawn_at=datetime.fromisoformat(data["withdrawn_at"]) if data.get("withdrawn_at") else None,
            ip_address=data.get("ip_address"),
            user_agent=data.get("user_agent"),
            consent_text=data.get("consent_text", ""),
            version=data.get("version", "1.0"),
            proof_hash=data.get("proof_hash"),
        )


class ConsentManager:
    """
    Manages user consent for AI processing.

    Implements GDPR Article 7 requirements:
    - Consent must be freely given, specific, informed, and unambiguous
    - Controller must demonstrate consent was given
    - Consent can be withdrawn at any time
    - Withdrawal must be as easy as giving consent
    """

    def __init__(self, default_expiry_days: int = 365):
        """
        Initialize Consent Manager.

        Args:
            default_expiry_days: Default consent expiry period
        """
        self._default_expiry_days = default_expiry_days
        self._purposes: dict[str, ConsentPurpose] = {}
        self._consents: dict[str, list[ConsentRecord]] = {}  # user_id -> consents
        self._consent_index: dict[str, ConsentRecord] = {}  # consent_id -> consent

    def register_purpose(
        self,
        name: str,
        description: str,
        consent_type: ConsentType,
        legal_basis: LegalBasis,
        data_categories: list[str],
        retention_period_days: int = 365,
        third_parties: Optional[list[str]] = None,
        mandatory: bool = False,
    ) -> ConsentPurpose:
        """
        Register a consent purpose.

        Args:
            name: Purpose name
            description: Clear description for users
            consent_type: Type of consent
            legal_basis: GDPR legal basis
            data_categories: Categories of data processed
            retention_period_days: How long data is retained
            third_parties: Third parties data may be shared with
            mandatory: Whether consent is mandatory for service

        Returns:
            Created ConsentPurpose
        """
        purpose_id = f"PURPOSE-{uuid.uuid4().hex[:8].upper()}"

        purpose = ConsentPurpose(
            purpose_id=purpose_id,
            name=name,
            description=description,
            consent_type=consent_type,
            legal_basis=legal_basis,
            data_categories=data_categories,
            retention_period_days=retention_period_days,
            third_parties=third_parties or [],
            mandatory=mandatory,
        )

        self._purposes[purpose_id] = purpose
        return purpose

    def record_consent(
        self,
        user_id: str,
        purpose_id: str,
        consent_text: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        expiry_days: Optional[int] = None,
    ) -> ConsentRecord:
        """
        Record user consent for a purpose.

        Args:
            user_id: User identifier
            purpose_id: Purpose being consented to
            consent_text: Exact text user consented to
            ip_address: User's IP address
            user_agent: User's browser/agent
            expiry_days: Override expiry period

        Returns:
            Created ConsentRecord
        """
        if purpose_id not in self._purposes:
            raise ValueError(f"Unknown purpose: {purpose_id}")

        purpose = self._purposes[purpose_id]
        now = datetime.utcnow()
        days = expiry_days or self._default_expiry_days

        consent_id = f"CONSENT-{uuid.uuid4().hex[:12].upper()}"

        # Generate proof hash
        proof_data = f"{consent_id}:{user_id}:{purpose_id}:{now.isoformat()}:{consent_text}"
        proof_hash = hashlib.sha256(proof_data.encode()).hexdigest()

        consent = ConsentRecord(
            consent_id=consent_id,
            user_id=user_id,
            purpose_id=purpose_id,
            consent_type=purpose.consent_type,
            status=ConsentStatus.ACTIVE,
            given_at=now,
            expires_at=now + timedelta(days=days),
            ip_address=ip_address,
            user_agent=user_agent,
            consent_text=consent_text,
            proof_hash=proof_hash,
        )

        # Store consent
        if user_id not in self._consents:
            self._consents[user_id] = []
        self._consents[user_id].append(consent)
        self._consent_index[consent_id] = consent

        return consent

    def withdraw_consent(
        self,
        user_id: str,
        consent_id: Optional[str] = None,
        purpose_id: Optional[str] = None,
    ) -> list[ConsentRecord]:
        """
        Withdraw user consent.

        Args:
            user_id: User identifier
            consent_id: Specific consent to withdraw
            purpose_id: Withdraw all consents for a purpose

        Returns:
            List of withdrawn consent records
        """
        if user_id not in self._consents:
            raise ValueError(f"No consents found for user: {user_id}")

        withdrawn = []
        now = datetime.utcnow()

        for consent in self._consents[user_id]:
            if consent.status != ConsentStatus.ACTIVE:
                continue

            should_withdraw = False
            if consent_id and consent.consent_id == consent_id:
                should_withdraw = True
            elif purpose_id and consent.purpose_id == purpose_id:
                should_withdraw = True
            elif not consent_id and not purpose_id:
                # Withdraw all
                should_withdraw = True

            if should_withdraw:
                consent.status = ConsentStatus.WITHDRAWN
                consent.withdrawn_at = now
                withdrawn.append(consent)

        return withdrawn

    def check_consent(
        self,
        user_id: str,
        consent_type: Optional[ConsentType] = None,
        purpose_id: Optional[str] = None,
    ) -> bool:
        """
        Check if user has valid consent.

        Args:
            user_id: User identifier
            consent_type: Type of consent to check
            purpose_id: Specific purpose to check

        Returns:
            True if valid consent exists
        """
        if user_id not in self._consents:
            return False

        for consent in self._consents[user_id]:
            if not consent.is_valid():
                continue

            if purpose_id and consent.purpose_id == purpose_id:
                return True

            if consent_type and consent.consent_type == consent_type:
                return True

        return False

    def get_user_consents(
        self,
        user_id: str,
        active_only: bool = True,
    ) -> list[ConsentRecord]:
        """
        Get all consents for a user.

        Args:
            user_id: User identifier
            active_only: Only return active consents

        Returns:
            List of consent records
        """
        if user_id not in self._consents:
            return []

        consents = self._consents[user_id]
        if active_only:
            consents = [c for c in consents if c.is_valid()]

        return consents

    def get_consent(self, consent_id: str) -> Optional[ConsentRecord]:
        """Get a specific consent by ID."""
        return self._consent_index.get(consent_id)

    def refresh_consent(
        self,
        consent_id: str,
        new_expiry_days: Optional[int] = None,
    ) -> ConsentRecord:
        """
        Refresh an existing consent (extend expiry).

        Args:
            consent_id: Consent to refresh
            new_expiry_days: New expiry period

        Returns:
            Updated consent record
        """
        if consent_id not in self._consent_index:
            raise ValueError(f"Consent not found: {consent_id}")

        consent = self._consent_index[consent_id]

        if consent.status != ConsentStatus.ACTIVE:
            raise ValueError("Cannot refresh withdrawn or expired consent")

        days = new_expiry_days or self._default_expiry_days
        consent.expires_at = datetime.utcnow() + timedelta(days=days)

        return consent

    def check_ai_processing_consent(self, user_id: str) -> bool:
        """
        Check if user has consented to AI processing.

        This is a convenience method for the most common check.

        Args:
            user_id: User identifier

        Returns:
            True if AI processing consent is valid
        """
        return self.check_consent(user_id, consent_type=ConsentType.AI_PROCESSING)

    def get_consent_proof(self, consent_id: str) -> dict[str, Any]:
        """
        Get proof of consent for auditing/compliance.

        Args:
            consent_id: Consent identifier

        Returns:
            Dictionary with consent proof data
        """
        if consent_id not in self._consent_index:
            raise ValueError(f"Consent not found: {consent_id}")

        consent = self._consent_index[consent_id]
        purpose = self._purposes.get(consent.purpose_id)

        return {
            "consent_id": consent.consent_id,
            "user_id": consent.user_id,
            "purpose": purpose.to_dict() if purpose else None,
            "consent_text": consent.consent_text,
            "given_at": consent.given_at.isoformat(),
            "status": consent.status.value,
            "proof_hash": consent.proof_hash,
            "ip_address": consent.ip_address,
            "user_agent": consent.user_agent,
        }

    def export_user_consents(self, user_id: str) -> str:
        """Export all user consents as JSON (for data portability)."""
        consents = self.get_user_consents(user_id, active_only=False)
        return json.dumps([c.to_dict() for c in consents], indent=2)

    def get_expiring_consents(self, days: int = 30) -> list[ConsentRecord]:
        """Get consents expiring within specified days."""
        threshold = datetime.utcnow() + timedelta(days=days)
        expiring = []

        for consents in self._consents.values():
            for consent in consents:
                if (
                    consent.status == ConsentStatus.ACTIVE
                    and consent.expires_at
                    and consent.expires_at <= threshold
                ):
                    expiring.append(consent)

        return expiring

    def get_purpose(self, purpose_id: str) -> Optional[ConsentPurpose]:
        """Get a consent purpose by ID."""
        return self._purposes.get(purpose_id)

    def list_purposes(self) -> list[ConsentPurpose]:
        """List all registered consent purposes."""
        return list(self._purposes.values())
