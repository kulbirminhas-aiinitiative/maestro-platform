"""
Feature Importance Calculation Engine

Calculates feature importance using various ML methods.
"""

import pandas as pd
import numpy as np
from typing import List, Optional
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.inspection import permutation_importance
from sklearn.feature_selection import mutual_info_classif, mutual_info_regression
import logging

from ..models.feature_schema import (
    ImportanceAnalysis, FeatureImportance, ImportanceMethod
)


logger = logging.getLogger(__name__)


class ImportanceCalculator:
    """
    Calculate feature importance using ML algorithms

    Example:
        >>> calculator = ImportanceCalculator()
        >>> X, y = df.drop('target', axis=1), df['target']
        >>> importance = calculator.calculate(X, y, method="random_forest")
    """

    def __init__(self, random_state: int = 42):
        """
        Initialize calculator

        Args:
            random_state: Random seed for reproducibility
        """
        self.random_state = random_state

    def calculate(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        dataset_name: str = "dataset",
        method: ImportanceMethod = ImportanceMethod.RANDOM_FOREST,
        is_classification: bool = True,
        top_n: int = 20
    ) -> ImportanceAnalysis:
        """
        Calculate feature importance

        Args:
            X: Feature matrix
            y: Target variable
            dataset_name: Dataset identifier
            method: Importance calculation method
            is_classification: Whether task is classification (vs regression)
            top_n: Number of top features to track

        Returns:
            ImportanceAnalysis with feature importance scores
        """
        logger.info(f"Calculating feature importance using {method}")

        # Remove any non-numeric columns
        X_numeric = X.select_dtypes(include=[np.number])

        if len(X_numeric.columns) == 0:
            logger.warning("No numerical features found for importance calculation")
            return ImportanceAnalysis(
                dataset_name=dataset_name,
                target=y.name if hasattr(y, 'name') else "target",
                method=method
            )

        # Calculate importance based on method
        if method == ImportanceMethod.RANDOM_FOREST:
            importances_data = self._random_forest_importance(X_numeric, y, is_classification)
        elif method == ImportanceMethod.GRADIENT_BOOSTING:
            importances_data = self._gradient_boosting_importance(X_numeric, y, is_classification)
        elif method == ImportanceMethod.PERMUTATION:
            importances_data = self._permutation_importance(X_numeric, y, is_classification)
        elif method == ImportanceMethod.MUTUAL_INFO:
            importances_data = self._mutual_info_importance(X_numeric, y, is_classification)
        else:
            raise ValueError(f"Unsupported importance method: {method}")

        # Create FeatureImportance objects
        importances = []
        for i, (feature, importance_value, std) in enumerate(importances_data, 1):
            importances.append(FeatureImportance(
                feature=feature,
                importance=float(importance_value),
                rank=i,
                method=method,
                std=float(std) if std is not None else None
            ))

        # Get top features
        top_features = [imp.feature for imp in importances[:top_n]]

        return ImportanceAnalysis(
            dataset_name=dataset_name,
            target=y.name if hasattr(y, 'name') else "target",
            method=method,
            importances=importances,
            top_features=top_features
        )

    def _random_forest_importance(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        is_classification: bool
    ) -> List[tuple]:
        """Calculate importance using Random Forest"""
        if is_classification:
            model = RandomForestClassifier(
                n_estimators=100,
                random_state=self.random_state,
                n_jobs=-1
            )
        else:
            model = RandomForestRegressor(
                n_estimators=100,
                random_state=self.random_state,
                n_jobs=-1
            )

        model.fit(X, y)

        # Get feature importances
        importances = model.feature_importances_

        # Calculate std from trees
        tree_importances = np.array([tree.feature_importances_ for tree in model.estimators_])
        std = np.std(tree_importances, axis=0)

        # Create list of (feature, importance, std)
        importance_data = list(zip(X.columns, importances, std))

        # Sort by importance
        importance_data.sort(key=lambda x: x[1], reverse=True)

        return importance_data

    def _gradient_boosting_importance(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        is_classification: bool
    ) -> List[tuple]:
        """Calculate importance using Gradient Boosting"""
        if is_classification:
            model = GradientBoostingClassifier(
                n_estimators=100,
                random_state=self.random_state,
                max_depth=3
            )
        else:
            model = GradientBoostingRegressor(
                n_estimators=100,
                random_state=self.random_state,
                max_depth=3
            )

        model.fit(X, y)

        importances = model.feature_importances_

        # Create list (no std available for GBM)
        importance_data = list(zip(X.columns, importances, [None] * len(importances)))
        importance_data.sort(key=lambda x: x[1], reverse=True)

        return importance_data

    def _permutation_importance(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        is_classification: bool
    ) -> List[tuple]:
        """Calculate permutation importance"""
        # Train a simple model first
        if is_classification:
            model = RandomForestClassifier(
                n_estimators=50,
                random_state=self.random_state,
                n_jobs=-1
            )
        else:
            model = RandomForestRegressor(
                n_estimators=50,
                random_state=self.random_state,
                n_jobs=-1
            )

        model.fit(X, y)

        # Calculate permutation importance
        result = permutation_importance(
            model, X, y,
            n_repeats=10,
            random_state=self.random_state,
            n_jobs=-1
        )

        importance_data = list(zip(
            X.columns,
            result.importances_mean,
            result.importances_std
        ))
        importance_data.sort(key=lambda x: x[1], reverse=True)

        return importance_data

    def _mutual_info_importance(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        is_classification: bool
    ) -> List[tuple]:
        """Calculate mutual information importance"""
        if is_classification:
            mi_scores = mutual_info_classif(
                X, y,
                random_state=self.random_state
            )
        else:
            mi_scores = mutual_info_regression(
                X, y,
                random_state=self.random_state
            )

        # Normalize scores to 0-1 range
        if mi_scores.max() > 0:
            mi_scores = mi_scores / mi_scores.max()

        importance_data = list(zip(X.columns, mi_scores, [None] * len(mi_scores)))
        importance_data.sort(key=lambda x: x[1], reverse=True)

        return importance_data
