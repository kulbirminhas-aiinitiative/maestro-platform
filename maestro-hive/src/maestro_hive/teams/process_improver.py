"""
ProcessImprover: Intelligent Workflow Optimization Engine

This module implements an AI-powered process improvement system that analyzes
team workflows and generates prioritized, actionable recommendations.

EPIC: MD-3015 - Autonomous Team Retrospective & Evaluation

Features:
- Workflow Analysis: Identifies bottlenecks and inefficiencies
- Impact-Effort Matrix: Prioritizes improvements by value vs cost
- Focused Recommendations: Maximum 3 high-priority per retrospective
- Category Coverage: Process, quality, communication, technical debt
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
import logging
import uuid


logger = logging.getLogger(__name__)


class ImprovementCategory(Enum):
    """Categories of process improvements"""
    PROCESS_EFFICIENCY = "process_efficiency"
    CODE_QUALITY = "code_quality"
    TEAM_COMMUNICATION = "team_communication"
    TECHNICAL_DEBT = "technical_debt"
    TESTING_PRACTICES = "testing_practices"
    DOCUMENTATION = "documentation"


class ImpactLevel(Enum):
    """Impact levels for improvements"""
    HIGH = "high"      # > 0.7
    MEDIUM = "medium"  # 0.4 - 0.7
    LOW = "low"        # < 0.4


class EffortLevel(Enum):
    """Effort levels for improvements"""
    HIGH = "high"      # > 0.7 (lots of work)
    MEDIUM = "medium"  # 0.4 - 0.7
    LOW = "low"        # < 0.4 (quick wins)


class PriorityQuadrant(Enum):
    """Impact-Effort matrix quadrants"""
    QUICK_WINS = "quick_wins"      # High impact, low effort - DO FIRST
    STRATEGIC = "strategic"         # High impact, high effort - PLAN
    FILL_INS = "fill_ins"          # Low impact, low effort - IF TIME
    AVOID = "avoid"                 # Low impact, high effort - SKIP


@dataclass
class Bottleneck:
    """Identified workflow bottleneck"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    severity: float = 0.0  # 0.0 to 1.0
    location: str = ""  # Where in the workflow
    detected_at: datetime = field(default_factory=datetime.utcnow)
    metrics_evidence: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "severity": self.severity,
            "location": self.location,
            "detected_at": self.detected_at.isoformat(),
            "metrics_evidence": self.metrics_evidence,
        }


@dataclass
class WorkflowData:
    """Data about team workflow"""
    team_id: str
    stages: List[str] = field(default_factory=list)
    avg_cycle_time: float = 0.0  # Average time through workflow (hours)
    stage_times: Dict[str, float] = field(default_factory=dict)
    handoff_count: int = 0
    rework_rate: float = 0.0


@dataclass
class WorkflowAnalysis:
    """Analysis of workflow patterns"""
    team_id: str
    analyzed_at: datetime = field(default_factory=datetime.utcnow)
    bottlenecks: List[Bottleneck] = field(default_factory=list)
    efficiency_score: float = 0.0  # 0.0 to 1.0
    cycle_time: float = 0.0
    recommendations: List[str] = field(default_factory=list)
    focus_areas: List[ImprovementCategory] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "team_id": self.team_id,
            "analyzed_at": self.analyzed_at.isoformat(),
            "bottlenecks": [b.to_dict() for b in self.bottlenecks],
            "efficiency_score": self.efficiency_score,
            "cycle_time": self.cycle_time,
            "recommendations": self.recommendations,
            "focus_areas": [f.value for f in self.focus_areas],
        }


@dataclass
class PrioritizedAction:
    """An improvement action with priority scoring"""
    improvement_id: str
    title: str
    description: str
    category: ImprovementCategory
    impact_score: float
    impact_level: ImpactLevel
    effort_score: float
    effort_level: EffortLevel
    priority_quadrant: PriorityQuadrant
    priority_rank: int
    confidence: float
    expected_benefit: str = ""
    implementation_steps: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "improvement_id": self.improvement_id,
            "title": self.title,
            "description": self.description,
            "category": self.category.value,
            "impact_score": self.impact_score,
            "impact_level": self.impact_level.value,
            "effort_score": self.effort_score,
            "effort_level": self.effort_level.value,
            "priority_quadrant": self.priority_quadrant.value,
            "priority_rank": self.priority_rank,
            "confidence": self.confidence,
            "expected_benefit": self.expected_benefit,
            "implementation_steps": self.implementation_steps,
        }


@dataclass
class ImproverConfig:
    """Configuration for the process improver"""
    max_suggestions: int = 5
    min_confidence: float = 0.7
    max_high_priority: int = 3  # Max high-priority recommendations per retrospective
    focus_areas: List[ImprovementCategory] = field(
        default_factory=lambda: [
            ImprovementCategory.PROCESS_EFFICIENCY,
            ImprovementCategory.CODE_QUALITY,
            ImprovementCategory.TEAM_COMMUNICATION,
            ImprovementCategory.TECHNICAL_DEBT,
        ]
    )


class ProcessImprover:
    """
    Intelligent Process Improvement Engine

    Analyzes team workflows and generates prioritized improvement
    recommendations using an impact-effort matrix.

    Example:
        >>> improver = ProcessImprover()
        >>> analysis = improver.analyze_workflow(metrics)
        >>> improvements = improver.suggest_improvements(metrics, assessment)
        >>> prioritized = improver.prioritize_actions(improvements)
    """

    def __init__(self, config: Optional[ImproverConfig] = None):
        """
        Initialize the ProcessImprover.

        Args:
            config: Configuration options
        """
        self.config = config or ImproverConfig()
        self._analysis_history: List[WorkflowAnalysis] = []

        logger.info("ProcessImprover initialized")

    def analyze_workflow(self, metrics: Any) -> WorkflowAnalysis:
        """
        Analyze team workflow patterns from metrics.

        Args:
            metrics: TeamMetrics with workflow data

        Returns:
            WorkflowAnalysis with bottlenecks and efficiency score
        """
        logger.info(f"Analyzing workflow for team {metrics.team_id}")

        # Detect bottlenecks
        bottlenecks = self.detect_bottlenecks(metrics)

        # Calculate efficiency score
        efficiency = self._calculate_efficiency(metrics, bottlenecks)

        # Identify focus areas
        focus_areas = self._identify_focus_areas(metrics, bottlenecks)

        analysis = WorkflowAnalysis(
            team_id=metrics.team_id,
            bottlenecks=bottlenecks,
            efficiency_score=efficiency,
            focus_areas=focus_areas,
            recommendations=[
                f"Address {b.name}" for b in bottlenecks[:3]
            ],
        )

        self._analysis_history.append(analysis)
        return analysis

    def detect_bottlenecks(self, metrics: Any) -> List[Bottleneck]:
        """
        Detect workflow bottlenecks from metrics.

        Args:
            metrics: TeamMetrics to analyze

        Returns:
            List of identified bottlenecks
        """
        from .retrospective_engine import MetricCategory

        bottlenecks = []

        # Check collaboration metrics for review bottleneck
        collab_metrics = metrics.get_by_category(MetricCategory.COLLABORATION)
        if collab_metrics:
            review_time = collab_metrics[0].value
            if review_time > 8:  # More than 8 hours
                bottlenecks.append(
                    Bottleneck(
                        name="Code Review Delay",
                        description=f"Average review turnaround is {review_time:.1f} hours",
                        severity=min(1.0, review_time / 24),
                        location="Code Review",
                        metrics_evidence=["code_review_turnaround"],
                    )
                )

        # Check quality metrics for testing bottleneck
        quality_metrics = metrics.get_by_category(MetricCategory.QUALITY)
        if quality_metrics:
            bug_rate = quality_metrics[0].value
            if bug_rate > 0.2:  # More than 0.2 bugs per story
                bottlenecks.append(
                    Bottleneck(
                        name="Quality Issues",
                        description=f"Bug rate is {bug_rate:.2f} per story",
                        severity=min(1.0, bug_rate * 2),
                        location="Testing/QA",
                        metrics_evidence=["bug_rate"],
                    )
                )

        # Check delivery metrics for planning bottleneck
        delivery_metrics = metrics.get_by_category(MetricCategory.DELIVERY)
        if delivery_metrics:
            completion_rate = delivery_metrics[0].value
            if completion_rate < 0.8:  # Less than 80% completion
                bottlenecks.append(
                    Bottleneck(
                        name="Sprint Planning Issues",
                        description=f"Sprint completion rate is {completion_rate:.0%}",
                        severity=1.0 - completion_rate,
                        location="Sprint Planning",
                        metrics_evidence=["sprint_completion_rate"],
                    )
                )

        return sorted(bottlenecks, key=lambda b: b.severity, reverse=True)

    def suggest_improvements(
        self,
        metrics: Any,
        assessment: Any
    ) -> List[Any]:
        """
        Generate improvement suggestions based on analysis.

        Args:
            metrics: TeamMetrics data
            assessment: PerformanceAssessment from evaluator

        Returns:
            List of Improvement suggestions
        """
        from .retrospective_engine import Improvement

        logger.info(f"Generating improvements for team {metrics.team_id}")

        # Analyze workflow
        analysis = self.analyze_workflow(metrics)

        improvements = []

        # Generate improvements from bottlenecks
        for bottleneck in analysis.bottlenecks:
            improvement = self._bottleneck_to_improvement(bottleneck)
            if improvement.confidence >= self.config.min_confidence:
                improvements.append(improvement)

        # Generate improvements from assessment areas
        for area in assessment.areas_for_improvement:
            improvement = self._area_to_improvement(area)
            if improvement.confidence >= self.config.min_confidence:
                improvements.append(improvement)

        # Add category-specific improvements
        for category in self.config.focus_areas:
            category_improvement = self._generate_category_improvement(
                category, metrics, assessment
            )
            if (
                category_improvement and
                category_improvement.confidence >= self.config.min_confidence
            ):
                improvements.append(category_improvement)

        # Deduplicate and limit
        seen_titles = set()
        unique_improvements = []
        for imp in improvements:
            if imp.title not in seen_titles:
                seen_titles.add(imp.title)
                unique_improvements.append(imp)

        logger.info(f"[IMPROVE] Generated {len(unique_improvements)} improvement suggestions")
        return unique_improvements[:self.config.max_suggestions]

    def prioritize_actions(
        self,
        improvements: List[Any]
    ) -> List[Any]:
        """
        Prioritize improvements using impact-effort matrix.

        Args:
            improvements: List of Improvement suggestions

        Returns:
            List of Improvement sorted by priority
        """
        prioritized = []

        for imp in improvements:
            # Determine quadrant
            quadrant = self._determine_quadrant(imp.impact_score, imp.effort_score)

            # Calculate priority rank (lower = higher priority)
            # Quick wins first, then strategic, then fill-ins, avoid last
            quadrant_order = {
                PriorityQuadrant.QUICK_WINS: 0,
                PriorityQuadrant.STRATEGIC: 1,
                PriorityQuadrant.FILL_INS: 2,
                PriorityQuadrant.AVOID: 3,
            }

            # Within quadrant, sort by impact (descending)
            priority_score = quadrant_order[quadrant] + (1 - imp.impact_score)

            # Update improvement with priority
            imp.priority = int(priority_score * 100)

            prioritized.append(imp)

        # Sort by priority
        return sorted(prioritized, key=lambda i: i.priority)

    def _calculate_efficiency(self, metrics: Any, bottlenecks: List[Bottleneck]) -> float:
        """Calculate overall workflow efficiency"""
        # Base efficiency starts at 1.0
        efficiency = 1.0

        # Reduce for each bottleneck based on severity
        for bottleneck in bottlenecks:
            efficiency -= bottleneck.severity * 0.2  # Each bottleneck can reduce up to 20%

        return max(0.0, min(1.0, efficiency))

    def _identify_focus_areas(
        self,
        metrics: Any,
        bottlenecks: List[Bottleneck]
    ) -> List[ImprovementCategory]:
        """Identify areas to focus on"""
        focus_areas = []

        for bottleneck in bottlenecks[:2]:  # Top 2 bottlenecks
            if "review" in bottleneck.name.lower():
                focus_areas.append(ImprovementCategory.TEAM_COMMUNICATION)
            elif "quality" in bottleneck.name.lower() or "bug" in bottleneck.name.lower():
                focus_areas.append(ImprovementCategory.CODE_QUALITY)
            elif "planning" in bottleneck.name.lower():
                focus_areas.append(ImprovementCategory.PROCESS_EFFICIENCY)
            else:
                focus_areas.append(ImprovementCategory.TECHNICAL_DEBT)

        return focus_areas

    def _bottleneck_to_improvement(self, bottleneck: Bottleneck) -> Any:
        """Convert a bottleneck to an improvement suggestion"""
        from .retrospective_engine import Improvement

        # Map bottleneck to improvement
        improvements_map = {
            "Code Review Delay": {
                "title": "Reduce Code Review Turnaround Time",
                "description": "Implement review SLAs and pair programming to speed up reviews",
                "category": "collaboration",
                "impact": 0.8,
                "effort": 0.4,
            },
            "Quality Issues": {
                "title": "Improve Code Quality Practices",
                "description": "Enhance testing coverage and implement quality gates",
                "category": "quality",
                "impact": 0.85,
                "effort": 0.6,
            },
            "Sprint Planning Issues": {
                "title": "Refine Sprint Planning Process",
                "description": "Break stories smaller and improve estimation accuracy",
                "category": "process",
                "impact": 0.75,
                "effort": 0.3,
            },
        }

        config = improvements_map.get(bottleneck.name, {
            "title": f"Address {bottleneck.name}",
            "description": bottleneck.description,
            "category": "process",
            "impact": bottleneck.severity,
            "effort": 0.5,
        })

        return Improvement(
            title=config["title"],
            description=config["description"],
            category=config["category"],
            impact_score=config["impact"],
            effort_score=config["effort"],
            confidence=0.8,
        )

    def _area_to_improvement(self, area: str) -> Any:
        """Convert an improvement area to an improvement suggestion"""
        from .retrospective_engine import Improvement

        area_lower = area.lower()

        if "velocity" in area_lower:
            return Improvement(
                title="Improve Velocity Consistency",
                description="Stabilize sprint velocity through better planning and estimation",
                category="process",
                impact_score=0.7,
                effort_score=0.4,
                confidence=0.75,
            )
        elif "quality" in area_lower:
            return Improvement(
                title="Enhance Quality Practices",
                description="Implement additional quality gates and testing",
                category="quality",
                impact_score=0.8,
                effort_score=0.6,
                confidence=0.8,
            )
        elif "collaboration" in area_lower:
            return Improvement(
                title="Improve Team Collaboration",
                description="Increase pair programming and knowledge sharing sessions",
                category="collaboration",
                impact_score=0.65,
                effort_score=0.3,
                confidence=0.75,
            )
        else:
            return Improvement(
                title=f"Address: {area}",
                description=f"Focus on improving {area}",
                category="process",
                impact_score=0.6,
                effort_score=0.4,
                confidence=0.7,
            )

    def _generate_category_improvement(
        self,
        category: ImprovementCategory,
        metrics: Any,
        assessment: Any
    ) -> Optional[Any]:
        """Generate improvement for a specific category"""
        from .retrospective_engine import Improvement

        category_improvements = {
            ImprovementCategory.PROCESS_EFFICIENCY: Improvement(
                title="Streamline Development Process",
                description="Remove unnecessary steps and automate repetitive tasks",
                category="process",
                impact_score=0.7,
                effort_score=0.5,
                confidence=0.75,
            ),
            ImprovementCategory.CODE_QUALITY: Improvement(
                title="Enhance Code Quality Standards",
                description="Implement stricter linting and automated code analysis",
                category="quality",
                impact_score=0.75,
                effort_score=0.4,
                confidence=0.8,
            ),
            ImprovementCategory.TEAM_COMMUNICATION: Improvement(
                title="Improve Team Communication",
                description="Establish regular sync meetings and documentation practices",
                category="communication",
                impact_score=0.65,
                effort_score=0.3,
                confidence=0.7,
            ),
            ImprovementCategory.TECHNICAL_DEBT: Improvement(
                title="Address Technical Debt",
                description="Allocate sprint capacity for refactoring and debt reduction",
                category="technical_debt",
                impact_score=0.7,
                effort_score=0.6,
                confidence=0.75,
            ),
        }

        improvement = category_improvements.get(category)

        # Only return if category score is low in assessment
        if improvement:
            category_score = assessment.category_scores.get(category.value, 1.0)
            if category_score < 0.7:
                return improvement

        return None

    def _determine_quadrant(
        self,
        impact: float,
        effort: float
    ) -> PriorityQuadrant:
        """Determine priority quadrant from impact and effort scores"""
        if impact >= 0.6:
            if effort <= 0.5:
                return PriorityQuadrant.QUICK_WINS
            else:
                return PriorityQuadrant.STRATEGIC
        else:
            if effort <= 0.5:
                return PriorityQuadrant.FILL_INS
            else:
                return PriorityQuadrant.AVOID


# Factory function
def create_process_improver(
    config: Optional[ImproverConfig] = None
) -> ProcessImprover:
    """
    Factory function to create a ProcessImprover.

    Args:
        config: Optional configuration

    Returns:
        Configured ProcessImprover instance
    """
    return ProcessImprover(config=config)
