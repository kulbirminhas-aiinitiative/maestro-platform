"""
Data Profiling Orchestrator

Main interface for running complete data quality and drift analysis.
"""

import pandas as pd
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

from .metrics.quality_metrics import QualityMetricsCalculator, DatasetQualityReport
from .drift.drift_detector import DriftDetector, DriftReport


class ComprehensiveProfilingReport(BaseModel):
    """Complete profiling report with quality and drift analysis"""
    dataset_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Quality analysis
    quality_report: DatasetQualityReport

    # Drift analysis (if baseline provided)
    drift_report: Optional[DriftReport] = None

    # Summary
    overall_health: str = Field(..., description="excellent, good, fair, poor")
    action_required: bool = False
    priority_actions: list = Field(default_factory=list)


class DataProfiler:
    """
    Complete data profiling orchestrator

    Runs quality metrics and drift detection in one go.

    Example:
        >>> profiler = DataProfiler()
        >>> df = pd.read_csv("data.csv")
        >>> report = profiler.profile(df, dataset_name="production_data")
        >>> print(f"Overall quality: {report.quality_report.overall_score:.1f}%")
        >>> if report.drift_report:
        >>>     print(f"Drift detected: {report.drift_report.drift_detected}")
    """

    def __init__(self):
        self.quality_calculator = QualityMetricsCalculator()
        self.drift_detector = DriftDetector()

    def profile(
        self,
        df: pd.DataFrame,
        dataset_name: str = "dataset",
        baseline_df: Optional[pd.DataFrame] = None,
        baseline_timestamp: Optional[datetime] = None
    ) -> ComprehensiveProfilingReport:
        """
        Run complete profiling analysis

        Args:
            df: Current dataset to profile
            dataset_name: Dataset identifier
            baseline_df: Optional baseline dataset for drift detection
            baseline_timestamp: Timestamp of baseline data

        Returns:
            ComprehensiveProfilingReport with quality and drift analysis
        """
        # Quality metrics
        quality_report = self.quality_calculator.calculate(df, dataset_name)

        # Drift detection (if baseline provided)
        drift_report = None
        if baseline_df is not None:
            drift_report = self.drift_detector.detect(
                baseline_df,
                df,
                dataset_name,
                baseline_timestamp
            )

        # Determine overall health
        overall_health = self._assess_health(quality_report, drift_report)

        # Determine priority actions
        action_required, priority_actions = self._determine_actions(
            quality_report,
            drift_report
        )

        return ComprehensiveProfilingReport(
            dataset_name=dataset_name,
            quality_report=quality_report,
            drift_report=drift_report,
            overall_health=overall_health,
            action_required=action_required,
            priority_actions=priority_actions
        )

    def _assess_health(
        self,
        quality_report: DatasetQualityReport,
        drift_report: Optional[DriftReport]
    ) -> str:
        """Assess overall dataset health"""
        score = quality_report.overall_score

        # Penalize for drift
        if drift_report and drift_report.retraining_recommended:
            score -= 10

        if score >= 90:
            return "excellent"
        elif score >= 75:
            return "good"
        elif score >= 60:
            return "fair"
        else:
            return "poor"

    def _determine_actions(
        self,
        quality_report: DatasetQualityReport,
        drift_report: Optional[DriftReport]
    ) -> tuple:
        """Determine if action is required and what actions"""
        priority_actions = []
        action_required = False

        # Quality-based actions
        if quality_report.overall_score < 70:
            action_required = True
            priority_actions.append("🚨 Data quality below threshold - immediate attention required")

        if len(quality_report.critical_issues) > 0:
            action_required = True
            priority_actions.append(
                f"⚠️ Fix {len(quality_report.critical_issues)} critical data quality issues"
            )

        if quality_report.missing_percentage > 20:
            action_required = True
            priority_actions.append("📊 High missing data rate - investigate data collection")

        # Drift-based actions
        if drift_report:
            if drift_report.retraining_recommended:
                action_required = True
                priority_actions.append("🔄 Model retraining recommended due to data drift")

            if len(drift_report.severe_drift_features) > 0:
                action_required = True
                priority_actions.append(
                    f"🔍 Investigate severe drift in: {', '.join(drift_report.severe_drift_features[:3])}"
                )

        return action_required, priority_actions

    def quick_profile(self, df: pd.DataFrame, dataset_name: str = "dataset"):
        """Quick profiling without drift detection"""
        return self.profile(df, dataset_name, baseline_df=None)
