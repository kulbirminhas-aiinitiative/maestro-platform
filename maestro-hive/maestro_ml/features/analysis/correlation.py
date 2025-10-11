"""
Correlation Analysis Engine

Calculates feature correlations using various methods.
"""

import pandas as pd
import numpy as np
from typing import List, Optional, Dict
from scipy import stats
import logging

from ..models.feature_schema import (
    CorrelationMatrix, CorrelationPair, CorrelationMethod
)


logger = logging.getLogger(__name__)


class CorrelationAnalyzer:
    """
    Analyze feature correlations

    Example:
        >>> analyzer = CorrelationAnalyzer()
        >>> df = pd.read_csv("data.csv")
        >>> corr_matrix = analyzer.analyze(df, method="pearson")
    """

    def __init__(self, correlation_threshold: float = 0.5):
        """
        Initialize analyzer

        Args:
            correlation_threshold: Threshold for "high" correlations
        """
        self.correlation_threshold = correlation_threshold

    def analyze(
        self,
        df: pd.DataFrame,
        dataset_name: str = "dataset",
        target: Optional[str] = None,
        method: CorrelationMethod = CorrelationMethod.PEARSON,
        include_p_values: bool = True
    ) -> CorrelationMatrix:
        """
        Analyze correlations between features

        Args:
            df: Input DataFrame
            dataset_name: Dataset identifier
            target: Optional target variable name
            method: Correlation method (pearson, spearman, kendall)
            include_p_values: Calculate statistical significance

        Returns:
            CorrelationMatrix with pairwise correlations
        """
        logger.info(f"Analyzing correlations for '{dataset_name}' using {method}")

        # Select only numerical columns
        numerical_cols = df.select_dtypes(include=[np.number]).columns.tolist()

        if len(numerical_cols) == 0:
            logger.warning("No numerical columns found for correlation analysis")
            return CorrelationMatrix(
                dataset_name=dataset_name,
                target=target,
                method=method
            )

        # Calculate correlation matrix
        if method == CorrelationMethod.PEARSON:
            corr_df = df[numerical_cols].corr(method='pearson')
        elif method == CorrelationMethod.SPEARMAN:
            corr_df = df[numerical_cols].corr(method='spearman')
        elif method == CorrelationMethod.KENDALL:
            corr_df = df[numerical_cols].corr(method='kendall')
        else:
            raise ValueError(f"Unsupported correlation method: {method}")

        # Convert to dictionary format
        matrix_dict = corr_df.to_dict()

        # Extract correlation pairs
        correlations = []
        high_correlations = []

        for i, feat1 in enumerate(numerical_cols):
            for feat2 in numerical_cols[i+1:]:  # Upper triangle only
                corr_value = corr_df.loc[feat1, feat2]

                # Calculate p-value if requested
                p_value = None
                if include_p_values:
                    p_value = self._calculate_p_value(
                        df[feat1], df[feat2], method
                    )

                pair = CorrelationPair(
                    feature1=feat1,
                    feature2=feat2,
                    correlation=float(corr_value),
                    p_value=p_value,
                    method=method
                )

                correlations.append(pair)

                # Track high correlations
                if abs(corr_value) >= self.correlation_threshold:
                    high_correlations.append(pair)

        # Sort high correlations by absolute value
        high_correlations.sort(key=lambda x: abs(x.correlation), reverse=True)

        return CorrelationMatrix(
            dataset_name=dataset_name,
            target=target,
            method=method,
            correlations=correlations,
            matrix=matrix_dict,
            high_correlations=high_correlations
        )

    def _calculate_p_value(
        self,
        series1: pd.Series,
        series2: pd.Series,
        method: CorrelationMethod
    ) -> Optional[float]:
        """Calculate p-value for correlation"""
        try:
            # Remove NaN values
            mask = series1.notna() & series2.notna()
            s1 = series1[mask]
            s2 = series2[mask]

            if len(s1) < 3:
                return None

            if method == CorrelationMethod.PEARSON:
                _, p_value = stats.pearsonr(s1, s2)
            elif method == CorrelationMethod.SPEARMAN:
                _, p_value = stats.spearmanr(s1, s2)
            elif method == CorrelationMethod.KENDALL:
                _, p_value = stats.kendalltau(s1, s2)
            else:
                return None

            return float(p_value)
        except Exception as e:
            logger.warning(f"Failed to calculate p-value: {e}")
            return None

    def get_target_correlations(
        self,
        correlation_matrix: CorrelationMatrix,
        target: str,
        top_n: int = 10
    ) -> List[CorrelationPair]:
        """
        Get top correlations with target variable

        Args:
            correlation_matrix: Correlation matrix
            target: Target variable name
            top_n: Number of top correlations to return

        Returns:
            List of top correlated features with target
        """
        target_corrs = [
            pair for pair in correlation_matrix.correlations
            if target in [pair.feature1, pair.feature2]
        ]

        # Sort by absolute correlation
        target_corrs.sort(key=lambda x: abs(x.correlation), reverse=True)

        return target_corrs[:top_n]
