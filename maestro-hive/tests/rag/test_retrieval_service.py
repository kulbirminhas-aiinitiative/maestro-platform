"""
Tests for RAG Retrieval Service.

EPIC: MD-2499
"""

import pytest
from datetime import datetime
from typing import List

from maestro_hive.rag import (
    RetrievalService,
    RetrievalConfig,
    RetrievalResult,
    ExecutionRecord,
    ExecutionOutcome,
    InMemoryStorage,
    SimpleEmbedding,
    FormattedContext,
)
from maestro_hive.rag.models import PhaseResult
from maestro_hive.rag.exceptions import RetrievalError


class TestRetrievalService:
    """Test RetrievalService core functionality."""

    @pytest.fixture
    def service(self) -> RetrievalService:
        """Create a test service with in-memory storage."""
        return RetrievalService(
            embedding_provider=SimpleEmbedding(dimension=64),
            storage=InMemoryStorage(),
            config=RetrievalConfig(
                default_top_k=5,
                similarity_threshold=0.0,  # Accept all for testing
                cache_embeddings=False,
            ),
        )

    @pytest.fixture
    def populated_service(self, service: RetrievalService) -> RetrievalService:
        """Create a service with sample executions."""
        # Add sample executions
        service.store_execution(
            execution_id="exec-001",
            requirement_text="Build a REST API with user authentication",
            outcome=ExecutionOutcome.SUCCESS,
            metadata={"type": "api", "language": "python"},
            duration_seconds=3600.0,
        )
        service.store_execution(
            execution_id="exec-002",
            requirement_text="Create a REST API with JWT tokens",
            outcome=ExecutionOutcome.SUCCESS,
            metadata={"type": "api", "language": "python"},
            duration_seconds=2800.0,
        )
        service.store_execution(
            execution_id="exec-003",
            requirement_text="Implement a dashboard frontend",
            outcome=ExecutionOutcome.FAILURE,
            metadata={"type": "frontend", "framework": "react"},
            duration_seconds=1200.0,
        )
        service.store_execution(
            execution_id="exec-004",
            requirement_text="Build machine learning pipeline",
            outcome=ExecutionOutcome.PARTIAL,
            metadata={"type": "ml", "framework": "pytorch"},
            duration_seconds=7200.0,
        )
        return service

    def test_service_initialization(self, service: RetrievalService):
        """Test service initializes correctly."""
        assert service is not None
        assert service.execution_count == 0
        assert service.config.default_top_k == 5

    def test_store_execution(self, service: RetrievalService):
        """Test storing an execution record."""
        record = service.store_execution(
            execution_id="test-001",
            requirement_text="Test requirement",
            outcome=ExecutionOutcome.SUCCESS,
            metadata={"key": "value"},
            duration_seconds=100.0,
        )

        assert record.execution_id == "test-001"
        assert record.requirement_text == "Test requirement"
        assert record.outcome == ExecutionOutcome.SUCCESS
        assert record.embedding is not None
        assert len(record.embedding) == 64  # SimpleEmbedding dimension

    def test_execution_count(self, populated_service: RetrievalService):
        """Test execution count is accurate."""
        assert populated_service.execution_count == 4

    def test_search_returns_results(self, populated_service: RetrievalService):
        """Test search returns similar executions."""
        results = populated_service.search("Build a REST API")

        assert len(results) > 0
        assert all(isinstance(r, RetrievalResult) for r in results)
        assert all(0 <= r.similarity_score <= 1 for r in results)

    def test_search_results_ordered_by_similarity(self, populated_service: RetrievalService):
        """Test search results are ordered by similarity (descending)."""
        results = populated_service.search("REST API authentication")

        if len(results) > 1:
            scores = [r.similarity_score for r in results]
            assert scores == sorted(scores, reverse=True)

    def test_search_respects_top_k(self, populated_service: RetrievalService):
        """Test search respects top_k parameter."""
        results = populated_service.search("API", top_k=2)
        assert len(results) <= 2

    def test_search_respects_threshold(self, populated_service: RetrievalService):
        """Test search respects similarity threshold."""
        results = populated_service.search("API", threshold=0.99)
        # With high threshold, may return few or no results
        for result in results:
            assert result.similarity_score >= 0.99

    def test_get_execution_by_id(self, populated_service: RetrievalService):
        """Test retrieving execution by ID."""
        record = populated_service.get_execution("exec-001")

        assert record is not None
        assert record.execution_id == "exec-001"
        assert "REST API" in record.requirement_text

    def test_get_nonexistent_execution(self, populated_service: RetrievalService):
        """Test retrieving non-existent execution returns None."""
        record = populated_service.get_execution("nonexistent")
        assert record is None

    def test_delete_execution(self, populated_service: RetrievalService):
        """Test deleting an execution."""
        initial_count = populated_service.execution_count

        success = populated_service.delete_execution("exec-001")

        assert success is True
        assert populated_service.execution_count == initial_count - 1
        assert populated_service.get_execution("exec-001") is None

    def test_delete_nonexistent_execution(self, populated_service: RetrievalService):
        """Test deleting non-existent execution returns False."""
        success = populated_service.delete_execution("nonexistent")
        assert success is False

    def test_list_executions(self, populated_service: RetrievalService):
        """Test listing all executions."""
        executions = populated_service.list_executions()

        assert len(executions) == 4
        assert all(isinstance(e, ExecutionRecord) for e in executions)

    def test_list_executions_by_outcome(self, populated_service: RetrievalService):
        """Test filtering executions by outcome."""
        successes = populated_service.list_executions(outcome=ExecutionOutcome.SUCCESS)
        failures = populated_service.list_executions(outcome=ExecutionOutcome.FAILURE)

        assert len(successes) == 2
        assert len(failures) == 1
        assert all(e.outcome == ExecutionOutcome.SUCCESS for e in successes)

    def test_list_executions_with_limit(self, populated_service: RetrievalService):
        """Test listing executions with limit."""
        executions = populated_service.list_executions(limit=2)
        assert len(executions) == 2

    def test_get_context(self, populated_service: RetrievalService):
        """Test get_context returns formatted context."""
        context = populated_service.get_context("Build REST API")

        assert isinstance(context, FormattedContext)
        assert context.execution_count > 0
        assert len(context.formatted_text) > 0
        assert context.token_count > 0

    def test_get_context_no_results(self, service: RetrievalService):
        """Test get_context with no stored executions."""
        context = service.get_context("Some query")

        assert context.execution_count == 0
        assert "No similar" in context.formatted_text

    def test_get_context_max_tokens(self, populated_service: RetrievalService):
        """Test get_context respects max_tokens."""
        context = populated_service.get_context("API", max_tokens=50)

        # Token count should be at or near limit
        assert context.token_count <= 50 or context.truncated


class TestVectorSimilaritySearch:
    """Test AC-1: Vector similarity search on requirement text."""

    @pytest.fixture
    def service(self) -> RetrievalService:
        """Create service with deterministic embeddings."""
        return RetrievalService(
            embedding_provider=SimpleEmbedding(dimension=128),
            storage=InMemoryStorage(),
            config=RetrievalConfig(similarity_threshold=0.0),
        )

    def test_similar_texts_have_higher_scores(self, service: RetrievalService):
        """Test similar texts produce higher similarity scores."""
        # Store varied executions
        service.store_execution(
            "exec-1", "Build REST API with authentication", ExecutionOutcome.SUCCESS
        )
        service.store_execution(
            "exec-2", "Create REST API with user login", ExecutionOutcome.SUCCESS
        )
        service.store_execution(
            "exec-3", "Implement machine learning model", ExecutionOutcome.SUCCESS
        )

        results = service.search("Build REST API")

        # REST API related should score higher than ML
        api_results = [r for r in results if "API" in r.execution.requirement_text]
        ml_results = [r for r in results if "machine learning" in r.execution.requirement_text]

        if api_results and ml_results:
            max_api_score = max(r.similarity_score for r in api_results)
            max_ml_score = max(r.similarity_score for r in ml_results)
            assert max_api_score >= max_ml_score

    def test_embedding_generated_for_stored_executions(self, service: RetrievalService):
        """Test embeddings are generated when storing executions."""
        record = service.store_execution(
            "exec-1", "Test requirement text", ExecutionOutcome.SUCCESS
        )

        assert record.embedding is not None
        assert len(record.embedding) == 128
        assert all(isinstance(x, float) for x in record.embedding)


class TestTopKRetrieval:
    """Test AC-2: Retrieve top-k similar executions."""

    @pytest.fixture
    def service_with_many_executions(self) -> RetrievalService:
        """Create service with many executions."""
        service = RetrievalService(
            embedding_provider=SimpleEmbedding(dimension=64),
            storage=InMemoryStorage(),
            config=RetrievalConfig(similarity_threshold=0.0, max_results=100),
        )

        # Add 20 executions
        for i in range(20):
            service.store_execution(
                f"exec-{i:03d}",
                f"Execution number {i} with API features",
                ExecutionOutcome.SUCCESS if i % 3 != 0 else ExecutionOutcome.FAILURE,
            )

        return service

    def test_top_k_limits_results(self, service_with_many_executions: RetrievalService):
        """Test top_k parameter limits results."""
        for k in [1, 3, 5, 10]:
            results = service_with_many_executions.search("API", top_k=k)
            assert len(results) <= k

    def test_default_top_k_from_config(self, service_with_many_executions: RetrievalService):
        """Test default top_k is used from config."""
        # Config has default_top_k=5
        results = service_with_many_executions.search("API")
        assert len(results) <= service_with_many_executions.config.default_top_k

    def test_max_results_caps_top_k(self):
        """Test max_results caps top_k."""
        service = RetrievalService(
            embedding_provider=SimpleEmbedding(dimension=64),
            storage=InMemoryStorage(),
            config=RetrievalConfig(max_results=3),
        )

        for i in range(10):
            service.store_execution(f"exec-{i}", f"Test {i}", ExecutionOutcome.SUCCESS)

        results = service.search("Test", top_k=100)
        assert len(results) <= 3


class TestKeywordFallback:
    """Test keyword search fallback."""

    def test_keyword_search_when_embedding_fails(self):
        """Test fallback to keyword search."""
        # This test verifies the fallback mechanism exists
        service = RetrievalService(
            embedding_provider=SimpleEmbedding(dimension=64),
            storage=InMemoryStorage(),
        )

        service.store_execution("exec-1", "Build REST API", ExecutionOutcome.SUCCESS)

        # Direct keyword search test
        results = service._keyword_search("REST API", top_k=5)

        assert len(results) > 0
        assert results[0].match_details.get("method") == "keyword"


class TestExecutionRecordSerialization:
    """Test ExecutionRecord serialization."""

    def test_to_dict_and_from_dict(self):
        """Test round-trip serialization."""
        original = ExecutionRecord(
            execution_id="test-001",
            requirement_text="Test requirement",
            outcome=ExecutionOutcome.SUCCESS,
            timestamp=datetime.utcnow(),
            duration_seconds=100.0,
            phase_results={
                "phase1": PhaseResult(
                    phase_name="phase1",
                    status="passed",
                    score=0.95,
                    duration_seconds=50.0,
                )
            },
            metadata={"key": "value"},
            embedding=[0.1, 0.2, 0.3],
        )

        # Convert to dict and back
        data = original.to_dict()
        restored = ExecutionRecord.from_dict(data)

        assert restored.execution_id == original.execution_id
        assert restored.requirement_text == original.requirement_text
        assert restored.outcome == original.outcome
        assert restored.duration_seconds == original.duration_seconds
        assert restored.embedding == original.embedding
        assert restored.metadata == original.metadata


class TestRetrievalConfig:
    """Test RetrievalConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = RetrievalConfig()

        assert config.default_top_k == 5
        assert config.similarity_threshold == 0.7
        assert config.max_results == 20
        assert config.timeout_seconds == 30.0
        assert config.cache_embeddings is True

    def test_custom_config(self):
        """Test custom configuration."""
        config = RetrievalConfig(
            default_top_k=10,
            similarity_threshold=0.8,
            max_results=50,
        )

        assert config.default_top_k == 10
        assert config.similarity_threshold == 0.8
        assert config.max_results == 50
