"""
Recommendation Engine Module
=============================

AI-powered improvement recommendation generation with ROI estimates.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from .pattern_analyzer import Pattern, PatternType, TrendDirection


class RecommendationType(Enum):
    """Types of improvement recommendations."""
    PROCESS_CHANGE = "process_change"
    TRAINING = "training"
    AUTOMATION = "automation"
    EQUIPMENT = "equipment"
    PROCEDURE_UPDATE = "procedure_update"
    SUPPLIER_ACTION = "supplier_action"
    DESIGN_CHANGE = "design_change"
    RESOURCE_ALLOCATION = "resource_allocation"


class ImplementationEffort(Enum):
    """Effort levels for implementation."""
    LOW = "low"          # < 1 week
    MEDIUM = "medium"    # 1-4 weeks
    HIGH = "high"        # 1-3 months
    VERY_HIGH = "very_high"  # > 3 months


class Priority(Enum):
    """Recommendation priority levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class CostEstimate:
    """Cost estimation for implementation."""
    implementation_cost: float  # One-time cost
    annual_savings: float       # Expected annual savings
    roi_months: float          # Months to positive ROI
    confidence: float          # Confidence in estimate

    @property
    def roi_percentage(self) -> float:
        """Calculate ROI percentage."""
        if self.implementation_cost <= 0:
            return float('inf')
        return (self.annual_savings / self.implementation_cost) * 100


@dataclass
class Recommendation:
    """Improvement recommendation."""
    id: str
    title: str
    description: str
    recommendation_type: RecommendationType
    priority: Priority
    effort: ImplementationEffort
    source_patterns: List[str]  # Pattern IDs
    expected_impact: str
    cost_estimate: Optional[CostEstimate] = None
    implementation_steps: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    affected_processes: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def priority_score(self) -> float:
        """Calculate numeric priority score."""
        priority_values = {
            Priority.CRITICAL: 10,
            Priority.HIGH: 7,
            Priority.MEDIUM: 5,
            Priority.LOW: 2
        }
        effort_multipliers = {
            ImplementationEffort.LOW: 1.5,
            ImplementationEffort.MEDIUM: 1.2,
            ImplementationEffort.HIGH: 0.9,
            ImplementationEffort.VERY_HIGH: 0.6
        }
        return priority_values[self.priority] * effort_multipliers[self.effort]


class RecommendationTemplates:
    """Templates for generating recommendations based on patterns."""

    TEMPLATES = {
        PatternType.RECURRING: {
            "process": {
                "title": "Process Control Enhancement for {category}",
                "type": RecommendationType.PROCESS_CHANGE,
                "description": "Implement additional process controls to prevent recurring {category} issues.",
                "steps": [
                    "Analyze root causes of recurring issues",
                    "Design additional control points",
                    "Update SOPs with new controls",
                    "Train affected personnel",
                    "Monitor effectiveness for 90 days"
                ]
            },
            "training": {
                "title": "Enhanced Training Program for {category}",
                "type": RecommendationType.TRAINING,
                "description": "Develop comprehensive training to address recurring {category} issues.",
                "steps": [
                    "Identify knowledge gaps from recurring issues",
                    "Develop targeted training materials",
                    "Conduct training sessions",
                    "Assess competency post-training",
                    "Track issue recurrence rates"
                ]
            }
        },
        PatternType.TRENDING: {
            "investigation": {
                "title": "Root Cause Investigation for {category} Trend",
                "type": RecommendationType.PROCESS_CHANGE,
                "description": "Conduct systematic investigation of increasing {category} trend.",
                "steps": [
                    "Gather all trend data and evidence",
                    "Perform comprehensive root cause analysis",
                    "Identify systemic factors",
                    "Develop corrective action plan",
                    "Implement and monitor effectiveness"
                ]
            }
        },
        PatternType.CORRELATED: {
            "integration": {
                "title": "Cross-System Integration for {sources}",
                "type": RecommendationType.AUTOMATION,
                "description": "Implement automated monitoring and alerts for correlated {sources} events.",
                "steps": [
                    "Map correlation dependencies",
                    "Design integrated monitoring system",
                    "Implement automated alerts",
                    "Create response procedures",
                    "Train teams on integrated approach"
                ]
            }
        },
        PatternType.CLUSTERED: {
            "targeted": {
                "title": "Targeted Improvement for {cluster_area}",
                "type": RecommendationType.PROCESS_CHANGE,
                "description": "Address concentrated issues in {cluster_area} through targeted improvements.",
                "steps": [
                    "Deep-dive analysis of cluster area",
                    "Identify specific contributing factors",
                    "Develop targeted interventions",
                    "Implement changes",
                    "Measure cluster reduction"
                ]
            }
        }
    }


class ROICalculator:
    """Calculates ROI estimates for recommendations."""

    # Average costs by category (configurable)
    ISSUE_COSTS = {
        "default": 5000,
        "critical": 50000,
        "high": 20000,
        "major": 15000,
        "medium": 5000,
        "minor": 1000,
    }

    # Implementation cost ranges by effort
    IMPLEMENTATION_COSTS = {
        ImplementationEffort.LOW: (5000, 15000),
        ImplementationEffort.MEDIUM: (15000, 50000),
        ImplementationEffort.HIGH: (50000, 150000),
        ImplementationEffort.VERY_HIGH: (150000, 500000),
    }

    def estimate_roi(
        self,
        pattern: Pattern,
        recommendation_type: RecommendationType,
        effort: ImplementationEffort
    ) -> CostEstimate:
        """
        Estimate ROI for a recommendation.

        Args:
            pattern: Source pattern
            recommendation_type: Type of recommendation
            effort: Implementation effort level

        Returns:
            CostEstimate with projected costs and savings
        """
        # Estimate annual cost of current issues
        issue_cost = self.ISSUE_COSTS.get(
            pattern.metadata.get("avg_severity", "medium"),
            self.ISSUE_COSTS["default"]
        )
        annual_issues = pattern.frequency * (365 / max(1, (pattern.last_occurrence - pattern.first_occurrence).days))
        current_annual_cost = issue_cost * annual_issues

        # Estimate effectiveness (reduction percentage)
        effectiveness = self._estimate_effectiveness(recommendation_type)
        annual_savings = current_annual_cost * effectiveness

        # Estimate implementation cost
        cost_range = self.IMPLEMENTATION_COSTS[effort]
        implementation_cost = (cost_range[0] + cost_range[1]) / 2

        # Calculate ROI months
        if annual_savings > 0:
            roi_months = (implementation_cost / annual_savings) * 12
        else:
            roi_months = float('inf')

        # Confidence based on data quality
        confidence = min(0.9, 0.5 + (pattern.confidence * 0.3) + (min(pattern.frequency, 20) * 0.01))

        return CostEstimate(
            implementation_cost=implementation_cost,
            annual_savings=annual_savings,
            roi_months=roi_months,
            confidence=confidence
        )

    def _estimate_effectiveness(self, rec_type: RecommendationType) -> float:
        """Estimate effectiveness percentage by recommendation type."""
        effectiveness_rates = {
            RecommendationType.PROCESS_CHANGE: 0.60,
            RecommendationType.TRAINING: 0.40,
            RecommendationType.AUTOMATION: 0.75,
            RecommendationType.EQUIPMENT: 0.70,
            RecommendationType.PROCEDURE_UPDATE: 0.50,
            RecommendationType.SUPPLIER_ACTION: 0.55,
            RecommendationType.DESIGN_CHANGE: 0.80,
            RecommendationType.RESOURCE_ALLOCATION: 0.45,
        }
        return effectiveness_rates.get(rec_type, 0.50)


class RecommendationEngine:
    """
    AI-powered recommendation generation engine.

    Analyzes patterns and generates actionable improvement recommendations.
    """

    def __init__(self):
        self.roi_calculator = ROICalculator()
        self.recommendations: Dict[str, Recommendation] = {}
        self.logger = logging.getLogger("qms-recommendations")
        self._configure_logger()

    def _configure_logger(self) -> None:
        """Configure logger."""
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def generate_recommendations(
        self,
        patterns: List[Pattern],
        max_recommendations: int = 10
    ) -> List[Recommendation]:
        """
        Generate recommendations from identified patterns.

        Args:
            patterns: List of identified patterns
            max_recommendations: Maximum number of recommendations

        Returns:
            List of prioritized recommendations
        """
        import uuid

        recommendations = []

        for pattern in patterns:
            # Generate recommendations based on pattern type
            recs = self._generate_for_pattern(pattern)
            recommendations.extend(recs)

        # Deduplicate and prioritize
        recommendations = self._deduplicate(recommendations)
        recommendations.sort(key=lambda r: r.priority_score, reverse=True)
        recommendations = recommendations[:max_recommendations]

        # Store recommendations
        for rec in recommendations:
            self.recommendations[rec.id] = rec

        self.logger.info(
            f"RECOMMENDATIONS_GENERATED | count={len(recommendations)} | "
            f"critical={sum(1 for r in recommendations if r.priority == Priority.CRITICAL)}"
        )

        return recommendations

    def _generate_for_pattern(self, pattern: Pattern) -> List[Recommendation]:
        """Generate recommendations for a single pattern."""
        import uuid

        recommendations = []
        templates = RecommendationTemplates.TEMPLATES.get(pattern.pattern_type, {})

        for template_key, template in templates.items():
            # Format template with pattern data
            category = pattern.affected_areas[0] if pattern.affected_areas else "quality"
            sources = ", ".join(s.value for s in pattern.sources)
            cluster_area = pattern.metadata.get("cluster_value", category)

            title = template["title"].format(
                category=category,
                sources=sources,
                cluster_area=cluster_area
            )
            description = template["description"].format(
                category=category,
                sources=sources,
                cluster_area=cluster_area
            )

            # Determine priority and effort
            priority = self._determine_priority(pattern)
            effort = self._determine_effort(template["type"], pattern)

            # Calculate ROI
            cost_estimate = self.roi_calculator.estimate_roi(
                pattern,
                template["type"],
                effort
            )

            recommendation = Recommendation(
                id=f"REC-{str(uuid.uuid4())[:8].upper()}",
                title=title,
                description=description,
                recommendation_type=template["type"],
                priority=priority,
                effort=effort,
                source_patterns=[pattern.id],
                expected_impact=self._estimate_impact(pattern, template["type"]),
                cost_estimate=cost_estimate,
                implementation_steps=template.get("steps", []),
                success_criteria=self._generate_success_criteria(pattern),
                risks=self._identify_risks(template["type"]),
                affected_processes=pattern.affected_areas
            )

            recommendations.append(recommendation)

        return recommendations

    def _determine_priority(self, pattern: Pattern) -> Priority:
        """Determine recommendation priority from pattern."""
        if pattern.is_critical or pattern.impact_score >= 8:
            return Priority.CRITICAL
        elif pattern.impact_score >= 6:
            return Priority.HIGH
        elif pattern.impact_score >= 4:
            return Priority.MEDIUM
        else:
            return Priority.LOW

    def _determine_effort(
        self,
        rec_type: RecommendationType,
        pattern: Pattern
    ) -> ImplementationEffort:
        """Determine implementation effort level."""
        # Base effort by type
        base_effort = {
            RecommendationType.PROCESS_CHANGE: ImplementationEffort.MEDIUM,
            RecommendationType.TRAINING: ImplementationEffort.LOW,
            RecommendationType.AUTOMATION: ImplementationEffort.HIGH,
            RecommendationType.EQUIPMENT: ImplementationEffort.HIGH,
            RecommendationType.PROCEDURE_UPDATE: ImplementationEffort.LOW,
            RecommendationType.SUPPLIER_ACTION: ImplementationEffort.MEDIUM,
            RecommendationType.DESIGN_CHANGE: ImplementationEffort.VERY_HIGH,
            RecommendationType.RESOURCE_ALLOCATION: ImplementationEffort.MEDIUM,
        }

        return base_effort.get(rec_type, ImplementationEffort.MEDIUM)

    def _estimate_impact(
        self,
        pattern: Pattern,
        rec_type: RecommendationType
    ) -> str:
        """Generate impact statement."""
        effectiveness = self.roi_calculator._estimate_effectiveness(rec_type)
        reduction_pct = int(effectiveness * 100)

        if pattern.pattern_type == PatternType.TRENDING:
            return f"Expected to reduce {pattern.affected_areas[0]} trend by {reduction_pct}%"
        elif pattern.pattern_type == PatternType.RECURRING:
            return f"Expected to reduce recurring issues by {reduction_pct}%, preventing ~{int(pattern.frequency * effectiveness)} recurrences"
        else:
            return f"Expected {reduction_pct}% improvement in affected area"

    def _generate_success_criteria(self, pattern: Pattern) -> List[str]:
        """Generate measurable success criteria."""
        return [
            f"Reduce {pattern.affected_areas[0] if pattern.affected_areas else 'issue'} frequency by 50% within 6 months",
            "Zero recurrence of identified root cause within 90 days",
            "Positive trend reversal within 3 months",
            "Employee competency verification at 100%"
        ]

    def _identify_risks(self, rec_type: RecommendationType) -> List[str]:
        """Identify implementation risks."""
        risks_by_type = {
            RecommendationType.PROCESS_CHANGE: [
                "Resistance to change from staff",
                "Temporary productivity dip during transition"
            ],
            RecommendationType.TRAINING: [
                "Training effectiveness varies by individual",
                "Time away from production"
            ],
            RecommendationType.AUTOMATION: [
                "Technical implementation challenges",
                "Integration with existing systems"
            ],
            RecommendationType.DESIGN_CHANGE: [
                "Regulatory revalidation requirements",
                "Extended timeline"
            ]
        }
        return risks_by_type.get(rec_type, ["Implementation timeline risk"])

    def _deduplicate(
        self,
        recommendations: List[Recommendation]
    ) -> List[Recommendation]:
        """Remove duplicate or very similar recommendations."""
        unique = {}
        for rec in recommendations:
            # Key on type + affected processes
            key = f"{rec.recommendation_type.value}:{':'.join(sorted(rec.affected_processes))}"
            if key not in unique or rec.priority_score > unique[key].priority_score:
                unique[key] = rec
        return list(unique.values())

    def get_recommendation(self, rec_id: str) -> Optional[Recommendation]:
        """Get recommendation by ID."""
        return self.recommendations.get(rec_id)

    def get_recommendations_by_type(
        self,
        rec_type: RecommendationType
    ) -> List[Recommendation]:
        """Get recommendations by type."""
        return [r for r in self.recommendations.values() if r.recommendation_type == rec_type]

    def get_high_roi_recommendations(
        self,
        max_roi_months: float = 12
    ) -> List[Recommendation]:
        """Get recommendations with ROI under specified months."""
        return [
            r for r in self.recommendations.values()
            if r.cost_estimate and r.cost_estimate.roi_months <= max_roi_months
        ]

    def get_summary(self) -> Dict[str, Any]:
        """Get recommendation summary."""
        total_savings = sum(
            r.cost_estimate.annual_savings
            for r in self.recommendations.values()
            if r.cost_estimate
        )
        total_cost = sum(
            r.cost_estimate.implementation_cost
            for r in self.recommendations.values()
            if r.cost_estimate
        )

        return {
            "total_recommendations": len(self.recommendations),
            "by_priority": {
                p.value: len([r for r in self.recommendations.values() if r.priority == p])
                for p in Priority
            },
            "by_type": {
                t.value: len([r for r in self.recommendations.values() if r.recommendation_type == t])
                for t in RecommendationType
            },
            "estimated_total_savings": total_savings,
            "estimated_total_cost": total_cost,
            "aggregate_roi_percentage": (total_savings / total_cost * 100) if total_cost > 0 else 0
        }
