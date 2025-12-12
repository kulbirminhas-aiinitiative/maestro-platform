"""
Tests for ExternalProjectScanner

EPIC: MD-3022 - External Project Gap Analysis Scanner
"""
import pytest
import tempfile
import os
from pathlib import Path
from datetime import datetime

from maestro_hive.gap_analysis.external_scanner import (
    ExternalProjectScanner,
    ScannerConfig,
    ScanResult,
    ScanStatus,
    FileAnalysis,
    FileMetrics,
    ProjectMetrics,
    DependencyInfo,
    FileType,
    FileAnalyzer,
    create_external_scanner,
    DEFAULT_EXCLUDE_PATTERNS,
)


class TestScannerConfig:
    """Tests for ScannerConfig dataclass"""

    def test_default_config(self):
        """Test default configuration values"""
        config = ScannerConfig()
        assert config.max_file_size_mb == 10.0
        assert config.timeout_seconds == 300
        assert config.include_hidden is False
        assert config.follow_symlinks is False
        assert config.max_files == 10000
        assert config.max_depth is None

    def test_exclude_patterns_default(self):
        """Test default exclude patterns are set"""
        config = ScannerConfig()
        assert "__pycache__" in config.exclude_patterns
        assert ".git" in config.exclude_patterns
        assert "node_modules" in config.exclude_patterns

    def test_should_exclude_hidden_file(self):
        """Test hidden file exclusion"""
        config = ScannerConfig(include_hidden=False)
        assert config.should_exclude(Path(".hidden_file")) is True

    def test_should_not_exclude_hidden_when_enabled(self):
        """Test hidden file included when enabled"""
        config = ScannerConfig(include_hidden=True)
        assert config.should_exclude(Path(".hidden_file")) is False

    def test_should_exclude_by_pattern(self):
        """Test pattern-based exclusion"""
        config = ScannerConfig()
        assert config.should_exclude(Path("__pycache__")) is True
        assert config.should_exclude(Path("src/__pycache__/module")) is True

    def test_should_exclude_glob_pattern(self):
        """Test glob-like pattern exclusion"""
        config = ScannerConfig()
        assert config.should_exclude(Path("test.pyc")) is True


class TestFileType:
    """Tests for FileType enum"""

    def test_python_types(self):
        """Test Python file types"""
        assert FileType.PYTHON.value == "python"

    def test_all_file_types_have_values(self):
        """Test all file types have string values"""
        for ft in FileType:
            assert isinstance(ft.value, str)
            assert len(ft.value) > 0


class TestScanStatus:
    """Tests for ScanStatus enum"""

    def test_status_values(self):
        """Test scan status values"""
        assert ScanStatus.PENDING.value == "pending"
        assert ScanStatus.IN_PROGRESS.value == "in_progress"
        assert ScanStatus.COMPLETED.value == "completed"
        assert ScanStatus.FAILED.value == "failed"


class TestFileMetrics:
    """Tests for FileMetrics dataclass"""

    def test_default_metrics(self):
        """Test default metric values"""
        metrics = FileMetrics()
        assert metrics.lines_total == 0
        assert metrics.lines_code == 0
        assert metrics.lines_comment == 0
        assert metrics.lines_blank == 0
        assert metrics.complexity_score == 0.0
        assert metrics.has_docstrings is False
        assert metrics.has_type_hints is False


class TestFileAnalysis:
    """Tests for FileAnalysis dataclass"""

    def test_to_dict(self):
        """Test FileAnalysis serialization"""
        analysis = FileAnalysis(
            path="/test/file.py",
            relative_path="file.py",
            file_type=FileType.PYTHON,
            size_bytes=100,
            last_modified=datetime(2025, 1, 1),
            metrics=FileMetrics(lines_total=10, lines_code=8),
            content_hash="abc123",
        )
        result = analysis.to_dict()

        assert result["path"] == "/test/file.py"
        assert result["relative_path"] == "file.py"
        assert result["file_type"] == "python"
        assert result["size_bytes"] == 100
        assert result["metrics"]["lines_total"] == 10


class TestProjectMetrics:
    """Tests for ProjectMetrics dataclass"""

    def test_default_metrics(self):
        """Test default project metrics"""
        metrics = ProjectMetrics()
        assert metrics.total_files == 0
        assert metrics.total_lines == 0
        assert metrics.has_tests is False
        assert metrics.has_docs is False
        assert metrics.has_ci is False

    def test_to_dict(self):
        """Test ProjectMetrics serialization"""
        metrics = ProjectMetrics(
            total_files=10,
            total_lines=1000,
            languages_detected=["python", "javascript"],
        )
        result = metrics.to_dict()

        assert result["total_files"] == 10
        assert result["total_lines"] == 1000
        assert "python" in result["languages_detected"]


class TestDependencyInfo:
    """Tests for DependencyInfo dataclass"""

    def test_dependency_info(self):
        """Test dependency info creation"""
        dep = DependencyInfo(
            name="pytest",
            version="7.0.0",
            source="requirements.txt",
            is_dev=True,
        )
        assert dep.name == "pytest"
        assert dep.version == "7.0.0"
        assert dep.is_dev is True


class TestScanResult:
    """Tests for ScanResult dataclass"""

    def test_default_result(self):
        """Test default scan result"""
        result = ScanResult(
            project_path="/test",
            project_name="test",
            status=ScanStatus.PENDING,
            scan_start=datetime.now(),
        )
        assert result.files_scanned == 0
        assert result.files_skipped == 0
        assert result.file_analyses == []
        assert result.dependencies == []

    def test_to_dict(self):
        """Test ScanResult serialization"""
        result = ScanResult(
            project_path="/test",
            project_name="test_project",
            status=ScanStatus.COMPLETED,
            scan_start=datetime(2025, 1, 1),
            scan_end=datetime(2025, 1, 1, 0, 1),
            files_scanned=5,
        )
        data = result.to_dict()

        assert data["project_name"] == "test_project"
        assert data["status"] == "completed"
        assert data["files_scanned"] == 5


class TestFileAnalyzer:
    """Tests for FileAnalyzer class"""

    def test_analyzer_creation(self):
        """Test FileAnalyzer instantiation"""
        analyzer = FileAnalyzer()
        assert analyzer is not None

    def test_analyze_python_file(self):
        """Test analyzing a Python file"""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.py', delete=False
        ) as f:
            f.write('"""Test module"""\n')
            f.write('import os\n')
            f.write('\n')
            f.write('def hello() -> str:\n')
            f.write('    """Say hello"""\n')
            f.write('    return "hello"\n')
            f.flush()

            analyzer = FileAnalyzer()
            result = analyzer.analyze_file(
                Path(f.name),
                Path(tempfile.gettempdir())
            )

            assert result.file_type == FileType.PYTHON
            assert result.metrics.lines_total >= 6  # May include trailing newline
            assert result.metrics.imports_count >= 1
            assert result.metrics.functions_count >= 1
            assert result.content_hash != ""

            os.unlink(f.name)

    def test_detect_file_type_python(self):
        """Test Python file type detection"""
        analyzer = FileAnalyzer()
        assert analyzer._detect_file_type(Path("test.py")) == FileType.PYTHON
        assert analyzer._detect_file_type(Path("test.pyi")) == FileType.PYTHON

    def test_detect_file_type_javascript(self):
        """Test JavaScript file type detection"""
        analyzer = FileAnalyzer()
        assert analyzer._detect_file_type(Path("test.js")) == FileType.JAVASCRIPT
        assert analyzer._detect_file_type(Path("test.jsx")) == FileType.JAVASCRIPT

    def test_detect_file_type_typescript(self):
        """Test TypeScript file type detection"""
        analyzer = FileAnalyzer()
        assert analyzer._detect_file_type(Path("test.ts")) == FileType.TYPESCRIPT
        assert analyzer._detect_file_type(Path("test.tsx")) == FileType.TYPESCRIPT

    def test_detect_file_type_unknown(self):
        """Test unknown file type detection"""
        analyzer = FileAnalyzer()
        assert analyzer._detect_file_type(Path("test.xyz")) == FileType.OTHER


class TestExternalProjectScanner:
    """Tests for ExternalProjectScanner class"""

    def test_scanner_creation(self):
        """Test scanner instantiation"""
        scanner = ExternalProjectScanner()
        assert scanner.config is not None

    def test_scanner_with_custom_config(self):
        """Test scanner with custom configuration"""
        config = ScannerConfig(max_files=100, max_file_size_mb=5.0)
        scanner = ExternalProjectScanner(config=config)
        assert scanner.config.max_files == 100
        assert scanner.config.max_file_size_mb == 5.0

    @pytest.mark.asyncio
    async def test_scan_nonexistent_path(self):
        """Test scanning non-existent path"""
        scanner = ExternalProjectScanner()
        result = await scanner.scan_project("/nonexistent/path")

        assert result.status == ScanStatus.FAILED
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_scan_file_not_directory(self):
        """Test scanning a file instead of directory"""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test")
            f.flush()

            scanner = ExternalProjectScanner()
            result = await scanner.scan_project(f.name)

            assert result.status == ScanStatus.FAILED

            os.unlink(f.name)

    @pytest.mark.asyncio
    async def test_scan_empty_directory(self):
        """Test scanning an empty directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            scanner = ExternalProjectScanner()
            result = await scanner.scan_project(tmpdir)

            assert result.status == ScanStatus.COMPLETED
            assert result.files_scanned == 0

    @pytest.mark.asyncio
    async def test_scan_directory_with_files(self):
        """Test scanning a directory with files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            py_file = Path(tmpdir) / "test.py"
            py_file.write_text("print('hello')")

            js_file = Path(tmpdir) / "app.js"
            js_file.write_text("console.log('hello');")

            scanner = ExternalProjectScanner()
            result = await scanner.scan_project(tmpdir)

            assert result.status == ScanStatus.COMPLETED
            assert result.files_scanned == 2
            assert result.metrics is not None
            assert result.metrics.total_files == 2

    @pytest.mark.asyncio
    async def test_scan_detects_languages(self):
        """Test language detection during scan"""
        with tempfile.TemporaryDirectory() as tmpdir:
            py_file = Path(tmpdir) / "main.py"
            py_file.write_text("import sys")

            ts_file = Path(tmpdir) / "index.ts"
            ts_file.write_text("const x: number = 1;")

            scanner = ExternalProjectScanner()
            result = await scanner.scan_project(tmpdir)

            assert "python" in result.metrics.languages_detected
            assert "typescript" in result.metrics.languages_detected

    @pytest.mark.asyncio
    async def test_scan_respects_max_files(self):
        """Test max files limit is respected"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create more files than limit
            for i in range(10):
                (Path(tmpdir) / f"file{i}.py").write_text("# test")

            config = ScannerConfig(max_files=5)
            scanner = ExternalProjectScanner(config=config)
            result = await scanner.scan_project(tmpdir)

            assert result.files_scanned <= 5

    @pytest.mark.asyncio
    async def test_scan_excludes_hidden(self):
        """Test hidden files are excluded"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create visible and hidden files
            (Path(tmpdir) / "visible.py").write_text("# visible")
            (Path(tmpdir) / ".hidden.py").write_text("# hidden")

            scanner = ExternalProjectScanner()
            result = await scanner.scan_project(tmpdir)

            paths = [a.relative_path for a in result.file_analyses]
            assert "visible.py" in paths
            assert ".hidden.py" not in paths

    @pytest.mark.asyncio
    async def test_detect_python_dependencies(self):
        """Test Python dependency detection"""
        with tempfile.TemporaryDirectory() as tmpdir:
            req_file = Path(tmpdir) / "requirements.txt"
            req_file.write_text("pytest>=7.0.0\nrequests==2.28.0\n")

            scanner = ExternalProjectScanner()
            result = await scanner.scan_project(tmpdir)

            dep_names = [d.name for d in result.dependencies]
            assert "pytest" in dep_names
            assert "requests" in dep_names

    @pytest.mark.asyncio
    async def test_detect_javascript_dependencies(self):
        """Test JavaScript dependency detection"""
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg_json = Path(tmpdir) / "package.json"
            pkg_json.write_text('''{
                "dependencies": {"react": "^18.0.0"},
                "devDependencies": {"jest": "^29.0.0"}
            }''')

            scanner = ExternalProjectScanner()
            result = await scanner.scan_project(tmpdir)

            dep_names = [d.name for d in result.dependencies]
            assert "react" in dep_names
            assert "jest" in dep_names

            jest_dep = next(d for d in result.dependencies if d.name == "jest")
            assert jest_dep.is_dev is True

    @pytest.mark.asyncio
    async def test_detects_test_directory(self):
        """Test detection of test directories"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tests_dir = Path(tmpdir) / "tests"
            tests_dir.mkdir()
            (tests_dir / "test_main.py").write_text("def test_foo(): pass")

            scanner = ExternalProjectScanner()
            result = await scanner.scan_project(tmpdir)

            assert result.metrics.has_tests is True

    @pytest.mark.asyncio
    async def test_detects_docs_directory(self):
        """Test detection of docs directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "README.md").write_text("# Project")

            scanner = ExternalProjectScanner()
            result = await scanner.scan_project(tmpdir)

            assert result.metrics.has_docs is True


class TestFactoryFunction:
    """Tests for factory functions"""

    def test_create_external_scanner(self):
        """Test scanner factory function"""
        scanner = create_external_scanner()
        assert isinstance(scanner, ExternalProjectScanner)

    def test_create_external_scanner_with_config(self):
        """Test scanner factory with config"""
        config = ScannerConfig(max_files=50)
        scanner = create_external_scanner(config=config)
        assert scanner.config.max_files == 50
