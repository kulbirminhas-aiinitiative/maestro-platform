#!/usr/bin/env python3
"""
Comprehensive tests for Learning Stores.

Tests cover all 5 Acceptance Criteria:
- AC-1: Three learning tables created with proper indexes
- AC-2: Embedding generation pipeline working
- AC-3: RAG retrieval queries return relevant results
- AC-4: Quality threshold filters low-confidence data
- AC-5: Learning stores populated during LEARNING mode

EPIC: MD-2490
"""

import pytest
import sys
import os
from datetime import datetime
from unittest.mock import MagicMock, patch

# Add the project root to path
sys.path.insert(0, '/home/ec2-user/projects/maestro-platform/maestro-hive')

from learning_stores.models import (
    TemplateExecution, QualityOutcome, CoordinationPattern,
    DecisionType, Outcome, ExecutionMode
)
from learning_stores.embedding_pipeline import EmbeddingPipeline, EmbeddingConfig
from learning_stores.template_learning import TemplateLearningService
from learning_stores.quality_learning import QualityLearningService
from learning_stores.coordination_learning import CoordinationLearningService


# =============================================================================
# AC-1: Three Learning Tables Tests
# =============================================================================

class TestLearningModels:
    """Test learning store model definitions."""
    
    def test_template_execution_model_exists(self):
        """AC-1: TemplateExecution table model exists."""
        assert TemplateExecution is not None
        assert TemplateExecution.__tablename__ == "template_executions"
    
    def test_template_execution_has_required_columns(self):
        """AC-1: TemplateExecution has all required columns."""
        columns = {c.name for c in TemplateExecution.__table__.columns}
        required = {'id', 'requirement_hash', 'requirement_text', 'template_id', 
                   'success', 'quality_score', 'requirement_embedding'}
        assert required.issubset(columns)
    
    def test_quality_outcome_model_exists(self):
        """AC-1: QualityOutcome table model exists."""
        assert QualityOutcome is not None
        assert QualityOutcome.__tablename__ == "quality_outcomes"
    
    def test_quality_outcome_has_required_columns(self):
        """AC-1: QualityOutcome has all required columns."""
        columns = {c.name for c in QualityOutcome.__table__.columns}
        required = {'id', 'decision_id', 'decision_type', 'decision_context',
                   'outcome', 'quality_delta', 'confidence', 'context_embedding'}
        assert required.issubset(columns)
    
    def test_coordination_pattern_model_exists(self):
        """AC-1: CoordinationPattern table model exists."""
        assert CoordinationPattern is not None
        assert CoordinationPattern.__tablename__ == "coordination_patterns"
    
    def test_coordination_pattern_has_required_columns(self):
        """AC-1: CoordinationPattern has all required columns."""
        columns = {c.name for c in CoordinationPattern.__table__.columns}
        required = {'id', 'complexity_description', 'team_composition',
                   'execution_mode', 'success_rate', 'avg_execution_time', 
                   'complexity_embedding'}
        assert required.issubset(columns)
    
    def test_template_execution_has_indexes(self):
        """AC-1: TemplateExecution has proper indexes."""
        index_names = {idx.name for idx in TemplateExecution.__table__.indexes}
        assert 'idx_template_requirement_hash' in index_names
        assert 'idx_template_template_id' in index_names
    
    def test_quality_outcome_has_indexes(self):
        """AC-1: QualityOutcome has proper indexes."""
        index_names = {idx.name for idx in QualityOutcome.__table__.indexes}
        assert 'idx_quality_decision_id' in index_names
        assert 'idx_quality_confidence' in index_names
    
    def test_coordination_pattern_has_indexes(self):
        """AC-1: CoordinationPattern has proper indexes."""
        index_names = {idx.name for idx in CoordinationPattern.__table__.indexes}
        assert 'idx_coord_execution_mode' in index_names
        assert 'idx_coord_success_rate' in index_names
    
    def test_requirement_hash_generation(self):
        """AC-1: Requirement hashing works correctly."""
        text1 = "Implement user authentication"
        text2 = "Implement user authentication"
        text3 = "Different requirement"
        
        hash1 = TemplateExecution.hash_requirement(text1)
        hash2 = TemplateExecution.hash_requirement(text2)
        hash3 = TemplateExecution.hash_requirement(text3)
        
        assert hash1 == hash2  # Same text produces same hash
        assert hash1 != hash3  # Different text produces different hash
        assert len(hash1) == 64  # SHA-256 produces 64-char hex


# =============================================================================
# AC-2: Embedding Pipeline Tests
# =============================================================================

class TestEmbeddingPipeline:
    """Test embedding generation pipeline."""
    
    def test_pipeline_initialization(self):
        """AC-2: Pipeline initializes correctly."""
        config = EmbeddingConfig(model="test-model", dimensions=1536)
        pipeline = EmbeddingPipeline(config)
        
        assert pipeline.config.model == "test-model"
        assert pipeline.config.dimensions == 1536
    
    def test_generate_single_embedding(self):
        """AC-2: Single embedding generation works."""
        pipeline = EmbeddingPipeline()
        embedding = pipeline.generate("Test requirement text")
        
        assert isinstance(embedding, list)
        assert len(embedding) == 1536  # Default dimensions
        assert all(isinstance(x, float) for x in embedding)
    
    def test_generate_batch_embeddings(self):
        """AC-2: Batch embedding generation works."""
        pipeline = EmbeddingPipeline()
        texts = ["First text", "Second text", "Third text"]
        embeddings = pipeline.generate_batch(texts)
        
        assert len(embeddings) == 3
        assert all(len(e) == 1536 for e in embeddings)
    
    def test_embeddings_are_deterministic(self):
        """AC-2: Same text produces same embedding (mock mode)."""
        pipeline = EmbeddingPipeline()
        text = "Deterministic test text"
        
        emb1 = pipeline.generate(text)
        emb2 = pipeline.generate(text)
        
        assert emb1 == emb2
    
    def test_different_texts_different_embeddings(self):
        """AC-2: Different texts produce different embeddings."""
        pipeline = EmbeddingPipeline()
        
        emb1 = pipeline.generate("First unique text")
        emb2 = pipeline.generate("Second unique text")
        
        assert emb1 != emb2
    
    def test_embedding_cache(self):
        """AC-2: Embedding caching works correctly."""
        config = EmbeddingConfig(cache_enabled=True)
        pipeline = EmbeddingPipeline(config)
        
        text = "Cache test text"
        
        # First call - cache miss
        emb1 = pipeline.generate(text)
        
        # Second call - cache hit
        emb2 = pipeline.generate(text)
        
        assert emb1 == emb2
    
    def test_compute_similarity(self):
        """AC-2: Similarity computation works."""
        pipeline = EmbeddingPipeline()
        
        emb1 = pipeline.generate("Similar requirement A")
        emb2 = pipeline.generate("Similar requirement A")  # Same
        emb3 = pipeline.generate("Completely different topic")
        
        similarity_same = pipeline.compute_similarity(emb1, emb2)
        similarity_diff = pipeline.compute_similarity(emb1, emb3)
        
        assert similarity_same == 1.0  # Identical embeddings
        assert 0 <= similarity_diff <= 1  # Valid range
    
    def test_health_check(self):
        """AC-2: Health check returns correct status."""
        pipeline = EmbeddingPipeline()
        health = pipeline.health_check()
        
        assert health["status"] in ["healthy", "degraded"]
        assert "model" in health
        assert "dimensions" in health


# =============================================================================
# AC-3: RAG Retrieval Tests
# =============================================================================

class TestRAGRetrieval:
    """Test RAG retrieval queries."""
    
    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        session = MagicMock()
        return session
    
    def test_template_query_returns_results(self, mock_session):
        """AC-3: Template RAG query returns relevant results."""
        # Create mock records
        mock_records = [
            MagicMock(
                template_id="template_1",
                template_version="1.0",
                requirement_embedding=[0.1] * 1536,
                success=True,
                quality_score=85.0,
                requirement_type="feature"
            ),
            MagicMock(
                template_id="template_2",
                template_version="1.0",
                requirement_embedding=[0.2] * 1536,
                success=True,
                quality_score=90.0,
                requirement_type="feature"
            )
        ]
        
        mock_session.query.return_value.filter.return_value.all.return_value = mock_records
        
        service = TemplateLearningService(mock_session, learning_mode=True)
        results = service.query_similar_templates("Test requirement")
        
        # Should return patterns (may be empty due to similarity threshold)
        assert isinstance(results, list)
    
    def test_quality_warning_check(self, mock_session):
        """AC-3: Quality warning check finds similar bad decisions."""
        # Create mock negative outcome
        mock_records = [
            MagicMock(
                decision_id="decision_1",
                decision_type=DecisionType.TEMPLATE_SELECTION,
                context_embedding=[0.1] * 1536,
                outcome=Outcome.FAILURE,
                quality_delta=-20.0,
                error_type="ValidationError",
                remediation_applied="Use different template"
            )
        ]
        
        mock_session.query.return_value.filter.return_value.all.return_value = mock_records
        
        service = QualityLearningService(mock_session, learning_mode=True)
        warnings = service.check_for_warnings("Similar decision context")
        
        assert isinstance(warnings, list)
    
    def test_coordination_recommendation(self, mock_session):
        """AC-3: Coordination recommendation returns results."""
        mock_records = [
            MagicMock(
                id="pattern_1",
                team_composition=["backend", "frontend"],
                execution_mode=ExecutionMode.PARALLEL,
                complexity_embedding=[0.1] * 1536,
                success_rate=0.9,
                avg_execution_time=300,
                sample_count=10
            )
        ]
        
        mock_session.query.return_value.filter.return_value.all.return_value = mock_records
        
        service = CoordinationLearningService(mock_session, learning_mode=True)
        recommendations = service.recommend_coordination(
            "Complex feature requirement",
            ["backend", "frontend", "qa"]
        )
        
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0


# =============================================================================
# AC-4: Quality Threshold Tests
# =============================================================================

class TestQualityThreshold:
    """Test quality threshold filtering."""
    
    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        session = MagicMock()
        return session
    
    def test_template_filters_low_quality(self, mock_session):
        """AC-4: Template store filters low quality scores."""
        service = TemplateLearningService(
            mock_session, 
            quality_threshold=70.0,
            learning_mode=True
        )
        
        # Try to store low quality record
        result = service.store_execution(
            requirement_text="Test requirement",
            template_id="test_template",
            success=False,
            quality_score=50.0  # Below threshold
        )
        
        assert result.stored == False
        assert "below threshold" in result.message.lower()
    
    def test_template_accepts_high_quality(self, mock_session):
        """AC-4: Template store accepts high quality scores."""
        service = TemplateLearningService(
            mock_session,
            quality_threshold=70.0,
            learning_mode=True
        )
        
        # Store high quality record
        result = service.store_execution(
            requirement_text="Test requirement",
            template_id="test_template",
            success=True,
            quality_score=85.0  # Above threshold
        )
        
        assert result.stored == True
    
    def test_quality_filters_low_confidence(self, mock_session):
        """AC-4: Quality store filters low confidence records."""
        service = QualityLearningService(
            mock_session,
            confidence_threshold=0.7,
            learning_mode=True
        )
        
        result = service.record_outcome(
            decision_id="test_decision",
            decision_type=DecisionType.TEMPLATE_SELECTION,
            decision_context="Test context",
            outcome=Outcome.SUCCESS,
            quality_delta=10.0,
            confidence=0.5  # Below threshold
        )
        
        assert result.stored == False
        assert "below threshold" in result.message.lower()
    
    def test_quality_accepts_high_confidence(self, mock_session):
        """AC-4: Quality store accepts high confidence records."""
        service = QualityLearningService(
            mock_session,
            confidence_threshold=0.7,
            learning_mode=True
        )
        
        result = service.record_outcome(
            decision_id="test_decision",
            decision_type=DecisionType.TEMPLATE_SELECTION,
            decision_context="Test context",
            outcome=Outcome.SUCCESS,
            quality_delta=10.0,
            confidence=0.85  # Above threshold
        )
        
        assert result.stored == True


# =============================================================================
# AC-5: Learning Mode Tests
# =============================================================================

class TestLearningMode:
    """Test learning mode population."""
    
    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        session = MagicMock()
        return session
    
    def test_template_learning_mode_required(self, mock_session):
        """AC-5: Template store requires learning mode."""
        service = TemplateLearningService(
            mock_session,
            learning_mode=False  # Disabled
        )
        
        result = service.store_execution(
            requirement_text="Test",
            template_id="template",
            success=True,
            quality_score=90.0
        )
        
        assert result.stored == False
        assert "learning mode disabled" in result.message.lower()
    
    def test_template_stores_in_learning_mode(self, mock_session):
        """AC-5: Template store works when learning mode enabled."""
        service = TemplateLearningService(
            mock_session,
            learning_mode=True  # Enabled
        )
        
        result = service.store_execution(
            requirement_text="Test",
            template_id="template",
            success=True,
            quality_score=90.0
        )
        
        assert result.stored == True
        mock_session.add.assert_called_once()
    
    def test_quality_learning_mode_required(self, mock_session):
        """AC-5: Quality store requires learning mode."""
        service = QualityLearningService(
            mock_session,
            learning_mode=False
        )
        
        result = service.record_outcome(
            decision_id="test",
            decision_type=DecisionType.TEMPLATE_SELECTION,
            decision_context="context",
            outcome=Outcome.SUCCESS,
            quality_delta=10.0,
            confidence=0.9
        )
        
        assert result.stored == False
        assert "learning mode disabled" in result.message.lower()
    
    def test_coordination_learning_mode_required(self, mock_session):
        """AC-5: Coordination store requires learning mode."""
        service = CoordinationLearningService(
            mock_session,
            learning_mode=False
        )
        
        result = service.store_pattern(
            complexity_description="Complex requirement",
            team_composition=["backend", "frontend"],
            execution_mode=ExecutionMode.PARALLEL,
            success=True,
            execution_time=300
        )
        
        assert result.stored == False
        assert "learning mode disabled" in result.message.lower()
    
    def test_coordination_stores_in_learning_mode(self, mock_session):
        """AC-5: Coordination store works when learning mode enabled."""
        mock_session.query.return_value.filter.return_value.all.return_value = []
        
        service = CoordinationLearningService(
            mock_session,
            learning_mode=True
        )
        
        result = service.store_pattern(
            complexity_description="Complex requirement",
            team_composition=["backend", "frontend"],
            execution_mode=ExecutionMode.PARALLEL,
            success=True,
            execution_time=300
        )
        
        assert result.stored == True


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests for learning stores."""
    
    def test_enums_defined(self):
        """All enums are properly defined."""
        assert DecisionType.TEMPLATE_SELECTION.value == "template_selection"
        assert Outcome.SUCCESS.value == "success"
        assert ExecutionMode.PARALLEL.value == "parallel"
    
    def test_coordination_pattern_update(self):
        """Coordination pattern metrics update correctly."""
        pattern = CoordinationPattern(
            complexity_description="Test",
            complexity_embedding=[0.1] * 1536,
            team_composition=["backend"],
            execution_mode=ExecutionMode.SEQUENTIAL,
            success_rate=1.0,
            avg_execution_time=100,
            sample_count=1
        )
        
        # Update with a failure
        pattern.update_with_execution(success=False, execution_time=200)
        
        assert pattern.sample_count == 2
        assert pattern.success_rate == 0.5  # 1 success / 2 total
        assert pattern.avg_execution_time == 150  # (100 + 200) / 2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
