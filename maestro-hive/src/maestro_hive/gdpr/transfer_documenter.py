"""
Transfer Documenter - Cross-border data transfer documentation

Implements AC-6: Document cross-border data transfers to AI providers.
Tracks international data transfers per GDPR Chapter V.

EPIC: MD-2156
Child Task: MD-2283 [Privacy-6]
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
import json
import uuid


class TransferMechanism(Enum):
    """Legal mechanism for international data transfer."""
    ADEQUACY_DECISION = "adequacy_decision"  # Article 45
    STANDARD_CLAUSES = "standard_clauses"  # Article 46(2)(c)
    BINDING_CORPORATE_RULES = "binding_corporate_rules"  # Article 47
    CERTIFICATION = "certification"  # Article 46(2)(f)
    CODE_OF_CONDUCT = "code_of_conduct"  # Article 46(2)(e)
    EXPLICIT_CONSENT = "explicit_consent"  # Article 49(1)(a)
    CONTRACT_NECESSITY = "contract_necessity"  # Article 49(1)(b)
    PUBLIC_INTEREST = "public_interest"  # Article 49(1)(d)
    LEGAL_CLAIMS = "legal_claims"  # Article 49(1)(e)


class DataProtectionLevel(Enum):
    """Assessment of destination's data protection level."""
    ADEQUATE = "adequate"
    ESSENTIALLY_EQUIVALENT = "essentially_equivalent"
    SUPPLEMENTARY_MEASURES = "supplementary_measures"
    INSUFFICIENT = "insufficient"


class TransferType(Enum):
    """Type of data transfer."""
    ONE_TIME = "one_time"
    CONTINUOUS = "continuous"
    PERIODIC = "periodic"
    ON_DEMAND = "on_demand"


@dataclass
class ThirdPartyRecipient:
    """Represents a third-party data recipient."""
    recipient_id: str
    name: str
    country: str
    country_code: str
    organization_type: str
    contact_email: str
    data_categories: list[str]
    purpose: str
    transfer_mechanism: TransferMechanism
    protection_level: DataProtectionLevel
    contract_reference: Optional[str] = None
    adequacy_decision_ref: Optional[str] = None
    supplementary_measures: list[str] = field(default_factory=list)
    last_assessment_date: Optional[datetime] = None
    next_review_date: Optional[datetime] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "recipient_id": self.recipient_id,
            "name": self.name,
            "country": self.country,
            "country_code": self.country_code,
            "organization_type": self.organization_type,
            "contact_email": self.contact_email,
            "data_categories": self.data_categories,
            "purpose": self.purpose,
            "transfer_mechanism": self.transfer_mechanism.value,
            "protection_level": self.protection_level.value,
            "contract_reference": self.contract_reference,
            "adequacy_decision_ref": self.adequacy_decision_ref,
            "supplementary_measures": self.supplementary_measures,
            "last_assessment_date": self.last_assessment_date.isoformat() if self.last_assessment_date else None,
            "next_review_date": self.next_review_date.isoformat() if self.next_review_date else None,
        }


@dataclass
class TransferRecord:
    """Record of a data transfer event."""
    transfer_id: str
    recipient_id: str
    user_id: Optional[str]
    transfer_type: TransferType
    data_categories: list[str]
    purpose: str
    timestamp: datetime
    volume_records: int
    volume_bytes: int
    legal_basis: str
    retention_period_days: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "transfer_id": self.transfer_id,
            "recipient_id": self.recipient_id,
            "user_id": self.user_id,
            "transfer_type": self.transfer_type.value,
            "data_categories": self.data_categories,
            "purpose": self.purpose,
            "timestamp": self.timestamp.isoformat(),
            "volume_records": self.volume_records,
            "volume_bytes": self.volume_bytes,
            "legal_basis": self.legal_basis,
            "retention_period_days": self.retention_period_days,
            "metadata": self.metadata,
        }


@dataclass
class TransferImpactAssessment:
    """Transfer Impact Assessment (TIA) for international transfers."""
    assessment_id: str
    recipient_id: str
    conducted_date: datetime
    assessor: str
    destination_country: str
    legal_framework_analysis: str
    government_access_risk: str
    redress_mechanisms: str
    protection_level: DataProtectionLevel
    supplementary_measures_required: list[str]
    conclusion: str
    valid_until: datetime
    approved_by: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "assessment_id": self.assessment_id,
            "recipient_id": self.recipient_id,
            "conducted_date": self.conducted_date.isoformat(),
            "assessor": self.assessor,
            "destination_country": self.destination_country,
            "legal_framework_analysis": self.legal_framework_analysis,
            "government_access_risk": self.government_access_risk,
            "redress_mechanisms": self.redress_mechanisms,
            "protection_level": self.protection_level.value,
            "supplementary_measures_required": self.supplementary_measures_required,
            "conclusion": self.conclusion,
            "valid_until": self.valid_until.isoformat(),
            "approved_by": self.approved_by,
        }


class TransferDocumenter:
    """
    Documents cross-border data transfers to AI providers.

    Implements GDPR Chapter V requirements:
    - Transfer to third countries only with appropriate safeguards
    - Document all international transfers
    - Maintain Transfer Impact Assessments
    - Implement supplementary measures where needed
    """

    # Countries with EU adequacy decisions (as of 2024)
    ADEQUATE_COUNTRIES = {
        "AD": "Andorra",
        "AR": "Argentina",
        "CA": "Canada",
        "FO": "Faroe Islands",
        "GG": "Guernsey",
        "IL": "Israel",
        "IM": "Isle of Man",
        "JP": "Japan",
        "JE": "Jersey",
        "NZ": "New Zealand",
        "KR": "South Korea",
        "CH": "Switzerland",
        "GB": "United Kingdom",
        "UY": "Uruguay",
        "US": "United States (DPF)",  # EU-US Data Privacy Framework
    }

    def __init__(self):
        """Initialize Transfer Documenter."""
        self._recipients: dict[str, ThirdPartyRecipient] = {}
        self._transfers: dict[str, TransferRecord] = {}
        self._assessments: dict[str, TransferImpactAssessment] = {}

    def register_recipient(
        self,
        name: str,
        country: str,
        country_code: str,
        organization_type: str,
        contact_email: str,
        data_categories: list[str],
        purpose: str,
        transfer_mechanism: TransferMechanism,
        contract_reference: Optional[str] = None,
        supplementary_measures: Optional[list[str]] = None,
    ) -> ThirdPartyRecipient:
        """
        Register a third-party data recipient.

        Args:
            name: Recipient organization name
            country: Country name
            country_code: ISO country code
            organization_type: Type of organization
            contact_email: DPO/privacy contact email
            data_categories: Categories of data received
            purpose: Purpose of transfer
            transfer_mechanism: Legal mechanism for transfer
            contract_reference: Reference to DPA/contract
            supplementary_measures: Additional protective measures

        Returns:
            Created recipient record
        """
        recipient_id = f"RCPT-{uuid.uuid4().hex[:8].upper()}"

        # Determine protection level
        if country_code in self.ADEQUATE_COUNTRIES:
            protection_level = DataProtectionLevel.ADEQUATE
        elif transfer_mechanism == TransferMechanism.STANDARD_CLAUSES:
            protection_level = DataProtectionLevel.SUPPLEMENTARY_MEASURES
        else:
            protection_level = DataProtectionLevel.ESSENTIALLY_EQUIVALENT

        recipient = ThirdPartyRecipient(
            recipient_id=recipient_id,
            name=name,
            country=country,
            country_code=country_code,
            organization_type=organization_type,
            contact_email=contact_email,
            data_categories=data_categories,
            purpose=purpose,
            transfer_mechanism=transfer_mechanism,
            protection_level=protection_level,
            contract_reference=contract_reference,
            supplementary_measures=supplementary_measures or [],
            last_assessment_date=datetime.utcnow(),
        )

        self._recipients[recipient_id] = recipient
        return recipient

    def record_transfer(
        self,
        recipient_id: str,
        transfer_type: TransferType,
        data_categories: list[str],
        purpose: str,
        volume_records: int,
        volume_bytes: int,
        legal_basis: str,
        retention_period_days: int,
        user_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> TransferRecord:
        """
        Record a data transfer event.

        Args:
            recipient_id: Recipient of the transfer
            transfer_type: Type of transfer
            data_categories: Categories of data transferred
            purpose: Purpose of this specific transfer
            volume_records: Number of records transferred
            volume_bytes: Size in bytes
            legal_basis: Legal basis for transfer
            retention_period_days: How long recipient retains data
            user_id: Optional user ID if user-specific
            metadata: Additional metadata

        Returns:
            Created transfer record
        """
        if recipient_id not in self._recipients:
            raise ValueError(f"Recipient not found: {recipient_id}")

        transfer_id = f"XFER-{uuid.uuid4().hex[:12].upper()}"

        transfer = TransferRecord(
            transfer_id=transfer_id,
            recipient_id=recipient_id,
            user_id=user_id,
            transfer_type=transfer_type,
            data_categories=data_categories,
            purpose=purpose,
            timestamp=datetime.utcnow(),
            volume_records=volume_records,
            volume_bytes=volume_bytes,
            legal_basis=legal_basis,
            retention_period_days=retention_period_days,
            metadata=metadata or {},
        )

        self._transfers[transfer_id] = transfer
        return transfer

    def conduct_tia(
        self,
        recipient_id: str,
        assessor: str,
        legal_framework_analysis: str,
        government_access_risk: str,
        redress_mechanisms: str,
        supplementary_measures: list[str],
        conclusion: str,
        validity_days: int = 365,
    ) -> TransferImpactAssessment:
        """
        Conduct a Transfer Impact Assessment.

        Args:
            recipient_id: Recipient being assessed
            assessor: Who conducted the assessment
            legal_framework_analysis: Analysis of destination legal framework
            government_access_risk: Assessment of government access risks
            redress_mechanisms: Available redress mechanisms
            supplementary_measures: Required supplementary measures
            conclusion: Assessment conclusion
            validity_days: How long assessment is valid

        Returns:
            Created assessment
        """
        if recipient_id not in self._recipients:
            raise ValueError(f"Recipient not found: {recipient_id}")

        recipient = self._recipients[recipient_id]
        assessment_id = f"TIA-{uuid.uuid4().hex[:8].upper()}"
        now = datetime.utcnow()

        # Determine protection level based on assessment
        if recipient.country_code in self.ADEQUATE_COUNTRIES:
            protection_level = DataProtectionLevel.ADEQUATE
        elif supplementary_measures:
            protection_level = DataProtectionLevel.SUPPLEMENTARY_MEASURES
        else:
            protection_level = DataProtectionLevel.ESSENTIALLY_EQUIVALENT

        assessment = TransferImpactAssessment(
            assessment_id=assessment_id,
            recipient_id=recipient_id,
            conducted_date=now,
            assessor=assessor,
            destination_country=recipient.country,
            legal_framework_analysis=legal_framework_analysis,
            government_access_risk=government_access_risk,
            redress_mechanisms=redress_mechanisms,
            protection_level=protection_level,
            supplementary_measures_required=supplementary_measures,
            conclusion=conclusion,
            valid_until=now + timedelta(days=validity_days),
        )

        self._assessments[assessment_id] = assessment

        # Update recipient with assessment info
        recipient.last_assessment_date = now
        recipient.supplementary_measures = supplementary_measures
        recipient.protection_level = protection_level

        return assessment

    def get_recipient(self, recipient_id: str) -> Optional[ThirdPartyRecipient]:
        """Get a recipient by ID."""
        return self._recipients.get(recipient_id)

    def get_transfer(self, transfer_id: str) -> Optional[TransferRecord]:
        """Get a transfer record by ID."""
        return self._transfers.get(transfer_id)

    def list_recipients(
        self,
        country_code: Optional[str] = None,
    ) -> list[ThirdPartyRecipient]:
        """List all recipients with optional country filter."""
        recipients = list(self._recipients.values())
        if country_code:
            recipients = [r for r in recipients if r.country_code == country_code]
        return recipients

    def list_transfers(
        self,
        recipient_id: Optional[str] = None,
        user_id: Optional[str] = None,
        since: Optional[datetime] = None,
    ) -> list[TransferRecord]:
        """
        List transfers with optional filters.

        Args:
            recipient_id: Filter by recipient
            user_id: Filter by user
            since: Filter by date

        Returns:
            List of matching transfers
        """
        transfers = list(self._transfers.values())

        if recipient_id:
            transfers = [t for t in transfers if t.recipient_id == recipient_id]

        if user_id:
            transfers = [t for t in transfers if t.user_id == user_id]

        if since:
            transfers = [t for t in transfers if t.timestamp >= since]

        return transfers

    def get_user_transfers(self, user_id: str) -> list[dict[str, Any]]:
        """
        Get all transfers for a specific user (for data portability).

        Args:
            user_id: User identifier

        Returns:
            List of transfer records with recipient details
        """
        transfers = self.list_transfers(user_id=user_id)
        result = []

        for transfer in transfers:
            recipient = self._recipients.get(transfer.recipient_id)
            result.append({
                "transfer": transfer.to_dict(),
                "recipient": recipient.to_dict() if recipient else None,
            })

        return result

    def check_adequacy(self, country_code: str) -> bool:
        """Check if a country has an adequacy decision."""
        return country_code in self.ADEQUATE_COUNTRIES

    def get_required_mechanisms(self, country_code: str) -> list[TransferMechanism]:
        """
        Get legal mechanisms required for transfer to a country.

        Args:
            country_code: ISO country code

        Returns:
            List of acceptable transfer mechanisms
        """
        if country_code in self.ADEQUATE_COUNTRIES:
            return [TransferMechanism.ADEQUACY_DECISION]

        # Non-adequate countries require additional safeguards
        return [
            TransferMechanism.STANDARD_CLAUSES,
            TransferMechanism.BINDING_CORPORATE_RULES,
            TransferMechanism.CERTIFICATION,
            TransferMechanism.CODE_OF_CONDUCT,
            TransferMechanism.EXPLICIT_CONSENT,
        ]

    def generate_article_30_record(self) -> dict[str, Any]:
        """
        Generate GDPR Article 30 record of processing activities for transfers.

        Returns:
            Dictionary with Article 30 compliant record
        """
        transfers_by_recipient: dict[str, list[TransferRecord]] = {}
        for transfer in self._transfers.values():
            if transfer.recipient_id not in transfers_by_recipient:
                transfers_by_recipient[transfer.recipient_id] = []
            transfers_by_recipient[transfer.recipient_id].append(transfer)

        record = {
            "record_type": "international_transfers",
            "generated_at": datetime.utcnow().isoformat(),
            "recipients": [],
        }

        for recipient_id, transfers in transfers_by_recipient.items():
            recipient = self._recipients.get(recipient_id)
            if not recipient:
                continue

            # Find latest TIA
            tia = None
            for assessment in self._assessments.values():
                if assessment.recipient_id == recipient_id:
                    if not tia or assessment.conducted_date > tia.conducted_date:
                        tia = assessment

            recipient_record = {
                "name": recipient.name,
                "country": recipient.country,
                "country_code": recipient.country_code,
                "transfer_mechanism": recipient.transfer_mechanism.value,
                "data_categories": recipient.data_categories,
                "purpose": recipient.purpose,
                "safeguards": recipient.supplementary_measures,
                "total_transfers": len(transfers),
                "tia_status": "valid" if tia and tia.valid_until > datetime.utcnow() else "required",
            }

            record["recipients"].append(recipient_record)

        return record

    def export_for_user(self, user_id: str) -> str:
        """Export all transfer records for a user as JSON."""
        transfers = self.get_user_transfers(user_id)
        return json.dumps(transfers, indent=2)

    def get_transfer_statistics(self) -> dict[str, Any]:
        """Get statistics about transfers."""
        stats = {
            "total_recipients": len(self._recipients),
            "total_transfers": len(self._transfers),
            "by_country": {},
            "by_mechanism": {},
            "adequate_countries": 0,
            "non_adequate_countries": 0,
        }

        for recipient in self._recipients.values():
            # Count by country
            if recipient.country not in stats["by_country"]:
                stats["by_country"][recipient.country] = 0
            stats["by_country"][recipient.country] += 1

            # Count by mechanism
            mechanism = recipient.transfer_mechanism.value
            if mechanism not in stats["by_mechanism"]:
                stats["by_mechanism"][mechanism] = 0
            stats["by_mechanism"][mechanism] += 1

            # Count adequacy
            if recipient.country_code in self.ADEQUATE_COUNTRIES:
                stats["adequate_countries"] += 1
            else:
                stats["non_adequate_countries"] += 1

        return stats


# Import timedelta for use in TIA
from datetime import timedelta
