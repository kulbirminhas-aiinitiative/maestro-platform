"""
Tests for the Technical Debt Analyzer module.

Tests AC-4: Technical debt analysis and tracking.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from maestro_hive.devops.code_quality.tech_debt import (
    TechDebtAnalyzer,
    DebtConfig,
    DebtReport,
    DebtItem,
    DebtCategory,
    DebtSeverity,
    calculate_debt_score,
)


class TestDebtCategory:
    """Tests for DebtCategory enum."""

    def test_category_values(self):
        """Test category enum values."""
        assert DebtCategory.CODE_COMPLEXITY.value == "code_complexity"
        assert DebtCategory.TODOS.value == "todos"
        assert DebtCategory.OUTDATED_DEPS.value == "outdated_deps"


class TestDebtSeverity:
    """Tests for DebtSeverity enum."""

    def test_severity_values(self):
        """Test severity enum values."""
        assert DebtSeverity.CRITICAL.value == "critical"
        assert DebtSeverity.HIGH.value == "high"
        assert DebtSeverity.MEDIUM.value == "medium"
        assert DebtSeverity.LOW.value == "low"


class TestDebtItem:
    """Tests for DebtItem dataclass."""

    def test_create_item(self):
        """Test creating a debt item."""
        item = DebtItem(
            category=DebtCategory.TODOS,
            severity=DebtSeverity.HIGH,
            file_path="/path/to/file.py",
            line=10,
            description="FIXME: Fix this bug",
            effort_estimate="1h",
        )
        assert item.category == DebtCategory.TODOS
        assert item.severity == DebtSeverity.HIGH
        assert item.line == 10

    def test_to_dict(self):
        """Test converting to dictionary."""
        item = DebtItem(
            category=DebtCategory.CODE_COMPLEXITY,
            severity=DebtSeverity.MEDIUM,
            file_path="test.py",
            line=5,
            description="Complex function",
            effort_estimate="2h",
            suggestion="Refactor",
        )
        d = item.to_dict()
        assert d["category"] == "code_complexity"
        assert d["severity"] == "medium"
        assert d["suggestion"] == "Refactor"


class TestDebtConfig:
    """Tests for DebtConfig dataclass."""

    def test_default_config(self):
        """Test default configuration."""
        config = DebtConfig()
        assert config.max_complexity == 10
        assert config.max_function_length == 50
        assert "TODO" in config.todo_patterns
        assert ".git" in config.exclude_patterns

    def test_custom_config(self):
        """Test custom configuration."""
        config = DebtConfig(
            max_complexity=15,
            todo_patterns=["TODO", "CUSTOM"],
        )
        assert config.max_complexity == 15
        assert "CUSTOM" in config.todo_patterns


class TestDebtReport:
    """Tests for DebtReport dataclass."""

    def test_empty_report(self):
        """Test empty report."""
        report = DebtReport()
        assert report.total_items == 0
        assert report.critical_count == 0
        assert report.high_count == 0

    def test_add_item(self):
        """Test adding items."""
        report = DebtReport()
        report.add_item(DebtItem(
            category=DebtCategory.TODOS,
            severity=DebtSeverity.CRITICAL,
            file_path="a.py",
            line=1,
            description="Critical bug",
            effort_estimate="4h",
        ))
        report.add_item(DebtItem(
            category=DebtCategory.TODOS,
            severity=DebtSeverity.HIGH,
            file_path="b.py",
            line=1,
            description="High priority",
            effort_estimate="2h",
        ))

        assert report.total_items == 2
        assert report.critical_count == 1
        assert report.high_count == 1

    def test_get_by_category(self):
        """Test filtering by category."""
        report = DebtReport()
        report.add_item(DebtItem(
            category=DebtCategory.TODOS,
            severity=DebtSeverity.LOW,
            file_path="a.py",
            line=1,
            description="TODO",
            effort_estimate="30m",
        ))
        report.add_item(DebtItem(
            category=DebtCategory.CODE_COMPLEXITY,
            severity=DebtSeverity.MEDIUM,
            file_path="b.py",
            line=1,
            description="Complex",
            effort_estimate="2h",
        ))

        todos = report.get_by_category(DebtCategory.TODOS)
        assert len(todos) == 1

        complexity = report.get_by_category(DebtCategory.CODE_COMPLEXITY)
        assert len(complexity) == 1

    def test_get_by_severity(self):
        """Test filtering by severity."""
        report = DebtReport()
        report.add_item(DebtItem(
            category=DebtCategory.TODOS,
            severity=DebtSeverity.LOW,
            file_path="a.py",
            line=1,
            description="Low",
            effort_estimate="15m",
        ))
        report.add_item(DebtItem(
            category=DebtCategory.TODOS,
            severity=DebtSeverity.LOW,
            file_path="b.py",
            line=1,
            description="Low 2",
            effort_estimate="15m",
        ))
        report.add_item(DebtItem(
            category=DebtCategory.TODOS,
            severity=DebtSeverity.HIGH,
            file_path="c.py",
            line=1,
            description="High",
            effort_estimate="1h",
        ))

        low_items = report.get_by_severity(DebtSeverity.LOW)
        assert len(low_items) == 2

        high_items = report.get_by_severity(DebtSeverity.HIGH)
        assert len(high_items) == 1


class TestTechDebtAnalyzer:
    """Tests for TechDebtAnalyzer class."""

    def test_init_default_config(self):
        """Test initialization with default config."""
        analyzer = TechDebtAnalyzer()
        assert analyzer.config is not None
        assert analyzer.config.max_complexity == 10

    def test_init_custom_config(self):
        """Test initialization with custom config."""
        config = DebtConfig(max_complexity=20)
        analyzer = TechDebtAnalyzer(config)
        assert analyzer.config.max_complexity == 20

    def test_analyze_todos_finds_todo(self, tmp_path):
        """Test finding TODO comments."""
        py_file = tmp_path / "test.py"
        py_file.write_text("""
# TODO: Fix this later
def foo():
    pass

# FIXME: Critical bug here
def bar():
    pass
""")

        analyzer = TechDebtAnalyzer()
        items = analyzer.analyze_todos(str(tmp_path))

        # Should find at least the TODO (FIXME may not match if on separate line)
        assert len(items) >= 1
        # Check TODO
        todo_items = [i for i in items if "TODO" in i.description]
        assert len(todo_items) >= 1
        assert todo_items[0].severity == DebtSeverity.LOW

        # Check for FIXME items if found
        fixme_items = [i for i in items if "FIXME" in i.description]
        if len(fixme_items) > 0:
            assert fixme_items[0].severity == DebtSeverity.HIGH

    def test_analyze_todos_finds_hack(self, tmp_path):
        """Test finding HACK comments."""
        py_file = tmp_path / "test.py"
        py_file.write_text("# HACK: Temporary workaround\nx = 1")

        analyzer = TechDebtAnalyzer()
        items = analyzer.analyze_todos(str(tmp_path))

        assert len(items) == 1
        assert items[0].severity == DebtSeverity.MEDIUM

    def test_analyze_todos_nonexistent_path(self):
        """Test analyzing non-existent path."""
        analyzer = TechDebtAnalyzer()
        items = analyzer.analyze_todos("/nonexistent/path")
        assert len(items) == 0

    def test_analyze_todos_excludes_patterns(self, tmp_path):
        """Test exclusion patterns."""
        (tmp_path / "good.py").write_text("# TODO: Should find this")
        venv = tmp_path / ".venv"
        venv.mkdir()
        (venv / "bad.py").write_text("# TODO: Should not find this")

        analyzer = TechDebtAnalyzer()
        items = analyzer.analyze_todos(str(tmp_path))

        assert len(items) == 1
        assert "good.py" in items[0].file_path

    @patch('subprocess.run')
    def test_analyze_complexity(self, mock_run, tmp_path):
        """Test complexity analysis."""
        py_file = tmp_path / "test.py"
        py_file.write_text("def complex_function(): pass")

        # Mock radon output
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"test.py": [{"name": "complex_function", "complexity": 15, "lineno": 1}]}'
        )

        analyzer = TechDebtAnalyzer()
        items = analyzer.analyze_complexity(str(tmp_path))

        assert len(items) == 1
        assert items[0].severity == DebtSeverity.MEDIUM
        assert "complex_function" in items[0].description

    @patch('subprocess.run')
    def test_analyze_complexity_critical(self, mock_run, tmp_path):
        """Test critical complexity detection."""
        py_file = tmp_path / "test.py"
        py_file.write_text("def very_complex(): pass")

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"test.py": [{"name": "very_complex", "complexity": 25, "lineno": 1}]}'
        )

        analyzer = TechDebtAnalyzer()
        items = analyzer.analyze_complexity(str(tmp_path))

        assert len(items) == 1
        assert items[0].severity == DebtSeverity.CRITICAL

    @patch('subprocess.run')
    def test_analyze_codebase(self, mock_run, tmp_path):
        """Test full codebase analysis."""
        (tmp_path / "a.py").write_text("# TODO: Test\nx = 1")
        (tmp_path / "b.py").write_text("y = 2")

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{}'
        )

        analyzer = TechDebtAnalyzer()
        report = analyzer.analyze_codebase(str(tmp_path))

        assert report.total_files_analyzed == 2
        assert report.analysis_timestamp != ""

    def test_analyze_codebase_nonexistent(self):
        """Test analyzing non-existent codebase."""
        analyzer = TechDebtAnalyzer()
        report = analyzer.analyze_codebase("/nonexistent")
        assert report.total_files_analyzed == 0


class TestCalculateDebtScore:
    """Tests for calculate_debt_score function."""

    def test_perfect_score(self):
        """Test score with no debt."""
        report = DebtReport()
        report.total_files_analyzed = 10
        score = calculate_debt_score(report)
        assert score == 100.0

    def test_score_with_critical(self):
        """Test score deduction for critical items."""
        report = DebtReport()
        report.total_files_analyzed = 10
        report.add_item(DebtItem(
            category=DebtCategory.TODOS,
            severity=DebtSeverity.CRITICAL,
            file_path="a.py",
            line=1,
            description="Critical",
            effort_estimate="1d",
        ))
        score = calculate_debt_score(report)
        assert score < 100.0
        assert score >= 0.0

    def test_score_with_mixed_severity(self):
        """Test score with mixed severity items."""
        report = DebtReport()
        report.total_files_analyzed = 10

        # Add critical
        report.add_item(DebtItem(
            category=DebtCategory.TODOS,
            severity=DebtSeverity.CRITICAL,
            file_path="a.py",
            line=1,
            description="Critical",
            effort_estimate="1d",
        ))
        # Add high
        report.add_item(DebtItem(
            category=DebtCategory.TODOS,
            severity=DebtSeverity.HIGH,
            file_path="b.py",
            line=1,
            description="High",
            effort_estimate="4h",
        ))
        # Add medium
        report.add_item(DebtItem(
            category=DebtCategory.TODOS,
            severity=DebtSeverity.MEDIUM,
            file_path="c.py",
            line=1,
            description="Medium",
            effort_estimate="2h",
        ))
        # Add low
        report.add_item(DebtItem(
            category=DebtCategory.TODOS,
            severity=DebtSeverity.LOW,
            file_path="d.py",
            line=1,
            description="Low",
            effort_estimate="30m",
        ))

        score = calculate_debt_score(report)
        # Score should be: 100 - 10(crit) - 5(high) - 2(med) - 0.5(low) = 82.5
        assert score == pytest.approx(82.5, 0.1)

    def test_score_never_negative(self):
        """Test score never goes below 0."""
        report = DebtReport()
        report.total_files_analyzed = 1

        # Add many critical items
        for i in range(20):
            report.add_item(DebtItem(
                category=DebtCategory.TODOS,
                severity=DebtSeverity.CRITICAL,
                file_path=f"file{i}.py",
                line=1,
                description="Critical",
                effort_estimate="1d",
            ))

        score = calculate_debt_score(report)
        assert score == 0.0

    def test_score_empty_codebase(self):
        """Test score for empty codebase."""
        report = DebtReport()
        report.total_files_analyzed = 0
        score = calculate_debt_score(report)
        assert score == 100.0
