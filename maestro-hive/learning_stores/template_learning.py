#!/usr/bin/env python3
"""
Template Learning Service.

Stores and retrieves template execution patterns based on requirement similarity.
Uses RAG (Retrieval Augmented Generation) to find templates that worked for
similar requirements in the past.

EPIC: MD-2490
AC-3: RAG retrieval queries return relevant results
AC-5: Learning stores populated during LEARNING mode
"""

import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

from learning_stores.models import TemplateExecution
from learning_stores.embedding_pipeline import EmbeddingPipeline, EmbeddingConfig

logger = logging.getLogger(__name__)


@dataclass
class TemplatePattern:
    """Result from template pattern query."""
    template_id: str
    template_version: Optional[str]
    similarity: float
    quality_score: float
    success_rate: float
    sample_count: int
    requirement_type: Optional[str]


@dataclass
class StoreResult:
    """Result from storing a template execution."""
    id: str
    requirement_hash: str
    stored: bool
    message: str


class TemplateLearningService:
    """
    Service for template learning store operations.
    
    Provides methods to:
    - Store template execution results
    - Query similar templates for new requirements
    - Calculate template success rates
    """
    
    def __init__(
        self,
        session: Session,
        embedding_pipeline: Optional[EmbeddingPipeline] = None,
        quality_threshold: float = 70.0,
        learning_mode: bool = False
    ):
        self.session = session
        self.embedding_pipeline = embedding_pipeline or EmbeddingPipeline()
        self.quality_threshold = quality_threshold
        self.learning_mode = learning_mode
    
    def store_execution(
        self,
        requirement_text: str,
        template_id: str,
        success: bool,
        quality_score: float,
        template_version: Optional[str] = None,
        execution_time_seconds: Optional[int] = None,
        requirement_type: Optional[str] = None,
        complexity_level: Optional[str] = None,
        execution_id: Optional[str] = None
    ) -> StoreResult:
        """
        Store a template execution result.
        
        Args:
            requirement_text: The requirement text that was processed
            template_id: ID of the template used
            success: Whether execution succeeded
            quality_score: Quality score achieved (0-100)
            template_version: Version of template used
            execution_time_seconds: Execution duration
            requirement_type: Type (feature, bug, refactor)
            complexity_level: Complexity (low, medium, high)
            execution_id: Reference to execution record
            
        Returns:
            StoreResult with storage details
        """
        # Only store in learning mode
        if not self.learning_mode:
            return StoreResult(
                id="",
                requirement_hash="",
                stored=False,
                message="Learning mode disabled"
            )
        
        # Filter low-quality data (AC-4)
        if quality_score < self.quality_threshold and not success:
            return StoreResult(
                id="",
                requirement_hash=TemplateExecution.hash_requirement(requirement_text),
                stored=False,
                message=f"Quality score {quality_score} below threshold {self.quality_threshold}"
            )
        
        try:
            # Generate embedding for requirement
            embedding = self.embedding_pipeline.generate(requirement_text)
            
            # Create record
            record = TemplateExecution(
                requirement_hash=TemplateExecution.hash_requirement(requirement_text),
                requirement_text=requirement_text,
                requirement_embedding=embedding,
                template_id=template_id,
                template_version=template_version,
                success=success,
                quality_score=quality_score,
                execution_time_seconds=execution_time_seconds,
                requirement_type=requirement_type,
                complexity_level=complexity_level,
                execution_id=execution_id
            )
            
            self.session.add(record)
            self.session.commit()
            
            logger.info(f"Stored template execution: {template_id} for requirement hash {record.requirement_hash}")
            
            return StoreResult(
                id=record.id,
                requirement_hash=record.requirement_hash,
                stored=True,
                message="Successfully stored"
            )
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to store template execution: {e}")
            return StoreResult(
                id="",
                requirement_hash="",
                stored=False,
                message=f"Storage failed: {str(e)}"
            )
    
    def query_similar_templates(
        self,
        requirement_text: str,
        limit: int = 5,
        min_quality: float = 70.0,
        min_similarity: float = 0.7
    ) -> List[TemplatePattern]:
        """
        Query templates that worked for similar requirements.
        
        Uses vector similarity search to find matching templates.
        
        Args:
            requirement_text: The new requirement to find templates for
            limit: Maximum number of results
            min_quality: Minimum quality score filter
            min_similarity: Minimum similarity threshold
            
        Returns:
            List of TemplatePattern results sorted by relevance
        """
        try:
            # Generate embedding for query
            query_embedding = self.embedding_pipeline.generate(requirement_text)
            
            # Get all template executions above quality threshold
            # In production with pgvector, this would use vector similarity SQL
            results = self.session.query(TemplateExecution).filter(
                TemplateExecution.quality_score >= min_quality
            ).all()
            
            if not results:
                return []
            
            # Calculate similarity scores
            scored_results = []
            for record in results:
                if record.requirement_embedding:
                    similarity = self.embedding_pipeline.compute_similarity(
                        query_embedding,
                        record.requirement_embedding
                    )
                    if similarity >= min_similarity:
                        scored_results.append((record, similarity))
            
            # Sort by similarity
            scored_results.sort(key=lambda x: x[1], reverse=True)
            
            # Aggregate by template_id
            template_stats: Dict[str, Dict[str, Any]] = {}
            for record, similarity in scored_results:
                tid = record.template_id
                if tid not in template_stats:
                    template_stats[tid] = {
                        'template_version': record.template_version,
                        'max_similarity': similarity,
                        'total_quality': 0,
                        'success_count': 0,
                        'total_count': 0,
                        'requirement_type': record.requirement_type
                    }
                
                stats = template_stats[tid]
                stats['total_quality'] += record.quality_score
                stats['total_count'] += 1
                if record.success:
                    stats['success_count'] += 1
                if similarity > stats['max_similarity']:
                    stats['max_similarity'] = similarity
            
            # Build results
            patterns = []
            for tid, stats in template_stats.items():
                patterns.append(TemplatePattern(
                    template_id=tid,
                    template_version=stats['template_version'],
                    similarity=stats['max_similarity'],
                    quality_score=stats['total_quality'] / stats['total_count'],
                    success_rate=stats['success_count'] / stats['total_count'],
                    sample_count=stats['total_count'],
                    requirement_type=stats['requirement_type']
                ))
            
            # Sort by similarity * success_rate (combined relevance)
            patterns.sort(key=lambda p: p.similarity * p.success_rate, reverse=True)
            
            return patterns[:limit]
            
        except Exception as e:
            logger.error(f"Template query failed: {e}")
            return []
    
    def get_template_stats(self, template_id: str) -> Dict[str, Any]:
        """Get statistics for a specific template."""
        results = self.session.query(TemplateExecution).filter(
            TemplateExecution.template_id == template_id
        ).all()
        
        if not results:
            return {"template_id": template_id, "found": False}
        
        success_count = sum(1 for r in results if r.success)
        total_quality = sum(r.quality_score for r in results)
        
        return {
            "template_id": template_id,
            "found": True,
            "total_executions": len(results),
            "success_count": success_count,
            "success_rate": success_count / len(results),
            "avg_quality_score": total_quality / len(results),
            "latest_execution": max(r.created_at for r in results).isoformat()
        }
    
    def cleanup_old_data(self, days_to_keep: int = 90) -> int:
        """Remove old learning data."""
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(days=days_to_keep)
        
        deleted = self.session.query(TemplateExecution).filter(
            TemplateExecution.created_at < cutoff
        ).delete()
        
        self.session.commit()
        logger.info(f"Cleaned up {deleted} old template execution records")
        return deleted
