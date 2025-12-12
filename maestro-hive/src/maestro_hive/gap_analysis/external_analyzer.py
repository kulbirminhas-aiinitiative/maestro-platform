"""
ExternalGapAnalyzer: Gap Analysis Engine for External Projects

This module implements gap analysis capabilities for comparing external
codebases against best practices and identifying improvement opportunities.

EPIC: MD-3022 - External Project Gap Analysis Scanner

Features:
- Best practices comparison
- Code quality gap detection
- Security vulnerability identification
- Documentation coverage analysis
- Test coverage gap detection
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from pathlib import Path
from enum import Enum
import logging
import re

from .external_scanner import (
    ScanResult,
    FileAnalysis,
    ProjectMetrics,
    FileType,
    ScanStatus,
)


logger = logging.getLogger(__name__)


class GapSeverity(Enum):
    """Severity levels for identified gaps"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class GapCategory(Enum):
    """Categories of gaps that can be identified"""
    SECURITY = "security"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    CODE_QUALITY = "code_quality"
    ARCHITECTURE = "architecture"
    PERFORMANCE = "performance"
    MAINTAINABILITY = "maintainability"
    BEST_PRACTICES = "best_practices"


@dataclass
class GapSuggestion:
    """A suggested fix for an identified gap"""
    description: str
    effort: str = "low"  # low, medium, high
    priority: int = 0


@dataclass
class Gap:
    """A single identified gap in the project"""
    gap_id: str
    category: GapCategory
    severity: GapSeverity
    title: str
    description: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    code_snippet: Optional[str] = None
    suggestions: List[GapSuggestion] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gap_id": self.gap_id,
            "category": self.category.value,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "code_snippet": self.code_snippet,
            "suggestions": [
                {"description": s.description, "effort": s.effort, "priority": s.priority}
                for s in self.suggestions
            ],
            "metadata": self.metadata,
        }


@dataclass
class AnalyzerConfig:
    """Configuration for the gap analyzer"""
    severity_threshold: GapSeverity = GapSeverity.LOW
    include_suggestions: bool = True
    max_suggestions_per_gap: int = 3
    best_practices_file: Optional[str] = None
    enabled_categories: List[GapCategory] = field(
        default_factory=lambda: list(GapCategory)
    )
    min_test_coverage: float = 80.0
    min_doc_coverage: float = 50.0
    max_complexity_threshold: float = 10.0


@dataclass
class AnalysisScore:
    """Scores for different analysis dimensions"""
    overall: float = 0.0
    security: float = 0.0
    documentation: float = 0.0
    testing: float = 0.0
    code_quality: float = 0.0
    architecture: float = 0.0
    maintainability: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        return {
            "overall": self.overall,
            "security": self.security,
            "documentation": self.documentation,
            "testing": self.testing,
            "code_quality": self.code_quality,
            "architecture": self.architecture,
            "maintainability": self.maintainability,
        }


@dataclass
class GapAnalysisResult:
    """Complete results of gap analysis"""
    project_name: str
    analysis_timestamp: datetime
    scan_result: ScanResult
    gaps: List[Gap] = field(default_factory=list)
    scores: Optional[AnalysisScore] = None
    summary: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_name": self.project_name,
            "analysis_timestamp": self.analysis_timestamp.isoformat(),
            "scan_result": self.scan_result.to_dict(),
            "gaps": [g.to_dict() for g in self.gaps],
            "scores": self.scores.to_dict() if self.scores else None,
            "summary": self.summary,
            "recommendations": self.recommendations,
        }

    @property
    def gaps_by_severity(self) -> Dict[str, List[Gap]]:
        """Group gaps by severity level"""
        result: Dict[str, List[Gap]] = {}
        for gap in self.gaps:
            sev = gap.severity.value
            if sev not in result:
                result[sev] = []
            result[sev].append(gap)
        return result

    @property
    def gaps_by_category(self) -> Dict[str, List[Gap]]:
        """Group gaps by category"""
        result: Dict[str, List[Gap]] = {}
        for gap in self.gaps:
            cat = gap.category.value
            if cat not in result:
                result[cat] = []
            result[cat].append(gap)
        return result


class BestPracticesChecker:
    """Checks project against best practices"""

    def __init__(self):
        self._security_patterns = [
            (re.compile(r'password\s*=\s*["\'][^"\']+["\']', re.I), "Hardcoded password"),
            (re.compile(r'api[_-]?key\s*=\s*["\'][^"\']+["\']', re.I), "Hardcoded API key"),
            (re.compile(r'secret\s*=\s*["\'][^"\']+["\']', re.I), "Hardcoded secret"),
            (re.compile(r'eval\s*\('), "Use of eval()"),
            (re.compile(r'exec\s*\('), "Use of exec()"),
        ]

        self._code_smell_patterns = [
            (re.compile(r'#\s*TODO', re.I), "TODO comment found"),
            (re.compile(r'#\s*FIXME', re.I), "FIXME comment found"),
            (re.compile(r'#\s*HACK', re.I), "HACK comment found"),
            (re.compile(r'#\s*XXX', re.I), "XXX comment found"),
        ]

    def check_security(self, content: str, file_path: str) -> List[Gap]:
        """Check file content for security issues"""
        gaps = []
        gap_count = 0

        for pattern, issue_name in self._security_patterns:
            matches = pattern.finditer(content)
            for match in matches:
                gap_count += 1
                line_num = content[:match.start()].count('\n') + 1
                gaps.append(Gap(
                    gap_id=f"SEC-{gap_count:04d}",
                    category=GapCategory.SECURITY,
                    severity=GapSeverity.HIGH,
                    title=f"Security Issue: {issue_name}",
                    description=f"Potential security vulnerability detected: {issue_name}",
                    file_path=file_path,
                    line_number=line_num,
                    code_snippet=match.group()[:100],
                    suggestions=[
                        GapSuggestion(
                            description="Move sensitive values to environment variables",
                            effort="low",
                            priority=1
                        ),
                        GapSuggestion(
                            description="Use a secrets management system",
                            effort="medium",
                            priority=2
                        ),
                    ]
                ))

        return gaps

    def check_code_quality(self, content: str, file_path: str) -> List[Gap]:
        """Check file content for code quality issues"""
        gaps = []
        gap_count = 0

        for pattern, issue_name in self._code_smell_patterns:
            matches = pattern.finditer(content)
            for match in matches:
                gap_count += 1
                line_num = content[:match.start()].count('\n') + 1
                gaps.append(Gap(
                    gap_id=f"CQ-{gap_count:04d}",
                    category=GapCategory.CODE_QUALITY,
                    severity=GapSeverity.LOW,
                    title=f"Code Quality: {issue_name}",
                    description=f"Code quality marker found: {issue_name}",
                    file_path=file_path,
                    line_number=line_num,
                    suggestions=[
                        GapSuggestion(
                            description="Address the TODO/FIXME item or create a ticket",
                            effort="medium",
                            priority=1
                        ),
                    ]
                ))

        return gaps


class ExternalGapAnalyzer:
    """
    Gap analyzer for external projects.

    Compares scan results against best practices and identifies
    improvement opportunities.
    """

    def __init__(self, config: Optional[AnalyzerConfig] = None):
        self.config = config or AnalyzerConfig()
        self._best_practices = BestPracticesChecker()
        self._gap_counter = 0
        logger.info("ExternalGapAnalyzer initialized")

    async def analyze(self, scan_result: ScanResult) -> GapAnalysisResult:
        """
        Analyze a scan result and identify gaps.

        Args:
            scan_result: Result from ExternalProjectScanner

        Returns:
            GapAnalysisResult containing all identified gaps
        """
        logger.info(f"Starting gap analysis for: {scan_result.project_name}")

        result = GapAnalysisResult(
            project_name=scan_result.project_name,
            analysis_timestamp=datetime.now(),
            scan_result=scan_result,
        )

        if scan_result.status == ScanStatus.FAILED:
            logger.error("Cannot analyze failed scan")
            return result

        # Analyze each file
        for file_analysis in scan_result.file_analyses:
            gaps = self._analyze_file(file_analysis)
            result.gaps.extend(gaps)

        # Analyze project-level gaps
        if scan_result.metrics:
            project_gaps = self._analyze_project_metrics(scan_result.metrics)
            result.gaps.extend(project_gaps)

        # Filter by severity threshold
        result.gaps = self._filter_gaps(result.gaps)

        # Calculate scores
        result.scores = self._calculate_scores(scan_result, result.gaps)

        # Generate summary and recommendations
        result.summary = self._generate_summary(result)
        result.recommendations = self._generate_recommendations(result)

        logger.info(f"Analysis complete: {len(result.gaps)} gaps identified")

        return result

    def _analyze_file(self, file_analysis: FileAnalysis) -> List[Gap]:
        """Analyze a single file for gaps"""
        gaps = []

        # Skip non-code files for detailed analysis
        if file_analysis.file_type in [FileType.OTHER, FileType.JSON, FileType.YAML]:
            return gaps

        # Read file content for detailed analysis
        try:
            with open(file_analysis.path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception as e:
            logger.warning(f"Cannot read file for analysis: {file_analysis.path}: {e}")
            return gaps

        # Security checks
        if GapCategory.SECURITY in self.config.enabled_categories:
            security_gaps = self._best_practices.check_security(
                content, file_analysis.relative_path
            )
            gaps.extend(security_gaps)

        # Code quality checks
        if GapCategory.CODE_QUALITY in self.config.enabled_categories:
            quality_gaps = self._best_practices.check_code_quality(
                content, file_analysis.relative_path
            )
            gaps.extend(quality_gaps)

        # Complexity check
        if file_analysis.metrics.complexity_score > self.config.max_complexity_threshold:
            self._gap_counter += 1
            gaps.append(Gap(
                gap_id=f"MAINT-{self._gap_counter:04d}",
                category=GapCategory.MAINTAINABILITY,
                severity=GapSeverity.MEDIUM,
                title="High Complexity Score",
                description=(
                    f"File has complexity score of {file_analysis.metrics.complexity_score:.2f}, "
                    f"exceeding threshold of {self.config.max_complexity_threshold}"
                ),
                file_path=file_analysis.relative_path,
                suggestions=[
                    GapSuggestion(
                        description="Refactor complex functions into smaller units",
                        effort="high",
                        priority=1
                    ),
                    GapSuggestion(
                        description="Extract common logic into helper functions",
                        effort="medium",
                        priority=2
                    ),
                ]
            ))

        # Documentation check for Python files
        if file_analysis.file_type == FileType.PYTHON:
            if not file_analysis.metrics.has_docstrings:
                self._gap_counter += 1
                gaps.append(Gap(
                    gap_id=f"DOC-{self._gap_counter:04d}",
                    category=GapCategory.DOCUMENTATION,
                    severity=GapSeverity.LOW,
                    title="Missing Docstrings",
                    description="Python file lacks docstrings for functions/classes",
                    file_path=file_analysis.relative_path,
                    suggestions=[
                        GapSuggestion(
                            description="Add docstrings to all public functions and classes",
                            effort="medium",
                            priority=1
                        ),
                    ]
                ))

            # Type hints check
            if not file_analysis.metrics.has_type_hints:
                self._gap_counter += 1
                gaps.append(Gap(
                    gap_id=f"BP-{self._gap_counter:04d}",
                    category=GapCategory.BEST_PRACTICES,
                    severity=GapSeverity.INFO,
                    title="Missing Type Hints",
                    description="Python file lacks type annotations",
                    file_path=file_analysis.relative_path,
                    suggestions=[
                        GapSuggestion(
                            description="Add type hints to function signatures",
                            effort="low",
                            priority=1
                        ),
                    ]
                ))

        return gaps

    def _analyze_project_metrics(self, metrics: ProjectMetrics) -> List[Gap]:
        """Analyze project-level metrics for gaps"""
        gaps = []

        # Test coverage check
        if not metrics.has_tests:
            self._gap_counter += 1
            gaps.append(Gap(
                gap_id=f"TEST-{self._gap_counter:04d}",
                category=GapCategory.TESTING,
                severity=GapSeverity.HIGH,
                title="No Tests Found",
                description="Project appears to have no test files or test directory",
                suggestions=[
                    GapSuggestion(
                        description="Add unit tests for core functionality",
                        effort="high",
                        priority=1
                    ),
                    GapSuggestion(
                        description="Set up a testing framework (pytest, jest, etc.)",
                        effort="medium",
                        priority=1
                    ),
                ]
            ))

        # Documentation check
        if not metrics.has_docs:
            self._gap_counter += 1
            gaps.append(Gap(
                gap_id=f"DOC-{self._gap_counter:04d}",
                category=GapCategory.DOCUMENTATION,
                severity=GapSeverity.MEDIUM,
                title="No Documentation Found",
                description="Project lacks a docs directory or README file",
                suggestions=[
                    GapSuggestion(
                        description="Add a README.md with project overview",
                        effort="low",
                        priority=1
                    ),
                    GapSuggestion(
                        description="Create a docs/ directory with usage guides",
                        effort="medium",
                        priority=2
                    ),
                ]
            ))

        # CI/CD check
        if not metrics.has_ci:
            self._gap_counter += 1
            gaps.append(Gap(
                gap_id=f"ARCH-{self._gap_counter:04d}",
                category=GapCategory.ARCHITECTURE,
                severity=GapSeverity.MEDIUM,
                title="No CI/CD Configuration",
                description="Project lacks continuous integration setup",
                suggestions=[
                    GapSuggestion(
                        description="Add GitHub Actions workflow for testing",
                        effort="low",
                        priority=1
                    ),
                    GapSuggestion(
                        description="Configure automated deployments",
                        effort="medium",
                        priority=2
                    ),
                ]
            ))

        # Comment ratio check
        if metrics.code_lines > 0:
            comment_ratio = metrics.comment_lines / metrics.code_lines
            if comment_ratio < 0.05:  # Less than 5% comments
                self._gap_counter += 1
                gaps.append(Gap(
                    gap_id=f"DOC-{self._gap_counter:04d}",
                    category=GapCategory.DOCUMENTATION,
                    severity=GapSeverity.LOW,
                    title="Low Comment Ratio",
                    description=(
                        f"Code has only {comment_ratio:.1%} comments. "
                        "Consider adding more inline documentation."
                    ),
                    suggestions=[
                        GapSuggestion(
                            description="Add comments for complex logic",
                            effort="low",
                            priority=1
                        ),
                    ]
                ))

        return gaps

    def _filter_gaps(self, gaps: List[Gap]) -> List[Gap]:
        """Filter gaps based on configuration"""
        severity_order = [
            GapSeverity.INFO,
            GapSeverity.LOW,
            GapSeverity.MEDIUM,
            GapSeverity.HIGH,
            GapSeverity.CRITICAL,
        ]
        threshold_idx = severity_order.index(self.config.severity_threshold)

        filtered = []
        for gap in gaps:
            gap_idx = severity_order.index(gap.severity)
            if gap_idx >= threshold_idx:
                # Filter suggestions if needed
                if self.config.include_suggestions:
                    gap.suggestions = gap.suggestions[:self.config.max_suggestions_per_gap]
                else:
                    gap.suggestions = []
                filtered.append(gap)

        return filtered

    def _calculate_scores(
        self,
        scan_result: ScanResult,
        gaps: List[Gap]
    ) -> AnalysisScore:
        """Calculate analysis scores based on findings"""
        scores = AnalysisScore()

        # Base scores start at 100 and are reduced by gaps
        category_scores = {cat: 100.0 for cat in GapCategory}
        severity_penalties = {
            GapSeverity.CRITICAL: 20.0,
            GapSeverity.HIGH: 10.0,
            GapSeverity.MEDIUM: 5.0,
            GapSeverity.LOW: 2.0,
            GapSeverity.INFO: 0.5,
        }

        for gap in gaps:
            penalty = severity_penalties.get(gap.severity, 1.0)
            category_scores[gap.category] = max(
                0, category_scores[gap.category] - penalty
            )

        scores.security = category_scores[GapCategory.SECURITY]
        scores.documentation = (
            category_scores[GapCategory.DOCUMENTATION]
        )
        scores.testing = category_scores[GapCategory.TESTING]
        scores.code_quality = category_scores[GapCategory.CODE_QUALITY]
        scores.architecture = category_scores[GapCategory.ARCHITECTURE]
        scores.maintainability = category_scores[GapCategory.MAINTAINABILITY]

        # Overall is weighted average
        weights = {
            'security': 0.25,
            'documentation': 0.10,
            'testing': 0.20,
            'code_quality': 0.20,
            'architecture': 0.15,
            'maintainability': 0.10,
        }

        scores.overall = sum(
            getattr(scores, k) * v for k, v in weights.items()
        )

        return scores

    def _generate_summary(self, result: GapAnalysisResult) -> Dict[str, Any]:
        """Generate analysis summary"""
        gaps_by_sev = result.gaps_by_severity
        gaps_by_cat = result.gaps_by_category

        return {
            "total_gaps": len(result.gaps),
            "gaps_by_severity": {
                sev: len(gaps) for sev, gaps in gaps_by_sev.items()
            },
            "gaps_by_category": {
                cat: len(gaps) for cat, gaps in gaps_by_cat.items()
            },
            "critical_gaps": len(gaps_by_sev.get("critical", [])),
            "high_gaps": len(gaps_by_sev.get("high", [])),
            "files_analyzed": result.scan_result.files_scanned,
            "health_grade": self._calculate_grade(result.scores.overall if result.scores else 0),
        }

    def _calculate_grade(self, score: float) -> str:
        """Convert score to letter grade"""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"

    def _generate_recommendations(self, result: GapAnalysisResult) -> List[str]:
        """Generate prioritized recommendations"""
        recommendations = []

        gaps_by_sev = result.gaps_by_severity

        if gaps_by_sev.get("critical"):
            recommendations.append(
                f"URGENT: Address {len(gaps_by_sev['critical'])} critical issues immediately"
            )

        if gaps_by_sev.get("high"):
            recommendations.append(
                f"HIGH PRIORITY: Fix {len(gaps_by_sev['high'])} high-severity gaps"
            )

        # Category-specific recommendations
        gaps_by_cat = result.gaps_by_category

        if GapCategory.SECURITY.value in gaps_by_cat:
            recommendations.append(
                "Security: Review and remediate all security-related findings"
            )

        if GapCategory.TESTING.value in gaps_by_cat:
            recommendations.append(
                "Testing: Improve test coverage to ensure code reliability"
            )

        if GapCategory.DOCUMENTATION.value in gaps_by_cat:
            recommendations.append(
                "Documentation: Enhance inline docs and project documentation"
            )

        # General recommendations
        if result.scores and result.scores.overall < 70:
            recommendations.append(
                "General: Consider a dedicated code quality improvement sprint"
            )

        return recommendations


def create_gap_analyzer(config: Optional[AnalyzerConfig] = None) -> ExternalGapAnalyzer:
    """Factory function to create an ExternalGapAnalyzer instance"""
    return ExternalGapAnalyzer(config=config)
