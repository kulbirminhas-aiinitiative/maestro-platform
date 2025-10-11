"""
SLA Monitoring and Metrics Tracking
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class SLAMetric(str, Enum):
    """SLA metrics"""

    UPTIME = "uptime"
    LATENCY_P99 = "latency_p99"
    LATENCY_P95 = "latency_p95"
    ERROR_RATE = "error_rate"
    AVAILABILITY = "availability"


class SLATarget(BaseModel):
    """SLA target definition"""

    metric: SLAMetric
    target_value: float
    unit: str  # %, ms, etc.
    description: str


class SLAStatus(BaseModel):
    """SLA status"""

    metric: SLAMetric
    target: float
    current: float
    is_meeting_sla: bool
    period_start: datetime
    period_end: datetime


class SLAMonitor:
    """
    SLA monitoring and tracking

    Features:
    - Uptime monitoring (99.9%, 99.99%)
    - Latency tracking (P95, P99)
    - Error rate monitoring
    - SLA breach alerts
    - Historical SLA reports
    """

    def __init__(self):
        self.targets: dict[SLAMetric, SLATarget] = {}
        self.metrics_data: dict[SLAMetric, list[float]] = defaultdict(list)
        self.downtime_events: list[tuple[datetime, datetime]] = []
        self.logger = logger

        # Set default SLA targets
        self._set_default_targets()

    def _set_default_targets(self):
        """Set industry-standard SLA targets"""
        self.targets = {
            SLAMetric.UPTIME: SLATarget(
                metric=SLAMetric.UPTIME,
                target_value=99.9,
                unit="%",
                description="99.9% uptime (43.2 min downtime/month)",
            ),
            SLAMetric.LATENCY_P99: SLATarget(
                metric=SLAMetric.LATENCY_P99,
                target_value=500,
                unit="ms",
                description="P99 latency under 500ms",
            ),
            SLAMetric.LATENCY_P95: SLATarget(
                metric=SLAMetric.LATENCY_P95,
                target_value=200,
                unit="ms",
                description="P95 latency under 200ms",
            ),
            SLAMetric.ERROR_RATE: SLATarget(
                metric=SLAMetric.ERROR_RATE,
                target_value=0.1,
                unit="%",
                description="Error rate under 0.1%",
            ),
            SLAMetric.AVAILABILITY: SLATarget(
                metric=SLAMetric.AVAILABILITY,
                target_value=99.95,
                unit="%",
                description="99.95% availability",
            ),
        }

    def record_metric(self, metric: SLAMetric, value: float):
        """Record a metric value"""
        self.metrics_data[metric].append(value)

    def record_downtime(self, start: datetime, end: datetime):
        """Record a downtime event"""
        self.downtime_events.append((start, end))
        self.logger.warning(f"Downtime recorded: {start} to {end}")

    def calculate_uptime(self, start_time: datetime, end_time: datetime) -> float:
        """
        Calculate uptime percentage

        Args:
            start_time: Period start
            end_time: Period end

        Returns:
            Uptime percentage
        """
        total_seconds = (end_time - start_time).total_seconds()
        downtime_seconds = 0.0

        for down_start, down_end in self.downtime_events:
            # Check if downtime overlaps with period
            if down_end < start_time or down_start > end_time:
                continue

            # Calculate overlap
            overlap_start = max(down_start, start_time)
            overlap_end = min(down_end, end_time)
            downtime_seconds += (overlap_end - overlap_start).total_seconds()

        uptime_seconds = total_seconds - downtime_seconds
        uptime_pct = (
            (uptime_seconds / total_seconds) * 100 if total_seconds > 0 else 100.0
        )

        return uptime_pct

    def check_sla_status(
        self, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None
    ) -> list[SLAStatus]:
        """
        Check current SLA status

        Args:
            start_time: Period start (default: 30 days ago)
            end_time: Period end (default: now)

        Returns:
            List of SLA status for each metric
        """
        if end_time is None:
            end_time = datetime.utcnow()
        if start_time is None:
            start_time = end_time - timedelta(days=30)

        statuses = []

        # Uptime
        if SLAMetric.UPTIME in self.targets:
            target = self.targets[SLAMetric.UPTIME]
            current_uptime = self.calculate_uptime(start_time, end_time)

            statuses.append(
                SLAStatus(
                    metric=SLAMetric.UPTIME,
                    target=target.target_value,
                    current=current_uptime,
                    is_meeting_sla=current_uptime >= target.target_value,
                    period_start=start_time,
                    period_end=end_time,
                )
            )

        # Latency P99
        if (
            SLAMetric.LATENCY_P99 in self.targets
            and self.metrics_data[SLAMetric.LATENCY_P99]
        ):
            target = self.targets[SLAMetric.LATENCY_P99]
            latencies = sorted(self.metrics_data[SLAMetric.LATENCY_P99])
            p99_idx = int(len(latencies) * 0.99)
            current_p99 = latencies[p99_idx] if latencies else 0

            statuses.append(
                SLAStatus(
                    metric=SLAMetric.LATENCY_P99,
                    target=target.target_value,
                    current=current_p99,
                    is_meeting_sla=current_p99 <= target.target_value,
                    period_start=start_time,
                    period_end=end_time,
                )
            )

        # Latency P95
        if (
            SLAMetric.LATENCY_P95 in self.targets
            and self.metrics_data[SLAMetric.LATENCY_P95]
        ):
            target = self.targets[SLAMetric.LATENCY_P95]
            latencies = sorted(self.metrics_data[SLAMetric.LATENCY_P95])
            p95_idx = int(len(latencies) * 0.95)
            current_p95 = latencies[p95_idx] if latencies else 0

            statuses.append(
                SLAStatus(
                    metric=SLAMetric.LATENCY_P95,
                    target=target.target_value,
                    current=current_p95,
                    is_meeting_sla=current_p95 <= target.target_value,
                    period_start=start_time,
                    period_end=end_time,
                )
            )

        # Error rate
        if (
            SLAMetric.ERROR_RATE in self.targets
            and self.metrics_data[SLAMetric.ERROR_RATE]
        ):
            target = self.targets[SLAMetric.ERROR_RATE]
            error_rates = self.metrics_data[SLAMetric.ERROR_RATE]
            avg_error_rate = sum(error_rates) / len(error_rates) if error_rates else 0

            statuses.append(
                SLAStatus(
                    metric=SLAMetric.ERROR_RATE,
                    target=target.target_value,
                    current=avg_error_rate,
                    is_meeting_sla=avg_error_rate <= target.target_value,
                    period_start=start_time,
                    period_end=end_time,
                )
            )

        return statuses

    def get_sla_report(
        self, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None
    ) -> dict:
        """
        Generate SLA report

        Args:
            start_time: Period start
            end_time: Period end

        Returns:
            SLA report dict
        """
        statuses = self.check_sla_status(start_time, end_time)

        all_meeting = all(s.is_meeting_sla for s in statuses)

        return {
            "period_start": statuses[0].period_start if statuses else None,
            "period_end": statuses[0].period_end if statuses else None,
            "overall_sla_met": all_meeting,
            "metrics": [
                {
                    "metric": s.metric.value,
                    "target": s.target,
                    "current": s.current,
                    "is_meeting_sla": s.is_meeting_sla,
                    "status": "✓" if s.is_meeting_sla else "✗",
                }
                for s in statuses
            ],
            "downtime_events": len(self.downtime_events),
        }
