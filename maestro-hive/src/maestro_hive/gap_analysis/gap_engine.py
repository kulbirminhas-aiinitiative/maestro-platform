"""
Gap Engine for External Project Gap Analysis.

Core engine that orchestrates scanning, analysis, and recommendation generation.

EPIC: MD-3022
Child Task: MD-2922
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from .external_analyzer import (
    ExternalGapAnalyzer as GapAnalyzer,
    GapCategory,
    GapSeverity,
    GapAnalysisResult as AnalysisReport,
    create_gap_analyzer,
)
from .external_scanner import (
    ExternalProjectScanner,
    ScanResult,
    create_external_scanner,
)
from .repo_manager import RepoManager, RepoInfo, CloneResult, create_repo_manager
from .vision_analyzer import (
    VisionAnalyzer,
    VisionAnalysisResult,
    CodeQuality,
    create_vision_analyzer,
)

logger = logging.getLogger(__name__)


class EngineStatus(Enum):
    """Status of the gap engine."""
    IDLE = "idle"
    CLONING = "cloning"
    SCANNING = "scanning"
    ANALYZING = "analyzing"
    COMPLETE = "complete"
    ERROR = "error"


class RecommendationPriority(Enum):
    """Priority levels for recommendations."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


@dataclass
class Recommendation:
    """A single improvement recommendation."""
    id: str
    title: str
    description: str
    priority: RecommendationPriority
    category: str
    effort_estimate: str  # "low", "medium", "high"
    impact_estimate: str  # "low", "medium", "high"
    affected_files: List[str] = field(default_factory=list)
    action_items: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority.value,
            "category": self.category,
            "effort_estimate": self.effort_estimate,
            "impact_estimate": self.impact_estimate,
            "affected_files": self.affected_files[:10],
            "action_items": self.action_items,
        }


@dataclass
class HealthScore:
    """Project health score breakdown."""
    overall: float  # 0-100
    code_quality: float
    architecture: float
    testing: float
    documentation: float
    security: float
    maintainability: float
    grade: str  # A, B, C, D, F

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall": self.overall,
            "code_quality": self.code_quality,
            "architecture": self.architecture,
            "testing": self.testing,
            "documentation": self.documentation,
            "security": self.security,
            "maintainability": self.maintainability,
            "grade": self.grade,
        }


@dataclass
class GapEngineResult:
    """Complete result from gap engine analysis."""
    project_url: str
    project_path: str
    status: EngineStatus
    started_at: datetime
    completed_at: Optional[datetime]
    duration_seconds: float

    # Sub-results
    repo_info: Optional[RepoInfo]
    scan_result: Optional[ScanResult]
    vision_result: Optional[VisionAnalysisResult]
    gap_report: Optional[AnalysisReport]

    # Aggregated results
    health_score: Optional[HealthScore]
    recommendations: List[Recommendation]
    summary: str

    # Metadata
    files_analyzed: int
    gaps_found: int
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_url": self.project_url,
            "project_path": self.project_path,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "repo_info": self.repo_info.to_dict() if self.repo_info else None,
            "scan_result": self.scan_result.to_dict() if self.scan_result else None,
            "vision_result": self.vision_result.to_dict() if self.vision_result else None,
            "gap_report": self.gap_report.to_dict() if self.gap_report else None,
            "health_score": self.health_score.to_dict() if self.health_score else None,
            "recommendations": [r.to_dict() for r in self.recommendations],
            "summary": self.summary,
            "files_analyzed": self.files_analyzed,
            "gaps_found": self.gaps_found,
            "error": self.error,
        }


@dataclass
class GapEngineConfig:
    """Configuration for the gap engine."""
    enable_repo_cloning: bool = True
    enable_vision_analysis: bool = True
    enable_gap_analysis: bool = True
    max_files: int = 1000
    timeout_seconds: int = 600
    generate_recommendations: bool = True
    min_recommendation_priority: RecommendationPriority = RecommendationPriority.LOW


class GapEngine:
    """
    Core engine for external project gap analysis.

    Orchestrates:
    1. Repository cloning/access
    2. Project scanning
    3. Vision analysis (patterns, quality, architecture)
    4. Gap identification
    5. Recommendation generation
    6. Health scoring
    """

    def __init__(
        self,
        config: Optional[GapEngineConfig] = None,
        repo_manager: Optional[RepoManager] = None,
        scanner: Optional[ExternalProjectScanner] = None,
        vision_analyzer: Optional[VisionAnalyzer] = None,
        gap_analyzer: Optional[GapAnalyzer] = None,
    ):
        """
        Initialize the gap engine.

        Args:
            config: Engine configuration
            repo_manager: Repository manager (created if not provided)
            scanner: Project scanner (created if not provided)
            vision_analyzer: Vision analyzer (created if not provided)
            gap_analyzer: Gap analyzer (created if not provided)
        """
        self.config = config or GapEngineConfig()
        self.repo_manager = repo_manager or create_repo_manager()
        self.scanner = scanner or create_external_scanner()
        self.vision_analyzer = vision_analyzer or create_vision_analyzer()
        self.gap_analyzer = gap_analyzer or create_gap_analyzer()
        self._status = EngineStatus.IDLE

    @property
    def status(self) -> EngineStatus:
        """Get current engine status."""
        return self._status

    def analyze(
        self,
        project_url: str,
        branch: str = "main",
        local_path: Optional[str] = None,
    ) -> GapEngineResult:
        """
        Perform complete gap analysis on a project.

        Args:
            project_url: Repository URL or local path
            branch: Branch to analyze (for remote repos)
            local_path: Override local path (skip cloning)

        Returns:
            GapEngineResult with complete analysis
        """
        started_at = datetime.now()
        repo_info = None
        scan_result = None
        vision_result = None
        gap_report = None
        error = None
        project_path = local_path or ""

        try:
            # Step 1: Clone/access repository
            if not local_path and self.config.enable_repo_cloning:
                self._status = EngineStatus.CLONING
                logger.info(f"Cloning repository: {project_url}")

                clone_result = self.repo_manager.clone(project_url, branch)
                if not clone_result.success:
                    raise RuntimeError(f"Failed to clone: {clone_result.error}")

                repo_info = clone_result.repo_info
                project_path = repo_info.local_path
            elif local_path:
                project_path = local_path

            if not project_path:
                raise ValueError("No project path available")

            # Step 2: Scan project
            self._status = EngineStatus.SCANNING
            logger.info(f"Scanning project: {project_path}")
            scan_result = self.scanner.scan(project_path)

            # Step 3: Vision analysis
            if self.config.enable_vision_analysis:
                self._status = EngineStatus.ANALYZING
                logger.info("Running vision analysis")
                vision_result = self.vision_analyzer.analyze(project_path)

            # Step 4: Gap analysis
            if self.config.enable_gap_analysis:
                logger.info("Running gap analysis")
                gap_report = self.gap_analyzer.analyze(scan_result)

            self._status = EngineStatus.COMPLETE

        except Exception as e:
            self._status = EngineStatus.ERROR
            error = str(e)
            logger.error(f"Gap engine error: {e}")

        # Calculate completion time
        completed_at = datetime.now()
        duration = (completed_at - started_at).total_seconds()

        # Generate health score
        health_score = self._calculate_health_score(
            scan_result, vision_result, gap_report
        )

        # Generate recommendations
        recommendations = []
        if self.config.generate_recommendations:
            recommendations = self._generate_recommendations(
                scan_result, vision_result, gap_report
            )

        # Generate summary
        summary = self._generate_summary(
            scan_result, vision_result, gap_report, health_score
        )

        # Count files and gaps
        files_analyzed = scan_result.total_files if scan_result else 0
        gaps_found = len(gap_report.gaps) if gap_report else 0

        return GapEngineResult(
            project_url=project_url,
            project_path=project_path,
            status=self._status,
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=duration,
            repo_info=repo_info,
            scan_result=scan_result,
            vision_result=vision_result,
            gap_report=gap_report,
            health_score=health_score,
            recommendations=recommendations,
            summary=summary,
            files_analyzed=files_analyzed,
            gaps_found=gaps_found,
            error=error,
        )

    def _calculate_health_score(
        self,
        scan_result: Optional[ScanResult],
        vision_result: Optional[VisionAnalysisResult],
        gap_report: Optional[AnalysisReport],
    ) -> Optional[HealthScore]:
        """Calculate overall project health score."""
        if not scan_result:
            return None

        # Base scores
        code_quality = 70.0
        architecture = 70.0
        testing = 50.0
        documentation = 50.0
        security = 70.0
        maintainability = 70.0

        # Adjust from vision analysis
        if vision_result:
            code_quality = vision_result.overall_score

            if vision_result.architecture:
                architecture = (
                    vision_result.architecture.modularity_score * 0.4 +
                    vision_result.architecture.cohesion_score * 0.3 +
                    vision_result.architecture.coupling_score * 0.3
                )

            # Extract from quality indicators
            for indicator in vision_result.quality_indicators:
                if "test" in indicator.name.lower():
                    testing = indicator.score
                elif "doc" in indicator.name.lower():
                    documentation = indicator.score
                elif "error" in indicator.name.lower():
                    security = indicator.score

        # Adjust from gap report
        if gap_report:
            # Reduce scores based on gaps
            critical_gaps = sum(
                1 for g in gap_report.gaps if g.severity == GapSeverity.CRITICAL
            )
            high_gaps = sum(
                1 for g in gap_report.gaps if g.severity == GapSeverity.HIGH
            )

            penalty = critical_gaps * 10 + high_gaps * 5
            code_quality = max(0, code_quality - penalty)
            security = max(0, security - penalty * 0.5)

        # Calculate maintainability
        maintainability = (code_quality * 0.4 + testing * 0.3 + documentation * 0.3)

        # Calculate overall
        overall = (
            code_quality * 0.25 +
            architecture * 0.15 +
            testing * 0.20 +
            documentation * 0.15 +
            security * 0.15 +
            maintainability * 0.10
        )

        # Determine grade
        if overall >= 90:
            grade = "A"
        elif overall >= 80:
            grade = "B"
        elif overall >= 70:
            grade = "C"
        elif overall >= 60:
            grade = "D"
        else:
            grade = "F"

        return HealthScore(
            overall=round(overall, 1),
            code_quality=round(code_quality, 1),
            architecture=round(architecture, 1),
            testing=round(testing, 1),
            documentation=round(documentation, 1),
            security=round(security, 1),
            maintainability=round(maintainability, 1),
            grade=grade,
        )

    def _generate_recommendations(
        self,
        scan_result: Optional[ScanResult],
        vision_result: Optional[VisionAnalysisResult],
        gap_report: Optional[AnalysisReport],
    ) -> List[Recommendation]:
        """Generate prioritized recommendations."""
        recommendations = []
        rec_id = 0

        # From gap report
        if gap_report:
            for gap in gap_report.gaps[:20]:  # Limit to top 20
                rec_id += 1
                priority = self._severity_to_priority(gap.severity)

                if priority.value >= self.config.min_recommendation_priority.value:
                    recommendations.append(Recommendation(
                        id=f"GAP-{rec_id:03d}",
                        title=f"Fix: {gap.title}",
                        description=gap.description,
                        priority=priority,
                        category=gap.category.value,
                        effort_estimate=self._estimate_effort(gap.severity),
                        impact_estimate=self._estimate_impact(gap.severity),
                        affected_files=gap.affected_files[:5],
                        action_items=gap.remediation_steps[:5],
                    ))

        # From vision analysis
        if vision_result:
            for indicator in vision_result.quality_indicators:
                if indicator.score < 60 and indicator.recommendations:
                    rec_id += 1
                    priority = (
                        RecommendationPriority.HIGH if indicator.score < 40
                        else RecommendationPriority.MEDIUM
                    )

                    recommendations.append(Recommendation(
                        id=f"QUAL-{rec_id:03d}",
                        title=f"Improve: {indicator.name}",
                        description=indicator.description,
                        priority=priority,
                        category="quality",
                        effort_estimate="medium",
                        impact_estimate="medium",
                        action_items=indicator.recommendations,
                    ))

            # Architecture recommendations
            if vision_result.architecture:
                for rec_text in vision_result.architecture.recommendations[:3]:
                    rec_id += 1
                    recommendations.append(Recommendation(
                        id=f"ARCH-{rec_id:03d}",
                        title="Architecture Improvement",
                        description=rec_text,
                        priority=RecommendationPriority.MEDIUM,
                        category="architecture",
                        effort_estimate="high",
                        impact_estimate="high",
                        action_items=[rec_text],
                    ))

        # Sort by priority
        priority_order = {
            RecommendationPriority.CRITICAL: 0,
            RecommendationPriority.HIGH: 1,
            RecommendationPriority.MEDIUM: 2,
            RecommendationPriority.LOW: 3,
            RecommendationPriority.INFORMATIONAL: 4,
        }
        recommendations.sort(key=lambda r: priority_order[r.priority])

        return recommendations[:30]  # Limit total recommendations

    def _severity_to_priority(self, severity: GapSeverity) -> RecommendationPriority:
        """Convert gap severity to recommendation priority."""
        mapping = {
            GapSeverity.CRITICAL: RecommendationPriority.CRITICAL,
            GapSeverity.HIGH: RecommendationPriority.HIGH,
            GapSeverity.MEDIUM: RecommendationPriority.MEDIUM,
            GapSeverity.LOW: RecommendationPriority.LOW,
        }
        return mapping.get(severity, RecommendationPriority.LOW)

    def _estimate_effort(self, severity: GapSeverity) -> str:
        """Estimate effort to fix based on severity."""
        if severity in [GapSeverity.CRITICAL, GapSeverity.HIGH]:
            return "high"
        elif severity == GapSeverity.MEDIUM:
            return "medium"
        return "low"

    def _estimate_impact(self, severity: GapSeverity) -> str:
        """Estimate impact of fix based on severity."""
        if severity == GapSeverity.CRITICAL:
            return "high"
        elif severity == GapSeverity.HIGH:
            return "high"
        elif severity == GapSeverity.MEDIUM:
            return "medium"
        return "low"

    def _generate_summary(
        self,
        scan_result: Optional[ScanResult],
        vision_result: Optional[VisionAnalysisResult],
        gap_report: Optional[AnalysisReport],
        health_score: Optional[HealthScore],
    ) -> str:
        """Generate human-readable summary."""
        parts = []

        if health_score:
            parts.append(
                f"Overall Health: {health_score.grade} ({health_score.overall}/100)"
            )

        if scan_result:
            parts.append(f"Files analyzed: {scan_result.total_files}")
            if scan_result.languages:
                langs = ", ".join(scan_result.languages[:3])
                parts.append(f"Languages: {langs}")

        if vision_result:
            parts.append(f"Code quality: {vision_result.overall_quality.value}")
            if vision_result.patterns:
                patterns = [p.pattern.value for p in vision_result.patterns[:2]]
                parts.append(f"Patterns: {', '.join(patterns)}")

        if gap_report:
            critical = sum(
                1 for g in gap_report.gaps if g.severity == GapSeverity.CRITICAL
            )
            high = sum(
                1 for g in gap_report.gaps if g.severity == GapSeverity.HIGH
            )
            parts.append(f"Gaps found: {len(gap_report.gaps)} ({critical} critical, {high} high)")

        return " | ".join(parts) if parts else "Analysis incomplete"


def create_gap_engine(config: Optional[Dict[str, Any]] = None) -> GapEngine:
    """
    Factory function to create a GapEngine instance.

    Args:
        config: Optional configuration dictionary

    Returns:
        Configured GapEngine instance
    """
    if config:
        engine_config = GapEngineConfig(
            enable_repo_cloning=config.get("enable_repo_cloning", True),
            enable_vision_analysis=config.get("enable_vision_analysis", True),
            enable_gap_analysis=config.get("enable_gap_analysis", True),
            max_files=config.get("max_files", 1000),
            timeout_seconds=config.get("timeout_seconds", 600),
            generate_recommendations=config.get("generate_recommendations", True),
        )
    else:
        engine_config = GapEngineConfig()

    return GapEngine(engine_config)
