"""
Tests for ErrorPatternAnalyzer - Error classification and analysis.

EPIC: MD-3027 - Self-Healing Execution Loop (Phase 3)
Task: MD-3029 - Implement ErrorPatternAnalyzer
"""

import pytest

from maestro_hive.execution.error_analyzer import (
    ErrorPatternAnalyzer,
    ErrorPattern,
    ErrorCategory,
    ErrorSeverity,
    RecoverySuggestion,
    ErrorAnalysisResult,
    DEFAULT_ERROR_PATTERNS,
    get_error_analyzer,
    reset_error_analyzer,
)


class TestErrorCategory:
    """Tests for ErrorCategory enum."""

    def test_all_categories_defined(self):
        """Test all expected categories are defined."""
        categories = [
            ErrorCategory.NETWORK,
            ErrorCategory.TIMEOUT,
            ErrorCategory.AUTHENTICATION,
            ErrorCategory.AUTHORIZATION,
            ErrorCategory.RESOURCE,
            ErrorCategory.VALIDATION,
            ErrorCategory.CONFIGURATION,
            ErrorCategory.DEPENDENCY,
            ErrorCategory.TRANSIENT,
            ErrorCategory.PERMANENT,
            ErrorCategory.UNKNOWN,
        ]
        assert len(categories) == 11


class TestErrorSeverity:
    """Tests for ErrorSeverity enum."""

    def test_all_severities_defined(self):
        """Test all expected severities are defined."""
        severities = [
            ErrorSeverity.LOW,
            ErrorSeverity.MEDIUM,
            ErrorSeverity.HIGH,
            ErrorSeverity.CRITICAL,
        ]
        assert len(severities) == 4


class TestRecoverySuggestion:
    """Tests for RecoverySuggestion enum."""

    def test_all_suggestions_defined(self):
        """Test all expected suggestions are defined."""
        suggestions = [
            RecoverySuggestion.RETRY_IMMEDIATELY,
            RecoverySuggestion.RETRY_WITH_BACKOFF,
            RecoverySuggestion.REFRESH_CREDENTIALS,
            RecoverySuggestion.CHECK_CONFIGURATION,
            RecoverySuggestion.INSTALL_DEPENDENCY,
            RecoverySuggestion.INCREASE_TIMEOUT,
            RecoverySuggestion.SCALE_RESOURCES,
            RecoverySuggestion.MANUAL_INTERVENTION,
            RecoverySuggestion.SKIP_AND_CONTINUE,
            RecoverySuggestion.ESCALATE_TO_JIRA,
        ]
        assert len(suggestions) == 10


class TestErrorPattern:
    """Tests for ErrorPattern dataclass."""

    def test_create_pattern(self):
        """Test creating an error pattern."""
        pattern = ErrorPattern(
            pattern_id="test_pattern",
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            regex_patterns=[r"connection.*refused"],
            keywords=["ConnectionError"],
            recovery_suggestions=[RecoverySuggestion.RETRY_WITH_BACKOFF],
            description="Test pattern",
            is_transient=True,
        )
        assert pattern.pattern_id == "test_pattern"
        assert pattern.category == ErrorCategory.NETWORK
        assert pattern.is_transient is True

    def test_pattern_compilation(self):
        """Test regex pattern compilation."""
        pattern = ErrorPattern(
            pattern_id="test",
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.LOW,
            regex_patterns=[r"test\d+"],
            keywords=[],
            recovery_suggestions=[],
            description="Test",
        )
        # Patterns should be compiled after __post_init__
        assert len(pattern._compiled_patterns) == 1


class TestErrorAnalysisResult:
    """Tests for ErrorAnalysisResult dataclass."""

    def test_create_result(self):
        """Test creating an analysis result."""
        result = ErrorAnalysisResult(
            error_hash="abc123",
            error_type="ValueError",
            error_message="Invalid value",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.MEDIUM,
            recovery_suggestions=[RecoverySuggestion.CHECK_CONFIGURATION],
        )
        assert result.error_hash == "abc123"
        assert result.category == ErrorCategory.VALIDATION

    def test_to_dict(self):
        """Test serialization to dictionary."""
        result = ErrorAnalysisResult(
            error_hash="abc123",
            error_type="ValueError",
            error_message="Invalid value",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.MEDIUM,
            recovery_suggestions=[RecoverySuggestion.CHECK_CONFIGURATION],
            confidence_score=0.85,
        )
        data = result.to_dict()
        assert data["error_hash"] == "abc123"
        assert data["category"] == "validation"
        assert data["confidence_score"] == 0.85


class TestDefaultErrorPatterns:
    """Tests for default error patterns."""

    def test_default_patterns_exist(self):
        """Test that default patterns are defined."""
        assert len(DEFAULT_ERROR_PATTERNS) > 0

    def test_network_pattern_exists(self):
        """Test network pattern exists."""
        network_patterns = [p for p in DEFAULT_ERROR_PATTERNS if p.category == ErrorCategory.NETWORK]
        assert len(network_patterns) > 0

    def test_timeout_pattern_exists(self):
        """Test timeout pattern exists."""
        timeout_patterns = [p for p in DEFAULT_ERROR_PATTERNS if p.category == ErrorCategory.TIMEOUT]
        assert len(timeout_patterns) > 0


class TestErrorPatternAnalyzer:
    """Tests for ErrorPatternAnalyzer class."""

    @pytest.fixture
    def analyzer(self):
        """Create analyzer for tests."""
        return ErrorPatternAnalyzer(enable_learning=True)

    @pytest.mark.asyncio
    async def test_analyze_network_error(self, analyzer):
        """Test analyzing a network error."""
        error = ConnectionError("Connection refused")
        result = await analyzer.analyze(error)

        assert result.category == ErrorCategory.NETWORK
        assert result.is_transient is True
        assert RecoverySuggestion.RETRY_WITH_BACKOFF in result.recovery_suggestions

    @pytest.mark.asyncio
    async def test_analyze_timeout_error(self, analyzer):
        """Test analyzing a timeout error."""
        import asyncio
        error = asyncio.TimeoutError("Operation timed out")
        result = await analyzer.analyze(error)

        assert result.category == ErrorCategory.TIMEOUT
        assert result.is_transient is True

    @pytest.mark.asyncio
    async def test_analyze_auth_error(self, analyzer):
        """Test analyzing an authentication error."""
        error = PermissionError("401 Unauthorized")
        result = await analyzer.analyze(error)

        # Should match auth or permission pattern
        assert result.category in (ErrorCategory.AUTHENTICATION, ErrorCategory.AUTHORIZATION)

    @pytest.mark.asyncio
    async def test_analyze_import_error(self, analyzer):
        """Test analyzing an import error."""
        error = ModuleNotFoundError("No module named 'missing_module'")
        result = await analyzer.analyze(error)

        assert result.category == ErrorCategory.DEPENDENCY
        assert RecoverySuggestion.INSTALL_DEPENDENCY in result.recovery_suggestions

    @pytest.mark.asyncio
    async def test_analyze_unknown_error(self, analyzer):
        """Test analyzing an unknown error type."""
        class CustomError(Exception):
            pass

        error = CustomError("Some custom error")
        result = await analyzer.analyze(error)

        assert result.category == ErrorCategory.UNKNOWN
        assert result.confidence_score == 0.0

    @pytest.mark.asyncio
    async def test_error_hash_computation(self, analyzer):
        """Test that similar errors get same hash."""
        error1 = ValueError("Invalid value 123")
        error2 = ValueError("Invalid value 456")

        result1 = await analyzer.analyze(error1)
        result2 = await analyzer.analyze(error2)

        # Numbers should be normalized, so hashes should match
        assert result1.error_hash == result2.error_hash

    @pytest.mark.asyncio
    async def test_learning_enabled(self, analyzer):
        """Test error frequency tracking."""
        error = ValueError("Test error")

        await analyzer.analyze(error)
        await analyzer.analyze(error)

        stats = analyzer.get_statistics()
        assert stats["unique_errors_seen"] >= 1

    @pytest.mark.asyncio
    async def test_context_passing(self, analyzer):
        """Test context is passed to result."""
        error = ValueError("Test")
        context = {"task_id": "123", "user": "test"}

        result = await analyzer.analyze(error, context=context)
        assert result.additional_context == context

    def test_add_custom_pattern(self, analyzer):
        """Test adding custom error pattern."""
        pattern = ErrorPattern(
            pattern_id="custom",
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.HIGH,
            regex_patterns=[r"custom.*error"],
            keywords=["CustomError"],
            recovery_suggestions=[RecoverySuggestion.CHECK_CONFIGURATION],
            description="Custom pattern",
        )
        initial_count = len(analyzer.patterns)
        analyzer.add_pattern(pattern)
        assert len(analyzer.patterns) == initial_count + 1

    def test_clear_history(self, analyzer):
        """Test clearing error history."""
        analyzer._error_history["test"] = []
        analyzer.clear_history()
        assert len(analyzer._error_history) == 0


class TestSingleton:
    """Tests for singleton pattern."""

    def test_get_error_analyzer(self):
        """Test singleton getter."""
        reset_error_analyzer()
        analyzer1 = get_error_analyzer()
        analyzer2 = get_error_analyzer()
        assert analyzer1 is analyzer2

    def test_reset_error_analyzer(self):
        """Test singleton reset."""
        analyzer1 = get_error_analyzer()
        reset_error_analyzer()
        analyzer2 = get_error_analyzer()
        assert analyzer1 is not analyzer2
