#!/usr/bin/env python3
"""
Risk Dashboard: Real-time risk visualization and monitoring.

Provides aggregated risk views and alerting for compliance.
"""

import json
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from .risk_scorer import RiskScorer, RiskAssessment, RiskLevel

logger = logging.getLogger(__name__)


@dataclass
class RiskDashboardMetrics:
    """Dashboard metrics."""
    total_entities: int
    by_risk_level: Dict[str, int]
    avg_risk_score: float
    critical_entities: List[str]
    recent_assessments: List[str]
    trend: str  # improving, stable, degrading
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class RiskDashboard:
    """Aggregates and visualizes risk data."""

    def __init__(self, scorer: Optional[RiskScorer] = None):
        self.scorer = scorer or RiskScorer()

    def get_metrics(self, entity_type: Optional[str] = None) -> RiskDashboardMetrics:
        """Get current dashboard metrics."""
        assessments = self.scorer.get_assessments(entity_type=entity_type, limit=1000)

        by_level = {level.value: 0 for level in RiskLevel}
        scores = []
        critical = []

        for assessment in assessments:
            by_level[assessment.risk_level.value] += 1
            scores.append(assessment.overall_score)
            if assessment.risk_level in (RiskLevel.CRITICAL, RiskLevel.HIGH):
                critical.append(assessment.entity_id)

        avg_score = sum(scores) / len(scores) if scores else 0.0

        return RiskDashboardMetrics(
            total_entities=len(assessments),
            by_risk_level=by_level,
            avg_risk_score=round(avg_score, 2),
            critical_entities=critical[:10],
            recent_assessments=[a.id for a in assessments[:5]],
            trend='stable'  # Would need historical data for real trend
        )

    def get_heatmap_data(self) -> Dict[str, Dict[str, float]]:
        """Get data for risk heatmap visualization."""
        assessments = self.scorer.get_assessments(limit=100)
        heatmap = {}

        for assessment in assessments:
            entity_type = assessment.entity_type
            if entity_type not in heatmap:
                heatmap[entity_type] = {'count': 0, 'total_score': 0}
            heatmap[entity_type]['count'] += 1
            heatmap[entity_type]['total_score'] += assessment.overall_score

        # Calculate averages
        for entity_type in heatmap:
            count = heatmap[entity_type]['count']
            heatmap[entity_type]['avg_score'] = heatmap[entity_type]['total_score'] / count

        return heatmap


def get_risk_dashboard(**kwargs) -> RiskDashboard:
    """Get risk dashboard instance."""
    return RiskDashboard(**kwargs)
