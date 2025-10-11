"""
Feature Importance Analyzer

Calculate feature importance using various methods.
"""

import logging
from collections.abc import Callable
from typing import Any, Optional, Union

import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance
from sklearn.metrics import accuracy_score, mean_squared_error

from ..models.explanation_models import (
    ExplanationType,
    FeatureImportance,
    GlobalExplanation,
    ModelType,
)

logger = logging.getLogger(__name__)


class FeatureImportanceAnalyzer:
    """
    Feature importance analysis using multiple methods

    Methods:
    1. Model-intrinsic (tree-based models)
    2. Permutation importance (model-agnostic)
    3. Drop-column importance
    4. SHAP-based importance
    """

    def __init__(
        self,
        model: Any,
        model_type: ModelType = ModelType.BLACK_BOX,
        feature_names: Optional[list[str]] = None,
    ):
        """
        Initialize feature importance analyzer

        Args:
            model: Trained model
            model_type: Type of model
            feature_names: List of feature names
        """
        self.model = model
        self.model_type = model_type
        self.feature_names = feature_names
        self.logger = logger

    def get_intrinsic_importance(self) -> Optional[GlobalExplanation]:
        """
        Get model-intrinsic feature importance

        Only works for models with built-in feature_importances_ attribute
        (tree-based models: RandomForest, XGBoost, LightGBM, etc.)

        Returns:
            Global explanation with feature importances, or None if not available
        """
        if not hasattr(self.model, "feature_importances_"):
            self.logger.warning("Model does not have feature_importances_ attribute")
            return None

        importances = self.model.feature_importances_

        # Create feature importance list
        feature_importances = []
        sorted_indices = np.argsort(importances)[::-1]

        for rank, idx in enumerate(sorted_indices, 1):
            if self.feature_names:
                feature_name = self.feature_names[idx]
            else:
                feature_name = f"feature_{idx}"

            feature_importances.append(
                FeatureImportance(
                    feature_name=feature_name,
                    importance=float(importances[idx]),
                    rank=rank,
                )
            )

        return GlobalExplanation(
            feature_importances=feature_importances,
            num_instances=0,  # Not applicable for intrinsic
            prediction_mean=0.0,
            prediction_std=0.0,
            explanation_type=ExplanationType.FEATURE_IMPORTANCE,
            model_type=self.model_type,
        )

    def get_permutation_importance(
        self,
        X: Union[np.ndarray, pd.DataFrame],
        y: Union[np.ndarray, pd.Series],
        n_repeats: int = 10,
        random_state: int = 42,
        scoring: Optional[str] = None,
    ) -> GlobalExplanation:
        """
        Calculate permutation importance

        Permutation importance measures how much model performance decreases
        when a feature is randomly shuffled.

        Args:
            X: Feature matrix
            y: Target values
            n_repeats: Number of times to permute each feature
            random_state: Random seed
            scoring: Scoring metric (None = auto-detect)

        Returns:
            Global explanation with permutation importances
        """
        # Convert to arrays
        if isinstance(X, pd.DataFrame):
            X_array = X.values
        else:
            X_array = X

        if isinstance(y, pd.Series):
            y_array = y.values
        else:
            y_array = y

        # Calculate permutation importance
        result = permutation_importance(
            estimator=self.model,
            X=X_array,
            y=y_array,
            n_repeats=n_repeats,
            random_state=random_state,
            scoring=scoring,
            n_jobs=-1,
        )

        # Create feature importance list
        feature_importances = []
        sorted_indices = np.argsort(result.importances_mean)[::-1]

        for rank, idx in enumerate(sorted_indices, 1):
            if self.feature_names:
                feature_name = self.feature_names[idx]
            else:
                feature_name = f"feature_{idx}"

            # Calculate 95% confidence interval
            importance_std = result.importances_std[idx]
            ci_lower = result.importances_mean[idx] - 1.96 * importance_std
            ci_upper = result.importances_mean[idx] + 1.96 * importance_std

            feature_importances.append(
                FeatureImportance(
                    feature_name=feature_name,
                    importance=float(result.importances_mean[idx]),
                    rank=rank,
                    std=float(importance_std),
                    confidence_interval=(float(ci_lower), float(ci_upper)),
                )
            )

        # Calculate prediction statistics
        predictions = self.model.predict(X_array)

        return GlobalExplanation(
            feature_importances=feature_importances,
            num_instances=len(X_array),
            prediction_mean=float(np.mean(predictions)),
            prediction_std=float(np.std(predictions)),
            explanation_type=ExplanationType.FEATURE_IMPORTANCE,
            model_type=self.model_type,
        )

    def get_drop_column_importance(
        self,
        X: Union[np.ndarray, pd.DataFrame],
        y: Union[np.ndarray, pd.Series],
        metric: Callable = None,
        cv: int = 3,
    ) -> GlobalExplanation:
        """
        Calculate drop-column importance

        Measures how much performance decreases when a feature is completely removed.
        More expensive than permutation importance but can capture feature interactions.

        Args:
            X: Feature matrix
            y: Target values
            metric: Scoring function (default: MSE for regression, accuracy for classification)
            cv: Number of cross-validation folds

        Returns:
            Global explanation with drop-column importances
        """
        from sklearn.model_selection import cross_val_score

        # Convert to DataFrame for easier column dropping
        if isinstance(X, np.ndarray):
            if self.feature_names:
                X_df = pd.DataFrame(X, columns=self.feature_names)
            else:
                X_df = pd.DataFrame(
                    X, columns=[f"feature_{i}" for i in range(X.shape[1])]
                )
        else:
            X_df = X.copy()

        if isinstance(y, pd.Series):
            y_array = y.values
        else:
            y_array = y

        # Default metric
        if metric is None:
            # Detect task type
            unique_values = np.unique(y_array)
            if len(unique_values) <= 10 and np.all(
                unique_values == unique_values.astype(int)
            ):
                metric = accuracy_score
                higher_is_better = True
            else:
                metric = mean_squared_error
                higher_is_better = False
        else:
            higher_is_better = True  # Assume custom metric is better when higher

        # Baseline score (all features)
        baseline_scores = cross_val_score(self.model, X_df, y_array, cv=cv, n_jobs=-1)
        baseline_mean = np.mean(baseline_scores)

        # Calculate importance for each feature
        importances = []
        for col in X_df.columns:
            # Drop one column
            X_dropped = X_df.drop(columns=[col])

            # Score without this feature
            scores = cross_val_score(self.model, X_dropped, y_array, cv=cv, n_jobs=-1)
            dropped_mean = np.mean(scores)

            # Importance = how much performance decreased
            if higher_is_better:
                importance = baseline_mean - dropped_mean
            else:
                importance = (
                    dropped_mean - baseline_mean
                )  # For metrics like MSE (lower is better)

            importances.append((col, importance, np.std(scores)))

        # Sort by importance
        importances.sort(key=lambda x: x[1], reverse=True)

        # Create feature importance list
        feature_importances = []
        for rank, (feature_name, importance, std) in enumerate(importances, 1):
            feature_importances.append(
                FeatureImportance(
                    feature_name=feature_name,
                    importance=float(importance),
                    rank=rank,
                    std=float(std),
                )
            )

        # Calculate prediction statistics
        predictions = self.model.predict(X_df.values)

        return GlobalExplanation(
            feature_importances=feature_importances,
            num_instances=len(X_df),
            prediction_mean=float(np.mean(predictions)),
            prediction_std=float(np.std(predictions)),
            explanation_type=ExplanationType.FEATURE_IMPORTANCE,
            model_type=self.model_type,
        )

    def compare_methods(
        self,
        X: Union[np.ndarray, pd.DataFrame],
        y: Union[np.ndarray, pd.Series],
        methods: list[str] = ["intrinsic", "permutation"],
    ) -> dict[str, GlobalExplanation]:
        """
        Compare feature importance across multiple methods

        Args:
            X: Feature matrix
            y: Target values
            methods: List of methods to compare ("intrinsic", "permutation", "drop_column")

        Returns:
            Dict mapping method name to GlobalExplanation
        """
        results = {}

        if "intrinsic" in methods:
            intrinsic = self.get_intrinsic_importance()
            if intrinsic:
                results["intrinsic"] = intrinsic

        if "permutation" in methods:
            results["permutation"] = self.get_permutation_importance(X, y)

        if "drop_column" in methods:
            results["drop_column"] = self.get_drop_column_importance(X, y)

        return results

    def plot_comparison(
        self,
        X: Union[np.ndarray, pd.DataFrame],
        y: Union[np.ndarray, pd.Series],
        methods: list[str] = ["intrinsic", "permutation"],
        top_k: int = 10,
        save_path: Optional[str] = None,
    ):
        """
        Plot feature importance comparison across methods

        Args:
            X: Feature matrix
            y: Target values
            methods: Methods to compare
            top_k: Number of top features to show
            save_path: Optional path to save plot
        """
        import matplotlib.pyplot as plt

        # Get importance from all methods
        results = self.compare_methods(X, y, methods)

        # Create figure
        fig, axes = plt.subplots(1, len(results), figsize=(6 * len(results), 8))
        if len(results) == 1:
            axes = [axes]

        for ax, (method_name, explanation) in zip(axes, results.items()):
            # Get top k features
            top_features = explanation.feature_importances[:top_k]

            features = [f.feature_name for f in top_features]
            importances = [f.importance for f in top_features]

            # Plot
            ax.barh(features[::-1], importances[::-1])
            ax.set_xlabel("Importance")
            ax.set_title(f"{method_name.capitalize()} Importance")
            ax.grid(axis="x", alpha=0.3)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, bbox_inches="tight", dpi=300)
            self.logger.info(f"Saved importance comparison plot to {save_path}")
        else:
            plt.show()

        plt.close()
