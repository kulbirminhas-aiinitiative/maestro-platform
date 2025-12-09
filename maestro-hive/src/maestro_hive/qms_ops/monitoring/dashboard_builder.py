"""
Dashboard Builder Module
========================

Intelligent dashboard generation for QMS KPI visualization.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from .kpi_engine import KPIEngine, KPICategory, KPIResult, TrendDirection


class WidgetType(Enum):
    """Types of dashboard widgets."""
    KPI_CARD = "kpi_card"
    TREND_CHART = "trend_chart"
    GAUGE = "gauge"
    TABLE = "table"
    ALERT_LIST = "alert_list"
    HEATMAP = "heatmap"
    COMPARISON = "comparison"
    SCORECARD = "scorecard"


class ChartType(Enum):
    """Types of charts."""
    LINE = "line"
    BAR = "bar"
    PIE = "pie"
    AREA = "area"
    RADAR = "radar"


@dataclass
class WidgetConfig:
    """Configuration for a dashboard widget."""
    id: str
    widget_type: WidgetType
    title: str
    kpi_ids: List[str] = field(default_factory=list)
    chart_type: Optional[ChartType] = None
    time_range_days: int = 30
    position: Dict[str, int] = field(default_factory=lambda: {"row": 0, "col": 0, "width": 1, "height": 1})
    options: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DashboardLayout:
    """Dashboard layout configuration."""
    id: str
    name: str
    description: str
    widgets: List[WidgetConfig]
    columns: int = 4
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    is_default: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class WidgetRenderer:
    """Renders widget data for display."""

    def render_kpi_card(self, kpi_engine: KPIEngine, kpi_id: str) -> Dict[str, Any]:
        """Render a KPI card widget."""
        result = kpi_engine.get_kpi_result(kpi_id)
        kpi = kpi_engine.kpis.get(kpi_id)

        if not result or not kpi:
            return {"error": f"KPI {kpi_id} not found"}

        # Determine color based on status
        colors = {
            "on_track": "#22c55e",    # green
            "at_risk": "#f59e0b",     # amber
            "off_track": "#ef4444"    # red
        }

        return {
            "kpi_id": kpi_id,
            "name": kpi.name,
            "value": result.current_value,
            "unit": kpi.unit,
            "target": result.target,
            "variance": result.variance_percentage,
            "trend": result.trend.value,
            "trend_icon": "↑" if result.trend == TrendDirection.IMPROVING else "↓" if result.trend == TrendDirection.DECLINING else "→",
            "status": result.status,
            "color": colors.get(result.status, "#6b7280"),
            "last_updated": result.last_updated.isoformat()
        }

    def render_trend_chart(
        self,
        kpi_engine: KPIEngine,
        kpi_ids: List[str],
        days: int = 30,
        chart_type: ChartType = ChartType.LINE
    ) -> Dict[str, Any]:
        """Render a trend chart widget."""
        series = []
        start_date = datetime.utcnow() - timedelta(days=days)

        for kpi_id in kpi_ids:
            history = kpi_engine.history.get(kpi_id, [])
            kpi = kpi_engine.kpis.get(kpi_id)

            if not kpi:
                continue

            # Filter to date range
            filtered = [dp for dp in history if dp.timestamp >= start_date]

            series.append({
                "name": kpi.name,
                "kpi_id": kpi_id,
                "data": [
                    {"x": dp.timestamp.isoformat(), "y": dp.value}
                    for dp in filtered
                ],
                "target": kpi.target
            })

        return {
            "chart_type": chart_type.value,
            "series": series,
            "time_range": {
                "start": start_date.isoformat(),
                "end": datetime.utcnow().isoformat()
            }
        }

    def render_gauge(self, kpi_engine: KPIEngine, kpi_id: str) -> Dict[str, Any]:
        """Render a gauge widget."""
        result = kpi_engine.get_kpi_result(kpi_id)
        kpi = kpi_engine.kpis.get(kpi_id)

        if not result or not kpi:
            return {"error": f"KPI {kpi_id} not found"}

        # Calculate gauge parameters
        min_val = 0
        max_val = kpi.target * 1.5 if kpi.threshold.direction == "above" else kpi.target * 1.2

        return {
            "kpi_id": kpi_id,
            "name": kpi.name,
            "value": result.current_value,
            "min": min_val,
            "max": max_val,
            "target": kpi.target,
            "warning_threshold": kpi.threshold.warning_threshold,
            "critical_threshold": kpi.threshold.critical_threshold,
            "unit": kpi.unit
        }

    def render_scorecard(self, kpi_engine: KPIEngine, category: Optional[KPICategory] = None) -> Dict[str, Any]:
        """Render a scorecard widget."""
        results = kpi_engine.get_all_results()
        kpis = kpi_engine.kpis

        # Filter by category if specified
        if category:
            filtered_ids = [kpi.id for kpi in kpis.values() if kpi.category == category]
            results = {k: v for k, v in results.items() if k in filtered_ids}

        # Calculate overall score
        scores = []
        for kpi_id, result in results.items():
            kpi = kpis.get(kpi_id)
            if not kpi:
                continue

            # Score based on variance from target
            variance_pct = abs(result.variance_percentage)
            if variance_pct <= 5:
                score = 100
            elif variance_pct <= 10:
                score = 90
            elif variance_pct <= 20:
                score = 70
            else:
                score = max(0, 100 - variance_pct)

            scores.append({
                "kpi_id": kpi_id,
                "name": kpi.name,
                "score": score,
                "status": result.status
            })

        overall_score = sum(s["score"] for s in scores) / len(scores) if scores else 0

        # Determine grade
        if overall_score >= 90:
            grade = "A"
        elif overall_score >= 80:
            grade = "B"
        elif overall_score >= 70:
            grade = "C"
        elif overall_score >= 60:
            grade = "D"
        else:
            grade = "F"

        return {
            "overall_score": overall_score,
            "grade": grade,
            "category": category.value if category else "all",
            "kpi_scores": scores,
            "on_track_count": len([s for s in scores if s["status"] == "on_track"]),
            "total_count": len(scores)
        }


class DashboardBuilder:
    """
    Builds and manages QMS KPI dashboards.

    Provides intelligent dashboard generation with customizable
    layouts and real-time data rendering.
    """

    # Standard dashboard templates
    TEMPLATES = {
        "executive": DashboardLayout(
            id="tpl-executive",
            name="Executive Summary",
            description="High-level QMS performance overview",
            widgets=[
                WidgetConfig("w1", WidgetType.SCORECARD, "Overall QMS Score", position={"row": 0, "col": 0, "width": 2, "height": 1}),
                WidgetConfig("w2", WidgetType.ALERT_LIST, "Active Alerts", position={"row": 0, "col": 2, "width": 2, "height": 1}),
                WidgetConfig("w3", WidgetType.KPI_CARD, "Defect Rate", ["defect_rate_dppm"], position={"row": 1, "col": 0, "width": 1, "height": 1}),
                WidgetConfig("w4", WidgetType.KPI_CARD, "First Pass Yield", ["first_pass_yield"], position={"row": 1, "col": 1, "width": 1, "height": 1}),
                WidgetConfig("w5", WidgetType.KPI_CARD, "CAPA Closure", ["capa_closure_rate"], position={"row": 1, "col": 2, "width": 1, "height": 1}),
                WidgetConfig("w6", WidgetType.KPI_CARD, "Complaint Rate", ["complaint_rate"], position={"row": 1, "col": 3, "width": 1, "height": 1}),
                WidgetConfig("w7", WidgetType.TREND_CHART, "Quality Trends", ["defect_rate_dppm", "first_pass_yield"], ChartType.LINE, 90, {"row": 2, "col": 0, "width": 4, "height": 2}),
            ],
            is_default=True
        ),
        "quality": DashboardLayout(
            id="tpl-quality",
            name="Quality Operations",
            description="Detailed quality metrics",
            widgets=[
                WidgetConfig("w1", WidgetType.GAUGE, "Defect Rate", ["defect_rate_dppm"], position={"row": 0, "col": 0, "width": 1, "height": 1}),
                WidgetConfig("w2", WidgetType.GAUGE, "First Pass Yield", ["first_pass_yield"], position={"row": 0, "col": 1, "width": 1, "height": 1}),
                WidgetConfig("w3", WidgetType.TREND_CHART, "Quality Trends", ["defect_rate_dppm", "first_pass_yield"], ChartType.LINE, 30, {"row": 0, "col": 2, "width": 2, "height": 1}),
                WidgetConfig("w4", WidgetType.TABLE, "NC Summary", position={"row": 1, "col": 0, "width": 2, "height": 1}),
                WidgetConfig("w5", WidgetType.TABLE, "CAPA Summary", position={"row": 1, "col": 2, "width": 2, "height": 1}),
            ]
        ),
        "compliance": DashboardLayout(
            id="tpl-compliance",
            name="Compliance Dashboard",
            description="Regulatory compliance overview",
            widgets=[
                WidgetConfig("w1", WidgetType.SCORECARD, "Compliance Score", position={"row": 0, "col": 0, "width": 2, "height": 1}),
                WidgetConfig("w2", WidgetType.KPI_CARD, "Training Compliance", ["training_compliance"], position={"row": 0, "col": 2, "width": 1, "height": 1}),
                WidgetConfig("w3", WidgetType.KPI_CARD, "CAPA Closure", ["capa_closure_rate"], position={"row": 0, "col": 3, "width": 1, "height": 1}),
                WidgetConfig("w4", WidgetType.TREND_CHART, "Compliance Trends", ["training_compliance", "capa_closure_rate"], ChartType.LINE, 90, {"row": 1, "col": 0, "width": 4, "height": 2}),
            ]
        ),
    }

    def __init__(self, kpi_engine: KPIEngine):
        self.kpi_engine = kpi_engine
        self.renderer = WidgetRenderer()
        self.dashboards: Dict[str, DashboardLayout] = {}
        self.logger = logging.getLogger("qms-dashboard")
        self._configure_logger()
        self._register_templates()

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

    def _register_templates(self) -> None:
        """Register dashboard templates."""
        for template in self.TEMPLATES.values():
            self.dashboards[template.id] = template

    def create_dashboard(
        self,
        name: str,
        description: str,
        created_by: str,
        widgets: List[WidgetConfig] = None
    ) -> DashboardLayout:
        """Create a custom dashboard."""
        import uuid

        dashboard = DashboardLayout(
            id=f"dash-{str(uuid.uuid4())[:8]}",
            name=name,
            description=description,
            widgets=widgets or [],
            created_by=created_by
        )

        self.dashboards[dashboard.id] = dashboard
        self.logger.info(f"DASHBOARD_CREATED | id={dashboard.id} | name={name}")

        return dashboard

    def get_dashboard(self, dashboard_id: str) -> Optional[DashboardLayout]:
        """Get a dashboard by ID."""
        return self.dashboards.get(dashboard_id)

    def render_dashboard(self, dashboard_id: str) -> Dict[str, Any]:
        """
        Render a complete dashboard with all widget data.

        Args:
            dashboard_id: Dashboard identifier

        Returns:
            Dictionary with rendered dashboard data
        """
        dashboard = self.get_dashboard(dashboard_id)
        if not dashboard:
            return {"error": f"Dashboard {dashboard_id} not found"}

        rendered_widgets = []

        for widget in dashboard.widgets:
            widget_data = self._render_widget(widget)
            rendered_widgets.append({
                "id": widget.id,
                "type": widget.widget_type.value,
                "title": widget.title,
                "position": widget.position,
                "data": widget_data
            })

        return {
            "dashboard_id": dashboard.id,
            "name": dashboard.name,
            "description": dashboard.description,
            "widgets": rendered_widgets,
            "rendered_at": datetime.utcnow().isoformat()
        }

    def _render_widget(self, widget: WidgetConfig) -> Dict[str, Any]:
        """Render a single widget."""
        if widget.widget_type == WidgetType.KPI_CARD:
            kpi_id = widget.kpi_ids[0] if widget.kpi_ids else None
            if kpi_id:
                return self.renderer.render_kpi_card(self.kpi_engine, kpi_id)

        elif widget.widget_type == WidgetType.TREND_CHART:
            return self.renderer.render_trend_chart(
                self.kpi_engine,
                widget.kpi_ids,
                widget.time_range_days,
                widget.chart_type or ChartType.LINE
            )

        elif widget.widget_type == WidgetType.GAUGE:
            kpi_id = widget.kpi_ids[0] if widget.kpi_ids else None
            if kpi_id:
                return self.renderer.render_gauge(self.kpi_engine, kpi_id)

        elif widget.widget_type == WidgetType.SCORECARD:
            category = widget.options.get("category")
            if category:
                category = KPICategory(category)
            return self.renderer.render_scorecard(self.kpi_engine, category)

        elif widget.widget_type == WidgetType.ALERT_LIST:
            alerts = self.kpi_engine.get_active_alerts()
            return {
                "alerts": [
                    {
                        "id": a.id,
                        "severity": a.severity.value,
                        "title": a.title,
                        "message": a.message,
                        "created_at": a.created_at.isoformat()
                    }
                    for a in alerts[:10]
                ],
                "total_count": len(alerts)
            }

        return {"type": widget.widget_type.value, "message": "Widget type not fully implemented"}

    def get_default_dashboard(self) -> Optional[DashboardLayout]:
        """Get the default dashboard."""
        for dashboard in self.dashboards.values():
            if dashboard.is_default:
                return dashboard
        return None
