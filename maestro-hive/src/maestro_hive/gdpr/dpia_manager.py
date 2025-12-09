"""
DPIA Manager - Data Protection Impact Assessment

Implements AC-1: Conduct Data Protection Impact Assessment (DPIA) for AI features.
Provides functionality to conduct, track, and report on DPIAs as required by
GDPR Article 35 and AI Act requirements.

EPIC: MD-2156
Child Task: MD-2278 [Privacy-1]
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional
import json
import hashlib
import uuid


class DPIAStatus(Enum):
    """Status of a DPIA assessment."""
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    REQUIRES_UPDATE = "requires_update"
    EXPIRED = "expired"


class RiskLevel(Enum):
    """Risk level classification for DPIA."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RiskAssessment:
    """Individual risk assessment within a DPIA."""
    risk_id: str
    category: str
    description: str
    likelihood: int  # 1-5
    impact: int  # 1-5
    risk_level: RiskLevel
    mitigations: list[str] = field(default_factory=list)
    residual_risk: Optional[RiskLevel] = None

    @property
    def risk_score(self) -> int:
        """Calculate risk score as likelihood * impact."""
        return self.likelihood * self.impact

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "risk_id": self.risk_id,
            "category": self.category,
            "description": self.description,
            "likelihood": self.likelihood,
            "impact": self.impact,
            "risk_level": self.risk_level.value,
            "risk_score": self.risk_score,
            "mitigations": self.mitigations,
            "residual_risk": self.residual_risk.value if self.residual_risk else None,
        }


@dataclass
class DPIAReport:
    """Complete DPIA report structure."""
    dpia_id: str
    title: str
    description: str
    processing_purpose: str
    data_categories: list[str]
    data_subjects: list[str]
    ai_system_description: str
    status: DPIAStatus
    created_at: datetime
    updated_at: datetime
    risk_assessments: list[RiskAssessment] = field(default_factory=list)
    necessity_assessment: str = ""
    proportionality_assessment: str = ""
    consultation_required: bool = False
    dpo_opinion: Optional[str] = None
    approval_date: Optional[datetime] = None
    next_review_date: Optional[datetime] = None

    @property
    def overall_risk_level(self) -> RiskLevel:
        """Calculate overall risk level from assessments."""
        if not self.risk_assessments:
            return RiskLevel.LOW

        max_score = max(ra.risk_score for ra in self.risk_assessments)
        if max_score >= 20:
            return RiskLevel.CRITICAL
        elif max_score >= 15:
            return RiskLevel.HIGH
        elif max_score >= 10:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "dpia_id": self.dpia_id,
            "title": self.title,
            "description": self.description,
            "processing_purpose": self.processing_purpose,
            "data_categories": self.data_categories,
            "data_subjects": self.data_subjects,
            "ai_system_description": self.ai_system_description,
            "status": self.status.value,
            "overall_risk_level": self.overall_risk_level.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "risk_assessments": [ra.to_dict() for ra in self.risk_assessments],
            "necessity_assessment": self.necessity_assessment,
            "proportionality_assessment": self.proportionality_assessment,
            "consultation_required": self.consultation_required,
            "dpo_opinion": self.dpo_opinion,
            "approval_date": self.approval_date.isoformat() if self.approval_date else None,
            "next_review_date": self.next_review_date.isoformat() if self.next_review_date else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DPIAReport":
        """Create from dictionary."""
        risk_assessments = [
            RiskAssessment(
                risk_id=ra["risk_id"],
                category=ra["category"],
                description=ra["description"],
                likelihood=ra["likelihood"],
                impact=ra["impact"],
                risk_level=RiskLevel(ra["risk_level"]),
                mitigations=ra.get("mitigations", []),
                residual_risk=RiskLevel(ra["residual_risk"]) if ra.get("residual_risk") else None,
            )
            for ra in data.get("risk_assessments", [])
        ]

        return cls(
            dpia_id=data["dpia_id"],
            title=data["title"],
            description=data["description"],
            processing_purpose=data["processing_purpose"],
            data_categories=data["data_categories"],
            data_subjects=data["data_subjects"],
            ai_system_description=data["ai_system_description"],
            status=DPIAStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            risk_assessments=risk_assessments,
            necessity_assessment=data.get("necessity_assessment", ""),
            proportionality_assessment=data.get("proportionality_assessment", ""),
            consultation_required=data.get("consultation_required", False),
            dpo_opinion=data.get("dpo_opinion"),
            approval_date=datetime.fromisoformat(data["approval_date"]) if data.get("approval_date") else None,
            next_review_date=datetime.fromisoformat(data["next_review_date"]) if data.get("next_review_date") else None,
        )


class DPIAManager:
    """
    Manages Data Protection Impact Assessments for AI features.

    Implements GDPR Article 35 requirements for DPIA:
    - Systematic description of processing operations
    - Assessment of necessity and proportionality
    - Assessment of risks to data subjects
    - Measures to address risks
    """

    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize DPIA Manager.

        Args:
            storage_path: Path for persistent storage of DPIAs
        """
        self._storage_path = storage_path
        self._dpias: dict[str, DPIAReport] = {}
        self._review_period_days = 365  # Annual review by default

    def create_dpia(
        self,
        title: str,
        description: str,
        processing_purpose: str,
        data_categories: list[str],
        data_subjects: list[str],
        ai_system_description: str,
    ) -> DPIAReport:
        """
        Create a new DPIA assessment.

        Args:
            title: DPIA title
            description: Detailed description
            processing_purpose: Purpose of data processing
            data_categories: Categories of personal data processed
            data_subjects: Categories of data subjects
            ai_system_description: Description of AI system being assessed

        Returns:
            Created DPIA report
        """
        dpia_id = f"DPIA-{uuid.uuid4().hex[:8].upper()}"
        now = datetime.utcnow()

        dpia = DPIAReport(
            dpia_id=dpia_id,
            title=title,
            description=description,
            processing_purpose=processing_purpose,
            data_categories=data_categories,
            data_subjects=data_subjects,
            ai_system_description=ai_system_description,
            status=DPIAStatus.DRAFT,
            created_at=now,
            updated_at=now,
        )

        self._dpias[dpia_id] = dpia
        return dpia

    def add_risk_assessment(
        self,
        dpia_id: str,
        category: str,
        description: str,
        likelihood: int,
        impact: int,
        mitigations: Optional[list[str]] = None,
    ) -> RiskAssessment:
        """
        Add a risk assessment to a DPIA.

        Args:
            dpia_id: DPIA identifier
            category: Risk category
            description: Risk description
            likelihood: Likelihood score (1-5)
            impact: Impact score (1-5)
            mitigations: List of mitigation measures

        Returns:
            Created risk assessment
        """
        if dpia_id not in self._dpias:
            raise ValueError(f"DPIA not found: {dpia_id}")

        dpia = self._dpias[dpia_id]

        # Validate scores
        if not (1 <= likelihood <= 5):
            raise ValueError("Likelihood must be between 1 and 5")
        if not (1 <= impact <= 5):
            raise ValueError("Impact must be between 1 and 5")

        # Determine risk level
        score = likelihood * impact
        if score >= 20:
            risk_level = RiskLevel.CRITICAL
        elif score >= 15:
            risk_level = RiskLevel.HIGH
        elif score >= 10:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW

        risk_id = f"RISK-{len(dpia.risk_assessments) + 1:03d}"

        risk = RiskAssessment(
            risk_id=risk_id,
            category=category,
            description=description,
            likelihood=likelihood,
            impact=impact,
            risk_level=risk_level,
            mitigations=mitigations or [],
        )

        dpia.risk_assessments.append(risk)
        dpia.updated_at = datetime.utcnow()

        # Check if supervisory authority consultation is required
        if risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            dpia.consultation_required = True

        return risk

    def set_necessity_assessment(self, dpia_id: str, assessment: str) -> None:
        """Set the necessity assessment for a DPIA."""
        if dpia_id not in self._dpias:
            raise ValueError(f"DPIA not found: {dpia_id}")

        self._dpias[dpia_id].necessity_assessment = assessment
        self._dpias[dpia_id].updated_at = datetime.utcnow()

    def set_proportionality_assessment(self, dpia_id: str, assessment: str) -> None:
        """Set the proportionality assessment for a DPIA."""
        if dpia_id not in self._dpias:
            raise ValueError(f"DPIA not found: {dpia_id}")

        self._dpias[dpia_id].proportionality_assessment = assessment
        self._dpias[dpia_id].updated_at = datetime.utcnow()

    def submit_for_review(self, dpia_id: str) -> DPIAReport:
        """Submit DPIA for DPO review."""
        if dpia_id not in self._dpias:
            raise ValueError(f"DPIA not found: {dpia_id}")

        dpia = self._dpias[dpia_id]

        # Validate completeness
        if not dpia.necessity_assessment:
            raise ValueError("Necessity assessment required")
        if not dpia.proportionality_assessment:
            raise ValueError("Proportionality assessment required")
        if not dpia.risk_assessments:
            raise ValueError("At least one risk assessment required")

        dpia.status = DPIAStatus.PENDING_REVIEW
        dpia.updated_at = datetime.utcnow()

        return dpia

    def approve_dpia(
        self,
        dpia_id: str,
        dpo_opinion: str,
        review_period_days: Optional[int] = None,
    ) -> DPIAReport:
        """
        Approve a DPIA after DPO review.

        Args:
            dpia_id: DPIA identifier
            dpo_opinion: DPO's opinion and recommendations
            review_period_days: Days until next review

        Returns:
            Updated DPIA report
        """
        if dpia_id not in self._dpias:
            raise ValueError(f"DPIA not found: {dpia_id}")

        dpia = self._dpias[dpia_id]

        if dpia.status != DPIAStatus.PENDING_REVIEW:
            raise ValueError("DPIA must be in pending review status")

        now = datetime.utcnow()
        review_days = review_period_days or self._review_period_days

        dpia.status = DPIAStatus.APPROVED
        dpia.dpo_opinion = dpo_opinion
        dpia.approval_date = now
        dpia.next_review_date = now + timedelta(days=review_days)
        dpia.updated_at = now

        return dpia

    def reject_dpia(self, dpia_id: str, dpo_opinion: str) -> DPIAReport:
        """Reject a DPIA requiring revisions."""
        if dpia_id not in self._dpias:
            raise ValueError(f"DPIA not found: {dpia_id}")

        dpia = self._dpias[dpia_id]
        dpia.status = DPIAStatus.REJECTED
        dpia.dpo_opinion = dpo_opinion
        dpia.updated_at = datetime.utcnow()

        return dpia

    def get_dpia(self, dpia_id: str) -> Optional[DPIAReport]:
        """Get a DPIA by ID."""
        return self._dpias.get(dpia_id)

    def list_dpias(
        self,
        status: Optional[DPIAStatus] = None,
        risk_level: Optional[RiskLevel] = None,
    ) -> list[DPIAReport]:
        """
        List DPIAs with optional filtering.

        Args:
            status: Filter by status
            risk_level: Filter by risk level

        Returns:
            List of matching DPIA reports
        """
        results = list(self._dpias.values())

        if status:
            results = [d for d in results if d.status == status]

        if risk_level:
            results = [d for d in results if d.overall_risk_level == risk_level]

        return results

    def check_reviews_due(self) -> list[DPIAReport]:
        """Get list of DPIAs due for review."""
        now = datetime.utcnow()
        return [
            dpia for dpia in self._dpias.values()
            if dpia.status == DPIAStatus.APPROVED
            and dpia.next_review_date
            and dpia.next_review_date <= now
        ]

    def generate_report_hash(self, dpia_id: str) -> str:
        """Generate SHA-256 hash of DPIA for integrity verification."""
        if dpia_id not in self._dpias:
            raise ValueError(f"DPIA not found: {dpia_id}")

        dpia = self._dpias[dpia_id]
        content = json.dumps(dpia.to_dict(), sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()

    def export_dpia(self, dpia_id: str) -> str:
        """Export DPIA as JSON string."""
        if dpia_id not in self._dpias:
            raise ValueError(f"DPIA not found: {dpia_id}")

        return json.dumps(self._dpias[dpia_id].to_dict(), indent=2)

    def import_dpia(self, json_data: str) -> DPIAReport:
        """Import DPIA from JSON string."""
        data = json.loads(json_data)
        dpia = DPIAReport.from_dict(data)
        self._dpias[dpia.dpia_id] = dpia
        return dpia
