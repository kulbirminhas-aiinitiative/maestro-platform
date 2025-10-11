"""
Cost Reporter

Generate cost reports, summaries, and budget alerts.
"""

from typing import List, Optional, Dict
from datetime import datetime, timedelta
import uuid

from ..models.cost_models import (
    CostSummary,
    CostBreakdown,
    BudgetAlert,
    TrainingCost,
    InferenceCost
)
from .training_cost_calculator import TrainingCostCalculator
from .inference_cost_tracker import InferenceCostTracker


class CostReporter:
    """
    Generate cost reports and summaries

    Example:
        >>> reporter = CostReporter(training_calc, inference_tracker)
        >>> summary = reporter.generate_model_summary(
        >>>     model_name="fraud_detector",
        >>>     start_time=datetime.utcnow() - timedelta(days=30),
        >>>     end_time=datetime.utcnow(),
        >>>     budget_allocated=1000.0
        >>> )
        >>> print(f"Total cost: ${summary.breakdown.total_cost:.2f}")
        >>> print(f"Budget remaining: ${summary.budget_remaining:.2f}")
    """

    def __init__(
        self,
        training_calculator: TrainingCostCalculator,
        inference_tracker: InferenceCostTracker
    ):
        """
        Initialize reporter

        Args:
            training_calculator: Training cost calculator
            inference_tracker: Inference cost tracker
        """
        self.training_calc = training_calculator
        self.inference_tracker = inference_tracker

        # Budget tracking: {model_name: budget_amount}
        self.budgets: Dict[str, float] = {}

        # Budget alerts
        self.budget_alerts: List[BudgetAlert] = []

    def generate_model_summary(
        self,
        model_name: str,
        start_time: datetime,
        end_time: datetime,
        model_version: Optional[str] = None,
        budget_allocated: Optional[float] = None
    ) -> CostSummary:
        """
        Generate comprehensive cost summary for a model

        Args:
            model_name: Model identifier
            start_time: Report start time
            end_time: Report end time
            model_version: Specific version (None = all versions)
            budget_allocated: Budget for this period

        Returns:
            CostSummary with complete breakdown
        """
        duration = end_time - start_time
        duration_days = duration.total_seconds() / (24 * 3600)

        # Get training costs
        training_costs = self.training_calc.get_model_training_costs(model_name, model_version)
        training_costs = [c for c in training_costs if start_time <= c.end_time <= end_time]

        total_training_cost = sum(c.total_cost for c in training_costs)
        total_training_hours = sum(c.duration_hours for c in training_costs)
        total_training_jobs = len(training_costs)

        # Get inference costs
        inference_costs = self.inference_tracker.get_model_inference_costs(model_name, model_version)
        inference_costs = [c for c in inference_costs if start_time <= c.end_time <= end_time]

        total_inference_cost = sum(c.total_cost for c in inference_costs)
        total_inference_requests = sum(c.total_requests for c in inference_costs)
        total_inference_hours = sum(c.duration_hours for c in inference_costs)

        # Build breakdown
        breakdown = CostBreakdown(
            compute_cost=sum(c.compute_cost for c in training_costs) + sum(c.compute_cost for c in inference_costs),
            storage_cost=sum(c.storage_cost for c in training_costs) + sum(c.storage_cost for c in inference_costs),
            network_cost=sum(c.network_cost for c in training_costs) + sum(c.network_cost for c in inference_costs),
            training_cost=total_training_cost,
            inference_cost=total_inference_cost,
            data_processing_cost=0.0,  # Could be added later
            total_cost=total_training_cost + total_inference_cost
        )

        # Calculate daily/weekly/monthly if period allows
        if duration_days >= 1:
            breakdown.daily_cost = breakdown.total_cost / duration_days
        if duration_days >= 7:
            breakdown.weekly_cost = breakdown.total_cost / (duration_days / 7)
        if duration_days >= 30:
            breakdown.monthly_cost = breakdown.total_cost / (duration_days / 30)

        # Efficiency metrics
        avg_cost_per_day = breakdown.total_cost / duration_days if duration_days > 0 else 0
        avg_cost_per_training_job = total_training_cost / total_training_jobs if total_training_jobs > 0 else None
        avg_cost_per_1k_requests = (total_inference_cost / total_inference_requests * 1000) if total_inference_requests > 0 else None

        # Budget tracking
        budget_used = breakdown.total_cost
        budget_remaining = None
        budget_utilization_pct = None

        if budget_allocated:
            budget_remaining = budget_allocated - budget_used
            budget_utilization_pct = (budget_used / budget_allocated * 100) if budget_allocated > 0 else 0

            # Check for budget alerts
            self._check_budget_alerts(
                model_name=model_name,
                budget_allocated=budget_allocated,
                budget_used=budget_used,
                period_start=start_time,
                period_end=end_time
            )

        # Determine cost trend (if we have historical data)
        cost_trend = self._determine_cost_trend(model_name, start_time, end_time, breakdown.total_cost)

        return CostSummary(
            model_name=model_name,
            start_time=start_time,
            end_time=end_time,
            duration_days=duration_days,
            breakdown=breakdown,
            total_training_jobs=total_training_jobs,
            total_training_hours=total_training_hours,
            total_training_cost=total_training_cost,
            total_inference_requests=total_inference_requests,
            total_inference_hours=total_inference_hours,
            total_inference_cost=total_inference_cost,
            avg_cost_per_day=avg_cost_per_day,
            avg_cost_per_training_job=avg_cost_per_training_job,
            avg_cost_per_1k_requests=avg_cost_per_1k_requests,
            budget_allocated=budget_allocated,
            budget_used=budget_used,
            budget_remaining=budget_remaining,
            budget_utilization_pct=budget_utilization_pct,
            cost_trend=cost_trend
        )

    def set_budget(self, model_name: str, budget_amount: float) -> None:
        """Set budget for a model"""
        self.budgets[model_name] = budget_amount

    def get_budget(self, model_name: str) -> Optional[float]:
        """Get budget for a model"""
        return self.budgets.get(model_name)

    def _check_budget_alerts(
        self,
        model_name: str,
        budget_allocated: float,
        budget_used: float,
        period_start: datetime,
        period_end: datetime
    ) -> None:
        """Check if budget thresholds are crossed and create alerts"""
        utilization_pct = (budget_used / budget_allocated * 100) if budget_allocated > 0 else 0
        budget_remaining = budget_allocated - budget_used

        # Define thresholds
        thresholds = [
            (80, "warning"),
            (90, "warning"),
            (100, "critical"),
            (110, "critical")
        ]

        for threshold_pct, severity in thresholds:
            if utilization_pct >= threshold_pct:
                # Check if we've already alerted for this threshold
                existing = any(
                    a.model_name == model_name and a.threshold_pct == threshold_pct
                    for a in self.budget_alerts
                )

                if not existing:
                    alert = BudgetAlert(
                        alert_id=f"budget_{uuid.uuid4().hex[:12]}",
                        model_name=model_name,
                        budget_allocated=budget_allocated,
                        budget_used=budget_used,
                        budget_remaining=budget_remaining,
                        utilization_pct=utilization_pct,
                        threshold_pct=threshold_pct,
                        severity=severity,
                        message=f"{severity.upper()}: Budget {utilization_pct:.1f}% utilized for {model_name} (${budget_used:.2f}/${budget_allocated:.2f})",
                        period_start=period_start,
                        period_end=period_end
                    )
                    self.budget_alerts.append(alert)

    def get_budget_alerts(
        self,
        model_name: Optional[str] = None,
        severity: Optional[str] = None
    ) -> List[BudgetAlert]:
        """Get budget alerts"""
        alerts = self.budget_alerts

        if model_name:
            alerts = [a for a in alerts if a.model_name == model_name]

        if severity:
            alerts = [a for a in alerts if a.severity == severity]

        return alerts

    def _determine_cost_trend(
        self,
        model_name: str,
        start_time: datetime,
        end_time: datetime,
        current_cost: float
    ) -> Optional[str]:
        """Determine if costs are trending up, down, or stable"""
        # Get historical costs from previous period (same duration)
        duration = end_time - start_time
        prev_end = start_time
        prev_start = prev_end - duration

        prev_training = self.training_calc.get_total_training_cost(
            model_name=model_name,
            start_time=prev_start,
            end_time=prev_end
        )

        prev_inference = self.inference_tracker.get_total_inference_cost(
            model_name=model_name,
            start_time=prev_start,
            end_time=prev_end
        )

        prev_cost = prev_training + prev_inference

        if prev_cost == 0:
            return None  # No historical data

        change_pct = ((current_cost - prev_cost) / prev_cost * 100)

        if change_pct > 10:
            return "increasing"
        elif change_pct < -10:
            return "decreasing"
        else:
            return "stable"

    def compare_models(
        self,
        model_names: List[str],
        start_time: datetime,
        end_time: datetime
    ) -> List[CostSummary]:
        """Compare costs across multiple models"""
        summaries = []

        for model_name in model_names:
            summary = self.generate_model_summary(
                model_name=model_name,
                start_time=start_time,
                end_time=end_time
            )
            summaries.append(summary)

        # Sort by total cost (descending)
        summaries.sort(key=lambda s: s.breakdown.total_cost, reverse=True)

        return summaries
