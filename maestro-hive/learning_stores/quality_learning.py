#!/usr/bin/env python3
"""
Quality Learning Service.

Records quality outcomes of decisions to prevent repeating mistakes.
Uses RAG to identify decisions that led to quality issues in similar contexts.

EPIC: MD-2490
AC-3: RAG retrieval queries return relevant results
AC-4: Quality threshold filters low-confidence data
"""

import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import desc

from learning_stores.models import QualityOutcome, DecisionType, Outcome
from learning_stores.embedding_pipeline import EmbeddingPipeline

logger = logging.getLogger(__name__)


@dataclass
class QualityWarning:
    """Warning about a decision based on historical outcomes."""
    similar_decision_id: str
    decision_type: str
    outcome: str
    quality_delta: float
    similarity: float
    recommendation: str


@dataclass
class RecordResult:
    """Result from recording a quality outcome."""
    id: str
    stored: bool
    message: str


class QualityLearningService:
    """
    Service for quality learning store operations.
    
    Provides methods to:
    - Record quality outcomes of decisions
    - Check if a decision context has known issues
    - Query quality patterns for similar decisions
    """
    
    def __init__(
        self,
        session: Session,
        embedding_pipeline: Optional[EmbeddingPipeline] = None,
        confidence_threshold: float = 0.7,
        learning_mode: bool = False
    ):
        self.session = session
        self.embedding_pipeline = embedding_pipeline or EmbeddingPipeline()
        self.confidence_threshold = confidence_threshold
        self.learning_mode = learning_mode
    
    def record_outcome(
        self,
        decision_id: str,
        decision_type: DecisionType,
        decision_context: str,
        outcome: Outcome,
        quality_delta: float,
        confidence: float = 0.5,
        error_type: Optional[str] = None,
        remediation_applied: Optional[str] = None,
        execution_id: Optional[str] = None
    ) -> RecordResult:
        """
        Record a quality outcome for a decision.
        
        Args:
            decision_id: Unique identifier for the decision
            decision_type: Type of decision made
            decision_context: Full context of the decision
            outcome: Result (success, failure, partial)
            quality_delta: Change in quality score (-100 to +100)
            confidence: Confidence in this outcome (0-1)
            error_type: Type of error if failure
            remediation_applied: What remediation was done
            execution_id: Reference to execution record
            
        Returns:
            RecordResult with storage details
        """
        # Only store in learning mode
        if not self.learning_mode:
            return RecordResult(
                id="",
                stored=False,
                message="Learning mode disabled"
            )
        
        # Filter low-confidence data (AC-4)
        if confidence < self.confidence_threshold:
            return RecordResult(
                id="",
                stored=False,
                message=f"Confidence {confidence} below threshold {self.confidence_threshold}"
            )
        
        try:
            # Generate embedding for context
            embedding = self.embedding_pipeline.generate(decision_context)
            
            # Create record
            record = QualityOutcome(
                decision_id=decision_id,
                decision_type=decision_type,
                decision_context=decision_context,
                context_embedding=embedding,
                outcome=outcome,
                quality_delta=quality_delta,
                confidence=confidence,
                error_type=error_type,
                remediation_applied=remediation_applied,
                execution_id=execution_id
            )
            
            self.session.add(record)
            self.session.commit()
            
            logger.info(f"Recorded quality outcome: {decision_id} ({outcome.value}, delta={quality_delta})")
            
            return RecordResult(
                id=record.id,
                stored=True,
                message="Successfully recorded"
            )
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to record quality outcome: {e}")
            return RecordResult(
                id="",
                stored=False,
                message=f"Recording failed: {str(e)}"
            )
    
    def check_for_warnings(
        self,
        decision_context: str,
        decision_type: Optional[DecisionType] = None,
        min_confidence: float = 0.7,
        min_similarity: float = 0.75
    ) -> List[QualityWarning]:
        """
        Check if a decision context has known quality issues.
        
        Searches for similar decisions that led to negative outcomes
        to warn before making the same mistake.
        
        Args:
            decision_context: Context of the decision being considered
            decision_type: Optional filter by decision type
            min_confidence: Minimum confidence threshold
            min_similarity: Minimum similarity to consider
            
        Returns:
            List of QualityWarning objects for similar bad decisions
        """
        try:
            # Generate embedding for query
            query_embedding = self.embedding_pipeline.generate(decision_context)
            
            # Build query for negative outcomes
            query = self.session.query(QualityOutcome).filter(
                QualityOutcome.confidence >= min_confidence,
                QualityOutcome.quality_delta < 0  # Only negative outcomes
            )
            
            if decision_type:
                query = query.filter(QualityOutcome.decision_type == decision_type)
            
            results = query.all()
            
            if not results:
                return []
            
            # Calculate similarity and filter
            warnings = []
            for record in results:
                if record.context_embedding:
                    similarity = self.embedding_pipeline.compute_similarity(
                        query_embedding,
                        record.context_embedding
                    )
                    if similarity >= min_similarity:
                        # Generate recommendation based on outcome
                        recommendation = self._generate_recommendation(record)
                        
                        warnings.append(QualityWarning(
                            similar_decision_id=record.decision_id,
                            decision_type=record.decision_type.value,
                            outcome=record.outcome.value,
                            quality_delta=record.quality_delta,
                            similarity=similarity,
                            recommendation=recommendation
                        ))
            
            # Sort by quality impact (most negative first)
            warnings.sort(key=lambda w: (w.quality_delta, -w.similarity))
            
            return warnings
            
        except Exception as e:
            logger.error(f"Warning check failed: {e}")
            return []
    
    def _generate_recommendation(self, record: QualityOutcome) -> str:
        """Generate recommendation based on historical outcome."""
        if record.remediation_applied:
            return f"Consider: {record.remediation_applied}"
        
        if record.error_type:
            return f"Watch for: {record.error_type}"
        
        if record.outcome == Outcome.FAILURE:
            return "Similar decision led to failure - review carefully"
        
        return "Similar decision had quality issues"
    
    def get_decision_history(
        self,
        decision_type: DecisionType,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Get historical statistics for a decision type."""
        results = self.session.query(QualityOutcome).filter(
            QualityOutcome.decision_type == decision_type,
            QualityOutcome.confidence >= self.confidence_threshold
        ).order_by(desc(QualityOutcome.created_at)).limit(limit).all()
        
        if not results:
            return {
                "decision_type": decision_type.value,
                "total_records": 0
            }
        
        success_count = sum(1 for r in results if r.outcome == Outcome.SUCCESS)
        failure_count = sum(1 for r in results if r.outcome == Outcome.FAILURE)
        avg_delta = sum(r.quality_delta for r in results) / len(results)
        
        return {
            "decision_type": decision_type.value,
            "total_records": len(results),
            "success_count": success_count,
            "failure_count": failure_count,
            "partial_count": len(results) - success_count - failure_count,
            "success_rate": success_count / len(results),
            "avg_quality_delta": avg_delta,
            "avg_confidence": sum(r.confidence for r in results) / len(results)
        }
    
    def get_common_errors(
        self,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get most common error types."""
        from sqlalchemy import func
        
        results = self.session.query(
            QualityOutcome.error_type,
            func.count(QualityOutcome.id).label('count'),
            func.avg(QualityOutcome.quality_delta).label('avg_delta')
        ).filter(
            QualityOutcome.error_type.isnot(None),
            QualityOutcome.confidence >= self.confidence_threshold
        ).group_by(
            QualityOutcome.error_type
        ).order_by(
            desc('count')
        ).limit(limit).all()
        
        return [
            {
                "error_type": r.error_type,
                "occurrence_count": r.count,
                "avg_quality_delta": float(r.avg_delta) if r.avg_delta else 0
            }
            for r in results
        ]
    
    def cleanup_low_confidence(self, min_confidence: float = 0.5) -> int:
        """Remove low-confidence records."""
        deleted = self.session.query(QualityOutcome).filter(
            QualityOutcome.confidence < min_confidence
        ).delete()
        
        self.session.commit()
        logger.info(f"Cleaned up {deleted} low-confidence quality outcome records")
        return deleted
