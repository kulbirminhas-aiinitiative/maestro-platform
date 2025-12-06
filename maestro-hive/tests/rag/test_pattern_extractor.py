"""
Tests for Pattern Extractor.

EPIC: MD-2499
AC-3: Extract success/failure patterns
"""

import pytest
from datetime import datetime

from maestro_hive.rag import (
    PatternExtractor,
    RetrievalResult,
    ExecutionRecord,
    ExecutionOutcome,
    SuccessPattern,
    FailurePattern,
    PatternSummary,
)
from maestro_hive.rag.models import PhaseResult


class TestPatternExtractor:
    """Test PatternExtractor functionality."""

    @pytest.fixture
    def extractor(self) -> PatternExtractor:
        """Create a pattern extractor."""
        return PatternExtractor(min_confidence=0.3, max_patterns=10)

    @pytest.fixture
    def success_results(self) -> list[RetrievalResult]:
        """Create sample successful execution results."""
        results = []
        for i in range(5):
            record = ExecutionRecord(
                execution_id=f"success-{i:03d}",
                requirement_text=f"Build REST API version {i}",
                outcome=ExecutionOutcome.SUCCESS,
                timestamp=datetime.utcnow(),
                duration_seconds=1000.0 + i * 100,
                phase_results={
                    "design": PhaseResult(
                        phase_name="design",
                        status="passed",
                        score=0.95,
                        duration_seconds=100.0,
                    ),
                    "implementation": PhaseResult(
                        phase_name="implementation",
                        status="passed",
                        score=0.90,
                        duration_seconds=500.0,
                    ),
                    "testing": PhaseResult(
                        phase_name="testing",
                        status="passed",
                        score=0.85,
                        duration_seconds=200.0,
                    ),
                },
                metadata={"type": "api", "language": "python"},
            )
            results.append(RetrievalResult(
                execution=record,
                similarity_score=0.9 - i * 0.05,
            ))
        return results

    @pytest.fixture
    def failure_results(self) -> list[RetrievalResult]:
        """Create sample failed execution results."""
        results = []
        for i in range(3):
            record = ExecutionRecord(
                execution_id=f"failure-{i:03d}",
                requirement_text=f"Failed execution {i}",
                outcome=ExecutionOutcome.FAILURE,
                timestamp=datetime.utcnow(),
                duration_seconds=500.0,
                phase_results={
                    "design": PhaseResult(
                        phase_name="design",
                        status="passed",
                        score=0.80,
                        duration_seconds=100.0,
                    ),
                    "implementation": PhaseResult(
                        phase_name="implementation",
                        status="failed",
                        score=0.0,
                        duration_seconds=200.0,
                        error_message="Build failed: timeout exceeded",
                    ),
                    "testing": PhaseResult(
                        phase_name="testing",
                        status="skipped",
                    ),
                },
                metadata={"type": "api"},
            )
            results.append(RetrievalResult(
                execution=record,
                similarity_score=0.7 - i * 0.1,
            ))
        return results

    @pytest.fixture
    def mixed_results(
        self,
        success_results: list[RetrievalResult],
        failure_results: list[RetrievalResult],
    ) -> list[RetrievalResult]:
        """Create mixed success/failure results."""
        return success_results + failure_results

    def test_extractor_initialization(self, extractor: PatternExtractor):
        """Test extractor initializes correctly."""
        assert extractor.min_confidence == 0.3
        assert extractor.max_patterns == 10

    def test_extract_patterns_empty_input(self, extractor: PatternExtractor):
        """Test extraction with empty input."""
        summary = extractor.extract_patterns([])

        assert isinstance(summary, PatternSummary)
        assert len(summary.success_patterns) == 0
        assert len(summary.failure_patterns) == 0
        assert summary.total_executions_analyzed == 0
        assert summary.confidence_score == 0.0

    def test_extract_patterns_success_only(
        self,
        extractor: PatternExtractor,
        success_results: list[RetrievalResult],
    ):
        """Test extraction from only successful executions."""
        summary = extractor.extract_patterns(success_results)

        assert summary.total_executions_analyzed == 5
        assert len(summary.success_patterns) > 0
        assert len(summary.failure_patterns) == 0

    def test_extract_patterns_failure_only(
        self,
        extractor: PatternExtractor,
        failure_results: list[RetrievalResult],
    ):
        """Test extraction from only failed executions."""
        summary = extractor.extract_patterns(failure_results)

        assert summary.total_executions_analyzed == 3
        assert len(summary.failure_patterns) > 0

    def test_extract_patterns_mixed(
        self,
        extractor: PatternExtractor,
        mixed_results: list[RetrievalResult],
    ):
        """Test extraction from mixed results."""
        summary = extractor.extract_patterns(mixed_results)

        assert summary.total_executions_analyzed == 8
        assert len(summary.success_patterns) > 0
        assert len(summary.failure_patterns) > 0

    def test_success_pattern_structure(
        self,
        extractor: PatternExtractor,
        success_results: list[RetrievalResult],
    ):
        """Test success pattern has correct structure."""
        summary = extractor.extract_patterns(success_results)

        for pattern in summary.success_patterns:
            assert isinstance(pattern, SuccessPattern)
            assert pattern.pattern_id is not None
            assert pattern.description is not None
            assert pattern.frequency > 0
            assert 0 <= pattern.confidence <= 1

    def test_failure_pattern_structure(
        self,
        extractor: PatternExtractor,
        failure_results: list[RetrievalResult],
    ):
        """Test failure pattern has correct structure."""
        summary = extractor.extract_patterns(failure_results)

        for pattern in summary.failure_patterns:
            assert isinstance(pattern, FailurePattern)
            assert pattern.pattern_id is not None
            assert pattern.description is not None
            assert pattern.failure_type is not None
            assert pattern.frequency > 0
            assert 0 <= pattern.confidence <= 1

    def test_get_success_patterns_filters_by_confidence(
        self,
        extractor: PatternExtractor,
        success_results: list[RetrievalResult],
    ):
        """Test get_success_patterns filters by confidence."""
        patterns = extractor.get_success_patterns(success_results, min_confidence=0.8)

        for pattern in patterns:
            assert pattern.confidence >= 0.8

    def test_get_failure_patterns_filters_by_confidence(
        self,
        extractor: PatternExtractor,
        failure_results: list[RetrievalResult],
    ):
        """Test get_failure_patterns filters by confidence."""
        patterns = extractor.get_failure_patterns(failure_results, min_confidence=0.5)

        for pattern in patterns:
            assert pattern.confidence >= 0.5

    def test_max_patterns_limit(self):
        """Test max_patterns limits output."""
        extractor = PatternExtractor(min_confidence=0.0, max_patterns=2)

        # Create many results
        results = []
        for i in range(20):
            record = ExecutionRecord(
                execution_id=f"exec-{i}",
                requirement_text=f"Execution {i}",
                outcome=ExecutionOutcome.SUCCESS,
                timestamp=datetime.utcnow(),
                phase_results={
                    f"phase_{j}": PhaseResult(
                        phase_name=f"phase_{j}",
                        status="passed",
                    )
                    for j in range(5)
                },
            )
            results.append(RetrievalResult(execution=record, similarity_score=0.5))

        summary = extractor.extract_patterns(results)

        assert len(summary.success_patterns) <= 2


class TestFailureClassification:
    """Test failure type classification."""

    @pytest.fixture
    def extractor(self) -> PatternExtractor:
        return PatternExtractor()

    def test_classify_timeout(self, extractor: PatternExtractor):
        """Test timeout classification."""
        result = extractor._classify_failure_type(["Operation timeout exceeded"])
        assert result == "timeout"

    def test_classify_network_error(self, extractor: PatternExtractor):
        """Test network error classification."""
        result = extractor._classify_failure_type(["Connection refused"])
        assert result == "network_error"

    def test_classify_permission_error(self, extractor: PatternExtractor):
        """Test permission error classification."""
        result = extractor._classify_failure_type(["Permission denied"])
        assert result == "permission_error"

    def test_classify_resource_not_found(self, extractor: PatternExtractor):
        """Test resource not found classification."""
        result = extractor._classify_failure_type(["File not found"])
        assert result == "resource_not_found"

    def test_classify_test_failure(self, extractor: PatternExtractor):
        """Test test failure classification."""
        result = extractor._classify_failure_type(["Test assertion failed"])
        assert result == "test_failure"

    def test_classify_build_error(self, extractor: PatternExtractor):
        """Test build error classification."""
        result = extractor._classify_failure_type(["Build compilation failed"])
        assert result == "build_error"

    def test_classify_unknown(self, extractor: PatternExtractor):
        """Test unknown classification."""
        result = extractor._classify_failure_type(["Some random error"])
        assert result == "unknown"


class TestMitigationSuggestions:
    """Test mitigation suggestions."""

    @pytest.fixture
    def extractor(self) -> PatternExtractor:
        return PatternExtractor()

    def test_mitigation_for_timeout(self, extractor: PatternExtractor):
        """Test mitigation for timeout."""
        mitigation = extractor._suggest_mitigation("timeout", "build", [])
        assert "timeout" in mitigation.lower()

    def test_mitigation_for_permission(self, extractor: PatternExtractor):
        """Test mitigation for permission error."""
        mitigation = extractor._suggest_mitigation("permission_error", "deploy", [])
        assert "permission" in mitigation.lower() or "credential" in mitigation.lower()

    def test_mitigation_for_test_failure(self, extractor: PatternExtractor):
        """Test mitigation for test failure."""
        mitigation = extractor._suggest_mitigation("test_failure", "test", [])
        assert "test" in mitigation.lower()


class TestConfidenceCalculation:
    """Test confidence score calculation."""

    @pytest.fixture
    def extractor(self) -> PatternExtractor:
        return PatternExtractor()

    def test_confidence_empty_results(self, extractor: PatternExtractor):
        """Test confidence with empty results."""
        confidence = extractor._calculate_confidence([])
        assert confidence == 0.0

    def test_confidence_high_similarity_results(self, extractor: PatternExtractor):
        """Test confidence with high similarity results."""
        results = [
            RetrievalResult(
                execution=ExecutionRecord(
                    execution_id=f"exec-{i}",
                    requirement_text="Test",
                    outcome=ExecutionOutcome.SUCCESS,
                    timestamp=datetime.utcnow(),
                ),
                similarity_score=0.95,
            )
            for i in range(10)
        ]

        confidence = extractor._calculate_confidence(results)
        assert confidence > 0.8

    def test_confidence_low_similarity_results(self, extractor: PatternExtractor):
        """Test confidence with low similarity results."""
        results = [
            RetrievalResult(
                execution=ExecutionRecord(
                    execution_id=f"exec-{i}",
                    requirement_text="Test",
                    outcome=ExecutionOutcome.SUCCESS,
                    timestamp=datetime.utcnow(),
                ),
                similarity_score=0.3,
            )
            for i in range(3)
        ]

        confidence = extractor._calculate_confidence(results)
        assert confidence < 0.5
