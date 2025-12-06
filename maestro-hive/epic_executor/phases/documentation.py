"""
Phase 2: Documentation

Generate and publish compliance documents to Confluence.
This phase creates the 6 required documents for 15 compliance points.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from ..models import (
    DocumentInfo,
    DocumentType,
    EpicInfo,
    ExecutionPhase,
    PhaseResult,
)
from ..confluence.publisher import ConfluencePublisher, ConfluenceConfig


@dataclass
class DocumentationResult:
    """Result from the documentation phase."""
    documents: List[DocumentInfo]
    confluence_links: List[str]
    points_earned: float  # Out of 15


class DocumentationPhase:
    """
    Phase 2: Documentation Generation

    Responsibilities:
    1. Generate 6 compliance documents
    2. Publish to Confluence
    3. Link documents to EPIC
    4. Calculate documentation score (15 points max)
    """

    # Points per document
    DOCUMENT_POINTS = {
        DocumentType.TECHNICAL_DESIGN: 5.0,
        DocumentType.RUNBOOK: 2.5,
        DocumentType.API_DOCS: 2.5,
        DocumentType.ADR: 2.0,
        DocumentType.CONFIG_GUIDE: 1.5,
        DocumentType.MONITORING: 1.5,
    }

    def __init__(self, confluence_config: ConfluenceConfig):
        """
        Initialize the documentation phase.

        Args:
            confluence_config: Confluence API configuration
        """
        self.confluence_config = confluence_config
        self.publisher = ConfluencePublisher(confluence_config)

    async def execute(
        self,
        epic_info: EpicInfo,
        implementation_context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[PhaseResult, Optional[DocumentationResult]]:
        """
        Execute the documentation phase.

        Args:
            epic_info: EPIC information
            implementation_context: Additional context from implementation phase

        Returns:
            Tuple of (PhaseResult, DocumentationResult or None if failed)
        """
        started_at = datetime.now()
        errors: List[str] = []
        warnings: List[str] = []
        artifacts: List[str] = []

        try:
            # Prepare context for templates
            context = implementation_context or {}
            context.setdefault("implementation_files", [])
            context.setdefault("test_files", [])

            # Publish all documents
            documents = await self.publisher.publish_all_documents(
                epic_info=epic_info,
                context=context,
            )

            # Collect results
            confluence_links = []
            points_earned = 0.0

            for doc in documents:
                if doc.confluence_url:
                    confluence_links.append(f"{doc.title}: {doc.confluence_url}")
                    points = self.DOCUMENT_POINTS.get(doc.doc_type, 0)
                    points_earned += points
                    artifacts.append(f"Created {doc.doc_type.value}: {doc.title}")

            # Check for missing documents
            created_types = {doc.doc_type for doc in documents}
            for doc_type in DocumentType:
                if doc_type not in created_types:
                    warnings.append(f"Failed to create {doc_type.value} document")

            # Build result
            doc_result = DocumentationResult(
                documents=documents,
                confluence_links=confluence_links,
                points_earned=points_earned,
            )

            completed_at = datetime.now()
            duration = (completed_at - started_at).total_seconds()

            phase_result = PhaseResult(
                phase=ExecutionPhase.DOCUMENTATION,
                success=len(documents) > 0,
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=duration,
                artifacts_created=artifacts,
                errors=errors,
                warnings=warnings,
                metrics={
                    "documents_created": len(documents),
                    "documents_expected": len(DocumentType),
                    "points_earned": points_earned,
                    "points_max": 15.0,
                }
            )

            return phase_result, doc_result

        except Exception as e:
            errors.append(str(e))
            completed_at = datetime.now()
            duration = (completed_at - started_at).total_seconds()

            phase_result = PhaseResult(
                phase=ExecutionPhase.DOCUMENTATION,
                success=False,
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=duration,
                artifacts_created=artifacts,
                errors=errors,
                warnings=warnings,
            )

            return phase_result, None

    async def verify_documents(
        self,
        documents: List[DocumentInfo],
    ) -> Dict[str, bool]:
        """
        Verify that all documents exist and are accessible.

        Args:
            documents: List of documents to verify

        Returns:
            Dict mapping document type to verification status
        """
        verification = {}

        for doc in documents:
            if doc.confluence_page_id and doc.confluence_url:
                # TODO: Actually verify page exists via API
                verification[doc.doc_type.value] = True
            else:
                verification[doc.doc_type.value] = False

        return verification
