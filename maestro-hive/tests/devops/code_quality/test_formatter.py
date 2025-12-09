"""
Tests for the Code Formatter module.

Tests AC-1: Code formatting with black, isort, prettier.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from maestro_hive.devops.code_quality.formatter import (
    CodeFormatter,
    FormatConfig,
    FormatResult,
    FormatStatus,
    FormatTool,
    FileFormatResult,
    format_python_files,
    format_typescript_files,
)


class TestFormatConfig:
    """Tests for FormatConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = FormatConfig()
        assert config.line_length == 88
        assert config.target_version == "py311"
        assert config.skip_string_normalization is False
        assert config.isort_profile == "black"
        assert ".git" in config.exclude_patterns
        assert "node_modules" in config.exclude_patterns

    def test_custom_config(self):
        """Test custom configuration."""
        config = FormatConfig(
            line_length=100,
            target_version="py310",
            known_first_party=["myapp"],
        )
        assert config.line_length == 100
        assert config.target_version == "py310"
        assert "myapp" in config.known_first_party


class TestFileFormatResult:
    """Tests for FileFormatResult dataclass."""

    def test_create_result(self):
        """Test creating a file format result."""
        result = FileFormatResult(
            file_path="/path/to/file.py",
            status=FormatStatus.REFORMATTED,
            tool=FormatTool.BLACK,
            changes_made=True,
        )
        assert result.file_path == "/path/to/file.py"
        assert result.status == FormatStatus.REFORMATTED
        assert result.tool == FormatTool.BLACK
        assert result.changes_made is True


class TestFormatResult:
    """Tests for FormatResult dataclass."""

    def test_empty_result(self):
        """Test empty format result."""
        result = FormatResult()
        assert result.total_files == 0
        assert result.files_reformatted == 0
        assert result.success is True

    def test_add_file_result(self):
        """Test adding file results."""
        result = FormatResult()

        result.add_file_result(FileFormatResult(
            file_path="a.py",
            status=FormatStatus.UNCHANGED,
            tool=FormatTool.BLACK,
            changes_made=False,
        ))
        assert result.files_checked == 1
        assert result.files_unchanged == 1

        result.add_file_result(FileFormatResult(
            file_path="b.py",
            status=FormatStatus.REFORMATTED,
            tool=FormatTool.BLACK,
            changes_made=True,
        ))
        assert result.files_checked == 2
        assert result.files_reformatted == 1

    def test_error_sets_success_false(self):
        """Test that errors mark result as failed."""
        result = FormatResult()
        result.add_file_result(FileFormatResult(
            file_path="bad.py",
            status=FormatStatus.ERROR,
            tool=FormatTool.BLACK,
            changes_made=False,
            error_message="Syntax error",
        ))
        assert result.success is False
        assert result.files_errored == 1


class TestCodeFormatter:
    """Tests for CodeFormatter class."""

    def test_init_default_config(self):
        """Test initialization with default config."""
        formatter = CodeFormatter()
        assert formatter.config is not None
        assert formatter.config.line_length == 88

    def test_init_custom_config(self):
        """Test initialization with custom config."""
        config = FormatConfig(line_length=120)
        formatter = CodeFormatter(config)
        assert formatter.config.line_length == 120

    def test_find_python_files_single_file(self, tmp_path):
        """Test finding a single Python file."""
        py_file = tmp_path / "test.py"
        py_file.write_text("print('hello')")

        formatter = CodeFormatter()
        files = formatter._find_python_files(py_file)
        assert len(files) == 1
        assert files[0] == py_file

    def test_find_python_files_directory(self, tmp_path):
        """Test finding Python files in directory."""
        (tmp_path / "a.py").write_text("# a")
        (tmp_path / "b.py").write_text("# b")
        (tmp_path / "c.txt").write_text("# not python")

        formatter = CodeFormatter()
        files = formatter._find_python_files(tmp_path)
        assert len(files) == 2

    def test_find_python_files_excludes_patterns(self, tmp_path):
        """Test exclusion patterns."""
        (tmp_path / "good.py").write_text("# good")
        venv = tmp_path / ".venv"
        venv.mkdir()
        (venv / "bad.py").write_text("# should be excluded")

        formatter = CodeFormatter()
        files = formatter._find_python_files(tmp_path)
        assert len(files) == 1
        assert "good.py" in str(files[0])

    def test_find_typescript_files(self, tmp_path):
        """Test finding TypeScript files."""
        (tmp_path / "app.ts").write_text("const x = 1;")
        (tmp_path / "component.tsx").write_text("export const C = () => null;")
        (tmp_path / "script.js").write_text("var y = 2;")
        (tmp_path / "other.py").write_text("# python")

        formatter = CodeFormatter()
        files = formatter._find_typescript_files(tmp_path)
        assert len(files) == 3

    @patch('subprocess.run')
    def test_format_with_black_success(self, mock_run, tmp_path):
        """Test successful black formatting."""
        py_file = tmp_path / "test.py"
        py_file.write_text("x=1")

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="",
            stderr=""
        )

        formatter = CodeFormatter()
        result = formatter.format_with_black(str(tmp_path))

        assert result.success is True
        assert mock_run.called

    @patch('subprocess.run')
    def test_format_with_black_check_only(self, mock_run, tmp_path):
        """Test black in check-only mode."""
        py_file = tmp_path / "test.py"
        py_file.write_text("x=1")

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        formatter = CodeFormatter()
        result = formatter.format_with_black(str(tmp_path), check_only=True)

        # Verify --check flag was passed
        call_args = mock_run.call_args[0][0]
        assert "--check" in call_args
        assert "--diff" in call_args

    def test_format_with_black_nonexistent_path(self):
        """Test formatting non-existent path."""
        formatter = CodeFormatter()
        result = formatter.format_with_black("/nonexistent/path")

        assert result.success is False
        assert "does not exist" in result.summary

    @patch('subprocess.run')
    def test_format_with_isort_success(self, mock_run, tmp_path):
        """Test successful isort formatting."""
        py_file = tmp_path / "test.py"
        py_file.write_text("import os\nimport sys")

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        formatter = CodeFormatter()
        result = formatter.format_with_isort(str(tmp_path))

        assert result.success is True

    @patch('subprocess.run')
    def test_format_with_prettier_success(self, mock_run, tmp_path):
        """Test successful prettier formatting."""
        ts_file = tmp_path / "app.ts"
        ts_file.write_text("const x=1;")

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        formatter = CodeFormatter()
        result = formatter.format_with_prettier(str(tmp_path))

        assert result.success is True

    def test_format_with_prettier_no_files(self, tmp_path):
        """Test prettier with no TypeScript files."""
        py_file = tmp_path / "test.py"
        py_file.write_text("# python only")

        formatter = CodeFormatter()
        result = formatter.format_with_prettier(str(tmp_path))

        assert "No TypeScript/JavaScript files found" in result.summary

    @patch('subprocess.run')
    def test_format_all(self, mock_run, tmp_path):
        """Test running all formatters."""
        (tmp_path / "test.py").write_text("x=1")
        (tmp_path / "app.ts").write_text("const y=2;")

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        formatter = CodeFormatter()
        results = formatter.format_all(str(tmp_path))

        assert "black" in results
        assert "isort" in results
        assert "prettier" in results


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    @patch('subprocess.run')
    def test_format_python_files(self, mock_run, tmp_path):
        """Test format_python_files function."""
        py_file = tmp_path / "test.py"
        py_file.write_text("x=1")

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = format_python_files(str(tmp_path))
        assert result is not None

    @patch('subprocess.run')
    def test_format_typescript_files(self, mock_run, tmp_path):
        """Test format_typescript_files function."""
        ts_file = tmp_path / "app.ts"
        ts_file.write_text("const x=1;")

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = format_typescript_files(str(tmp_path))
        assert result is not None
