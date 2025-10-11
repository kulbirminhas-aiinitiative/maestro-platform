"""
Data Drift Detection

Detects distribution changes between baseline and current datasets.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime
from scipy import stats
from enum import Enum


class DriftMethod(str, Enum):
    """Drift detection methods"""
    KS_TEST = "ks_test"  # Kolmogorov-Smirnov
    CHI_SQUARE = "chi_square"
    PSI = "psi"  # Population Stability Index
    WASSERSTEIN = "wasserstein"


class DriftSeverity(str, Enum):
    """Drift severity levels"""
    NO_DRIFT = "no_drift"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    SEVERE = "severe"


class FeatureDrift(BaseModel):
    """Drift detection result for a single feature"""
    feature_name: str
    method: DriftMethod

    # Test statistics
    statistic: float
    p_value: Optional[float] = None

    # Drift assessment
    drift_detected: bool
    drift_severity: DriftSeverity
    drift_score: float = Field(..., ge=0, le=1, description="Normalized drift score")

    # Distribution comparison
    baseline_mean: Optional[float] = None
    current_mean: Optional[float] = None
    baseline_std: Optional[float] = None
    current_std: Optional[float] = None

    # Additional metrics
    recommendation: str


class DriftReport(BaseModel):
    """Complete drift detection report"""
    dataset_name: str
    baseline_timestamp: datetime
    current_timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Overall assessment
    drift_detected: bool
    drift_features_count: int
    total_features_analyzed: int
    drift_percentage: float

    # Per-feature drift
    feature_drifts: List[FeatureDrift] = Field(default_factory=list)

    # Severity breakdown
    severe_drift_features: List[str] = Field(default_factory=list)
    high_drift_features: List[str] = Field(default_factory=list)
    medium_drift_features: List[str] = Field(default_factory=list)

    # Recommendations
    recommendations: List[str] = Field(default_factory=list)
    retraining_recommended: bool = False


class DriftDetector:
    """
    Detect data drift between baseline and current datasets

    Example:
        >>> detector = DriftDetector()
        >>> baseline_df = pd.read_csv("baseline.csv")
        >>> current_df = pd.read_csv("current.csv")
        >>> drift_report = detector.detect(baseline_df, current_df)
        >>> if drift_report.drift_detected:
        >>>     print(f"Drift detected in {drift_report.drift_features_count} features!")
    """

    def __init__(
        self,
        significance_level: float = 0.05,
        psi_threshold: float = 0.1,
        drift_threshold: float = 0.2
    ):
        """
        Initialize drift detector

        Args:
            significance_level: Statistical significance level for tests
            psi_threshold: PSI threshold (0.1=low, 0.2=medium, 0.25=high drift)
            drift_threshold: General drift score threshold
        """
        self.significance_level = significance_level
        self.psi_threshold = psi_threshold
        self.drift_threshold = drift_threshold

    def detect(
        self,
        baseline_df: pd.DataFrame,
        current_df: pd.DataFrame,
        dataset_name: str = "dataset",
        baseline_timestamp: Optional[datetime] = None,
        columns: Optional[List[str]] = None
    ) -> DriftReport:
        """
        Detect drift between baseline and current datasets

        Args:
            baseline_df: Baseline/reference dataset
            current_df: Current/production dataset
            dataset_name: Dataset identifier
            baseline_timestamp: Timestamp of baseline data
            columns: Specific columns to analyze (None = all numerical)

        Returns:
            DriftReport with drift detection results
        """
        if baseline_timestamp is None:
            baseline_timestamp = datetime.utcnow()

        # Select numerical columns if not specified
        if columns is None:
            columns = baseline_df.select_dtypes(include=[np.number]).columns.tolist()
            columns = [c for c in columns if c in current_df.columns]

        # Detect drift for each feature
        feature_drifts = []
        for col in columns:
            drift = self._detect_feature_drift(
                baseline_df[col],
                current_df[col],
                col
            )
            feature_drifts.append(drift)

        # Analyze results
        drift_features = [fd for fd in feature_drifts if fd.drift_detected]
        drift_features_count = len(drift_features)
        total_features = len(feature_drifts)
        drift_percentage = (drift_features_count / total_features * 100) if total_features > 0 else 0

        # Categorize by severity
        severe_drift = [fd.feature_name for fd in drift_features if fd.drift_severity == DriftSeverity.SEVERE]
        high_drift = [fd.feature_name for fd in drift_features if fd.drift_severity == DriftSeverity.HIGH]
        medium_drift = [fd.feature_name for fd in drift_features if fd.drift_severity == DriftSeverity.MEDIUM]

        # Generate recommendations
        recommendations = self._generate_recommendations(drift_features, drift_percentage)
        retraining_recommended = drift_percentage > 20 or len(severe_drift) > 0

        return DriftReport(
            dataset_name=dataset_name,
            baseline_timestamp=baseline_timestamp,
            drift_detected=drift_features_count > 0,
            drift_features_count=drift_features_count,
            total_features_analyzed=total_features,
            drift_percentage=drift_percentage,
            feature_drifts=feature_drifts,
            severe_drift_features=severe_drift,
            high_drift_features=high_drift,
            medium_drift_features=medium_drift,
            recommendations=recommendations,
            retraining_recommended=retraining_recommended
        )

    def _detect_feature_drift(
        self,
        baseline_series: pd.Series,
        current_series: pd.Series,
        feature_name: str
    ) -> FeatureDrift:
        """Detect drift for a single feature"""
        # Clean data
        baseline_clean = baseline_series.dropna()
        current_clean = current_series.dropna()

        if len(baseline_clean) < 10 or len(current_clean) < 10:
            return FeatureDrift(
                feature_name=feature_name,
                method=DriftMethod.KS_TEST,
                statistic=0.0,
                drift_detected=False,
                drift_severity=DriftSeverity.NO_DRIFT,
                drift_score=0.0,
                recommendation="Insufficient data for drift detection"
            )

        # Perform KS test (Kolmogorov-Smirnov)
        ks_stat, p_value = stats.ks_2samp(baseline_clean, current_clean)

        # Calculate distribution metrics
        baseline_mean = float(baseline_clean.mean())
        current_mean = float(current_clean.mean())
        baseline_std = float(baseline_clean.std())
        current_std = float(current_clean.std())

        # Determine drift
        drift_detected = p_value < self.significance_level
        drift_score = ks_stat  # KS statistic as drift score (0-1)

        # Determine severity
        if drift_score > 0.5:
            severity = DriftSeverity.SEVERE
        elif drift_score > 0.3:
            severity = DriftSeverity.HIGH
        elif drift_score > 0.1:
            severity = DriftSeverity.MEDIUM
        elif drift_detected:
            severity = DriftSeverity.LOW
        else:
            severity = DriftSeverity.NO_DRIFT

        # Generate recommendation
        if severity == DriftSeverity.SEVERE:
            recommendation = "🚨 Severe drift detected! Immediate investigation and retraining required."
        elif severity == DriftSeverity.HIGH:
            recommendation = "⚠️ High drift detected. Review data pipeline and consider retraining."
        elif severity == DriftSeverity.MEDIUM:
            recommendation = "⚡ Moderate drift detected. Monitor closely and plan retraining."
        elif severity == DriftSeverity.LOW:
            recommendation = "ℹ️ Low drift detected. Continue monitoring."
        else:
            recommendation = "✅ No significant drift detected."

        return FeatureDrift(
            feature_name=feature_name,
            method=DriftMethod.KS_TEST,
            statistic=float(ks_stat),
            p_value=float(p_value),
            drift_detected=drift_detected,
            drift_severity=severity,
            drift_score=drift_score,
            baseline_mean=baseline_mean,
            current_mean=current_mean,
            baseline_std=baseline_std,
            current_std=current_std,
            recommendation=recommendation
        )

    def _generate_recommendations(
        self,
        drift_features: List[FeatureDrift],
        drift_percentage: float
    ) -> List[str]:
        """Generate drift-based recommendations"""
        recommendations = []

        if drift_percentage > 30:
            recommendations.append(
                "🚨 CRITICAL: Over 30% of features show drift. Immediate model retraining required!"
            )
        elif drift_percentage > 20:
            recommendations.append(
                "⚠️ HIGH: Significant drift detected (>20% features). Schedule model retraining soon."
            )
        elif drift_percentage > 10:
            recommendations.append(
                "⚡ MEDIUM: Moderate drift detected (>10% features). Monitor performance and plan retraining."
            )

        severe_features = [fd for fd in drift_features if fd.drift_severity == DriftSeverity.SEVERE]
        if severe_features:
            feat_names = ', '.join([fd.feature_name for fd in severe_features[:5]])
            recommendations.append(
                f"🔍 Investigate severe drift in: {feat_names}"
            )

        # Check for mean shift
        large_mean_shifts = [
            fd for fd in drift_features
            if fd.baseline_mean and fd.current_mean
            and abs(fd.current_mean - fd.baseline_mean) / (fd.baseline_std + 1e-10) > 2
        ]
        if large_mean_shifts:
            recommendations.append(
                f"📊 Large mean shifts detected in {len(large_mean_shifts)} features. Review data collection process."
            )

        return recommendations
