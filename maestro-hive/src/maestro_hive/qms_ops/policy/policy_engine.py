"""
Policy Engine Module
=====================

Intelligent policy and document management for QMS compliance.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set


class DocumentType(Enum):
    """QMS document types."""
    POLICY = "policy"
    PROCEDURE = "procedure"
    WORK_INSTRUCTION = "work_instruction"
    FORM = "form"
    TEMPLATE = "template"
    RECORD = "record"
    SPECIFICATION = "specification"
    GUIDELINE = "guideline"


class DocumentStatus(Enum):
    """Document lifecycle status."""
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    EFFECTIVE = "effective"
    SUPERSEDED = "superseded"
    OBSOLETE = "obsolete"


class ReviewResult(Enum):
    """Document review outcomes."""
    APPROVED = "approved"
    REJECTED = "rejected"
    REVISION_REQUIRED = "revision_required"


class ComplianceStatus(Enum):
    """Compliance status levels."""
    COMPLIANT = "compliant"
    MINOR_GAPS = "minor_gaps"
    MAJOR_GAPS = "major_gaps"
    NON_COMPLIANT = "non_compliant"


@dataclass
class RegulatoryRequirement:
    """Regulatory requirement reference."""
    id: str
    regulation: str  # e.g., "ISO 13485:2016"
    clause: str      # e.g., "4.2.4"
    description: str
    requirement_type: str  # "mandatory", "should", "may"


@dataclass
class DocumentVersion:
    """Document version record."""
    version: str
    created_at: datetime
    created_by: str
    change_summary: str
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None


@dataclass
class Document:
    """QMS document record."""
    id: str
    title: str
    doc_type: DocumentType
    status: DocumentStatus
    owner: str
    department: str
    current_version: str
    effective_date: Optional[datetime] = None
    review_date: Optional[datetime] = None
    content_hash: str = ""
    regulatory_refs: List[RegulatoryRequirement] = field(default_factory=list)
    versions: List[DocumentVersion] = field(default_factory=list)
    tags: Set[str] = field(default_factory=set)
    linked_documents: List[str] = field(default_factory=list)
    training_required: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_due_for_review(self) -> bool:
        """Check if document is due for periodic review."""
        if not self.review_date:
            return False
        return datetime.utcnow() >= self.review_date

    @property
    def days_until_review(self) -> Optional[int]:
        """Days until next review."""
        if not self.review_date:
            return None
        return (self.review_date - datetime.utcnow()).days


@dataclass
class ComplianceMapping:
    """Mapping of documents to regulatory requirements."""
    requirement_id: str
    document_ids: List[str]
    coverage_percentage: float
    gaps: List[str]
    last_assessed: datetime


@dataclass
class PolicyReview:
    """Policy review record."""
    id: str
    document_id: str
    reviewer: str
    result: ReviewResult
    comments: str
    reviewed_at: datetime
    changes_required: List[str] = field(default_factory=list)


class DocumentWorkflow:
    """Manages document approval workflow."""

    ALLOWED_TRANSITIONS = {
        DocumentStatus.DRAFT: [DocumentStatus.UNDER_REVIEW],
        DocumentStatus.UNDER_REVIEW: [DocumentStatus.DRAFT, DocumentStatus.APPROVED],
        DocumentStatus.APPROVED: [DocumentStatus.EFFECTIVE],
        DocumentStatus.EFFECTIVE: [DocumentStatus.UNDER_REVIEW, DocumentStatus.SUPERSEDED, DocumentStatus.OBSOLETE],
        DocumentStatus.SUPERSEDED: [],
        DocumentStatus.OBSOLETE: [],
    }

    @classmethod
    def can_transition(cls, from_status: DocumentStatus, to_status: DocumentStatus) -> bool:
        """Check if status transition is allowed."""
        return to_status in cls.ALLOWED_TRANSITIONS.get(from_status, [])

    @classmethod
    def get_next_statuses(cls, current: DocumentStatus) -> List[DocumentStatus]:
        """Get allowed next statuses."""
        return cls.ALLOWED_TRANSITIONS.get(current, [])


class ComplianceChecker:
    """Checks document compliance against regulations."""

    # Standard regulatory frameworks
    FRAMEWORKS = {
        "ISO_13485_2016": {
            "4.2.3": "Control of documents",
            "4.2.4": "Control of records",
            "4.2.5": "Document changes",
            "5.5.3": "Internal communication",
            "6.2.2": "Competence, training and awareness",
            "7.3.1": "Design and development planning",
            "7.5.1": "Control of production",
            "8.2.1": "Feedback",
            "8.2.2": "Complaint handling",
            "8.2.4": "Internal audit",
            "8.5.1": "Improvement",
            "8.5.2": "Corrective action",
            "8.5.3": "Preventive action",
        },
        "FDA_21_CFR_820": {
            "820.20": "Management responsibility",
            "820.22": "Quality audit",
            "820.25": "Personnel",
            "820.30": "Design controls",
            "820.40": "Document controls",
            "820.50": "Purchasing controls",
            "820.70": "Production and process controls",
            "820.90": "Nonconforming product",
            "820.100": "Corrective and preventive action",
            "820.180": "General requirements - records",
            "820.184": "Device history record",
        },
        "EU_MDR_2017_745": {
            "10.9": "Post-market surveillance",
            "10.10": "Reporting of serious incidents",
            "83": "Notified body requirements",
            "Annex_II": "Technical documentation",
            "Annex_IX": "Quality management system",
        }
    }

    def check_compliance(
        self,
        documents: List[Document],
        framework: str
    ) -> Dict[str, ComplianceMapping]:
        """
        Check document compliance against a regulatory framework.

        Args:
            documents: List of documents to check
            framework: Regulatory framework to check against

        Returns:
            Dictionary of requirement ID to ComplianceMapping
        """
        requirements = self.FRAMEWORKS.get(framework, {})
        mappings = {}

        for req_id, req_desc in requirements.items():
            # Find documents that address this requirement
            matching_docs = []
            for doc in documents:
                # Check if document references this requirement
                for ref in doc.regulatory_refs:
                    if ref.clause == req_id or req_id in ref.clause:
                        matching_docs.append(doc.id)
                        break
                # Also check tags
                if req_id in doc.tags or framework.lower() in [t.lower() for t in doc.tags]:
                    if doc.id not in matching_docs:
                        matching_docs.append(doc.id)

            # Calculate coverage
            coverage = min(1.0, len(matching_docs) / 1)  # At least 1 doc per requirement
            gaps = [] if matching_docs else [f"No document addresses {framework} {req_id}: {req_desc}"]

            mappings[req_id] = ComplianceMapping(
                requirement_id=req_id,
                document_ids=matching_docs,
                coverage_percentage=coverage * 100,
                gaps=gaps,
                last_assessed=datetime.utcnow()
            )

        return mappings

    def get_compliance_score(self, mappings: Dict[str, ComplianceMapping]) -> float:
        """Calculate overall compliance score."""
        if not mappings:
            return 0.0
        total_coverage = sum(m.coverage_percentage for m in mappings.values())
        return total_coverage / len(mappings)

    def get_compliance_status(self, score: float) -> ComplianceStatus:
        """Determine compliance status from score."""
        if score >= 95:
            return ComplianceStatus.COMPLIANT
        elif score >= 80:
            return ComplianceStatus.MINOR_GAPS
        elif score >= 60:
            return ComplianceStatus.MAJOR_GAPS
        else:
            return ComplianceStatus.NON_COMPLIANT


class PolicyEngine:
    """
    Intelligent policy and document management engine.

    Provides automated document control, compliance checking,
    and policy lifecycle management.
    """

    def __init__(self):
        self.documents: Dict[str, Document] = {}
        self.reviews: Dict[str, List[PolicyReview]] = {}
        self.compliance_checker = ComplianceChecker()
        self.event_handlers: Dict[str, List[Callable]] = {}
        self.logger = logging.getLogger("qms-policy")
        self._configure_logger()

    def _configure_logger(self) -> None:
        """Configure logger."""
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def create_document(
        self,
        title: str,
        doc_type: DocumentType,
        owner: str,
        department: str,
        content_hash: str = "",
        regulatory_refs: List[RegulatoryRequirement] = None,
        review_period_days: int = 365,
        training_required: bool = False
    ) -> Document:
        """
        Create a new document.

        Args:
            title: Document title
            doc_type: Type of document
            owner: Document owner
            department: Owning department
            content_hash: Hash of document content
            regulatory_refs: Regulatory references
            review_period_days: Days between reviews
            training_required: Whether training is required

        Returns:
            Created Document
        """
        import uuid

        doc_id = f"DOC-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
        now = datetime.utcnow()

        initial_version = DocumentVersion(
            version="1.0",
            created_at=now,
            created_by=owner,
            change_summary="Initial version"
        )

        document = Document(
            id=doc_id,
            title=title,
            doc_type=doc_type,
            status=DocumentStatus.DRAFT,
            owner=owner,
            department=department,
            current_version="1.0",
            content_hash=content_hash,
            regulatory_refs=regulatory_refs or [],
            versions=[initial_version],
            training_required=training_required,
            review_date=now + timedelta(days=review_period_days)
        )

        self.documents[doc_id] = document
        self.reviews[doc_id] = []

        self.logger.info(
            f"DOCUMENT_CREATED | id={doc_id} | title={title} | "
            f"type={doc_type.value} | owner={owner}"
        )
        self._trigger_event("document_created", document)

        return document

    def get_document(self, doc_id: str) -> Optional[Document]:
        """Get document by ID."""
        return self.documents.get(doc_id)

    def update_status(
        self,
        doc_id: str,
        new_status: DocumentStatus,
        updated_by: str
    ) -> Document:
        """
        Update document status with workflow validation.

        Args:
            doc_id: Document ID
            new_status: New status
            updated_by: User making the update

        Returns:
            Updated Document
        """
        document = self.get_document(doc_id)
        if not document:
            raise ValueError(f"Document {doc_id} not found")

        if not DocumentWorkflow.can_transition(document.status, new_status):
            raise ValueError(
                f"Cannot transition from {document.status.value} to {new_status.value}"
            )

        old_status = document.status
        document.status = new_status
        document.updated_at = datetime.utcnow()

        if new_status == DocumentStatus.EFFECTIVE:
            document.effective_date = datetime.utcnow()

        self.logger.info(
            f"DOCUMENT_STATUS_CHANGED | id={doc_id} | from={old_status.value} | "
            f"to={new_status.value} | by={updated_by}"
        )
        self._trigger_event("status_changed", document, old_status, new_status)

        return document

    def submit_for_review(self, doc_id: str, submitted_by: str) -> Document:
        """Submit document for review."""
        return self.update_status(doc_id, DocumentStatus.UNDER_REVIEW, submitted_by)

    def review_document(
        self,
        doc_id: str,
        reviewer: str,
        result: ReviewResult,
        comments: str,
        changes_required: List[str] = None
    ) -> PolicyReview:
        """
        Record a document review.

        Args:
            doc_id: Document ID
            reviewer: Reviewer name
            result: Review result
            comments: Review comments
            changes_required: List of required changes

        Returns:
            PolicyReview record
        """
        import uuid

        document = self.get_document(doc_id)
        if not document:
            raise ValueError(f"Document {doc_id} not found")

        review = PolicyReview(
            id=f"REV-{str(uuid.uuid4())[:8].upper()}",
            document_id=doc_id,
            reviewer=reviewer,
            result=result,
            comments=comments,
            reviewed_at=datetime.utcnow(),
            changes_required=changes_required or []
        )

        self.reviews[doc_id].append(review)

        # Update document status based on result
        if result == ReviewResult.APPROVED:
            self.update_status(doc_id, DocumentStatus.APPROVED, reviewer)
        elif result == ReviewResult.REJECTED:
            self.update_status(doc_id, DocumentStatus.DRAFT, reviewer)

        self.logger.info(
            f"DOCUMENT_REVIEWED | id={doc_id} | reviewer={reviewer} | result={result.value}"
        )

        return review

    def make_effective(self, doc_id: str, approved_by: str) -> Document:
        """Make an approved document effective."""
        document = self.get_document(doc_id)
        if not document:
            raise ValueError(f"Document {doc_id} not found")

        if document.status != DocumentStatus.APPROVED:
            raise ValueError("Document must be approved before making effective")

        # Mark current version as approved
        if document.versions:
            document.versions[-1].approved_by = approved_by
            document.versions[-1].approved_at = datetime.utcnow()

        return self.update_status(doc_id, DocumentStatus.EFFECTIVE, approved_by)

    def create_revision(
        self,
        doc_id: str,
        change_summary: str,
        revised_by: str,
        new_content_hash: str = ""
    ) -> Document:
        """
        Create a new revision of a document.

        Args:
            doc_id: Document ID
            change_summary: Description of changes
            revised_by: User creating revision
            new_content_hash: Hash of new content

        Returns:
            Revised Document
        """
        document = self.get_document(doc_id)
        if not document:
            raise ValueError(f"Document {doc_id} not found")

        # Calculate new version
        current = document.current_version
        major, minor = map(int, current.split('.'))
        new_version = f"{major}.{minor + 1}"

        # Add new version
        version = DocumentVersion(
            version=new_version,
            created_at=datetime.utcnow(),
            created_by=revised_by,
            change_summary=change_summary
        )
        document.versions.append(version)
        document.current_version = new_version
        document.content_hash = new_content_hash or document.content_hash
        document.status = DocumentStatus.DRAFT
        document.updated_at = datetime.utcnow()

        self.logger.info(
            f"DOCUMENT_REVISED | id={doc_id} | version={new_version} | by={revised_by}"
        )

        return document

    def check_compliance(self, framework: str) -> Dict[str, Any]:
        """
        Check compliance against a regulatory framework.

        Args:
            framework: Framework identifier (e.g., "ISO_13485_2016")

        Returns:
            Compliance assessment results
        """
        documents = [d for d in self.documents.values() if d.status == DocumentStatus.EFFECTIVE]
        mappings = self.compliance_checker.check_compliance(documents, framework)
        score = self.compliance_checker.get_compliance_score(mappings)
        status = self.compliance_checker.get_compliance_status(score)

        gaps = []
        for mapping in mappings.values():
            gaps.extend(mapping.gaps)

        result = {
            "framework": framework,
            "score": score,
            "status": status.value,
            "requirements_checked": len(mappings),
            "requirements_covered": len([m for m in mappings.values() if m.coverage_percentage == 100]),
            "gaps": gaps,
            "assessed_at": datetime.utcnow().isoformat()
        }

        self.logger.info(
            f"COMPLIANCE_CHECKED | framework={framework} | score={score:.1f}% | status={status.value}"
        )

        return result

    def get_documents_due_for_review(self) -> List[Document]:
        """Get documents due for periodic review."""
        return [d for d in self.documents.values() if d.is_due_for_review]

    def get_documents_by_status(self, status: DocumentStatus) -> List[Document]:
        """Get documents by status."""
        return [d for d in self.documents.values() if d.status == status]

    def get_documents_by_type(self, doc_type: DocumentType) -> List[Document]:
        """Get documents by type."""
        return [d for d in self.documents.values() if d.doc_type == doc_type]

    def get_statistics(self) -> Dict[str, Any]:
        """Get document statistics."""
        all_docs = list(self.documents.values())
        return {
            "total_documents": len(all_docs),
            "by_status": {
                status.value: len([d for d in all_docs if d.status == status])
                for status in DocumentStatus
            },
            "by_type": {
                dtype.value: len([d for d in all_docs if d.doc_type == dtype])
                for dtype in DocumentType
            },
            "due_for_review": len(self.get_documents_due_for_review()),
            "training_required": len([d for d in all_docs if d.training_required])
        }

    def on_event(self, event_name: str, handler: Callable) -> None:
        """Register an event handler."""
        if event_name not in self.event_handlers:
            self.event_handlers[event_name] = []
        self.event_handlers[event_name].append(handler)

    def _trigger_event(self, event_name: str, *args, **kwargs) -> None:
        """Trigger event handlers."""
        for handler in self.event_handlers.get(event_name, []):
            try:
                handler(*args, **kwargs)
            except Exception as e:
                self.logger.error(f"Event handler error: {e}")
