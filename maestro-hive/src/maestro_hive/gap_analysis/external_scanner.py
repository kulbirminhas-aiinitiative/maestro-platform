"""
ExternalProjectScanner: External Codebase Scanning Engine

This module implements external project scanning capabilities for analyzing
external codebases, identifying patterns, and extracting metrics.

EPIC: MD-3022 - External Project Gap Analysis Scanner

Features:
- Directory traversal with configurable exclusions
- File type detection and categorization
- Code metrics extraction
- Dependency detection
- Pattern recognition
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from pathlib import Path
from enum import Enum
import logging
import os
import re
import hashlib


logger = logging.getLogger(__name__)


class FileType(Enum):
    """Types of files that can be scanned"""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    GO = "go"
    RUST = "rust"
    MARKDOWN = "markdown"
    JSON = "json"
    YAML = "yaml"
    CONFIG = "config"
    OTHER = "other"


class ScanStatus(Enum):
    """Status of a scan operation"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


# File extension to type mapping
FILE_TYPE_MAP = {
    ".py": FileType.PYTHON,
    ".pyx": FileType.PYTHON,
    ".pyi": FileType.PYTHON,
    ".js": FileType.JAVASCRIPT,
    ".jsx": FileType.JAVASCRIPT,
    ".ts": FileType.TYPESCRIPT,
    ".tsx": FileType.TYPESCRIPT,
    ".java": FileType.JAVA,
    ".go": FileType.GO,
    ".rs": FileType.RUST,
    ".md": FileType.MARKDOWN,
    ".json": FileType.JSON,
    ".yaml": FileType.YAML,
    ".yml": FileType.YAML,
    ".toml": FileType.CONFIG,
    ".ini": FileType.CONFIG,
    ".cfg": FileType.CONFIG,
}

# Default patterns to exclude from scanning
DEFAULT_EXCLUDE_PATTERNS = [
    "__pycache__",
    ".git",
    ".svn",
    ".hg",
    "node_modules",
    "venv",
    ".venv",
    "env",
    ".env",
    "dist",
    "build",
    ".eggs",
    "*.egg-info",
    ".pytest_cache",
    ".mypy_cache",
    ".tox",
    "coverage",
    ".coverage",
    "*.pyc",
    "*.pyo",
    "*.so",
    "*.dylib",
]


@dataclass
class ScannerConfig:
    """Configuration for the external project scanner"""
    max_file_size_mb: float = 10.0
    timeout_seconds: int = 300
    exclude_patterns: List[str] = field(default_factory=lambda: DEFAULT_EXCLUDE_PATTERNS.copy())
    include_hidden: bool = False
    follow_symlinks: bool = False
    max_files: int = 10000
    max_depth: Optional[int] = None

    def should_exclude(self, path: Path) -> bool:
        """Check if a path should be excluded based on patterns"""
        path_str = str(path)
        name = path.name

        # Check hidden files
        if not self.include_hidden and name.startswith('.'):
            return True

        for pattern in self.exclude_patterns:
            if pattern.startswith('*'):
                # Glob-like pattern
                if name.endswith(pattern[1:]):
                    return True
            elif pattern in path_str or name == pattern:
                return True

        return False


@dataclass
class FileMetrics:
    """Metrics for a single file"""
    lines_total: int = 0
    lines_code: int = 0
    lines_comment: int = 0
    lines_blank: int = 0
    complexity_score: float = 0.0
    has_docstrings: bool = False
    has_type_hints: bool = False
    imports_count: int = 0
    functions_count: int = 0
    classes_count: int = 0


@dataclass
class FileAnalysis:
    """Analysis results for a single file"""
    path: str
    relative_path: str
    file_type: FileType
    size_bytes: int
    last_modified: datetime
    metrics: FileMetrics
    content_hash: str
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "relative_path": self.relative_path,
            "file_type": self.file_type.value,
            "size_bytes": self.size_bytes,
            "last_modified": self.last_modified.isoformat(),
            "metrics": {
                "lines_total": self.metrics.lines_total,
                "lines_code": self.metrics.lines_code,
                "lines_comment": self.metrics.lines_comment,
                "lines_blank": self.metrics.lines_blank,
                "complexity_score": self.metrics.complexity_score,
                "has_docstrings": self.metrics.has_docstrings,
                "has_type_hints": self.metrics.has_type_hints,
                "imports_count": self.metrics.imports_count,
                "functions_count": self.metrics.functions_count,
                "classes_count": self.metrics.classes_count,
            },
            "content_hash": self.content_hash,
            "errors": self.errors,
        }


@dataclass
class ProjectMetrics:
    """Aggregated metrics for entire project"""
    total_files: int = 0
    total_lines: int = 0
    code_lines: int = 0
    comment_lines: int = 0
    blank_lines: int = 0
    total_size_bytes: int = 0
    files_by_type: Dict[str, int] = field(default_factory=dict)
    languages_detected: List[str] = field(default_factory=list)
    avg_file_size: float = 0.0
    avg_complexity: float = 0.0
    has_tests: bool = False
    has_docs: bool = False
    has_ci: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_files": self.total_files,
            "total_lines": self.total_lines,
            "code_lines": self.code_lines,
            "comment_lines": self.comment_lines,
            "blank_lines": self.blank_lines,
            "total_size_bytes": self.total_size_bytes,
            "files_by_type": self.files_by_type,
            "languages_detected": self.languages_detected,
            "avg_file_size": self.avg_file_size,
            "avg_complexity": self.avg_complexity,
            "has_tests": self.has_tests,
            "has_docs": self.has_docs,
            "has_ci": self.has_ci,
        }


@dataclass
class DependencyInfo:
    """Information about a detected dependency"""
    name: str
    version: Optional[str] = None
    source: str = ""  # e.g., "requirements.txt", "package.json"
    is_dev: bool = False


@dataclass
class ScanResult:
    """Complete results of a project scan"""
    project_path: str
    project_name: str
    status: ScanStatus
    scan_start: datetime
    scan_end: Optional[datetime] = None
    files_scanned: int = 0
    files_skipped: int = 0
    file_analyses: List[FileAnalysis] = field(default_factory=list)
    metrics: Optional[ProjectMetrics] = None
    dependencies: List[DependencyInfo] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_path": self.project_path,
            "project_name": self.project_name,
            "status": self.status.value,
            "scan_start": self.scan_start.isoformat(),
            "scan_end": self.scan_end.isoformat() if self.scan_end else None,
            "files_scanned": self.files_scanned,
            "files_skipped": self.files_skipped,
            "file_analyses": [fa.to_dict() for fa in self.file_analyses],
            "metrics": self.metrics.to_dict() if self.metrics else None,
            "dependencies": [
                {"name": d.name, "version": d.version, "source": d.source, "is_dev": d.is_dev}
                for d in self.dependencies
            ],
            "errors": self.errors,
            "warnings": self.warnings,
        }


class FileAnalyzer:
    """Analyzes individual files for metrics and patterns"""

    def __init__(self):
        self._python_patterns = {
            "import": re.compile(r'^(?:from\s+\S+\s+)?import\s+'),
            "function": re.compile(r'^(?:async\s+)?def\s+\w+'),
            "class": re.compile(r'^class\s+\w+'),
            "docstring": re.compile(r'^\s*["\'][\'"]{2}'),
            "type_hint": re.compile(r':\s*\w+\s*[=\)]|->'),
        }

    def analyze_file(self, path: Path, base_path: Path) -> FileAnalysis:
        """Analyze a single file and return results"""
        try:
            stat = path.stat()
            file_type = self._detect_file_type(path)

            # Read file content
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            except Exception as e:
                return FileAnalysis(
                    path=str(path),
                    relative_path=str(path.relative_to(base_path)),
                    file_type=file_type,
                    size_bytes=stat.st_size,
                    last_modified=datetime.fromtimestamp(stat.st_mtime),
                    metrics=FileMetrics(),
                    content_hash="",
                    errors=[f"Failed to read file: {str(e)}"]
                )

            # Calculate metrics
            metrics = self._calculate_metrics(content, file_type)
            content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

            return FileAnalysis(
                path=str(path),
                relative_path=str(path.relative_to(base_path)),
                file_type=file_type,
                size_bytes=stat.st_size,
                last_modified=datetime.fromtimestamp(stat.st_mtime),
                metrics=metrics,
                content_hash=content_hash,
            )

        except Exception as e:
            logger.error(f"Error analyzing file {path}: {e}")
            return FileAnalysis(
                path=str(path),
                relative_path=str(path.relative_to(base_path)) if base_path else str(path),
                file_type=FileType.OTHER,
                size_bytes=0,
                last_modified=datetime.now(),
                metrics=FileMetrics(),
                content_hash="",
                errors=[str(e)]
            )

    def _detect_file_type(self, path: Path) -> FileType:
        """Detect file type based on extension"""
        suffix = path.suffix.lower()
        return FILE_TYPE_MAP.get(suffix, FileType.OTHER)

    def _calculate_metrics(self, content: str, file_type: FileType) -> FileMetrics:
        """Calculate metrics for file content"""
        lines = content.split('\n')
        metrics = FileMetrics()

        metrics.lines_total = len(lines)

        in_multiline_comment = False
        for line in lines:
            stripped = line.strip()

            if not stripped:
                metrics.lines_blank += 1
                continue

            # Handle multiline comments/docstrings
            if file_type == FileType.PYTHON:
                if '"""' in stripped or "'''" in stripped:
                    if stripped.count('"""') == 1 or stripped.count("'''") == 1:
                        in_multiline_comment = not in_multiline_comment
                    metrics.lines_comment += 1
                    continue

            if in_multiline_comment:
                metrics.lines_comment += 1
                continue

            # Single line comments
            if stripped.startswith('#') or stripped.startswith('//'):
                metrics.lines_comment += 1
                continue

            metrics.lines_code += 1

            # Python-specific analysis
            if file_type == FileType.PYTHON:
                if self._python_patterns["import"].match(stripped):
                    metrics.imports_count += 1
                if self._python_patterns["function"].match(stripped):
                    metrics.functions_count += 1
                if self._python_patterns["class"].match(stripped):
                    metrics.classes_count += 1
                if self._python_patterns["docstring"].match(stripped):
                    metrics.has_docstrings = True
                if self._python_patterns["type_hint"].search(stripped):
                    metrics.has_type_hints = True

        # Calculate complexity score (simplified McCabe-like)
        complexity_keywords = ['if', 'elif', 'for', 'while', 'except', 'with', 'and', 'or']
        complexity = 1
        for kw in complexity_keywords:
            complexity += content.count(f' {kw} ') + content.count(f'\t{kw} ')
        metrics.complexity_score = complexity / max(metrics.lines_code, 1)

        return metrics


class ExternalProjectScanner:
    """
    Scanner for external project codebases.

    Analyzes project structure, extracts metrics, and identifies patterns
    for gap analysis.
    """

    def __init__(self, config: Optional[ScannerConfig] = None):
        self.config = config or ScannerConfig()
        self._file_analyzer = FileAnalyzer()
        logger.info("ExternalProjectScanner initialized")

    async def scan_project(self, project_path: str) -> ScanResult:
        """
        Scan an external project directory.

        Args:
            project_path: Path to the project directory to scan

        Returns:
            ScanResult containing all analysis results
        """
        path = Path(project_path)

        if not path.exists():
            logger.error(f"Project path does not exist: {project_path}")
            return ScanResult(
                project_path=project_path,
                project_name=path.name,
                status=ScanStatus.FAILED,
                scan_start=datetime.now(),
                scan_end=datetime.now(),
                errors=[f"Project path does not exist: {project_path}"]
            )

        if not path.is_dir():
            logger.error(f"Project path is not a directory: {project_path}")
            return ScanResult(
                project_path=project_path,
                project_name=path.name,
                status=ScanStatus.FAILED,
                scan_start=datetime.now(),
                scan_end=datetime.now(),
                errors=[f"Project path is not a directory: {project_path}"]
            )

        logger.info(f"Starting scan of project: {project_path}")

        result = ScanResult(
            project_path=project_path,
            project_name=path.name,
            status=ScanStatus.IN_PROGRESS,
            scan_start=datetime.now(),
        )

        try:
            # Scan all files
            files_scanned = 0
            files_skipped = 0

            for file_path in self._walk_directory(path):
                if files_scanned >= self.config.max_files:
                    result.warnings.append(f"Max files limit reached ({self.config.max_files})")
                    break

                # Check file size
                try:
                    size = file_path.stat().st_size
                    if size > self.config.max_file_size_mb * 1024 * 1024:
                        files_skipped += 1
                        continue
                except Exception:
                    files_skipped += 1
                    continue

                # Analyze file
                analysis = self._file_analyzer.analyze_file(file_path, path)
                result.file_analyses.append(analysis)
                files_scanned += 1

            result.files_scanned = files_scanned
            result.files_skipped = files_skipped

            # Calculate aggregate metrics
            result.metrics = self._calculate_project_metrics(result.file_analyses, path)

            # Detect dependencies
            result.dependencies = self._detect_dependencies(path)

            result.status = ScanStatus.COMPLETED
            result.scan_end = datetime.now()

            logger.info(f"Scan completed: {files_scanned} files scanned, {files_skipped} skipped")

        except Exception as e:
            logger.error(f"Scan failed: {e}")
            result.status = ScanStatus.FAILED
            result.scan_end = datetime.now()
            result.errors.append(str(e))

        return result

    def _walk_directory(self, root: Path, current_depth: int = 0):
        """Walk directory yielding files, respecting config"""
        if self.config.max_depth and current_depth > self.config.max_depth:
            return

        try:
            for item in root.iterdir():
                if self.config.should_exclude(item):
                    continue

                if item.is_symlink() and not self.config.follow_symlinks:
                    continue

                if item.is_file():
                    yield item
                elif item.is_dir():
                    yield from self._walk_directory(item, current_depth + 1)
        except PermissionError:
            logger.warning(f"Permission denied: {root}")
        except Exception as e:
            logger.warning(f"Error walking directory {root}: {e}")

    def _calculate_project_metrics(
        self,
        analyses: List[FileAnalysis],
        project_path: Path
    ) -> ProjectMetrics:
        """Calculate aggregate metrics from file analyses"""
        metrics = ProjectMetrics()

        metrics.total_files = len(analyses)

        type_counts: Dict[str, int] = {}
        languages: Set[str] = set()
        total_complexity = 0.0

        for analysis in analyses:
            metrics.total_lines += analysis.metrics.lines_total
            metrics.code_lines += analysis.metrics.lines_code
            metrics.comment_lines += analysis.metrics.lines_comment
            metrics.blank_lines += analysis.metrics.lines_blank
            metrics.total_size_bytes += analysis.size_bytes

            # Count by type
            type_name = analysis.file_type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1

            if analysis.file_type not in [FileType.OTHER, FileType.CONFIG, FileType.MARKDOWN]:
                languages.add(type_name)

            total_complexity += analysis.metrics.complexity_score

        metrics.files_by_type = type_counts
        metrics.languages_detected = list(languages)

        if metrics.total_files > 0:
            metrics.avg_file_size = metrics.total_size_bytes / metrics.total_files
            metrics.avg_complexity = total_complexity / metrics.total_files

        # Check for common project elements
        metrics.has_tests = any(
            'test' in a.relative_path.lower() or
            a.relative_path.startswith('tests/') or
            a.relative_path.endswith('_test.py')
            for a in analyses
        )

        metrics.has_docs = any(
            a.relative_path.lower().startswith('docs/') or
            a.relative_path.lower() == 'readme.md'
            for a in analyses
        )

        # Check for CI configuration
        ci_files = ['.github/workflows', '.gitlab-ci.yml', 'Jenkinsfile', '.circleci']
        metrics.has_ci = any(
            any(cf in a.relative_path for cf in ci_files)
            for a in analyses
        )

        return metrics

    def _detect_dependencies(self, project_path: Path) -> List[DependencyInfo]:
        """Detect project dependencies from common files"""
        dependencies = []

        # Python: requirements.txt
        req_file = project_path / "requirements.txt"
        if req_file.exists():
            try:
                with open(req_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            parts = re.split(r'[<>=!~\[]', line)
                            name = parts[0].strip()
                            if name:
                                dependencies.append(DependencyInfo(
                                    name=name,
                                    source="requirements.txt"
                                ))
            except Exception as e:
                logger.warning(f"Error reading requirements.txt: {e}")

        # Python: pyproject.toml
        pyproject = project_path / "pyproject.toml"
        if pyproject.exists():
            try:
                with open(pyproject, 'r') as f:
                    content = f.read()
                    # Simple extraction (not full TOML parsing)
                    if 'dependencies' in content:
                        dependencies.append(DependencyInfo(
                            name="pyproject.toml dependencies",
                            source="pyproject.toml"
                        ))
            except Exception as e:
                logger.warning(f"Error reading pyproject.toml: {e}")

        # JavaScript/TypeScript: package.json
        pkg_json = project_path / "package.json"
        if pkg_json.exists():
            try:
                import json
                with open(pkg_json, 'r') as f:
                    data = json.load(f)

                    for dep_name in data.get('dependencies', {}):
                        dependencies.append(DependencyInfo(
                            name=dep_name,
                            version=data['dependencies'].get(dep_name),
                            source="package.json",
                            is_dev=False
                        ))

                    for dep_name in data.get('devDependencies', {}):
                        dependencies.append(DependencyInfo(
                            name=dep_name,
                            version=data['devDependencies'].get(dep_name),
                            source="package.json",
                            is_dev=True
                        ))
            except Exception as e:
                logger.warning(f"Error reading package.json: {e}")

        return dependencies


def create_external_scanner(config: Optional[ScannerConfig] = None) -> ExternalProjectScanner:
    """Factory function to create an ExternalProjectScanner instance"""
    return ExternalProjectScanner(config=config)
