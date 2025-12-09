"""
QMS-OPS Real-Time KPI Monitoring Package
========================================

Intelligent dashboards and alerting for QMS performance monitoring.

Modules:
- kpi_engine: KPI calculation and alerting engine
- dashboard_builder: Intelligent dashboard generation
"""

from .kpi_engine import (
    KPIEngine,
    KPIDefinition,
    KPIResult,
    KPIDataPoint,
    KPIThreshold,
    KPICategory,
    TrendDirection,
    Alert,
    AlertSeverity,
    KPICalculator,
    TrendAnalyzer,
)

from .dashboard_builder import (
    DashboardBuilder,
    DashboardLayout,
    WidgetConfig,
    WidgetType,
    ChartType,
    WidgetRenderer,
)

__all__ = [
    "KPIEngine",
    "KPIDefinition",
    "KPIResult",
    "KPIDataPoint",
    "KPIThreshold",
    "KPICategory",
    "TrendDirection",
    "Alert",
    "AlertSeverity",
    "KPICalculator",
    "TrendAnalyzer",
    "DashboardBuilder",
    "DashboardLayout",
    "WidgetConfig",
    "WidgetType",
    "ChartType",
    "WidgetRenderer",
]

__version__ = "1.0.0"
__epic__ = "MD-2413"
