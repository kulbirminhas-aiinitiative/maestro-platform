"""
KPI Engine Module
==================

Real-time QMS KPI calculation and tracking engine.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


class KPICategory(Enum):
    """Categories of QMS KPIs."""
    QUALITY = "quality"
    COMPLIANCE = "compliance"
    OPERATIONAL = "operational"
    CUSTOMER = "customer"
    FINANCIAL = "financial"
    SAFETY = "safety"


class TrendDirection(Enum):
    """KPI trend directions."""
    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"
    CRITICAL = "critical"


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class KPIThreshold:
    """Threshold configuration for KPI alerts."""
    warning_threshold: float
    critical_threshold: float
    direction: str = "below"  # "below" or "above" - which direction is bad
    warning_message: str = ""
    critical_message: str = ""


@dataclass
class KPIDataPoint:
    """Single KPI measurement."""
    value: float
    timestamp: datetime
    source: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class KPIDefinition:
    """KPI definition with calculation rules."""
    id: str
    name: str
    description: str
    category: KPICategory
    unit: str
    target: float
    threshold: KPIThreshold
    calculation_formula: str = ""
    data_sources: List[str] = field(default_factory=list)
    update_frequency_minutes: int = 60
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class KPIResult:
    """Current KPI result with analysis."""
    kpi_id: str
    current_value: float
    previous_value: Optional[float]
    target: float
    variance_from_target: float
    variance_percentage: float
    trend: TrendDirection
    trend_slope: float
    status: str  # "on_track", "at_risk", "off_track"
    last_updated: datetime
    history: List[KPIDataPoint] = field(default_factory=list)

    @property
    def is_meeting_target(self) -> bool:
        """Check if KPI is meeting target."""
        return abs(self.variance_percentage) <= 10


@dataclass
class Alert:
    """KPI alert notification."""
    id: str
    kpi_id: str
    severity: AlertSeverity
    title: str
    message: str
    current_value: float
    threshold_value: float
    created_at: datetime
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class KPICalculator:
    """Calculates KPI values from source data."""

    # Standard QMS KPI formulas
    FORMULAS = {
        "defect_rate": lambda data: (data["defects"] / data["total_units"]) * 1000000 if data.get("total_units", 0) > 0 else 0,
        "first_pass_yield": lambda data: (data["passed_first_time"] / data["total_inspected"]) * 100 if data.get("total_inspected", 0) > 0 else 0,
        "capa_closure_rate": lambda data: (data["closed_capas"] / data["total_capas"]) * 100 if data.get("total_capas", 0) > 0 else 0,
        "nc_cycle_time": lambda data: data.get("total_days", 0) / max(data.get("nc_count", 1), 1),
        "audit_findings": lambda data: data.get("findings_count", 0),
        "complaint_rate": lambda data: (data["complaints"] / data["units_shipped"]) * 10000 if data.get("units_shipped", 0) > 0 else 0,
        "training_compliance": lambda data: (data["trained"] / data["required"]) * 100 if data.get("required", 0) > 0 else 0,
        "supplier_quality_index": lambda data: 100 - (data.get("rejects", 0) / max(data.get("lots_received", 1), 1)) * 100,
        "oee": lambda data: data.get("availability", 0) * data.get("performance", 0) * data.get("quality", 0) / 10000,
        "scrap_rate": lambda data: (data["scrap_units"] / data["total_produced"]) * 100 if data.get("total_produced", 0) > 0 else 0,
    }

    def calculate(self, kpi_id: str, data: Dict[str, Any]) -> float:
        """
        Calculate KPI value using predefined formula.

        Args:
            kpi_id: KPI identifier
            data: Input data for calculation

        Returns:
            Calculated KPI value
        """
        if kpi_id in self.FORMULAS:
            try:
                return self.FORMULAS[kpi_id](data)
            except (ZeroDivisionError, KeyError, TypeError):
                return 0.0
        return data.get("value", 0.0)


class TrendAnalyzer:
    """Analyzes KPI trends over time."""

    def analyze(self, history: List[KPIDataPoint], periods: int = 5) -> Tuple[TrendDirection, float]:
        """
        Analyze trend from historical data.

        Args:
            history: Historical data points
            periods: Number of recent periods to analyze

        Returns:
            Tuple of (TrendDirection, slope)
        """
        if len(history) < 2:
            return TrendDirection.STABLE, 0.0

        recent = sorted(history, key=lambda x: x.timestamp)[-periods:]
        values = [dp.value for dp in recent]

        if len(values) < 2:
            return TrendDirection.STABLE, 0.0

        # Calculate simple slope
        n = len(values)
        x_mean = (n - 1) / 2
        y_mean = sum(values) / n

        numerator = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        slope = numerator / denominator if denominator > 0 else 0

        # Determine direction based on slope and context
        threshold = y_mean * 0.02 if y_mean > 0 else 0.1

        if abs(slope) < threshold:
            direction = TrendDirection.STABLE
        elif slope > 0:
            direction = TrendDirection.IMPROVING
        else:
            direction = TrendDirection.DECLINING

        return direction, slope


class KPIEngine:
    """
    Real-time KPI calculation and monitoring engine.

    Provides comprehensive KPI management including definition,
    calculation, trend analysis, and alerting.
    """

    # Standard QMS KPIs
    STANDARD_KPIS = [
        KPIDefinition(
            id="defect_rate_dppm",
            name="Defect Rate (DPPM)",
            description="Defects per million units produced",
            category=KPICategory.QUALITY,
            unit="DPPM",
            target=1000,
            threshold=KPIThreshold(
                warning_threshold=2000,
                critical_threshold=5000,
                direction="above"
            )
        ),
        KPIDefinition(
            id="first_pass_yield",
            name="First Pass Yield",
            description="Percentage of units passing inspection on first attempt",
            category=KPICategory.QUALITY,
            unit="%",
            target=98.0,
            threshold=KPIThreshold(
                warning_threshold=95.0,
                critical_threshold=90.0,
                direction="below"
            )
        ),
        KPIDefinition(
            id="capa_closure_rate",
            name="CAPA Closure Rate",
            description="Percentage of CAPAs closed on time",
            category=KPICategory.COMPLIANCE,
            unit="%",
            target=95.0,
            threshold=KPIThreshold(
                warning_threshold=85.0,
                critical_threshold=75.0,
                direction="below"
            )
        ),
        KPIDefinition(
            id="nc_avg_cycle_time",
            name="NC Average Cycle Time",
            description="Average days to close non-conformances",
            category=KPICategory.OPERATIONAL,
            unit="days",
            target=30,
            threshold=KPIThreshold(
                warning_threshold=45,
                critical_threshold=60,
                direction="above"
            )
        ),
        KPIDefinition(
            id="complaint_rate",
            name="Customer Complaint Rate",
            description="Complaints per 10,000 units shipped",
            category=KPICategory.CUSTOMER,
            unit="per 10k",
            target=5,
            threshold=KPIThreshold(
                warning_threshold=10,
                critical_threshold=20,
                direction="above"
            )
        ),
        KPIDefinition(
            id="training_compliance",
            name="Training Compliance",
            description="Percentage of required training completed",
            category=KPICategory.COMPLIANCE,
            unit="%",
            target=100,
            threshold=KPIThreshold(
                warning_threshold=95,
                critical_threshold=90,
                direction="below"
            )
        ),
    ]

    def __init__(self):
        self.kpis: Dict[str, KPIDefinition] = {}
        self.results: Dict[str, KPIResult] = {}
        self.history: Dict[str, List[KPIDataPoint]] = {}
        self.alerts: Dict[str, Alert] = {}
        self.calculator = KPICalculator()
        self.trend_analyzer = TrendAnalyzer()
        self.alert_handlers: List[Callable] = []
        self.logger = logging.getLogger("qms-kpi")
        self._configure_logger()
        self._register_standard_kpis()

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

    def _register_standard_kpis(self) -> None:
        """Register standard QMS KPIs."""
        for kpi in self.STANDARD_KPIS:
            self.register_kpi(kpi)

    def register_kpi(self, kpi: KPIDefinition) -> None:
        """Register a KPI definition."""
        self.kpis[kpi.id] = kpi
        self.history[kpi.id] = []
        self.logger.info(f"KPI_REGISTERED | id={kpi.id} | name={kpi.name}")

    def update_kpi(self, kpi_id: str, data: Dict[str, Any]) -> KPIResult:
        """
        Update a KPI with new data.

        Args:
            kpi_id: KPI identifier
            data: Data for KPI calculation

        Returns:
            Updated KPIResult
        """
        import uuid

        kpi = self.kpis.get(kpi_id)
        if not kpi:
            raise ValueError(f"KPI {kpi_id} not found")

        # Calculate new value
        value = self.calculator.calculate(kpi_id, data)

        # Store data point
        data_point = KPIDataPoint(
            value=value,
            timestamp=datetime.utcnow(),
            source=data.get("source", "manual"),
            metadata=data
        )
        self.history[kpi_id].append(data_point)

        # Keep history limited
        if len(self.history[kpi_id]) > 1000:
            self.history[kpi_id] = self.history[kpi_id][-500:]

        # Get previous value
        previous = self.results.get(kpi_id)
        previous_value = previous.current_value if previous else None

        # Analyze trend
        trend, slope = self.trend_analyzer.analyze(self.history[kpi_id])

        # Calculate variance
        variance = value - kpi.target
        variance_pct = (variance / kpi.target * 100) if kpi.target != 0 else 0

        # Determine status
        if abs(variance_pct) <= 5:
            status = "on_track"
        elif abs(variance_pct) <= 15:
            status = "at_risk"
        else:
            status = "off_track"

        # Create result
        result = KPIResult(
            kpi_id=kpi_id,
            current_value=value,
            previous_value=previous_value,
            target=kpi.target,
            variance_from_target=variance,
            variance_percentage=variance_pct,
            trend=trend,
            trend_slope=slope,
            status=status,
            last_updated=datetime.utcnow(),
            history=self.history[kpi_id][-10:]
        )

        self.results[kpi_id] = result

        # Check thresholds and generate alerts
        self._check_thresholds(kpi, result)

        self.logger.info(
            f"KPI_UPDATED | id={kpi_id} | value={value:.2f} | "
            f"target={kpi.target} | variance={variance_pct:.1f}% | status={status}"
        )

        return result

    def _check_thresholds(self, kpi: KPIDefinition, result: KPIResult) -> None:
        """Check thresholds and generate alerts if needed."""
        import uuid

        threshold = kpi.threshold
        value = result.current_value

        # Determine if threshold is breached
        is_warning = False
        is_critical = False

        if threshold.direction == "below":
            is_critical = value < threshold.critical_threshold
            is_warning = not is_critical and value < threshold.warning_threshold
        else:  # "above"
            is_critical = value > threshold.critical_threshold
            is_warning = not is_critical and value > threshold.warning_threshold

        if is_critical or is_warning:
            severity = AlertSeverity.CRITICAL if is_critical else AlertSeverity.WARNING
            threshold_value = threshold.critical_threshold if is_critical else threshold.warning_threshold

            alert = Alert(
                id=f"ALT-{datetime.now().strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:4].upper()}",
                kpi_id=kpi.id,
                severity=severity,
                title=f"KPI Alert: {kpi.name}",
                message=f"{kpi.name} is {severity.value}: {value:.2f} {kpi.unit} "
                       f"(threshold: {threshold_value} {kpi.unit})",
                current_value=value,
                threshold_value=threshold_value,
                created_at=datetime.utcnow()
            )

            self.alerts[alert.id] = alert
            self._notify_alert(alert)

    def _notify_alert(self, alert: Alert) -> None:
        """Notify registered alert handlers."""
        self.logger.warning(
            f"KPI_ALERT | severity={alert.severity.value} | kpi={alert.kpi_id} | "
            f"value={alert.current_value:.2f} | threshold={alert.threshold_value}"
        )
        for handler in self.alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                self.logger.error(f"Alert handler error: {e}")

    def register_alert_handler(self, handler: Callable) -> None:
        """Register an alert handler callback."""
        self.alert_handlers.append(handler)

    def get_kpi_result(self, kpi_id: str) -> Optional[KPIResult]:
        """Get current KPI result."""
        return self.results.get(kpi_id)

    def get_all_results(self) -> Dict[str, KPIResult]:
        """Get all current KPI results."""
        return self.results.copy()

    def get_kpis_by_category(self, category: KPICategory) -> List[KPIDefinition]:
        """Get KPIs by category."""
        return [k for k in self.kpis.values() if k.category == category]

    def get_active_alerts(self) -> List[Alert]:
        """Get unacknowledged alerts."""
        return [a for a in self.alerts.values() if not a.acknowledged]

    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> Alert:
        """Acknowledge an alert."""
        alert = self.alerts.get(alert_id)
        if not alert:
            raise ValueError(f"Alert {alert_id} not found")

        alert.acknowledged = True
        alert.acknowledged_by = acknowledged_by
        alert.acknowledged_at = datetime.utcnow()

        self.logger.info(f"ALERT_ACKNOWLEDGED | id={alert_id} | by={acknowledged_by}")

        return alert

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get data for dashboard display."""
        results = list(self.results.values())

        return {
            "summary": {
                "total_kpis": len(self.kpis),
                "on_track": len([r for r in results if r.status == "on_track"]),
                "at_risk": len([r for r in results if r.status == "at_risk"]),
                "off_track": len([r for r in results if r.status == "off_track"]),
                "active_alerts": len(self.get_active_alerts())
            },
            "by_category": {
                cat.value: {
                    "kpis": [
                        {
                            "id": r.kpi_id,
                            "name": self.kpis[r.kpi_id].name,
                            "value": r.current_value,
                            "target": r.target,
                            "status": r.status,
                            "trend": r.trend.value
                        }
                        for r in results if self.kpis.get(r.kpi_id, KPIDefinition("","","",cat,"",0,KPIThreshold(0,0))).category == cat
                    ]
                }
                for cat in KPICategory
            },
            "alerts": [
                {
                    "id": a.id,
                    "severity": a.severity.value,
                    "title": a.title,
                    "message": a.message,
                    "created_at": a.created_at.isoformat()
                }
                for a in self.get_active_alerts()
            ],
            "last_updated": datetime.utcnow().isoformat()
        }
