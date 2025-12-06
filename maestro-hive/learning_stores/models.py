#!/usr/bin/env python3
"""
SQLAlchemy models for Learning Stores.

Implements three learning tables with pgvector indexes:
- template_executions: Template selection patterns
- quality_outcomes: Quality decision outcomes
- coordination_patterns: Team coordination patterns

EPIC: MD-2490
AC-1: Three learning tables created with proper indexes
"""

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, DateTime, JSON,
    ForeignKey, Enum as SQLEnum, Index, CheckConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from enum import Enum
import uuid
import hashlib

Base = declarative_base()


# =============================================================================
# Enums
# =============================================================================

class DecisionType(str, Enum):
    """Type of decision recorded in quality learning."""
    TEMPLATE_SELECTION = "template_selection"
    TEAM_COMPOSITION = "team_composition"
    EXECUTION_MODE = "execution_mode"
    RETRY_STRATEGY = "retry_strategy"
    QUALITY_THRESHOLD = "quality_threshold"


class Outcome(str, Enum):
    """Outcome of a decision."""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"


class ExecutionMode(str, Enum):
    """Execution mode for coordination patterns."""
    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"
    HYBRID = "hybrid"


# =============================================================================
# Learning Store Models
# =============================================================================

class TemplateExecution(Base):
    """
    Store 1: Template Learning.
    
    Records which templates work for different requirement types.
    Uses vector similarity search to find matching templates.
    
    Query: "Given requirement X, which template worked?"
    """
    __tablename__ = "template_executions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Requirement identification
    requirement_hash = Column(String(64), nullable=False, index=True)
    requirement_text = Column(Text, nullable=False)
    
    # Vector embedding for similarity search (stored as JSON array)
    # In production with pgvector: Column(Vector(1536))
    requirement_embedding = Column(JSON, nullable=True)
    
    # Template selection
    template_id = Column(String(100), nullable=False, index=True)
    template_version = Column(String(20), nullable=True)
    
    # Outcome metrics
    success = Column(Boolean, nullable=False)
    quality_score = Column(Float, nullable=False)  # 0-100
    execution_time_seconds = Column(Integer, nullable=True)
    
    # Context for learning
    requirement_type = Column(String(50), nullable=True)  # feature, bug, refactor
    complexity_level = Column(String(20), nullable=True)  # low, medium, high
    
    # Metadata
    execution_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index('idx_template_requirement_hash', 'requirement_hash'),
        Index('idx_template_template_id', 'template_id'),
        Index('idx_template_success', 'success'),
        Index('idx_template_quality', 'quality_score'),
        Index('idx_template_created', 'created_at'),
        CheckConstraint('quality_score >= 0 AND quality_score <= 100', name='check_quality_range'),
    )

    @staticmethod
    def hash_requirement(text: str) -> str:
        """Generate SHA-256 hash of requirement text."""
        return hashlib.sha256(text.encode()).hexdigest()

    def __repr__(self):
        return f"<TemplateExecution(template={self.template_id}, success={self.success}, quality={self.quality_score})>"


class QualityOutcome(Base):
    """
    Store 2: Quality Learning.
    
    Records quality outcomes of decisions to prevent repeating mistakes.
    Uses vector similarity to find decisions that led to quality issues.
    
    Query: "This decision led to quality issues before"
    """
    __tablename__ = "quality_outcomes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Decision identification
    decision_id = Column(String(100), nullable=False, index=True)
    decision_type = Column(SQLEnum(DecisionType), nullable=False)
    
    # Decision context
    decision_context = Column(Text, nullable=False)
    
    # Vector embedding for similarity search
    context_embedding = Column(JSON, nullable=True)
    
    # Outcome
    outcome = Column(SQLEnum(Outcome), nullable=False)
    quality_delta = Column(Float, nullable=False)  # -100 to +100
    
    # Confidence for filtering low-quality data
    confidence = Column(Float, nullable=False, default=0.5)  # 0-1
    
    # Additional context
    error_type = Column(String(100), nullable=True)
    remediation_applied = Column(Text, nullable=True)
    
    # Metadata
    execution_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index('idx_quality_decision_id', 'decision_id'),
        Index('idx_quality_decision_type', 'decision_type'),
        Index('idx_quality_outcome', 'outcome'),
        Index('idx_quality_confidence', 'confidence'),
        Index('idx_quality_created', 'created_at'),
        CheckConstraint('confidence >= 0 AND confidence <= 1', name='check_confidence_range'),
        CheckConstraint('quality_delta >= -100 AND quality_delta <= 100', name='check_delta_range'),
    )

    def __repr__(self):
        return f"<QualityOutcome(decision={self.decision_id}, outcome={self.outcome.value}, delta={self.quality_delta})>"


class CoordinationPattern(Base):
    """
    Store 3: Coordination Learning.
    
    Records successful team compositions and execution modes.
    Uses vector similarity to match requirement complexity.
    
    Query: "For this type of requirement, parallel or sequential?"
    """
    __tablename__ = "coordination_patterns"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Complexity embedding for similarity search
    complexity_description = Column(Text, nullable=False)
    complexity_embedding = Column(JSON, nullable=True)
    
    # Team composition (stored as JSON array of roles)
    team_composition = Column(JSON, nullable=False)  # ["backend", "frontend", "qa"]
    
    # Execution mode
    execution_mode = Column(SQLEnum(ExecutionMode), nullable=False)
    
    # Outcome metrics
    success_rate = Column(Float, nullable=False)  # 0-1
    avg_execution_time = Column(Integer, nullable=False)  # seconds
    sample_count = Column(Integer, default=1, nullable=False)
    
    # Pattern context
    requirement_type = Column(String(50), nullable=True)
    estimated_complexity = Column(String(20), nullable=True)  # low, medium, high
    
    # Metadata
    last_execution_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_coord_execution_mode', 'execution_mode'),
        Index('idx_coord_success_rate', 'success_rate'),
        Index('idx_coord_sample_count', 'sample_count'),
        Index('idx_coord_created', 'created_at'),
        CheckConstraint('success_rate >= 0 AND success_rate <= 1', name='check_success_rate_range'),
        CheckConstraint('sample_count >= 1', name='check_sample_count_positive'),
    )

    def update_with_execution(self, success: bool, execution_time: int) -> None:
        """Update pattern metrics with new execution result."""
        # Running average for success rate
        total_successes = self.success_rate * self.sample_count
        if success:
            total_successes += 1
        self.sample_count += 1
        self.success_rate = total_successes / self.sample_count
        
        # Running average for execution time
        total_time = self.avg_execution_time * (self.sample_count - 1)
        total_time += execution_time
        self.avg_execution_time = int(total_time / self.sample_count)

    def __repr__(self):
        return f"<CoordinationPattern(mode={self.execution_mode.value}, success_rate={self.success_rate:.2%}, samples={self.sample_count})>"


# =============================================================================
# Migration Script for pgvector (AC-1)
# =============================================================================

PGVECTOR_MIGRATION_SQL = """
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Add vector columns (replace JSON columns in production)
-- ALTER TABLE template_executions ADD COLUMN requirement_embedding_vec vector(1536);
-- ALTER TABLE quality_outcomes ADD COLUMN context_embedding_vec vector(1536);
-- ALTER TABLE coordination_patterns ADD COLUMN complexity_embedding_vec vector(1536);

-- Create vector indexes for similarity search
-- CREATE INDEX template_embedding_idx ON template_executions 
--   USING ivfflat (requirement_embedding_vec vector_cosine_ops) WITH (lists = 100);
-- CREATE INDEX quality_embedding_idx ON quality_outcomes 
--   USING ivfflat (context_embedding_vec vector_cosine_ops) WITH (lists = 100);
-- CREATE INDEX coord_embedding_idx ON coordination_patterns 
--   USING ivfflat (complexity_embedding_vec vector_cosine_ops) WITH (lists = 100);
"""
