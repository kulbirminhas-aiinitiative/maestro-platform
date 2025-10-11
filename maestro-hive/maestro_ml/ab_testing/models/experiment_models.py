"""
A/B Testing Experiment Models
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ExperimentStatus(str, Enum):
    """Experiment lifecycle status"""

    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class MetricType(str, Enum):
    """Type of metric being tracked"""

    CONVERSION_RATE = "conversion_rate"
    ACCURACY = "accuracy"
    LATENCY = "latency"
    ERROR_RATE = "error_rate"
    REVENUE = "revenue"
    ENGAGEMENT = "engagement"
    CUSTOM = "custom"


class StatisticalTest(str, Enum):
    """Statistical test type"""

    T_TEST = "t_test"
    CHI_SQUARE = "chi_square"
    MANN_WHITNEY = "mann_whitney"
    BAYESIAN = "bayesian"


class ExperimentVariant(BaseModel):
    """A variant in an A/B test"""

    variant_id: str = Field(..., description="Unique variant identifier")
    name: str = Field(..., description="Variant name")
    description: Optional[str] = Field(None, description="Variant description")

    # Model configuration
    model_name: Optional[str] = Field(None, description="Model name")
    model_version: Optional[str] = Field(None, description="Model version")
    model_uri: Optional[str] = Field(None, description="Model URI")

    # Traffic allocation
    traffic_percentage: float = Field(
        ..., ge=0, le=100, description="Traffic percentage"
    )

    # Configuration overrides
    config_overrides: dict[str, Any] = Field(
        default_factory=dict, description="Config overrides"
    )

    # Tracking
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_control: bool = Field(False, description="Is this the control variant?")


class TrafficSplit(BaseModel):
    """Traffic split configuration"""

    variant_weights: dict[str, float] = Field(
        ..., description="Variant ID -> Weight mapping"
    )
    sticky_sessions: bool = Field(True, description="Use sticky sessions?")
    session_duration_seconds: int = Field(3600, description="Session duration")

    def validate_weights(self) -> bool:
        """Validate that weights sum to 100"""
        total = sum(self.variant_weights.values())
        return abs(total - 100.0) < 0.01


class ExperimentMetric(BaseModel):
    """A metric being tracked in the experiment"""

    metric_name: str = Field(..., description="Metric name")
    metric_type: MetricType = Field(..., description="Metric type")

    # Primary metric?
    is_primary: bool = Field(False, description="Is this the primary metric?")

    # Direction (higher or lower is better)
    higher_is_better: bool = Field(True, description="Higher values are better?")

    # Statistical test configuration
    statistical_test: StatisticalTest = Field(
        StatisticalTest.T_TEST, description="Statistical test"
    )
    significance_level: float = Field(0.05, ge=0, le=1, description="Alpha level")
    minimum_detectable_effect: float = Field(
        0.05, description="Minimum effect size to detect"
    )

    # Sample size requirements
    min_sample_size_per_variant: int = Field(
        100, description="Minimum samples per variant"
    )


class Experiment(BaseModel):
    """A/B test experiment"""

    experiment_id: str = Field(..., description="Unique experiment ID")
    name: str = Field(..., description="Experiment name")
    description: Optional[str] = Field(None, description="Experiment description")

    # Status
    status: ExperimentStatus = Field(
        ExperimentStatus.DRAFT, description="Experiment status"
    )

    # Variants
    variants: list[ExperimentVariant] = Field(
        ..., min_length=2, description="Experiment variants"
    )

    # Traffic configuration
    traffic_split: TrafficSplit = Field(..., description="Traffic split configuration")

    # Metrics
    metrics: list[ExperimentMetric] = Field(
        ..., min_length=1, description="Tracked metrics"
    )

    # Experiment timeline
    start_time: Optional[datetime] = Field(None, description="Experiment start time")
    end_time: Optional[datetime] = Field(None, description="Experiment end time")
    duration_days: Optional[int] = Field(None, description="Planned duration in days")

    # Early stopping
    enable_early_stopping: bool = Field(True, description="Enable early stopping?")
    early_stopping_threshold: float = Field(
        0.99, description="Early stopping confidence"
    )

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(..., description="Creator user ID")
    tags: list[str] = Field(default_factory=list, description="Experiment tags")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class VariantMetrics(BaseModel):
    """Metrics for a single variant"""

    variant_id: str
    sample_size: int
    metrics: dict[str, float]  # metric_name -> value
    metric_std: dict[str, float]  # metric_name -> standard deviation
    confidence_intervals: dict[
        str, tuple[float, float]
    ]  # metric_name -> (lower, upper)


class ComparisonResult(BaseModel):
    """Comparison between two variants"""

    control_variant_id: str
    treatment_variant_id: str
    metric_name: str

    # Statistical test results
    test_statistic: float
    p_value: float
    is_significant: bool

    # Effect size
    absolute_difference: float
    relative_difference_percent: float

    # Confidence interval for difference
    confidence_interval: tuple[float, float]
    confidence_level: float = 0.95

    # Power analysis
    statistical_power: Optional[float] = None

    # Recommendation
    recommendation: str  # "deploy", "continue", "stop"


class ExperimentResult(BaseModel):
    """Complete experiment results"""

    experiment_id: str
    experiment_name: str
    status: ExperimentStatus

    # Variant metrics
    variant_metrics: list[VariantMetrics]

    # Comparisons (control vs each treatment)
    comparisons: list[ComparisonResult]

    # Winner
    winning_variant_id: Optional[str] = None
    confidence_in_winner: Optional[float] = None

    # Summary statistics
    total_sample_size: int
    experiment_duration_hours: float
    data_quality_score: float  # 0-1, based on sample size, variance, etc.

    # Recommendations
    recommendation: str
    reason: str

    # Timestamps
    analysis_timestamp: datetime = Field(default_factory=datetime.utcnow)


class BayesianResult(BaseModel):
    """Bayesian A/B test result"""

    variant_id: str
    probability_of_being_best: float
    expected_loss: float
    credible_interval_95: tuple[float, float]
