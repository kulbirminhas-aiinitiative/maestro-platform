"""
SHAP (SHapley Additive exPlanations) Explainer

Provides global and local explanations using SHAP values.
"""

import logging
from typing import Any, Optional, Union

import numpy as np
import pandas as pd

try:
    import shap

    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False

from ..models.explanation_models import (
    ExplanationType,
    FeatureImportance,
    GlobalExplanation,
    LocalExplanation,
    ModelType,
    SHAPValues,
)

logger = logging.getLogger(__name__)


class SHAPExplainer:
    """
    SHAP-based model explainer

    Supports:
    - Tree-based models (XGBoost, LightGBM, RandomForest)
    - Linear models
    - Deep learning models
    - Any black-box model (via Kernel SHAP)

    SHAP values represent the contribution of each feature to the prediction,
    with the guarantee that contributions sum to (prediction - baseline).
    """

    def __init__(
        self,
        model: Any,
        model_type: ModelType = ModelType.BLACK_BOX,
        feature_names: Optional[list[str]] = None,
        class_names: Optional[list[str]] = None,
    ):
        """
        Initialize SHAP explainer

        Args:
            model: Trained model to explain
            model_type: Type of model (determines which SHAP explainer to use)
            feature_names: List of feature names
            class_names: List of class names (for classification)
        """
        if not SHAP_AVAILABLE:
            raise ImportError("SHAP is not installed. Install with: pip install shap")

        self.model = model
        self.model_type = model_type
        self.feature_names = feature_names
        self.class_names = class_names
        self.explainer = None
        self.logger = logger

    def fit(self, X_train: Union[np.ndarray, pd.DataFrame], **kwargs):
        """
        Fit the SHAP explainer

        Args:
            X_train: Training data (used as background for Kernel SHAP)
            **kwargs: Additional arguments for specific explainers
        """
        if isinstance(X_train, pd.DataFrame):
            if self.feature_names is None:
                self.feature_names = X_train.columns.tolist()
            X_train = X_train.values

        # Choose appropriate explainer based on model type
        if self.model_type == ModelType.TREE_BASED:
            self.explainer = shap.TreeExplainer(self.model, **kwargs)
            self.logger.info("Initialized TreeExplainer for tree-based model")

        elif self.model_type == ModelType.LINEAR:
            self.explainer = shap.LinearExplainer(self.model, X_train, **kwargs)
            self.logger.info("Initialized LinearExplainer for linear model")

        elif self.model_type == ModelType.NEURAL_NETWORK:
            # DeepExplainer for neural networks
            self.explainer = shap.DeepExplainer(self.model, X_train, **kwargs)
            self.logger.info("Initialized DeepExplainer for neural network")

        else:
            # KernelExplainer for any model (model-agnostic, slower)
            # Sample background data for efficiency
            if len(X_train) > 100:
                background = shap.sample(X_train, 100)
            else:
                background = X_train

            self.explainer = shap.KernelExplainer(
                self.model.predict, background, **kwargs
            )
            self.logger.info("Initialized KernelExplainer for black-box model")

    def explain_local(
        self,
        instance: Union[np.ndarray, pd.DataFrame],
        instance_id: Optional[str] = None,
        top_k: int = 5,
    ) -> LocalExplanation:
        """
        Explain a single prediction

        Args:
            instance: Single instance to explain (1D array or single-row DataFrame)
            instance_id: Optional identifier for this instance
            top_k: Number of top features to return

        Returns:
            Local explanation with SHAP values
        """
        if self.explainer is None:
            raise ValueError("Explainer not fitted. Call fit() first.")

        # Convert to appropriate format
        if isinstance(instance, pd.DataFrame):
            instance_values = (
                instance.values[0] if len(instance.shape) == 2 else instance.values
            )
        else:
            instance_values = (
                instance.reshape(1, -1) if len(instance.shape) == 1 else instance
            )

        # Calculate SHAP values
        shap_values = self.explainer.shap_values(instance_values)

        # Handle multi-class classification (get SHAP values for positive class)
        if isinstance(shap_values, list):
            shap_values = shap_values[1]  # Positive class for binary classification

        # Get base value (expected value)
        if hasattr(self.explainer, "expected_value"):
            if isinstance(self.explainer.expected_value, (list, np.ndarray)):
                base_value = self.explainer.expected_value[1]  # Positive class
            else:
                base_value = self.explainer.expected_value
        else:
            base_value = 0.0

        # Get prediction
        prediction = self.model.predict(instance_values)[0]

        # Create feature contributions dict
        if self.feature_names:
            feature_contributions = {
                name: float(shap_values[0][i])
                for i, name in enumerate(self.feature_names)
            }
            feature_values = {
                name: float(instance_values[0][i])
                if isinstance(instance_values[0][i], (int, float, np.number))
                else instance_values[0][i]
                for i, name in enumerate(self.feature_names)
            }
        else:
            feature_contributions = {
                f"feature_{i}": float(val) for i, val in enumerate(shap_values[0])
            }
            feature_values = {
                f"feature_{i}": float(val)
                if isinstance(val, (int, float, np.number))
                else val
                for i, val in enumerate(instance_values[0])
            }

        # Sort features by absolute SHAP value
        sorted_features = sorted(
            feature_contributions.items(), key=lambda x: abs(x[1]), reverse=True
        )

        # Split into positive and negative
        positive = [(f, v) for f, v in sorted_features if v > 0][:top_k]
        negative = [(f, v) for f, v in sorted_features if v < 0][:top_k]

        return LocalExplanation(
            instance_id=instance_id,
            prediction=float(prediction),
            expected_value=float(base_value),
            feature_contributions=feature_contributions,
            feature_values=feature_values,
            top_positive_features=positive,
            top_negative_features=negative,
            explanation_type=ExplanationType.SHAP,
            model_type=self.model_type,
        )

    def explain_global(
        self, X: Union[np.ndarray, pd.DataFrame], num_samples: Optional[int] = None
    ) -> GlobalExplanation:
        """
        Explain overall model behavior

        Args:
            X: Dataset to explain (multiple instances)
            num_samples: Max number of samples to use (for efficiency)

        Returns:
            Global explanation with feature importance
        """
        if self.explainer is None:
            raise ValueError("Explainer not fitted. Call fit() first.")

        # Sample if needed
        if num_samples and len(X) > num_samples:
            indices = np.random.choice(len(X), num_samples, replace=False)
            X_sample = X[indices] if isinstance(X, np.ndarray) else X.iloc[indices]
        else:
            X_sample = X

        # Convert to array
        if isinstance(X_sample, pd.DataFrame):
            X_array = X_sample.values
        else:
            X_array = X_sample

        # Calculate SHAP values
        shap_values = self.explainer.shap_values(X_array)

        # Handle multi-class
        if isinstance(shap_values, list):
            shap_values = shap_values[1]  # Positive class

        # Calculate mean absolute SHAP values (feature importance)
        mean_abs_shap = np.abs(shap_values).mean(axis=0)
        std_shap = np.abs(shap_values).std(axis=0)

        # Create feature importance list
        feature_importances = []
        sorted_indices = np.argsort(mean_abs_shap)[::-1]

        for rank, idx in enumerate(sorted_indices, 1):
            if self.feature_names:
                feature_name = self.feature_names[idx]
            else:
                feature_name = f"feature_{idx}"

            feature_importances.append(
                FeatureImportance(
                    feature_name=feature_name,
                    importance=float(mean_abs_shap[idx]),
                    rank=rank,
                    std=float(std_shap[idx]),
                )
            )

        # Calculate prediction statistics
        predictions = self.model.predict(X_array)

        return GlobalExplanation(
            feature_importances=feature_importances,
            num_instances=len(X_array),
            prediction_mean=float(np.mean(predictions)),
            prediction_std=float(np.std(predictions)),
            explanation_type=ExplanationType.SHAP,
            model_type=self.model_type,
        )

    def get_shap_values(self, instance: Union[np.ndarray, pd.DataFrame]) -> SHAPValues:
        """
        Get raw SHAP values for an instance

        Args:
            instance: Instance to explain

        Returns:
            SHAP values object
        """
        if self.explainer is None:
            raise ValueError("Explainer not fitted. Call fit() first.")

        # Convert to array
        if isinstance(instance, pd.DataFrame):
            instance_values = (
                instance.values[0] if len(instance.shape) == 2 else instance.values
            )
        else:
            instance_values = (
                instance.reshape(1, -1) if len(instance.shape) == 1 else instance
            )

        # Calculate SHAP values
        shap_values = self.explainer.shap_values(instance_values)

        # Handle multi-class
        if isinstance(shap_values, list):
            shap_values = shap_values[1]

        # Get base value
        if hasattr(self.explainer, "expected_value"):
            if isinstance(self.explainer.expected_value, (list, np.ndarray)):
                base_value = self.explainer.expected_value[1]
            else:
                base_value = self.explainer.expected_value
        else:
            base_value = 0.0

        # Get prediction
        prediction = self.model.predict(instance_values)[0]

        # Create SHAP values dict
        if self.feature_names:
            shap_dict = {
                name: float(shap_values[0][i])
                for i, name in enumerate(self.feature_names)
            }
            values_dict = {
                name: float(instance_values[0][i])
                if isinstance(instance_values[0][i], (int, float, np.number))
                else instance_values[0][i]
                for i, name in enumerate(self.feature_names)
            }
        else:
            shap_dict = {
                f"feature_{i}": float(val) for i, val in enumerate(shap_values[0])
            }
            values_dict = {
                f"feature_{i}": float(val)
                if isinstance(val, (int, float, np.number))
                else val
                for i, val in enumerate(instance_values[0])
            }

        return SHAPValues(
            base_value=float(base_value),
            shap_values=shap_dict,
            feature_values=values_dict,
            prediction=float(prediction),
        )

    def plot_summary(
        self, X: Union[np.ndarray, pd.DataFrame], save_path: Optional[str] = None
    ):
        """
        Create SHAP summary plot

        Args:
            X: Dataset to explain
            save_path: Optional path to save plot
        """
        import matplotlib.pyplot as plt

        if self.explainer is None:
            raise ValueError("Explainer not fitted. Call fit() first.")

        # Convert to array
        if isinstance(X, pd.DataFrame):
            X_array = X.values
        else:
            X_array = X

        # Calculate SHAP values
        shap_values = self.explainer.shap_values(X_array)

        # Handle multi-class
        if isinstance(shap_values, list):
            shap_values = shap_values[1]

        # Create summary plot
        shap.summary_plot(shap_values, X, feature_names=self.feature_names, show=False)

        if save_path:
            plt.savefig(save_path, bbox_inches="tight", dpi=300)
            self.logger.info(f"Saved SHAP summary plot to {save_path}")
        else:
            plt.show()

        plt.close()

    def plot_waterfall(
        self, instance: Union[np.ndarray, pd.DataFrame], save_path: Optional[str] = None
    ):
        """
        Create SHAP waterfall plot for a single instance

        Args:
            instance: Instance to explain
            save_path: Optional path to save plot
        """
        import matplotlib.pyplot as plt

        shap_values_obj = self.get_shap_values(instance)

        # Create waterfall plot (requires SHAP >= 0.40)
        if hasattr(shap, "plots"):
            # Convert to SHAP Explanation object
            if isinstance(instance, pd.DataFrame):
                instance_values = instance.values[0]
            else:
                instance_values = instance.reshape(-1)

            explanation = shap.Explanation(
                values=np.array(list(shap_values_obj.shap_values.values())),
                base_values=shap_values_obj.base_value,
                data=instance_values,
                feature_names=self.feature_names,
            )

            shap.plots.waterfall(explanation, show=False)

            if save_path:
                plt.savefig(save_path, bbox_inches="tight", dpi=300)
                self.logger.info(f"Saved waterfall plot to {save_path}")
            else:
                plt.show()

            plt.close()
        else:
            self.logger.warning("Waterfall plot requires SHAP >= 0.40")
