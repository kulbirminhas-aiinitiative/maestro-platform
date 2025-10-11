"""
Feature Discovery Data Models
"""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class FeatureType(str, Enum):
    """Feature data types"""
    NUMERICAL = "numerical"
    CATEGORICAL = "categorical"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    TEXT = "text"
    UNKNOWN = "unknown"


class CorrelationMethod(str, Enum):
    """Correlation calculation methods"""
    PEARSON = "pearson"
    SPEARMAN = "spearman"
    KENDALL = "kendall"


class ImportanceMethod(str, Enum):
    """Feature importance calculation methods"""
    RANDOM_FOREST = "random_forest"
    GRADIENT_BOOSTING = "gradient_boosting"
    PERMUTATION = "permutation"
    SHAP = "shap"
    MUTUAL_INFO = "mutual_info"


class FeatureStats(BaseModel):
    """Statistical summary of a feature"""
    name: str = Field(..., description="Feature name")
    type: FeatureType = Field(..., description="Feature type")

    # Basic stats
    count: int = Field(..., description="Number of non-null values")
    null_count: int = Field(0, description="Number of null values")
    null_percentage: float = Field(0.0, description="Percentage of null values")

    # Numerical stats (if applicable)
    mean: Optional[float] = Field(None, description="Mean value")
    std: Optional[float] = Field(None, description="Standard deviation")
    min: Optional[float] = Field(None, description="Minimum value")
    max: Optional[float] = Field(None, description="Maximum value")
    median: Optional[float] = Field(None, description="Median value")
    q25: Optional[float] = Field(None, description="25th percentile")
    q75: Optional[float] = Field(None, description="75th percentile")

    # Categorical stats (if applicable)
    unique_count: Optional[int] = Field(None, description="Number of unique values")
    top_value: Optional[str] = Field(None, description="Most frequent value")
    top_frequency: Optional[int] = Field(None, description="Frequency of most common value")

    # Additional metadata
    skewness: Optional[float] = Field(None, description="Skewness")
    kurtosis: Optional[float] = Field(None, description="Kurtosis")


class CorrelationPair(BaseModel):
    """Correlation between two features"""
    feature1: str = Field(..., description="First feature name")
    feature2: str = Field(..., description="Second feature name")
    correlation: float = Field(..., description="Correlation coefficient (-1 to 1)")
    p_value: Optional[float] = Field(None, description="Statistical significance")
    method: CorrelationMethod = Field(..., description="Correlation method used")

    @property
    def strength(self) -> str:
        """Correlation strength classification"""
        abs_corr = abs(self.correlation)
        if abs_corr >= 0.8:
            return "very_strong"
        elif abs_corr >= 0.6:
            return "strong"
        elif abs_corr >= 0.4:
            return "moderate"
        elif abs_corr >= 0.2:
            return "weak"
        else:
            return "very_weak"


class FeatureImportance(BaseModel):
    """Feature importance score"""
    feature: str = Field(..., description="Feature name")
    importance: float = Field(..., description="Importance score (0-1)")
    rank: int = Field(..., description="Rank by importance (1 = most important)")
    method: ImportanceMethod = Field(..., description="Calculation method")

    # Additional context
    std: Optional[float] = Field(None, description="Standard deviation of importance")
    confidence_interval: Optional[List[float]] = Field(None, description="95% CI [lower, upper]")


class FeatureRecommendation(BaseModel):
    """Feature recommendation"""
    feature: str = Field(..., description="Recommended feature")
    score: float = Field(..., description="Recommendation score (0-1)")
    reason: str = Field(..., description="Why this feature is recommended")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Supporting evidence")


class DatasetProfile(BaseModel):
    """Complete dataset profile"""
    dataset_name: str = Field(..., description="Dataset identifier")
    num_rows: int = Field(..., description="Number of rows")
    num_features: int = Field(..., description="Number of features")

    # Feature statistics
    features: List[FeatureStats] = Field(default_factory=list, description="Per-feature statistics")

    # Numerical/categorical breakdown
    numerical_features: List[str] = Field(default_factory=list)
    categorical_features: List[str] = Field(default_factory=list)

    # Data quality
    total_nulls: int = Field(0, description="Total null values across all features")
    null_percentage: float = Field(0.0, description="Overall null percentage")

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CorrelationMatrix(BaseModel):
    """Correlation analysis results"""
    dataset_name: str = Field(..., description="Dataset identifier")
    target: Optional[str] = Field(None, description="Target variable (if applicable)")
    method: CorrelationMethod = Field(..., description="Correlation method used")

    # Correlation pairs
    correlations: List[CorrelationPair] = Field(default_factory=list)

    # Matrix representation (feature names -> correlation)
    matrix: Dict[str, Dict[str, float]] = Field(default_factory=dict)

    # High correlations
    high_correlations: List[CorrelationPair] = Field(
        default_factory=list,
        description="Correlations above threshold"
    )

    created_at: datetime = Field(default_factory=datetime.utcnow)


class ImportanceAnalysis(BaseModel):
    """Feature importance analysis results"""
    dataset_name: str = Field(..., description="Dataset identifier")
    target: str = Field(..., description="Target variable")
    method: ImportanceMethod = Field(..., description="Calculation method")

    # Importance scores
    importances: List[FeatureImportance] = Field(default_factory=list)

    # Top features
    top_features: List[str] = Field(default_factory=list, description="Top N most important features")

    # Model metadata (if applicable)
    model_score: Optional[float] = Field(None, description="Model performance score")

    created_at: datetime = Field(default_factory=datetime.utcnow)


class FeatureDiscoveryReport(BaseModel):
    """Complete feature discovery report"""
    dataset_name: str = Field(..., description="Dataset identifier")

    # Analyses
    profile: Optional[DatasetProfile] = None
    correlations: Optional[CorrelationMatrix] = None
    importance: Optional[ImportanceAnalysis] = None

    # Recommendations
    recommendations: List[FeatureRecommendation] = Field(default_factory=list)

    # Summary insights
    insights: List[str] = Field(default_factory=list, description="Key insights and findings")

    created_at: datetime = Field(default_factory=datetime.utcnow)
