"""
Knowledge Retriever - Retrieve relevant knowledge with scoring

Implements:
- AC-2543-1: Semantic search capabilities
- AC-2543-4: Relevance scoring for knowledge retrieval
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from .models import (
    KnowledgeArtifact,
    KnowledgeType,
    KnowledgeStatus,
    RelevanceScore,
)
from .store import KnowledgeStore
from .indexer import KnowledgeIndexer


logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """Result from knowledge retrieval."""
    artifact: KnowledgeArtifact
    score: RelevanceScore
    highlights: List[str] = field(default_factory=list)
    explanation: str = ""


@dataclass
class RetrievalContext:
    """Context for retrieval to improve relevance."""
    domain: Optional[str] = None
    subdomain: Optional[str] = None
    user_id: Optional[str] = None
    persona_id: Optional[UUID] = None
    recent_queries: List[str] = field(default_factory=list)
    preferred_types: List[KnowledgeType] = field(default_factory=list)
    exclude_ids: List[UUID] = field(default_factory=list)
    min_confidence: float = 0.0
    max_age_days: Optional[int] = None


class KnowledgeRetriever:
    """
    Retrieves relevant knowledge with intelligent scoring.
    
    Features:
    - Multi-factor relevance scoring
    - Context-aware retrieval
    - Recency and usage weighting
    - Configurable result ranking
    """
    
    # Default scoring weights
    DEFAULT_WEIGHTS = {
        "semantic_similarity": 0.35,
        "keyword_match": 0.20,
        "domain_relevance": 0.20,
        "recency_score": 0.10,
        "usage_score": 0.10,
        "confidence_score": 0.05,
    }
    
    def __init__(
        self,
        store: KnowledgeStore,
        indexer: KnowledgeIndexer,
        weights: Optional[Dict[str, float]] = None,
    ):
        """
        Initialize the retriever.
        
        Args:
            store: Knowledge store instance
            indexer: Knowledge indexer instance
            weights: Custom scoring weights
        """
        self.store = store
        self.indexer = indexer
        self.weights = {**self.DEFAULT_WEIGHTS, **(weights or {})}
        
        logger.info("KnowledgeRetriever initialized")
    
    def retrieve(
        self,
        query: str,
        context: Optional[RetrievalContext] = None,
        limit: int = 10,
    ) -> List[RetrievalResult]:
        """
        Retrieve knowledge relevant to the query.
        
        Args:
            query: Search query
            context: Retrieval context for personalization
            limit: Maximum results
        
        Returns:
            List of retrieval results sorted by relevance
        """
        context = context or RetrievalContext()
        
        # Get initial candidates from indexer
        candidates = self.indexer.search(
            query=query,
            domain=context.domain,
            knowledge_types=context.preferred_types,
            limit=limit * 3,  # Get more candidates for re-ranking
        )
        
        if not candidates:
            logger.debug("No candidates found for query: %s", query)
            return []
        
        # Enhance scores with additional factors
        results = []
        for artifact_id, base_score in candidates:
            artifact = self.store.get(artifact_id)
            if not artifact:
                continue
            
            # Skip excluded artifacts
            if artifact_id in context.exclude_ids:
                continue
            
            # Skip archived unless specifically included
            if artifact.status == KnowledgeStatus.ARCHIVED:
                continue
            
            # Apply confidence filter
            if artifact.metadata.confidence < context.min_confidence:
                continue
            
            # Apply age filter
            if context.max_age_days:
                age = datetime.utcnow() - artifact.updated_at
                if age.days > context.max_age_days:
                    continue
            
            # Calculate enhanced score
            enhanced_score = self._enhance_score(
                artifact=artifact,
                base_score=base_score,
                context=context,
            )
            
            # Generate explanation
            explanation = self._generate_explanation(
                artifact=artifact,
                score=enhanced_score,
                query=query,
            )
            
            results.append(RetrievalResult(
                artifact=artifact,
                score=enhanced_score,
                highlights=self._extract_highlights(artifact, query),
                explanation=explanation,
            ))
        
        # Sort by overall score
        results.sort(key=lambda r: r.score.overall_score(), reverse=True)
        
        # Record usage for retrieved artifacts
        for result in results[:limit]:
            result.artifact.record_usage()
        
        return results[:limit]
    
    def _enhance_score(
        self,
        artifact: KnowledgeArtifact,
        base_score: RelevanceScore,
        context: RetrievalContext,
    ) -> RelevanceScore:
        """Enhance base score with additional factors."""
        score = RelevanceScore(
            semantic_similarity=base_score.semantic_similarity,
            keyword_match=base_score.keyword_match,
            domain_relevance=base_score.domain_relevance,
            weights=self.weights,
        )
        
        # Calculate recency score
        age = datetime.utcnow() - artifact.updated_at
        days_old = age.days
        if days_old <= 7:
            score.recency_score = 1.0
        elif days_old <= 30:
            score.recency_score = 0.8
        elif days_old <= 90:
            score.recency_score = 0.6
        elif days_old <= 365:
            score.recency_score = 0.4
        else:
            score.recency_score = 0.2
        
        # Calculate usage score (normalized)
        usage = artifact.metadata.usage_count
        if usage >= 100:
            score.usage_score = 1.0
        elif usage >= 50:
            score.usage_score = 0.8
        elif usage >= 20:
            score.usage_score = 0.6
        elif usage >= 5:
            score.usage_score = 0.4
        else:
            score.usage_score = 0.2
        
        # Use artifact confidence as confidence score
        score.confidence_score = artifact.metadata.confidence
        
        # Domain match boost
        if context.domain and artifact.metadata.domain == context.domain:
            score.domain_relevance = max(score.domain_relevance, 0.9)
            if context.subdomain and artifact.metadata.subdomain == context.subdomain:
                score.domain_relevance = 1.0
        
        # Type preference boost
        if context.preferred_types and artifact.knowledge_type in context.preferred_types:
            score.custom_scores["type_preference"] = 0.2
        
        return score
    
    def _extract_highlights(
        self,
        artifact: KnowledgeArtifact,
        query: str,
    ) -> List[str]:
        """Extract relevant highlights from artifact content."""
        highlights = []
        content = artifact.content
        query_terms = query.lower().split()
        
        # Split into sentences
        sentences = content.replace('\n', ' ').split('.')
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # Check if sentence contains query terms
            sentence_lower = sentence.lower()
            matches = sum(1 for term in query_terms if term in sentence_lower)
            
            if matches > 0:
                # Truncate if too long
                if len(sentence) > 200:
                    sentence = sentence[:200] + "..."
                highlights.append(sentence)
            
            if len(highlights) >= 3:
                break
        
        return highlights
    
    def _generate_explanation(
        self,
        artifact: KnowledgeArtifact,
        score: RelevanceScore,
        query: str,
    ) -> str:
        """Generate human-readable explanation of relevance."""
        parts = []
        
        overall = score.overall_score()
        if overall > 0.8:
            parts.append("Highly relevant")
        elif overall > 0.6:
            parts.append("Relevant")
        elif overall > 0.4:
            parts.append("Somewhat relevant")
        else:
            parts.append("Possibly relevant")
        
        # Add factor explanations
        factors = []
        if score.semantic_similarity > 0.7:
            factors.append("strong content match")
        if score.keyword_match > 0.7:
            factors.append("keyword match")
        if score.domain_relevance > 0.8:
            factors.append("same domain")
        if score.recency_score > 0.8:
            factors.append("recently updated")
        if score.usage_score > 0.7:
            factors.append("frequently used")
        
        if factors:
            parts.append(f"({', '.join(factors)})")
        
        return " ".join(parts)
    
    def retrieve_by_type(
        self,
        knowledge_type: KnowledgeType,
        domain: Optional[str] = None,
        limit: int = 10,
    ) -> List[KnowledgeArtifact]:
        """Retrieve artifacts of a specific type."""
        artifacts = self.store.list_by_type(knowledge_type)
        
        if domain:
            artifacts = [a for a in artifacts if a.metadata.domain == domain]
        
        # Sort by usage and recency
        artifacts.sort(
            key=lambda a: (a.metadata.usage_count, a.updated_at),
            reverse=True,
        )
        
        return artifacts[:limit]
    
    def retrieve_related(
        self,
        artifact_id: UUID,
        limit: int = 5,
    ) -> List[RetrievalResult]:
        """Retrieve artifacts related to a given artifact."""
        source = self.store.get(artifact_id)
        if not source:
            return []
        
        # Build query from source
        query = f"{source.title} {' '.join(source.keywords[:5])}"
        
        context = RetrievalContext(
            domain=source.metadata.domain,
            exclude_ids=[artifact_id],
        )
        
        return self.retrieve(query, context, limit)
    
    def retrieve_for_task(
        self,
        task_description: str,
        domain: str,
        required_types: Optional[List[KnowledgeType]] = None,
        limit: int = 10,
    ) -> List[RetrievalResult]:
        """
        Retrieve knowledge relevant to a specific task.
        
        Args:
            task_description: Description of the task
            domain: Task domain
            required_types: Required knowledge types
            limit: Maximum results
        
        Returns:
            Relevant knowledge for the task
        """
        context = RetrievalContext(
            domain=domain,
            preferred_types=required_types or [],
            min_confidence=0.5,
        )
        
        return self.retrieve(task_description, context, limit)
    
    def get_popular(
        self,
        domain: Optional[str] = None,
        days: int = 30,
        limit: int = 10,
    ) -> List[KnowledgeArtifact]:
        """Get most popular artifacts."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        artifacts = []
        for summary in self.store.list_all(limit=1000):
            artifact = self.store.get(UUID(summary["id"]))
            if artifact and artifact.updated_at > cutoff:
                if not domain or artifact.metadata.domain == domain:
                    artifacts.append(artifact)
        
        # Sort by usage count
        artifacts.sort(key=lambda a: a.metadata.usage_count, reverse=True)
        
        return artifacts[:limit]
