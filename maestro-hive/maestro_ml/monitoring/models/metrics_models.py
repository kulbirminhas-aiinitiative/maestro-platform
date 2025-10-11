"""
Performance Metrics Data Models

Time-series tracking of model performance metrics.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class MetricType(str, Enum):
    """Types of performance metrics"""
    # Classification
    ACCURACY = "accuracy"
    PRECISION = "precision"
    RECALL = "recall"
    F1_SCORE = "f1_score"
    AUC_ROC = "auc_roc"
    AUC_PR = "auc_pr"

    # Regression
    MAE = "mae"  # Mean Absolute Error
    MSE = "mse"  # Mean Squared Error
    RMSE = "rmse"  # Root Mean Squared Error
    R2_SCORE = "r2_score"
    MAPE = "mape"  # Mean Absolute Percentage Error

    # Business/Custom
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    CUSTOM = "custom"


class PerformanceMetric(BaseModel):
    """Single performance metric data point"""
    model_name: str
    model_version: str
    metric_type: MetricType
    metric_value: float

    # Context
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    dataset_name: Optional[str] = None
    dataset_size: Optional[int] = None

    # Additional metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)


class MetricSnapshot(BaseModel):
    """Snapshot of all metrics at a point in time"""
    model_name: str
    model_version: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # All metrics as key-value pairs
    metrics: Dict[str, float] = Field(default_factory=dict)

    # Context
    dataset_name: Optional[str] = None
    environment: str = Field(default="production", description="production, staging, test")

    # Computed fields
    overall_health: Optional[str] = None  # excellent, good, fair, poor


class MetricSummary(BaseModel):
    """Statistical summary of a metric over time"""
    metric_type: MetricType

    # Statistical measures
    current_value: float
    baseline_value: Optional[float] = None

    mean: float
    median: float
    std: float
    min: float
    max: float

    # Trend analysis
    trend: str = Field(..., description="improving, stable, degrading")
    change_percentage: Optional[float] = None

    # Time range
    start_time: datetime
    end_time: datetime
    data_points: int


class ModelPerformanceHistory(BaseModel):
    """Complete performance history for a model"""
    model_name: str
    model_version: str

    # Time range
    start_time: datetime
    end_time: datetime
    total_snapshots: int

    # Metric summaries
    metric_summaries: List[MetricSummary] = Field(default_factory=list)

    # All snapshots
    snapshots: List[MetricSnapshot] = Field(default_factory=list)

    # Health assessment
    overall_health: str = Field(..., description="excellent, good, fair, poor")
    health_trend: str = Field(..., description="improving, stable, degrading")

    # Alerts
    active_alerts: int = 0
    total_alerts: int = 0


class MetricThreshold(BaseModel):
    """Threshold configuration for a metric"""
    metric_type: MetricType

    # Thresholds (lower is better vs higher is better)
    min_acceptable: Optional[float] = None
    max_acceptable: Optional[float] = None

    # Degradation detection
    baseline_value: Optional[float] = None
    max_degradation_percentage: float = Field(default=10.0, description="Max % degradation allowed")

    # Direction (for determining if change is good or bad)
    higher_is_better: bool = Field(default=True, description="True for accuracy, False for error rates")


class MetricComparisonResult(BaseModel):
    """Result of comparing current vs baseline metrics"""
    metric_type: MetricType

    current_value: float
    baseline_value: float

    absolute_change: float
    percentage_change: float

    is_degraded: bool
    severity: str = Field(..., description="critical, high, medium, low, none")

    recommendation: str
