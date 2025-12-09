#!/usr/bin/env python3
"""
Cost Reporter: Generate cost analytics and reports.

Creates detailed cost reports by team, project, and model usage.
"""

import json
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from .cost_tracker import CostTracker, CostSummary

logger = logging.getLogger(__name__)


@dataclass
class CostReport:
    """A cost analytics report."""
    id: str
    period_start: str
    period_end: str
    summary: CostSummary
    trends: Dict[str, Any]
    projections: Dict[str, float]
    recommendations: List[str]
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['summary'] = self.summary.to_dict()
        return data


class CostReporter:
    """Generates cost analytics reports."""

    def __init__(
        self,
        output_dir: Optional[str] = None,
        tracker: Optional[CostTracker] = None
    ):
        self.output_dir = Path(output_dir) if output_dir else Path.cwd() / 'cost_reports'
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.tracker = tracker or CostTracker()
        self._report_counter = 0

    def generate_report(
        self,
        period: str = '30d',
        team_id: Optional[str] = None,
        project_id: Optional[str] = None
    ) -> CostReport:
        """Generate a cost analytics report."""
        summary = self.tracker.get_summary(since=period, team_id=team_id, project_id=project_id)

        # Calculate trends (simplified)
        trends = {
            'daily_average': summary.total_cost_usd / 30 if period == '30d' else summary.total_cost_usd / 7,
            'top_model': max(summary.by_model.items(), key=lambda x: x[1].get('cost', 0))[0] if summary.by_model else None,
            'top_team': max(summary.by_team.items(), key=lambda x: x[1])[0] if summary.by_team else None
        }

        # Simple projection (linear)
        daily_rate = trends['daily_average']
        projections = {
            'next_week': daily_rate * 7,
            'next_month': daily_rate * 30,
            'next_quarter': daily_rate * 90
        }

        # Recommendations
        recommendations = []
        if trends['daily_average'] > 100:
            recommendations.append("Consider implementing caching to reduce API calls")
        if summary.total_requests > 10000:
            recommendations.append("Review request patterns for optimization opportunities")
        if trends['top_model'] in ['gpt-4', 'claude-3-opus']:
            recommendations.append("Consider using smaller models for simple tasks")

        self._report_counter += 1
        report_id = f"COST-RPT-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{self._report_counter:04d}"

        report = CostReport(
            id=report_id,
            period_start=summary.period_start,
            period_end=summary.period_end,
            summary=summary,
            trends=trends,
            projections=projections,
            recommendations=recommendations
        )

        # Save report
        output_file = self.output_dir / f"{report_id}.json"
        with open(output_file, 'w') as f:
            json.dump(report.to_dict(), f, indent=2)

        logger.info(f"Generated cost report: {report_id} (${summary.total_cost_usd:.2f})")

        return report


def get_cost_reporter(**kwargs) -> CostReporter:
    """Get cost reporter instance."""
    return CostReporter(**kwargs)
