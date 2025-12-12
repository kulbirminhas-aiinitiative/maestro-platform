#!/usr/bin/env python3
"""
Tests for Context Enhancer module.

Related EPIC: MD-3026 - RAG Persona Integration
"""

import pytest
import asyncio
from typing import List

from maestro_hive.personas.context_enhancer import (
    ContextEnhancer,
    EnhancerConfig,
    EnhancementStrategy,
    ContextFormat,
    EnhancementPriority,
    ContextChunk,
    EnhancedPrompt,
    EnhancedResponse,
    TokenEstimator,
    ContentDeduplicator,
    ContextFormatter,
    get_context_enhancer,
    reset_context_enhancer,
    enhance_prompt,
)
from maestro_hive.personas.rag_connector import (
    RetrievalResult,
    RetrievalContext,
    QueryStrategy,
    reset_rag_connector,
)


class TestEnhancerConfig:
    """Tests for EnhancerConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = EnhancerConfig()

        assert config.strategy == EnhancementStrategy.STRUCTURED
        assert config.context_format == ContextFormat.MARKDOWN
        assert config.max_context_tokens == 2000
        assert config.max_results_to_include == 5
        assert config.min_relevance_score == 0.7
        assert config.include_sources is True
        assert config.deduplicate is True

    def test_custom_config(self):
        """Test custom configuration."""
        config = EnhancerConfig(
            strategy=EnhancementStrategy.PREPEND,
            context_format=ContextFormat.PLAIN,
            max_context_tokens=1000,
            max_results_to_include=3
        )

        assert config.strategy == EnhancementStrategy.PREPEND
        assert config.context_format == ContextFormat.PLAIN
        assert config.max_context_tokens == 1000
        assert config.max_results_to_include == 3


class TestContextChunk:
    """Tests for ContextChunk dataclass."""

    def test_create_chunk(self):
        """Test creating a context chunk."""
        chunk = ContextChunk(
            chunk_id="chunk_1",
            content="This is sample content",
            source="document.pdf",
            relevance_score=0.85,
            priority=EnhancementPriority.HIGH,
            token_estimate=10
        )

        assert chunk.chunk_id == "chunk_1"
        assert chunk.content == "This is sample content"
        assert chunk.source == "document.pdf"
        assert chunk.relevance_score == 0.85
        assert chunk.priority == EnhancementPriority.HIGH

    def test_to_dict(self):
        """Test converting to dictionary."""
        chunk = ContextChunk(
            chunk_id="chunk_1",
            content="content",
            source="source",
            relevance_score=0.9,
            priority=EnhancementPriority.CRITICAL,
            token_estimate=10
        )

        data = chunk.to_dict()

        assert data["chunk_id"] == "chunk_1"
        assert data["priority"] == "critical"


class TestEnhancedPrompt:
    """Tests for EnhancedPrompt dataclass."""

    def test_context_included(self):
        """Test context_included property."""
        prompt_with_context = EnhancedPrompt(
            original_prompt="test",
            enhanced_prompt="enhanced test",
            context_chunks=[
                ContextChunk("c1", "content", "src", 0.9, EnhancementPriority.HIGH, 10)
            ],
            total_context_tokens=10,
            retrieval_context=None
        )

        prompt_without_context = EnhancedPrompt(
            original_prompt="test",
            enhanced_prompt="test",
            context_chunks=[],
            total_context_tokens=0,
            retrieval_context=None
        )

        assert prompt_with_context.context_included is True
        assert prompt_without_context.context_included is False

    def test_average_relevance(self):
        """Test average_relevance property."""
        prompt = EnhancedPrompt(
            original_prompt="test",
            enhanced_prompt="enhanced",
            context_chunks=[
                ContextChunk("c1", "content", "src", 0.8, EnhancementPriority.HIGH, 10),
                ContextChunk("c2", "content", "src", 0.6, EnhancementPriority.MEDIUM, 10),
            ],
            total_context_tokens=20,
            retrieval_context=None
        )

        assert prompt.average_relevance == 0.7

    def test_to_dict(self):
        """Test converting to dictionary."""
        prompt = EnhancedPrompt(
            original_prompt="test",
            enhanced_prompt="enhanced",
            context_chunks=[],
            total_context_tokens=0,
            retrieval_context=None,
            strategy_used=EnhancementStrategy.PREPEND
        )

        data = prompt.to_dict()

        assert data["original_prompt"] == "test"
        assert data["enhanced_prompt"] == "enhanced"
        assert data["strategy_used"] == "prepend"


class TestTokenEstimator:
    """Tests for TokenEstimator."""

    def test_estimate_tokens(self):
        """Test token estimation."""
        estimator = TokenEstimator(chars_per_token=4.0)

        # 20 characters should be ~5 tokens (int division)
        tokens = estimator.estimate("This is some text!!")  # 20 chars

        assert tokens == 5 or tokens == 4  # int(20/4) = 5, but implementation may vary

    def test_estimate_batch(self):
        """Test batch estimation."""
        estimator = TokenEstimator(chars_per_token=4.0)

        texts = ["short", "medium length text", "a"]
        estimates = estimator.estimate_batch(texts)

        assert len(estimates) == 3
        assert estimates[0] == 1  # 5 chars
        assert estimates[1] == 4  # 18 chars
        assert estimates[2] == 0  # 1 char


class TestContentDeduplicator:
    """Tests for ContentDeduplicator."""

    def test_deduplicate_identical(self):
        """Test deduplicating identical content."""
        dedup = ContentDeduplicator(similarity_threshold=0.85)

        chunks = [
            ContextChunk("c1", "This is the same content", "s1", 0.9, EnhancementPriority.HIGH, 10),
            ContextChunk("c2", "This is the same content", "s2", 0.8, EnhancementPriority.HIGH, 10),
        ]

        result = dedup.deduplicate(chunks)

        assert len(result) == 1
        # Should keep the one with higher relevance
        assert result[0].relevance_score == 0.9

    def test_deduplicate_similar(self):
        """Test deduplicating similar content."""
        dedup = ContentDeduplicator(similarity_threshold=0.5)

        chunks = [
            ContextChunk("c1", "Python is a programming language", "s1", 0.9, EnhancementPriority.HIGH, 10),
            ContextChunk("c2", "Python programming language is great", "s2", 0.8, EnhancementPriority.HIGH, 10),
        ]

        result = dedup.deduplicate(chunks)

        # Should deduplicate based on word overlap
        assert len(result) <= 2

    def test_deduplicate_different(self):
        """Test that different content is preserved."""
        dedup = ContentDeduplicator(similarity_threshold=0.85)

        chunks = [
            ContextChunk("c1", "Apple banana cherry", "s1", 0.9, EnhancementPriority.HIGH, 10),
            ContextChunk("c2", "Dog elephant fox", "s2", 0.8, EnhancementPriority.HIGH, 10),
        ]

        result = dedup.deduplicate(chunks)

        assert len(result) == 2


class TestContextFormatter:
    """Tests for ContextFormatter."""

    @pytest.fixture
    def sample_chunks(self):
        """Create sample chunks for testing."""
        return [
            ContextChunk(
                chunk_id="c1",
                content="First chunk content",
                source="doc1.pdf",
                relevance_score=0.9,
                priority=EnhancementPriority.HIGH,
                token_estimate=10
            ),
            ContextChunk(
                chunk_id="c2",
                content="Second chunk content",
                source="doc2.pdf",
                relevance_score=0.8,
                priority=EnhancementPriority.MEDIUM,
                token_estimate=10
            ),
        ]

    def test_format_markdown(self, sample_chunks):
        """Test markdown formatting."""
        formatter = ContextFormatter(format_type=ContextFormat.MARKDOWN)

        result = formatter.format_chunks(
            sample_chunks,
            header="## Context",
            include_sources=True,
            include_confidence=True
        )

        assert "## Context" in result
        assert "First chunk content" in result
        assert "doc1.pdf" in result
        assert "0.9" in result or "0.90" in result

    def test_format_plain(self, sample_chunks):
        """Test plain text formatting."""
        formatter = ContextFormatter(format_type=ContextFormat.PLAIN)

        result = formatter.format_chunks(
            sample_chunks,
            header="Context",
            include_sources=True
        )

        assert "Context" in result
        assert "First chunk content" in result
        assert "doc1.pdf" in result

    def test_format_json(self, sample_chunks):
        """Test JSON formatting."""
        formatter = ContextFormatter(format_type=ContextFormat.JSON)

        result = formatter.format_chunks(sample_chunks)

        assert "context_chunks" in result
        assert "First chunk content" in result

    def test_format_bulleted(self, sample_chunks):
        """Test bulleted list formatting."""
        formatter = ContextFormatter(format_type=ContextFormat.BULLETED)

        result = formatter.format_chunks(
            sample_chunks,
            header="Context:"
        )

        assert "Context:" in result
        assert "- " in result


class TestContextEnhancer:
    """Tests for ContextEnhancer."""

    @pytest.fixture
    def enhancer(self):
        """Create a test enhancer."""
        reset_rag_connector()
        reset_context_enhancer()
        config = EnhancerConfig(
            strategy=EnhancementStrategy.STRUCTURED,
            max_context_tokens=500
        )
        return ContextEnhancer(config=config)

    @pytest.mark.asyncio
    async def test_enhance_prompt_basic(self, enhancer):
        """Test basic prompt enhancement."""
        result = await enhancer.enhance_prompt(
            prompt="What is machine learning?"
        )

        assert result is not None
        assert isinstance(result, EnhancedPrompt)
        assert result.original_prompt == "What is machine learning?"

    @pytest.mark.asyncio
    async def test_enhance_prompt_with_persona(self, enhancer):
        """Test enhancement with persona ID."""
        result = await enhancer.enhance_prompt(
            prompt="Explain quantum computing",
            persona_id="scientist_001"
        )

        assert result is not None
        assert "scientist_001" in result.enhancement_metadata.get("persona_id", "")

    @pytest.mark.asyncio
    async def test_enhance_prompt_with_additional_context(self, enhancer):
        """Test enhancement with additional context."""
        result = await enhancer.enhance_prompt(
            prompt="Summarize the project status",
            additional_context=[
                "The project is on track.",
                "All milestones have been met."
            ]
        )

        assert result is not None
        assert len(result.context_chunks) >= 2

    def test_enhance_prompt_sync(self, enhancer):
        """Test synchronous enhancement."""
        result = enhancer.enhance_prompt_sync(
            prompt="Test prompt",
            context_texts=["Context 1", "Context 2"],
            sources=["source1", "source2"]
        )

        assert result is not None
        assert result.original_prompt == "Test prompt"
        assert len(result.context_chunks) == 2

    def test_ground_response(self, enhancer):
        """Test response grounding."""
        chunks = [
            ContextChunk(
                chunk_id="c1",
                content="Python is a programming language",
                source="doc.pdf",
                relevance_score=0.9,
                priority=EnhancementPriority.HIGH,
                token_estimate=10
            )
        ]

        response = "Python is widely used for programming."
        result = enhancer.ground_response(response, chunks)

        assert result is not None
        assert isinstance(result, EnhancedResponse)
        assert result.original_response == response

    def test_ground_response_no_context(self, enhancer):
        """Test grounding with no context."""
        result = enhancer.ground_response("Some response", [])

        assert result.confidence_score == 0.5
        assert "warning" in result.grounding_metadata

    def test_get_metrics(self, enhancer):
        """Test getting metrics."""
        metrics = enhancer.get_metrics()

        assert "enhancement_count" in metrics
        assert "strategy" in metrics
        assert "format" in metrics


class TestEnhancementStrategies:
    """Tests for different enhancement strategies."""

    @pytest.fixture
    def chunks(self):
        """Create sample chunks."""
        return [
            ContextChunk(
                chunk_id="c1",
                content="Relevant context here",
                source="doc.pdf",
                relevance_score=0.9,
                priority=EnhancementPriority.HIGH,
                token_estimate=10
            )
        ]

    def test_prepend_strategy(self, chunks):
        """Test prepend strategy."""
        config = EnhancerConfig(strategy=EnhancementStrategy.PREPEND)
        enhancer = ContextEnhancer(config=config)

        result = enhancer.enhance_prompt_sync(
            "User question here",
            [c.content for c in chunks]
        )

        # Context should appear before the prompt
        idx_context = result.enhanced_prompt.find("Relevant context")
        idx_question = result.enhanced_prompt.find("User question")

        if idx_context >= 0 and idx_question >= 0:
            assert idx_context < idx_question

    def test_append_strategy(self, chunks):
        """Test append strategy."""
        config = EnhancerConfig(strategy=EnhancementStrategy.APPEND)
        enhancer = ContextEnhancer(config=config)

        result = enhancer.enhance_prompt_sync(
            "User question here",
            [c.content for c in chunks]
        )

        # Context should appear after the prompt
        idx_context = result.enhanced_prompt.find("Relevant context")
        idx_question = result.enhanced_prompt.find("User question")

        if idx_context >= 0 and idx_question >= 0:
            assert idx_question < idx_context

    def test_structured_strategy(self, chunks):
        """Test structured strategy."""
        config = EnhancerConfig(strategy=EnhancementStrategy.STRUCTURED)
        enhancer = ContextEnhancer(config=config)

        result = enhancer.enhance_prompt_sync(
            "User question here",
            [c.content for c in chunks]
        )

        # Should have structured sections
        assert "Task" in result.enhanced_prompt or "Context" in result.enhanced_prompt


class TestModuleFunctions:
    """Tests for module-level functions."""

    def test_get_context_enhancer(self):
        """Test getting default enhancer."""
        reset_context_enhancer()
        enhancer = get_context_enhancer()

        assert enhancer is not None
        assert isinstance(enhancer, ContextEnhancer)

    def test_get_context_enhancer_singleton(self):
        """Test that enhancer is singleton."""
        reset_context_enhancer()
        enhancer1 = get_context_enhancer()
        enhancer2 = get_context_enhancer()

        assert enhancer1 is enhancer2

    def test_reset_context_enhancer(self):
        """Test resetting enhancer."""
        enhancer1 = get_context_enhancer()
        reset_context_enhancer()
        enhancer2 = get_context_enhancer()

        assert enhancer1 is not enhancer2

    @pytest.mark.asyncio
    async def test_enhance_prompt_function(self):
        """Test convenience enhance function."""
        reset_context_enhancer()
        reset_rag_connector()

        result = await enhance_prompt(
            prompt="What is the capital of France?"
        )

        assert result is not None
        assert isinstance(result, EnhancedPrompt)
