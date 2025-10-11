"""
Dataset Profiling Engine

Analyzes datasets to extract statistical summaries and data quality metrics.
"""

import pandas as pd
import numpy as np
from typing import List, Optional
import logging

from ..models.feature_schema import (
    FeatureStats, FeatureType, DatasetProfile
)


logger = logging.getLogger(__name__)


class DatasetProfiler:
    """
    Profile datasets to understand feature distributions and quality

    Example:
        >>> profiler = DatasetProfiler()
        >>> df = pd.read_csv("data.csv")
        >>> profile = profiler.profile(df, dataset_name="my_dataset")
    """

    def __init__(self, max_unique_for_categorical: int = 50):
        """
        Initialize profiler

        Args:
            max_unique_for_categorical: Max unique values to treat as categorical
        """
        self.max_unique_for_categorical = max_unique_for_categorical

    def profile(self, df: pd.DataFrame, dataset_name: str = "dataset") -> DatasetProfile:
        """
        Generate complete dataset profile

        Args:
            df: Input DataFrame
            dataset_name: Dataset identifier

        Returns:
            DatasetProfile with statistics for all features
        """
        logger.info(f"Profiling dataset '{dataset_name}' with {len(df)} rows, {len(df.columns)} columns")

        feature_stats = []
        numerical_features = []
        categorical_features = []
        total_nulls = 0

        for col in df.columns:
            stats = self._profile_feature(df, col)
            feature_stats.append(stats)

            if stats.type == FeatureType.NUMERICAL:
                numerical_features.append(col)
            elif stats.type == FeatureType.CATEGORICAL:
                categorical_features.append(col)

            total_nulls += stats.null_count

        # Calculate overall null percentage
        total_cells = len(df) * len(df.columns)
        null_percentage = (total_nulls / total_cells * 100) if total_cells > 0 else 0

        return DatasetProfile(
            dataset_name=dataset_name,
            num_rows=len(df),
            num_features=len(df.columns),
            features=feature_stats,
            numerical_features=numerical_features,
            categorical_features=categorical_features,
            total_nulls=total_nulls,
            null_percentage=null_percentage
        )

    def _profile_feature(self, df: pd.DataFrame, column: str) -> FeatureStats:
        """Profile a single feature"""
        series = df[column]

        # Basic stats
        count = series.count()
        null_count = series.isna().sum()
        null_percentage = (null_count / len(series) * 100) if len(series) > 0 else 0

        # Determine feature type
        feature_type = self._infer_type(series)

        # Initialize stats
        stats = FeatureStats(
            name=column,
            type=feature_type,
            count=count,
            null_count=null_count,
            null_percentage=null_percentage
        )

        # Compute type-specific statistics
        if feature_type == FeatureType.NUMERICAL:
            self._add_numerical_stats(stats, series)
        elif feature_type == FeatureType.CATEGORICAL:
            self._add_categorical_stats(stats, series)

        return stats

    def _infer_type(self, series: pd.Series) -> FeatureType:
        """Infer feature type from pandas Series"""
        # Drop nulls for type inference
        series_clean = series.dropna()

        if len(series_clean) == 0:
            return FeatureType.UNKNOWN

        # Check pandas dtype
        if pd.api.types.is_numeric_dtype(series):
            # Check if boolean (0/1 only)
            unique_vals = series_clean.unique()
            if len(unique_vals) == 2 and set(unique_vals).issubset({0, 1, True, False}):
                return FeatureType.BOOLEAN
            return FeatureType.NUMERICAL

        elif pd.api.types.is_datetime64_any_dtype(series):
            return FeatureType.DATETIME

        elif pd.api.types.is_object_dtype(series) or pd.api.types.is_categorical_dtype(series):
            # Categorical if unique count is low
            if series_clean.nunique() <= self.max_unique_for_categorical:
                return FeatureType.CATEGORICAL
            else:
                return FeatureType.TEXT

        return FeatureType.UNKNOWN

    def _add_numerical_stats(self, stats: FeatureStats, series: pd.Series):
        """Add numerical statistics"""
        series_clean = series.dropna()

        if len(series_clean) == 0:
            return

        stats.mean = float(series_clean.mean())
        stats.std = float(series_clean.std())
        stats.min = float(series_clean.min())
        stats.max = float(series_clean.max())
        stats.median = float(series_clean.median())

        # Quartiles
        stats.q25 = float(series_clean.quantile(0.25))
        stats.q75 = float(series_clean.quantile(0.75))

        # Unique count
        stats.unique_count = int(series_clean.nunique())

        # Skewness and kurtosis
        try:
            stats.skewness = float(series_clean.skew())
            stats.kurtosis = float(series_clean.kurtosis())
        except:
            pass

    def _add_categorical_stats(self, stats: FeatureStats, series: pd.Series):
        """Add categorical statistics"""
        series_clean = series.dropna()

        if len(series_clean) == 0:
            return

        stats.unique_count = int(series_clean.nunique())

        # Most frequent value
        value_counts = series_clean.value_counts()
        if len(value_counts) > 0:
            stats.top_value = str(value_counts.index[0])
            stats.top_frequency = int(value_counts.iloc[0])
