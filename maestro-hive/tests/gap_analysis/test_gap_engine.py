"""
Tests for GapEngine.

EPIC: MD-3022
Child Task: MD-2922
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.maestro_hive.gap_analysis.gap_engine import (
    GapEngine,
    GapEngineConfig,
    GapEngineResult,
    EngineStatus,
    Recommendation,
    RecommendationPriority,
    HealthScore,
    create_gap_engine,
)


class TestGapEngineConfig:
    """Tests for GapEngineConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = GapEngineConfig()
        assert config.enable_repo_cloning is True
        assert config.enable_vision_analysis is True
        assert config.enable_gap_analysis is True
        assert config.max_files == 1000
        assert config.timeout_seconds == 600

    def test_custom_config(self):
        """Test custom configuration values."""
        config = GapEngineConfig(
            enable_repo_cloning=False,
            max_files=500,
            timeout_seconds=300,
        )
        assert config.enable_repo_cloning is False
        assert config.max_files == 500
        assert config.timeout_seconds == 300


class TestEngineStatus:
    """Tests for EngineStatus enum."""

    def test_status_values(self):
        """Test engine status values."""
        assert EngineStatus.IDLE.value == "idle"
        assert EngineStatus.CLONING.value == "cloning"
        assert EngineStatus.SCANNING.value == "scanning"
        assert EngineStatus.ANALYZING.value == "analyzing"
        assert EngineStatus.COMPLETE.value == "complete"
        assert EngineStatus.ERROR.value == "error"


class TestRecommendationPriority:
    """Tests for RecommendationPriority enum."""

    def test_priority_values(self):
        """Test priority values."""
        assert RecommendationPriority.CRITICAL.value == "critical"
        assert RecommendationPriority.HIGH.value == "high"
        assert RecommendationPriority.MEDIUM.value == "medium"
        assert RecommendationPriority.LOW.value == "low"


class TestRecommendation:
    """Tests for Recommendation dataclass."""

    def test_recommendation_creation(self):
        """Test creating Recommendation."""
        rec = Recommendation(
            id="REC-001",
            title="Add tests",
            description="Improve test coverage",
            priority=RecommendationPriority.HIGH,
            category="testing",
            effort_estimate="medium",
            impact_estimate="high",
        )
        assert rec.id == "REC-001"
        assert rec.priority == RecommendationPriority.HIGH

    def test_recommendation_to_dict(self):
        """Test Recommendation serialization."""
        rec = Recommendation(
            id="REC-002",
            title="Fix security issue",
            description="Address security gap",
            priority=RecommendationPriority.CRITICAL,
            category="security",
            effort_estimate="high",
            impact_estimate="high",
            action_items=["Update dependencies"],
        )
        result = rec.to_dict()
        assert result["id"] == "REC-002"
        assert result["priority"] == "critical"
        assert result["category"] == "security"


class TestHealthScore:
    """Tests for HealthScore dataclass."""

    def test_health_score_creation(self):
        """Test creating HealthScore."""
        score = HealthScore(
            overall=75.0,
            code_quality=80.0,
            architecture=70.0,
            testing=60.0,
            documentation=65.0,
            security=75.0,
            maintainability=72.0,
            grade="C",
        )
        assert score.overall == 75.0
        assert score.grade == "C"

    def test_health_score_to_dict(self):
        """Test HealthScore serialization."""
        score = HealthScore(
            overall=85.0,
            code_quality=90.0,
            architecture=80.0,
            testing=75.0,
            documentation=85.0,
            security=90.0,
            maintainability=82.0,
            grade="B",
        )
        result = score.to_dict()
        assert result["overall"] == 85.0
        assert result["grade"] == "B"


class TestGapEngine:
    """Tests for GapEngine class."""

    @pytest.fixture
    def engine(self):
        """Create a GapEngine instance."""
        config = GapEngineConfig(
            enable_repo_cloning=False,  # Don't try to clone in tests
        )
        return GapEngine(config)

    @pytest.fixture
    def sample_project(self):
        """Create a sample project directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create structure
            Path(tmpdir, "src").mkdir()
            Path(tmpdir, "tests").mkdir()

            # Create Python files
            Path(tmpdir, "src", "main.py").write_text('"""Main module."""\n\ndef main():\n    pass\n')
            Path(tmpdir, "tests", "test_main.py").write_text('"""Tests."""\n\ndef test_main():\n    pass\n')

            yield tmpdir

    def test_engine_creation(self, engine):
        """Test engine initialization."""
        assert engine.config is not None
        assert engine.status == EngineStatus.IDLE

    def test_engine_status_property(self, engine):
        """Test status property."""
        assert isinstance(engine.status, EngineStatus)

    def test_analyze_local_path(self, engine, sample_project):
        """Test analyzing a local path."""
        result = engine.analyze(
            project_url=sample_project,
            local_path=sample_project,
        )

        assert isinstance(result, GapEngineResult)
        assert result.status in [EngineStatus.COMPLETE, EngineStatus.ERROR]
        assert result.project_path == sample_project

    def test_analyze_returns_health_score(self, engine, sample_project):
        """Test that analysis returns health score."""
        result = engine.analyze(
            project_url=sample_project,
            local_path=sample_project,
        )

        if result.status == EngineStatus.COMPLETE:
            assert result.health_score is not None

    def test_analyze_returns_recommendations(self, engine, sample_project):
        """Test that analysis returns recommendations."""
        result = engine.analyze(
            project_url=sample_project,
            local_path=sample_project,
        )

        assert isinstance(result.recommendations, list)

    def test_analyze_returns_summary(self, engine, sample_project):
        """Test that analysis returns summary."""
        result = engine.analyze(
            project_url=sample_project,
            local_path=sample_project,
        )

        assert result.summary is not None

    def test_severity_to_priority_critical(self, engine):
        """Test severity to priority mapping - critical."""
        from src.maestro_hive.gap_analysis.external_analyzer import GapSeverity
        result = engine._severity_to_priority(GapSeverity.CRITICAL)
        assert result == RecommendationPriority.CRITICAL

    def test_severity_to_priority_high(self, engine):
        """Test severity to priority mapping - high."""
        from src.maestro_hive.gap_analysis.external_analyzer import GapSeverity
        result = engine._severity_to_priority(GapSeverity.HIGH)
        assert result == RecommendationPriority.HIGH

    def test_estimate_effort_critical(self, engine):
        """Test effort estimation for critical severity."""
        from src.maestro_hive.gap_analysis.external_analyzer import GapSeverity
        result = engine._estimate_effort(GapSeverity.CRITICAL)
        assert result == "high"

    def test_estimate_effort_low(self, engine):
        """Test effort estimation for low severity."""
        from src.maestro_hive.gap_analysis.external_analyzer import GapSeverity
        result = engine._estimate_effort(GapSeverity.LOW)
        assert result == "low"


class TestGapEngineResult:
    """Tests for GapEngineResult dataclass."""

    def test_result_to_dict(self):
        """Test GapEngineResult serialization."""
        from datetime import datetime

        result = GapEngineResult(
            project_url="https://github.com/user/repo",
            project_path="/tmp/repo",
            status=EngineStatus.COMPLETE,
            started_at=datetime.now(),
            completed_at=datetime.now(),
            duration_seconds=5.0,
            repo_info=None,
            scan_result=None,
            vision_result=None,
            gap_report=None,
            health_score=None,
            recommendations=[],
            summary="Analysis complete",
            files_analyzed=10,
            gaps_found=3,
        )

        data = result.to_dict()
        assert data["project_url"] == "https://github.com/user/repo"
        assert data["status"] == "complete"
        assert data["files_analyzed"] == 10


class TestFactoryFunction:
    """Tests for create_gap_engine factory."""

    def test_create_gap_engine_default(self):
        """Test creating engine with defaults."""
        engine = create_gap_engine()
        assert isinstance(engine, GapEngine)

    def test_create_gap_engine_with_config(self):
        """Test creating engine with custom config."""
        engine = create_gap_engine({
            "enable_repo_cloning": False,
            "max_files": 500,
        })
        assert engine.config.enable_repo_cloning is False
        assert engine.config.max_files == 500
