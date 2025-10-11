"""
Data Quality Metrics Calculator

Comprehensive data quality metrics including completeness, validity, accuracy, consistency.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class QualityDimension(str, Enum):
    """Data quality dimensions"""
    COMPLETENESS = "completeness"
    VALIDITY = "validity"
    ACCURACY = "accuracy"
    CONSISTENCY = "consistency"
    UNIQUENESS = "uniqueness"
    TIMELINESS = "timeliness"


class QualityIssue(BaseModel):
    """Data quality issue"""
    dimension: QualityDimension
    severity: str = Field(..., description="critical, high, medium, low")
    column: Optional[str] = None
    issue: str
    affected_rows: int = 0
    recommendation: str


class QualityMetrics(BaseModel):
    """Comprehensive quality metrics for a column"""
    column_name: str

    # Completeness
    completeness_score: float = Field(..., ge=0, le=100)
    null_count: int
    null_percentage: float

    # Validity
    validity_score: float = Field(..., ge=0, le=100)
    invalid_count: int = 0
    invalid_percentage: float = 0.0

    # Uniqueness
    uniqueness_score: float = Field(..., ge=0, le=100)
    unique_count: int
    duplicate_count: int = 0

    # Statistical metrics
    min_value: Optional[Any] = None
    max_value: Optional[Any] = None
    mean_value: Optional[float] = None
    std_value: Optional[float] = None

    # Quality issues
    issues: List[QualityIssue] = Field(default_factory=list)


class DatasetQualityReport(BaseModel):
    """Overall dataset quality report"""
    dataset_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Overall scores (0-100)
    overall_score: float = Field(..., ge=0, le=100)
    completeness_score: float = Field(..., ge=0, le=100)
    validity_score: float = Field(..., ge=0, le=100)
    consistency_score: float = Field(..., ge=0, le=100)
    uniqueness_score: float = Field(..., ge=0, le=100)

    # Dataset metrics
    total_rows: int
    total_columns: int
    total_cells: int
    missing_cells: int
    missing_percentage: float

    # Per-column metrics
    column_metrics: List[QualityMetrics] = Field(default_factory=list)

    # Issues
    critical_issues: List[QualityIssue] = Field(default_factory=list)
    warnings: List[QualityIssue] = Field(default_factory=list)

    # Recommendations
    recommendations: List[str] = Field(default_factory=list)


class QualityMetricsCalculator:
    """
    Calculate comprehensive data quality metrics

    Example:
        >>> calculator = QualityMetricsCalculator()
        >>> report = calculator.calculate(df, dataset_name="my_data")
        >>> print(f"Overall quality: {report.overall_score:.1f}%")
    """

    def __init__(
        self,
        completeness_threshold: float = 95.0,
        validity_threshold: float = 98.0,
        uniqueness_threshold: float = 90.0
    ):
        """
        Initialize calculator

        Args:
            completeness_threshold: Minimum acceptable completeness %
            validity_threshold: Minimum acceptable validity %
            uniqueness_threshold: Minimum acceptable uniqueness %
        """
        self.completeness_threshold = completeness_threshold
        self.validity_threshold = validity_threshold
        self.uniqueness_threshold = uniqueness_threshold

    def calculate(
        self,
        df: pd.DataFrame,
        dataset_name: str = "dataset",
        expected_types: Optional[Dict[str, str]] = None
    ) -> DatasetQualityReport:
        """
        Calculate comprehensive quality metrics

        Args:
            df: Input DataFrame
            dataset_name: Dataset identifier
            expected_types: Expected data types per column

        Returns:
            DatasetQualityReport with quality metrics and issues
        """
        total_rows = len(df)
        total_columns = len(df.columns)
        total_cells = total_rows * total_columns
        missing_cells = df.isna().sum().sum()
        missing_percentage = (missing_cells / total_cells * 100) if total_cells > 0 else 0

        # Calculate per-column metrics
        column_metrics = []
        for col in df.columns:
            metrics = self._calculate_column_metrics(
                df[col],
                col,
                expected_types.get(col) if expected_types else None
            )
            column_metrics.append(metrics)

        # Calculate overall scores
        completeness_score = self._calculate_completeness_score(df)
        validity_score = self._calculate_validity_score(column_metrics)
        consistency_score = self._calculate_consistency_score(df)
        uniqueness_score = self._calculate_uniqueness_score(column_metrics)

        overall_score = np.mean([
            completeness_score,
            validity_score,
            consistency_score,
            uniqueness_score
        ])

        # Collect issues
        critical_issues = []
        warnings = []

        for metrics in column_metrics:
            for issue in metrics.issues:
                if issue.severity in ["critical", "high"]:
                    critical_issues.append(issue)
                else:
                    warnings.append(issue)

        # Generate recommendations
        recommendations = self._generate_recommendations(
            completeness_score,
            validity_score,
            consistency_score,
            uniqueness_score,
            column_metrics
        )

        return DatasetQualityReport(
            dataset_name=dataset_name,
            overall_score=overall_score,
            completeness_score=completeness_score,
            validity_score=validity_score,
            consistency_score=consistency_score,
            uniqueness_score=uniqueness_score,
            total_rows=total_rows,
            total_columns=total_columns,
            total_cells=total_cells,
            missing_cells=missing_cells,
            missing_percentage=missing_percentage,
            column_metrics=column_metrics,
            critical_issues=critical_issues,
            warnings=warnings,
            recommendations=recommendations
        )

    def _calculate_column_metrics(
        self,
        series: pd.Series,
        column_name: str,
        expected_type: Optional[str] = None
    ) -> QualityMetrics:
        """Calculate metrics for a single column"""
        total_count = len(series)
        null_count = series.isna().sum()
        valid_count = total_count - null_count

        # Completeness
        completeness_score = (valid_count / total_count * 100) if total_count > 0 else 0
        null_percentage = 100 - completeness_score

        # Uniqueness
        unique_count = series.nunique()
        duplicate_count = valid_count - unique_count
        uniqueness_score = (unique_count / valid_count * 100) if valid_count > 0 else 0

        # Validity (check data type consistency)
        invalid_count = 0
        validity_score = 100.0

        if expected_type and valid_count > 0:
            # Check if values match expected type
            try:
                if expected_type == "numeric":
                    invalid_count = series.dropna().apply(
                        lambda x: not isinstance(x, (int, float, np.number))
                    ).sum()
                elif expected_type == "string":
                    invalid_count = series.dropna().apply(
                        lambda x: not isinstance(x, str)
                    ).sum()

                validity_score = ((valid_count - invalid_count) / valid_count * 100)
            except:
                pass

        # Statistical metrics (for numerical columns)
        min_val = None
        max_val = None
        mean_val = None
        std_val = None

        if pd.api.types.is_numeric_dtype(series):
            try:
                min_val = float(series.min())
                max_val = float(series.max())
                mean_val = float(series.mean())
                std_val = float(series.std())
            except:
                pass

        # Identify issues
        issues = []

        if completeness_score < self.completeness_threshold:
            issues.append(QualityIssue(
                dimension=QualityDimension.COMPLETENESS,
                severity="high" if completeness_score < 80 else "medium",
                column=column_name,
                issue=f"High missing data rate: {null_percentage:.1f}%",
                affected_rows=null_count,
                recommendation=f"Investigate missing data pattern. Consider imputation or removal."
            ))

        if validity_score < self.validity_threshold and invalid_count > 0:
            issues.append(QualityIssue(
                dimension=QualityDimension.VALIDITY,
                severity="high",
                column=column_name,
                issue=f"Invalid values found: {invalid_count}",
                affected_rows=invalid_count,
                recommendation=f"Clean or transform invalid values to match expected type '{expected_type}'"
            ))

        if uniqueness_score < self.uniqueness_threshold and duplicate_count > 0:
            issues.append(QualityIssue(
                dimension=QualityDimension.UNIQUENESS,
                severity="medium",
                column=column_name,
                issue=f"High duplicate rate: {duplicate_count} duplicates",
                affected_rows=duplicate_count,
                recommendation="Consider if duplicates are expected or need deduplication"
            ))

        return QualityMetrics(
            column_name=column_name,
            completeness_score=completeness_score,
            null_count=null_count,
            null_percentage=null_percentage,
            validity_score=validity_score,
            invalid_count=invalid_count,
            invalid_percentage=(invalid_count / valid_count * 100) if valid_count > 0 else 0,
            uniqueness_score=uniqueness_score,
            unique_count=unique_count,
            duplicate_count=duplicate_count,
            min_value=min_val,
            max_value=max_val,
            mean_value=mean_val,
            std_value=std_val,
            issues=issues
        )

    def _calculate_completeness_score(self, df: pd.DataFrame) -> float:
        """Calculate overall completeness score"""
        total_cells = df.shape[0] * df.shape[1]
        valid_cells = total_cells - df.isna().sum().sum()
        return (valid_cells / total_cells * 100) if total_cells > 0 else 0

    def _calculate_validity_score(self, column_metrics: List[QualityMetrics]) -> float:
        """Calculate overall validity score"""
        if not column_metrics:
            return 100.0
        return np.mean([m.validity_score for m in column_metrics])

    def _calculate_consistency_score(self, df: pd.DataFrame) -> float:
        """Calculate consistency score (simplified)"""
        # Check for consistent data types within columns
        consistency_scores = []

        for col in df.columns:
            series = df[col].dropna()
            if len(series) == 0:
                continue

            # Check type consistency
            first_type = type(series.iloc[0])
            type_consistency = series.apply(lambda x: isinstance(x, first_type)).mean()
            consistency_scores.append(type_consistency * 100)

        return np.mean(consistency_scores) if consistency_scores else 100.0

    def _calculate_uniqueness_score(self, column_metrics: List[QualityMetrics]) -> float:
        """Calculate overall uniqueness score"""
        if not column_metrics:
            return 100.0
        return np.mean([m.uniqueness_score for m in column_metrics])

    def _generate_recommendations(
        self,
        completeness: float,
        validity: float,
        consistency: float,
        uniqueness: float,
        column_metrics: List[QualityMetrics]
    ) -> List[str]:
        """Generate quality improvement recommendations"""
        recommendations = []

        if completeness < 90:
            recommendations.append(
                "⚠️ Overall completeness is low. Review missing data patterns and consider imputation strategies."
            )

        if validity < 95:
            recommendations.append(
                "⚠️ Data validity issues detected. Implement validation rules during data ingestion."
            )

        if consistency < 90:
            recommendations.append(
                "⚠️ Data consistency issues found. Standardize data types and formats across columns."
            )

        # Column-specific recommendations
        high_missing_cols = [m for m in column_metrics if m.null_percentage > 30]
        if high_missing_cols:
            recommendations.append(
                f"🗑️ Consider removing columns with >30% missing data: {', '.join([m.column_name for m in high_missing_cols[:5]])}"
            )

        duplicate_cols = [m for m in column_metrics if m.duplicate_count > len(column_metrics) * 0.5]
        if duplicate_cols:
            recommendations.append(
                f"🔍 High duplicate rates in: {', '.join([m.column_name for m in duplicate_cols[:5]])}. Review for deduplication."
            )

        return recommendations
