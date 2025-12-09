"""
Tests for the Code Linter module.

Tests AC-2: Linting violation fixes.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from maestro_hive.devops.code_quality.linter import (
    CodeLinter,
    LintConfig,
    LintResult,
    LintViolation,
    LintSeverity,
    LintTool,
    run_flake8,
    run_eslint,
)


class TestLintSeverity:
    """Tests for LintSeverity enum."""

    def test_severity_values(self):
        """Test severity enum values."""
        assert LintSeverity.ERROR.value == "error"
        assert LintSeverity.WARNING.value == "warning"
        assert LintSeverity.INFO.value == "info"
        assert LintSeverity.CONVENTION.value == "convention"


class TestLintTool:
    """Tests for LintTool enum."""

    def test_tool_values(self):
        """Test tool enum values."""
        assert LintTool.FLAKE8.value == "flake8"
        assert LintTool.ESLINT.value == "eslint"
        assert LintTool.MYPY.value == "mypy"


class TestLintViolation:
    """Tests for LintViolation dataclass."""

    def test_create_violation(self):
        """Test creating a lint violation."""
        violation = LintViolation(
            file_path="/path/to/file.py",
            line=10,
            column=5,
            code="E501",
            message="line too long",
            severity=LintSeverity.ERROR,
            tool=LintTool.FLAKE8,
        )
        assert violation.file_path == "/path/to/file.py"
        assert violation.line == 10
        assert violation.code == "E501"

    def test_location_property(self):
        """Test location property."""
        violation = LintViolation(
            file_path="test.py",
            line=5,
            column=3,
            code="W503",
            message="test",
            severity=LintSeverity.WARNING,
            tool=LintTool.FLAKE8,
        )
        assert violation.location == "test.py:5:3"

    def test_to_dict(self):
        """Test converting to dictionary."""
        violation = LintViolation(
            file_path="test.py",
            line=1,
            column=1,
            code="E001",
            message="test message",
            severity=LintSeverity.ERROR,
            tool=LintTool.FLAKE8,
            rule="some-rule",
        )
        d = violation.to_dict()
        assert d["file_path"] == "test.py"
        assert d["severity"] == "error"
        assert d["tool"] == "flake8"
        assert d["rule"] == "some-rule"


class TestLintConfig:
    """Tests for LintConfig dataclass."""

    def test_default_config(self):
        """Test default configuration."""
        config = LintConfig()
        assert config.max_line_length == 88
        assert config.max_complexity == 10
        assert "E203" in config.ignore_codes
        assert ".git" in config.exclude_patterns

    def test_custom_config(self):
        """Test custom configuration."""
        config = LintConfig(
            max_line_length=120,
            max_complexity=15,
            ignore_codes=["E501"],
        )
        assert config.max_line_length == 120
        assert config.max_complexity == 15
        assert config.ignore_codes == ["E501"]


class TestLintResult:
    """Tests for LintResult dataclass."""

    def test_empty_result(self):
        """Test empty result."""
        result = LintResult()
        assert result.total_violations == 0
        assert result.error_count == 0
        assert result.warning_count == 0
        assert result.success is True

    def test_add_violation(self):
        """Test adding violations."""
        result = LintResult()

        result.add_violation(LintViolation(
            file_path="a.py",
            line=1,
            column=1,
            code="E001",
            message="error",
            severity=LintSeverity.ERROR,
            tool=LintTool.FLAKE8,
        ))
        assert result.total_violations == 1
        assert result.error_count == 1
        assert result.warning_count == 0

        result.add_violation(LintViolation(
            file_path="a.py",
            line=2,
            column=1,
            code="W001",
            message="warning",
            severity=LintSeverity.WARNING,
            tool=LintTool.FLAKE8,
        ))
        assert result.total_violations == 2
        assert result.warning_count == 1

    def test_get_violations_by_file(self):
        """Test grouping violations by file."""
        result = LintResult()
        result.add_violation(LintViolation(
            file_path="a.py", line=1, column=1, code="E1",
            message="", severity=LintSeverity.ERROR, tool=LintTool.FLAKE8
        ))
        result.add_violation(LintViolation(
            file_path="a.py", line=2, column=1, code="E2",
            message="", severity=LintSeverity.ERROR, tool=LintTool.FLAKE8
        ))
        result.add_violation(LintViolation(
            file_path="b.py", line=1, column=1, code="E3",
            message="", severity=LintSeverity.ERROR, tool=LintTool.FLAKE8
        ))

        by_file = result.get_violations_by_file()
        assert len(by_file["a.py"]) == 2
        assert len(by_file["b.py"]) == 1

    def test_get_violations_by_code(self):
        """Test grouping violations by code."""
        result = LintResult()
        result.add_violation(LintViolation(
            file_path="a.py", line=1, column=1, code="E501",
            message="", severity=LintSeverity.ERROR, tool=LintTool.FLAKE8
        ))
        result.add_violation(LintViolation(
            file_path="b.py", line=1, column=1, code="E501",
            message="", severity=LintSeverity.ERROR, tool=LintTool.FLAKE8
        ))
        result.add_violation(LintViolation(
            file_path="c.py", line=1, column=1, code="W503",
            message="", severity=LintSeverity.WARNING, tool=LintTool.FLAKE8
        ))

        by_code = result.get_violations_by_code()
        assert len(by_code["E501"]) == 2
        assert len(by_code["W503"]) == 1


class TestCodeLinter:
    """Tests for CodeLinter class."""

    def test_init_default_config(self):
        """Test initialization with default config."""
        linter = CodeLinter()
        assert linter.config is not None
        assert linter.config.max_line_length == 88

    def test_init_custom_config(self):
        """Test initialization with custom config."""
        config = LintConfig(max_line_length=100)
        linter = CodeLinter(config)
        assert linter.config.max_line_length == 100

    def test_parse_flake8_output(self):
        """Test parsing flake8 output."""
        linter = CodeLinter()
        output = """test.py:1:1: E101 indentation contains mixed spaces and tabs
test.py:5:80: E501 line too long (85 > 79 characters)
test.py:10:1: W503 line break before binary operator"""

        violations = linter._parse_flake8_output(output)
        assert len(violations) == 3

        assert violations[0].file_path == "test.py"
        assert violations[0].line == 1
        assert violations[0].code == "E101"
        assert violations[0].severity == LintSeverity.ERROR

        assert violations[1].code == "E501"
        assert violations[2].code == "W503"
        assert violations[2].severity == LintSeverity.WARNING

    def test_parse_flake8_output_empty(self):
        """Test parsing empty flake8 output."""
        linter = CodeLinter()
        violations = linter._parse_flake8_output("")
        assert len(violations) == 0

    def test_parse_eslint_output(self):
        """Test parsing eslint JSON output."""
        linter = CodeLinter()
        output = '''[
            {
                "filePath": "/path/to/file.ts",
                "messages": [
                    {
                        "line": 5,
                        "column": 10,
                        "ruleId": "no-unused-vars",
                        "message": "Variable is unused",
                        "severity": 2
                    },
                    {
                        "line": 10,
                        "column": 1,
                        "ruleId": "semi",
                        "message": "Missing semicolon",
                        "severity": 1
                    }
                ]
            }
        ]'''

        violations = linter._parse_eslint_output(output)
        assert len(violations) == 2

        assert violations[0].file_path == "/path/to/file.ts"
        assert violations[0].code == "no-unused-vars"
        assert violations[0].severity == LintSeverity.ERROR

        assert violations[1].code == "semi"
        assert violations[1].severity == LintSeverity.WARNING

    def test_parse_eslint_invalid_json(self):
        """Test parsing invalid eslint output."""
        linter = CodeLinter()
        violations = linter._parse_eslint_output("not valid json")
        assert len(violations) == 0

    @patch('subprocess.run')
    def test_run_flake8_success(self, mock_run, tmp_path):
        """Test running flake8 successfully."""
        py_file = tmp_path / "test.py"
        py_file.write_text("x = 1")

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="",
            stderr=""
        )

        linter = CodeLinter()
        result = linter.run_flake8(str(tmp_path))

        assert result.success is True
        assert result.total_violations == 0

    @patch('subprocess.run')
    def test_run_flake8_with_violations(self, mock_run, tmp_path):
        """Test running flake8 with violations."""
        py_file = tmp_path / "test.py"
        py_file.write_text("x=1")

        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="test.py:1:2: E225 missing whitespace around operator",
            stderr=""
        )

        linter = CodeLinter()
        result = linter.run_flake8(str(tmp_path))

        assert result.total_violations == 1
        assert result.violations[0].code == "E225"

    def test_run_flake8_nonexistent_path(self):
        """Test running flake8 on non-existent path."""
        linter = CodeLinter()
        result = linter.run_flake8("/nonexistent/path")

        assert result.success is False
        assert "does not exist" in result.summary

    @patch('subprocess.run')
    def test_run_eslint_success(self, mock_run, tmp_path):
        """Test running eslint successfully."""
        ts_file = tmp_path / "app.ts"
        ts_file.write_text("const x = 1;")

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="[]",
            stderr=""
        )

        linter = CodeLinter()
        result = linter.run_eslint(str(tmp_path))

        assert result.success is True

    @patch('subprocess.run')
    def test_run_all(self, mock_run, tmp_path):
        """Test running all linters."""
        (tmp_path / "test.py").write_text("x = 1")
        (tmp_path / "app.ts").write_text("const y = 2;")

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="[]",
            stderr=""
        )

        linter = CodeLinter()
        results = linter.run_all(str(tmp_path))

        assert "flake8" in results
        assert "eslint" in results


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    @patch('subprocess.run')
    def test_run_flake8_function(self, mock_run, tmp_path):
        """Test run_flake8 convenience function."""
        py_file = tmp_path / "test.py"
        py_file.write_text("x = 1")

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = run_flake8(str(tmp_path))
        assert result is not None

    @patch('subprocess.run')
    def test_run_eslint_function(self, mock_run, tmp_path):
        """Test run_eslint convenience function."""
        ts_file = tmp_path / "app.ts"
        ts_file.write_text("const x = 1;")

        mock_run.return_value = MagicMock(returncode=0, stdout="[]", stderr="")

        result = run_eslint(str(tmp_path))
        assert result is not None
