"""
Tests for VisionAnalyzer.

EPIC: MD-3022
Child Task: MD-2921
"""

import tempfile
from pathlib import Path

import pytest

from src.maestro_hive.gap_analysis.vision_analyzer import (
    VisionAnalyzer,
    VisionConfig,
    VisionAnalysisResult,
    PatternMatch,
    CodePattern,
    CodeQuality,
    QualityIndicator,
    ArchitectureAnalysis,
    ArchitectureStyle,
    create_vision_analyzer,
)


class TestVisionConfig:
    """Tests for VisionConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = VisionConfig()
        assert config.max_files == 500
        assert config.analyze_patterns is True
        assert config.analyze_quality is True
        assert config.analyze_architecture is True
        assert ".py" in config.file_extensions

    def test_custom_config(self):
        """Test custom configuration values."""
        config = VisionConfig(
            max_files=100,
            analyze_patterns=False,
            min_confidence=0.8,
        )
        assert config.max_files == 100
        assert config.analyze_patterns is False
        assert config.min_confidence == 0.8


class TestCodePattern:
    """Tests for CodePattern enum."""

    def test_pattern_values(self):
        """Test pattern enum values."""
        assert CodePattern.MVC.value == "mvc"
        assert CodePattern.REPOSITORY.value == "repository"
        assert CodePattern.SERVICE_LAYER.value == "service_layer"


class TestCodeQuality:
    """Tests for CodeQuality enum."""

    def test_quality_values(self):
        """Test quality enum values."""
        assert CodeQuality.EXCELLENT.value == "excellent"
        assert CodeQuality.GOOD.value == "good"
        assert CodeQuality.POOR.value == "poor"


class TestPatternMatch:
    """Tests for PatternMatch dataclass."""

    def test_pattern_match_creation(self):
        """Test creating PatternMatch."""
        match = PatternMatch(
            pattern=CodePattern.MVC,
            confidence=0.85,
            locations=["controllers/", "views/"],
        )
        assert match.pattern == CodePattern.MVC
        assert match.confidence == 0.85
        assert len(match.locations) == 2

    def test_pattern_match_to_dict(self):
        """Test PatternMatch serialization."""
        match = PatternMatch(
            pattern=CodePattern.REPOSITORY,
            confidence=0.75,
            evidence=["Repository class found"],
        )
        result = match.to_dict()
        assert result["pattern"] == "repository"
        assert result["confidence"] == 0.75


class TestQualityIndicator:
    """Tests for QualityIndicator dataclass."""

    def test_quality_indicator_creation(self):
        """Test creating QualityIndicator."""
        indicator = QualityIndicator(
            name="Documentation",
            score=75.0,
            description="Documentation coverage",
        )
        assert indicator.name == "Documentation"
        assert indicator.score == 75.0

    def test_quality_indicator_to_dict(self):
        """Test QualityIndicator serialization."""
        indicator = QualityIndicator(
            name="Testing",
            score=60.0,
            description="Test coverage",
            recommendations=["Add more tests"],
        )
        result = indicator.to_dict()
        assert result["name"] == "Testing"
        assert result["score"] == 60.0
        assert len(result["recommendations"]) == 1


class TestArchitectureAnalysis:
    """Tests for ArchitectureAnalysis dataclass."""

    def test_architecture_analysis_creation(self):
        """Test creating ArchitectureAnalysis."""
        analysis = ArchitectureAnalysis(
            primary_style=ArchitectureStyle.LAYERED,
            confidence=0.8,
            detected_layers=["presentation", "business", "data"],
            coupling_score=70.0,
            cohesion_score=75.0,
            modularity_score=80.0,
        )
        assert analysis.primary_style == ArchitectureStyle.LAYERED
        assert len(analysis.detected_layers) == 3

    def test_architecture_analysis_to_dict(self):
        """Test ArchitectureAnalysis serialization."""
        analysis = ArchitectureAnalysis(
            primary_style=ArchitectureStyle.HEXAGONAL,
            confidence=0.7,
            detected_layers=["domain"],
            coupling_score=80.0,
            cohesion_score=85.0,
            modularity_score=75.0,
        )
        result = analysis.to_dict()
        assert result["primary_style"] == "hexagonal"
        assert result["coupling_score"] == 80.0


class TestVisionAnalyzer:
    """Tests for VisionAnalyzer class."""

    @pytest.fixture
    def analyzer(self):
        """Create a VisionAnalyzer instance."""
        return VisionAnalyzer()

    @pytest.fixture
    def sample_project(self):
        """Create a sample project directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create structure
            Path(tmpdir, "src").mkdir()
            Path(tmpdir, "tests").mkdir()
            Path(tmpdir, "services").mkdir()

            # Create Python files
            Path(tmpdir, "src", "main.py").write_text('"""Main module."""\n\ndef main():\n    pass\n')
            Path(tmpdir, "src", "service.py").write_text('"""Service module."""\n\nclass Service:\n    def process(self):\n        pass\n')
            Path(tmpdir, "tests", "test_main.py").write_text('"""Tests."""\n\ndef test_main():\n    pass\n')

            yield tmpdir

    def test_analyzer_creation(self, analyzer):
        """Test analyzer initialization."""
        assert analyzer.config is not None

    def test_analyze_nonexistent_path(self, analyzer):
        """Test analyzing nonexistent path."""
        with pytest.raises(ValueError):
            analyzer.analyze("/nonexistent/path/12345")

    def test_analyze_sample_project(self, analyzer, sample_project):
        """Test analyzing a sample project."""
        result = analyzer.analyze(sample_project)

        assert isinstance(result, VisionAnalysisResult)
        assert result.project_path == sample_project
        assert result.analyzed_files > 0
        assert result.overall_score >= 0

    def test_analyze_returns_patterns(self, analyzer, sample_project):
        """Test that analysis returns patterns."""
        result = analyzer.analyze(sample_project)
        # Patterns may or may not be found depending on structure
        assert isinstance(result.patterns, list)

    def test_analyze_returns_quality_indicators(self, analyzer, sample_project):
        """Test that analysis returns quality indicators."""
        result = analyzer.analyze(sample_project)
        assert len(result.quality_indicators) > 0

    def test_analyze_returns_architecture(self, analyzer, sample_project):
        """Test that analysis returns architecture analysis."""
        result = analyzer.analyze(sample_project)
        assert result.architecture is not None

    def test_analyze_returns_insights(self, analyzer, sample_project):
        """Test that analysis returns insights."""
        result = analyzer.analyze(sample_project)
        assert isinstance(result.insights, list)

    def test_score_to_quality_excellent(self, analyzer):
        """Test score to quality mapping - excellent."""
        assert analyzer._score_to_quality(95) == CodeQuality.EXCELLENT

    def test_score_to_quality_good(self, analyzer):
        """Test score to quality mapping - good."""
        assert analyzer._score_to_quality(80) == CodeQuality.GOOD

    def test_score_to_quality_acceptable(self, analyzer):
        """Test score to quality mapping - acceptable."""
        assert analyzer._score_to_quality(65) == CodeQuality.ACCEPTABLE

    def test_score_to_quality_needs_improvement(self, analyzer):
        """Test score to quality mapping - needs improvement."""
        assert analyzer._score_to_quality(45) == CodeQuality.NEEDS_IMPROVEMENT

    def test_score_to_quality_poor(self, analyzer):
        """Test score to quality mapping - poor."""
        assert analyzer._score_to_quality(30) == CodeQuality.POOR


class TestVisionAnalysisResult:
    """Tests for VisionAnalysisResult dataclass."""

    def test_result_to_dict(self):
        """Test VisionAnalysisResult serialization."""
        result = VisionAnalysisResult(
            project_path="/test/project",
            patterns=[],
            quality_indicators=[],
            architecture=None,
            overall_quality=CodeQuality.GOOD,
            overall_score=75.0,
            insights=["Good code quality"],
            analyzed_files=10,
            analysis_time_seconds=1.5,
        )
        data = result.to_dict()
        assert data["project_path"] == "/test/project"
        assert data["overall_quality"] == "good"
        assert data["overall_score"] == 75.0


class TestFactoryFunction:
    """Tests for create_vision_analyzer factory."""

    def test_create_vision_analyzer_default(self):
        """Test creating analyzer with defaults."""
        analyzer = create_vision_analyzer()
        assert isinstance(analyzer, VisionAnalyzer)

    def test_create_vision_analyzer_with_config(self):
        """Test creating analyzer with custom config."""
        analyzer = create_vision_analyzer({
            "max_files": 200,
            "analyze_patterns": False,
        })
        assert analyzer.config.max_files == 200
        assert analyzer.config.analyze_patterns is False
