"""
Knowledge Contributor - Enable AI agents to contribute knowledge

Implements:
- AC-2543-5: Enable knowledge contribution from AI agents
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
from uuid import UUID, uuid4

from .models import (
    KnowledgeArtifact,
    KnowledgeType,
    KnowledgeStatus,
    KnowledgeMetadata,
    KnowledgeContribution,
    ContributorType,
)
from .store import KnowledgeStore
from .indexer import KnowledgeIndexer


logger = logging.getLogger(__name__)


class ContributionStatus(Enum):
    """Status of a contribution."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    MERGED = "merged"


@dataclass
class ContributionProposal:
    """A proposed contribution to the knowledge store."""
    id: UUID = field(default_factory=uuid4)
    contributor_id: str = ""
    contributor_type: ContributorType = ContributorType.AI_AGENT
    contribution_type: str = "create"  # create, update, validate, deprecate
    status: ContributionStatus = ContributionStatus.PENDING
    
    # Proposed artifact (for create) or changes (for update)
    artifact: Optional[KnowledgeArtifact] = None
    target_artifact_id: Optional[UUID] = None
    changes: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    rationale: str = ""
    evidence: List[str] = field(default_factory=list)
    confidence: float = 0.8
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None
    review_notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize proposal to dictionary."""
        return {
            "id": str(self.id),
            "contributor_id": self.contributor_id,
            "contributor_type": self.contributor_type.value,
            "contribution_type": self.contribution_type,
            "status": self.status.value,
            "artifact": self.artifact.to_dict() if self.artifact else None,
            "target_artifact_id": str(self.target_artifact_id) if self.target_artifact_id else None,
            "changes": self.changes,
            "rationale": self.rationale,
            "evidence": self.evidence,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat(),
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "reviewed_by": self.reviewed_by,
            "review_notes": self.review_notes,
        }


class KnowledgeContributor:
    """
    Manages knowledge contributions from AI agents and other sources.
    
    Features:
    - Contribution proposal workflow
    - Auto-approval for trusted contributors
    - Quality validation
    - Deduplication checking
    """
    
    # Confidence threshold for auto-approval
    DEFAULT_AUTO_APPROVE_THRESHOLD = 0.9
    
    # Trusted contributor types for auto-approval
    TRUSTED_CONTRIBUTORS = {ContributorType.SYSTEM}
    
    def __init__(
        self,
        store: KnowledgeStore,
        indexer: KnowledgeIndexer,
        auto_approve_threshold: float = DEFAULT_AUTO_APPROVE_THRESHOLD,
        auto_approve_types: Optional[set] = None,
        validation_hook: Optional[Callable[[ContributionProposal], bool]] = None,
    ):
        """
        Initialize the contributor manager.
        
        Args:
            store: Knowledge store instance
            indexer: Knowledge indexer instance
            auto_approve_threshold: Confidence threshold for auto-approval
            auto_approve_types: Contributor types eligible for auto-approval
            validation_hook: Custom validation function
        """
        self.store = store
        self.indexer = indexer
        self.auto_approve_threshold = auto_approve_threshold
        self.auto_approve_types = auto_approve_types or self.TRUSTED_CONTRIBUTORS
        self.validation_hook = validation_hook
        
        # Pending proposals
        self._proposals: Dict[UUID, ContributionProposal] = {}
        
        logger.info("KnowledgeContributor initialized")
    
    def propose_knowledge(
        self,
        title: str,
        content: str,
        knowledge_type: KnowledgeType,
        contributor_id: str,
        contributor_type: ContributorType = ContributorType.AI_AGENT,
        domain: str = "",
        tags: Optional[List[str]] = None,
        rationale: str = "",
        evidence: Optional[List[str]] = None,
        confidence: float = 0.8,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ContributionProposal:
        """
        Propose new knowledge for addition to the store.
        
        Args:
            title: Knowledge title
            content: Knowledge content
            knowledge_type: Type of knowledge
            contributor_id: ID of contributing entity
            contributor_type: Type of contributor
            domain: Knowledge domain
            tags: Classification tags
            rationale: Why this knowledge should be added
            evidence: Supporting evidence
            confidence: Contributor's confidence in this knowledge
            metadata: Additional metadata
        
        Returns:
            ContributionProposal
        """
        # Create artifact
        artifact = KnowledgeArtifact(
            title=title,
            content=content,
            knowledge_type=knowledge_type,
            metadata=KnowledgeMetadata(
                domain=domain,
                tags=tags or [],
                confidence=confidence,
                custom=metadata or {},
            ),
        )
        artifact.keywords = artifact.extract_keywords()
        
        # Create proposal
        proposal = ContributionProposal(
            contributor_id=contributor_id,
            contributor_type=contributor_type,
            contribution_type="create",
            artifact=artifact,
            rationale=rationale,
            evidence=evidence or [],
            confidence=confidence,
        )
        
        # Validate proposal
        if not self._validate_proposal(proposal):
            proposal.status = ContributionStatus.REJECTED
            proposal.review_notes = "Failed validation"
            logger.warning("Proposal %s failed validation", proposal.id)
            return proposal
        
        # Check for duplicates
        duplicate = self._check_duplicate(artifact)
        if duplicate:
            proposal.status = ContributionStatus.REJECTED
            proposal.review_notes = f"Duplicate of existing artifact: {duplicate}"
            logger.warning("Proposal %s is duplicate of %s", proposal.id, duplicate)
            return proposal
        
        # Auto-approve if criteria met
        if self._should_auto_approve(proposal):
            return self._approve_and_store(proposal, "auto-approved")
        
        # Store for manual review
        self._proposals[proposal.id] = proposal
        logger.info(
            "Proposal %s from %s pending review",
            proposal.id,
            contributor_id,
        )
        
        return proposal
    
    def propose_update(
        self,
        artifact_id: UUID,
        changes: Dict[str, Any],
        contributor_id: str,
        contributor_type: ContributorType = ContributorType.AI_AGENT,
        rationale: str = "",
        evidence: Optional[List[str]] = None,
        confidence: float = 0.8,
    ) -> ContributionProposal:
        """
        Propose an update to existing knowledge.
        
        Args:
            artifact_id: ID of artifact to update
            changes: Dictionary of changes (field: new_value)
            contributor_id: ID of contributing entity
            contributor_type: Type of contributor
            rationale: Why this update should be made
            evidence: Supporting evidence
            confidence: Confidence in the update
        
        Returns:
            ContributionProposal
        """
        # Verify artifact exists
        artifact = self.store.get(artifact_id)
        if not artifact:
            proposal = ContributionProposal(
                contributor_id=contributor_id,
                contributor_type=contributor_type,
                contribution_type="update",
                target_artifact_id=artifact_id,
                changes=changes,
                status=ContributionStatus.REJECTED,
                review_notes="Target artifact not found",
            )
            return proposal
        
        proposal = ContributionProposal(
            contributor_id=contributor_id,
            contributor_type=contributor_type,
            contribution_type="update",
            target_artifact_id=artifact_id,
            changes=changes,
            rationale=rationale,
            evidence=evidence or [],
            confidence=confidence,
        )
        
        # Auto-approve if criteria met
        if self._should_auto_approve(proposal):
            return self._apply_update(proposal, "auto-approved")
        
        # Store for manual review
        self._proposals[proposal.id] = proposal
        logger.info(
            "Update proposal %s for artifact %s pending review",
            proposal.id,
            artifact_id,
        )
        
        return proposal
    
    def propose_validation(
        self,
        artifact_id: UUID,
        contributor_id: str,
        contributor_type: ContributorType = ContributorType.AI_AGENT,
        rationale: str = "",
        confidence_adjustment: float = 0.0,
    ) -> ContributionProposal:
        """
        Propose validation of existing knowledge.
        
        Args:
            artifact_id: ID of artifact to validate
            contributor_id: ID of validator
            contributor_type: Type of contributor
            rationale: Validation rationale
            confidence_adjustment: Adjustment to confidence (-0.2 to +0.2)
        
        Returns:
            ContributionProposal
        """
        artifact = self.store.get(artifact_id)
        if not artifact:
            return ContributionProposal(
                contributor_id=contributor_id,
                contribution_type="validate",
                target_artifact_id=artifact_id,
                status=ContributionStatus.REJECTED,
                review_notes="Target artifact not found",
            )
        
        # Clamp adjustment
        adjustment = max(-0.2, min(0.2, confidence_adjustment))
        
        proposal = ContributionProposal(
            contributor_id=contributor_id,
            contributor_type=contributor_type,
            contribution_type="validate",
            target_artifact_id=artifact_id,
            changes={"confidence_adjustment": adjustment},
            rationale=rationale,
        )
        
        # Validations are typically auto-approved
        return self._apply_validation(proposal)
    
    def review_proposal(
        self,
        proposal_id: UUID,
        approved: bool,
        reviewer_id: str,
        notes: str = "",
    ) -> ContributionProposal:
        """
        Review a pending proposal.
        
        Args:
            proposal_id: ID of proposal to review
            approved: Whether to approve
            reviewer_id: ID of reviewer
            notes: Review notes
        
        Returns:
            Updated proposal
        """
        proposal = self._proposals.get(proposal_id)
        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found")
        
        proposal.reviewed_at = datetime.utcnow()
        proposal.reviewed_by = reviewer_id
        proposal.review_notes = notes
        
        if approved:
            if proposal.contribution_type == "create":
                return self._approve_and_store(proposal, reviewer_id)
            elif proposal.contribution_type == "update":
                return self._apply_update(proposal, reviewer_id)
        else:
            proposal.status = ContributionStatus.REJECTED
            logger.info("Proposal %s rejected by %s", proposal_id, reviewer_id)
        
        return proposal
    
    def _validate_proposal(self, proposal: ContributionProposal) -> bool:
        """Validate a proposal meets quality criteria."""
        if proposal.contribution_type == "create" and proposal.artifact:
            artifact = proposal.artifact
            
            # Check minimum content length
            if len(artifact.content) < 20:
                return False
            
            # Check title exists
            if not artifact.title or len(artifact.title) < 3:
                return False
        
        # Run custom validation hook if provided
        if self.validation_hook:
            return self.validation_hook(proposal)
        
        return True
    
    def _check_duplicate(self, artifact: KnowledgeArtifact) -> Optional[UUID]:
        """Check if artifact is duplicate of existing knowledge."""
        # Simple title-based check
        existing = self.store.get_by_title(artifact.title)
        if existing:
            return existing.id
        
        # Could add more sophisticated duplicate detection here
        # (semantic similarity, content hashing, etc.)
        
        return None
    
    def _should_auto_approve(self, proposal: ContributionProposal) -> bool:
        """Check if proposal should be auto-approved."""
        # Auto-approve trusted contributors
        if proposal.contributor_type in self.auto_approve_types:
            return True
        
        # Auto-approve high-confidence proposals
        if proposal.confidence >= self.auto_approve_threshold:
            return True
        
        return False
    
    def _approve_and_store(
        self,
        proposal: ContributionProposal,
        approved_by: str,
    ) -> ContributionProposal:
        """Approve proposal and store the artifact."""
        artifact = proposal.artifact
        if not artifact:
            raise ValueError("No artifact in proposal")
        
        # Add contribution record
        contribution = KnowledgeContribution(
            artifact_id=artifact.id,
            contributor_id=proposal.contributor_id,
            contributor_type=proposal.contributor_type,
            contribution_type="create",
            rationale=proposal.rationale,
            approved=True,
            approved_by=approved_by,
            approved_at=datetime.utcnow(),
        )
        artifact.add_contribution(contribution)
        
        # Store and index
        self.store.store(artifact)
        self.indexer.index_artifact(artifact)
        
        # Update proposal status
        proposal.status = ContributionStatus.MERGED
        proposal.reviewed_at = datetime.utcnow()
        proposal.reviewed_by = approved_by
        
        logger.info(
            "Proposal %s approved, artifact %s stored",
            proposal.id,
            artifact.id,
        )
        
        return proposal
    
    def _apply_update(
        self,
        proposal: ContributionProposal,
        approved_by: str,
    ) -> ContributionProposal:
        """Apply update proposal to artifact."""
        artifact = self.store.get(proposal.target_artifact_id)
        if not artifact:
            proposal.status = ContributionStatus.REJECTED
            proposal.review_notes = "Target artifact no longer exists"
            return proposal
        
        # Apply changes
        for field, value in proposal.changes.items():
            if hasattr(artifact, field):
                setattr(artifact, field, value)
            elif hasattr(artifact.metadata, field):
                setattr(artifact.metadata, field, value)
        
        # Add contribution record
        contribution = KnowledgeContribution(
            artifact_id=artifact.id,
            contributor_id=proposal.contributor_id,
            contributor_type=proposal.contributor_type,
            contribution_type="update",
            changes=proposal.changes,
            rationale=proposal.rationale,
            approved=True,
            approved_by=approved_by,
            approved_at=datetime.utcnow(),
        )
        artifact.add_contribution(contribution)
        
        # Update store and index
        self.store.update(
            artifact,
            contributor_id=proposal.contributor_id,
            contributor_type=proposal.contributor_type,
            changelog=proposal.rationale,
        )
        self.indexer.index_artifact(artifact)
        
        proposal.status = ContributionStatus.MERGED
        proposal.reviewed_at = datetime.utcnow()
        proposal.reviewed_by = approved_by
        
        logger.info(
            "Update proposal %s applied to artifact %s",
            proposal.id,
            artifact.id,
        )
        
        return proposal
    
    def _apply_validation(
        self,
        proposal: ContributionProposal,
    ) -> ContributionProposal:
        """Apply validation to artifact."""
        artifact = self.store.get(proposal.target_artifact_id)
        if not artifact:
            proposal.status = ContributionStatus.REJECTED
            return proposal
        
        # Update validation metadata
        artifact.metadata.last_validated = datetime.utcnow()
        artifact.metadata.validation_count += 1
        
        # Apply confidence adjustment
        adjustment = proposal.changes.get("confidence_adjustment", 0)
        new_confidence = max(0, min(1, artifact.metadata.confidence + adjustment))
        artifact.metadata.confidence = new_confidence
        
        # Add contribution record
        contribution = KnowledgeContribution(
            artifact_id=artifact.id,
            contributor_id=proposal.contributor_id,
            contributor_type=proposal.contributor_type,
            contribution_type="validate",
            rationale=proposal.rationale,
            approved=True,
            approved_by="auto",
            approved_at=datetime.utcnow(),
        )
        artifact.add_contribution(contribution)
        
        # Update store
        self.store.update(
            artifact,
            bump_version="patch",
            contributor_id=proposal.contributor_id,
            contributor_type=proposal.contributor_type,
            changelog=f"Validated: {proposal.rationale}",
        )
        
        proposal.status = ContributionStatus.MERGED
        logger.info("Validation applied to artifact %s", artifact.id)
        
        return proposal
    
    def list_pending(self) -> List[Dict[str, Any]]:
        """List all pending proposals."""
        return [
            p.to_dict()
            for p in self._proposals.values()
            if p.status == ContributionStatus.PENDING
        ]
    
    def get_proposal(self, proposal_id: UUID) -> Optional[ContributionProposal]:
        """Get a proposal by ID."""
        return self._proposals.get(proposal_id)
    
    def get_contribution_stats(
        self,
        contributor_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get contribution statistics."""
        stats = {
            "total_proposals": len(self._proposals),
            "pending": sum(1 for p in self._proposals.values() if p.status == ContributionStatus.PENDING),
            "approved": sum(1 for p in self._proposals.values() if p.status == ContributionStatus.MERGED),
            "rejected": sum(1 for p in self._proposals.values() if p.status == ContributionStatus.REJECTED),
        }
        
        if contributor_id:
            stats["contributor_proposals"] = sum(
                1 for p in self._proposals.values()
                if p.contributor_id == contributor_id
            )
        
        return stats
