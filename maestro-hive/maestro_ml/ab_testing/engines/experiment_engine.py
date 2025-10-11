"""
Experiment Management Engine
"""

import hashlib
import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from ..models.experiment_models import (
    Experiment,
    ExperimentMetric,
    ExperimentResult,
    ExperimentStatus,
    ExperimentVariant,
    TrafficSplit,
)
from .statistical_analyzer import StatisticalAnalyzer

logger = logging.getLogger(__name__)


class ExperimentEngine:
    """
    A/B Test Experiment Engine

    Manages experiment lifecycle:
    - Creating and configuring experiments
    - Starting/stopping experiments
    - Tracking metrics
    - Analyzing results
    - Early stopping decisions
    """

    def __init__(self):
        self.logger = logger
        self.analyzer = StatisticalAnalyzer()
        self.experiments: dict[str, Experiment] = {}
        self.experiment_data: dict[str, dict[str, dict[str, list[float]]]] = {}

    def create_experiment(
        self,
        name: str,
        description: str,
        variants: list[ExperimentVariant],
        metrics: list[ExperimentMetric],
        traffic_split: TrafficSplit,
        duration_days: Optional[int] = None,
        created_by: str = "system",
        **kwargs,
    ) -> Experiment:
        """
        Create a new A/B test experiment

        Args:
            name: Experiment name
            description: Description
            variants: List of variants (must have at least 2)
            metrics: Metrics to track
            traffic_split: Traffic allocation
            duration_days: Planned duration
            created_by: Creator user ID

        Returns:
            Created experiment
        """
        # Validate
        if len(variants) < 2:
            raise ValueError("Experiment must have at least 2 variants")

        if not traffic_split.validate_weights():
            raise ValueError("Traffic split weights must sum to 100")

        # Generate experiment ID
        experiment_id = self._generate_experiment_id(name)

        # Ensure exactly one control
        control_count = sum(1 for v in variants if v.is_control)
        if control_count != 1:
            # Set first variant as control
            variants[0].is_control = True
            for v in variants[1:]:
                v.is_control = False

        # Create experiment
        experiment = Experiment(
            experiment_id=experiment_id,
            name=name,
            description=description,
            status=ExperimentStatus.DRAFT,
            variants=variants,
            traffic_split=traffic_split,
            metrics=metrics,
            duration_days=duration_days,
            created_by=created_by,
            **kwargs,
        )

        self.experiments[experiment_id] = experiment
        self.experiment_data[experiment_id] = {
            v.variant_id: {m.metric_name: [] for m in metrics} for v in variants
        }

        self.logger.info(f"Created experiment: {experiment_id} - {name}")
        return experiment

    def start_experiment(self, experiment_id: str) -> Experiment:
        """Start an experiment"""
        if experiment_id not in self.experiments:
            raise ValueError(f"Experiment {experiment_id} not found")

        experiment = self.experiments[experiment_id]

        if experiment.status != ExperimentStatus.DRAFT:
            raise ValueError(f"Cannot start experiment in status {experiment.status}")

        experiment.status = ExperimentStatus.RUNNING
        experiment.start_time = datetime.utcnow()

        if experiment.duration_days:
            experiment.end_time = experiment.start_time + timedelta(
                days=experiment.duration_days
            )

        self.logger.info(f"Started experiment: {experiment_id}")
        return experiment

    def stop_experiment(
        self, experiment_id: str, reason: str = "Manual stop"
    ) -> Experiment:
        """Stop a running experiment"""
        if experiment_id not in self.experiments:
            raise ValueError(f"Experiment {experiment_id} not found")

        experiment = self.experiments[experiment_id]
        experiment.status = ExperimentStatus.COMPLETED
        experiment.end_time = datetime.utcnow()

        self.logger.info(f"Stopped experiment: {experiment_id}. Reason: {reason}")
        return experiment

    def pause_experiment(self, experiment_id: str) -> Experiment:
        """Pause a running experiment"""
        if experiment_id not in self.experiments:
            raise ValueError(f"Experiment {experiment_id} not found")

        experiment = self.experiments[experiment_id]

        if experiment.status != ExperimentStatus.RUNNING:
            raise ValueError("Can only pause running experiments")

        experiment.status = ExperimentStatus.PAUSED
        self.logger.info(f"Paused experiment: {experiment_id}")
        return experiment

    def resume_experiment(self, experiment_id: str) -> Experiment:
        """Resume a paused experiment"""
        if experiment_id not in self.experiments:
            raise ValueError(f"Experiment {experiment_id} not found")

        experiment = self.experiments[experiment_id]

        if experiment.status != ExperimentStatus.PAUSED:
            raise ValueError("Can only resume paused experiments")

        experiment.status = ExperimentStatus.RUNNING
        self.logger.info(f"Resumed experiment: {experiment_id}")
        return experiment

    def record_metric(
        self, experiment_id: str, variant_id: str, metric_name: str, value: float
    ):
        """Record a metric value for a variant"""
        if experiment_id not in self.experiments:
            raise ValueError(f"Experiment {experiment_id} not found")

        if experiment_id not in self.experiment_data:
            raise ValueError(f"No data storage for experiment {experiment_id}")

        if variant_id not in self.experiment_data[experiment_id]:
            raise ValueError(f"Variant {variant_id} not in experiment {experiment_id}")

        if metric_name not in self.experiment_data[experiment_id][variant_id]:
            self.experiment_data[experiment_id][variant_id][metric_name] = []

        self.experiment_data[experiment_id][variant_id][metric_name].append(value)

    def record_metrics_batch(
        self, experiment_id: str, variant_id: str, metrics: dict[str, float]
    ):
        """Record multiple metrics at once"""
        for metric_name, value in metrics.items():
            self.record_metric(experiment_id, variant_id, metric_name, value)

    def get_experiment_status(self, experiment_id: str) -> dict[str, Any]:
        """Get current experiment status with sample counts"""
        if experiment_id not in self.experiments:
            raise ValueError(f"Experiment {experiment_id} not found")

        experiment = self.experiments[experiment_id]
        data = self.experiment_data[experiment_id]

        variant_samples = {}
        for variant_id, metric_data in data.items():
            # Get max sample count across metrics
            max_samples = (
                max(len(values) for values in metric_data.values())
                if metric_data
                else 0
            )
            variant_samples[variant_id] = max_samples

        total_samples = sum(variant_samples.values())

        return {
            "experiment_id": experiment_id,
            "name": experiment.name,
            "status": experiment.status,
            "start_time": experiment.start_time,
            "end_time": experiment.end_time,
            "total_samples": total_samples,
            "variant_samples": variant_samples,
            "variants": len(experiment.variants),
            "metrics": [m.metric_name for m in experiment.metrics],
        }

    def analyze_experiment(self, experiment_id: str) -> ExperimentResult:
        """Analyze experiment results"""
        if experiment_id not in self.experiments:
            raise ValueError(f"Experiment {experiment_id} not found")

        experiment = self.experiments[experiment_id]
        data = self.experiment_data[experiment_id]

        # Find control variant
        control_variant = next(v for v in experiment.variants if v.is_control)

        # Calculate experiment duration
        if experiment.start_time:
            end = experiment.end_time or datetime.utcnow()
            duration_hours = (end - experiment.start_time).total_seconds() / 3600
        else:
            duration_hours = 0

        # Perform analysis
        result = self.analyzer.analyze_experiment(
            experiment_id=experiment_id,
            experiment_name=experiment.name,
            variant_data=data,
            metrics=experiment.metrics,
            control_variant_id=control_variant.variant_id,
            status=experiment.status,
            experiment_duration_hours=duration_hours,
        )

        return result

    def check_early_stopping(self, experiment_id: str) -> tuple[bool, str]:
        """
        Check if experiment should be stopped early

        Returns:
            (should_stop, reason)
        """
        if experiment_id not in self.experiments:
            raise ValueError(f"Experiment {experiment_id} not found")

        experiment = self.experiments[experiment_id]

        if not experiment.enable_early_stopping:
            return False, "Early stopping disabled"

        # Analyze current results
        result = self.analyze_experiment(experiment_id)

        # Check data quality
        if result.data_quality_score < 0.5:
            return False, "Insufficient data quality"

        # Check if we have a clear winner
        if result.winning_variant_id and result.confidence_in_winner:
            if result.confidence_in_winner >= experiment.early_stopping_threshold:
                return (
                    True,
                    f"Clear winner found with {result.confidence_in_winner:.1%} confidence",
                )

        # Check if no difference is likely
        primary_metric = next(
            (m for m in experiment.metrics if m.is_primary), experiment.metrics[0]
        )
        primary_comparisons = [
            c for c in result.comparisons if c.metric_name == primary_metric.metric_name
        ]

        # If all comparisons show no significance with high power, can stop
        high_power_no_sig = all(
            not c.is_significant and c.statistical_power and c.statistical_power > 0.8
            for c in primary_comparisons
        )

        if high_power_no_sig:
            return True, "No significant difference detected with sufficient power"

        return False, "Continue collecting data"

    def _generate_experiment_id(self, name: str) -> str:
        """Generate unique experiment ID"""
        timestamp = datetime.utcnow().isoformat()
        content = f"{name}:{timestamp}"
        hash_hex = hashlib.sha256(content.encode()).hexdigest()
        return f"exp_{hash_hex[:12]}"

    def list_experiments(
        self,
        status: Optional[ExperimentStatus] = None,
        created_by: Optional[str] = None,
    ) -> list[Experiment]:
        """List experiments with optional filters"""
        experiments = list(self.experiments.values())

        if status:
            experiments = [e for e in experiments if e.status == status]

        if created_by:
            experiments = [e for e in experiments if e.created_by == created_by]

        # Sort by creation time, newest first
        experiments.sort(key=lambda e: e.created_at, reverse=True)

        return experiments

    def get_experiment(self, experiment_id: str) -> Experiment:
        """Get experiment by ID"""
        if experiment_id not in self.experiments:
            raise ValueError(f"Experiment {experiment_id} not found")

        return self.experiments[experiment_id]
