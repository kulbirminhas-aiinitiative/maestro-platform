"""
Technical Documentation Module - EU AI Act Article 11 Compliance

Generates and maintains comprehensive technical documentation covering
system design, intended purpose, and risk assessment.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import json
import hashlib


class DocumentationType(Enum):
    """Types of technical documentation per Article 11."""
    SYSTEM_DESCRIPTION = "system_description"
    DESIGN_SPECIFICATION = "design_specification"
    INTENDED_PURPOSE = "intended_purpose"
    RISK_ASSESSMENT = "risk_assessment"
    DATA_GOVERNANCE = "data_governance"
    TESTING_PROCEDURE = "testing_procedure"
    MONITORING_PLAN = "monitoring_plan"
    CHANGE_LOG = "change_log"


class RiskLevel(Enum):
    """Risk classification levels."""
    MINIMAL = "minimal"
    LIMITED = "limited"
    HIGH = "high"
    UNACCEPTABLE = "unacceptable"


@dataclass
class DocumentVersion:
    """Version information for documentation."""
    version: str
    created_at: datetime
    created_by: str
    changes: List[str]
    checksum: str = ""


@dataclass
class RiskAssessment:
    """Risk assessment details for AI system."""
    risk_id: str
    risk_description: str
    risk_level: RiskLevel
    likelihood: float  # 0.0 to 1.0
    impact: float  # 0.0 to 1.0
    mitigation_measures: List[str]
    residual_risk: float = 0.0
    assessment_date: datetime = field(default_factory=datetime.utcnow)

    def calculate_risk_score(self) -> float:
        """Calculate composite risk score."""
        return self.likelihood * self.impact


@dataclass
class TechnicalDocument:
    """A technical documentation artifact."""
    doc_id: str
    doc_type: DocumentationType
    title: str
    content: Dict[str, Any]
    version: DocumentVersion
    ai_system_id: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    approved: bool = False
    approved_by: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert document to dictionary."""
        return {
            "doc_id": self.doc_id,
            "doc_type": self.doc_type.value,
            "title": self.title,
            "content": self.content,
            "version": {
                "version": self.version.version,
                "created_at": self.version.created_at.isoformat(),
                "created_by": self.version.created_by,
                "changes": self.version.changes,
                "checksum": self.version.checksum
            },
            "ai_system_id": self.ai_system_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "approved": self.approved,
            "approved_by": self.approved_by
        }


class TechnicalDocumentation:
    """
    Technical Documentation manager for EU AI Act Article 11 compliance.

    Generates and maintains comprehensive documentation covering system
    design, intended purpose, capabilities, and risk assessments.
    """

    def __init__(self, ai_system_id: str, ai_system_name: str):
        """
        Initialize technical documentation manager.

        Args:
            ai_system_id: Unique identifier for the AI system
            ai_system_name: Human-readable name for the AI system
        """
        self.ai_system_id = ai_system_id
        self.ai_system_name = ai_system_name
        self._documents: Dict[str, TechnicalDocument] = {}
        self._risk_assessments: List[RiskAssessment] = []
        self._version_history: List[DocumentVersion] = []

    def _generate_doc_id(self, doc_type: DocumentationType) -> str:
        """Generate unique document ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        content = f"{self.ai_system_id}:{doc_type.value}:{timestamp}"
        return hashlib.md5(content.encode()).hexdigest()[:12]

    def _calculate_checksum(self, content: Dict[str, Any]) -> str:
        """Calculate SHA-256 checksum of document content."""
        content_str = json.dumps(content, sort_keys=True)
        return hashlib.sha256(content_str.encode()).hexdigest()

    def create_system_description(
        self,
        description: str,
        capabilities: List[str],
        limitations: List[str],
        technical_specs: Dict[str, Any],
        author: str
    ) -> TechnicalDocument:
        """
        Create system description document.

        Args:
            description: General description of the AI system
            capabilities: List of system capabilities
            limitations: Known limitations
            technical_specs: Technical specifications
            author: Document author

        Returns:
            Created TechnicalDocument
        """
        content = {
            "system_name": self.ai_system_name,
            "system_id": self.ai_system_id,
            "description": description,
            "capabilities": capabilities,
            "limitations": limitations,
            "technical_specifications": technical_specs,
            "documentation_date": datetime.utcnow().isoformat()
        }

        doc = self._create_document(
            doc_type=DocumentationType.SYSTEM_DESCRIPTION,
            title=f"System Description - {self.ai_system_name}",
            content=content,
            author=author
        )
        return doc

    def create_intended_purpose(
        self,
        purpose: str,
        use_cases: List[Dict[str, str]],
        target_users: List[str],
        deployment_context: str,
        geographic_scope: List[str],
        author: str
    ) -> TechnicalDocument:
        """
        Document intended purpose per Article 11(1)(a).

        Args:
            purpose: Primary intended purpose
            use_cases: List of intended use cases
            target_users: Types of intended users
            deployment_context: Context of deployment
            geographic_scope: Geographic regions of deployment
            author: Document author

        Returns:
            Created TechnicalDocument
        """
        content = {
            "intended_purpose": purpose,
            "use_cases": use_cases,
            "target_users": target_users,
            "deployment_context": deployment_context,
            "geographic_scope": geographic_scope,
            "prohibited_uses": [],
            "documentation_date": datetime.utcnow().isoformat()
        }

        doc = self._create_document(
            doc_type=DocumentationType.INTENDED_PURPOSE,
            title=f"Intended Purpose - {self.ai_system_name}",
            content=content,
            author=author
        )
        return doc

    def create_risk_assessment_doc(
        self,
        assessments: List[RiskAssessment],
        overall_risk_level: RiskLevel,
        assessment_methodology: str,
        author: str
    ) -> TechnicalDocument:
        """
        Create risk assessment documentation.

        Args:
            assessments: List of individual risk assessments
            overall_risk_level: Overall system risk level
            assessment_methodology: Methodology used
            author: Document author

        Returns:
            Created TechnicalDocument
        """
        self._risk_assessments.extend(assessments)

        content = {
            "overall_risk_level": overall_risk_level.value,
            "assessment_methodology": assessment_methodology,
            "risk_assessments": [
                {
                    "risk_id": a.risk_id,
                    "description": a.risk_description,
                    "level": a.risk_level.value,
                    "likelihood": a.likelihood,
                    "impact": a.impact,
                    "risk_score": a.calculate_risk_score(),
                    "mitigation_measures": a.mitigation_measures,
                    "residual_risk": a.residual_risk
                }
                for a in assessments
            ],
            "total_risks_identified": len(assessments),
            "high_risk_count": sum(1 for a in assessments if a.risk_level == RiskLevel.HIGH),
            "assessment_date": datetime.utcnow().isoformat()
        }

        doc = self._create_document(
            doc_type=DocumentationType.RISK_ASSESSMENT,
            title=f"Risk Assessment - {self.ai_system_name}",
            content=content,
            author=author
        )
        return doc

    def create_data_governance_doc(
        self,
        training_data_description: str,
        data_sources: List[str],
        data_quality_measures: List[str],
        bias_mitigation: List[str],
        data_retention_policy: str,
        author: str
    ) -> TechnicalDocument:
        """
        Document data governance practices per Article 11(1)(d).

        Args:
            training_data_description: Description of training data
            data_sources: Sources of data
            data_quality_measures: Quality assurance measures
            bias_mitigation: Bias detection and mitigation measures
            data_retention_policy: Data retention policy
            author: Document author

        Returns:
            Created TechnicalDocument
        """
        content = {
            "training_data": {
                "description": training_data_description,
                "sources": data_sources
            },
            "data_quality_measures": data_quality_measures,
            "bias_detection_mitigation": bias_mitigation,
            "data_retention_policy": data_retention_policy,
            "gdpr_compliance": {
                "lawful_basis": "legitimate_interest",
                "data_minimization": True,
                "purpose_limitation": True
            },
            "documentation_date": datetime.utcnow().isoformat()
        }

        doc = self._create_document(
            doc_type=DocumentationType.DATA_GOVERNANCE,
            title=f"Data Governance - {self.ai_system_name}",
            content=content,
            author=author
        )
        return doc

    def create_testing_procedure_doc(
        self,
        test_methodology: str,
        test_cases: List[Dict[str, Any]],
        validation_metrics: Dict[str, float],
        test_results_summary: str,
        author: str
    ) -> TechnicalDocument:
        """
        Document testing and validation procedures.

        Args:
            test_methodology: Testing methodology description
            test_cases: List of test cases
            validation_metrics: Validation metrics and results
            test_results_summary: Summary of test results
            author: Document author

        Returns:
            Created TechnicalDocument
        """
        content = {
            "test_methodology": test_methodology,
            "test_cases": test_cases,
            "validation_metrics": validation_metrics,
            "test_results_summary": test_results_summary,
            "test_coverage": {
                "unit_tests": True,
                "integration_tests": True,
                "performance_tests": True,
                "bias_tests": True,
                "security_tests": True
            },
            "documentation_date": datetime.utcnow().isoformat()
        }

        doc = self._create_document(
            doc_type=DocumentationType.TESTING_PROCEDURE,
            title=f"Testing Procedures - {self.ai_system_name}",
            content=content,
            author=author
        )
        return doc

    def create_monitoring_plan(
        self,
        monitoring_objectives: List[str],
        kpis: Dict[str, Dict[str, Any]],
        alert_thresholds: Dict[str, float],
        review_frequency: str,
        author: str
    ) -> TechnicalDocument:
        """
        Document post-deployment monitoring plan.

        Args:
            monitoring_objectives: Objectives of monitoring
            kpis: Key performance indicators
            alert_thresholds: Thresholds for alerts
            review_frequency: Frequency of reviews
            author: Document author

        Returns:
            Created TechnicalDocument
        """
        content = {
            "monitoring_objectives": monitoring_objectives,
            "key_performance_indicators": kpis,
            "alert_thresholds": alert_thresholds,
            "review_frequency": review_frequency,
            "incident_response_plan": {
                "detection": "Automated monitoring with alerting",
                "response": "Immediate investigation and mitigation",
                "escalation": "Escalate to compliance team if unresolved"
            },
            "documentation_date": datetime.utcnow().isoformat()
        }

        doc = self._create_document(
            doc_type=DocumentationType.MONITORING_PLAN,
            title=f"Monitoring Plan - {self.ai_system_name}",
            content=content,
            author=author
        )
        return doc

    def _create_document(
        self,
        doc_type: DocumentationType,
        title: str,
        content: Dict[str, Any],
        author: str
    ) -> TechnicalDocument:
        """Internal method to create and store a document."""
        doc_id = self._generate_doc_id(doc_type)
        checksum = self._calculate_checksum(content)

        version = DocumentVersion(
            version="1.0.0",
            created_at=datetime.utcnow(),
            created_by=author,
            changes=["Initial document creation"],
            checksum=checksum
        )

        doc = TechnicalDocument(
            doc_id=doc_id,
            doc_type=doc_type,
            title=title,
            content=content,
            version=version,
            ai_system_id=self.ai_system_id
        )

        self._documents[doc_id] = doc
        self._version_history.append(version)
        return doc

    def update_document(
        self,
        doc_id: str,
        content_updates: Dict[str, Any],
        author: str,
        change_description: str
    ) -> Optional[TechnicalDocument]:
        """
        Update an existing document with new content.

        Args:
            doc_id: Document ID to update
            content_updates: Dictionary of content updates
            author: Update author
            change_description: Description of changes

        Returns:
            Updated document or None if not found
        """
        if doc_id not in self._documents:
            return None

        doc = self._documents[doc_id]

        # Merge updates into existing content
        doc.content.update(content_updates)
        doc.updated_at = datetime.utcnow()

        # Create new version
        current_version = doc.version.version.split(".")
        new_minor = int(current_version[1]) + 1
        new_version_str = f"{current_version[0]}.{new_minor}.0"

        doc.version = DocumentVersion(
            version=new_version_str,
            created_at=datetime.utcnow(),
            created_by=author,
            changes=[change_description],
            checksum=self._calculate_checksum(doc.content)
        )

        self._version_history.append(doc.version)
        return doc

    def approve_document(self, doc_id: str, approver: str) -> bool:
        """
        Mark a document as approved.

        Args:
            doc_id: Document ID to approve
            approver: Name of approver

        Returns:
            True if approved successfully
        """
        if doc_id not in self._documents:
            return False

        self._documents[doc_id].approved = True
        self._documents[doc_id].approved_by = approver
        return True

    def get_document(self, doc_id: str) -> Optional[TechnicalDocument]:
        """Retrieve a document by ID."""
        return self._documents.get(doc_id)

    def get_documents_by_type(self, doc_type: DocumentationType) -> List[TechnicalDocument]:
        """Retrieve all documents of a specific type."""
        return [
            doc for doc in self._documents.values()
            if doc.doc_type == doc_type
        ]

    def get_all_documents(self) -> List[TechnicalDocument]:
        """Retrieve all documents."""
        return list(self._documents.values())

    def get_compliance_status(self) -> Dict[str, Any]:
        """
        Check documentation compliance status.

        Returns:
            Dictionary with compliance status for each document type
        """
        required_types = [
            DocumentationType.SYSTEM_DESCRIPTION,
            DocumentationType.INTENDED_PURPOSE,
            DocumentationType.RISK_ASSESSMENT,
            DocumentationType.DATA_GOVERNANCE,
            DocumentationType.TESTING_PROCEDURE,
            DocumentationType.MONITORING_PLAN
        ]

        status = {}
        for doc_type in required_types:
            docs = self.get_documents_by_type(doc_type)
            approved_docs = [d for d in docs if d.approved]
            status[doc_type.value] = {
                "exists": len(docs) > 0,
                "approved": len(approved_docs) > 0,
                "document_count": len(docs),
                "approved_count": len(approved_docs)
            }

        # Calculate overall compliance
        compliant_types = sum(1 for s in status.values() if s["exists"] and s["approved"])
        overall_compliance = compliant_types / len(required_types) if required_types else 0.0

        return {
            "ai_system_id": self.ai_system_id,
            "ai_system_name": self.ai_system_name,
            "document_types": status,
            "overall_compliance": overall_compliance,
            "fully_compliant": overall_compliance == 1.0,
            "total_documents": len(self._documents),
            "assessment_date": datetime.utcnow().isoformat()
        }

    def export_documentation(self) -> Dict[str, Any]:
        """Export all documentation as a dictionary."""
        return {
            "ai_system_id": self.ai_system_id,
            "ai_system_name": self.ai_system_name,
            "documents": [doc.to_dict() for doc in self._documents.values()],
            "risk_assessments": [
                {
                    "risk_id": r.risk_id,
                    "description": r.risk_description,
                    "level": r.risk_level.value,
                    "score": r.calculate_risk_score()
                }
                for r in self._risk_assessments
            ],
            "export_date": datetime.utcnow().isoformat()
        }
