"""
Tests for Context Formatter.

EPIC: MD-2499
AC-4: Format context for persona injection
"""

import pytest

from maestro_hive.rag import (
    ContextFormatter,
    ContextConfig,
    FormattedContext,
    PatternSummary,
    SuccessPattern,
    FailurePattern,
)


class TestContextFormatter:
    """Test ContextFormatter functionality."""

    @pytest.fixture
    def formatter(self) -> ContextFormatter:
        """Create a context formatter."""
        return ContextFormatter()

    @pytest.fixture
    def sample_patterns(self) -> PatternSummary:
        """Create sample pattern summary."""
        return PatternSummary(
            success_patterns=[
                SuccessPattern(
                    pattern_id="success-001",
                    description="Phase 'design' consistently passes",
                    frequency=5,
                    confidence=0.85,
                    context={"phase_name": "design", "success_rate": 0.85},
                    examples=["exec-001", "exec-002"],
                ),
                SuccessPattern(
                    pattern_id="success-002",
                    description="Average execution time: 1200s",
                    frequency=8,
                    confidence=0.90,
                    context={"avg_seconds": 1200},
                ),
            ],
            failure_patterns=[
                FailurePattern(
                    pattern_id="failure-001",
                    description="Phase 'testing' frequently fails",
                    failure_type="test_failure",
                    frequency=3,
                    confidence=0.75,
                    mitigation="Review test assertions and fix failing test cases",
                    context={"phase_name": "testing", "failure_rate": 0.75},
                    examples=["Test assertion failed"],
                ),
            ],
            total_executions_analyzed=10,
            confidence_score=0.82,
        )

    @pytest.fixture
    def empty_patterns(self) -> PatternSummary:
        """Create empty pattern summary."""
        return PatternSummary(
            success_patterns=[],
            failure_patterns=[],
            total_executions_analyzed=0,
            confidence_score=0.0,
        )

    def test_formatter_initialization(self, formatter: ContextFormatter):
        """Test formatter initializes correctly."""
        assert formatter is not None

    def test_format_returns_formatted_context(
        self,
        formatter: ContextFormatter,
        sample_patterns: PatternSummary,
    ):
        """Test format returns FormattedContext."""
        result = formatter.format(sample_patterns)

        assert isinstance(result, FormattedContext)
        assert result.formatted_text is not None
        assert result.token_count > 0
        assert result.execution_count == 10
        assert result.patterns_included == 3

    def test_format_empty_patterns(
        self,
        formatter: ContextFormatter,
        empty_patterns: PatternSummary,
    ):
        """Test format with empty patterns."""
        result = formatter.format(empty_patterns)

        assert isinstance(result, FormattedContext)
        assert result.execution_count == 0
        assert result.patterns_included == 0

    def test_format_structured_style(
        self,
        formatter: ContextFormatter,
        sample_patterns: PatternSummary,
    ):
        """Test structured formatting style."""
        config = ContextConfig(format_style="structured")
        result = formatter.format(sample_patterns, config)

        # Structured format should have headers
        assert "##" in result.formatted_text
        assert "Success Patterns" in result.formatted_text or "Failure Patterns" in result.formatted_text

    def test_format_narrative_style(
        self,
        formatter: ContextFormatter,
        sample_patterns: PatternSummary,
    ):
        """Test narrative formatting style."""
        config = ContextConfig(format_style="narrative")
        result = formatter.format(sample_patterns, config)

        # Narrative should be more prose-like
        assert "Analysis of" in result.formatted_text or "executions" in result.formatted_text

    def test_format_bullet_style(
        self,
        formatter: ContextFormatter,
        sample_patterns: PatternSummary,
    ):
        """Test bullet formatting style."""
        config = ContextConfig(format_style="bullet")
        result = formatter.format(sample_patterns, config)

        # Bullet format should have bullet points
        assert "-" in result.formatted_text

    def test_format_respects_max_tokens(
        self,
        formatter: ContextFormatter,
        sample_patterns: PatternSummary,
    ):
        """Test format respects max_tokens limit."""
        config = ContextConfig(max_tokens=50)
        result = formatter.format(sample_patterns, config)

        assert result.token_count <= 50 or result.truncated

    def test_format_truncation_marker(
        self,
        formatter: ContextFormatter,
        sample_patterns: PatternSummary,
    ):
        """Test truncation adds marker."""
        config = ContextConfig(max_tokens=20)  # Very small
        result = formatter.format(sample_patterns, config)

        if result.truncated:
            assert "truncated" in result.formatted_text.lower()

    def test_format_prioritizes_failures(
        self,
        formatter: ContextFormatter,
        sample_patterns: PatternSummary,
    ):
        """Test failures are prioritized when configured."""
        config = ContextConfig(prioritize_failures=True)
        result = formatter.format(sample_patterns, config)

        # Find positions of patterns in output
        failure_pos = result.formatted_text.find("Failure")
        success_pos = result.formatted_text.find("Success")

        # Failure should appear before success when prioritized
        if failure_pos >= 0 and success_pos >= 0:
            assert failure_pos < success_pos


class TestPersonaFormatting:
    """Test persona-specific formatting."""

    @pytest.fixture
    def formatter(self) -> ContextFormatter:
        return ContextFormatter()

    @pytest.fixture
    def sample_patterns(self) -> PatternSummary:
        """Create patterns with varied content."""
        return PatternSummary(
            success_patterns=[
                SuccessPattern(
                    pattern_id="arch-001",
                    description="Architecture design pattern works well",
                    frequency=5,
                    confidence=0.85,
                ),
                SuccessPattern(
                    pattern_id="test-001",
                    description="Test coverage above 80%",
                    frequency=4,
                    confidence=0.80,
                ),
                SuccessPattern(
                    pattern_id="duration-001",
                    description="Average execution time: 1200s",
                    frequency=8,
                    confidence=0.90,
                    context={"avg_seconds": 1200},
                ),
            ],
            failure_patterns=[
                FailurePattern(
                    pattern_id="build-001",
                    description="Build fails on dependency issues",
                    failure_type="build_error",
                    frequency=3,
                    confidence=0.70,
                    mitigation="Check dependency versions",
                ),
                FailurePattern(
                    pattern_id="test-002",
                    description="Integration tests timeout",
                    failure_type="test_failure",
                    frequency=2,
                    confidence=0.65,
                    examples=["Test timeout after 300s"],
                ),
            ],
            total_executions_analyzed=15,
            confidence_score=0.75,
        )

    def test_format_for_architect(
        self,
        formatter: ContextFormatter,
        sample_patterns: PatternSummary,
    ):
        """Test architect persona formatting."""
        result = formatter.format_for_persona(sample_patterns, "architect")

        assert isinstance(result, str)
        assert "Architecture" in result or "architecture" in result.lower()

    def test_format_for_developer(
        self,
        formatter: ContextFormatter,
        sample_patterns: PatternSummary,
    ):
        """Test developer persona formatting."""
        result = formatter.format_for_persona(sample_patterns, "developer")

        assert isinstance(result, str)
        assert "Implementation" in result or "implementation" in result.lower() or "patterns" in result.lower()

    def test_format_for_tester(
        self,
        formatter: ContextFormatter,
        sample_patterns: PatternSummary,
    ):
        """Test tester persona formatting."""
        result = formatter.format_for_persona(sample_patterns, "tester")

        assert isinstance(result, str)
        assert "Testing" in result or "test" in result.lower()

    def test_format_for_reviewer(
        self,
        formatter: ContextFormatter,
        sample_patterns: PatternSummary,
    ):
        """Test reviewer persona formatting."""
        result = formatter.format_for_persona(sample_patterns, "reviewer")

        assert isinstance(result, str)
        assert "Quality" in result or "Review" in result

    def test_format_for_unknown_persona(
        self,
        formatter: ContextFormatter,
        sample_patterns: PatternSummary,
    ):
        """Test unknown persona falls back to structured."""
        result = formatter.format_for_persona(sample_patterns, "unknown")

        # Should still produce valid output
        assert isinstance(result, str)
        assert len(result) > 0


class TestContextConfig:
    """Test ContextConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = ContextConfig()

        assert config.max_tokens == 2000
        assert config.format_style == "structured"
        assert config.include_metadata is True
        assert config.prioritize_failures is True

    def test_custom_config(self):
        """Test custom configuration."""
        config = ContextConfig(
            max_tokens=1000,
            format_style="bullet",
            include_metadata=False,
            prioritize_failures=False,
        )

        assert config.max_tokens == 1000
        assert config.format_style == "bullet"
        assert config.include_metadata is False
        assert config.prioritize_failures is False


class TestFormattedContext:
    """Test FormattedContext model."""

    def test_formatted_context_fields(self):
        """Test FormattedContext has all fields."""
        context = FormattedContext(
            formatted_text="Test content",
            token_count=2,
            execution_count=5,
            patterns_included=3,
            truncated=False,
        )

        assert context.formatted_text == "Test content"
        assert context.token_count == 2
        assert context.execution_count == 5
        assert context.patterns_included == 3
        assert context.truncated is False

    def test_formatted_context_truncated(self):
        """Test FormattedContext with truncation."""
        context = FormattedContext(
            formatted_text="Truncated...",
            token_count=100,
            execution_count=50,
            patterns_included=10,
            truncated=True,
        )

        assert context.truncated is True
