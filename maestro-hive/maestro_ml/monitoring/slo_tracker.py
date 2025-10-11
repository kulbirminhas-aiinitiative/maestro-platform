"""
SLO/SLI Tracking System

Tracks Service Level Objectives and Service Level Indicators:
- Availability SLO
- Latency SLO
- Error budget tracking
- SLO compliance reporting
- Multi-window error budgets

Based on Google SRE practices.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum
import time
import json
import logging

logger = logging.getLogger(__name__)


class SLOStatus(Enum):
    """SLO compliance status"""
    HEALTHY = "healthy"          # Well within SLO
    WARNING = "warning"          # Close to violating SLO
    VIOLATED = "violated"        # SLO violated
    CRITICAL = "critical"        # Severely violated


@dataclass
class SLOTarget:
    """
    Defines an SLO target

    Example:
        SLOTarget(
            name="API Availability",
            target=0.999,  # 99.9%
            description="API returns non-5xx responses"
        )
    """
    name: str
    target: float  # 0.0 to 1.0 (e.g., 0.999 = 99.9%)
    description: str
    window_days: int = 30  # Rolling window in days


@dataclass
class SLI:
    """
    Service Level Indicator measurement

    Example:
        SLI(
            timestamp=datetime.utcnow(),
            value=0.9995,  # 99.95%
            total_requests=10000,
            successful_requests=9995
        )
    """
    timestamp: datetime
    value: float  # 0.0 to 1.0
    total_requests: int = 0
    successful_requests: int = 0
    metadata: Dict = field(default_factory=dict)


@dataclass
class ErrorBudget:
    """
    Error budget tracking

    Example:
        budget = ErrorBudget(
            slo_target=0.999,
            window_days=30,
            total_budget=0.001  # 0.1% allowed error rate
        )
    """
    slo_target: float
    window_days: int
    total_budget: float  # 1 - slo_target (e.g., 0.001 for 99.9%)
    consumed: float = 0.0  # Amount of budget consumed
    remaining: float = 0.0  # Amount of budget remaining
    burn_rate: float = 0.0  # Current burn rate (1.0 = normal, >1.0 = faster)

    @property
    def remaining_percentage(self) -> float:
        """Get remaining budget as percentage (0-100)"""
        if self.total_budget == 0:
            return 100.0
        return (self.remaining / self.total_budget) * 100.0

    @property
    def consumed_percentage(self) -> float:
        """Get consumed budget as percentage (0-100)"""
        if self.total_budget == 0:
            return 0.0
        return (self.consumed / self.total_budget) * 100.0


@dataclass
class SLOReport:
    """
    SLO compliance report

    Example:
        report = SLOReport(
            slo_name="API Availability",
            slo_target=0.999,
            current_sli=0.9995,
            status=SLOStatus.HEALTHY,
            error_budget=budget
        )
    """
    slo_name: str
    slo_target: float
    current_sli: float
    status: SLOStatus
    error_budget: ErrorBudget
    window_start: datetime
    window_end: datetime
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0

    def to_dict(self) -> Dict:
        return {
            "slo_name": self.slo_name,
            "slo_target": self.slo_target,
            "current_sli": self.current_sli,
            "status": self.status.value,
            "error_budget": {
                "total": self.error_budget.total_budget,
                "consumed": self.error_budget.consumed,
                "remaining": self.error_budget.remaining,
                "remaining_percentage": self.error_budget.remaining_percentage,
                "burn_rate": self.error_budget.burn_rate
            },
            "window": {
                "start": self.window_start.isoformat(),
                "end": self.window_end.isoformat(),
                "days": self.error_budget.window_days
            },
            "requests": {
                "total": self.total_requests,
                "successful": self.successful_requests,
                "failed": self.failed_requests,
                "success_rate": self.current_sli
            }
        }


class SLOTracker:
    """
    Tracks SLOs and calculates error budgets

    Usage:
        tracker = SLOTracker()

        # Define SLO
        tracker.add_slo(SLOTarget(
            name="api_availability",
            target=0.999,
            description="API availability",
            window_days=30
        ))

        # Record measurements
        tracker.record_sli("api_availability", SLI(
            timestamp=datetime.utcnow(),
            value=0.9995,
            total_requests=1000,
            successful_requests=999
        ))

        # Get report
        report = tracker.get_slo_report("api_availability")
        print(f"Status: {report.status.value}")
        print(f"Error budget remaining: {report.error_budget.remaining_percentage}%")
    """

    def __init__(self):
        self.slos: Dict[str, SLOTarget] = {}
        self.sli_history: Dict[str, List[SLI]] = {}

    def add_slo(self, slo: SLOTarget):
        """Add an SLO to track"""
        self.slos[slo.name] = slo
        if slo.name not in self.sli_history:
            self.sli_history[slo.name] = []
        logger.info(f"Added SLO: {slo.name} (target: {slo.target * 100}%)")

    def record_sli(self, slo_name: str, sli: SLI):
        """Record an SLI measurement"""
        if slo_name not in self.slos:
            logger.warning(f"SLO {slo_name} not defined, skipping SLI")
            return

        self.sli_history[slo_name].append(sli)

        # Trim old measurements outside the window
        slo = self.slos[slo_name]
        cutoff = datetime.utcnow() - timedelta(days=slo.window_days)
        self.sli_history[slo_name] = [
            s for s in self.sli_history[slo_name]
            if s.timestamp > cutoff
        ]

    def get_slo_report(self, slo_name: str) -> Optional[SLOReport]:
        """Generate SLO compliance report"""
        if slo_name not in self.slos:
            logger.error(f"SLO {slo_name} not found")
            return None

        slo = self.slos[slo_name]
        measurements = self.sli_history.get(slo_name, [])

        if not measurements:
            logger.warning(f"No SLI measurements for {slo_name}")
            return None

        # Calculate time window
        window_end = datetime.utcnow()
        window_start = window_end - timedelta(days=slo.window_days)

        # Calculate SLI for the window
        total_requests = sum(m.total_requests for m in measurements)
        successful_requests = sum(m.successful_requests for m in measurements)

        if total_requests == 0:
            current_sli = 1.0
        else:
            current_sli = successful_requests / total_requests

        # Calculate error budget
        error_budget = self._calculate_error_budget(
            slo_target=slo.target,
            current_sli=current_sli,
            window_days=slo.window_days,
            measurements=measurements
        )

        # Determine status
        status = self._determine_status(slo.target, current_sli, error_budget)

        return SLOReport(
            slo_name=slo.name,
            slo_target=slo.target,
            current_sli=current_sli,
            status=status,
            error_budget=error_budget,
            window_start=window_start,
            window_end=window_end,
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=total_requests - successful_requests
        )

    def _calculate_error_budget(
        self,
        slo_target: float,
        current_sli: float,
        window_days: int,
        measurements: List[SLI]
    ) -> ErrorBudget:
        """Calculate error budget"""
        # Total budget = 1 - SLO target
        total_budget = 1.0 - slo_target

        # Consumed budget = SLO target - current SLI
        # (positive if we're below target)
        consumed = max(0, slo_target - current_sli)

        # Remaining budget
        remaining = max(0, total_budget - consumed)

        # Calculate burn rate (how fast we're consuming budget)
        # Burn rate of 1.0 means we're on track to exactly hit the SLO
        # Burn rate > 1.0 means we're burning budget faster than expected
        if total_budget > 0:
            expected_consumption_rate = total_budget / window_days
            if len(measurements) > 1:
                # Calculate recent burn rate (last 1 hour)
                recent_cutoff = datetime.utcnow() - timedelta(hours=1)
                recent_measurements = [m for m in measurements if m.timestamp > recent_cutoff]

                if recent_measurements:
                    recent_total = sum(m.total_requests for m in recent_measurements)
                    recent_successful = sum(m.successful_requests for m in recent_measurements)

                    if recent_total > 0:
                        recent_sli = recent_successful / recent_total
                        recent_error_rate = 1.0 - recent_sli
                        burn_rate = recent_error_rate / total_budget if total_budget > 0 else 0
                    else:
                        burn_rate = 0
                else:
                    burn_rate = consumed / total_budget if total_budget > 0 else 0
            else:
                burn_rate = consumed / total_budget if total_budget > 0 else 0
        else:
            burn_rate = 0

        return ErrorBudget(
            slo_target=slo_target,
            window_days=window_days,
            total_budget=total_budget,
            consumed=consumed,
            remaining=remaining,
            burn_rate=burn_rate
        )

    def _determine_status(
        self,
        slo_target: float,
        current_sli: float,
        error_budget: ErrorBudget
    ) -> SLOStatus:
        """Determine SLO compliance status"""
        # SLO violated
        if current_sli < slo_target:
            # Check if severely violated
            if error_budget.consumed_percentage > 100:
                return SLOStatus.CRITICAL
            return SLOStatus.VIOLATED

        # SLO met, check error budget
        if error_budget.remaining_percentage < 10:
            return SLOStatus.WARNING

        # Check burn rate
        if error_budget.burn_rate > 5:
            return SLOStatus.WARNING

        return SLOStatus.HEALTHY

    def get_all_reports(self) -> List[SLOReport]:
        """Get reports for all SLOs"""
        reports = []
        for slo_name in self.slos.keys():
            report = self.get_slo_report(slo_name)
            if report:
                reports.append(report)
        return reports


# ============================================================================
# Multi-Window Error Budget (Google SRE Practice)
# ============================================================================

@dataclass
class MultiWindowBudget:
    """
    Multi-window error budget for more responsive alerting

    Based on Google SRE practices:
    - 1 hour: Fast burn, alerts on immediate issues
    - 6 hours: Medium burn
    - 3 days: Slow burn
    - 30 days: Overall budget
    """
    window_1h: ErrorBudget
    window_6h: ErrorBudget
    window_3d: ErrorBudget
    window_30d: ErrorBudget

    @property
    def is_fast_burn(self) -> bool:
        """Check if burning budget too fast (1h window)"""
        return self.window_1h.burn_rate > 14.4  # 2% of 30d budget in 1h

    @property
    def is_medium_burn(self) -> bool:
        """Check if medium burn (6h window)"""
        return self.window_6h.burn_rate > 6  # 10% of 30d budget in 6h

    @property
    def is_slow_burn(self) -> bool:
        """Check if slow burn (3d window)"""
        return self.window_3d.burn_rate > 1  # Normal consumption rate


class AdvancedSLOTracker(SLOTracker):
    """
    Advanced SLO tracker with multi-window error budgets

    Usage:
        tracker = AdvancedSLOTracker()
        tracker.add_slo(SLOTarget(name="api", target=0.999))

        # Record measurement
        tracker.record_sli("api", SLI(...))

        # Check multi-window budget
        multi_budget = tracker.get_multi_window_budget("api")
        if multi_budget.is_fast_burn:
            print("ALERT: Fast error budget burn!")
    """

    def get_multi_window_budget(self, slo_name: str) -> Optional[MultiWindowBudget]:
        """Get multi-window error budget"""
        if slo_name not in self.slos:
            return None

        slo = self.slos[slo_name]
        measurements = self.sli_history.get(slo_name, [])

        if not measurements:
            return None

        # Calculate budgets for each window
        windows = [
            (timedelta(hours=1), "1h"),
            (timedelta(hours=6), "6h"),
            (timedelta(days=3), "3d"),
            (timedelta(days=30), "30d")
        ]

        budgets = {}
        for window_delta, window_name in windows:
            cutoff = datetime.utcnow() - window_delta
            window_measurements = [m for m in measurements if m.timestamp > cutoff]

            if window_measurements:
                total = sum(m.total_requests for m in window_measurements)
                successful = sum(m.successful_requests for m in window_measurements)

                if total > 0:
                    sli = successful / total
                else:
                    sli = 1.0

                budget = self._calculate_error_budget(
                    slo_target=slo.target,
                    current_sli=sli,
                    window_days=window_delta.days if window_delta.days > 0 else 1,
                    measurements=window_measurements
                )
                budgets[window_name] = budget
            else:
                # No data for this window
                budgets[window_name] = ErrorBudget(
                    slo_target=slo.target,
                    window_days=window_delta.days if window_delta.days > 0 else 1,
                    total_budget=1.0 - slo.target,
                    consumed=0.0,
                    remaining=1.0 - slo.target,
                    burn_rate=0.0
                )

        return MultiWindowBudget(
            window_1h=budgets["1h"],
            window_6h=budgets["6h"],
            window_3d=budgets["3d"],
            window_30d=budgets["30d"]
        )


# ============================================================================
# SLO Definitions (Common)
# ============================================================================

# Availability SLO: 99.9% (43 minutes downtime per month)
SLO_AVAILABILITY_999 = SLOTarget(
    name="availability_999",
    target=0.999,
    description="99.9% availability (3 nines)",
    window_days=30
)

# Availability SLO: 99.95% (21 minutes downtime per month)
SLO_AVAILABILITY_9995 = SLOTarget(
    name="availability_9995",
    target=0.9995,
    description="99.95% availability",
    window_days=30
)

# Latency SLO: 95% of requests < 500ms
SLO_LATENCY_P95_500MS = SLOTarget(
    name="latency_p95_500ms",
    target=0.95,
    description="95% of requests < 500ms",
    window_days=30
)

# Latency SLO: 99% of requests < 1s
SLO_LATENCY_P99_1S = SLOTarget(
    name="latency_p99_1s",
    target=0.99,
    description="99% of requests < 1s",
    window_days=30
)


# ============================================================================
# Usage Examples
# ============================================================================

"""
1. Basic Usage:

   from monitoring.slo_tracker import SLOTracker, SLOTarget, SLI
   from datetime import datetime

   tracker = SLOTracker()

   # Define SLO
   tracker.add_slo(SLOTarget(
       name="api_availability",
       target=0.999,
       description="API availability SLO",
       window_days=30
   ))

   # Record measurements
   tracker.record_sli("api_availability", SLI(
       timestamp=datetime.utcnow(),
       value=0.9995,
       total_requests=10000,
       successful_requests=9995
   ))

   # Get report
   report = tracker.get_slo_report("api_availability")
   print(f"SLO Status: {report.status.value}")
   print(f"Current SLI: {report.current_sli * 100}%")
   print(f"Error Budget Remaining: {report.error_budget.remaining_percentage}%")

2. Multi-Window Error Budget:

   from monitoring.slo_tracker import AdvancedSLOTracker

   tracker = AdvancedSLOTracker()
   tracker.add_slo(SLOTarget(name="api", target=0.999))

   # Record measurements...

   # Check multi-window budget
   budget = tracker.get_multi_window_budget("api")

   if budget.is_fast_burn:
       print("CRITICAL: Fast error budget burn rate!")
   elif budget.is_medium_burn:
       print("WARNING: Medium error budget burn rate")
   elif budget.is_slow_burn:
       print("INFO: Normal error budget consumption")

3. Integration with Metrics:

   from monitoring.metrics_collector import metrics_collector
   from monitoring.slo_tracker import SLOTracker, SLI

   tracker = SLOTracker()
   tracker.add_slo(SLOTarget(name="api", target=0.999))

   # Periodically calculate SLI from metrics
   import time

   def update_slo_metrics():
       # Get metrics from Prometheus or calculate from request counters
       total = 10000
       successful = 9990

       # Record SLI
       tracker.record_sli("api", SLI(
           timestamp=datetime.utcnow(),
           value=successful / total,
           total_requests=total,
           successful_requests=successful
       ))

       # Update Prometheus metrics
       report = tracker.get_slo_report("api")
       if report:
           metrics_collector.set_slo_success_rate("api", report.current_sli)
           metrics_collector.set_error_budget_remaining(
               "api",
               report.error_budget.remaining_percentage
           )

   # Run periodically
   while True:
       update_slo_metrics()
       time.sleep(60)

4. Alert on SLO Violation:

   report = tracker.get_slo_report("api")

   if report.status == SLOStatus.CRITICAL:
       send_pagerduty_alert(f"CRITICAL: SLO severely violated ({report.current_sli * 100}%)")
   elif report.status == SLOStatus.VIOLATED:
       send_slack_alert(f"WARNING: SLO violated ({report.current_sli * 100}%)")
   elif report.status == SLOStatus.WARNING:
       send_email_alert(f"INFO: Error budget low ({report.error_budget.remaining_percentage}%)")

5. Generate JSON Report:

   import json

   reports = tracker.get_all_reports()
   report_data = [r.to_dict() for r in reports]

   with open("slo_report.json", "w") as f:
       json.dump(report_data, f, indent=2)
"""
