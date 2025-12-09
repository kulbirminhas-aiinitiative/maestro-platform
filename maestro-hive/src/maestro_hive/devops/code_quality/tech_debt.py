"""
Technical Debt Analyzer Module - AC-4: Technical debt analysis and tracking.

This module provides technical debt analysis including:
- Code complexity analysis
- TODO/FIXME tracking
- Dependency outdatedness checking
- Debt score calculation

Implements: MD-2788 AC-4
"""

import logging
import re
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class DebtCategory(Enum):
    """Categories of technical debt."""
    CODE_COMPLEXITY = "code_complexity"
    TODOS = "todos"
    DEPRECATED_DEPS = "deprecated_deps"
    MISSING_TYPES = "missing_types"
    MISSING_TESTS = "missing_tests"
    CODE_DUPLICATION = "code_duplication"
    NAMING_CONVENTION = "naming_convention"
    OUTDATED_DEPS = "outdated_deps"


class DebtSeverity(Enum):
    """Severity of technical debt items."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class DebtItem:
    """A single technical debt item."""
    category: DebtCategory
    severity: DebtSeverity
    file_path: str
    line: Optional[int]
    description: str
    effort_estimate: str  # e.g., "1h", "2d", "1w"
    suggestion: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "category": self.category.value,
            "severity": self.severity.value,
            "file_path": self.file_path,
            "line": self.line,
            "description": self.description,
            "effort_estimate": self.effort_estimate,
            "suggestion": self.suggestion,
        }


@dataclass
class DebtReport:
    """Technical debt analysis report."""
    items: list[DebtItem] = field(default_factory=list)
    total_files_analyzed: int = 0
    total_lines_analyzed: int = 0
    analysis_timestamp: str = ""

    @property
    def total_items(self) -> int:
        """Get total debt items."""
        return len(self.items)

    @property
    def critical_count(self) -> int:
        """Get count of critical items."""
        return sum(1 for i in self.items if i.severity == DebtSeverity.CRITICAL)

    @property
    def high_count(self) -> int:
        """Get count of high severity items."""
        return sum(1 for i in self.items if i.severity == DebtSeverity.HIGH)

    def get_by_category(self, category: DebtCategory) -> list[DebtItem]:
        """Get items by category."""
        return [i for i in self.items if i.category == category]

    def get_by_severity(self, severity: DebtSeverity) -> list[DebtItem]:
        """Get items by severity."""
        return [i for i in self.items if i.severity == severity]

    def add_item(self, item: DebtItem) -> None:
        """Add a debt item to the report."""
        self.items.append(item)


@dataclass
class DebtConfig:
    """Configuration for debt analysis."""
    max_complexity: int = 10
    max_function_length: int = 50
    todo_patterns: list[str] = field(default_factory=lambda: [
        r"TODO", r"FIXME", r"HACK", r"XXX", r"BUG"
    ])
    exclude_patterns: list[str] = field(default_factory=lambda: [
        ".git", "__pycache__", ".venv", "node_modules"
    ])


class TechDebtAnalyzer:
    """Analyzes technical debt in a codebase."""

    def __init__(self, config: Optional[DebtConfig] = None):
        """Initialize analyzer.

        Args:
            config: Analysis configuration.
        """
        self.config = config or DebtConfig()

    def _find_files(self, path: Path, extensions: list[str]) -> list[Path]:
        """Find files with given extensions."""
        files = []
        for ext in extensions:
            for f in path.glob(f"**/*{ext}"):
                if not any(p in str(f) for p in self.config.exclude_patterns):
                    files.append(f)
        return files

    def analyze_todos(self, path: str) -> list[DebtItem]:
        """Find TODO/FIXME comments in code.

        Args:
            path: Directory to analyze.

        Returns:
            List of debt items for TODOs found.
        """
        items = []
        target_path = Path(path)

        if not target_path.exists():
            return items

        # Find all source files
        files = self._find_files(target_path, [".py", ".ts", ".tsx", ".js", ".jsx"])

        combined_pattern = "|".join(self.config.todo_patterns)
        regex = re.compile(rf"#.*({combined_pattern})[\s:]*(.+)?", re.IGNORECASE)

        for file_path in files:
            try:
                content = file_path.read_text()
                for i, line in enumerate(content.split("\n"), 1):
                    match = regex.search(line)
                    if match:
                        keyword = match.group(1).upper()
                        message = match.group(2) or "No description"

                        # Determine severity based on keyword
                        if keyword in ["FIXME", "BUG"]:
                            severity = DebtSeverity.HIGH
                        elif keyword == "HACK":
                            severity = DebtSeverity.MEDIUM
                        else:
                            severity = DebtSeverity.LOW

                        items.append(DebtItem(
                            category=DebtCategory.TODOS,
                            severity=severity,
                            file_path=str(file_path),
                            line=i,
                            description=f"{keyword}: {message.strip()}",
                            effort_estimate="30m",
                        ))
            except Exception as e:
                logger.warning(f"Failed to analyze {file_path}: {e}")

        return items

    def analyze_complexity(self, path: str) -> list[DebtItem]:
        """Analyze code complexity.

        Args:
            path: Directory to analyze.

        Returns:
            List of debt items for complex code.
        """
        items = []
        target_path = Path(path)

        if not target_path.exists():
            return items

        # Use radon for Python complexity
        try:
            result = subprocess.run(
                ["radon", "cc", str(target_path), "-j"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)

                for file_path, functions in data.items():
                    for func in functions:
                        complexity = func.get("complexity", 0)
                        if complexity > self.config.max_complexity:
                            severity = (
                                DebtSeverity.CRITICAL if complexity > 20
                                else DebtSeverity.HIGH if complexity > 15
                                else DebtSeverity.MEDIUM
                            )
                            items.append(DebtItem(
                                category=DebtCategory.CODE_COMPLEXITY,
                                severity=severity,
                                file_path=file_path,
                                line=func.get("lineno"),
                                description=(
                                    f"Function '{func.get('name')}' has complexity "
                                    f"{complexity} (max: {self.config.max_complexity})"
                                ),
                                effort_estimate="2h",
                                suggestion="Consider refactoring into smaller functions",
                            ))
        except Exception as e:
            logger.warning(f"Complexity analysis failed: {e}")

        return items

    def analyze_missing_types(self, path: str) -> list[DebtItem]:
        """Find functions missing type hints.

        Args:
            path: Directory to analyze.

        Returns:
            List of debt items for missing types.
        """
        items = []
        target_path = Path(path)

        if not target_path.exists():
            return items

        # Use mypy to find missing types
        try:
            result = subprocess.run(
                ["mypy", str(target_path), "--ignore-missing-imports", "--show-error-codes"],
                capture_output=True,
                text=True
            )

            for line in result.stdout.split("\n"):
                if "error:" in line and ("Missing return type" in line or "Function is missing" in line):
                    parts = line.split(":")
                    if len(parts) >= 3:
                        items.append(DebtItem(
                            category=DebtCategory.MISSING_TYPES,
                            severity=DebtSeverity.LOW,
                            file_path=parts[0],
                            line=int(parts[1]) if parts[1].isdigit() else None,
                            description=parts[-1].strip(),
                            effort_estimate="15m",
                            suggestion="Add type annotations",
                        ))
        except Exception as e:
            logger.warning(f"Type analysis failed: {e}")

        return items

    def analyze_codebase(self, path: str) -> DebtReport:
        """Run full technical debt analysis.

        Args:
            path: Directory to analyze.

        Returns:
            Complete DebtReport.
        """
        report = DebtReport()
        target_path = Path(path)

        if not target_path.exists():
            return report

        from datetime import datetime
        report.analysis_timestamp = datetime.now().isoformat()

        # Count files and lines
        all_files = self._find_files(target_path, [".py", ".ts", ".tsx", ".js", ".jsx"])
        report.total_files_analyzed = len(all_files)

        for f in all_files:
            try:
                report.total_lines_analyzed += len(f.read_text().split("\n"))
            except Exception:
                pass

        # Run all analyzers
        logger.info("Analyzing TODOs...")
        for item in self.analyze_todos(path):
            report.add_item(item)

        logger.info("Analyzing complexity...")
        for item in self.analyze_complexity(path):
            report.add_item(item)

        logger.info("Analyzing type coverage...")
        for item in self.analyze_missing_types(path):
            report.add_item(item)

        return report


def calculate_debt_score(report: DebtReport) -> float:
    """Calculate overall technical debt score.

    Score is 0-100 where:
    - 100 = No debt
    - 0 = Critical debt level

    Args:
        report: DebtReport to score.

    Returns:
        Score from 0 to 100.
    """
    if report.total_files_analyzed == 0:
        return 100.0

    # Base score
    score = 100.0

    # Deduct based on severity
    score -= report.critical_count * 10
    score -= report.high_count * 5
    score -= sum(1 for i in report.items if i.severity == DebtSeverity.MEDIUM) * 2
    score -= sum(1 for i in report.items if i.severity == DebtSeverity.LOW) * 0.5

    # Normalize based on file count
    items_per_file = report.total_items / report.total_files_analyzed
    if items_per_file > 5:
        score -= (items_per_file - 5) * 2

    return max(0.0, min(100.0, score))
