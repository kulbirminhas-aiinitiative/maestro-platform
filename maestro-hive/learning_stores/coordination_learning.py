#!/usr/bin/env python3
"""
Coordination Learning Service.

Records successful team compositions and execution modes based on requirement complexity.
Uses RAG to recommend optimal coordination patterns for new requirements.

EPIC: MD-2490
AC-3: RAG retrieval queries return relevant results
AC-5: Learning stores populated during LEARNING mode
"""

import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import desc

from learning_stores.models import CoordinationPattern, ExecutionMode
from learning_stores.embedding_pipeline import EmbeddingPipeline

logger = logging.getLogger(__name__)


@dataclass
class CoordinationRecommendation:
    """Recommended coordination pattern."""
    team_composition: List[str]
    execution_mode: str
    confidence: float
    historical_success_rate: float
    avg_execution_time: int
    sample_count: int
    complexity_match: float


@dataclass
class StoreResult:
    """Result from storing a coordination pattern."""
    id: str
    stored: bool
    updated_existing: bool
    message: str


class CoordinationLearningService:
    """
    Service for coordination learning store operations.
    
    Provides methods to:
    - Store coordination patterns from executions
    - Recommend team composition and execution mode
    - Query patterns for similar complexity requirements
    """
    
    def __init__(
        self,
        session: Session,
        embedding_pipeline: Optional[EmbeddingPipeline] = None,
        min_success_rate: float = 0.6,
        learning_mode: bool = False
    ):
        self.session = session
        self.embedding_pipeline = embedding_pipeline or EmbeddingPipeline()
        self.min_success_rate = min_success_rate
        self.learning_mode = learning_mode
    
    def store_pattern(
        self,
        complexity_description: str,
        team_composition: List[str],
        execution_mode: ExecutionMode,
        success: bool,
        execution_time: int,
        requirement_type: Optional[str] = None,
        estimated_complexity: Optional[str] = None,
        execution_id: Optional[str] = None
    ) -> StoreResult:
        """
        Store or update a coordination pattern.
        
        If a similar pattern exists, updates its metrics.
        Otherwise creates a new pattern record.
        
        Args:
            complexity_description: Description of requirement complexity
            team_composition: List of agent roles used
            execution_mode: Mode (parallel, sequential, hybrid)
            success: Whether execution succeeded
            execution_time: Execution duration in seconds
            requirement_type: Type (feature, bug, refactor)
            estimated_complexity: Complexity level (low, medium, high)
            execution_id: Reference to execution record
            
        Returns:
            StoreResult with storage details
        """
        # Only store in learning mode
        if not self.learning_mode:
            return StoreResult(
                id="",
                stored=False,
                updated_existing=False,
                message="Learning mode disabled"
            )
        
        try:
            # Generate embedding for complexity
            embedding = self.embedding_pipeline.generate(complexity_description)
            
            # Look for existing similar pattern
            existing_pattern = self._find_similar_pattern(
                embedding,
                team_composition,
                execution_mode
            )
            
            if existing_pattern:
                # Update existing pattern
                existing_pattern.update_with_execution(success, execution_time)
                existing_pattern.last_execution_id = execution_id
                self.session.commit()
                
                logger.info(f"Updated coordination pattern: {existing_pattern.id}")
                
                return StoreResult(
                    id=existing_pattern.id,
                    stored=True,
                    updated_existing=True,
                    message="Updated existing pattern"
                )
            else:
                # Create new pattern
                record = CoordinationPattern(
                    complexity_description=complexity_description,
                    complexity_embedding=embedding,
                    team_composition=team_composition,
                    execution_mode=execution_mode,
                    success_rate=1.0 if success else 0.0,
                    avg_execution_time=execution_time,
                    sample_count=1,
                    requirement_type=requirement_type,
                    estimated_complexity=estimated_complexity,
                    last_execution_id=execution_id
                )
                
                self.session.add(record)
                self.session.commit()
                
                logger.info(f"Created new coordination pattern: {record.id}")
                
                return StoreResult(
                    id=record.id,
                    stored=True,
                    updated_existing=False,
                    message="Created new pattern"
                )
                
        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to store coordination pattern: {e}")
            return StoreResult(
                id="",
                stored=False,
                updated_existing=False,
                message=f"Storage failed: {str(e)}"
            )
    
    def _find_similar_pattern(
        self,
        embedding: List[float],
        team_composition: List[str],
        execution_mode: ExecutionMode,
        similarity_threshold: float = 0.9
    ) -> Optional[CoordinationPattern]:
        """Find existing pattern with same team/mode and similar complexity."""
        # Get patterns with same team composition and mode
        results = self.session.query(CoordinationPattern).filter(
            CoordinationPattern.execution_mode == execution_mode
        ).all()
        
        for pattern in results:
            # Check team composition match
            if set(pattern.team_composition) != set(team_composition):
                continue
            
            # Check complexity similarity
            if pattern.complexity_embedding:
                similarity = self.embedding_pipeline.compute_similarity(
                    embedding,
                    pattern.complexity_embedding
                )
                if similarity >= similarity_threshold:
                    return pattern
        
        return None
    
    def recommend_coordination(
        self,
        complexity_description: str,
        available_agents: List[str],
        limit: int = 3,
        min_samples: int = 3
    ) -> List[CoordinationRecommendation]:
        """
        Recommend team composition and execution mode.
        
        Uses vector similarity to find patterns that worked
        for similar complexity requirements.
        
        Args:
            complexity_description: Description of requirement complexity
            available_agents: List of available agent roles
            limit: Maximum recommendations to return
            min_samples: Minimum sample count for confidence
            
        Returns:
            List of CoordinationRecommendation sorted by relevance
        """
        try:
            # Generate embedding for query
            query_embedding = self.embedding_pipeline.generate(complexity_description)
            
            # Get all patterns with sufficient samples
            results = self.session.query(CoordinationPattern).filter(
                CoordinationPattern.sample_count >= min_samples,
                CoordinationPattern.success_rate >= self.min_success_rate
            ).all()
            
            if not results:
                # Return default recommendation
                return [self._default_recommendation(available_agents)]
            
            # Calculate similarity and filter by available agents
            recommendations = []
            for pattern in results:
                # Check if team can be composed from available agents
                if not all(agent in available_agents for agent in pattern.team_composition):
                    continue
                
                # Calculate complexity match
                if pattern.complexity_embedding:
                    similarity = self.embedding_pipeline.compute_similarity(
                        query_embedding,
                        pattern.complexity_embedding
                    )
                else:
                    similarity = 0.5  # Default similarity for patterns without embedding
                
                # Calculate confidence based on samples and success rate
                confidence = min(1.0, (pattern.sample_count / 10)) * pattern.success_rate
                
                recommendations.append(CoordinationRecommendation(
                    team_composition=pattern.team_composition,
                    execution_mode=pattern.execution_mode.value,
                    confidence=confidence,
                    historical_success_rate=pattern.success_rate,
                    avg_execution_time=pattern.avg_execution_time,
                    sample_count=pattern.sample_count,
                    complexity_match=similarity
                ))
            
            if not recommendations:
                return [self._default_recommendation(available_agents)]
            
            # Sort by combined score: similarity * confidence
            recommendations.sort(
                key=lambda r: r.complexity_match * r.confidence,
                reverse=True
            )
            
            return recommendations[:limit]
            
        except Exception as e:
            logger.error(f"Coordination recommendation failed: {e}")
            return [self._default_recommendation(available_agents)]
    
    def _default_recommendation(self, available_agents: List[str]) -> CoordinationRecommendation:
        """Generate default recommendation when no patterns match."""
        return CoordinationRecommendation(
            team_composition=available_agents[:3] if len(available_agents) >= 3 else available_agents,
            execution_mode="sequential",
            confidence=0.5,
            historical_success_rate=0.0,
            avg_execution_time=0,
            sample_count=0,
            complexity_match=0.0
        )
    
    def get_mode_statistics(self) -> Dict[str, Any]:
        """Get statistics by execution mode."""
        from sqlalchemy import func
        
        results = self.session.query(
            CoordinationPattern.execution_mode,
            func.count(CoordinationPattern.id).label('pattern_count'),
            func.sum(CoordinationPattern.sample_count).label('total_executions'),
            func.avg(CoordinationPattern.success_rate).label('avg_success_rate'),
            func.avg(CoordinationPattern.avg_execution_time).label('avg_time')
        ).group_by(
            CoordinationPattern.execution_mode
        ).all()
        
        return {
            r.execution_mode.value: {
                "pattern_count": r.pattern_count,
                "total_executions": r.total_executions or 0,
                "avg_success_rate": float(r.avg_success_rate) if r.avg_success_rate else 0,
                "avg_execution_time": int(r.avg_time) if r.avg_time else 0
            }
            for r in results
        }
    
    def get_top_patterns(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top performing coordination patterns."""
        results = self.session.query(CoordinationPattern).filter(
            CoordinationPattern.sample_count >= 5
        ).order_by(
            desc(CoordinationPattern.success_rate),
            desc(CoordinationPattern.sample_count)
        ).limit(limit).all()
        
        return [
            {
                "id": p.id,
                "team_composition": p.team_composition,
                "execution_mode": p.execution_mode.value,
                "success_rate": p.success_rate,
                "avg_execution_time": p.avg_execution_time,
                "sample_count": p.sample_count,
                "requirement_type": p.requirement_type
            }
            for p in results
        ]
    
    def cleanup_low_sample_patterns(self, min_samples: int = 3) -> int:
        """Remove patterns with too few samples."""
        deleted = self.session.query(CoordinationPattern).filter(
            CoordinationPattern.sample_count < min_samples
        ).delete()
        
        self.session.commit()
        logger.info(f"Cleaned up {deleted} low-sample coordination patterns")
        return deleted
