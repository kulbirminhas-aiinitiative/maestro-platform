"""
Tests for ExternalGapAnalyzer

EPIC: MD-3022 - External Project Gap Analysis Scanner
"""
import pytest
import tempfile
import os
from pathlib import Path
from datetime import datetime

from maestro_hive.gap_analysis.external_scanner import (
    ExternalProjectScanner,
    ScanResult,
    ScanStatus,
    FileAnalysis,
    FileMetrics,
    ProjectMetrics,
    FileType,
)

from maestro_hive.gap_analysis.external_analyzer import (
    ExternalGapAnalyzer,
    AnalyzerConfig,
    GapAnalysisResult,
    Gap,
    GapSeverity,
    GapCategory,
    GapSuggestion,
    AnalysisScore,
    BestPracticesChecker,
    create_gap_analyzer,
)


class TestGapSeverity:
    """Tests for GapSeverity enum"""

    def test_severity_values(self):
        """Test severity enum values"""
        assert GapSeverity.CRITICAL.value == "critical"
        assert GapSeverity.HIGH.value == "high"
        assert GapSeverity.MEDIUM.value == "medium"
        assert GapSeverity.LOW.value == "low"
        assert GapSeverity.INFO.value == "info"


class TestGapCategory:
    """Tests for GapCategory enum"""

    def test_category_values(self):
        """Test category enum values"""
        assert GapCategory.SECURITY.value == "security"
        assert GapCategory.DOCUMENTATION.value == "documentation"
        assert GapCategory.TESTING.value == "testing"
        assert GapCategory.CODE_QUALITY.value == "code_quality"


class TestGapSuggestion:
    """Tests for GapSuggestion dataclass"""

    def test_suggestion_creation(self):
        """Test suggestion creation"""
        suggestion = GapSuggestion(
            description="Fix the issue",
            effort="low",
            priority=1,
        )
        assert suggestion.description == "Fix the issue"
        assert suggestion.effort == "low"
        assert suggestion.priority == 1


class TestGap:
    """Tests for Gap dataclass"""

    def test_gap_creation(self):
        """Test gap creation"""
        gap = Gap(
            gap_id="SEC-0001",
            category=GapCategory.SECURITY,
            severity=GapSeverity.HIGH,
            title="Security Issue",
            description="Found a security vulnerability",
        )
        assert gap.gap_id == "SEC-0001"
        assert gap.category == GapCategory.SECURITY
        assert gap.severity == GapSeverity.HIGH

    def test_gap_to_dict(self):
        """Test gap serialization"""
        gap = Gap(
            gap_id="TEST-0001",
            category=GapCategory.TESTING,
            severity=GapSeverity.MEDIUM,
            title="Missing Tests",
            description="No tests found",
            file_path="src/module.py",
            suggestions=[
                GapSuggestion(description="Add tests", effort="high", priority=1)
            ],
        )
        result = gap.to_dict()

        assert result["gap_id"] == "TEST-0001"
        assert result["category"] == "testing"
        assert result["severity"] == "medium"
        assert len(result["suggestions"]) == 1


class TestAnalyzerConfig:
    """Tests for AnalyzerConfig dataclass"""

    def test_default_config(self):
        """Test default analyzer configuration"""
        config = AnalyzerConfig()
        assert config.severity_threshold == GapSeverity.LOW
        assert config.include_suggestions is True
        assert config.max_suggestions_per_gap == 3
        assert config.min_test_coverage == 80.0

    def test_custom_config(self):
        """Test custom configuration"""
        config = AnalyzerConfig(
            severity_threshold=GapSeverity.MEDIUM,
            include_suggestions=False,
            max_suggestions_per_gap=5,
        )
        assert config.severity_threshold == GapSeverity.MEDIUM
        assert config.include_suggestions is False
        assert config.max_suggestions_per_gap == 5


class TestAnalysisScore:
    """Tests for AnalysisScore dataclass"""

    def test_default_scores(self):
        """Test default score values"""
        scores = AnalysisScore()
        assert scores.overall == 0.0
        assert scores.security == 0.0
        assert scores.testing == 0.0

    def test_to_dict(self):
        """Test score serialization"""
        scores = AnalysisScore(
            overall=85.0,
            security=90.0,
            documentation=70.0,
        )
        result = scores.to_dict()

        assert result["overall"] == 85.0
        assert result["security"] == 90.0
        assert result["documentation"] == 70.0


class TestGapAnalysisResult:
    """Tests for GapAnalysisResult dataclass"""

    def test_result_creation(self):
        """Test result creation"""
        scan_result = ScanResult(
            project_path="/test",
            project_name="test",
            status=ScanStatus.COMPLETED,
            scan_start=datetime.now(),
        )
        result = GapAnalysisResult(
            project_name="test",
            analysis_timestamp=datetime.now(),
            scan_result=scan_result,
        )
        assert result.project_name == "test"
        assert result.gaps == []

    def test_gaps_by_severity(self):
        """Test grouping gaps by severity"""
        scan_result = ScanResult(
            project_path="/test",
            project_name="test",
            status=ScanStatus.COMPLETED,
            scan_start=datetime.now(),
        )
        result = GapAnalysisResult(
            project_name="test",
            analysis_timestamp=datetime.now(),
            scan_result=scan_result,
            gaps=[
                Gap("G1", GapCategory.SECURITY, GapSeverity.HIGH, "H1", "D1"),
                Gap("G2", GapCategory.SECURITY, GapSeverity.HIGH, "H2", "D2"),
                Gap("G3", GapCategory.TESTING, GapSeverity.LOW, "L1", "D3"),
            ],
        )
        by_sev = result.gaps_by_severity

        assert len(by_sev["high"]) == 2
        assert len(by_sev["low"]) == 1

    def test_gaps_by_category(self):
        """Test grouping gaps by category"""
        scan_result = ScanResult(
            project_path="/test",
            project_name="test",
            status=ScanStatus.COMPLETED,
            scan_start=datetime.now(),
        )
        result = GapAnalysisResult(
            project_name="test",
            analysis_timestamp=datetime.now(),
            scan_result=scan_result,
            gaps=[
                Gap("G1", GapCategory.SECURITY, GapSeverity.HIGH, "H1", "D1"),
                Gap("G2", GapCategory.TESTING, GapSeverity.HIGH, "H2", "D2"),
                Gap("G3", GapCategory.TESTING, GapSeverity.LOW, "L1", "D3"),
            ],
        )
        by_cat = result.gaps_by_category

        assert len(by_cat["security"]) == 1
        assert len(by_cat["testing"]) == 2


class TestBestPracticesChecker:
    """Tests for BestPracticesChecker class"""

    def test_checker_creation(self):
        """Test checker instantiation"""
        checker = BestPracticesChecker()
        assert checker is not None

    def test_check_security_password(self):
        """Test security check for hardcoded passwords"""
        checker = BestPracticesChecker()
        content = 'password = "secret123"'
        gaps = checker.check_security(content, "test.py")

        assert len(gaps) >= 1
        assert gaps[0].category == GapCategory.SECURITY
        assert gaps[0].severity == GapSeverity.HIGH

    def test_check_security_api_key(self):
        """Test security check for hardcoded API keys"""
        checker = BestPracticesChecker()
        content = 'api_key = "sk-12345abcdef"'
        gaps = checker.check_security(content, "config.py")

        assert len(gaps) >= 1
        assert "API key" in gaps[0].title or "api" in gaps[0].title.lower()

    def test_check_security_eval(self):
        """Test security check for eval usage"""
        checker = BestPracticesChecker()
        content = 'result = eval(user_input)'
        gaps = checker.check_security(content, "dangerous.py")

        assert len(gaps) >= 1

    def test_check_code_quality_todo(self):
        """Test code quality check for TODOs"""
        checker = BestPracticesChecker()
        content = '# TODO: Fix this later'
        gaps = checker.check_code_quality(content, "test.py")

        assert len(gaps) >= 1
        assert gaps[0].category == GapCategory.CODE_QUALITY

    def test_check_code_quality_fixme(self):
        """Test code quality check for FIXMEs"""
        checker = BestPracticesChecker()
        content = '# FIXME: This is broken'
        gaps = checker.check_code_quality(content, "test.py")

        assert len(gaps) >= 1

    def test_no_gaps_for_clean_code(self):
        """Test no gaps for clean code"""
        checker = BestPracticesChecker()
        content = '''
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b
'''
        security_gaps = checker.check_security(content, "clean.py")
        quality_gaps = checker.check_code_quality(content, "clean.py")

        assert len(security_gaps) == 0
        assert len(quality_gaps) == 0


class TestExternalGapAnalyzer:
    """Tests for ExternalGapAnalyzer class"""

    def test_analyzer_creation(self):
        """Test analyzer instantiation"""
        analyzer = ExternalGapAnalyzer()
        assert analyzer.config is not None

    def test_analyzer_with_custom_config(self):
        """Test analyzer with custom configuration"""
        config = AnalyzerConfig(severity_threshold=GapSeverity.HIGH)
        analyzer = ExternalGapAnalyzer(config=config)
        assert analyzer.config.severity_threshold == GapSeverity.HIGH

    @pytest.mark.asyncio
    async def test_analyze_failed_scan(self):
        """Test analyzing a failed scan"""
        scan_result = ScanResult(
            project_path="/test",
            project_name="test",
            status=ScanStatus.FAILED,
            scan_start=datetime.now(),
            errors=["Scan failed"],
        )

        analyzer = ExternalGapAnalyzer()
        result = await analyzer.analyze(scan_result)

        assert result.project_name == "test"
        assert len(result.gaps) == 0

    @pytest.mark.asyncio
    async def test_analyze_empty_scan(self):
        """Test analyzing an empty scan result"""
        scan_result = ScanResult(
            project_path="/test",
            project_name="test",
            status=ScanStatus.COMPLETED,
            scan_start=datetime.now(),
            metrics=ProjectMetrics(),
        )

        analyzer = ExternalGapAnalyzer()
        result = await analyzer.analyze(scan_result)

        assert result.project_name == "test"
        assert result.scores is not None

    @pytest.mark.asyncio
    async def test_analyze_project_no_tests(self):
        """Test analyzing project without tests"""
        scan_result = ScanResult(
            project_path="/test",
            project_name="test",
            status=ScanStatus.COMPLETED,
            scan_start=datetime.now(),
            metrics=ProjectMetrics(has_tests=False),
        )

        analyzer = ExternalGapAnalyzer()
        result = await analyzer.analyze(scan_result)

        test_gaps = [g for g in result.gaps if g.category == GapCategory.TESTING]
        assert len(test_gaps) >= 1

    @pytest.mark.asyncio
    async def test_analyze_project_no_docs(self):
        """Test analyzing project without documentation"""
        scan_result = ScanResult(
            project_path="/test",
            project_name="test",
            status=ScanStatus.COMPLETED,
            scan_start=datetime.now(),
            metrics=ProjectMetrics(has_docs=False),
        )

        analyzer = ExternalGapAnalyzer()
        result = await analyzer.analyze(scan_result)

        doc_gaps = [g for g in result.gaps if g.category == GapCategory.DOCUMENTATION]
        assert len(doc_gaps) >= 1

    @pytest.mark.asyncio
    async def test_analyze_project_no_ci(self):
        """Test analyzing project without CI"""
        scan_result = ScanResult(
            project_path="/test",
            project_name="test",
            status=ScanStatus.COMPLETED,
            scan_start=datetime.now(),
            metrics=ProjectMetrics(has_ci=False),
        )

        analyzer = ExternalGapAnalyzer()
        result = await analyzer.analyze(scan_result)

        arch_gaps = [g for g in result.gaps if g.category == GapCategory.ARCHITECTURE]
        assert len(arch_gaps) >= 1

    @pytest.mark.asyncio
    async def test_analyze_with_security_issues(self):
        """Test analyzing files with security issues"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create file with security issue
            bad_file = Path(tmpdir) / "config.py"
            bad_file.write_text('password = "secret123"\napi_key = "key123"')

            scanner = ExternalProjectScanner()
            scan_result = await scanner.scan_project(tmpdir)

            analyzer = ExternalGapAnalyzer()
            result = await analyzer.analyze(scan_result)

            security_gaps = [g for g in result.gaps if g.category == GapCategory.SECURITY]
            assert len(security_gaps) >= 1

    @pytest.mark.asyncio
    async def test_severity_filtering(self):
        """Test that gaps are filtered by severity threshold"""
        scan_result = ScanResult(
            project_path="/test",
            project_name="test",
            status=ScanStatus.COMPLETED,
            scan_start=datetime.now(),
            metrics=ProjectMetrics(has_tests=False, has_docs=False, has_ci=False),
        )

        # With LOW threshold - see all gaps
        config_low = AnalyzerConfig(severity_threshold=GapSeverity.LOW)
        analyzer_low = ExternalGapAnalyzer(config=config_low)
        result_low = await analyzer_low.analyze(scan_result)

        # With HIGH threshold - filter out low/medium gaps
        config_high = AnalyzerConfig(severity_threshold=GapSeverity.HIGH)
        analyzer_high = ExternalGapAnalyzer(config=config_high)
        result_high = await analyzer_high.analyze(scan_result)

        # Should have fewer gaps with higher threshold
        assert len(result_high.gaps) <= len(result_low.gaps)

    @pytest.mark.asyncio
    async def test_suggestion_limiting(self):
        """Test that suggestions are limited per gap"""
        config = AnalyzerConfig(max_suggestions_per_gap=1)
        analyzer = ExternalGapAnalyzer(config=config)

        scan_result = ScanResult(
            project_path="/test",
            project_name="test",
            status=ScanStatus.COMPLETED,
            scan_start=datetime.now(),
            metrics=ProjectMetrics(has_tests=False),
        )

        result = await analyzer.analyze(scan_result)

        for gap in result.gaps:
            assert len(gap.suggestions) <= 1

    @pytest.mark.asyncio
    async def test_score_calculation(self):
        """Test score calculation"""
        scan_result = ScanResult(
            project_path="/test",
            project_name="test",
            status=ScanStatus.COMPLETED,
            scan_start=datetime.now(),
            metrics=ProjectMetrics(
                has_tests=True,
                has_docs=True,
                has_ci=True,
            ),
        )

        analyzer = ExternalGapAnalyzer()
        result = await analyzer.analyze(scan_result)

        assert result.scores is not None
        assert 0 <= result.scores.overall <= 100
        assert 0 <= result.scores.security <= 100

    @pytest.mark.asyncio
    async def test_recommendations_generated(self):
        """Test that recommendations are generated"""
        scan_result = ScanResult(
            project_path="/test",
            project_name="test",
            status=ScanStatus.COMPLETED,
            scan_start=datetime.now(),
            metrics=ProjectMetrics(has_tests=False),
        )

        analyzer = ExternalGapAnalyzer()
        result = await analyzer.analyze(scan_result)

        assert len(result.recommendations) > 0

    @pytest.mark.asyncio
    async def test_summary_generated(self):
        """Test that summary is generated"""
        scan_result = ScanResult(
            project_path="/test",
            project_name="test",
            status=ScanStatus.COMPLETED,
            scan_start=datetime.now(),
            metrics=ProjectMetrics(),
        )

        analyzer = ExternalGapAnalyzer()
        result = await analyzer.analyze(scan_result)

        assert "total_gaps" in result.summary
        assert "health_grade" in result.summary

    @pytest.mark.asyncio
    async def test_health_grade_calculation(self):
        """Test health grade calculation"""
        analyzer = ExternalGapAnalyzer()

        assert analyzer._calculate_grade(95) == "A"
        assert analyzer._calculate_grade(85) == "B"
        assert analyzer._calculate_grade(75) == "C"
        assert analyzer._calculate_grade(65) == "D"
        assert analyzer._calculate_grade(55) == "F"


class TestFactoryFunction:
    """Tests for factory functions"""

    def test_create_gap_analyzer(self):
        """Test analyzer factory function"""
        analyzer = create_gap_analyzer()
        assert isinstance(analyzer, ExternalGapAnalyzer)

    def test_create_gap_analyzer_with_config(self):
        """Test analyzer factory with config"""
        config = AnalyzerConfig(min_test_coverage=90.0)
        analyzer = create_gap_analyzer(config=config)
        assert analyzer.config.min_test_coverage == 90.0


class TestEndToEndAnalysis:
    """End-to-end integration tests"""

    @pytest.mark.asyncio
    async def test_full_analysis_workflow(self):
        """Test complete scan and analysis workflow"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a mini project
            src_dir = Path(tmpdir) / "src"
            src_dir.mkdir()

            # Main module
            (src_dir / "main.py").write_text('''
"""Main module."""
import os

def greet(name: str) -> str:
    """Greet someone."""
    return f"Hello, {name}!"

# TODO: Add more features
''')

            # Config with potential issue
            (src_dir / "config.py").write_text('''
"""Configuration."""
DEBUG = True
# FIXME: Remove hardcoded value
API_ENDPOINT = "https://api.example.com"
''')

            # README
            (Path(tmpdir) / "README.md").write_text("# Test Project")

            # Scan project
            scanner = ExternalProjectScanner()
            scan_result = await scanner.scan_project(tmpdir)

            assert scan_result.status == ScanStatus.COMPLETED

            # Analyze gaps
            analyzer = ExternalGapAnalyzer()
            analysis_result = await analyzer.analyze(scan_result)

            # Verify results
            assert analysis_result.project_name == Path(tmpdir).name
            assert analysis_result.scores is not None
            assert len(analysis_result.summary) > 0

            # Should detect TODO and FIXME
            code_quality_gaps = [
                g for g in analysis_result.gaps
                if g.category == GapCategory.CODE_QUALITY
            ]
            assert len(code_quality_gaps) >= 2

    @pytest.mark.asyncio
    async def test_clean_project_high_score(self):
        """Test that clean projects get high scores"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a clean project structure
            src_dir = Path(tmpdir) / "src"
            src_dir.mkdir()
            tests_dir = Path(tmpdir) / "tests"
            tests_dir.mkdir()
            docs_dir = Path(tmpdir) / "docs"
            docs_dir.mkdir()
            github_dir = Path(tmpdir) / ".github" / "workflows"
            github_dir.mkdir(parents=True)

            # Clean main module
            (src_dir / "main.py").write_text('''
"""Main module for the application."""
from typing import Optional


def process_data(data: Optional[str] = None) -> str:
    """Process the input data.

    Args:
        data: Input data string

    Returns:
        Processed data string
    """
    if data is None:
        return ""
    return data.strip().upper()
''')

            # Test file
            (tests_dir / "test_main.py").write_text('''
"""Tests for main module."""
import pytest


def test_process_data():
    """Test data processing."""
    assert True
''')

            # README
            (Path(tmpdir) / "README.md").write_text("# Clean Project")

            # CI config
            (github_dir / "ci.yml").write_text("name: CI")

            # Scan and analyze
            scanner = ExternalProjectScanner()
            scan_result = await scanner.scan_project(tmpdir)

            analyzer = ExternalGapAnalyzer()
            result = await analyzer.analyze(scan_result)

            # Clean project should have good scores
            assert result.scores.overall >= 70
            assert result.summary["health_grade"] in ["A", "B", "C"]
